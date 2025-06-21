"""
메인 애플리케이션
Swift & iOS 논문 요약 슬랙봇의 메인 실행 파일입니다.
"""
import logging
import sys
from typing import List, Tuple
from datetime import datetime

from .config import Config
from .arxiv_client import ArxivClient, Paper
from .summarizer import PaperSummarizer, PaperSummary
from .slack_client import SlackClient
from .database import DatabaseManager
from .scheduler import TaskScheduler

logger = logging.getLogger(__name__)

class SwiftPaperBot:
    """Swift 논문 요약 슬랙봇 메인 클래스"""
    
    def __init__(self):
        # 설정 검증
        if not Config.validate_config():
            raise ValueError("필수 설정이 누락되었습니다. config.env 파일을 확인해주세요.")
        
        # 컴포넌트 초기화
        self.arxiv_client = ArxivClient()
        self.summarizer = PaperSummarizer(Config.OPENAI_API_KEY or "")
        self.slack_client = SlackClient(Config.SLACK_BOT_TOKEN or "", Config.SLACK_CHANNEL)
        self.db_manager = DatabaseManager(Config.DATABASE_PATH)
        self.scheduler = TaskScheduler()
        
        logger.info("SwiftPaperBot 초기화 완료")
    
    def daily_paper_summary_task(self):
        """매일 실행되는 논문 요약 작업 (확장된 기능)"""
        logger.info("=== 일일 논문 요약 작업 시작 ===")
        
        try:
            # 1. arXiv에서 새로운 논문 검색
            logger.info(f"arXiv에서 논문 검색 중... (최근 {Config.ARXIV_SEARCH_DAYS}일)")
            papers = self.arxiv_client.search_papers(days_back=Config.ARXIV_SEARCH_DAYS)
            
            if not papers:
                logger.info("새로운 논문이 없습니다")
                # 빈 메시지와 함께 기본 통계 전송
                stats = self.db_manager.get_statistics(days=7)
                self.slack_client.send_paper_summaries([], [], stats)
                return
            
            logger.info(f"{len(papers)}개의 논문을 찾았습니다")
            
            # 2. 논문 필터링 및 확장된 요약 생성
            candidate_summaries = []
            candidate_papers = []
            all_summaries = []  # 통계용
            
            for paper in papers:
                # 이미 전송된 논문인지 확인
                if self.db_manager.is_paper_sent_today(paper.id):
                    logger.info(f"이미 전송된 논문 건너뛰기: {paper.title}")
                    continue
                
                # 논문 정보 저장
                self.db_manager.save_paper(paper)
                
                # 논문 요약 생성 (확장된 기능)
                logger.info(f"논문 요약 생성 중: {paper.title}")
                summary = self.summarizer.summarize_paper(paper)
                
                if summary:
                    # 요약 저장
                    self.db_manager.save_summary(summary)
                    all_summaries.append(summary)
                    
                    # 관련성 체크
                    if self.summarizer.is_relevant_paper(summary, min_score=Config.MIN_RELEVANCE_SCORE):
                        candidate_summaries.append(summary)
                        candidate_papers.append(paper)
                        logger.info(f"관련성 있는 논문 발견: {paper.title} (점수: {summary.relevance_score})")
                    else:
                        logger.info(f"관련성 낮은 논문 제외: {paper.title} (점수: {summary.relevance_score})")
                else:
                    logger.warning(f"요약 생성 실패: {paper.title}")
            
            # 3. 통계 생성
            stats = self._generate_comprehensive_stats(all_summaries)
            
            # 4. 관련성 점수와 최신성 기준으로 상위 논문 선택
            if candidate_summaries:
                # 관련성 점수 내림차순, 게시일 내림차순으로 정렬
                sorted_indices = sorted(
                    range(len(candidate_summaries)),
                    key=lambda i: (candidate_summaries[i].relevance_score, candidate_papers[i].published),
                    reverse=True
                )
                
                # 상위 논문들만 선택
                max_papers = min(Config.MAX_DAILY_PAPERS, len(sorted_indices))
                top_summaries = [candidate_summaries[i] for i in sorted_indices[:max_papers]]
                top_papers = [candidate_papers[i] for i in sorted_indices[:max_papers]]
                
                logger.info(f"상위 {len(top_summaries)}개 논문 선택 (총 {len(candidate_summaries)}개 중)")
                for i, summary in enumerate(top_summaries, 1):
                    paper = top_papers[i-1]
                    logger.info(f"  {i}. {paper.title} (관련성: {summary.relevance_score}/10, 날짜: {paper.published.date()})")
                
                # 5. 슬랙으로 확장된 요약 전송
                success = self.slack_client.send_paper_summaries(top_summaries, top_papers, stats)
                
                if success:
                    # 전송 성공 시 전송 기록 저장
                    for paper in top_papers:
                        self.db_manager.mark_paper_as_sent(paper.id)
                    
                    # 일일 통계 저장
                    today = datetime.now().strftime("%Y-%m-%d")
                    self.db_manager.save_daily_statistics(today, stats)
                    
                    logger.info("슬랙 전송 및 기록 저장 완료")
                else:
                    logger.error("슬랙 전송 실패")
                    self.slack_client.send_error_notification("논문 요약 전송에 실패했습니다.")
            else:
                logger.info(f"관련성 높은 논문이 없어 빈 메시지를 전송합니다 ({Config.MIN_RELEVANCE_SCORE}점 이상 기준)")
                self.slack_client.send_paper_summaries([], [], stats)
            
            # 6. 데이터베이스 정리 (주 1회)
            if datetime.now().weekday() == 0:  # 월요일
                logger.info("주간 데이터베이스 정리 실행")
                self.db_manager.cleanup_old_data(days=30)
            
        except Exception as e:
            logger.error(f"일일 논문 요약 작업 중 오류 발생: {e}")
            self.slack_client.send_error_notification(f"논문 요약 작업 중 오류가 발생했습니다: {str(e)}")
        
        logger.info("=== 일일 논문 요약 작업 완료 ===")
    
    def _generate_comprehensive_stats(self, summaries: List[PaperSummary]) -> dict:
        """종합적인 통계를 생성합니다"""
        try:
            # 기본 통계
            basic_stats = self.summarizer.get_summary_statistics(summaries)
            
            # 데이터베이스 통계 (최근 30일)
            db_stats = self.db_manager.get_statistics(days=30)
            
            # 통합 통계
            combined_stats = {
                **basic_stats,
                'db_total_papers': db_stats.get('total_papers', 0),
                'db_avg_relevance': db_stats.get('avg_relevance_score', 0),
                'db_category_distribution': db_stats.get('category_distribution', {}),
                'daily_breakdown': db_stats.get('daily_breakdown', []),
                'top_keywords': db_stats.get('top_keywords', {}),
                'relevance_rate': db_stats.get('relevance_rate', 0)
            }
            
            return combined_stats
            
        except Exception as e:
            logger.error(f"통계 생성 중 오류: {e}")
            return {}
    
    def start_scheduler(self, schedule_time: str = "08:00"):
        """스케줄러를 시작합니다"""
        logger.info(f"슬랙봇 스케줄러 시작 - 매일 {schedule_time}")
        
        # 슬랙 연결 테스트
        if not self.slack_client.send_test_message():
            raise ConnectionError("슬랙 연결에 실패했습니다. 토큰을 확인해주세요.")
        
        # 스케줄 등록
        self.scheduler.schedule_daily_task(
            self.daily_paper_summary_task,
            schedule_time
        )
        
        # 다음 실행 시간 로그
        next_run = self.scheduler.get_next_run_time()
        logger.info(f"다음 실행 예정: {next_run}")
        
        # 스케줄러 실행
        self.scheduler.run_scheduler()
    
    def run_once(self):
        """한 번만 실행합니다 (테스트용)"""
        logger.info("논문 요약 작업을 한 번 실행합니다")
        self.daily_paper_summary_task()
    
    def get_statistics(self):
        """봇 통계를 출력합니다 (확장된 통계)"""
        stats = self.db_manager.get_statistics(days=30)
        
        logger.info("=== 봇 통계 (최근 30일) ===")
        logger.info(f"총 저장된 논문 수: {stats.get('total_papers', 0)}")
        logger.info(f"평균 관련성 점수: {stats.get('avg_relevance_score', 0)}/10")
        logger.info(f"높은 관련성 논문 수: {stats.get('high_relevance_count', 0)}")
        logger.info(f"관련성 비율: {stats.get('relevance_rate', 0)}%")
        
        # 카테고리 분포
        if stats.get('category_distribution'):
            logger.info("카테고리 분포:")
            for category, count in stats['category_distribution'].items():
                logger.info(f"  - {category}: {count}개")
        
        # 상위 키워드
        if stats.get('top_keywords'):
            logger.info("상위 키워드:")
            for keyword, freq in list(stats['top_keywords'].items())[:5]:
                logger.info(f"  - {keyword}: {freq}회")
        
        return stats
    
    def test_enhanced_features(self):
        """확장된 기능들을 테스트합니다"""
        logger.info("=== 확장된 기능 테스트 시작 ===")
        
        try:
            # 1. 최근 논문 1개 가져와서 확장된 요약 테스트
            papers = self.arxiv_client.search_papers(days_back=7)
            if papers:
                test_paper = papers[0]
                logger.info(f"테스트 논문: {test_paper.title}")
                
                # 확장된 요약 생성
                summary = self.summarizer.summarize_paper(test_paper)
                if summary:
                    logger.info("=== 확장된 요약 결과 ===")
                    logger.info(f"관련성 점수: {summary.relevance_score}/10")
                    logger.info(f"Swift 키워드 점수: {summary.swift_keywords_score}/10")
                    logger.info(f"예측 카테고리: {summary.category_prediction}")
                    logger.info(f"추출된 키워드: {summary.extracted_keywords[:5]}")
                    logger.info(f"기술적 요약: {summary.technical_summary[:100]}...")
                    logger.info(f"비즈니스 임팩트: {summary.business_impact[:100]}...")
                    
                    # 데이터베이스에 저장
                    self.db_manager.save_paper(test_paper)
                    self.db_manager.save_summary(summary)
                    
                    logger.info("테스트 데이터 저장 완료")
                else:
                    logger.error("요약 생성 실패")
            
            # 2. 통계 기능 테스트
            stats = self.db_manager.get_statistics(days=7)
            logger.info("=== 통계 기능 테스트 ===")
            logger.info(f"최근 7일 통계: {stats}")
            
            logger.info("=== 확장된 기능 테스트 완료 ===")
            
        except Exception as e:
            logger.error(f"확장된 기능 테스트 중 오류: {e}")

def main():
    """메인 실행 함수"""
    # 로깅 설정
    Config.setup_logging()
    
    logger.info("Swift 논문 요약 슬랙봇 시작")
    
    # 설정 정보 출력
    print("✅ 모든 필수 환경 변수가 설정되었습니다.")
    print(f"📊 검색 설정: 최대 {Config.ARXIV_MAX_RESULTS}개 논문, 최근 {Config.ARXIV_SEARCH_DAYS}일")
    print(f"🔍 필터링: 관련성 {Config.MIN_RELEVANCE_SCORE}점 이상, 일일 최대 {Config.MAX_DAILY_PAPERS}편")
    
    # 검색 키워드 출력
    if hasattr(Config, 'ARXIV_SEARCH_TERMS') and Config.ARXIV_SEARCH_TERMS:
        terms = str(Config.ARXIV_SEARCH_TERMS).split(',')
        terms_preview = [term.strip().strip('"') for term in terms[:4]]
        print(f"🔍 검색 키워드: {', '.join(terms_preview)}... (등 총 {len(terms)}개)")
    
    try:
        bot = SwiftPaperBot()
        
        # 명령행 인자 처리
        if len(sys.argv) > 1:
            command = sys.argv[1].lower()
            
            if command == "once":
                # 한 번만 실행
                bot.run_once()
            elif command == "stats":
                # 통계 출력
                bot.get_statistics()
            elif command == "test":
                # 확장된 기능 테스트
                bot.test_enhanced_features()
            elif command.startswith("schedule"):
                # 스케줄 실행 (시간 지정 가능)
                time_str = "08:00"
                if len(sys.argv) > 2:
                    time_str = sys.argv[2]
                bot.start_scheduler(time_str)
            else:
                print("사용법:")
                print("  python -m src.main once        # 한 번만 실행")
                print("  python -m src.main stats       # 통계 출력")
                print("  python -m src.main test        # 확장된 기능 테스트")
                print("  python -m src.main schedule [HH:MM]  # 스케줄 실행")
        else:
            # 기본값: 오전 8시 스케줄 실행
            bot.start_scheduler("08:00")
            
    except Exception as e:
        logger.error(f"봇 실행 중 오류 발생: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()