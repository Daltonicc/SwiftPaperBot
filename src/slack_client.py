"""
슬랙 클라이언트 모듈
논문 요약을 슬랙 채널로 전송합니다.
"""
import logging
from typing import List, Dict, Optional
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from datetime import datetime

from .summarizer import PaperSummary
from .arxiv_client import Paper

logger = logging.getLogger(__name__)

class SlackClient:
    """슬랙 클라이언트 클래스"""
    
    def __init__(self, token: str, channel: str):
        self.client = WebClient(token=token)
        self.channel = channel
    
    def send_paper_summaries(self, summaries: List[PaperSummary], papers: List[Paper], stats: Optional[Dict] = None) -> bool:
        """
        논문 요약들을 슬랙으로 전송합니다 (확장된 정보 포함)
        
        Args:
            summaries: 전송할 논문 요약 리스트
            papers: 논문 정보 리스트
            stats: 통계 정보 (선택사항)
            
        Returns:
            전송 성공 여부
        """
        logger.info(f"슬랙으로 {len(summaries)}개 논문 요약 전송 시작")
        
        try:
            if not summaries:
                # 빈 메시지 전송 (관련성 높은 논문이 없을 때)
                return self._send_empty_message(stats)
            
            # 헤더 메시지 생성
            header_message = self._create_header_message(len(summaries), stats)
            
            # 헤더 전송
            response = self.client.chat_postMessage(
                channel=self.channel,
                text=header_message,
                mrkdwn=True
            )
            
            # 각 논문 요약 전송
            for i, (summary, paper) in enumerate(zip(summaries, papers), 1):
                message = self._create_enhanced_paper_message(summary, paper, i)
                
                response = self.client.chat_postMessage(
                    channel=self.channel,
                    text=message,
                    mrkdwn=True
                )
            
            # 통계 정보가 있으면 푸터 메시지 전송
            if stats:
                footer_message = self._create_statistics_message(stats)
                response = self.client.chat_postMessage(
                    channel=self.channel,
                    text=footer_message,
                    mrkdwn=True
                )
            
            logger.info("슬랙 메시지 전송 완료")
            return True
            
        except SlackApiError as e:
            logger.error(f"슬랙 API 오류: {e.response['error']}")
            return False
        except Exception as e:
            logger.error(f"슬랙 전송 중 오류 발생: {e}")
            return False
    
    def _send_empty_message(self, stats: Optional[Dict] = None) -> bool:
        """관련성 높은 논문이 없을 때 전송하는 메시지"""
        try:
            today = datetime.now().strftime("%Y년 %m월 %d일")
            
            message = f"""📚 *Swift/iOS 논문 요약 - {today}*

🔍 *검색 결과*
오늘은 관련성 높은 Swift/iOS 논문이 발견되지 않았습니다.

"""
            
            if stats:
                message += f"""📊 *검색 통계*
• 총 검색된 논문: {stats.get('total_papers', 0)}개
• 평균 관련성 점수: {stats.get('avg_relevance_score', 0)}/10점
• 높은 관련성 논문 (8점 이상): {stats.get('high_relevance_count', 0)}개

"""
            
            message += "내일 더 좋은 논문으로 찾아뵙겠습니다! 🚀"
            
            response = self.client.chat_postMessage(
                channel=self.channel,
                text=message,
                mrkdwn=True
            )
            
            return True
            
        except Exception as e:
            logger.error(f"빈 메시지 전송 실패: {e}")
            return False
    
    def _create_header_message(self, count: int, stats: Optional[Dict] = None) -> str:
        """헤더 메시지를 생성합니다"""
        today = datetime.now().strftime("%Y년 %m월 %d일")
        
        message = f"""📚 *Swift/iOS 논문 요약 - {today}*

🎯 *오늘의 추천 논문 {count}편*

"""
        
        if stats:
            message += f"""📊 *검색 통계*
• 총 검색된 논문: {stats.get('total_papers', 0)}개
• 평균 관련성 점수: {stats.get('avg_relevance_score', 0)}/10점
• 높은 관련성 논문: {stats.get('high_relevance_count', 0)}개
• 관련성 비율: {stats.get('relevance_rate', 0)}%

"""
        
        return message
    
    def _create_enhanced_paper_message(self, summary: PaperSummary, paper: Paper, index: int) -> str:
        """확장된 논문 메시지를 생성합니다"""
        # 발행일 포맷팅
        published_date = paper.published.strftime("%Y-%m-%d")
        
        # 저자 정보 (최대 3명)
        authors = ", ".join(paper.authors[:3])
        if len(paper.authors) > 3:
            authors += f" 외 {len(paper.authors) - 3}명"
        
        # 키워드 정보
        keywords_str = ""
        if summary.extracted_keywords:
            top_keywords = summary.extracted_keywords[:5]  # 상위 5개만
            keywords_str = f"\n🏷️ *키워드*: {', '.join(top_keywords)}"
        
        # 카테고리 이모지 매핑
        category_emojis = {
            'Mobile Development': '📱',
            'User Interface': '🎨',
            'Machine Learning': '🤖',
            'Security': '🔒',
            'Performance': '⚡',
            'System': '🏗️',
            'General': '📄'
        }
        
        category_emoji = category_emojis.get(summary.category_prediction, '📄')
        
        message = f"""
---

## {index}. {paper.title}

👥 *저자*: {authors}
📅 *발행일*: {published_date}
⭐ *관련성*: {summary.relevance_score}/10점
🎯 *Swift 키워드 매칭*: {summary.swift_keywords_score}/10점
{category_emoji} *카테고리*: {summary.category_prediction}{keywords_str}

### 📝 한줄 요약
{summary.one_line_summary}

### 🔍 주요 내용
{summary.key_points}

### 📋 상세 요약
{summary.detailed_summary}

### 🔧 기술적 분석
{summary.technical_summary}

### 💼 비즈니스 임팩트
{summary.business_impact}

🔗 *논문 링크*: {paper.url}
📄 *PDF*: {paper.pdf_url}
"""
        
        return message
    
    def _create_statistics_message(self, stats: Dict) -> str:
        """통계 메시지를 생성합니다"""
        message = """
---

📈 *상세 통계 정보*

"""
        
        # 카테고리 분포
        if stats.get('category_distribution'):
            message += "📊 *카테고리 분포*\n"
            for category, count in stats['category_distribution'].items():
                message += f"  • {category}: {count}개\n"
            message += "\n"
        
        # 상위 키워드
        if stats.get('top_keywords'):
            message += "🏷️ *인기 키워드*\n"
            for keyword, freq in list(stats['top_keywords'].items())[:5]:
                message += f"  • {keyword}: {freq}회\n"
            message += "\n"
        
        # 일별 통계 (최근 3일)
        if stats.get('daily_breakdown'):
            message += "📅 *최근 활동*\n"
            for daily in stats['daily_breakdown'][:3]:
                message += f"  • {daily['date']}: {daily['total_papers']}개 논문, {daily['relevant_papers']}개 관련\n"
            message += "\n"
        
        message += "---\n"
        message += "🤖 *SwiftPaperBot* | 매일 아침 8시에 최신 Swift/iOS 논문을 전달합니다"
        
        return message
    
    def send_test_message(self) -> bool:
        """테스트 메시지를 전송합니다"""
        try:
            message = "🧪 SlackBot 연결 테스트 - 정상 작동 중입니다!"
            
            response = self.client.chat_postMessage(
                channel=self.channel,
                text=message
            )
            
            logger.info("테스트 메시지 전송 성공")
            return True
            
        except SlackApiError as e:
            logger.error(f"슬랙 테스트 메시지 전송 실패: {e.response['error']}")
            return False
    
    def send_error_notification(self, error_message: str) -> bool:
        """오류 알림을 전송합니다"""
        try:
            message = f"""⚠️ *SwiftPaperBot 오류 발생*

{error_message}

시스템 관리자에게 문의해주세요."""
            
            response = self.client.chat_postMessage(
                channel=self.channel,
                text=message,
                mrkdwn=True
            )
            
            logger.info("오류 알림 전송 완료")
            return True
            
        except SlackApiError as e:
            logger.error(f"오류 알림 전송 실패: {e.response['error']}")
            return False 