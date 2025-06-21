"""
ArXiv API 클라이언트
Swift 및 iOS 관련 논문을 검색하고 메타데이터를 가져옵니다.
"""
import logging
import requests
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from dataclasses import dataclass
from .config import Config

logger = logging.getLogger(__name__)

@dataclass
class Paper:
    """논문 정보를 담는 데이터 클래스"""
    id: str
    title: str
    abstract: str
    authors: List[str]
    published: datetime
    updated: datetime
    url: str
    pdf_url: str
    categories: List[str]
    
    def __post_init__(self):
        """초기화 후 처리"""
        # arXiv ID에서 버전 정보 제거
        if 'v' in self.id:
            self.id = self.id.split('v')[0]

class ArxivClient:
    """ArXiv API 클라이언트"""
    
    def __init__(self):
        self.base_url = "http://export.arxiv.org/api/query"
        self.search_terms = [term.strip() for term in Config.ARXIV_SEARCH_TERMS]
        self.max_results = Config.ARXIV_MAX_RESULTS
        self.search_days = Config.ARXIV_SEARCH_DAYS
    
    def search_papers(self, days_back: Optional[int] = None) -> List[Paper]:
        """
        Swift/iOS 관련 논문을 검색합니다.
        
        Args:
            days_back: 검색할 일수 (기본값: Config.ARXIV_SEARCH_DAYS)
            
        Returns:
            List[Paper]: 검색된 논문 리스트
        """
        if days_back is None:
            days_back = self.search_days
            
        try:
            # 검색어 구성 (OR 조건으로 연결)
            search_query = " OR ".join([f'all:"{term}"' for term in self.search_terms])
            
            # 날짜 필터 추가 (최근 N일)
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days_back)
            
            # ArXiv API 파라미터
            params = {
                'search_query': search_query,
                'start': 0,
                'max_results': self.max_results,
                'sortBy': 'submittedDate',  # 제출일 기준 정렬
                'sortOrder': 'descending'   # 최신순
            }
            
            logger.info(f"ArXiv 검색 시작: {len(self.search_terms)}개 키워드, 최근 {days_back}일, 최대 {self.max_results}개")
            
            response = requests.get(self.base_url, params=params, timeout=30)
            response.raise_for_status()
            
            papers = self._parse_response(response.text, start_date)
            
            logger.info(f"검색 완료: {len(papers)}개 논문 발견")
            return papers
            
        except requests.exceptions.RequestException as e:
            logger.error(f"ArXiv API 요청 실패: {str(e)}")
            return []
        except Exception as e:
            logger.error(f"논문 검색 중 오류 발생: {str(e)}")
            return []
    
    def _parse_response(self, xml_content: str, start_date: datetime) -> List[Paper]:
        """XML 응답을 파싱하여 논문 리스트로 변환"""
        papers = []
        
        try:
            root = ET.fromstring(xml_content)
            
            # XML 네임스페이스 정의
            namespaces = {
                'atom': 'http://www.w3.org/2005/Atom',
                'arxiv': 'http://arxiv.org/schemas/atom'
            }
            
            entries = root.findall('atom:entry', namespaces)
            logger.info(f"XML에서 {len(entries)}개 항목 발견")
            
            for entry in entries:
                try:
                    paper = self._parse_entry(entry, namespaces)
                    
                    # 날짜 필터링 (더 유연하게)
                    if paper and paper.published >= start_date:
                        papers.append(paper)
                    elif paper:
                        logger.debug(f"날짜 필터로 제외된 논문: {paper.title[:50]}... ({paper.published.date()})")
                        
                except Exception as e:
                    logger.warning(f"논문 항목 파싱 실패: {str(e)}")
                    continue
            
            # 최신순으로 정렬 (published 날짜 기준)
            papers.sort(key=lambda x: x.published, reverse=True)
            
            return papers
            
        except ET.ParseError as e:
            logger.error(f"XML 파싱 오류: {str(e)}")
            return []
        except Exception as e:
            logger.error(f"응답 파싱 중 오류 발생: {str(e)}")
            return []
    
    def _parse_entry(self, entry, namespaces) -> Optional[Paper]:
        """개별 논문 항목을 파싱"""
        try:
            # ID 추출
            id_elem = entry.find('atom:id', namespaces)
            if id_elem is None:
                return None
            paper_id = id_elem.text.split('/')[-1]  # URL에서 ID만 추출
            
            # 제목 추출
            title_elem = entry.find('atom:title', namespaces)
            if title_elem is None:
                return None
            title = title_elem.text.strip()
            
            # 초록 추출
            summary_elem = entry.find('atom:summary', namespaces)
            abstract = summary_elem.text.strip() if summary_elem is not None else ""
            
            # 저자 추출
            author_elems = entry.findall('atom:author/atom:name', namespaces)
            authors = [author.text.strip() for author in author_elems]
            
            # 날짜 추출
            published_elem = entry.find('atom:published', namespaces)
            updated_elem = entry.find('atom:updated', namespaces)
            
            published = self._parse_date(published_elem.text) if published_elem is not None else datetime.now()
            updated = self._parse_date(updated_elem.text) if updated_elem is not None else published
            
            # URL 추출
            url = id_elem.text
            pdf_url = url.replace('/abs/', '/pdf/') + '.pdf'
            
            # 카테고리 추출
            category_elems = entry.findall('atom:category', namespaces)
            categories = [cat.get('term', '') for cat in category_elems]
            
            return Paper(
                id=paper_id,
                title=title,
                abstract=abstract,
                authors=authors,
                published=published,
                updated=updated,
                url=url,
                pdf_url=pdf_url,
                categories=categories
            )
            
        except Exception as e:
            logger.warning(f"논문 항목 파싱 실패: {str(e)}")
            return None
    
    def _parse_date(self, date_str: str) -> datetime:
        """날짜 문자열을 datetime 객체로 변환"""
        try:
            # ArXiv 날짜 형식: 2024-01-15T09:00:00Z
            return datetime.fromisoformat(date_str.replace('Z', '+00:00')).replace(tzinfo=None)
        except Exception:
            # 파싱 실패 시 현재 시간 반환
            return datetime.now() 