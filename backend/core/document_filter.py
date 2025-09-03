"""
Intelligent Document Filtering System
Provides relevance-based document filtering for improved query performance
"""

import logging
import asyncio
from typing import List, Dict, Any, Optional, Set
from datetime import datetime, timedelta
import re

from openai import AsyncOpenAI
from .utils import get_env_var

logger = logging.getLogger(__name__)


class IntelligentDocumentFilter:
    """Filter documents based on query relevance to reduce API payload"""
    
    def __init__(self):
        """Initialize the document filter"""
        self.openai = AsyncOpenAI(api_key=get_env_var("OPENAI_API_KEY"))
        self.cache = {}  # Simple in-memory cache for query analysis
        self.cache_ttl = 300  # 5 minutes
    
    async def filter_relevant_documents(self,
                                       query: str,
                                       documents: List[Dict],
                                       max_documents: int = 10) -> List[Dict]:
        """
        Filter documents based on relevance to the query
        
        Args:
            query: User's query string
            documents: List of all available documents
            max_documents: Maximum number of documents to return
            
        Returns:
            List of most relevant documents
        """
        
        if not documents:
            return []
        
        # Quick return if few documents
        if len(documents) <= max_documents:
            return documents
        
        try:
            # Analyze query in parallel with scoring
            query_analysis_task = self._analyze_query(query)
            
            # Start scoring documents immediately with basic keyword matching
            keyword_scores = self._quick_keyword_scoring(query, documents)
            
            # Wait for query analysis
            query_analysis = await query_analysis_task
            
            # Calculate comprehensive relevance scores in parallel
            scoring_tasks = [
                self._calculate_relevance_score(doc, query_analysis, keyword_scores.get(doc['id'], 0))
                for doc in documents
            ]
            
            scores = await asyncio.gather(*scoring_tasks)
            
            # Combine documents with scores
            scored_documents = [
                {**doc, 'relevance_score': score}
                for doc, score in zip(documents, scores)
            ]
            
            # Sort by relevance and return top N
            scored_documents.sort(key=lambda x: x['relevance_score'], reverse=True)
            
            # Log filtering results
            logger.info(f"Filtered {len(documents)} documents to {min(max_documents, len(scored_documents))} most relevant")
            
            return scored_documents[:max_documents]
            
        except Exception as e:
            logger.error(f"Error in intelligent filtering, returning all documents: {str(e)}")
            return documents[:max_documents]
    
    def _quick_keyword_scoring(self, query: str, documents: List[Dict]) -> Dict[str, float]:
        """Quick keyword-based scoring without API calls"""
        scores = {}
        query_words = set(query.lower().split())
        
        for doc in documents:
            score = 0.0
            
            # Check filename
            filename = doc.get('filename', '').lower()
            for word in query_words:
                if word in filename:
                    score += 0.3
            
            # Check metadata
            metadata = doc.get('metadata', {})
            
            # Check tags
            tags = metadata.get('tags', [])
            if isinstance(tags, list):
                tag_text = ' '.join(tags).lower()
                for word in query_words:
                    if word in tag_text:
                        score += 0.2
            
            # Check category
            category = metadata.get('category', '').lower()
            for word in query_words:
                if word in category:
                    score += 0.25
            
            # Check text preview
            preview = doc.get('text_preview', '').lower()[:500]
            for word in query_words:
                if word in preview:
                    score += 0.1
            
            scores[doc.get('id', doc.get('filename', ''))] = min(score, 1.0)
        
        return scores
    
    async def _analyze_query(self, query: str) -> Dict[str, Any]:
        """Analyze query to understand intent and extract key information"""
        
        # Check cache first
        cache_key = f"query_analysis:{query[:100]}"
        if cache_key in self.cache:
            cached_result, timestamp = self.cache[cache_key]
            if datetime.now() - timestamp < timedelta(seconds=self.cache_ttl):
                logger.debug("Using cached query analysis")
                return cached_result
        
        try:
            prompt = f"""Analyze this query and extract key information for document filtering.
            
Query: {query}

Return a JSON object with:
- main_topic: The primary subject/topic
- keywords: List of 3-5 important keywords
- document_types: Likely document types (e.g., policy, report, manual, form)
- time_context: If any time period is mentioned (recent, 2024, last month, etc.)
- department: If any department/team is mentioned
- intent: What the user wants (find, explain, compare, etc.)
"""
            
            response = await self.openai.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are a query analysis expert. Always return valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                response_format={"type": "json_object"},
                temperature=0,
                max_tokens=200
            )
            
            import json
            result = json.loads(response.choices[0].message.content)
            
            # Cache the result
            self.cache[cache_key] = (result, datetime.now())
            
            return result
            
        except Exception as e:
            logger.warning(f"Query analysis failed, using fallback: {str(e)}")
            # Fallback to basic keyword extraction
            words = query.lower().split()
            return {
                "main_topic": words[0] if words else "",
                "keywords": words[:5],
                "document_types": [],
                "time_context": None,
                "department": None,
                "intent": "find"
            }
    
    async def _calculate_relevance_score(self,
                                        document: Dict,
                                        query_analysis: Dict,
                                        keyword_score: float) -> float:
        """Calculate comprehensive relevance score for a document"""
        
        score = keyword_score * 0.3  # Start with keyword score (30% weight)
        
        metadata = document.get('metadata', {})
        
        # Category matching (20% weight)
        doc_category = metadata.get('category', '').lower()
        if doc_category:
            query_keywords = [kw.lower() for kw in query_analysis.get('keywords', [])]
            if any(keyword in doc_category for keyword in query_keywords):
                score += 0.2
            
            main_topic = query_analysis.get('main_topic', '').lower()
            if main_topic and main_topic in doc_category:
                score += 0.15
        
        # Document type matching (15% weight)
        doc_type = metadata.get('document_type', '').lower()
        query_types = [dt.lower() for dt in query_analysis.get('document_types', [])]
        if doc_type and doc_type in query_types:
            score += 0.15
        
        # Department matching (10% weight)
        doc_dept = metadata.get('department', '').lower()
        query_dept = (query_analysis.get('department', '') or '').lower()
        if doc_dept and query_dept and doc_dept == query_dept:
            score += 0.1
        
        # Time relevance (10% weight)
        time_context = query_analysis.get('time_context', '')
        if time_context:
            if 'recent' in time_context.lower() or 'latest' in time_context.lower():
                # Boost recent documents
                uploaded_at = metadata.get('uploaded_at')
                if uploaded_at:
                    try:
                        upload_date = datetime.fromisoformat(uploaded_at.replace('Z', '+00:00'))
                        days_old = (datetime.now(upload_date.tzinfo) - upload_date).days
                        if days_old < 30:
                            score += 0.1
                        elif days_old < 90:
                            score += 0.05
                    except:
                        pass
        
        # Filename relevance (15% weight)
        filename = document.get('filename', '').lower()
        query_keywords = query_analysis.get('keywords', [])
        filename_matches = sum(1 for kw in query_keywords if kw.lower() in filename)
        if filename_matches > 0:
            score += min(0.15, filename_matches * 0.05)
        
        return min(score, 1.0)  # Cap at 1.0
    
    async def get_file_ids_for_query(self, 
                                    query: str, 
                                    documents: List[Dict],
                                    max_documents: int = 10) -> List[str]:
        """
        Convenience method to get just the file IDs for relevant documents
        
        Args:
            query: User's query
            documents: All available documents
            max_documents: Maximum number of documents to include
            
        Returns:
            List of file IDs for most relevant documents
        """
        
        relevant_docs = await self.filter_relevant_documents(
            query, 
            documents, 
            max_documents
        )
        
        return [
            doc.get('file_id') 
            for doc in relevant_docs 
            if doc.get('file_id')
        ]
    
    def clear_cache(self):
        """Clear the query analysis cache"""
        self.cache.clear()
        logger.info("Document filter cache cleared")