# Swift & iOS 논문 요약 슬랙봇 🍎📚

arXiv에서 Swift와 iOS 관련 논문을 자동으로 수집하고, AI를 활용하여 요약한 후 매일 아침 슬랙으로 전달하는 봇입니다.

## 주요 기능

- 🔍 **자동 논문 검색**: arXiv에서 Swift/iOS 관련 최신 논문을 매일 검색
- 🤖 **AI 기반 요약**: OpenAI GPT를 활용하여 논문의 핵심 내용을 한국어로 요약
- 📱 **슬랙 알림**: 매일 아침 8시에 요약된 논문 정보를 슬랙으로 전송
- 🗄️ **중복 방지**: 이미 전송된 논문은 재전송하지 않음
- 📊 **관련성 필터링**: Swift/iOS 개발과의 관련성을 평가하여 유용한 논문만 선별

## 🚀 GitHub Actions를 사용한 자동 실행 (추천)

### 1. GitHub 리포지토리 생성 및 코드 업로드

1. GitHub에서 새 리포지토리 생성
2. 이 프로젝트를 리포지토리에 업로드

```bash
git init
git add .
git commit -m "Initial commit: Swift 논문 요약 슬랙봇"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/SwiftThesisSlackBot.git
git push -u origin main
```

### 2. GitHub Secrets 설정

GitHub 리포지토리 → Settings → Secrets and variables → Actions → "New repository secret"

다음 3개의 Secret을 추가하세요:

| Secret Name | Value | 설명 |
|-------------|--------|------|
| `SLACK_BOT_TOKEN` | `xoxb-your-slack-bot-token` | 슬랙 봇 토큰 |
| `SLACK_CHANNEL` | `#general` | 슬랙 채널명 |
| `OPENAI_API_KEY` | `sk-your-openai-api-key` | OpenAI API 키 |

### 3. 자동 실행 확인

- **자동 실행**: 매일 오전 8시 (한국 시간)
- **수동 실행**: GitHub → Actions → "Swift 논문 요약 봇 자동 실행" → "Run workflow"
- **실행 로그**: Actions 탭에서 실행 결과 확인 가능

### 4. GitHub Actions 장점

- ✅ **완전 무료** (월 2000분 제한, 충분함)
- ✅ **서버 불필요** (GitHub 서버에서 실행)
- ✅ **24시간 자동 실행**
- ✅ **안정적인 실행 환경**
- ✅ **실행 로그 자동 기록**

## 📱 로컬 실행 방법

### 설치 방법

#### 1. 필요한 패키지 설치

```bash
pip install -r requirements.txt
```

#### 2. 환경 변수 설정

`config.env.example` 파일을 복사하여 `config.env` 파일을 생성하고, 다음 값들을 설정하세요:

```env
# Slack Bot Configuration
SLACK_BOT_TOKEN=xoxb-your-slack-bot-token
SLACK_CHANNEL=#your-channel-name

# OpenAI Configuration
OPENAI_API_KEY=your-openai-api-key

# arXiv Configuration (옵션)
ARXIV_MAX_RESULTS=10
ARXIV_SEARCH_TERMS=Swift,iOS,iPhone,iPad,SwiftUI,Objective-C,UIKit,Core Data

# Database Configuration (옵션)
DATABASE_PATH=./data/papers.db

# Logging Configuration (옵션)
LOG_LEVEL=INFO
LOG_FILE=./logs/slackbot.log
```

#### 3. 필요한 API 키 발급

##### Slack Bot Token 발급
1. [Slack API 사이트](https://api.slack.com/)에서 새 앱 생성
2. "OAuth & Permissions"에서 다음 권한 추가:
   - `chat:write`
   - `chat:write.public`
3. Bot Token을 복사하여 `SLACK_BOT_TOKEN`에 설정
4. 봇을 원하는 채널에 초대

##### OpenAI API Key 발급
1. [OpenAI 플랫폼](https://platform.openai.com/)에서 API 키 생성
2. 생성된 키를 `OPENAI_API_KEY`에 설정

### 사용 방법

#### 로컬에서 테스트 실행

```bash
# 한 번만 실행 (테스트용)
python -m src.main once

# 통계 확인
python -m src.main stats

# 스케줄 실행 (매일 자동 실행)
python -m src.main schedule 08:00
```

## 프로젝트 구조

```
SwiftThesisSlackBot/
├── .github/workflows/
│   └── daily-paper-summary.yml  # GitHub Actions 워크플로우
├── src/
│   ├── __init__.py
│   ├── config.py          # 환경 변수 및 설정 관리
│   ├── arxiv_client.py    # arXiv API 클라이언트
│   ├── summarizer.py      # AI 기반 논문 요약
│   ├── slack_client.py    # 슬랙 봇 클라이언트
│   ├── database.py        # SQLite 데이터베이스 관리
│   ├── scheduler.py       # 작업 스케줄링
│   └── main.py           # 메인 애플리케이션
├── data/                 # 데이터베이스 파일 저장소
├── logs/                 # 로그 파일 저장소
├── requirements.txt      # Python 의존성
├── config.env.example    # 환경 변수 예시
└── README.md
```

## 동작 과정

1. **논문 검색**: arXiv API를 통해 Swift/iOS 관련 키워드로 최신 논문 검색 (최근 7일)
2. **중복 확인**: 데이터베이스에서 이미 처리된 논문인지 확인
3. **AI 요약**: OpenAI GPT를 사용하여 논문 초록을 분석하고 요약 생성
4. **관련성 평가**: Swift/iOS 개발과의 관련성을 0-10점으로 평가
5. **필터링**: 관련성 점수 7점 이상인 논문만 선별
6. **슬랙 전송**: 선별된 논문들의 요약을 슬랙으로 전송
7. **기록 저장**: 전송된 논문 정보를 데이터베이스에 기록

## 요약 포맷

각 논문에 대해 다음 정보가 제공됩니다:

- **한줄요약**: 논문의 핵심 내용을 50자 이내로 요약
- **핵심 내용**: Swift/iOS 개발과 관련된 주요 포인트들 (3-5개)
- **상세 요약**: 논문의 상세한 요약 및 개발에 미치는 영향 (200자 이내)
- **관련성 점수**: Swift/iOS 개발과의 관련성 (0-10점, 7점 이상만 전송)

## 로그 및 모니터링

- GitHub Actions에서 모든 실행 로그 확인 가능
- 오류 발생 시 슬랙으로 알림이 전송됩니다
- 데이터베이스에는 논문 정보, 요약, 전송 기록이 저장됩니다

## 주의사항

- OpenAI API 사용료가 발생할 수 있습니다 (GPT-4o-mini 사용으로 비용 최적화)
- arXiv API는 rate limiting이 있으므로 대량 요청 시 주의가 필요합니다
- GitHub Actions는 월 2000분 무료 사용량이 있습니다 (일반적으로 충분)
- 슬랙 봇 토큰과 OpenAI API 키는 GitHub Secrets에 안전하게 저장됩니다

## 트러블슈팅

### 자주 발생하는 문제들

1. **GitHub Actions 실행 실패**
   - GitHub Secrets가 올바르게 설정되었는지 확인
   - Actions 탭에서 에러 로그 확인

2. **슬랙 연결 실패**
   - 봇 토큰이 올바른지 확인
   - 봇이 채널에 초대되었는지 확인

3. **OpenAI API 오류**
   - API 키가 유효한지 확인
   - API 사용량 한도를 확인

4. **논문을 찾을 수 없음**
   - arXiv 검색 키워드를 조정해보세요
   - 관련성 점수 기준을 낮춰보세요 (현재 7점 이상)

## 라이선스

MIT License

## 기여하기

버그 리포트나 기능 제안은 GitHub Issues를 통해 해주세요! 