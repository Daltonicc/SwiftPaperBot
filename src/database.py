"""
데이터베이스 관리 모듈
논문 정보와 요약 데이터를 SQLite에 저장하고 관리합니다.
"""
import sqlite3
import logging
import os
from datetime import datetime
from typing import List, Optional, Tuple
from contextlib import contextmanager

from .arxiv_client import Paper
from .summarizer import PaperSummary

logger = logging.getLogger(__name__)

class DatabaseManager:
    """데이터베이스 관리 클래스"""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        self._ensure_db_directory()
        self._initialize_database()
    
    def _ensure_db_directory(self):
        """데이터베이스 디렉토리가 존재하는지 확인하고 생성합니다"""
        db_dir = os.path.dirname(self.db_path)
        if db_dir and not os.path.exists(db_dir):
            os.makedirs(db_dir)
    
    def _initialize_database(self):
        """데이터베이스 테이블을 초기화합니다"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # 논문 테이블 생성
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS papers (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    authors TEXT NOT NULL,
                    abstract TEXT NOT NULL,
                    published_date TIMESTAMP NOT NULL,
                    pdf_url TEXT NOT NULL,
                    categories TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # 요약 테이블 생성
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS summaries (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    paper_id TEXT NOT NULL,
                    one_line_summary TEXT NOT NULL,
                    key_points TEXT NOT NULL,
                    detailed_summary TEXT NOT NULL,
                    relevance_score REAL NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (paper_id) REFERENCES papers (id)
                )
            ''')
            
            # 전송 기록 테이블 생성 (중복 전송 방지)
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS sent_papers (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    paper_id TEXT NOT NULL,
                    sent_date DATE NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(paper_id, sent_date)
                )
            ''')
            
            conn.commit()
            logger.info("데이터베이스 초기화 완료")
    
    @contextmanager
    def _get_connection(self):
        """데이터베이스 연결 컨텍스트 매니저"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row  # 딕셔너리 형태로 결과 반환
        try:
            yield conn
        finally:
            conn.close()
    
    def save_paper(self, paper: Paper) -> bool:
        """논문 정보를 저장합니다"""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT OR REPLACE INTO papers 
                    (id, title, authors, abstract, published_date, pdf_url, categories)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (
                    paper.id,
                    paper.title,
                    ';'.join(paper.authors),
                    paper.abstract,
                    paper.published_date,
                    paper.pdf_url,
                    ';'.join(paper.categories)
                ))
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"논문 저장 실패: {e}")
            return False
    
    def save_summary(self, summary: PaperSummary) -> bool:
        """논문 요약을 저장합니다"""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO summaries 
                    (paper_id, one_line_summary, key_points, detailed_summary, relevance_score)
                    VALUES (?, ?, ?, ?, ?)
                ''', (
                    summary.paper_id,
                    summary.one_line_summary,
                    summary.key_points,
                    summary.detailed_summary,
                    summary.relevance_score
                ))
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"요약 저장 실패: {e}")
            return False
    
    def is_paper_sent_today(self, paper_id: str) -> bool:
        """오늘 이미 전송된 논문인지 확인합니다"""
        today = datetime.now().date()
        
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT COUNT(*) FROM sent_papers 
                    WHERE paper_id = ? AND sent_date = ?
                ''', (paper_id, today))
                
                count = cursor.fetchone()[0]
                return count > 0
        except Exception as e:
            logger.error(f"전송 기록 확인 실패: {e}")
            return False
    
    def mark_paper_as_sent(self, paper_id: str) -> bool:
        """논문을 전송됨으로 표시합니다"""
        today = datetime.now().date()
        
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT OR IGNORE INTO sent_papers (paper_id, sent_date)
                    VALUES (?, ?)
                ''', (paper_id, today))
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"전송 기록 저장 실패: {e}")
            return False
    
    def get_paper_by_id(self, paper_id: str) -> Optional[Paper]:
        """ID로 논문을 조회합니다"""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT * FROM papers WHERE id = ?', (paper_id,))
                row = cursor.fetchone()
                
                if row:
                    return Paper(
                        id=row['id'],
                        title=row['title'],
                        authors=row['authors'].split(';'),
                        abstract=row['abstract'],
                        published_date=datetime.fromisoformat(row['published_date']),
                        pdf_url=row['pdf_url'],
                        categories=row['categories'].split(';')
                    )
                return None
        except Exception as e:
            logger.error(f"논문 조회 실패: {e}")
            return None
    
    def get_recent_papers(self, days: int = 7) -> List[Paper]:
        """최근 며칠간의 논문을 조회합니다"""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT * FROM papers 
                    WHERE created_at >= datetime('now', '-{} days')
                    ORDER BY published_date DESC
                '''.format(days))
                
                papers = []
                for row in cursor.fetchall():
                    papers.append(Paper(
                        id=row['id'],
                        title=row['title'],
                        authors=row['authors'].split(';'),
                        abstract=row['abstract'],
                        published_date=datetime.fromisoformat(row['published_date']),
                        pdf_url=row['pdf_url'],
                        categories=row['categories'].split(';')
                    ))
                
                return papers
        except Exception as e:
            logger.error(f"최근 논문 조회 실패: {e}")
            return []
    
    def cleanup_old_data(self, days: int = 30):
        """30일 이상 된 데이터를 정리합니다"""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                # 오래된 전송 기록 삭제
                cursor.execute('''
                    DELETE FROM sent_papers 
                    WHERE created_at < datetime('now', '-{} days')
                '''.format(days))
                
                # 오래된 요약 삭제
                cursor.execute('''
                    DELETE FROM summaries 
                    WHERE created_at < datetime('now', '-{} days')
                '''.format(days))
                
                # 오래된 논문 삭제
                cursor.execute('''
                    DELETE FROM papers 
                    WHERE created_at < datetime('now', '-{} days')
                '''.format(days))
                
                conn.commit()
                logger.info(f"{days}일 이상 된 데이터 정리 완료")
                
        except Exception as e:
            logger.error(f"데이터 정리 실패: {e}")
    
    def get_statistics(self) -> dict:
        """데이터베이스 통계를 반환합니다"""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                stats = {}
                
                # 총 논문 수
                cursor.execute('SELECT COUNT(*) FROM papers')
                stats['total_papers'] = cursor.fetchone()[0]
                
                # 총 요약 수
                cursor.execute('SELECT COUNT(*) FROM summaries')
                stats['total_summaries'] = cursor.fetchone()[0]
                
                # 이번 달 전송된 논문 수
                cursor.execute('''
                    SELECT COUNT(*) FROM sent_papers 
                    WHERE sent_date >= date('now', 'start of month')
                ''')
                stats['sent_this_month'] = cursor.fetchone()[0]
                
                return stats
                
        except Exception as e:
            logger.error(f"통계 조회 실패: {e}")
            return {} 