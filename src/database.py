"""
데이터베이스 관리 모듈
논문 정보와 요약 데이터를 SQLite에 저장하고 관리합니다.
"""
import sqlite3
import logging
import os
from datetime import datetime, timedelta
from typing import List, Optional, Tuple, Dict
from contextlib import contextmanager
import json

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
            
            # 요약 테이블 생성 (확장된 스키마)
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS summaries (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    paper_id TEXT NOT NULL,
                    one_line_summary TEXT NOT NULL,
                    key_points TEXT NOT NULL,
                    detailed_summary TEXT NOT NULL,
                    relevance_score REAL NOT NULL,
                    technical_summary TEXT DEFAULT '',
                    business_impact TEXT DEFAULT '',
                    extracted_keywords TEXT DEFAULT '[]',
                    swift_keywords_score REAL DEFAULT 0.0,
                    category_prediction TEXT DEFAULT 'General',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (paper_id) REFERENCES papers (id)
                )
            ''')
            
            # 기존 테이블에 새 컬럼 추가 (ALTER TABLE)
            try:
                cursor.execute('ALTER TABLE summaries ADD COLUMN technical_summary TEXT DEFAULT ""')
            except sqlite3.OperationalError:
                pass  # 이미 존재하는 컬럼
            
            try:
                cursor.execute('ALTER TABLE summaries ADD COLUMN business_impact TEXT DEFAULT ""')
            except sqlite3.OperationalError:
                pass
            
            try:
                cursor.execute('ALTER TABLE summaries ADD COLUMN extracted_keywords TEXT DEFAULT "[]"')
            except sqlite3.OperationalError:
                pass
            
            try:
                cursor.execute('ALTER TABLE summaries ADD COLUMN swift_keywords_score REAL DEFAULT 0.0')
            except sqlite3.OperationalError:
                pass
            
            try:
                cursor.execute('ALTER TABLE summaries ADD COLUMN category_prediction TEXT DEFAULT "General"')
            except sqlite3.OperationalError:
                pass
            
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
            
            # 통계 테이블 생성 (일일 통계 저장)
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS daily_statistics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date DATE NOT NULL UNIQUE,
                    total_papers INTEGER DEFAULT 0,
                    relevant_papers INTEGER DEFAULT 0,
                    avg_relevance_score REAL DEFAULT 0.0,
                    avg_swift_keywords_score REAL DEFAULT 0.0,
                    category_distribution TEXT DEFAULT '{}',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
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
                    paper.published,
                    paper.pdf_url,
                    ';'.join(paper.categories)
                ))
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"논문 저장 실패: {e}")
            return False
    
    def save_summary(self, summary: PaperSummary) -> bool:
        """논문 요약을 저장합니다 (확장된 필드 포함)"""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO summaries 
                    (paper_id, one_line_summary, key_points, detailed_summary, relevance_score,
                     technical_summary, business_impact, extracted_keywords, swift_keywords_score, category_prediction)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    summary.paper_id,
                    summary.one_line_summary,
                    summary.key_points,
                    summary.detailed_summary,
                    summary.relevance_score,
                    summary.technical_summary,
                    summary.business_impact,
                    json.dumps(summary.extracted_keywords),
                    summary.swift_keywords_score,
                    summary.category_prediction
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
                        abstract=row['abstract'],
                        authors=row['authors'].split(';'),
                        published=datetime.fromisoformat(row['published_date']),
                        updated=datetime.fromisoformat(row['published_date']),
                        url=f"https://arxiv.org/abs/{row['id']}",
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
                    ORDER BY created_at DESC
                '''.format(days))
                
                papers = []
                for row in cursor.fetchall():
                    papers.append(Paper(
                        id=row['id'],
                        title=row['title'],
                        abstract=row['abstract'],
                        authors=row['authors'].split(';'),
                        published=datetime.fromisoformat(row['published_date']),
                        updated=datetime.fromisoformat(row['published_date']),
                        url=f"https://arxiv.org/abs/{row['id']}",
                        pdf_url=row['pdf_url'],
                        categories=row['categories'].split(';')
                    ))
                
                return papers
        except Exception as e:
            logger.error(f"최근 논문 조회 실패: {e}")
            return []
    
    def cleanup_old_data(self, days: int = 30):
        """오래된 데이터를 정리합니다"""
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
                
                # 오래된 논문 삭제 (참조되지 않는 것만)
                cursor.execute('''
                    DELETE FROM papers 
                    WHERE created_at < datetime('now', '-{} days')
                    AND id NOT IN (SELECT DISTINCT paper_id FROM summaries)
                '''.format(days))
                
                conn.commit()
                logger.info(f"{days}일 이전 데이터 정리 완료")
        except Exception as e:
            logger.error(f"데이터 정리 실패: {e}")
    
    def save_daily_statistics(self, date: str, stats: Dict) -> bool:
        """일일 통계를 저장합니다"""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT OR REPLACE INTO daily_statistics 
                    (date, total_papers, relevant_papers, avg_relevance_score, 
                     avg_swift_keywords_score, category_distribution)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (
                    date,
                    stats.get('total_papers', 0),
                    stats.get('high_relevance_count', 0),
                    stats.get('avg_relevance_score', 0.0),
                    stats.get('avg_swift_keywords_score', 0.0),
                    json.dumps(stats.get('category_distribution', {}))
                ))
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"일일 통계 저장 실패: {e}")
            return False
    
    def get_statistics(self, days: int = 30) -> Dict:
        """통계 정보를 조회합니다 (확장된 통계)"""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                # 기본 통계
                cursor.execute('''
                    SELECT 
                        COUNT(*) as total_papers,
                        AVG(relevance_score) as avg_relevance,
                        MAX(relevance_score) as max_relevance,
                        MIN(relevance_score) as min_relevance,
                        AVG(swift_keywords_score) as avg_swift_keywords,
                        COUNT(CASE WHEN relevance_score >= 8.0 THEN 1 END) as high_relevance_count
                    FROM summaries 
                    WHERE created_at >= datetime('now', '-{} days')
                '''.format(days))
                
                basic_stats = cursor.fetchone()
                
                # 카테고리 분포
                cursor.execute('''
                    SELECT category_prediction, COUNT(*) as count
                    FROM summaries 
                    WHERE created_at >= datetime('now', '-{} days')
                    GROUP BY category_prediction
                    ORDER BY count DESC
                '''.format(days))
                
                category_stats = cursor.fetchall()
                category_distribution = {row['category_prediction']: row['count'] for row in category_stats}
                
                # 일별 통계 (최근 7일)
                cursor.execute('''
                    SELECT 
                        DATE(created_at) as date,
                        COUNT(*) as papers_count,
                        AVG(relevance_score) as avg_relevance,
                        COUNT(CASE WHEN relevance_score >= 8.0 THEN 1 END) as relevant_count
                    FROM summaries 
                    WHERE created_at >= datetime('now', '-7 days')
                    GROUP BY DATE(created_at)
                    ORDER BY date DESC
                ''')
                
                daily_stats = cursor.fetchall()
                daily_breakdown = []
                for row in daily_stats:
                    daily_breakdown.append({
                        'date': row['date'],
                        'total_papers': row['papers_count'],
                        'relevant_papers': row['relevant_count'],
                        'avg_relevance': round(row['avg_relevance'] or 0, 2)
                    })
                
                # 키워드 분석
                cursor.execute('''
                    SELECT extracted_keywords
                    FROM summaries 
                    WHERE created_at >= datetime('now', '-{} days')
                    AND extracted_keywords != '[]'
                '''.format(days))
                
                keyword_rows = cursor.fetchall()
                all_keywords = []
                for row in keyword_rows:
                    try:
                        keywords = json.loads(row['extracted_keywords'])
                        all_keywords.extend(keywords)
                    except:
                        continue
                
                # 키워드 빈도 계산
                keyword_freq = {}
                for keyword in all_keywords:
                    keyword_freq[keyword] = keyword_freq.get(keyword, 0) + 1
                
                top_keywords = sorted(keyword_freq.items(), key=lambda x: x[1], reverse=True)[:10]
                
                return {
                    'period_days': days,
                    'total_papers': basic_stats['total_papers'] or 0,
                    'avg_relevance_score': round(basic_stats['avg_relevance'] or 0, 2),
                    'max_relevance_score': basic_stats['max_relevance'] or 0,
                    'min_relevance_score': basic_stats['min_relevance'] or 0,
                    'avg_swift_keywords_score': round(basic_stats['avg_swift_keywords'] or 0, 2),
                    'high_relevance_count': basic_stats['high_relevance_count'] or 0,
                    'category_distribution': category_distribution,
                    'daily_breakdown': daily_breakdown,
                    'top_keywords': dict(top_keywords),
                    'relevance_rate': round((basic_stats['high_relevance_count'] or 0) / max(basic_stats['total_papers'] or 1, 1) * 100, 1)
                }
                
        except Exception as e:
            logger.error(f"통계 조회 실패: {e}")
            return {}
    
    def get_summary_by_paper_id(self, paper_id: str) -> Optional[PaperSummary]:
        """논문 ID로 요약을 조회합니다"""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT * FROM summaries WHERE paper_id = ? ORDER BY created_at DESC LIMIT 1', (paper_id,))
                row = cursor.fetchone()
                
                if row:
                    try:
                        extracted_keywords = json.loads(row['extracted_keywords'] or '[]')
                    except:
                        extracted_keywords = []
                    
                    return PaperSummary(
                        paper_id=row['paper_id'],
                        one_line_summary=row['one_line_summary'],
                        key_points=row['key_points'],
                        detailed_summary=row['detailed_summary'],
                        relevance_score=row['relevance_score'],
                        technical_summary=row.get('technical_summary', ''),
                        business_impact=row.get('business_impact', ''),
                        extracted_keywords=extracted_keywords,
                        swift_keywords_score=row.get('swift_keywords_score', 0.0),
                        category_prediction=row.get('category_prediction', 'General')
                    )
                return None
        except Exception as e:
            logger.error(f"요약 조회 실패: {e}")
            return None 