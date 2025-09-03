"""
Unified Chat Service
Consolidates all chat functionality into a single service with strategy pattern
"""

import asyncio
import logging
from typing import Dict, Any, Optional, Protocol
from abc import ABC, abstractmethod
from datetime import datetime
from openai import OpenAI

from core.config import get_settings
from core.session_manager import get_session_manager
from core.retrieval_client import RetrievalAPIClient
from core.services.document_service import get_document_service

logger = logging.getLogger(__name__)


class ChatStrategy(ABC):
    """Abstract base class for chat strategies"""
    
    @abstractmethod
    async def process_message(
        self,
        message: str,
        session_id: Optional[str] = None,
        user_id: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Process a chat message and return response"""
        pass


class ThreadBasedChatStrategy(ChatStrategy):
    """Chat strategy using OpenAI Assistant API with threads"""
    
    def __init__(self, retrieval_client: RetrievalAPIClient):
        self.retrieval_client = retrieval_client
        self.session_manager = get_session_manager()
        
    async def process_message(
        self,
        message: str,
        session_id: Optional[str] = None,
        user_id: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Process message using Assistant API with threads"""
        try:
            # Get or create session
            if not session_id:
                session = self.session_manager.create_session(
                    user_id=user_id,
                    title=message[:50] + "..." if len(message) > 50 else message
                )
                session_id = session["session_id"]
            else:
                session = self.session_manager.get_session(session_id)
                if not session:
                    session = self.session_manager.create_session(
                        user_id=user_id,
                        title=message[:50] + "..." if len(message) > 50 else message
                    )
                    session_id = session["session_id"]
            
            # Get thread ID from session
            thread_id = session.get("thread_id")
            
            # Process with retrieval client
            response = await self.retrieval_client.process_with_thread(
                message=message,
                thread_id=thread_id
            )
            
            # Save message to session
            self.session_manager.add_message(
                session_id=session_id,
                role="user",
                content=message
            )
            
            self.session_manager.add_message(
                session_id=session_id,
                role="assistant",
                content=response.get("response", "")
            )
            
            # Update session with thread ID if new
            if not thread_id and response.get("thread_id"):
                self.session_manager.update_session(
                    session_id,
                    {"thread_id": response["thread_id"]}
                )
            
            return {
                "response": response.get("response", ""),
                "session_id": session_id,
                "thread_id": response.get("thread_id"),
                "usage": response.get("usage", {}),
                "metadata": response.get("metadata", {})
            }
            
        except Exception as e:
            logger.error(f"Error in thread-based chat: {str(e)}")
            raise


class DirectChatStrategy(ChatStrategy):
    """Chat strategy using direct OpenAI API without threads"""
    
    def __init__(self, model: str = "gpt-4-turbo-preview"):
        self.model = model
        self.session_manager = get_session_manager()
        
    async def process_message(
        self,
        message: str,
        session_id: Optional[str] = None,
        user_id: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Process message using direct OpenAI API"""
        try:
            import openai
            from ..config import get_settings
            
            settings = get_settings()
            client = openai.AsyncOpenAI(api_key=settings.openai_api_key)
            
            # Get or create session
            if not session_id:
                session = self.session_manager.create_session(
                    user_id=user_id,
                    title=message[:50] + "..." if len(message) > 50 else message
                )
                session_id = session["session_id"]
            
            # Get conversation history
            messages = self.session_manager.get_messages(session_id, limit=10)
            
            # Build messages for API
            api_messages = [
                {"role": "system", "content": "You are a helpful AI assistant."}
            ]
            
            for msg in messages:
                api_messages.append({
                    "role": msg["role"],
                    "content": msg["content"]
                })
            
            api_messages.append({"role": "user", "content": message})
            
            # Call OpenAI API
            response = await client.chat.completions.create(
                model=self.model,
                messages=api_messages,
                temperature=0.7,
                max_tokens=800
            )
            
            assistant_response = response.choices[0].message.content
            
            # Save messages
            self.session_manager.add_message(
                session_id=session_id,
                role="user",
                content=message
            )
            
            self.session_manager.add_message(
                session_id=session_id,
                role="assistant",
                content=assistant_response,
                tokens_used=response.usage.total_tokens if response.usage else 0
            )
            
            return {
                "response": assistant_response,
                "session_id": session_id,
                "usage": {
                    "total_tokens": response.usage.total_tokens if response.usage else 0,
                    "prompt_tokens": response.usage.prompt_tokens if response.usage else 0,
                    "completion_tokens": response.usage.completion_tokens if response.usage else 0,
                }
            }
            
        except Exception as e:
            logger.error(f"Error in direct chat: {str(e)}")
            raise


class UnifiedChatService:
    """
    Unified chat service that consolidates all chat functionality
    Uses strategy pattern to support different chat modes
    """
    
    def __init__(self):
        self.settings = get_settings()
        self.strategies: Dict[str, ChatStrategy] = {}
        self._initialized = False
        
    async def initialize(self):
        """Initialize the chat service and strategies"""
        if self._initialized:
            return
            
        try:
            # Initialize retrieval client for thread-based strategy
            retrieval_client = RetrievalAPIClient()
            await retrieval_client.initialize_assistant()
            
            # Register strategies
            self.strategies["thread"] = ThreadBasedChatStrategy(retrieval_client)
            self.strategies["direct"] = DirectChatStrategy(self.settings.chat_model)
            
            # Set default strategy based on settings
            self.default_strategy = "thread" if self.settings.use_threads else "direct"
            
            self._initialized = True
            logger.info(f"Chat service initialized with default strategy: {self.default_strategy}")
            
        except Exception as e:
            logger.error(f"Failed to initialize chat service: {str(e)}")
            raise
    
    async def process_message(
        self,
        message: str,
        session_id: Optional[str] = None,
        user_id: Optional[str] = None,
        strategy: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Process a chat message using the specified or default strategy
        
        Args:
            message: The user's message
            session_id: Optional session ID for conversation continuity
            user_id: User ID for session association
            strategy: Optional strategy name ("thread" or "direct")
            **kwargs: Additional arguments passed to the strategy
            
        Returns:
            Response dictionary with message, session_id, and metadata
        """
        if not self._initialized:
            await self.initialize()
        
        # Select strategy
        strategy_name = strategy or self.default_strategy
        
        if strategy_name not in self.strategies:
            raise ValueError(f"Unknown chat strategy: {strategy_name}")
        
        chat_strategy = self.strategies[strategy_name]
        
        # Process message
        start_time = asyncio.get_event_loop().time()
        
        try:
            response = await chat_strategy.process_message(
                message=message,
                session_id=session_id,
                user_id=user_id,
                **kwargs
            )
            
            # Add timing metadata
            response["metadata"] = response.get("metadata", {})
            response["metadata"]["processing_time"] = asyncio.get_event_loop().time() - start_time
            response["metadata"]["strategy"] = strategy_name
            
            logger.info(
                f"Message processed successfully using {strategy_name} strategy "
                f"in {response['metadata']['processing_time']:.2f}s"
            )
            
            return response
            
        except Exception as e:
            logger.error(f"Error processing message with {strategy_name} strategy: {str(e)}")
            raise
    
    def get_available_strategies(self) -> list:
        """Get list of available chat strategies"""
        return list(self.strategies.keys())
    
    def set_default_strategy(self, strategy: str):
        """Set the default chat strategy"""
        if strategy not in self.strategies:
            raise ValueError(f"Unknown strategy: {strategy}")
        self.default_strategy = strategy
        logger.info(f"Default chat strategy set to: {strategy}")


# Singleton instance
_chat_service_instance: Optional[UnifiedChatService] = None


def get_chat_service() -> UnifiedChatService:
    """Get or create the singleton chat service instance"""
    global _chat_service_instance
    if _chat_service_instance is None:
        _chat_service_instance = UnifiedChatService()
    return _chat_service_instance