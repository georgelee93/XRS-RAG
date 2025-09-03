"""
OpenAI Assistant Manager
Handles all interactions with OpenAI's Assistants API v2
"""

import os
import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
import asyncio

from openai import AsyncOpenAI
from openai.types.beta import Assistant, Thread
from openai.types.beta.threads import Message, Run

from ..config import get_settings
from ..timezone_utils import now_kst_iso

logger = logging.getLogger(__name__)


@dataclass
class AssistantConfig:
    """Configuration for OpenAI Assistant"""
    name: str = "청암 챗봇"
    instructions: str = """You are 청암 챗봇, a helpful AI assistant that answers questions based on the uploaded documents.
    
    CRITICAL INSTRUCTIONS:
    1. When asked about documents or their contents, you MUST use the file_search tool to search through attached files
    2. NEVER make up or hallucinate document names - only refer to files that are actually attached
    3. When asked "현재 가지고 있는 문서 이름들 알려줘" or similar, list ONLY the actual file names that are attached to this message
    4. If no relevant information is found in the attached documents, clearly state "업로드된 문서에서 해당 정보를 찾을 수 없습니다"
    5. Always search files before answering questions about document contents
    
    Respond in the same language as the user's question (Korean or English)."""
    model: str = "gpt-4-turbo-preview"
    temperature: float = 0.7
    max_tokens: int = 1000


class OpenAIAssistantManager:
    """Manages OpenAI Assistant v2 with file search for document RAG"""
    
    def __init__(self):
        """Initialize OpenAI Assistant client"""
        settings = get_settings()
        self.api_key = settings.openai_api_key
        self.client = AsyncOpenAI(api_key=self.api_key)
        self.config = AssistantConfig()
        
        # Assistant and vector store management
        self.assistant: Optional[Assistant] = None
        self.assistant_id = settings.openai_assistant_id
        self.vector_store_id: Optional[str] = None
        self.file_registry: Dict[str, Any] = {}
        
        # BigQuery integration (optional)
        self.bigquery_client = None
        if settings.enable_bigquery:
            try:
                from ..integrations.bigquery import BigQueryClient
                self.bigquery_client = BigQueryClient()
                logger.info("BigQuery integration enabled")
            except Exception as e:
                logger.warning(f"BigQuery integration not available: {e}")
        
        logger.info("OpenAI Assistant Manager initialized")
    
    async def initialize(self) -> None:
        """Initialize or retrieve assistant"""
        try:
            if self.assistant_id:
                # Use existing assistant
                self.assistant = await self.client.beta.assistants.retrieve(self.assistant_id)
                logger.info(f"Using existing assistant: {self.assistant_id}")
                
                # Get vector store from assistant
                if hasattr(self.assistant, 'tool_resources') and self.assistant.tool_resources:
                    file_search = getattr(self.assistant.tool_resources, 'file_search', None)
                    if file_search and hasattr(file_search, 'vector_store_ids'):
                        self.vector_store_id = file_search.vector_store_ids[0] if file_search.vector_store_ids else None
                        logger.info(f"Using existing vector store: {self.vector_store_id}")
            else:
                # Create new assistant
                await self._create_assistant()
            
            # Ensure vector store exists
            await self._ensure_vector_store()
            
            # Refresh file registry
            await self._refresh_file_registry()
            
        except Exception as e:
            logger.error(f"Failed to initialize assistant: {e}")
            raise
    
    async def _create_assistant(self) -> None:
        """Create a new assistant with file search capability"""
        logger.info("Creating new assistant with file search...")
        
        # Get existing files
        files = await self.list_files()
        
        # Prepare tools
        tools = [{"type": "file_search"}]
        if self.bigquery_client:
            tools.extend(self._get_bigquery_tools())
        
        # Create assistant
        self.assistant = await self.client.beta.assistants.create(
            name=self.config.name,
            instructions=self.config.instructions,
            model=self.config.model,
            tools=tools,
            temperature=self.config.temperature
        )
        
        logger.info(f"Assistant created: {self.assistant.id}")
        logger.info("=" * 60)
        logger.info("IMPORTANT: Save this assistant ID for reuse!")
        logger.info(f"OPENAI_ASSISTANT_ID={self.assistant.id}")
        logger.info("Add this to your environment variables")
        logger.info("=" * 60)
    
    async def _ensure_vector_store(self) -> None:
        """Ensure vector store exists for the assistant"""
        if not self.vector_store_id:
            logger.info("Creating new vector store...")
            try:
                # Create vector store
                vector_store = await self.client.vector_stores.create(
                    name=f"Vector Store for {self.config.name}"
                )
                self.vector_store_id = vector_store.id
                
                # Update assistant with vector store
                await self.client.beta.assistants.update(
                    self.assistant.id,
                    tool_resources={
                        "file_search": {
                            "vector_store_ids": [self.vector_store_id]
                        }
                    }
                )
                logger.info(f"Vector store created and attached: {self.vector_store_id}")
            except Exception as e:
                logger.error(f"Failed to ensure vector store: {e}")
    
    async def _refresh_file_registry(self) -> None:
        """Refresh the registry of available files"""
        try:
            files = await self.list_files()
            self.file_registry = {f["id"]: f for f in files}
            logger.info(f"File registry refreshed: {len(self.file_registry)} files available")
        except Exception as e:
            logger.error(f"Failed to refresh file registry: {e}")
    
    async def list_files(self) -> List[Dict[str, Any]]:
        """List all files available for assistant"""
        try:
            response = await self.client.files.list(purpose="assistants")
            return [
                {
                    "id": file.id,
                    "filename": file.filename,
                    "created_at": file.created_at,
                    "bytes": file.bytes,
                    "purpose": file.purpose
                }
                for file in response.data
            ]
        except Exception as e:
            logger.error(f"Failed to list files: {e}")
            return []
    
    async def upload_file(self, file_content: bytes, filename: str) -> Dict[str, Any]:
        """Upload a file to OpenAI"""
        try:
            # Upload to OpenAI with original filename preserved
            file_obj = await self.client.files.create(
                file=(filename, file_content),  # Pass filename explicitly to preserve it
                purpose="assistants"
            )
            
            # Add to vector store if available
            if self.vector_store_id:
                try:
                    await self.client.vector_stores.files.create(
                        vector_store_id=self.vector_store_id,
                        file_id=file_obj.id
                    )
                    logger.info(f"File added to vector store: {file_obj.id}")
                except Exception as e:
                    logger.error(f"Failed to add file to vector store: {e}")
            
            # Update registry
            await self._refresh_file_registry()
            
            return {
                "file_id": file_obj.id,
                "filename": filename,
                "size": len(file_content),
                "status": "success"
            }
            
        except Exception as e:
            logger.error(f"Failed to upload file: {e}")
            raise
    
    async def delete_file(self, file_id: str) -> bool:
        """Delete a file from OpenAI"""
        try:
            logger.info(f"Deleting file: {file_id}")
            
            # Remove from vector store if present
            if self.vector_store_id:
                try:
                    await self.client.vector_stores.files.delete(
                        vector_store_id=self.vector_store_id,
                        file_id=file_id
                    )
                    logger.info(f"Removed from vector store: {file_id}")
                except Exception as e:
                    logger.warning(f"Failed to remove from vector store: {e}")
            
            # Delete from OpenAI
            await self.client.files.delete(file_id)
            logger.info(f"Deleted from OpenAI: {file_id}")
            
            # Update registry
            await self._refresh_file_registry()
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete file: {e}")
            return False
    
    async def list_documents(self) -> List[Dict[str, Any]]:
        """List documents with metadata"""
        files = await self.list_files()
        return [
            {
                "file_id": f["id"],
                "filename": f["filename"],
                "created_at": f["created_at"],
                "size_bytes": f["bytes"],
                "purpose": f["purpose"]
            }
            for f in files
        ]
    
    async def create_thread(self) -> Thread:
        """Create a new conversation thread"""
        return await self.client.beta.threads.create()
    
    async def send_message(
        self,
        thread_id: str,
        message: str,
        file_ids: Optional[List[str]] = None
    ) -> str:
        """Send a message to a thread and get response"""
        try:
            # Add message to thread
            # DO NOT attach files to messages - they should be accessed via vector store
            # Attaching files creates duplicate "untitled" vector stores
            await self.client.beta.threads.messages.create(
                thread_id=thread_id,
                role="user",
                content=message
                # No attachments - files are accessed via assistant's vector store
            )
            
            # Run assistant
            run = await self.client.beta.threads.runs.create(
                thread_id=thread_id,
                assistant_id=self.assistant.id,
                temperature=self.config.temperature,
                max_prompt_tokens=25000,
                max_completion_tokens=self.config.max_tokens
            )
            
            # Wait for completion
            while run.status in ["queued", "in_progress", "requires_action"]:
                await asyncio.sleep(1)
                run = await self.client.beta.threads.runs.retrieve(
                    thread_id=thread_id,
                    run_id=run.id
                )
                
                # Handle function calls if BigQuery is enabled
                if run.status == "requires_action" and self.bigquery_client:
                    run = await self._handle_function_calls(thread_id, run)
            
            if run.status != "completed":
                raise Exception(f"Run failed with status: {run.status}")
            
            # Get response
            messages = await self.client.beta.threads.messages.list(
                thread_id=thread_id,
                order="desc",
                limit=1
            )
            
            if messages.data:
                content = messages.data[0].content[0]
                if hasattr(content, 'text'):
                    return content.text.value
            
            return "No response generated"
            
        except Exception as e:
            logger.error(f"Failed to send message: {e}")
            raise
    
    async def _handle_function_calls(self, thread_id: str, run: Run) -> Run:
        """Handle BigQuery function calls"""
        if not run.required_action:
            return run
        
        tool_outputs = []
        for tool_call in run.required_action.submit_tool_outputs.tool_calls:
            if tool_call.function.name == "query_bigquery":
                args = json.loads(tool_call.function.arguments)
                result = await self.bigquery_client.execute_query(args.get("query"))
                tool_outputs.append({
                    "tool_call_id": tool_call.id,
                    "output": json.dumps(result)
                })
        
        if tool_outputs:
            run = await self.client.beta.threads.runs.submit_tool_outputs(
                thread_id=thread_id,
                run_id=run.id,
                tool_outputs=tool_outputs
            )
        
        return run
    
    def _get_bigquery_tools(self) -> List[Dict[str, Any]]:
        """Get BigQuery function tools"""
        return [
            {
                "type": "function",
                "function": {
                    "name": "query_bigquery",
                    "description": "Execute a BigQuery SQL query",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "The SQL query to execute"
                            }
                        },
                        "required": ["query"]
                    }
                }
            }
        ]