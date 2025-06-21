"""
스케줄링 모듈
매일 정해진 시간에 논문 요약 작업을 실행합니다.
"""
import logging
import schedule
import time
from datetime import datetime
from typing import Callable

logger = logging.getLogger(__name__)

class TaskScheduler:
    """작업 스케줄러 클래스"""
    
    def __init__(self):
        self.is_running = False
    
    def schedule_daily_task(self, task_func: Callable, time_str: str = "08:00"):
        """
        매일 정해진 시간에 실행할 작업을 스케줄링합니다.
        
        Args:
            task_func: 실행할 함수
            time_str: 실행 시간 (HH:MM 형식)
        """
        schedule.clear()  # 기존 스케줄 제거
        schedule.every().day.at(time_str).do(task_func)
        logger.info(f"매일 {time_str}에 논문 요약 작업이 예약되었습니다")
    
    def run_scheduler(self):
        """스케줄러를 실행합니다 (무한 루프)"""
        self.is_running = True
        logger.info("스케줄러 시작")
        
        try:
            while self.is_running:
                schedule.run_pending()
                time.sleep(60)  # 1분마다 체크
        except KeyboardInterrupt:
            logger.info("스케줄러가 사용자에 의해 중단되었습니다")
        except Exception as e:
            logger.error(f"스케줄러 실행 중 오류: {e}")
        finally:
            self.is_running = False
            logger.info("스케줄러 종료")
    
    def stop_scheduler(self):
        """스케줄러를 중단합니다"""
        self.is_running = False
        logger.info("스케줄러 중단 요청")
    
    def run_task_now(self, task_func: Callable):
        """작업을 즉시 실행합니다 (테스트용)"""
        logger.info("작업을 즉시 실행합니다")
        try:
            task_func()
            logger.info("작업 실행 완료")
        except Exception as e:
            logger.error(f"작업 실행 중 오류: {e}")
    
    def get_next_run_time(self) -> str:
        """다음 실행 예정 시간을 반환합니다"""
        jobs = schedule.get_jobs()
        if jobs:
            next_run = jobs[0].next_run
            if next_run:
                return next_run.strftime("%Y-%m-%d %H:%M:%S")
        return "예약된 작업이 없습니다" 