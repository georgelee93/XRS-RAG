"""
Parallel Enhanced Chat Interface with Optimized Performance
Implements parallel processing for improved response times
"""

import logging
import asyncio
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime

from .chat_interface import ChatInterface, Message, ConversationContext
from .bigquery_ai_query import BigQueryAI
from .document_manager_supabase import DocumentManagerSupabase
from .document_filter import IntelligentDocumentFilter
from .session_manager import get_session_manager
from .monitoring import MonitoringSystem

logger = logging.getLogger(__name__)


class ParallelEnhancedChatInterface(ChatInterface):
    """Enhanced chat interface with parallel processing optimizations"""
    
    def __init__(self, retrieval_client, model="gpt-4-1106-preview", 
                 temperature=0.7, max_tokens=1000):
        """Initialize parallel enhanced chat interface"""
        super().__init__(retrieval_client, model, temperature, max_tokens)
        
        # Initialize BigQuery AI
        self.bigquery_ai = BigQueryAI()
        self.monitoring = MonitoringSystem()
        self.document_filter = IntelligentDocumentFilter()
        logger.info("Parallel enhanced chat interface initialized with intelligent filtering")
    
    async def process_message(self, 
                            message: str, 
                            context_ids=None,
                            session_id: Optional[str] = None,
                            user_id: Optional[str] = None,
                            user_email: Optional[str] = None) -> Dict[str, Any]:
        """Process message with parallel operations for optimal performance"""
        
        start_time = asyncio.get_event_loop().time()
        
        try:
            # Generate session ID if not provided
            if not session_id:
                session_id = f"session_{datetime.now().timestamp()}"
            
            # Execute parallel initialization tasks
            init_results = await self._parallel_initialization(
                session_id, message, user_id
            )
            
            # Route to appropriate handler based on query type
            if init_results['is_data_query'] and self.bigquery_ai.enabled:
                response = await self._process_bigquery_parallel(
                    message=message,
                    session_id=session_id,
                    session=init_results['session'],
                    schemas=init_results['schemas'],
                    user_id=user_id,
                    user_email=user_email
                )
            else:
                response = await self._process_rag_parallel(
                    message=message,
                    session_id=session_id,
                    session=init_results['session'],
                    documents=init_results['documents'],
                    user_id=user_id,
                    user_email=user_email
                )
            
            # Log performance metrics asynchronously
            elapsed_time = asyncio.get_event_loop().time() - start_time
            asyncio.create_task(self._log_performance_async(
                message, elapsed_time, response.get("metadata", {})
            ))
            
            return response
            
        except Exception as e:
            logger.error(f"Error in parallel process_message: {str(e)}")
            # Fall back to base implementation on error (only pass supported parameters)
            return await super().process_message(
                message, context_ids, session_id
            )
    
    async def _parallel_initialization(self, 
                                      session_id: str, 
                                      message: str,
                                      user_id: Optional[str]) -> Dict[str, Any]:
        """Execute initialization tasks in parallel"""
        
        logger.info(f"Starting parallel initialization for session {session_id}")
        
        # Define parallel tasks
        tasks = {
            'session': self._ensure_session(session_id, user_id),
            'assistant': self._ensure_assistant(),
            'is_data_query': self._check_data_query(message),
            'documents': self._get_documents_async(),
            'schemas': self._get_schemas_if_enabled()
        }
        
        # Execute all tasks in parallel
        results = await self._gather_named(tasks)
        
        logger.info(f"Parallel initialization completed in {asyncio.get_event_loop().time():.2f}s")
        return results
    
    async def _gather_named(self, tasks: Dict[str, Any]) -> Dict[str, Any]:
        """Execute named tasks in parallel and return results dict"""
        names = list(tasks.keys())
        coroutines = list(tasks.values())
        
        # Execute all coroutines in parallel
        results = await asyncio.gather(*coroutines, return_exceptions=True)
        
        # Map results back to names
        output = {}
        for name, result in zip(names, results):
            if isinstance(result, Exception):
                logger.warning(f"Task {name} failed: {result}")
                output[name] = None
            else:
                output[name] = result
        
        return output
    
    async def _ensure_session(self, session_id: str, user_id: Optional[str]) -> ConversationContext:
        """Ensure session exists or create new one"""
        if session_id not in self.conversations:
            return await self.start_conversation(session_id, user_id=user_id)
        return self.conversations[session_id]
    
    async def _ensure_assistant(self) -> bool:
        """Ensure assistant is initialized"""
        if not self.retrieval_client.assistant_id:
            logger.info("Initializing assistant...")
            await self.retrieval_client.initialize_assistant()
        return True
    
    async def _check_data_query(self, message: str) -> bool:
        """Check if message is a data query"""
        try:
            if self.bigquery_ai.enabled:
                return await self.bigquery_ai.is_data_query(message)
        except Exception as e:
            logger.warning(f"Error checking data query: {e}")
        return False
    
    async def _get_documents_async(self) -> List[Dict]:
        """Get all documents asynchronously"""
        try:
            doc_manager = DocumentManagerSupabase(self.retrieval_client)
            return await doc_manager.list_documents()
        except Exception as e:
            logger.warning(f"Error getting documents: {e}")
            return []
    
    async def _get_schemas_if_enabled(self) -> Optional[List[Dict]]:
        """Get BigQuery schemas if enabled"""
        try:
            if self.bigquery_ai.enabled and self.bigquery_ai.schema_manager:
                return await self.bigquery_ai.schema_manager.get_available_schemas(
                    self.bigquery_ai.dataset_id
                )
        except Exception as e:
            logger.warning(f"Error getting schemas: {e}")
        return None
    
    async def _process_bigquery_parallel(self,
                                        message: str,
                                        session_id: str,
                                        session: ConversationContext,
                                        schemas: Optional[List[Dict]],
                                        user_id: Optional[str],
                                        user_email: Optional[str]) -> Dict[str, Any]:
        """Process BigQuery with parallel optimizations"""
        
        logger.info(f"Processing BigQuery query with parallel optimization")
        
        try:
            # If schemas weren't pre-fetched, get them now
            if not schemas:
                schemas = await self.bigquery_ai.schema_manager.get_available_schemas(
                    self.bigquery_ai.dataset_id
                )
            
            # Generate SQL and prepare formatting context in parallel
            sql_task = self.bigquery_ai._generate_sql(message, schemas, "auto")
            
            # Wait for SQL generation
            sql_response = await sql_task
            
            if not sql_response.get("success"):
                raise Exception(f"SQL generation failed: {sql_response.get('error')}")
            
            generated_sql = sql_response["sql"]
            
            # Validate SQL
            if not self.bigquery_ai._validate_sql(generated_sql):
                raise Exception("Generated SQL contains forbidden operations")
            
            # Execute query and start preparing response format
            execution_task = self.bigquery_ai._execute_bigquery(generated_sql)
            
            # Wait for execution
            query_result = await execution_task
            
            if not query_result.get("success"):
                raise Exception(f"Query execution failed: {query_result.get('error')}")
            
            # Format response
            final_response = await self.bigquery_ai._format_response(
                message, 
                query_result["data"], 
                "auto"
            )
            
            # Log query asynchronously (don't wait)
            asyncio.create_task(self.bigquery_ai._log_query(
                user_query=message,
                generated_sql=generated_sql,
                rows_returned=len(query_result["data"]),
                success=True,
                execution_time_ms=query_result.get("execution_time_ms", 0)
            ))
            
            # Update conversation context
            user_msg = Message(role="user", content=message)
            session.add_message(user_msg)
            
            assistant_msg = Message(
                role="assistant",
                content=final_response,
                metadata={
                    "source": "bigquery",
                    "sql": generated_sql,
                    "rows": len(query_result["data"]),
                    "execution_time_ms": query_result.get("execution_time_ms", 0)
                }
            )
            session.add_message(assistant_msg)
            
            # Save to database asynchronously
            if session.db_session_id:
                asyncio.create_task(self._save_messages_async(
                    session.db_session_id, user_msg, assistant_msg
                ))
            
            return {
                "success": True,
                "response": final_response,
                "session_id": session_id,
                "metadata": {
                    "source": "bigquery",
                    "query_type": "data",
                    "rows": len(query_result["data"])
                }
            }
            
        except Exception as e:
            logger.error(f"BigQuery parallel processing failed: {str(e)}")
            # Fall back to document RAG
            return await self._process_rag_parallel(
                message, session_id, session, [], user_id, user_email
            )
    
    async def _process_rag_parallel(self,
                                   message: str,
                                   session_id: str,
                                   session: ConversationContext,
                                   documents: List[Dict],
                                   user_id: Optional[str],
                                   user_email: Optional[str]) -> Dict[str, Any]:
        """Process RAG with parallel optimizations"""
        
        logger.info(f"Processing RAG query with parallel optimization")
        
        try:
            # Start filtering documents and ensuring thread in parallel
            filter_task = self._filter_relevant_documents(message, documents)
            thread_task = self._ensure_thread(session)
            
            # Wait for both operations
            relevant_docs, thread_id = await asyncio.gather(
                filter_task,
                thread_task
            )
            
            # Use send_message from parent class which handles the assistant interaction
            response_data = await super().send_message(
                session_id, 
                message, 
                use_retrieval=True,
                user_id=user_id,
                user_email=user_email
            )
            
            return {
                "success": True,
                "response": response_data.get("response", ""),
                "session_id": session_id,
                "usage": response_data.get("usage", {}),
                "metadata": response_data.get("metadata", {})
            }
            
        except Exception as e:
            logger.error(f"RAG parallel processing failed: {str(e)}")
            raise
    
    async def _filter_relevant_documents(self, 
                                        message: str, 
                                        documents: List[Dict]) -> List[Dict]:
        """Filter documents for relevance using intelligent filtering"""
        try:
            # Use intelligent document filter
            relevant_docs = await self.document_filter.filter_relevant_documents(
                query=message,
                documents=documents,
                max_documents=10  # Limit to top 10 most relevant
            )
            
            # Only return documents with file_ids
            filtered = [doc for doc in relevant_docs if doc.get("file_id")]
            
            logger.info(f"Filtered {len(documents)} documents to {len(filtered)} relevant ones")
            return filtered
            
        except Exception as e:
            logger.warning(f"Intelligent filtering failed, using all documents: {e}")
            # Fallback to all documents with file_ids
            return [doc for doc in documents if doc.get("file_id")]
    
    async def _ensure_thread(self, session: ConversationContext) -> str:
        """Ensure thread exists for the session"""
        if not session.thread_id:
            thread = await self.retrieval_client.async_client.beta.threads.create()
            session.thread_id = thread.id
            logger.info(f"Created thread: {thread.id}")
        return session.thread_id
    
    async def _save_messages_async(self, 
                                  session_id: str,
                                  user_msg: Message,
                                  assistant_msg: Message):
        """Save messages to database asynchronously"""
        try:
            self.session_manager.add_message(
                session_id,
                role="user",
                content=user_msg.content
            )
            self.session_manager.add_message(
                session_id,
                role="assistant",
                content=assistant_msg.content,
                metadata=assistant_msg.metadata
            )
        except Exception as e:
            logger.warning(f"Failed to save messages async: {e}")
    
    async def _log_performance_async(self, 
                                    message: str,
                                    elapsed_time: float,
                                    metadata: Dict):
        """Log performance metrics asynchronously"""
        try:
            await self.monitoring.log_event("parallel_chat_performance", {
                "message_length": len(message),
                "elapsed_time_ms": elapsed_time * 1000,
                "source": metadata.get("source", "unknown"),
                "parallel_processing": True
            })
        except Exception as e:
            logger.warning(f"Failed to log performance: {e}")
    
    async def health_check(self) -> Dict[str, Any]:
        """Check health of parallel enhanced chat interface"""
        base_health = await super().health_check()
        
        # Add parallel processing status
        base_health["parallel_processing"] = {
            "enabled": True,
            "optimization_level": "full"
        }
        
        # Add BigQuery health check
        if self.bigquery_ai.enabled:
            base_health["bigquery"] = {
                "healthy": True,
                "enabled": True,
                "project_id": self.bigquery_ai.project_id
            }
        
        return base_health