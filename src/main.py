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
from .slack_client import SlackBot
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
        self.arxiv_client = ArxivClient(max_results=Config.ARXIV_MAX_RESULTS)
        self.summarizer = PaperSummarizer(Config.OPENAI_API_KEY)
        self.slack_bot = SlackBot(Config.SLACK_BOT_TOKEN, Config.SLACK_CHANNEL)
        self.db_manager = DatabaseManager(Config.DATABASE_PATH)
        self.scheduler = TaskScheduler()
        
        logger.info("SwiftPaperBot 초기화 완료")
    
    def daily_paper_summary_task(self):
        """매일 실행되는 논문 요약 작업"""
        logger.info("=== 일일 논문 요약 작업 시작 ===")
        
        try:
            # 1. arXiv에서 새로운 논문 검색 (최근 7일)
            logger.info("arXiv에서 논문 검색 중... (최근 7일)")
            papers = self.arxiv_client.search_papers(
                search_terms=Config.ARXIV_SEARCH_TERMS,
                days_back=7  # 30일에서 7일로 변경
            )
            
            if not papers:
                logger.info("새로운 논문이 없습니다")
                self.slack_bot.send_daily_summary([])
                return
            
            logger.info(f"{len(papers)}개의 논문을 찾았습니다")
            
            # 2. 논문 필터링 및 요약 생성
            relevant_papers = []
            
            for paper in papers:
                # 이미 전송된 논문인지 확인
                if self.db_manager.is_paper_sent_today(paper.id):
                    logger.info(f"이미 전송된 논문 건너뛰기: {paper.title}")
                    continue
                
                # 논문 정보 저장
                self.db_manager.save_paper(paper)
                
                # 논문 요약 생성
                logger.info(f"논문 요약 생성 중: {paper.title}")
                summary = self.summarizer.summarize_paper(paper)
                
                if summary and self.summarizer.is_relevant_paper(summary, min_score=7.0):  # 7점 이상으로 변경
                    # 요약 저장
                    self.db_manager.save_summary(summary)
                    relevant_papers.append((paper, summary))
                    logger.info(f"관련성 높은 논문 발견: {paper.title} (점수: {summary.relevance_score})")
                else:
                    score = summary.relevance_score if summary else "N/A"
                    logger.info(f"관련성 낮은 논문 제외: {paper.title} (점수: {score})")
            
            # 3. 슬랙으로 요약 전송
            if relevant_papers:
                logger.info(f"{len(relevant_papers)}개의 관련 논문을 슬랙으로 전송합니다 (7점 이상)")
                success = self.slack_bot.send_daily_summary(relevant_papers)
                
                if success:
                    # 전송 성공 시 전송 기록 저장
                    for paper, _ in relevant_papers:
                        self.db_manager.mark_paper_as_sent(paper.id)
                    logger.info("슬랙 전송 및 기록 저장 완료")
                else:
                    logger.error("슬랙 전송 실패")
            else:
                logger.info("관련성 높은 논문이 없어 빈 메시지를 전송합니다 (7점 이상 기준)")
                self.slack_bot.send_daily_summary([])
            
            # 4. 데이터베이스 정리 (주 1회)
            if datetime.now().weekday() == 0:  # 월요일
                logger.info("주간 데이터베이스 정리 실행")
                self.db_manager.cleanup_old_data(days=30)
            
        except Exception as e:
            logger.error(f"일일 논문 요약 작업 중 오류 발생: {e}")
            self._send_error_notification(str(e))
        
        logger.info("=== 일일 논문 요약 작업 완료 ===")
    
    def _send_error_notification(self, error_message: str):
        """오류 발생 시 슬랙으로 알림을 전송합니다"""
        try:
            message = f"""
🚨 **Swift 논문 봇 오류 발생**

📅 시간: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
❌ 오류: {error_message}

시스템 관리자에게 문의해주세요.
"""
            self.slack_bot._send_message(message)
        except Exception as e:
            logger.error(f"오류 알림 전송 실패: {e}")
    
    def start_scheduler(self, schedule_time: str = "08:00"):
        """스케줄러를 시작합니다"""
        logger.info(f"슬랙봇 스케줄러 시작 - 매일 {schedule_time}")
        
        # 슬랙 연결 테스트
        if not self.slack_bot.test_connection():
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
        """봇 통계를 출력합니다"""
        stats = self.db_manager.get_statistics()
        logger.info("=== 봇 통계 ===")
        logger.info(f"총 저장된 논문 수: {stats.get('total_papers', 0)}")
        logger.info(f"총 생성된 요약 수: {stats.get('total_summaries', 0)}")
        logger.info(f"이번 달 전송된 논문 수: {stats.get('sent_this_month', 0)}")
        return stats

def main():
    """메인 실행 함수"""
    # 로깅 설정
    Config.setup_logging()
    
    logger.info("Swift 논문 요약 슬랙봇 시작")
    
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
                print("  python -m src.main schedule [HH:MM]  # 스케줄 실행")
        else:
            # 기본값: 오전 8시 스케줄 실행
            bot.start_scheduler()
            
    except KeyboardInterrupt:
        logger.info("사용자에 의해 중단됨")
    except Exception as e:
        logger.error(f"봇 실행 중 오류 발생: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()