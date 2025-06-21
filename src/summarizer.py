"""
논문 요약 서비스
OpenAI API를 사용하여 논문의 초록을 분석하고 요약을 생성합니다.
"""
import logging
from typing import Dict, Optional
from dataclasses import dataclass
from openai import OpenAI

from .arxiv_client import Paper

logger = logging.getLogger(__name__)

@dataclass
class PaperSummary:
    """논문 요약 정보를 담는 데이터 클래스"""
    paper_id: str
    one_line_summary: str  # 1줄 요약
    key_points: str        # 핵심 내용
    detailed_summary: str  # 상세 요약
    relevance_score: float # Swift/iOS 관련성 점수 (0-10)

class PaperSummarizer:
    """논문 요약 생성 클래스"""
    
    def __init__(self, api_key: str):
        self.client = OpenAI(api_key=api_key)
    
    def summarize_paper(self, paper: Paper) -> Optional[PaperSummary]:
        """
        논문을 요약합니다.
        
        Args:
            paper: Paper 객체
            
        Returns:
            PaperSummary 객체 또는 None (요약 실패시)
        """
        logger.info(f"논문 요약 시작: {paper.title}")
        
        try:
            # 요약 프롬프트 생성
            prompt = self._create_summary_prompt(paper)
            
            # OpenAI API 호출
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",  # 비용 효율적인 모델 사용
                messages=[
                    {
                        "role": "system",
                        "content": """당신은 Swift와 iOS 개발 전문가입니다. 
                        논문을 분석하여 Swift/iOS 개발자들에게 유용한 정보를 추출하는 것이 목표입니다.
                        응답은 반드시 JSON 형식으로 해주세요."""
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.3,
                max_tokens=1000,
                response_format={"type": "json_object"}
            )
            
            # 응답 파싱
            result = response.choices[0].message.content
            summary_data = self._parse_summary_response(result)
            
            if summary_data:
                return PaperSummary(
                    paper_id=paper.id,
                    one_line_summary=summary_data.get("one_line_summary", ""),
                    key_points=summary_data.get("key_points", ""),
                    detailed_summary=summary_data.get("detailed_summary", ""),
                    relevance_score=float(summary_data.get("relevance_score", 0))
                )
            
            return None
            
        except Exception as e:
            logger.error(f"논문 요약 중 오류 발생: {e}")
            return None
    
    def _create_summary_prompt(self, paper: Paper) -> str:
        """요약을 위한 프롬프트를 생성합니다"""
        authors_str = ", ".join(paper.authors[:3])  # 최대 3명까지만
        if len(paper.authors) > 3:
            authors_str += " 외"
        
        return f"""
다음 논문을 분석하여 Swift/iOS 개발자들에게 유용한 정보를 추출해주세요:

제목: {paper.title}
저자: {authors_str}
초록: {paper.abstract}
카테고리: {', '.join(paper.categories)}

다음 JSON 형식으로 응답해주세요:
{{
    "one_line_summary": "논문의 핵심 내용을 한 줄로 요약 (50자 이내)",
    "key_points": "Swift/iOS 개발과 관련된 주요 포인트들 (3-5개 불릿 포인트)",
    "detailed_summary": "논문의 상세한 요약 및 Swift/iOS 개발에 미치는 영향 (200자 이내)",
    "relevance_score": "Swift/iOS 개발과의 관련성 점수 (0-10, 숫자만)"
}}

만약 이 논문이 Swift/iOS 개발과 직접적인 관련이 없다면 relevance_score를 낮게 주세요.
"""
    
    def _parse_summary_response(self, response: str) -> Optional[Dict]:
        """OpenAI 응답을 파싱합니다"""
        try:
            import json
            return json.loads(response)
        except json.JSONDecodeError as e:
            logger.error(f"JSON 파싱 오류: {e}")
            return None
    
    def is_relevant_paper(self, summary: PaperSummary, min_score: float = 5.0) -> bool:
        """논문이 Swift/iOS 개발과 관련이 있는지 판단합니다"""
        return summary.relevance_score >= min_score 