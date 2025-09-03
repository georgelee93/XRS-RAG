"""
Query Classification System
Determines optimal routing path for user queries
"""

import re
import logging
from typing import Dict, Any, List, Optional, Tuple
from enum import Enum
import asyncio

from openai import AsyncOpenAI
from .utils import get_env_var

logger = logging.getLogger(__name__)


class QueryType(Enum):
    """Types of queries and their routing"""
    SIMPLE = "simple"           # Direct to ChatGPT (no documents needed)
    DOCUMENT = "document"        # Needs document retrieval
    DATA = "data"               # BigQuery data analysis
    HYBRID = "hybrid"           # Needs both documents and general knowledge


class QueryClassifier:
    """Intelligent query classification for optimal routing"""
    
    def __init__(self):
        """Initialize the query classifier"""
        self.openai = AsyncOpenAI(api_key=get_env_var("OPENAI_API_KEY"))
        self.classification_cache = {}
        self.cache_ttl = 3600  # 1 hour cache
        
        # Define patterns for different query types
        self._init_patterns()
    
    def _init_patterns(self):
        """Initialize classification patterns"""
        
        # Patterns that definitely DON'T need documents
        self.simple_patterns = [
            # Greetings and social
            (r'^(hi|hello|hey|good morning|good afternoon)', 1.0),
            (r'^(thanks|thank you|bye|goodbye)', 1.0),
            (r'^how are you', 1.0),
            
            # Math and calculations
            (r'\d+\s*[\+\-\*/]\s*\d+', 0.9),
            (r'^(calculate|compute|what is|solve)', 0.7),
            
            # General knowledge questions
            (r'^what is (the )?(weather|time|date)', 1.0),
            (r'^(who|what|when|where) (is|was|are|were) \w+$', 0.6),
            (r'^define \w+', 0.8),
            (r'^explain \w+ in simple terms', 0.7),
            
            # Translations and conversions
            (r'^translate .+ to \w+', 1.0),
            (r'^convert \d+ .+ to \w+', 0.9),
            
            # Programming help (unless asking about YOUR code)
            (r'^(write|create|generate) .+ (code|function|script)', 0.7),
            (r'^how (do I|to) .+ in (python|javascript|sql)', 0.8),
            
            # Creative tasks
            (r'^(write|compose|create) .+ (poem|story|song|email)', 1.0),
            (r'^suggest .+ (names|ideas|topics)', 0.9),
        ]
        
        # Patterns that definitely NEED documents
        self.document_patterns = [
            # Explicit document references
            (r'(policy|policies|procedure|handbook|manual|guide|document|report)', 0.9),
            (r'(form|template|checklist|protocol)', 0.8),
            
            # Company-specific terms (customize these!)
            (r'(청암|cheongam|our company|our organization)', 0.9),
            (r'(employee|staff|HR|human resources)', 0.8),
            (r'(vacation|leave|PTO|time off|benefits)', 0.85),
            (r'(expense|reimbursement|travel policy)', 0.9),
            
            # Document actions
            (r'(find|search|look up|locate|show me|where is)', 0.7),
            (r'(latest|recent|current|updated) .+ (report|document|policy)', 0.95),
            (r'according to (the|our)', 0.9),
            (r'(in|from) (the|our) .+ (document|policy|report)', 0.95),
            
            # Specific document types
            (r'(quarterly|annual|monthly) report', 0.95),
            (r'(training|onboarding) (material|document)', 0.9),
            (r'(contract|agreement|terms)', 0.85),
            
            # Process and procedure questions
            (r'how (do I|to) .+ (submit|request|apply|file)', 0.8),
            (r'(process|procedure|steps) (for|to)', 0.8),
            (r'(requirements|criteria|eligibility)', 0.75),
        ]
        
        # Keywords that suggest document need
        self.document_keywords = {
            # Strong indicators (0.8-1.0 confidence)
            'policy': 0.95,
            'procedure': 0.9,
            'handbook': 0.95,
            'manual': 0.9,
            'documentation': 0.95,
            'report': 0.85,
            'form': 0.8,
            'template': 0.8,
            'guideline': 0.85,
            'protocol': 0.85,
            
            # Medium indicators (0.5-0.8 confidence)
            'company': 0.7,
            'employee': 0.65,
            'internal': 0.75,
            'process': 0.6,
            'workflow': 0.7,
            'standard': 0.65,
            'compliance': 0.75,
            
            # Weak indicators (0.3-0.5 confidence)
            'how': 0.3,
            'what': 0.3,
            'where': 0.4,
            'find': 0.5,
            'show': 0.4,
        }
        
        # Phrases that negate document need
        self.negation_phrases = [
            'in general',
            'generally speaking',
            'typically',
            'usually',
            'in theory',
            'hypothetically',
            'what do you think',
            'your opinion',
        ]
    
    async def classify_query(self, 
                           query: str, 
                           conversation_context: Optional[List[Dict]] = None) -> Tuple[QueryType, float, Dict[str, Any]]:
        """
        Classify a query to determine the optimal processing path
        
        Args:
            query: The user's query
            conversation_context: Previous messages for context
            
        Returns:
            Tuple of (QueryType, confidence_score, metadata)
        """
        
        # Clean the query
        query_lower = query.lower().strip()
        
        # Step 1: Check cache
        cache_key = f"{query_lower[:100]}"
        if cache_key in self.classification_cache:
            cached_result, _ = self.classification_cache[cache_key]
            logger.debug(f"Using cached classification: {cached_result}")
            return cached_result
        
        # Step 2: Rule-based classification
        rule_result = self._apply_rules(query_lower)
        
        # Step 3: If confident in rules, return immediately
        if rule_result[1] >= 0.8:  # High confidence
            self.classification_cache[cache_key] = (rule_result, asyncio.get_event_loop().time())
            return rule_result
        
        # Step 4: For uncertain cases, use AI classification
        ai_result = await self._ai_classification(query, conversation_context)
        
        # Step 5: Combine rule and AI results
        final_result = self._combine_results(rule_result, ai_result)
        
        # Cache the result
        self.classification_cache[cache_key] = (final_result, asyncio.get_event_loop().time())
        
        return final_result
    
    def _apply_rules(self, query: str) -> Tuple[QueryType, float, Dict[str, Any]]:
        """Apply rule-based classification"""
        
        scores = {
            QueryType.SIMPLE: 0.5,    # Default baseline
            QueryType.DOCUMENT: 0.0,
        }
        
        metadata = {
            'matched_patterns': [],
            'keywords_found': []
        }
        
        # Check for negation phrases (reduces document need)
        for phrase in self.negation_phrases:
            if phrase in query:
                scores[QueryType.SIMPLE] += 0.2
                scores[QueryType.DOCUMENT] -= 0.2
        
        # Check simple patterns
        for pattern, confidence in self.simple_patterns:
            if re.search(pattern, query):
                scores[QueryType.SIMPLE] += confidence
                metadata['matched_patterns'].append(pattern)
        
        # Check document patterns
        for pattern, confidence in self.document_patterns:
            if re.search(pattern, query):
                scores[QueryType.DOCUMENT] += confidence
                metadata['matched_patterns'].append(pattern)
        
        # Check keywords
        words = query.split()
        for word in words:
            if word in self.document_keywords:
                keyword_conf = self.document_keywords[word]
                scores[QueryType.DOCUMENT] += keyword_conf
                metadata['keywords_found'].append(word)
        
        # Normalize scores
        total_score = sum(scores.values())
        if total_score > 0:
            for key in scores:
                scores[key] /= total_score
        
        # Determine winner
        if scores[QueryType.DOCUMENT] > 0.6:
            return (QueryType.DOCUMENT, scores[QueryType.DOCUMENT], metadata)
        else:
            return (QueryType.SIMPLE, scores[QueryType.SIMPLE], metadata)
    
    async def _ai_classification(self, 
                                query: str, 
                                context: Optional[List[Dict]] = None) -> Tuple[QueryType, float, Dict[str, Any]]:
        """Use AI for classification when rules are uncertain"""
        
        try:
            # Build context string
            context_str = ""
            if context:
                recent_context = context[-3:]  # Last 3 messages
                context_str = "\nRecent conversation:\n"
                for msg in recent_context:
                    context_str += f"{msg['role']}: {msg['content'][:100]}...\n"
            
            prompt = f"""Classify if this query needs to search through uploaded documents or can be answered with general knowledge.

Query: "{query}"
{context_str}

Consider:
1. Does it reference specific company documents, policies, or procedures?
2. Is it asking about information that would be in uploaded files?
3. Or is it a general question that can be answered without documents?

Respond with JSON:
{{
    "needs_documents": true/false,
    "confidence": 0.0-1.0,
    "reasoning": "brief explanation",
    "suggested_document_types": ["policy", "manual", etc] or []
}}"""

            response = await self.openai.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are a query classification expert."},
                    {"role": "user", "content": prompt}
                ],
                response_format={"type": "json_object"},
                temperature=0,
                max_tokens=150
            )
            
            import json
            result = json.loads(response.choices[0].message.content)
            
            query_type = QueryType.DOCUMENT if result["needs_documents"] else QueryType.SIMPLE
            confidence = result["confidence"]
            metadata = {
                "ai_reasoning": result["reasoning"],
                "suggested_types": result.get("suggested_document_types", [])
            }
            
            return (query_type, confidence, metadata)
            
        except Exception as e:
            logger.warning(f"AI classification failed: {e}")
            # Fallback to neutral
            return (QueryType.SIMPLE, 0.5, {"error": str(e)})
    
    def _combine_results(self, 
                        rule_result: Tuple[QueryType, float, Dict],
                        ai_result: Tuple[QueryType, float, Dict]) -> Tuple[QueryType, float, Dict]:
        """Combine rule-based and AI classification results"""
        
        # Weight the results (rules are faster and often sufficient)
        rule_weight = 0.6
        ai_weight = 0.4
        
        # If they agree, high confidence
        if rule_result[0] == ai_result[0]:
            combined_confidence = (rule_result[1] * rule_weight + ai_result[1] * ai_weight)
            return (rule_result[0], min(combined_confidence * 1.2, 1.0), {
                **rule_result[2],
                **ai_result[2],
                "classification_method": "combined_agreement"
            })
        
        # If they disagree, go with higher confidence
        if rule_result[1] > ai_result[1]:
            return (*rule_result[:2], {
                **rule_result[2],
                "classification_method": "rule_based",
                "ai_disagreed": True
            })
        else:
            return (*ai_result[:2], {
                **ai_result[2],
                "classification_method": "ai_based",
                "rule_disagreed": True
            })
    
    def get_document_filter_hints(self, query: str, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """
        Provide hints for document filtering based on classification
        
        Returns:
            Dictionary with filtering hints like categories, keywords, etc.
        """
        
        hints = {
            "categories": [],
            "keywords": metadata.get("keywords_found", []),
            "document_types": metadata.get("suggested_types", []),
            "priority": "normal"
        }
        
        # Map keywords to categories
        category_mapping = {
            "hr": ["employee", "vacation", "leave", "benefits", "handbook"],
            "finance": ["expense", "budget", "reimbursement", "invoice"],
            "technical": ["api", "code", "development", "technical"],
            "policy": ["policy", "procedure", "guideline", "protocol"],
        }
        
        query_lower = query.lower()
        for category, keywords in category_mapping.items():
            if any(keyword in query_lower for keyword in keywords):
                hints["categories"].append(category)
        
        # Set priority based on certain keywords
        if any(word in query_lower for word in ["urgent", "immediate", "asap", "emergency"]):
            hints["priority"] = "high"
        elif any(word in query_lower for word in ["latest", "recent", "current"]):
            hints["priority"] = "recent"
        
        return hints
    
    def clear_cache(self):
        """Clear the classification cache"""
        self.classification_cache.clear()
        logger.info("Query classification cache cleared")


# Example usage and testing
async def test_classifier():
    """Test the query classifier with various queries"""
    
    classifier = QueryClassifier()
    
    test_queries = [
        # Should be SIMPLE (no documents)
        "What's 2+2?",
        "Hello, how are you?",
        "Translate 'hello' to Spanish",
        "What's the weather like?",
        "Explain quantum computing",
        "Write a Python function to sort a list",
        
        # Should be DOCUMENT (needs retrieval)
        "What's our vacation policy?",
        "Show me the employee handbook",
        "Find the latest quarterly report",
        "What's the procedure for submitting expenses?",
        "According to our guidelines, how do I request time off?",
        "Where can I find the onboarding checklist?",
        
        # Edge cases
        "How do I write a policy document?",  # SIMPLE - asking how to write, not for a policy
        "What does policy mean in general?",  # SIMPLE - general knowledge
        "Tell me about our company policy",   # DOCUMENT - specific to company
    ]
    
    print("\nQuery Classification Test Results")
    print("=" * 80)
    
    for query in test_queries:
        query_type, confidence, metadata = await classifier.classify_query(query)
        print(f"\nQuery: {query}")
        print(f"  Type: {query_type.value}")
        print(f"  Confidence: {confidence:.2%}")
        if metadata.get('matched_patterns'):
            print(f"  Patterns: {metadata['matched_patterns'][:2]}")
        if metadata.get('keywords_found'):
            print(f"  Keywords: {metadata['keywords_found']}")
        if metadata.get('ai_reasoning'):
            print(f"  AI says: {metadata['ai_reasoning']}")


if __name__ == "__main__":
    # Run tests
    import asyncio
    asyncio.run(test_classifier())