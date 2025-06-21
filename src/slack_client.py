"""
슬랙 봇 클라이언트
논문 요약 정보를 슬랙 채널로 전송합니다.
"""
import logging
from typing import List
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

from .arxiv_client import Paper
from .summarizer import PaperSummary

logger = logging.getLogger(__name__)

class SlackBot:
    """슬랙 봇 클래스"""
    
    def __init__(self, token: str, channel: str):
        self.client = WebClient(token=token)
        self.channel = channel
    
    def send_daily_summary(self, papers_with_summaries: List[tuple[Paper, PaperSummary]]) -> bool:
        """
        일일 논문 요약을 슬랙으로 전송합니다.
        
        Args:
            papers_with_summaries: (Paper, PaperSummary) 튜플의 리스트
            
        Returns:
            전송 성공 여부
        """
        logger.info(f"슬랙으로 {len(papers_with_summaries)}개 논문 요약 전송 시작")
        
        try:
            if not papers_with_summaries:
                return self._send_no_papers_message()
            
            # 헤더 메시지 전송
            header_message = self._create_header_message(len(papers_with_summaries))
            self._send_message(header_message)
            
            # 각 논문 요약 전송
            for paper, summary in papers_with_summaries:
                message = self._create_paper_message(paper, summary)
                self._send_message(message)
            
            # 푸터 메시지 전송
            footer_message = self._create_footer_message()
            self._send_message(footer_message)
            
            logger.info("슬랙 메시지 전송 완료")
            return True
            
        except Exception as e:
            logger.error(f"슬랙 메시지 전송 중 오류 발생: {e}")
            return False
    
    def _send_message(self, message: str) -> None:
        """슬랙 메시지를 전송합니다"""
        try:
            self.client.chat_postMessage(
                channel=self.channel,
                text=message,
                mrkdwn=True  # 슬랙 마크다운 활성화
            )
        except SlackApiError as e:
            logger.error(f"슬랙 API 오류: {e.response['error']}")
            raise
    
    def _create_header_message(self, paper_count: int) -> str:
        """헤더 메시지를 생성합니다"""
        from datetime import datetime
        
        today = datetime.now().strftime("%Y년 %m월 %d일")
        
        return f"""
🍎 *Swift & iOS 논문 데일리 요약* 📚
📅 {today}

오늘 arXiv에 새로 올라온 Swift/iOS 관련 논문 *{paper_count}편*을 요약해드립니다!

---
"""
    
    def _create_paper_message(self, paper: Paper, summary: PaperSummary) -> str:
        """개별 논문 메시지를 생성합니다"""
        authors_str = ", ".join(paper.authors[:2])  # 최대 2명까지만
        if len(paper.authors) > 2:
            authors_str += f" 외 {len(paper.authors) - 2}명"
        
        # 관련성 점수에 따른 이모지
        relevance_emoji = "🔥" if summary.relevance_score >= 8 else "⭐"
        
        message = f"""
{relevance_emoji} *{paper.title}*

👨‍💻 *저자*: {authors_str}
📊 *관련성*: {summary.relevance_score}/10

💡 *한줄요약*: {summary.one_line_summary}

🔍 *핵심 내용*:
{summary.key_points}

📝 *상세 요약*:
{summary.detailed_summary}

🔗 *논문 링크*: <{paper.pdf_url}|논문 보기>
📅 *발행일*: {paper.published_date.strftime("%Y-%m-%d")}

---
"""
        return message
    
    def _create_footer_message(self) -> str:
        """푸터 메시지를 생성합니다"""
        return """
🤖 이 요약은 AI가 자동으로 생성한 것입니다.
더 자세한 내용은 논문 링크를 통해 확인해주세요!

*Happy coding!* 🚀
"""
    
    def _send_no_papers_message(self) -> bool:
        """새로운 논문이 없을 때의 메시지를 전송합니다"""
        from datetime import datetime
        
        today = datetime.now().strftime("%Y년 %m월 %d일")
        
        message = f"""
🍎 *Swift & iOS 논문 데일리 요약* 📚
📅 {today}

오늘은 새로운 Swift/iOS 관련 논문이 없습니다. 📭

내일 또 좋은 논문으로 찾아뵙겠습니다! 🤖
"""
        
        try:
            self._send_message(message)
            return True
        except Exception as e:
            logger.error(f"빈 메시지 전송 실패: {e}")
            return False
    
    def test_connection(self) -> bool:
        """슬랙 연결을 테스트합니다"""
        try:
            response = self.client.auth_test()
            logger.info(f"슬랙 연결 성공: {response['user']}")
            return True
        except SlackApiError as e:
            logger.error(f"슬랙 연결 실패: {e.response['error']}")
            return False 