"""
Enhanced Chat Interface with BigQuery Support
Extends the base chat interface to handle data queries
"""

import logging
from typing import Dict, Any, Optional

from .chat_interface import ChatInterface
from .bigquery_ai_query import BigQueryAI

logger = logging.getLogger(__name__)


class EnhancedChatInterface(ChatInterface):
    """Enhanced chat with BigQuery support"""
    
    def __init__(self, retrieval_client, model="gpt-4-1106-preview", 
                 temperature=0.7, max_tokens=1000):
        """Initialize enhanced chat interface"""
        super().__init__(retrieval_client, model, temperature, max_tokens)
        
        # Initialize BigQuery AI
        self.bigquery_ai = BigQueryAI()
        logger.info("Enhanced chat interface initialized with BigQuery support")
    
    async def send_message(self, session_id: str, user_message: str, 
                          use_retrieval: bool = True,
                          user_id: Optional[str] = None,
                          user_email: Optional[str] = None) -> Dict[str, Any]:
        """Process user message with BigQuery support"""
        try:
            # Check if this is a data query
            is_data_query = await self.bigquery_ai.is_data_query(user_message)
            
            if is_data_query and self.bigquery_ai.enabled:
                logger.info(f"Detected data query: {user_message[:100]}...")
                
                # Process with BigQuery
                result = await self.bigquery_ai.process_query(user_message)
                
                if result.get("success"):
                    # Format response for chat interface
                    response_content = result.get("response", "")
                    metadata = result.get("metadata", {})
                    
                    # Add to conversation context
                    if session_id not in self.conversations:
                        await self.start_conversation(session_id, user_id=user_id)
                    
                    context = self.conversations[session_id]
                    
                    # Add user message
                    from .chat_interface import Message
                    user_msg = Message(role="user", content=user_message)
                    context.add_message(user_msg)
                    
                    # Add assistant response
                    assistant_msg = Message(
                        role="assistant",
                        content=response_content,
                        metadata={
                            "source": "bigquery",
                            "sql": metadata.get("sql"),
                            "rows": metadata.get("rows"),
                            "execution_time_ms": metadata.get("execution_time_ms")
                        }
                    )
                    context.add_message(assistant_msg)
                    
                    # Save to database if available
                    if context.db_session_id:
                        try:
                            self.session_manager.add_message(
                                context.db_session_id,
                                role="user",
                                content=user_message
                            )
                            self.session_manager.add_message(
                                context.db_session_id,
                                role="assistant",
                                content=response_content,
                                metadata=assistant_msg.metadata
                            )
                        except Exception as e:
                            logger.warning(f"Failed to save BigQuery messages: {str(e)}")
                    
                    return {
                        "status": "success",
                        "response": response_content,
                        "metadata": {
                            "source": "bigquery",
                            "query_type": "data"
                        },
                        "session_id": session_id
                    }
                else:
                    # If BigQuery query failed, fall back to document RAG
                    logger.warning(f"BigQuery query failed: {result.get('error')}")
                    return await super().send_message(session_id, user_message, use_retrieval, user_id, user_email)
            else:
                # Process with document RAG as before
                return await super().send_message(session_id, user_message, use_retrieval, user_id, user_email)
                
        except Exception as e:
            logger.error(f"Error in enhanced send_message: {str(e)}")
            # Fall back to base implementation on error
            return await super().send_message(session_id, user_message, use_retrieval, user_id, user_email)
    
    async def process_message(self, message: str, context_ids=None, 
                            session_id: Optional[str] = None,
                            user_id: Optional[str] = None,
                            user_email: Optional[str] = None) -> Dict[str, Any]:
        """Process a chat message with BigQuery support"""
        # Generate session ID if not provided
        if not session_id:
            from datetime import datetime
            session_id = f"session_{datetime.now().timestamp()}"
        
        # Get or create conversation
        if session_id not in self.conversations:
            await self.start_conversation(session_id, user_id=user_id)
        
        # Check if assistant is initialized
        if not self.retrieval_client.assistant_id:
            logger.info("Initializing assistant...")
            await self.retrieval_client.initialize_assistant()
        
        # Use enhanced send_message which includes BigQuery support
        response_data = await self.send_message(session_id, message, use_retrieval=True, 
                                               user_id=user_id, user_email=user_email)
        
        # Format response for API
        return {
            "success": True,
            "response": response_data.get("response", response_data.get("content", "")),
            "session_id": session_id,
            "usage": response_data.get("usage", {}),
            "metadata": response_data.get("metadata", {})
        }
    
    async def health_check(self) -> Dict[str, Any]:
        """Check health of enhanced chat interface"""
        base_health = await super().health_check()
        
        # Add BigQuery health check
        bigquery_health = {
            "healthy": self.bigquery_ai.enabled,
            "enabled": self.bigquery_ai.enabled,
            "project_id": self.bigquery_ai.project_id if self.bigquery_ai.enabled else None,
            "dataset_id": self.bigquery_ai.dataset_id if self.bigquery_ai.enabled else None
        }
        
        return {
            **base_health,
            "bigquery": bigquery_health,
            "enhanced_features": ["bigquery_integration", "data_queries"]
        }