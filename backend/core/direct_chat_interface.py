"""
Direct Chat Interface without Threads
Uses Chat Completion API directly with file content
"""

import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
import asyncio

from openai import AsyncOpenAI

from .retrieval_client import RetrievalAPIClient
from .utils import calculate_cost
from .session_manager import get_session_manager

logger = logging.getLogger(__name__)


class DirectChatInterface:
    """Chat interface that doesn't use Assistants API or Threads"""
    
    def __init__(self, 
                 retrieval_client: RetrievalAPIClient,
                 model: str = "gpt-4-turbo-preview",
                 temperature: float = 0.7,
                 max_tokens: int = 1000):
        
        self.retrieval_client = retrieval_client
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        
        # Initialize OpenAI client
        self.openai_client = AsyncOpenAI(
            api_key=retrieval_client.api_key
        )
        
        self.session_manager = get_session_manager()
        
    async def search_documents(self, query: str) -> str:
        """Search documents in vector store and return relevant content"""
        try:
            # Get all document content from database
            from .document_manager_supabase import DocumentManagerSupabase
            doc_manager = DocumentManagerSupabase(self.retrieval_client)
            
            documents = await doc_manager.list_documents()
            
            # Also get files from vector store
            vector_store_files = []
            try:
                if self.retrieval_client.vector_store_id:
                    files = await self.retrieval_client.list_vector_store_files(
                        self.retrieval_client.vector_store_id
                    )
                    if files:
                        vector_store_files = files
                        print(f"[DIRECT CHAT] Found {len(vector_store_files)} files in vector store")
            except Exception as vs_error:
                logger.warning(f"Could not fetch vector store files: {vs_error}")
            
            # Build context from documents
            context_parts = []
            
            # Add database documents with previews
            for doc in documents:
                if doc.get('text_preview'):
                    context_parts.append(f"Document: {doc.get('filename', 'Unknown')}\nContent: {doc['text_preview'][:2000]}\n")
            
            # Add vector store files (list only, no content)
            if vector_store_files:
                file_list = []
                for file in vector_store_files:
                    filename = getattr(file, 'filename', None) or getattr(file, 'id', 'Unknown')
                    file_list.append(filename)
                
                if file_list:
                    context_parts.append(f"Additional files in vector store: {', '.join(file_list)}")
            
            # Special handling for "사용 가능한 문서" queries
            if "사용 가능한 문서" in query or "available documents" in query.lower():
                all_files = []
                
                # Add database files
                for doc in documents:
                    all_files.append(doc.get('filename', 'Unknown'))
                
                # Add vector store files
                for file in vector_store_files:
                    filename = getattr(file, 'filename', None) or getattr(file, 'id', 'Unknown')
                    if filename not in all_files:
                        all_files.append(filename)
                
                if all_files:
                    return f"사용 가능한 문서 목록:\n" + "\n".join([f"- {f}" for f in all_files])
                else:
                    return "현재 업로드된 문서가 없습니다."
            
            if context_parts:
                return "\n---\n".join(context_parts)
            else:
                return ""
                
        except Exception as e:
            logger.error(f"Error searching documents: {str(e)}")
            return ""
    
    async def process_message(self, 
                             message: str,
                             session_id: Optional[str] = None,
                             user_id: Optional[str] = None) -> Dict[str, Any]:
        """Process a message without using threads"""
        try:
            print(f"[DIRECT CHAT] Processing message without threads")
            
            # Get document context
            document_context = await self.search_documents(message)
            
            # Build system prompt
            system_prompt = """You are 청암 챗봇, a helpful assistant that answers questions based on the provided documents.

IMPORTANT: You have been provided with document content below. Use this information to answer questions.

Key behaviors:
1. Answer based on the document content provided
2. If information is not found in the provided context, clearly state "업로드된 문서에서 해당 정보를 찾을 수 없습니다"
3. Cite the document name when providing information
4. Be concise and accurate

Respond in the same language as the user's question (Korean or English)."""

            # Build messages
            messages = [
                {"role": "system", "content": system_prompt}
            ]
            
            # Add document context if available
            if document_context:
                messages.append({
                    "role": "system", 
                    "content": f"Available Documents:\n{document_context}"
                })
            
            # Add user message
            messages.append({"role": "user", "content": message})
            
            # Get conversation history from session if available
            if session_id and self.session_manager:
                try:
                    session = self.session_manager.get_session(session_id)
                    if session and session.get('messages'):
                        # Add recent history (last 5 exchanges)
                        history = session['messages'][-10:]  # Last 5 Q&A pairs
                        for hist_msg in history:
                            if hist_msg.get('role') in ['user', 'assistant']:
                                messages.insert(-1, {
                                    "role": hist_msg['role'],
                                    "content": hist_msg['content']
                                })
                except Exception as e:
                    # Session doesn't exist yet, that's ok
                    logger.debug(f"Session not found (will be created): {session_id}")
            
            # Call OpenAI Chat Completion API
            print(f"[DIRECT CHAT] Calling OpenAI Chat Completion API")
            response = await self.openai_client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=self.temperature,
                max_tokens=self.max_tokens
            )
            
            # Extract response
            assistant_message = response.choices[0].message.content
            
            # Calculate usage
            usage = {
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
                "total_tokens": response.usage.total_tokens,
                "cost": calculate_cost(response.usage, self.model)
            }
            
            # Update session if available - but don't let it break the chat
            if session_id and self.session_manager:
                try:
                    # Check if session exists
                    session = None
                    try:
                        session = self.session_manager.get_session(session_id)
                    except:
                        pass
                    
                    if not session:
                        # Create new session with the given session_id
                        try:
                            from .supabase_client import get_supabase_manager
                            supabase = get_supabase_manager()
                            
                            session_data = {
                                "session_id": session_id,
                                "user_id": user_id,
                                "thread_id": None,  # No thread in direct mode
                                "session_title": "Direct Chat",
                                "metadata": {
                                    "mode": "direct_chat",
                                    "created_from": "web_app"
                                }
                            }
                            
                            result = supabase.client.table("chat_sessions").insert(session_data).execute()
                            print(f"[DIRECT CHAT] Created new session: {session_id}")
                        except Exception as e:
                            logger.warning(f"Could not create session: {e}")
                    
                    # Try to add messages to history
                    try:
                        self.session_manager.add_message(
                            session_id, 
                            "user", 
                            message
                        )
                        self.session_manager.add_message(
                            session_id, 
                            "assistant", 
                            assistant_message
                        )
                    except Exception as e:
                        # Log but don't fail
                        logger.debug(f"Could not save messages to session (non-critical): {e}")
                        
                except Exception as e:
                    # Session operations failed, but chat should continue
                    logger.debug(f"Session operations failed (non-critical): {e}")
            
            print(f"[DIRECT CHAT] Response generated successfully")
            
            return {
                "status": "success",
                "response": assistant_message,
                "usage": usage,
                "session_id": session_id,
                "mode": "direct_chat"  # Indicate this is thread-less mode
            }
            
        except Exception as e:
            logger.error(f"Error in direct chat: {str(e)}")
            return {
                "status": "error",
                "error": str(e),
                "session_id": session_id
            }
    
    async def list_documents(self) -> List[str]:
        """List available documents"""
        try:
            from .document_manager_supabase import DocumentManagerSupabase
            doc_manager = DocumentManagerSupabase(self.retrieval_client)
            
            documents = await doc_manager.list_documents()
            return [doc.get('filename', 'Unknown') for doc in documents]
            
        except Exception as e:
            logger.error(f"Error listing documents: {str(e)}")
            return []