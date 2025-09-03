"""
Hybrid Retrieval Engine
Combines OpenAI Retrieval API with BigQuery for comprehensive responses
"""

import logging
import json
from typing import Dict, Any, Optional, List
from datetime import datetime
import asyncio

from .retrieval_client import RetrievalAPIClient
from .bigquery_integration import BigQueryRAGIntegration
from .chat_interface import ChatInterface
from .utils import truncate_text, create_error_response


logger = logging.getLogger(__name__)


class HybridRAGEngine:
    """Main engine that orchestrates retrieval from multiple sources"""
    
    def __init__(self, 
                 retrieval_client: RetrievalAPIClient,
                 bigquery_client: Optional[BigQueryRAGIntegration] = None,
                 chat_client: Optional[ChatInterface] = None):
        
        self.retrieval_client = retrieval_client
        self.bigquery_client = bigquery_client
        self.chat_client = chat_client
        
        # Track performance metrics
        self.metrics = {
            "queries_processed": 0,
            "retrieval_hits": 0,
            "bigquery_hits": 0,
            "hybrid_responses": 0,
            "errors": 0
        }
    
    async def process_query(self, user_question: str, 
                          session_id: Optional[str] = None,
                          use_live_data: bool = True) -> Dict[str, Any]:
        """
        Process user query using both document retrieval and live data
        """
        self.metrics["queries_processed"] += 1
        
        try:
            # Start tasks concurrently
            tasks = []
            
            # Task 1: Document retrieval
            doc_task = asyncio.create_task(
                self._get_document_context(user_question)
            )
            tasks.append(("documents", doc_task))
            
            # Task 2: Live data retrieval (if enabled)
            if use_live_data and self.bigquery_client and self.bigquery_client.enabled:
                bq_task = asyncio.create_task(
                    asyncio.to_thread(
                        self.bigquery_client.get_live_context, 
                        user_question
                    )
                )
                tasks.append(("bigquery", bq_task))
            
            # Wait for all tasks to complete
            results = {}
            for name, task in tasks:
                try:
                    results[name] = await task
                except Exception as e:
                    logger.error(f"Error in {name} task: {str(e)}")
                    results[name] = None
            
            # Combine contexts
            combined_context = self._combine_contexts(
                results.get("documents"),
                results.get("bigquery")
            )
            
            # Generate response
            if self.chat_client and session_id:
                # Use existing chat session
                response = await self._generate_chat_response(
                    session_id, user_question, combined_context
                )
            else:
                # Use retrieval API directly
                response = await self._generate_retrieval_response(
                    user_question, combined_context
                )
            
            # Update metrics
            if results.get("documents"):
                self.metrics["retrieval_hits"] += 1
            if results.get("bigquery") and results["bigquery"].get("has_data"):
                self.metrics["bigquery_hits"] += 1
            if results.get("documents") and results.get("bigquery"):
                self.metrics["hybrid_responses"] += 1
            
            return response
            
        except Exception as e:
            self.metrics["errors"] += 1
            logger.error(f"Error processing query: {str(e)}")
            return create_error_response(e, {"query": user_question})
    
    async def _get_document_context(self, user_question: str) -> Dict[str, Any]:
        """Get relevant document context using Retrieval API"""
        try:
            result = await self.retrieval_client.search(user_question)
            
            if result["status"] == "success" and result["response"]:
                return {
                    "has_content": True,
                    "content": result["response"],
                    "thread_id": result.get("thread_id"),
                    "annotations": result.get("annotations", [])
                }
            else:
                return {
                    "has_content": False,
                    "error": result.get("error")
                }
                
        except Exception as e:
            logger.error(f"Document retrieval error: {str(e)}")
            return {
                "has_content": False,
                "error": str(e)
            }
    
    def _combine_contexts(self, doc_context: Optional[Dict[str, Any]], 
                         live_context: Optional[Dict[str, Any]]) -> str:
        """Combine document and live data contexts"""
        combined = []
        
        # Add document context
        if doc_context and doc_context.get("has_content"):
            combined.append("REFERENCE DOCUMENTS:")
            combined.append(doc_context["content"])
            combined.append("")
        
        # Add live data context
        if live_context and live_context.get("has_data"):
            combined.append(f"LIVE DATA ({live_context['query_type']}):")
            combined.append(f"Summary: {live_context['summary']}")
            
            # Include sample of data
            if live_context.get("data"):
                data_preview = live_context["data"][:5]  # First 5 records
                combined.append("Sample Data:")
                combined.append(json.dumps(data_preview, indent=2, default=str))
            
            combined.append(f"Total Records: {live_context['row_count']}")
            combined.append("")
        
        return "\n".join(combined)
    
    async def _generate_chat_response(self, session_id: str, 
                                    user_question: str, 
                                    context: str) -> Dict[str, Any]:
        """Generate response using chat interface"""
        # Prepare enhanced prompt with context
        enhanced_prompt = f"""Based on the following context, please answer the user's question.

{context}

User Question: {user_question}

Please provide a comprehensive answer that combines information from both the reference documents and live data (if available)."""
        
        # Send to chat interface
        response = await self.chat_client.send_message(
            session_id, 
            enhanced_prompt,
            use_retrieval=False  # We already have context
        )
        
        return response
    
    async def _generate_retrieval_response(self, user_question: str, 
                                         context: str) -> Dict[str, Any]:
        """Generate response using retrieval API directly"""
        # Create a new thread for this query
        thread = await self.retrieval_client.create_thread()
        
        # Add context as system message
        await self.retrieval_client.add_message(
            thread.id,
            f"Context:\n{context}",
            role="assistant"
        )
        
        # Add user question
        await self.retrieval_client.add_message(
            thread.id,
            user_question,
            role="user"
        )
        
        # Run assistant
        run = await self.retrieval_client.run_assistant(thread.id)
        
        # Wait for completion
        await self.retrieval_client.wait_for_run_completion(thread.id, run.id)
        
        # Get response
        messages = await self.retrieval_client.get_messages(thread.id)
        
        if messages:
            assistant_message = messages[0]  # Most recent message
            return {
                "status": "success",
                "response": assistant_message.content[0].text.value,
                "thread_id": thread.id,
                "context_used": {
                    "documents": bool(context and "REFERENCE DOCUMENTS:" in context),
                    "live_data": bool(context and "LIVE DATA" in context)
                }
            }
        else:
            return {
                "status": "error",
                "error": "No response generated"
            }
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get performance metrics"""
        return {
            "metrics": self.metrics,
            "timestamp": datetime.now().isoformat()
        }
    
    async def health_check(self) -> Dict[str, Any]:
        """Check health of all components"""
        health = {
            "status": "healthy",
            "components": {},
            "timestamp": datetime.now().isoformat()
        }
        
        # Check retrieval API
        try:
            files = await self.retrieval_client.list_files()
            health["components"]["retrieval_api"] = {
                "status": "healthy",
                "file_count": len(files)
            }
        except Exception as e:
            health["components"]["retrieval_api"] = {
                "status": "unhealthy",
                "error": str(e)
            }
            health["status"] = "degraded"
        
        # Check BigQuery
        if self.bigquery_client and self.bigquery_client.enabled:
            try:
                bq_healthy = self.bigquery_client.test_connection()
                health["components"]["bigquery"] = {
                    "status": "healthy" if bq_healthy else "unhealthy"
                }
            except Exception as e:
                health["components"]["bigquery"] = {
                    "status": "unhealthy",
                    "error": str(e)
                }
                health["status"] = "degraded"
        else:
            health["components"]["bigquery"] = {
                "status": "disabled"
            }
        
        return health


class QueryRouter:
    """Routes queries to appropriate handlers based on content"""
    
    def __init__(self):
        self.route_patterns = {
            "document_only": [
                "policy", "procedure", "guide", "manual", "documentation",
                "how to", "explain", "what is", "definition"
            ],
            "data_only": [
                "current", "latest", "now", "today", "real-time",
                "how many", "count", "total", "statistics"
            ],
            "hybrid": [
                "compare", "analyze", "trend", "historical vs current",
                "policy and current", "should be"
            ]
        }
    
    def determine_route(self, query: str) -> str:
        """Determine the best route for a query"""
        query_lower = query.lower()
        
        # Check for hybrid indicators
        for pattern in self.route_patterns["hybrid"]:
            if pattern in query_lower:
                return "hybrid"
        
        # Check for data-only indicators
        data_score = sum(1 for pattern in self.route_patterns["data_only"] 
                        if pattern in query_lower)
        
        # Check for document-only indicators
        doc_score = sum(1 for pattern in self.route_patterns["document_only"] 
                       if pattern in query_lower)
        
        # Determine route based on scores
        if data_score > doc_score:
            return "data_only"
        elif doc_score > data_score:
            return "document_only"
        else:
            return "hybrid"  # Default to hybrid for ambiguous queries
    
    async def health_check(self) -> Dict[str, Any]:
        """Check health of retrieval engine"""
        try:
            # Check component health
            retrieval_healthy = await self.retrieval_client.health_check() if hasattr(self.retrieval_client, "health_check") else True
            bigquery_healthy = self.bigquery_client.health_check() if self.bigquery_client and hasattr(self.bigquery_client, "health_check") else True
            chat_healthy = await self.chat_interface.health_check() if hasattr(self.chat_interface, "health_check") else True
            
            all_healthy = retrieval_healthy and bigquery_healthy and chat_healthy
            
            return {
                "healthy": all_healthy,
                "service": "retrieval_engine",
                "components": {
                    "retrieval_client": retrieval_healthy,
                    "bigquery": bigquery_healthy,
                    "chat_interface": chat_healthy
                }
            }
        except Exception as e:
            return {
                "healthy": False,
                "service": "retrieval_engine",
                "error": str(e)
            }
