"""
Korean-English Tag Mapping System
Maps Korean queries to English tags for internal processing
"""

import re
from typing import Dict, List, Set, Optional, Tuple
import logging

logger = logging.getLogger(__name__)


class KoreanTagMapper:
    """Maps Korean terms to English tags for consistent internal processing"""
    
    def __init__(self):
        """Initialize Korean-English mappings"""
        
        # Category mappings (Korean → English)
        self.category_map = {
            # Korean variations → English category
            '인사': 'hr',
            '인사팀': 'hr',
            '인사부': 'hr',
            'HR': 'hr',
            
            '재무': 'finance',
            '재무팀': 'finance',
            '회계': 'finance',
            '경리': 'finance',
            
            '기술': 'technical',
            '개발': 'technical',
            '개발팀': 'technical',
            'IT': 'technical',
            '기술팀': 'technical',
            
            '정책': 'policy',
            '규정': 'policy',
            '지침': 'policy',
            '규칙': 'policy',
            
            '교육': 'training',
            '연수': 'training',
            '트레이닝': 'training',
            '온보딩': 'training',
            
            '영업': 'sales',
            '세일즈': 'sales',
            '판매': 'sales',
            
            '마케팅': 'marketing',
            '홍보': 'marketing',
            '브랜드': 'marketing',
        }
        
        # Keyword mappings (Korean → English tags)
        self.keyword_map = {
            # HR related
            '휴가': ['vacation', 'leave', 'time-off'],
            '연차': ['annual-leave', 'vacation', 'pto'],
            '병가': ['sick-leave', 'medical-leave'],
            '출산휴가': ['maternity-leave', 'parental-leave'],
            '육아휴직': ['parental-leave', 'childcare-leave'],
            
            # Benefits
            '복지': ['benefits', 'welfare'],
            '복리후생': ['benefits', 'perks'],
            '보험': ['insurance', 'benefits'],
            '연금': ['pension', 'retirement'],
            
            # Work arrangements
            '재택근무': ['remote-work', 'work-from-home', 'wfh'],
            '원격근무': ['remote-work', 'telecommuting'],
            '유연근무': ['flexible-work', 'flextime'],
            '출퇴근': ['commute', 'office-hours'],
            
            # Documents
            '정책': ['policy', 'policies'],
            '절차': ['procedure', 'process'],
            '가이드': ['guide', 'manual'],
            '핸드북': ['handbook', 'manual'],
            '양식': ['form', 'template'],
            '신청서': ['application', 'form', 'request'],
            '보고서': ['report', 'analysis'],
            
            # Finance
            '경비': ['expense', 'reimbursement'],
            '예산': ['budget', 'financial-planning'],
            '급여': ['salary', 'payroll', 'compensation'],
            '보너스': ['bonus', 'incentive'],
            
            # Time references
            '올해': ['current-year', '2024'],
            '작년': ['last-year', '2023'],
            '이번달': ['current-month'],
            '지난달': ['last-month'],
            '1분기': ['q1', 'first-quarter'],
            '2분기': ['q2', 'second-quarter'],
            '3분기': ['q3', 'third-quarter'],
            '4분기': ['q4', 'fourth-quarter'],
            
            # Actions
            '신청': ['apply', 'request', 'submit'],
            '제출': ['submit', 'file'],
            '승인': ['approval', 'approve'],
            '확인': ['check', 'verify', 'confirm'],
            '찾기': ['find', 'search', 'locate'],
            '보기': ['view', 'show', 'display'],
        }
        
        # Document type mappings
        self.doc_type_map = {
            '정책문서': 'policy',
            '정책': 'policy',
            '매뉴얼': 'manual',
            '가이드': 'guide',
            '안내서': 'guide',
            '핸드북': 'handbook',
            '보고서': 'report',
            '리포트': 'report',
            '양식': 'form',
            '템플릿': 'template',
            '신청서': 'application-form',
            '체크리스트': 'checklist',
            '프레젠테이션': 'presentation',
            '발표자료': 'presentation',
        }
        
        # Company-specific terms (customize for 청암)
        self.company_terms = {
            '청암': 'cheongam',
            '우리회사': 'our-company',
            '당사': 'our-company',
            '본사': 'headquarters',
            '서울사무실': 'seoul-office',
            '부산지점': 'busan-branch',
        }
        
        # Build reverse mappings for display
        self.reverse_category_map = {v: k for k, v in self.category_map.items()}
        self.reverse_doc_type_map = {v: k for k, v in self.doc_type_map.items()}
    
    def extract_english_tags(self, korean_text: str) -> Dict[str, List[str]]:
        """
        Extract English tags from Korean text
        
        Args:
            korean_text: Korean query or document text
            
        Returns:
            Dictionary of English tags by type
        """
        
        tags = {
            'categories': [],
            'keywords': [],
            'document_types': [],
            'company_terms': []
        }
        
        korean_lower = korean_text.lower()
        
        # Extract categories
        for korean_cat, english_cat in self.category_map.items():
            if korean_cat in korean_lower:
                if english_cat not in tags['categories']:
                    tags['categories'].append(english_cat)
        
        # Extract keywords
        for korean_keyword, english_tags in self.keyword_map.items():
            if korean_keyword in korean_lower:
                tags['keywords'].extend(english_tags)
        
        # Extract document types
        for korean_type, english_type in self.doc_type_map.items():
            if korean_type in korean_lower:
                if english_type not in tags['document_types']:
                    tags['document_types'].append(english_type)
        
        # Extract company terms
        for korean_term, english_term in self.company_terms.items():
            if korean_term in korean_lower:
                if english_term not in tags['company_terms']:
                    tags['company_terms'].append(english_term)
        
        # Remove duplicates
        tags['keywords'] = list(set(tags['keywords']))
        
        return tags
    
    def map_query_to_tags(self, korean_query: str) -> Dict[str, any]:
        """
        Map Korean query to English tags for system processing
        
        Args:
            korean_query: User's query in Korean
            
        Returns:
            Mapped tags and metadata
        """
        
        # Extract English tags
        extracted_tags = self.extract_english_tags(korean_query)
        
        # Detect query patterns
        query_patterns = self.detect_korean_patterns(korean_query)
        
        # Combine into search hints
        search_hints = {
            'original_query': korean_query,
            'categories': extracted_tags['categories'],
            'tags': extracted_tags['keywords'],
            'document_types': extracted_tags['document_types'],
            'query_intent': query_patterns.get('intent'),
            'time_context': query_patterns.get('time_context'),
            'urgency': query_patterns.get('urgency'),
            'department': self.extract_department(korean_query),
        }
        
        # Add debugging info
        logger.debug(f"Korean query: {korean_query}")
        logger.debug(f"Mapped to tags: {search_hints}")
        
        return search_hints
    
    def detect_korean_patterns(self, text: str) -> Dict[str, str]:
        """Detect patterns in Korean text"""
        
        patterns = {}
        
        # Detect intent
        if any(word in text for word in ['찾아', '찾기', '검색', '보여줘', '알려줘']):
            patterns['intent'] = 'search'
        elif any(word in text for word in ['신청', '제출', '요청']):
            patterns['intent'] = 'submit'
        elif any(word in text for word in ['확인', '체크', '검토']):
            patterns['intent'] = 'verify'
        elif any(word in text for word in ['설명', '알려', '무엇', '뭐야']):
            patterns['intent'] = 'explain'
        
        # Detect time context
        import datetime
        current_year = datetime.datetime.now().year
        
        if '올해' in text or str(current_year) in text:
            patterns['time_context'] = str(current_year)
        elif '작년' in text or str(current_year - 1) in text:
            patterns['time_context'] = str(current_year - 1)
        elif '이번달' in text:
            patterns['time_context'] = 'current-month'
        elif '최신' in text or '최근' in text:
            patterns['time_context'] = 'recent'
        
        # Detect urgency
        if any(word in text for word in ['급해', '긴급', '빨리', '즉시', 'ASAP']):
            patterns['urgency'] = 'high'
        
        return patterns
    
    def extract_department(self, korean_text: str) -> Optional[str]:
        """Extract department from Korean text"""
        
        dept_patterns = {
            'hr': ['인사팀', '인사부', 'HR'],
            'finance': ['재무팀', '재무부', '회계팀'],
            'engineering': ['개발팀', '기술팀', '개발부', 'IT팀'],
            'sales': ['영업팀', '영업부', '세일즈'],
            'marketing': ['마케팅팀', '마케팅부', '홍보팀'],
        }
        
        for dept, korean_names in dept_patterns.items():
            if any(name in korean_text for name in korean_names):
                return dept
        
        return None
    
    def translate_tags_for_display(self, english_tags: Dict[str, any]) -> Dict[str, any]:
        """
        Translate English tags back to Korean for display
        
        Args:
            english_tags: Internal English tags
            
        Returns:
            Korean display values
        """
        
        korean_display = {}
        
        # Translate category
        if 'category' in english_tags:
            korean_display['카테고리'] = self.reverse_category_map.get(
                english_tags['category'], 
                english_tags['category']
            )
        
        # Translate document type
        if 'document_type' in english_tags:
            korean_display['문서유형'] = self.reverse_doc_type_map.get(
                english_tags['document_type'],
                english_tags['document_type']
            )
        
        # Keep some tags in English (technical terms)
        if 'tags' in english_tags:
            korean_display['태그'] = english_tags['tags']
        
        return korean_display
    
    def create_bilingual_document_metadata(self, 
                                          filename: str,
                                          korean_description: str = None) -> Dict:
        """
        Create bilingual metadata for a document
        
        Args:
            filename: Document filename
            korean_description: Optional Korean description
            
        Returns:
            Bilingual metadata structure
        """
        
        # Extract English tags from filename and description
        text_to_analyze = filename
        if korean_description:
            text_to_analyze += " " + korean_description
        
        english_tags = self.extract_english_tags(text_to_analyze)
        
        metadata = {
            # English (for system processing)
            'category': english_tags['categories'][0] if english_tags['categories'] else 'general',
            'tags': english_tags['keywords'],
            'document_type': english_tags['document_types'][0] if english_tags['document_types'] else 'document',
            
            # Korean (for display)
            'display': {
                'filename': filename,
                'description': korean_description,
                'category_korean': self.reverse_category_map.get(
                    english_tags['categories'][0] if english_tags['categories'] else 'general',
                    '일반'
                ),
            },
            
            # Bilingual search terms
            'search_terms': {
                'korean': self.extract_korean_keywords(text_to_analyze),
                'english': english_tags['keywords']
            }
        }
        
        return metadata
    
    def extract_korean_keywords(self, text: str) -> List[str]:
        """Extract Korean keywords for search"""
        
        # Simple keyword extraction (can be enhanced with Korean NLP)
        keywords = []
        
        # Extract nouns (simplified - consider using konlpy for better results)
        korean_patterns = [
            r'[가-힣]+정책',
            r'[가-힣]+신청',
            r'[가-힣]+가이드',
            r'[가-힣]+절차',
            r'[가-힣]+규정',
        ]
        
        for pattern in korean_patterns:
            matches = re.findall(pattern, text)
            keywords.extend(matches)
        
        return list(set(keywords))


# Usage example
def demonstrate_korean_mapping():
    """Demonstrate Korean to English tag mapping"""
    
    mapper = KoreanTagMapper()
    
    test_queries = [
        "2024년 휴가 정책 보여줘",
        "재택근무 신청서 양식 찾아줘",
        "인사팀 최신 공지사항",
        "청암 직원 복리후생 안내서",
        "경비 처리 절차 문서",
        "올해 1분기 재무 보고서",
    ]
    
    print("\n" + "="*60)
    print("Korean Query → English Tags Mapping")
    print("="*60)
    
    for query in test_queries:
        print(f"\n🇰🇷 Korean Query: {query}")
        
        # Map to English tags
        tags = mapper.map_query_to_tags(query)
        
        print("🇬🇧 English Tags:")
        if tags['categories']:
            print(f"  Categories: {tags['categories']}")
        if tags['tags']:
            print(f"  Tags: {tags['tags'][:5]}")  # Show first 5
        if tags['document_types']:
            print(f"  Doc Types: {tags['document_types']}")
        if tags['department']:
            print(f"  Department: {tags['department']}")
        if tags.get('time_context'):
            print(f"  Time: {tags['time_context']}")
    
    # Demonstrate bilingual metadata
    print("\n" + "="*60)
    print("Bilingual Document Metadata")
    print("="*60)
    
    doc_metadata = mapper.create_bilingual_document_metadata(
        filename="2024_휴가정책_최종.pdf",
        korean_description="2024년도 청암 직원 휴가 및 연차 사용 정책 안내"
    )
    
    print("\n📄 Document Metadata:")
    print(f"System Tags (English): {doc_metadata['tags']}")
    print(f"Display Category (Korean): {doc_metadata['display']['category_korean']}")
    print(f"Search Terms (Both):")
    print(f"  Korean: {doc_metadata['search_terms']['korean']}")
    print(f"  English: {doc_metadata['search_terms']['english']}")


if __name__ == "__main__":
    demonstrate_korean_mapping()