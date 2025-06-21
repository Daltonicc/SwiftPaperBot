"""
설정 관리 모듈
환경 변수를 로드하고 애플리케이션 설정을 관리합니다.
"""
import os
import logging
from typing import List
from dotenv import load_dotenv

# 프로젝트 루트 디렉토리 찾기
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
config_path = os.path.join(project_root, 'config.env')

# 환경 변수 로드 (명시적 경로 지정)
load_dotenv(config_path)

class Config:
    """애플리케이션 설정 클래스"""
    
    # Slack 설정
    SLACK_BOT_TOKEN = os.getenv("SLACK_BOT_TOKEN")
    SLACK_CHANNEL = os.getenv("SLACK_CHANNEL", "#general")
    
    # OpenAI 설정
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    
    # arXiv 설정
    ARXIV_MAX_RESULTS = int(os.getenv("ARXIV_MAX_RESULTS", "10"))
    ARXIV_SEARCH_TERMS = os.getenv(
        "ARXIV_SEARCH_TERMS", 
        "Swift,iOS,iPhone,iPad,SwiftUI,Objective-C,UIKit,Core Data"
    ).split(",")
    
    # 데이터베이스 설정
    DATABASE_PATH = os.getenv("DATABASE_PATH", "./data/papers.db")
    
    # 로깅 설정
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    LOG_FILE = os.getenv("LOG_FILE", "./logs/slackbot.log")
    
    @classmethod
    def validate_config(cls) -> bool:
        """필수 설정 값들이 모두 설정되어 있는지 확인"""
        required_configs = [
            cls.SLACK_BOT_TOKEN,
            cls.OPENAI_API_KEY,
        ]
        
        missing_configs = [
            config for config in required_configs if not config
        ]
        
        if missing_configs:
            logging.error(f"필수 설정이 누락되었습니다: {missing_configs}")
            # 디버깅을 위해 실제 값들 출력
            logging.error(f"SLACK_BOT_TOKEN: {cls.SLACK_BOT_TOKEN}")
            logging.error(f"OPENAI_API_KEY: {cls.OPENAI_API_KEY}")
            logging.error(f"config.env 경로: {config_path}")
            logging.error(f"config.env 존재 여부: {os.path.exists(config_path)}")
            return False
        
        return True
    
    @classmethod
    def setup_logging(cls):
        """로깅 설정"""
        # 로그 디렉토리 생성
        log_dir = os.path.dirname(cls.LOG_FILE)
        if log_dir and not os.path.exists(log_dir):
            os.makedirs(log_dir)
        
        logging.basicConfig(
            level=getattr(logging, cls.LOG_LEVEL.upper()),
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(cls.LOG_FILE, encoding='utf-8'),
                logging.StreamHandler()
            ]
        ) 