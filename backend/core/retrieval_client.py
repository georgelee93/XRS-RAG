"""
OpenAI Retrieval API Client
Handles interaction with OpenAI's file storage and retrieval capabilities
"""

import os
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
import asyncio
from tenacity import retry, stop_after_attempt, wait_exponential
import httpx

from openai import OpenAI, AsyncOpenAI
from openai.types.beta import Assistant, Thread
from openai.types.beta.threads import Message, Run
# import tiktoken  # Optional for token counting

from .utils import get_env_var, calculate_cost


logger = logging.getLogger(__name__)


class RetrievalAPIClient:
    """Client for OpenAI's Retrieval API"""
    
    def __init__(self, api_key: Optional[str] = None):
        # Always get fresh API key from config
        from core.config import get_settings
        settings = get_settings()
        self.api_key = api_key or settings.openai_api_key
        self.client = OpenAI(
            api_key=self.api_key,
            default_headers={"OpenAI-Beta": "assistants=v2"}
        )
        self.async_client = AsyncOpenAI(
            api_key=self.api_key,
            default_headers={"OpenAI-Beta": "assistants=v2"}
        )
        self.assistant_id = None
        self.vector_store_id = None
        self.file_ids = []
        
    async def initialize_assistant(self, name: str = "청암 챗봇 Assistant", 
                                 instructions: str = """You are 청암 챗봇, a helpful assistant that answers questions based on the provided documents.

CRITICAL INSTRUCTIONS:
1. Always use the file_search tool to search through attached files when asked about documents
2. NEVER hallucinate document names - only refer to files that are actually attached
3. If no relevant information is found, clearly state "업로드된 문서에서 해당 정보를 찾을 수 없습니다"
4. Cite source documents when providing information
5. Synthesize information from multiple sources when relevant

Respond in the same language as the user's question (Korean or English)."""):
        """Create or retrieve an assistant with file search capabilities (v2)"""
        try:
            print("[ASSISTANT] Initializing assistant...")
            
            # Get settings from config
            from core.config import get_settings
            settings = get_settings()
            
            # Use settings if available
            name = settings.assistant_name if hasattr(settings, 'assistant_name') else name
            model = settings.assistant_model if hasattr(settings, 'assistant_model') else "gpt-4-turbo-preview"
            
            # Get assistant configuration from settings (env vars or JSON fallback)
            assistant_config = settings.get_assistant_config()
            existing_assistant_id = assistant_config.get("assistant_id")
            existing_vector_store_id = assistant_config.get("vector_store_id")
            
            if existing_assistant_id:
                print(f"[ASSISTANT] Found existing assistant in configuration: {existing_assistant_id}")
            
            if existing_assistant_id:
                try:
                    # Verify assistant still exists
                    assistant = await self.async_client.beta.assistants.retrieve(existing_assistant_id)
                    print(f"[ASSISTANT] Using existing assistant: {existing_assistant_id}")
                    self.assistant_id = existing_assistant_id
                    self.vector_store_id = existing_vector_store_id
                    
                    # Create vector store if it doesn't exist
                    if not existing_vector_store_id:
                        print("[ASSISTANT] No vector store found, creating one...")
                        vs_id = await self._create_and_attach_vector_store()
                        if vs_id:
                            self.vector_store_id = vs_id
                            print(f"[ASSISTANT] Vector store created: {vs_id}")
                    
                    # Sync files with vector store
                    await self.sync_vector_store_files()
                    return assistant
                except Exception as e:
                    print(f"[ASSISTANT] Could not retrieve existing assistant: {str(e)}")
                    print("[ASSISTANT] Will create new assistant")
            
            # Get all file IDs from document manager
            file_ids = []
            try:
                from .document_manager_supabase import DocumentManagerSupabase
                doc_manager = DocumentManagerSupabase(self)
                
                # Get all active documents from Supabase
                documents = await doc_manager.list_documents()
                for doc in documents:
                    # Check for OpenAI file ID (correct field name)
                    if doc.get("openai_file_id"):
                        file_ids.append(doc["openai_file_id"])
                        print(f"[ASSISTANT] Found file: {doc.get('filename')} - {doc['openai_file_id']}")
                
                print(f"[ASSISTANT] Found {len(file_ids)} files in database")
            except Exception as e:
                print(f"[ASSISTANT] Could not get file IDs from database: {str(e)}")
            
            # Skip vector store creation for now - use direct file attachments
            vector_store_id = None
            self.file_ids = file_ids
            print(f"[ASSISTANT] Will use {len(file_ids)} files directly with assistant")
            
            # Create assistant with settings from config
            assistant_config = {
                "name": name,
                "instructions": instructions,
                "model": model,
            }
            
            # Configure tools based on available features
            if vector_store_id:
                # Use file_search with vector store
                assistant_config["tools"] = [{"type": "file_search"}]
                assistant_config["tool_resources"] = {
                    "file_search": {
                        "vector_store_ids": [vector_store_id]
                    }
                }
                print(f"[ASSISTANT] Using file_search with vector store")
            else:
                # No vector store, use file_search without vector store
                assistant_config["tools"] = [{"type": "file_search"}]
                print(f"[ASSISTANT] Using file_search tool (files will be attached to messages)")
                self.file_ids = file_ids  # Store for later use
            
            assistant = await self.async_client.beta.assistants.create(**assistant_config)
            self.assistant_id = assistant.id
            self.vector_store_id = vector_store_id
            
            # Save to config file for future use
            # Save assistant ID to config file only if not using env vars
            if not settings.openai_assistant_id:
                import json
                from datetime import datetime
                config = {
                    "assistant_id": self.assistant_id,
                    "vector_store_id": self.vector_store_id,
                    "created_at": datetime.now().isoformat(),
                    "last_updated": datetime.now().isoformat()
                }
                with open(settings.assistant_config_path, 'w') as f:
                    json.dump(config, f, indent=2)
                print(f"[ASSISTANT] Saved new assistant config to {settings.assistant_config_path}")
            
            print(f"[ASSISTANT] Created assistant: {self.assistant_id}")
            if self.vector_store_id:
                print(f"[ASSISTANT] With vector store: {self.vector_store_id}")
            logger.info(f"Created assistant with ID: {self.assistant_id}, vector store: {vector_store_id}")
            return assistant
            
        except Exception as e:
            print(f"[ASSISTANT] Error creating assistant: {str(e)}")
            logger.error(f"Error creating assistant: {str(e)}")
            raise
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    async def add_file_to_vector_store_direct(self, file_id: str, vector_store_id: str) -> bool:
        """Add file to vector store using direct API call"""
        try:
            api_key = self.api_key
            
            # Use direct HTTP call to add file to vector store
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"https://api.openai.com/v1/vector_stores/{vector_store_id}/files",
                    headers={
                        "Authorization": f"Bearer {api_key}",
                        "OpenAI-Beta": "assistants=v2"
                    },
                    json={"file_id": file_id}
                )
                
                if response.status_code == 200:
                    print(f"[OPENAI] Successfully added file {file_id} to vector store {vector_store_id}")
                    logger.info(f"Added file {file_id} to vector store {vector_store_id} via direct API")
                    return True
                else:
                    print(f"[OPENAI] Failed to add file to vector store: {response.status_code}")
                    print(f"[OPENAI] Response: {response.text}")
                    return False
                    
        except Exception as e:
            print(f"[OPENAI] Error adding file to vector store: {str(e)}")
            logger.error(f"Error in add_file_to_vector_store_direct: {str(e)}")
            return False
    
    async def upload_file(self, file_path: str, purpose: str = "assistants", original_filename: str = None) -> str:
        """Upload a file to OpenAI for retrieval"""
        try:
            logger.info(f"[OPENAI API] Starting file upload")
            logger.info(f"  - File path: {file_path}")
            logger.info(f"  - Purpose: {purpose}")
            
            file_size = os.path.getsize(file_path)
            logger.info(f"  - File size: {file_size:,} bytes ({file_size/1024/1024:.2f} MB)")
            
            # Log file info
            import mimetypes
            mime_type, _ = mimetypes.guess_type(file_path)
            logger.info(f"  - MIME type: {mime_type}")
            logger.info(f"  - File exists: {os.path.exists(file_path)}")
            
            with open(file_path, 'rb') as file:
                logger.debug(f"[OPENAI API] Sending file to OpenAI API...")
                # Use original filename if provided, otherwise use basename
                filename = original_filename if original_filename else os.path.basename(file_path)
                logger.info(f"  - Uploading with filename: {filename}")
                response = await self.async_client.files.create(
                    file=(filename, file),
                    purpose=purpose
                )
            
            file_id = response.id
            self.file_ids.append(file_id)
            
            logger.info(f"[OPENAI API] File upload successful")
            logger.info(f"  - File ID: {file_id}")
            logger.info(f"  - Response status: {response.status if hasattr(response, 'status') else 'N/A'}")
            
            print(f"[OPENAI] Successfully uploaded file to OpenAI - File ID: {file_id}")
            
            # Add file to vector store if we have one
            if self.vector_store_id:
                print(f"[OPENAI] Adding file to vector store {self.vector_store_id}...")
                success = await self.add_file_to_vector_store_direct(file_id, self.vector_store_id)
                if success:
                    print(f"[OPENAI] File successfully added to vector store")
                else:
                    print(f"[OPENAI] Failed to add file to vector store, will use direct attachment")
                    # Still keep file ID for direct attachment as fallback
                    
            # Keep the assistant configuration updated
            if self.assistant_id:
                try:
                    # Ensure file_search tool is enabled and vector store is attached
                    update_params = {
                        "tools": [{"type": "file_search"}]
                    }
                    
                    if self.vector_store_id:
                        update_params["tool_resources"] = {
                            "file_search": {
                                "vector_store_ids": [self.vector_store_id]
                            }
                        }
                    
                    await self.async_client.beta.assistants.update(
                        assistant_id=self.assistant_id,
                        **update_params
                    )
                    print(f"[OPENAI] Assistant configuration updated")
                except Exception as e:
                    print(f"[OPENAI] Warning: Could not update assistant: {str(e)}")
            
            print(f"[OPENAI] File ready for use in conversations")
            
            logger.info(f"Uploaded file {file_path} with ID: {file_id}")
            return file_id
            
        except Exception as e:
            logger.error(f"[OPENAI API] File upload failed")
            logger.error(f"  - Error: {str(e)}")
            logger.error(f"  - Error type: {type(e).__name__}")
            logger.error(f"  - File path: {file_path}")
            import traceback
            logger.error(f"  - Traceback: {traceback.format_exc()}")
            raise
    
    async def _create_and_attach_vector_store(self, file_ids=None):
        """Create vector store and attach to assistant"""
        try:
            # Get file IDs if not provided
            if file_ids is None:
                file_ids = []
                try:
                    from .document_manager_supabase import DocumentManagerSupabase
                    doc_manager = DocumentManagerSupabase(self)
                    documents = await doc_manager.list_documents()
                    for doc in documents:
                        if doc.get("openai_file_id"):
                            file_ids.append(doc["openai_file_id"])
                    print(f"[ASSISTANT] Found {len(file_ids)} files for vector store")
                except Exception as e:
                    print(f"[ASSISTANT] Could not get files: {str(e)}")
            
            # Create vector store
            print("[ASSISTANT] Creating vector store...")
            vector_store_params = {"name": "청암 챗봇 Document Store"}
            if file_ids:
                vector_store_params["file_ids"] = file_ids
            
            vector_store = await self.async_client.vector_stores.create(**vector_store_params)
            self.vector_store_id = vector_store.id
            print(f"[ASSISTANT] Created vector store: {self.vector_store_id}")
            
            # Update assistant with vector store
            if self.assistant_id:
                await self.async_client.beta.assistants.update(
                    self.assistant_id,
                    tool_resources={
                        "file_search": {
                            "vector_store_ids": [self.vector_store_id]
                        }
                    }
                )
                print(f"[ASSISTANT] Attached vector store to assistant")
            
            # Update config file only if not using env vars
            from core.config import get_settings
            settings = get_settings()
            if not settings.openai_vector_store_id:
                import json
                from datetime import datetime
                config_file = settings.assistant_config_path
                config = {}
                if os.path.exists(config_file):
                    with open(config_file, 'r') as f:
                        config = json.load(f)
                
                config["vector_store_id"] = self.vector_store_id
                config["last_updated"] = datetime.now().isoformat()
                
                with open(config_file, 'w') as f:
                    json.dump(config, f, indent=2)
            
            return self.vector_store_id
            
        except Exception as e:
            print(f"[ASSISTANT] Failed to create vector store: {str(e)}")
            return None
    
    async def _add_file_to_assistant(self, file_id):
        """Add file directly to assistant (fallback method)"""
        if not self.assistant_id:
            return
            
        try:
            print(f"[OPENAI] Adding file {file_id} to assistant...")
            current_files = list(self.file_ids) if self.file_ids else []
            if file_id not in current_files:
                current_files.append(file_id)
            
            await self.async_client.beta.assistants.update(
                self.assistant_id,
                file_ids=current_files
            )
            self.file_ids = current_files
            print(f"[OPENAI] File added to assistant successfully")
            logger.info(f"Added file {file_id} to assistant {self.assistant_id}")
        except Exception as e:
            print(f"[OPENAI] Failed to add file to assistant: {str(e)}")
            logger.error(f"Failed to add file {file_id} to assistant: {str(e)}")
    
    async def list_vector_store_files(self, vector_store_id: str) -> List[Any]:
        """List all files in a vector store"""
        try:
            # Use direct API call since the SDK may not expose this properly
            import httpx
            
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"https://api.openai.com/v1/vector_stores/{vector_store_id}/files",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "OpenAI-Beta": "assistants=v2"
                    }
                )
                
                if response.status_code == 200:
                    data = response.json()
                    files = data.get('data', [])
                    logger.info(f"Found {len(files)} files in vector store {vector_store_id}")
                    
                    # Convert to objects with filename attribute
                    file_objects = []
                    for file_data in files:
                        # Try to get the actual file info
                        try:
                            file_response = await client.get(
                                f"https://api.openai.com/v1/files/{file_data['id']}",
                                headers={
                                    "Authorization": f"Bearer {self.api_key}",
                                    "OpenAI-Beta": "assistants=v2"
                                }
                            )
                            if file_response.status_code == 200:
                                file_info = file_response.json()
                                # Create a simple object with filename
                                class FileObject:
                                    def __init__(self, id, filename):
                                        self.id = id
                                        self.filename = filename
                                
                                file_objects.append(FileObject(
                                    file_data['id'],
                                    file_info.get('filename', file_data['id'])
                                ))
                        except:
                            # If we can't get file info, just use ID
                            class FileObject:
                                def __init__(self, id):
                                    self.id = id
                                    self.filename = id
                            file_objects.append(FileObject(file_data['id']))
                    
                    return file_objects
                else:
                    logger.warning(f"Failed to list vector store files: {response.status_code}")
                    return []
                    
        except Exception as e:
            logger.error(f"Error listing vector store files: {str(e)}")
            return []
    
    async def attach_files_to_assistant(self, file_ids: Optional[List[str]] = None):
        """Attach uploaded files to the assistant"""
        if not self.assistant_id:
            raise ValueError("Assistant not initialized")
        
        files_to_attach = file_ids or self.file_ids
        
        try:
            # Update assistant with file IDs
            assistant = await self.async_client.beta.assistants.update(
                self.assistant_id,
                file_ids=files_to_attach
            )
            
            logger.info(f"Attached {len(files_to_attach)} files to assistant")
            return assistant
            
        except Exception as e:
            logger.error(f"Error attaching files: {str(e)}")
            raise
    
    async def create_thread(self) -> Thread:
        """Create a new conversation thread"""
        try:
            thread = await self.async_client.beta.threads.create()
            logger.info(f"Created thread with ID: {thread.id}")
            return thread
            
        except Exception as e:
            logger.error(f"Error creating thread: {str(e)}")
            raise
    
    async def add_message(self, thread_id: str, content: str, role: str = "user") -> Message:
        """Add a message to a thread with file attachments"""
        try:
            # Prepare attachments if we have file IDs
            attachments = []
            if self.file_ids and role == "user":
                # Attach all uploaded files to the message
                for file_id in self.file_ids:
                    attachments.append({
                        "file_id": file_id,
                        "tools": [{"type": "file_search"}]
                    })
                print(f"[OPENAI] Attaching {len(attachments)} files to message")
            
            # Create message with or without attachments
            if attachments:
                message = await self.async_client.beta.threads.messages.create(
                    thread_id=thread_id,
                    role=role,
                    content=content,
                    attachments=attachments
                )
            else:
                message = await self.async_client.beta.threads.messages.create(
                    thread_id=thread_id,
                    role=role,
                    content=content
                )
            
            logger.debug(f"Added message to thread {thread_id} with {len(attachments)} attachments")
            return message
            
        except Exception as e:
            logger.error(f"Error adding message: {str(e)}")
            raise
    
    async def run_assistant(self, thread_id: str, instructions: Optional[str] = None) -> Run:
        """Run the assistant on a thread"""
        if not self.assistant_id:
            raise ValueError("Assistant not initialized")
        
        try:
            run = await self.async_client.beta.threads.runs.create(
                thread_id=thread_id,
                assistant_id=self.assistant_id,
                instructions=instructions
            )
            
            logger.info(f"Started run {run.id} on thread {thread_id}")
            return run
            
        except Exception as e:
            logger.error(f"Error running assistant: {str(e)}")
            raise
    
    async def wait_for_run_completion(self, thread_id: str, run_id: str, 
                                    timeout: int = 300) -> Run:
        """Wait for a run to complete with timeout"""
        start_time = datetime.now()
        
        while (datetime.now() - start_time).seconds < timeout:
            try:
                run = await self.async_client.beta.threads.runs.retrieve(
                    thread_id=thread_id,
                    run_id=run_id
                )
                
                if run.status == "completed":
                    logger.info(f"Run {run_id} completed successfully")
                    return run
                elif run.status in ["failed", "cancelled", "expired"]:
                    logger.error(f"Run {run_id} failed with status: {run.status}")
                    raise Exception(f"Run failed with status: {run.status}")
                
                await asyncio.sleep(1)
                
            except Exception as e:
                logger.error(f"Error checking run status: {str(e)}")
                raise
        
        raise TimeoutError(f"Run {run_id} timed out after {timeout} seconds")
    
    async def get_messages(self, thread_id: str, limit: int = 20) -> List[Message]:
        """Retrieve messages from a thread"""
        try:
            messages = await self.async_client.beta.threads.messages.list(
                thread_id=thread_id,
                limit=limit
            )
            
            return messages.data
            
        except Exception as e:
            logger.error(f"Error retrieving messages: {str(e)}")
            raise
    
    async def sync_vector_store_files(self):
        """Sync all files from database with the vector store"""
        if not self.vector_store_id:
            print("[ASSISTANT] No vector store to sync")
            return
        
        try:
            print(f"[ASSISTANT] Syncing files with vector store {self.vector_store_id}...")
            
            # Get all file IDs from document manager
            from .document_manager_supabase import DocumentManagerSupabase
            doc_manager = DocumentManagerSupabase(self)
            
            # Get all active documents from Supabase
            documents = await doc_manager.list_documents()
            db_file_ids = set()
            for doc in documents:
                if doc.get("openai_file_id"):  # Use correct field name
                    db_file_ids.add(doc["openai_file_id"])
            
            print(f"[ASSISTANT] Found {len(db_file_ids)} files in database")
            
            # Files must be managed through vector store in v2 API
            if db_file_ids and self.assistant_id:
                # Store file IDs for reference (cannot directly attach to assistant)
                self.file_ids = list(db_file_ids)
                print(f"[ASSISTANT] Found {len(self.file_ids)} files (managed through vector store)")
            else:
                print("[ASSISTANT] No files to sync or assistant not initialized")
                
        except Exception as e:
            print(f"[ASSISTANT] Error syncing vector store: {str(e)}")
            logger.error(f"Error syncing vector store: {str(e)}")
    
    async def process_with_thread(self, message: str, thread_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Process a message with the assistant using a thread
        This is the main method for chat interactions
        """
        try:
            # Create thread if not provided
            if not thread_id:
                thread = await self.create_thread()
                thread_id = thread.id
            
            # Add user message
            await self.add_message(thread_id, message)
            
            # Run assistant
            run = await self.run_assistant(thread_id)
            
            # Wait for completion
            completed_run = await self.wait_for_run_completion(thread_id, run.id)
            
            # Get the response
            messages = await self.get_messages(thread_id, limit=1)
            
            if messages and messages[0].role == "assistant":
                response_content = messages[0].content[0].text.value if messages[0].content else ""
                
                # Calculate usage (estimate)
                total_tokens = len(message.split()) + len(response_content.split())
                
                return {
                    "response": response_content,
                    "thread_id": thread_id,
                    "usage": {
                        "total_tokens": total_tokens,
                        "cost": total_tokens * 0.00001  # Rough estimate
                    },
                    "metadata": {
                        "run_id": run.id,
                        "status": completed_run.status
                    }
                }
            else:
                return {
                    "response": "I couldn't generate a response. Please try again.",
                    "thread_id": thread_id,
                    "usage": {},
                    "metadata": {}
                }
                
        except Exception as e:
            logger.error(f"Error in process_with_thread: {str(e)}")
            return {
                "response": f"Error: {str(e)}",
                "thread_id": thread_id,
                "usage": {},
                "metadata": {"error": str(e)}
            }
    
    async def add_to_vector_store(self, file_content: bytes, filename: str) -> str:
        """
        Add a file to the vector store
        
        Args:
            file_content: File content as bytes
            filename: Name of the file
            
        Returns:
            File ID in the vector store
        """
        try:
            # First upload file to OpenAI
            file = await self.async_client.files.create(
                file=(filename, file_content),
                purpose='assistants'
            )
            
            # Add to vector store if we have one
            if self.vector_store_id:
                await self.async_client.vector_stores.files.create(
                    vector_store_id=self.vector_store_id,
                    file_id=file.id
                )
                logger.info(f"Added file {filename} to vector store: {file.id}")
            else:
                logger.warning(f"No vector store configured, file uploaded but not indexed: {file.id}")
            
            return file.id
            
        except Exception as e:
            logger.error(f"Error adding file to vector store: {str(e)}")
            raise
    
    async def search(self, query: str, thread_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Perform a search using the retrieval API
        Returns the assistant's response with retrieved context
        """
        try:
            # Create thread if not provided
            if not thread_id:
                thread = await self.create_thread()
                thread_id = thread.id
            
            # Add user message
            await self.add_message(thread_id, query)
            
            # Run assistant
            run = await self.run_assistant(thread_id)
            
            # Wait for completion
            await self.wait_for_run_completion(thread_id, run.id)
            
            # Get messages
            messages = await self.get_messages(thread_id)
            
            # Extract assistant's response
            assistant_messages = [
                msg for msg in messages 
                if msg.role == "assistant" and msg.run_id == run.id
            ]
            
            if assistant_messages:
                response_content = assistant_messages[0].content[0].text.value
                
                # Extract annotations (citations) if any
                annotations = []
                if hasattr(assistant_messages[0].content[0].text, 'annotations'):
                    annotations = assistant_messages[0].content[0].text.annotations
                
                return {
                    "response": response_content,
                    "thread_id": thread_id,
                    "run_id": run.id,
                    "annotations": annotations,
                    "status": "success"
                }
            else:
                return {
                    "response": None,
                    "thread_id": thread_id,
                    "run_id": run.id,
                    "status": "no_response"
                }
                
        except Exception as e:
            logger.error(f"Error in search: {str(e)}")
            return {
                "response": None,
                "error": str(e),
                "status": "error"
            }
    
    async def delete_file(self, file_id: str):
        """Delete a file from OpenAI storage and vector store"""
        try:
            logger.info(f"[OPENAI API] Starting file deletion")
            logger.info(f"  - File ID: {file_id}")
            
            # Remove from vector store first if it exists
            if self.vector_store_id:
                try:
                    logger.info(f"[OPENAI API] Removing from vector store: {self.vector_store_id}")
                    await self.async_client.vector_stores.files.delete(
                        vector_store_id=self.vector_store_id,
                        file_id=file_id
                    )
                    logger.info(f"[OPENAI API] Removed from vector store successfully")
                except Exception as vs_error:
                    logger.warning(f"[OPENAI API] Could not remove from vector store: {str(vs_error)}")
            
            # Delete the file itself
            await self.async_client.files.delete(file_id)
            
            if file_id in self.file_ids:
                self.file_ids.remove(file_id)
                logger.debug(f"  - Removed from local file_ids list")
            
            logger.info(f"[OPENAI API] File deletion successful")
            logger.info(f"  - Deleted file ID: {file_id}")
            
        except Exception as e:
            logger.error(f"[OPENAI API] File deletion failed")
            logger.error(f"  - File ID: {file_id}")
            logger.error(f"  - Error: {str(e)}")
            logger.error(f"  - Error type: {type(e).__name__}")
            if "404" in str(e):
                logger.warning(f"  - File may have already been deleted")
            raise
    
    async def list_files(self, purpose: str = "assistants") -> List[Dict[str, Any]]:
        """List all uploaded files"""
        try:
            files = await self.async_client.files.list(purpose=purpose)
            return [
                {
                    "id": f.id,
                    "filename": f.filename,
                    "bytes": f.bytes,
                    "created_at": f.created_at,
                    "purpose": f.purpose
                }
                for f in files.data
            ]
            
        except Exception as e:
            logger.error(f"Error listing files: {str(e)}")
            raise
    
    def estimate_tokens(self, text: str, model: str = "gpt-4") -> int:
        """Estimate token count for text"""
        try:
            encoding = tiktoken.encoding_for_model(model)
            return len(encoding.encode(text))
        except Exception:
            # Fallback estimation
            return len(text) // 4