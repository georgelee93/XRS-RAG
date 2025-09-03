"""
Streaming Chat Interface for faster response times
"""

import logging
from typing import AsyncGenerator, Dict, Any, Optional
import json
from datetime import datetime

from openai import AsyncOpenAI

from .retrieval_client import RetrievalAPIClient
from .utils import calculate_cost
from .session_manager import get_session_manager

logger = logging.getLogger(__name__)


class StreamingChatInterface:
    """Chat interface with streaming support for faster perceived response times"""
    
    def __init__(self, 
                 retrieval_client: RetrievalAPIClient,
                 model: str = "gpt-3.5-turbo-1106",  # Faster model
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
    
    async def stream_message(self, 
                            message: str,
                            session_id: Optional[str] = None,
                            user_id: Optional[str] = None) -> AsyncGenerator[str, None]:
        """Stream chat response for faster perceived response time"""
        try:
            # Get document context (simplified for speed)
            from .document_manager_supabase import DocumentManagerSupabase
            doc_manager = DocumentManagerSupabase(self.retrieval_client)
            
            documents = await doc_manager.list_documents()
            
            # Build minimal context for speed
            context_parts = []
            for doc in documents[:3]:  # Limit to top 3 documents for speed
                if doc.get('text_preview'):
                    context_parts.append(f"Document: {doc.get('filename', 'Unknown')}\n{doc['text_preview'][:500]}\n")
            
            document_context = "\n---\n".join(context_parts) if context_parts else ""
            
            # Build messages
            messages = [
                {"role": "system", "content": "You are 청암 챗봇, a helpful assistant. Answer concisely based on the provided documents."},
            ]
            
            if document_context:
                messages.append({
                    "role": "system", 
                    "content": f"Available Documents:\n{document_context}"
                })
            
            messages.append({"role": "user", "content": message})
            
            # Stream response
            stream = await self.openai_client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=self.temperature,
                max_tokens=self.max_tokens,
                stream=True
            )
            
            # Yield chunks as they arrive
            full_response = ""
            async for chunk in stream:
                if chunk.choices[0].delta.content:
                    content = chunk.choices[0].delta.content
                    full_response += content
                    # Send as Server-Sent Event format
                    yield f"data: {json.dumps({'type': 'content', 'content': content})}\n\n"
            
            # Send completion signal
            yield f"data: {json.dumps({'type': 'done', 'full_response': full_response})}\n\n"
            
        except Exception as e:
            logger.error(f"Error in streaming chat: {str(e)}")
            yield f"data: {json.dumps({'type': 'error', 'error': str(e)})}\n\n"