"""
논문 요약 서비스
OpenAI API를 사용하여 논문의 초록을 분석하고 요약을 생성합니다.
"""
import logging
from typing import Dict, Optional, List
from dataclasses import dataclass
from openai import OpenAI
import json
import re

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
    # 새로운 필드들 추가
    technical_summary: str    # 기술적 요약
    business_impact: str      # 비즈니스 임팩트
    extracted_keywords: List[str]  # 추출된 키워드
    swift_keywords_score: float    # Swift 관련 키워드 매칭 점수
    category_prediction: str       # 예측된 카테고리

class PaperSummarizer:
    """논문 요약 생성 클래스"""
    
    # Swift/iOS 관련 키워드 사전
    SWIFT_KEYWORDS = {
        'core': ['swift', 'ios', 'iphone', 'ipad', 'swiftui', 'uikit', 'objective-c', 'xcode'],
        'frameworks': ['core data', 'core animation', 'core graphics', 'foundation', 'cocoa touch'],
        'platforms': ['macos', 'watchos', 'tvos', 'visionos', 'vision pro'],
        'development': ['app store', 'apple sdk', 'ios sdk', 'mobile development', 'apple development']
    }
    
    def __init__(self, api_key: str):
        self.client = OpenAI(api_key=api_key)
    
    def summarize_paper(self, paper: Paper) -> Optional[PaperSummary]:
        """
        논문을 다중 접근법으로 요약합니다.
        
        Args:
            paper: Paper 객체
            
        Returns:
            PaperSummary 객체 또는 None (요약 실패시)
        """
        logger.info(f"논문 요약 시작: {paper.title}")
        
        try:
            # 1. 기본 요약 생성
            basic_summary = self._generate_basic_summary(paper)
            if not basic_summary:
                return None
            
            # 2. 기술적 요약 생성
            technical_summary = self._generate_technical_summary(paper)
            
            # 3. 비즈니스 임팩트 분석
            business_impact = self._analyze_business_impact(paper)
            
            # 4. 키워드 추출
            extracted_keywords = self._extract_keywords(paper)
            
            # 5. Swift 키워드 매칭 점수 계산
            swift_keywords_score = self._calculate_swift_keywords_score(paper, extracted_keywords)
            
            # 6. 카테고리 예측
            category_prediction = self._predict_category(paper, extracted_keywords)
            
            return PaperSummary(
                paper_id=paper.id,
                one_line_summary=basic_summary.get("one_line_summary", ""),
                key_points=basic_summary.get("key_points", ""),
                detailed_summary=basic_summary.get("detailed_summary", ""),
                relevance_score=float(basic_summary.get("relevance_score", 0)),
                technical_summary=technical_summary,
                business_impact=business_impact,
                extracted_keywords=extracted_keywords,
                swift_keywords_score=swift_keywords_score,
                category_prediction=category_prediction
            )
            
        except Exception as e:
            logger.error(f"논문 요약 중 오류 발생: {e}")
            return None
    
    def _generate_basic_summary(self, paper: Paper) -> Optional[Dict]:
        """기본 요약을 생성합니다"""
        prompt = self._create_summary_prompt(paper)
        
        response = self.client.chat.completions.create(
            model="gpt-4o-mini",
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
        
        result = response.choices[0].message.content
        return self._parse_summary_response(result)
    
    def _generate_technical_summary(self, paper: Paper) -> str:
        """기술적 요약을 생성합니다"""
        try:
            prompt = f"""
다음 논문의 기술적 측면을 분석해주세요:

제목: {paper.title}
초록: {paper.abstract}

기술적 요약 (100자 이내):
- 사용된 기술/방법론
- 알고리즘이나 아키텍처
- 성능 지표나 결과
"""
            
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.2,
                max_tokens=200
            )
            
            return response.choices[0].message.content.strip()
        except Exception as e:
            logger.error(f"기술적 요약 생성 실패: {e}")
            return "기술적 요약 생성 실패"
    
    def _analyze_business_impact(self, paper: Paper) -> str:
        """비즈니스 임팩트를 분석합니다"""
        try:
            prompt = f"""
다음 논문이 Swift/iOS 개발 비즈니스에 미치는 영향을 분석해주세요:

제목: {paper.title}
초록: {paper.abstract}

비즈니스 임팩트 (100자 이내):
- 개발 생산성에 미치는 영향
- 사용자 경험 개선 가능성
- 시장 경쟁력 향상 요소
"""
            
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.2,
                max_tokens=200
            )
            
            return response.choices[0].message.content.strip()
        except Exception as e:
            logger.error(f"비즈니스 임팩트 분석 실패: {e}")
            return "비즈니스 임팩트 분석 실패"
    
    def _extract_keywords(self, paper: Paper) -> List[str]:
        """논문에서 키워드를 추출합니다"""
        try:
            # 제목과 초록에서 키워드 추출
            text = f"{paper.title} {paper.abstract}".lower()
            
            # 기본적인 키워드 추출 (단어 빈도 기반)
            words = re.findall(r'\b[a-zA-Z]{3,}\b', text)
            
            # 불용어 제거
            stop_words = {'the', 'and', 'for', 'are', 'but', 'not', 'you', 'all', 'can', 'had', 'her', 'was', 'one', 'our', 'out', 'day', 'get', 'has', 'him', 'his', 'how', 'man', 'new', 'now', 'old', 'see', 'two', 'way', 'who', 'boy', 'did', 'its', 'let', 'put', 'say', 'she', 'too', 'use'}
            
            # 빈도 계산
            word_freq = {}
            for word in words:
                if word not in stop_words and len(word) > 3:
                    word_freq[word] = word_freq.get(word, 0) + 1
            
            # 상위 10개 키워드 추출
            top_keywords = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)[:10]
            
            return [keyword for keyword, freq in top_keywords]
            
        except Exception as e:
            logger.error(f"키워드 추출 실패: {e}")
            return []
    
    def _calculate_swift_keywords_score(self, paper: Paper, extracted_keywords: List[str]) -> float:
        """Swift 관련 키워드 매칭 점수를 계산합니다"""
        try:
            text = f"{paper.title} {paper.abstract}".lower()
            total_score = 0.0
            max_score = 0.0
            
            for category, keywords in self.SWIFT_KEYWORDS.items():
                category_score = 0.0
                category_weight = {'core': 3.0, 'frameworks': 2.0, 'platforms': 2.0, 'development': 1.0}
                
                for keyword in keywords:
                    if keyword in text:
                        category_score += text.count(keyword) * category_weight.get(category, 1.0)
                
                total_score += category_score
                max_score += len(keywords) * category_weight.get(category, 1.0)
            
            # 추출된 키워드에서도 매칭 확인
            for keyword in extracted_keywords:
                for category, swift_keywords in self.SWIFT_KEYWORDS.items():
                    if keyword in swift_keywords:
                        total_score += 1.0
            
            # 0-10 점수로 정규화
            if max_score > 0:
                normalized_score = min(10.0, (total_score / max_score) * 10)
            else:
                normalized_score = 0.0
                
            return round(normalized_score, 1)
            
        except Exception as e:
            logger.error(f"Swift 키워드 점수 계산 실패: {e}")
            return 0.0
    
    def _predict_category(self, paper: Paper, extracted_keywords: List[str]) -> str:
        """논문의 카테고리를 예측합니다"""
        try:
            categories = {
                'Mobile Development': ['mobile', 'app', 'application', 'device', 'smartphone'],
                'User Interface': ['ui', 'interface', 'design', 'user', 'experience', 'interaction'],
                'Machine Learning': ['learning', 'neural', 'model', 'algorithm', 'prediction', 'classification'],
                'Security': ['security', 'privacy', 'encryption', 'authentication', 'protection'],
                'Performance': ['performance', 'optimization', 'efficiency', 'speed', 'memory'],
                'System': ['system', 'architecture', 'framework', 'platform', 'infrastructure']
            }
            
            text = f"{paper.title} {paper.abstract}".lower()
            category_scores = {}
            
            for category, keywords in categories.items():
                score = 0
                for keyword in keywords:
                    score += text.count(keyword)
                    if keyword in extracted_keywords:
                        score += 2  # 추출된 키워드에 가중치
                
                category_scores[category] = score
            
            # 가장 높은 점수의 카테고리 반환
            if category_scores:
                predicted_category = max(category_scores.keys(), key=lambda k: category_scores[k])
                if category_scores[predicted_category] > 0:
                    return predicted_category
            
            return "General"
            
        except Exception as e:
            logger.error(f"카테고리 예측 실패: {e}")
            return "Unknown"
    
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
            return json.loads(response)
        except json.JSONDecodeError as e:
            logger.error(f"JSON 파싱 오류: {e}")
            return None
    
    def is_relevant_paper(self, summary: PaperSummary, min_score: float = 5.0) -> bool:
        """논문이 Swift/iOS 개발과 관련이 있는지 판단합니다"""
        return summary.relevance_score >= min_score
    
    def get_summary_statistics(self, summaries: List[PaperSummary]) -> Dict:
        """요약 통계를 생성합니다"""
        if not summaries:
            return {}
        
        relevance_scores = [s.relevance_score for s in summaries]
        swift_keyword_scores = [s.swift_keywords_score for s in summaries]
        
        # 카테고리 분포
        category_dist = {}
        for summary in summaries:
            category = summary.category_prediction
            category_dist[category] = category_dist.get(category, 0) + 1
        
        return {
            'total_papers': len(summaries),
            'avg_relevance_score': round(sum(relevance_scores) / len(relevance_scores), 2),
            'max_relevance_score': max(relevance_scores),
            'min_relevance_score': min(relevance_scores),
            'avg_swift_keywords_score': round(sum(swift_keyword_scores) / len(swift_keyword_scores), 2),
            'category_distribution': category_dist,
            'high_relevance_count': len([s for s in summaries if s.relevance_score >= 8.0])
        } 