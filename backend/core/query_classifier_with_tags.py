"""
Enhanced Query Classification with Document Tag Integration
Combines query classification with document tagging for optimal routing
"""

import re
import logging
from typing import Dict, Any, List, Optional, Tuple, Set
from enum import Enum
import asyncio

from openai import AsyncOpenAI
from .utils import get_env_var
from .query_classifier import QueryType, QueryClassifier

logger = logging.getLogger(__name__)


class TagAwareQueryClassifier(QueryClassifier):
    """Query classifier that leverages document tags for intelligent routing"""
    
    def __init__(self):
        """Initialize tag-aware classifier"""
        super().__init__()
        
        # Tag-to-keyword mappings for better matching
        self.tag_mappings = {
            # Category mappings
            'hr': ['human resources', 'employee', 'staff', '인사', '직원'],
            'finance': ['financial', 'budget', 'expense', '재무', '예산'],
            'technical': ['tech', 'engineering', 'development', '기술', '개발'],
            'policy': ['policies', 'guideline', 'rule', '정책', '지침'],
            'training': ['onboarding', 'learning', 'education', '교육', '연수'],
            
            # Document type mappings
            'manual': ['guide', 'handbook', 'instructions', '매뉴얼', '안내서'],
            'report': ['analysis', 'summary', 'review', '보고서', '분석'],
            'form': ['template', 'application', 'request', '양식', '신청서'],
            
            # Time-based mappings
            '2024': ['this year', 'current year', '올해'],
            '2023': ['last year', 'previous year', '작년'],
            'q1': ['first quarter', 'jan-mar', '1분기'],
            'q2': ['second quarter', 'apr-jun', '2분기'],
        }
    
    async def classify_with_tag_hints(self, 
                                     query: str,
                                     available_tags: Optional[Dict[str, List[str]]] = None) -> Dict[str, Any]:
        """
        Classify query and provide tag-based filtering hints
        
        Args:
            query: User's query
            available_tags: Dictionary of available tags from documents
                          {category: [...], tags: [...], departments: [...]}
        
        Returns:
            Classification result with tag filtering hints
        """
        
        # Get base classification
        query_type, confidence, metadata = await self.classify_query(query)
        
        # If it doesn't need documents, no tag filtering needed
        if query_type == QueryType.SIMPLE:
            return {
                'query_type': query_type,
                'confidence': confidence,
                'needs_documents': False,
                'metadata': metadata
            }
        
        # Extract tag hints for document filtering
        tag_hints = self.extract_tag_hints(query, metadata)
        
        # Match against available tags if provided
        if available_tags:
            matched_tags = self.match_available_tags(tag_hints, available_tags)
            tag_hints['matched_tags'] = matched_tags
            
            # Adjust confidence based on tag matches
            if matched_tags['exact_matches']:
                confidence = min(confidence * 1.2, 1.0)
            elif not matched_tags['partial_matches']:
                confidence *= 0.8  # Lower confidence if no tag matches
        
        return {
            'query_type': query_type,
            'confidence': confidence,
            'needs_documents': True,
            'tag_filters': tag_hints,
            'metadata': metadata
        }
    
    def extract_tag_hints(self, query: str, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract tag hints from query for document filtering
        
        Returns:
            Dictionary with suggested tags for filtering
        """
        
        query_lower = query.lower()
        hints = {
            'categories': set(),
            'tags': set(),
            'departments': set(),
            'document_types': set(),
            'time_context': None,
            'priority_terms': [],
            'exclude_categories': set()
        }
        
        # Extract categories based on keywords
        for category, keywords in self.tag_mappings.items():
            if category in ['hr', 'finance', 'technical', 'policy', 'training']:
                if any(kw in query_lower for kw in [category] + keywords):
                    hints['categories'].add(category)
        
        # Extract document types
        doc_type_patterns = {
            'manual': r'(manual|guide|handbook|how.to)',
            'report': r'(report|analysis|summary|metrics)',
            'policy': r'(policy|policies|guideline|procedure)',
            'form': r'(form|template|application|checklist)',
            'presentation': r'(presentation|slides|deck|ppt)',
        }
        
        for doc_type, pattern in doc_type_patterns.items():
            if re.search(pattern, query_lower):
                hints['document_types'].add(doc_type)
        
        # Extract time context
        time_patterns = [
            (r'(2024|this year|current year)', '2024'),
            (r'(2023|last year|previous year)', '2023'),
            (r'(q1|first quarter|jan|feb|mar)', 'q1-2024'),
            (r'(q2|second quarter|apr|may|jun)', 'q2-2024'),
            (r'(recent|latest|newest|current)', 'recent'),
            (r'(january|february|march|april|may|june)', 'month-specific'),
        ]
        
        for pattern, time_context in time_patterns:
            if re.search(pattern, query_lower):
                hints['time_context'] = time_context
                hints['tags'].add(time_context)
                break
        
        # Extract department hints
        dept_patterns = {
            'hr': r'(hr|human.resources|people.team|인사)',
            'engineering': r'(engineering|development|tech.team|개발|기술)',
            'sales': r'(sales|revenue|business.development|영업)',
            'marketing': r'(marketing|brand|communications|마케팅)',
            'finance': r'(finance|accounting|budget|재무|회계)',
            'legal': r'(legal|compliance|contracts|법무)',
        }
        
        for dept, pattern in dept_patterns.items():
            if re.search(pattern, query_lower):
                hints['departments'].add(dept)
        
        # Extract priority terms (for ranking)
        priority_patterns = [
            (r'(urgent|asap|immediately|critical)', 'urgent'),
            (r'(latest|newest|most.recent|updated)', 'recent'),
            (r'(official|approved|final)', 'official'),
            (r'(draft|preliminary|proposed)', 'draft'),
        ]
        
        for pattern, priority in priority_patterns:
            if re.search(pattern, query_lower):
                hints['priority_terms'].append(priority)
        
        # Extract specific tags from the query
        # Look for quoted terms or specific references
        quoted_terms = re.findall(r'"([^"]+)"', query)
        for term in quoted_terms:
            hints['tags'].add(term.lower())
        
        # Add keywords found during classification
        if metadata.get('keywords_found'):
            hints['tags'].update(metadata['keywords_found'])
        
        # Determine exclusions (what NOT to include)
        if 'not' in query_lower or 'except' in query_lower:
            # Simple negation detection
            negation_patterns = [
                r'not?\s+(\w+)',
                r'except?\s+(\w+)',
                r'excluding?\s+(\w+)',
            ]
            for pattern in negation_patterns:
                matches = re.findall(pattern, query_lower)
                for match in matches:
                    if match in self.tag_mappings:
                        hints['exclude_categories'].add(match)
        
        # Convert sets to lists for JSON serialization
        return {
            'categories': list(hints['categories']),
            'tags': list(hints['tags']),
            'departments': list(hints['departments']),
            'document_types': list(hints['document_types']),
            'time_context': hints['time_context'],
            'priority_terms': hints['priority_terms'],
            'exclude_categories': list(hints['exclude_categories'])
        }
    
    def match_available_tags(self, 
                            tag_hints: Dict[str, Any], 
                            available_tags: Dict[str, List[str]]) -> Dict[str, Any]:
        """
        Match extracted hints against available document tags
        
        Args:
            tag_hints: Extracted hints from query
            available_tags: Available tags in the document system
        
        Returns:
            Matched tags with confidence scores
        """
        
        matches = {
            'exact_matches': {},
            'partial_matches': {},
            'suggested_expansions': []
        }
        
        # Check exact matches
        for hint_type in ['categories', 'tags', 'departments']:
            if hint_type in tag_hints and hint_type in available_tags:
                hint_values = set(tag_hints[hint_type])
                available_values = set(available_tags.get(hint_type, []))
                
                exact = hint_values.intersection(available_values)
                if exact:
                    matches['exact_matches'][hint_type] = list(exact)
                
                # Check for partial/fuzzy matches
                for hint in hint_values - exact:
                    for available in available_values:
                        if hint in available or available in hint:
                            if hint_type not in matches['partial_matches']:
                                matches['partial_matches'][hint_type] = []
                            matches['partial_matches'][hint_type].append({
                                'query_term': hint,
                                'matched_tag': available,
                                'similarity': 0.7  # Simple substring match
                            })
        
        # Suggest tag expansions based on mappings
        for category in tag_hints.get('categories', []):
            if category in self.tag_mappings:
                related_terms = self.tag_mappings[category]
                for term in related_terms:
                    if term in available_tags.get('tags', []):
                        matches['suggested_expansions'].append(term)
        
        return matches
    
    def calculate_document_relevance_score(self,
                                          document_tags: Dict[str, Any],
                                          tag_hints: Dict[str, Any]) -> float:
        """
        Calculate relevance score for a document based on tag matching
        
        Args:
            document_tags: Tags assigned to the document
            tag_hints: Tag hints extracted from query
        
        Returns:
            Relevance score between 0 and 1
        """
        
        score = 0.0
        weights = {
            'category': 0.3,
            'tags': 0.25,
            'department': 0.2,
            'document_type': 0.15,
            'time_context': 0.1
        }
        
        # Category match
        if tag_hints.get('categories') and document_tags.get('category'):
            if document_tags['category'] in tag_hints['categories']:
                score += weights['category']
        
        # Tag matches (partial credit for multiple matches)
        if tag_hints.get('tags') and document_tags.get('tags'):
            doc_tags = set(document_tags['tags'])
            query_tags = set(tag_hints['tags'])
            overlap = len(doc_tags.intersection(query_tags))
            if overlap > 0:
                score += weights['tags'] * min(1.0, overlap / len(query_tags))
        
        # Department match
        if tag_hints.get('departments') and document_tags.get('department'):
            if document_tags['department'] in tag_hints['departments']:
                score += weights['department']
        
        # Document type match
        if tag_hints.get('document_types') and document_tags.get('document_type'):
            if document_tags['document_type'] in tag_hints['document_types']:
                score += weights['document_type']
        
        # Time context bonus
        if tag_hints.get('time_context'):
            if tag_hints['time_context'] == 'recent':
                # Boost recent documents
                if document_tags.get('created_at'):
                    # Simple recency check (implement proper date logic)
                    score += weights['time_context']
            elif tag_hints['time_context'] in document_tags.get('tags', []):
                score += weights['time_context']
        
        # Apply exclusions
        if tag_hints.get('exclude_categories'):
            if document_tags.get('category') in tag_hints['exclude_categories']:
                score *= 0.1  # Heavily penalize excluded categories
        
        return min(score, 1.0)
    
    async def generate_search_query(self, 
                                   query: str, 
                                   tag_hints: Dict[str, Any]) -> str:
        """
        Generate an optimized search query based on classification and tags
        
        Args:
            query: Original user query
            tag_hints: Extracted tag hints
        
        Returns:
            Optimized search query for document retrieval
        """
        
        # Build search query components
        search_parts = []
        
        # Add main query terms
        search_parts.append(query)
        
        # Add category as context
        if tag_hints.get('categories'):
            search_parts.append(f"category:{','.join(tag_hints['categories'])}")
        
        # Add specific tags
        if tag_hints.get('tags'):
            search_parts.append(f"tags:{','.join(tag_hints['tags'][:5])}")  # Limit tags
        
        # Add time context
        if tag_hints.get('time_context'):
            search_parts.append(f"time:{tag_hints['time_context']}")
        
        # Add document type
        if tag_hints.get('document_types'):
            search_parts.append(f"type:{tag_hints['document_types'][0]}")  # Primary type
        
        # Combine into search query
        optimized_query = ' '.join(search_parts)
        
        return optimized_query


# Example integration
async def demonstrate_tag_aware_classification():
    """Demonstrate how tag-aware classification works"""
    
    classifier = TagAwareQueryClassifier()
    
    # Simulate available tags in your document system
    available_tags = {
        'categories': ['hr', 'finance', 'technical', 'policy', 'training'],
        'tags': ['vacation', '2024', 'benefits', 'remote-work', 'employee-handbook',
                'expense-policy', 'q1-2024', 'q2-2024', 'onboarding'],
        'departments': ['hr', 'engineering', 'sales', 'marketing'],
        'document_types': ['policy', 'manual', 'report', 'form', 'presentation']
    }
    
    test_queries = [
        "What's our vacation policy for 2024?",
        "Show me the latest HR reports",
        "Find the employee handbook but not the contractor one",
        "Q1 financial reports from this year",
        "Remote work guidelines for engineering team",
    ]
    
    print("\n" + "="*80)
    print("TAG-AWARE QUERY CLASSIFICATION DEMO")
    print("="*80)
    
    for query in test_queries:
        print(f"\nQuery: {query}")
        print("-" * 40)
        
        result = await classifier.classify_with_tag_hints(query, available_tags)
        
        print(f"Query Type: {result['query_type'].value}")
        print(f"Confidence: {result['confidence']:.2%}")
        print(f"Needs Documents: {result.get('needs_documents', False)}")
        
        if result.get('tag_filters'):
            filters = result['tag_filters']
            print("\nTag Filters:")
            if filters['categories']:
                print(f"  Categories: {filters['categories']}")
            if filters['tags']:
                print(f"  Tags: {filters['tags']}")
            if filters['departments']:
                print(f"  Departments: {filters['departments']}")
            if filters['document_types']:
                print(f"  Doc Types: {filters['document_types']}")
            if filters['time_context']:
                print(f"  Time: {filters['time_context']}")
        
        if result.get('tag_filters', {}).get('matched_tags'):
            matches = result['tag_filters']['matched_tags']
            if matches['exact_matches']:
                print(f"\nExact Tag Matches: {matches['exact_matches']}")
            if matches['partial_matches']:
                print(f"Partial Matches: {matches['partial_matches']}")
    
    # Demonstrate relevance scoring
    print("\n" + "="*80)
    print("DOCUMENT RELEVANCE SCORING")
    print("="*80)
    
    sample_document = {
        'filename': 'employee_handbook_2024.pdf',
        'category': 'hr',
        'tags': ['employee-handbook', '2024', 'benefits', 'vacation'],
        'department': 'hr',
        'document_type': 'manual'
    }
    
    query = "Find the 2024 employee vacation benefits"
    result = await classifier.classify_with_tag_hints(query, available_tags)
    
    relevance_score = classifier.calculate_document_relevance_score(
        sample_document,
        result['tag_filters']
    )
    
    print(f"\nDocument: {sample_document['filename']}")
    print(f"Query: {query}")
    print(f"Relevance Score: {relevance_score:.2%}")
    print("\nScore Breakdown:")
    print(f"  - Category Match (HR): {'✓' if sample_document['category'] in result['tag_filters']['categories'] else '✗'}")
    print(f"  - Tag Overlap: {len(set(sample_document['tags']).intersection(set(result['tag_filters']['tags'])))} matches")
    print(f"  - Department Match: {'✓' if sample_document['department'] in result['tag_filters']['departments'] else '✗'}")


if __name__ == "__main__":
    import asyncio
    asyncio.run(demonstrate_tag_aware_classification())