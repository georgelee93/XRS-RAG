"""
ChatGPT Integration Module
Handles conversation management and response generation with RAG context
"""

import logging
import json
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
import asyncio
from dataclasses import dataclass, asdict

from openai import AsyncOpenAI
import tiktoken  # For accurate token counting

from .retrieval_client import RetrievalAPIClient
from .utils import calculate_cost, truncate_text, get_env_var
from .session_manager import get_session_manager
from .usage_tracker import get_usage_tracker


logger = logging.getLogger(__name__)


@dataclass
class Message:
    """Represents a conversation message"""
    role: str  # 'user', 'assistant', 'system'
    content: str
    timestamp: datetime = None
    metadata: Optional[Dict[str, Any]] = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API calls"""
        return {
            "role": self.role,
            "content": self.content
        }


@dataclass
class ConversationContext:
    """Maintains conversation context and memory"""
    messages: List[Message]
    thread_id: Optional[str] = None
    total_tokens: int = 0
    total_cost: float = 0.0
    db_session_id: Optional[str] = None  # Database session ID
    
    def add_message(self, message: Message):
        """Add message to conversation history"""
        self.messages.append(message)
    
    def get_messages_for_api(self, max_messages: int = 20) -> List[Dict[str, str]]:
        """Get recent messages formatted for API"""
        recent_messages = self.messages[-max_messages:]
        return [msg.to_dict() for msg in recent_messages]
    
    def clear_old_messages(self, keep_recent: int = 10):
        """Keep only recent messages to manage context window"""
        if len(self.messages) > keep_recent:
            # Always keep system message if present
            system_messages = [msg for msg in self.messages if msg.role == "system"]
            recent_messages = self.messages[-keep_recent:]
            
            self.messages = system_messages + [msg for msg in recent_messages if msg.role != "system"]


class ChatInterface:
    """Main chat interface for RAG-enhanced conversations"""
    
    DEFAULT_SYSTEM_PROMPT = """You are 청암 챗봇, a helpful AI assistant with access to all uploaded documents in the knowledge base.

CRITICAL INSTRUCTIONS:
1. When asked about documents or their contents, you MUST search through the knowledge base first
2. NEVER make up or hallucinate document names - only refer to documents that actually exist
3. If no relevant information is found in the documents, clearly state "업로드된 문서에서 해당 정보를 찾을 수 없습니다"
4. When providing information from documents, always cite the source document name for transparency
5. For multiple relevant documents, synthesize information and cite all sources
6. Ask clarifying questions for ambiguous queries to provide more accurate answers

RESPONSE GUIDELINES:
- Be concise but comprehensive
- Maintain professional and friendly tone
- Use structured format (bullets/numbers) when appropriate
- Explain technical terms briefly when necessary
- Respond in the same language as the user's question (Korean or English)

You can answer questions based on the information available in the system."""
    
    def __init__(self, 
                 retrieval_client: RetrievalAPIClient,
                 model: str = "gpt-4-1106-preview",
                 temperature: float = 0.7,
                 max_tokens: int = 1000):
        
        self.retrieval_client = retrieval_client
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        
        # Initialize OpenAI client for direct chat
        self.openai_client = AsyncOpenAI(
            api_key=get_env_var("OPENAI_API_KEY"),
            default_headers={"OpenAI-Beta": "assistants=v2"}
        )
        
        # Token encoder for counting
        try:
            self.encoder = tiktoken.encoding_for_model(model)
        except Exception:
            # Fallback if model not found
            self.encoder = tiktoken.get_encoding("cl100k_base")
        
        # Conversation contexts by session
        self.conversations: Dict[str, ConversationContext] = {}
        
        # Session manager for persistence
        self.session_manager = get_session_manager()
        
        # Usage tracker
        self.usage_tracker = get_usage_tracker()
    
    async def start_conversation(self, session_id: str, 
                               system_prompt: Optional[str] = None,
                               user_id: Optional[str] = None) -> ConversationContext:
        """Initialize a new conversation"""
        system_prompt = system_prompt or self.DEFAULT_SYSTEM_PROMPT
        
        context = ConversationContext(
            messages=[Message(role="system", content=system_prompt)]
        )
        
        # Create session in database
        db_session = self.session_manager.create_session(
            user_id=user_id,
            thread_id=None,
            title="New Chat"
        )
        
        # Store the database session ID in context
        context.db_session_id = db_session["session_id"]
        
        self.conversations[session_id] = context
        
        logger.info(f"Started new conversation: {session_id}")
        return context
    
    async def send_message(self, session_id: str, user_message: str, 
                          use_retrieval: bool = True,
                          user_id: Optional[str] = None,
                          user_email: Optional[str] = None) -> Dict[str, Any]:
        """Process user message and generate response"""
        try:
            # Get or create conversation context
            if session_id not in self.conversations:
                context = await self.start_conversation(session_id, user_id=user_id)
            else:
                context = self.conversations[session_id]
            
            # Add user message
            user_msg = Message(role="user", content=user_message)
            context.add_message(user_msg)
            
            # Save message to database
            if context.db_session_id:
                try:
                    self.session_manager.add_message(
                        context.db_session_id,
                        role="user",
                        content=user_message
                    )
                except Exception as db_error:
                    logger.warning(f"Failed to save user message to database: {str(db_error)}")
                    # Continue anyway - don't fail the whole request
            
            # Generate response
            if use_retrieval and self.retrieval_client.assistant_id:
                # Use Assistants API v2 with file search
                response = await self._generate_assistant_response(context, user_message)
            else:
                # Fallback to direct response
                response = await self._generate_direct_response(context, user_message)
            
            # Add assistant response to context
            assistant_msg = Message(
                role="assistant", 
                content=response["content"],
                metadata=response.get("metadata")
            )
            context.add_message(assistant_msg)
            
            # Save assistant message to database
            if context.db_session_id:
                try:
                    usage = response.get("usage", {})
                    # Clean metadata for database storage (remove non-serializable objects)
                    clean_metadata = response.get("metadata", {}).copy() if response.get("metadata") else {}
                    if "annotations" in clean_metadata:
                        # Annotations are already converted to serializable format
                        pass
                        
                    self.session_manager.add_message(
                        context.db_session_id,
                        role="assistant",
                        content=response["content"],
                        tokens_used=usage.get("total_tokens", 0),
                        cost_usd=usage.get("cost", 0.0),
                        metadata=clean_metadata
                    )
                except Exception as db_error:
                    logger.warning(f"Failed to save message to database: {str(db_error)}")
                    # Continue anyway - don't fail the whole response
            
            # Update usage stats
            if "usage" in response:
                context.total_tokens += response["usage"]["total_tokens"]
                context.total_cost += response["usage"]["cost"]
            
            # Filter out file reference information from user-facing response
            user_metadata = response.get("metadata", {}).copy()
            if "annotations" in user_metadata:
                # Remove annotations that contain file citations from user response
                user_metadata.pop("annotations", None)
            
            return {
                "status": "success",
                "response": response["content"],
                "metadata": user_metadata,
                "usage": response.get("usage", {}),
                "session_id": session_id
            }
            
        except Exception as e:
            logger.error(f"Error in send_message: {str(e)}")
            return {
                "status": "error",
                "error": str(e),
                "session_id": session_id
            }
    
    async def _generate_assistant_response(self, context: ConversationContext, 
                                         user_message: str) -> Dict[str, Any]:
        """Generate response using Assistants API v2 with file search"""
        start_time = asyncio.get_event_loop().time()
        try:
            print(f"[ASSISTANT] Generating response with Assistant API v2")
            
            # Ensure assistant is initialized
            if not self.retrieval_client.assistant_id:
                print("[ASSISTANT] Assistant not initialized, initializing now...")
                await self.retrieval_client.initialize_assistant()
            
            # Sync files to ensure all documents are available
            await self.retrieval_client.sync_vector_store_files()
            
            # Check configuration
            if hasattr(self.retrieval_client, 'vector_store_id') and self.retrieval_client.vector_store_id:
                print(f"[ASSISTANT] Using vector store: {self.retrieval_client.vector_store_id}")
            elif hasattr(self.retrieval_client, 'file_ids') and self.retrieval_client.file_ids:
                print(f"[ASSISTANT] Using {len(self.retrieval_client.file_ids)} files directly")
            else:
                print(f"[ASSISTANT] No files available for search")
            
            # Create or get thread
            if not context.thread_id:
                # Check if we have a thread_id from session
                if session_id and self.session_manager:
                    session = self.session_manager.get_session(session_id)
                    if session and session.get('thread_id'):
                        context.thread_id = session['thread_id']
                        print(f"[ASSISTANT] Reusing existing thread from session: {context.thread_id}")
                        
                        # Update thread with vector store if needed
                        if hasattr(self.retrieval_client, 'vector_store_id') and self.retrieval_client.vector_store_id:
                            try:
                                # Update the existing thread to ensure it has the vector store
                                await self.retrieval_client.async_client.beta.threads.update(
                                    context.thread_id,
                                    tool_resources={
                                        "file_search": {
                                            "vector_store_ids": [self.retrieval_client.vector_store_id]
                                        }
                                    }
                                )
                                print(f"[ASSISTANT] Updated thread with vector store: {self.retrieval_client.vector_store_id}")
                            except Exception as e:
                                print(f"[ASSISTANT] Could not update thread with vector store: {e}")
                
                # Create new thread only if we don't have one
                if not context.thread_id:
                    thread_params = {}
                    
                    # If we have a vector store with files, attach it to the thread
                    if hasattr(self.retrieval_client, 'vector_store_id') and self.retrieval_client.vector_store_id:
                        thread_params["tool_resources"] = {
                            "file_search": {
                                "vector_store_ids": [self.retrieval_client.vector_store_id]
                            }
                        }
                        print(f"[ASSISTANT] Creating NEW thread with vector store {self.retrieval_client.vector_store_id}")
                    else:
                        print(f"[ASSISTANT] Creating NEW thread without vector store")
                    
                    thread = await self.retrieval_client.async_client.beta.threads.create(**thread_params)
                    context.thread_id = thread.id
                    print(f"[ASSISTANT] Created new thread: {thread.id}")
                    
                    # Update session with thread_id
                    if session_id and self.session_manager:
                        self.session_manager.update_session(session_id, thread_id=context.thread_id)
            
            # Add message to thread
            message_data = {
                "thread_id": context.thread_id,
                "role": "user",
                "content": user_message
            }
            
            # Only attach files directly if we don't have a working vector store
            # If vector store is configured, files should be accessed through it
            if not self.retrieval_client.vector_store_id and hasattr(self.retrieval_client, 'file_ids') and self.retrieval_client.file_ids:
                # Create attachments for file_search as fallback
                attachments = []
                for file_id in self.retrieval_client.file_ids[:10]:  # Max 10 files
                    attachments.append({
                        "file_id": file_id,
                        "tools": [{"type": "file_search"}]
                    })
                if attachments:
                    message_data["attachments"] = attachments
                    print(f"[ASSISTANT] Attaching {len(attachments)} files directly to message (fallback mode)")
            
            await self.retrieval_client.async_client.beta.threads.messages.create(**message_data)
            
            # Run the assistant
            print(f"[ASSISTANT] Running assistant on thread...")
            run = await self.retrieval_client.async_client.beta.threads.runs.create(
                thread_id=context.thread_id,
                assistant_id=self.retrieval_client.assistant_id
            )
            
            # Wait for completion with timeout
            max_wait_time = 50  # 50 seconds max wait time
            wait_time = 0
            while run.status in ["queued", "in_progress"] and wait_time < max_wait_time:
                await asyncio.sleep(1)
                wait_time += 1
                run = await self.retrieval_client.async_client.beta.threads.runs.retrieve(
                    thread_id=context.thread_id,
                    run_id=run.id
                )
                print(f"[ASSISTANT] Run status: {run.status} (waited {wait_time}s)")
            
            # Check if we timed out
            if wait_time >= max_wait_time and run.status in ["queued", "in_progress"]:
                # Cancel the run
                try:
                    await self.retrieval_client.async_client.beta.threads.runs.cancel(
                        thread_id=context.thread_id,
                        run_id=run.id
                    )
                except:
                    pass
                raise TimeoutError("Assistant response timed out after 50 seconds")
            
            if run.status == "completed":
                # Get messages
                messages = await self.retrieval_client.async_client.beta.threads.messages.list(
                    thread_id=context.thread_id
                )
                
                # Get the latest assistant message (skip older messages)
                for msg in messages.data:
                    if msg.role == "assistant" and msg.run_id == run.id:
                        # Debug: print message structure
                        print(f"[ASSISTANT] Message content type: {type(msg.content)}")
                        print(f"[ASSISTANT] Message content: {msg.content}")
                        
                        content = ""
                        if msg.content and len(msg.content) > 0:
                            if hasattr(msg.content[0], 'text'):
                                content = msg.content[0].text.value
                                # Remove file citation references from the response
                                import re
                                content = re.sub(r'【\d+:\d+†[^】]+】', '', content).strip()
                            else:
                                print(f"[ASSISTANT] Unexpected content type: {type(msg.content[0])}")
                        
                        # Extract annotations for internal tracking only (not shown to users)
                        annotations = []
                        if msg.content and len(msg.content) > 0 and hasattr(msg.content[0], 'text') and hasattr(msg.content[0].text, 'annotations'):
                            # Convert annotations to serializable format for internal tracking
                            for ann in msg.content[0].text.annotations:
                                if hasattr(ann, 'file_citation'):
                                    annotations.append({
                                        "type": "file_citation",
                                        "file_id": ann.file_citation.file_id if hasattr(ann.file_citation, 'file_id') else None,
                                        "quote": ann.file_citation.quote if hasattr(ann.file_citation, 'quote') else None
                                    })
                        
                        print(f"[ASSISTANT] Response content: {content[:200]}...")
                        print(f"[ASSISTANT] Response received with {len(annotations)} annotations (internal tracking only)")
                        
                        # Track usage
                        estimated_tokens = self._estimate_tokens(user_message + content)
                        self.usage_tracker.track_assistant_usage(
                            thread_id=context.thread_id,
                            run_id=run.id,
                            tokens=estimated_tokens,
                            duration_ms=int((asyncio.get_event_loop().time() - start_time) * 1000)
                        )
                        
                        return {
                            "content": content,
                            "metadata": {
                                "method": "assistant_v2",
                                "thread_id": context.thread_id,
                                "run_id": run.id,
                                "annotations": annotations  # Keep for internal tracking but not exposed to users
                            },
                            "usage": {
                                "total_tokens": estimated_tokens,
                                "cost": 0.01  # Estimate
                            }
                        }
                
            else:
                print(f"[ASSISTANT] Run failed with status: {run.status}")
                logger.error(f"Assistant run failed: {run.status}")
                # Fallback to direct response
                return await self._generate_direct_response(context, user_message)
                
        except Exception as e:
            print(f"[ASSISTANT] Error: {str(e)}")
            logger.error(f"Error in assistant response: {str(e)}")
            # Fallback to direct response
            return await self._generate_direct_response(context, user_message)
    
    async def _generate_direct_response(self, context: ConversationContext, 
                                      user_message: str) -> Dict[str, Any]:
        """Generate response using direct ChatGPT API"""
        start_time = asyncio.get_event_loop().time()
        try:
            # Get document context
            doc_context = await self._get_document_context()
            
            # Prepare messages with document context
            messages = context.get_messages_for_api()
            
            # If we have documents, add them to the system message
            if doc_context:
                system_msg = next((m for m in messages if m["role"] == "system"), None)
                if system_msg:
                    system_msg["content"] += f"\n\nAvailable Documents:\n{doc_context}\n\nUse the information from these documents to answer questions."
            
            print(f"[CHAT] Sending message with {len(messages)} messages in context")
            if doc_context:
                print(f"[CHAT] Including document context ({len(doc_context)} chars)")
            
            # Call OpenAI API
            response = await self.openai_client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=self.temperature,
                max_tokens=self.max_tokens
            )
            
            # Extract response
            content = response.choices[0].message.content
            usage = response.usage
            
            # Calculate cost
            cost = calculate_cost(usage, self.model)
            
            # Track usage
            self.usage_tracker.track_openai_completion(
                model=self.model,
                usage_data={
                    "prompt_tokens": usage.prompt_tokens,
                    "completion_tokens": usage.completion_tokens,
                    "total_tokens": usage.total_tokens
                },
                operation="chat",
                related_id=context.db_session_id,
                duration_ms=int((asyncio.get_event_loop().time() - start_time) * 1000)
            )
            
            return {
                "content": content,
                "metadata": {
                    "method": "direct",
                    "model": self.model,
                    "finish_reason": response.choices[0].finish_reason
                },
                "usage": {
                    "prompt_tokens": usage.prompt_tokens,
                    "completion_tokens": usage.completion_tokens,
                    "total_tokens": usage.total_tokens,
                    "cost": cost
                }
            }
            
        except Exception as e:
            logger.error(f"Error in direct response generation: {str(e)}")
            raise
    
    async def get_conversation_history(self, session_id: str, 
                                     include_metadata: bool = False) -> List[Dict[str, Any]]:
        """Get conversation history for a session"""
        if session_id not in self.conversations:
            return []
        
        context = self.conversations[session_id]
        history = []
        
        for msg in context.messages:
            msg_dict = {
                "role": msg.role,
                "content": msg.content,
                "timestamp": msg.timestamp.isoformat()
            }
            
            if include_metadata and msg.metadata:
                # Filter out file reference information from metadata
                clean_metadata = msg.metadata.copy()
                if "annotations" in clean_metadata:
                    clean_metadata.pop("annotations", None)
                msg_dict["metadata"] = clean_metadata
            
            history.append(msg_dict)
        
        return history
    
    async def clear_conversation(self, session_id: str):
        """Clear conversation history"""
        if session_id in self.conversations:
            del self.conversations[session_id]
            logger.info(f"Cleared conversation: {session_id}")
    
    async def export_conversation(self, session_id: str) -> Dict[str, Any]:
        """Export conversation data"""
        if session_id not in self.conversations:
            return {"error": "Conversation not found"}
        
        context = self.conversations[session_id]
        
        return {
            "session_id": session_id,
            "thread_id": context.thread_id,
            "messages": await self.get_conversation_history(session_id, include_metadata=True),
            "stats": {
                "total_messages": len(context.messages),
                "total_tokens": context.total_tokens,
                "total_cost": context.total_cost,
                "start_time": context.messages[0].timestamp.isoformat() if context.messages else None,
                "last_message_time": context.messages[-1].timestamp.isoformat() if context.messages else None
            }
        }
    
    def _extract_citations(self, annotations: List[Any]) -> List[Dict[str, Any]]:
        """Extract citation information from annotations"""
        citations = []
        
        for annotation in annotations:
            if hasattr(annotation, 'file_citation'):
                citations.append({
                    "type": "file",
                    "file_id": annotation.file_citation.file_id,
                    "quote": annotation.file_citation.quote if hasattr(annotation.file_citation, 'quote') else None
                })
        
        return citations
    
    def _estimate_tokens(self, text: str) -> int:
        """Estimate token count for text"""
        if self.encoder:
            try:
                return len(self.encoder.encode(text))
            except Exception:
                pass
        # Fallback estimation
        return len(text) // 4
    
    async def process_message(self, message: str, context_ids: List[str] = None, 
                            session_id: Optional[str] = None,
                            user_id: Optional[str] = None,
                            user_email: Optional[str] = None) -> Dict[str, Any]:
        """Process a chat message - wrapper for API compatibility"""
        # Generate session ID if not provided
        if not session_id:
            session_id = f"session_{datetime.now().timestamp()}"
        
        # Get or create conversation
        if session_id not in self.conversations:
            await self.start_conversation(session_id, user_id=user_id)
        
        # Check if assistant is initialized
        if not self.retrieval_client.assistant_id:
            print("[CHAT] Initializing assistant...")
            await self.retrieval_client.initialize_assistant()
        
        # Use Assistants API v2 with file search
        response_data = await self.send_message(session_id, message, 
                                               use_retrieval=True, 
                                               user_id=user_id,
                                               user_email=user_email)
        
        # Format response for API (without file references for users)
        return {
            "success": True,
            "response": response_data.get("response", response_data.get("content", "")),
            "session_id": session_id,
            "usage": response_data.get("usage", {})
        }
    
    async def generate_summary(self, session_id: str) -> Optional[str]:
        """Generate a summary of the conversation"""
        if session_id not in self.conversations:
            return None
        
        context = self.conversations[session_id]
        
        # Prepare conversation for summarization
        conversation_text = "\n".join([
            f"{msg.role}: {msg.content}" 
            for msg in context.messages 
            if msg.role != "system"
        ])
        
        # Limit length
        conversation_text = truncate_text(conversation_text, 2000)
        
        try:
            response = await self.openai_client.chat.completions.create(
                model="gpt-3.5-turbo",  # Use cheaper model for summaries
                messages=[
                    {"role": "system", "content": "Summarize the following conversation in 2-3 sentences."},
                    {"role": "user", "content": conversation_text}
                ],
                temperature=0.5,
                max_tokens=150
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            logger.error(f"Error generating summary: {str(e)}")
            return None
    
    async def _get_document_context(self) -> Optional[str]:
        """Get document content for context"""
        try:
            # Get document manager from retrieval client
            from .document_manager_supabase import DocumentManagerSupabase
            doc_manager = DocumentManagerSupabase(self.retrieval_client)
            # DocumentManagerSupabase doesn't need _ensure_registry_loaded()
            
            # Get all active documents
            docs = await doc_manager.list_documents()
            if not docs:
                return None
            
            # Build context from document information
            context_parts = []
            for doc in docs[:5]:  # Limit to 5 most recent documents
                # DocumentManagerSupabase returns documents with file_id and filename
                if doc.get("filename"):
                    context_parts.append(f"Document: {doc['filename']}\n")
            
            if context_parts:
                return "\n---\n".join(context_parts)
            return None
            
        except Exception as e:
            logger.error(f"Error getting document context: {str(e)}")
            return None
    
    async def health_check(self) -> Dict[str, Any]:
        """Check health of chat interface"""
        try:
            # Test OpenAI connection
            test_response = await self.openai_client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": "test"}],
                max_tokens=5
            )
            
            return {
                "healthy": True,
                "service": "chat_interface",
                "model": self.model,
                "active_sessions": len(self.conversations)
            }
        except Exception as e:
            return {
                "healthy": False,
                "service": "chat_interface",
                "error": str(e)
            }