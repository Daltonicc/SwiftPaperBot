"""
arXiv API 클라이언트
Swift 및 iOS 관련 논문을 검색하고 메타데이터를 가져옵니다.
"""
import logging
import requests
import feedparser
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class Paper:
    """논문 정보를 담는 데이터 클래스"""
    id: str
    title: str
    authors: List[str]
    abstract: str
    published_date: datetime
    pdf_url: str
    categories: List[str]
    
    def __post_init__(self):
        """초기화 후 처리"""
        # arXiv ID에서 버전 정보 제거
        if 'v' in self.id:
            self.id = self.id.split('v')[0]

class ArxivClient:
    """arXiv API 클라이언트 클래스"""
    
    BASE_URL = "http://export.arxiv.org/api/query"
    
    def __init__(self, max_results: int = 10):
        self.max_results = max_results
    
    def search_papers(self, 
                     search_terms: List[str], 
                     days_back: int = 1) -> List[Paper]:
        """
        Swift/iOS 관련 논문을 검색합니다.
        
        Args:
            search_terms: 검색할 키워드 리스트
            days_back: 며칠 전까지의 논문을 가져올지 결정
            
        Returns:
            Paper 객체의 리스트
        """
        logger.info(f"arXiv에서 논문 검색 시작: {search_terms}")
        
        try:
            # 검색 쿼리 구성
            query = self._build_search_query(search_terms)
            
            # API 요청
            params = {
                'search_query': query,
                'start': 0,
                'max_results': self.max_results,
                'sortBy': 'submittedDate',
                'sortOrder': 'descending'
            }
            
            response = requests.get(self.BASE_URL, params=params, timeout=30)
            response.raise_for_status()
            
            # XML 파싱
            feed = feedparser.parse(response.content)
            
            papers = []
            cutoff_date = datetime.now() - timedelta(days=days_back)
            
            for entry in feed.entries:
                try:
                    paper = self._parse_entry(entry)
                    
                    # 최근 논문만 필터링
                    if paper.published_date >= cutoff_date:
                        papers.append(paper)
                        
                except Exception as e:
                    logger.warning(f"논문 파싱 중 오류 발생: {e}")
                    continue
            
            logger.info(f"{len(papers)}개의 논문을 찾았습니다")
            return papers
            
        except Exception as e:
            logger.error(f"arXiv 검색 중 오류 발생: {e}")
            return []
    
    def _build_search_query(self, search_terms: List[str]) -> str:
        """검색 쿼리를 구성합니다"""
        # Swift/iOS 관련 키워드로 제목과 초록에서 검색
        terms = [term.strip() for term in search_terms if term.strip()]
        
        # OR 조건으로 연결하여 하나라도 매치되면 검색
        title_queries = [f'ti:"{term}"' for term in terms]
        abstract_queries = [f'abs:"{term}"' for term in terms]
        
        # 제목 또는 초록에 키워드가 포함된 논문 검색
        query_parts = title_queries + abstract_queries
        query = '(' + ' OR '.join(query_parts) + ')'
        
        # 컴퓨터 과학 분야로 제한
        query += ' AND cat:cs.*'
        
        return query
    
    def _parse_entry(self, entry) -> Paper:
        """arXiv 엔트리를 Paper 객체로 변환합니다"""
        # ID 추출 (URL에서 arXiv ID 부분만)
        arxiv_id = entry.id.split('/')[-1]
        
        # 저자 정보 추출
        authors = []
        if hasattr(entry, 'authors'):
            authors = [author.name for author in entry.authors]
        elif hasattr(entry, 'author'):
            authors = [entry.author]
        
        # 발행 날짜 파싱
        published_date = datetime.strptime(
            entry.published, '%Y-%m-%dT%H:%M:%SZ'
        )
        
        # PDF URL 찾기
        pdf_url = ""
        if hasattr(entry, 'links'):
            for link in entry.links:
                if link.get('type') == 'application/pdf':
                    pdf_url = link.href
                    break
        
        # 카테고리 추출
        categories = []
        if hasattr(entry, 'tags'):
            categories = [tag.term for tag in entry.tags]
        
        return Paper(
            id=arxiv_id,
            title=entry.title.replace('\n', ' ').strip(),
            authors=authors,
            abstract=entry.summary.replace('\n', ' ').strip(),
            published_date=published_date,
            pdf_url=pdf_url,
            categories=categories
        ) 