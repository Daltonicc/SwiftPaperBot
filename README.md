# Swift & iOS Research Paper Summary Slack Bot 🍎📚

An intelligent bot that automatically collects Swift and iOS-related research papers from arXiv, generates AI-powered summaries with comprehensive analysis, and delivers them to Slack every morning.

## Key Features

- 🔍 **Automated Paper Discovery**: Daily search for the latest Swift/iOS-related papers from arXiv
- 🤖 **Advanced AI Analysis**: Multi-layered analysis using OpenAI GPT including:
  - Basic summary for general understanding
  - Technical analysis for developers
  - Business impact assessment
  - Keyword extraction and frequency analysis
  - Swift-specific keyword matching (0-10 scoring)
  - Automatic category classification (6 categories)
- 📱 **Smart Slack Notifications**: Daily delivery at 8 AM with comprehensive paper insights
- 🗄️ **Duplicate Prevention**: Intelligent tracking to avoid resending previously processed papers
- 📊 **Relevance Filtering**: Advanced scoring system to select only the most relevant papers (7+ points)
- 📈 **Comprehensive Statistics**: Daily and 30-day analytics with category distribution and keyword trends
- 🎯 **Top Paper Selection**: Automatically selects top 3 most relevant papers based on relevance and recency

## 🚀 Automated Execution with GitHub Actions (Recommended)

### 1. Setup GitHub Repository

1. Create a new GitHub repository
2. Upload this project to your repository

```bash
git init
git add .
git commit -m "Initial commit: Swift Research Paper Summary Slack Bot"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/SwiftThesisSlackBot.git
git push -u origin main
```

### 2. Configure GitHub Secrets

Navigate to your repository's Settings > Secrets and variables > Actions, and add:

- `SLACK_BOT_TOKEN`: Your Slack bot token
- `SLACK_CHANNEL`: Your Slack channel (e.g., #swift-papers)
- `OPENAI_API_KEY`: Your OpenAI API key

### 3. Automatic Daily Execution

The GitHub Actions workflow will automatically run every day at 8:00 AM KST, processing papers and sending summaries to your Slack channel.

## 📱 Local Development Setup

### Installation

#### 1. Install Required Packages

```bash
pip install -r requirements.txt
```

#### 2. Environment Configuration

Copy `config.env.example` to `config.env` and configure the following values:

```env
# Slack Bot Configuration
SLACK_BOT_TOKEN=xoxb-your-slack-bot-token
SLACK_CHANNEL=#your-channel-name

# OpenAI Configuration
OPENAI_API_KEY=your-openai-api-key

# arXiv Search Configuration
ARXIV_MAX_RESULTS=100
ARXIV_SEARCH_DAYS=730
ARXIV_SEARCH_TERMS="Swift programming","iOS development","SwiftUI","iPhone app","iPad app","Objective-C","UIKit","Core Data","WatchOS","tvOS","macOS development","visionOS","Vision Pro","Xcode","App Store","Apple SDK","iOS SDK","Swift language","mobile development"
MIN_RELEVANCE_SCORE=7
MAX_DAILY_PAPERS=3

# Database Configuration
DATABASE_PATH=./data/papers.db

# Logging Configuration
LOG_LEVEL=INFO
LOG_FILE=./logs/slackbot.log
```

#### 3. API Key Setup

##### Slack Bot Token
1. Visit [Slack API website](https://api.slack.com/) and create a new app
2. Add the following permissions in "OAuth & Permissions":
   - `chat:write`
   - `chat:write.public`
3. Copy the Bot Token and set it as `SLACK_BOT_TOKEN`
4. Invite the bot to your desired channel

##### OpenAI API Key
1. Generate an API key at [OpenAI Platform](https://platform.openai.com/)
2. Set the generated key as `OPENAI_API_KEY`

### Usage

#### Local Testing

```bash
# Single execution (for testing)
python -m src.main once

# Extended feature testing
python -m src.main extended-test

# View statistics
python -m src.main stats

# Scheduled execution (daily automation)
python -m src.main schedule 08:00
```

## Project Structure

```
SwiftThesisSlackBot/
├── .github/workflows/
│   └── daily-paper-summary.yml  # GitHub Actions workflow
├── src/
│   ├── __init__.py
│   ├── config.py          # Environment variables and configuration
│   ├── arxiv_client.py    # arXiv API client
│   ├── summarizer.py      # Advanced AI-powered paper analysis
│   ├── slack_client.py    # Enhanced Slack bot client
│   ├── database.py        # SQLite database with extended schema
│   ├── scheduler.py       # Task scheduling
│   └── main.py           # Main application with enhanced features
├── data/                 # Database storage
├── logs/                 # Log file storage
├── requirements.txt      # Python dependencies
├── config.env.example    # Environment variables example
└── README.md
```

## How It Works

1. **Paper Discovery**: Search arXiv API for Swift/iOS-related papers (last 730 days, up to 100 papers)
2. **Duplicate Check**: Verify against database to avoid reprocessing
3. **Advanced AI Analysis**: Multi-layered analysis using OpenAI GPT:
   - Generate basic summary for general understanding
   - Create technical analysis for developers
   - Assess business impact and implications
   - Extract and analyze keywords with frequency counting
   - Calculate Swift-specific keyword matching score (0-10)
   - Predict paper category (6 categories available)
4. **Relevance Scoring**: Evaluate Swift/iOS development relevance (0-10 scale)
5. **Smart Filtering**: Select papers with 7+ relevance score
6. **Top Selection**: Choose top 3 papers based on relevance and recency
7. **Comprehensive Slack Delivery**: Send detailed summaries with statistics
8. **Data Persistence**: Store all analysis results and statistics in database

## Enhanced Summary Format

Each paper includes comprehensive analysis:

### 📋 **Basic Information**
- **One-line Summary**: Core concept in under 50 characters
- **Publication Date**: When the paper was published
- **arXiv ID**: Direct link to the original paper

### 🔍 **Multi-layered Analysis**
- **Basic Summary**: General overview for broad understanding
- **Technical Analysis**: Developer-focused insights and implementation details
- **Business Impact**: Commercial implications and market relevance
- **Key Points**: 3-5 critical takeaways for Swift/iOS development

### 🏷️ **Smart Classification**
- **Category**: Automatically predicted from 6 categories
- **Keywords**: Extracted keywords with frequency analysis
- **Swift Keywords**: Specialized Swift/iOS keyword matching
- **Relevance Score**: 0-10 scale (only 7+ papers are delivered)

### 📊 **Daily Statistics**
- **Category Distribution**: Breakdown of paper categories
- **Top Keywords**: Most frequent keywords across papers
- **Daily Trends**: Analysis of daily paper patterns
- **30-day Overview**: Long-term statistics and trends

## Advanced Features

### 🎯 **Multi-Summary Approach**
- **Basic Summary**: Accessible overview for all team members
- **Technical Summary**: In-depth analysis for developers
- **Business Impact**: Strategic insights for decision makers

### 🔤 **Intelligent Keyword Analysis**
- **Automatic Extraction**: AI-powered keyword identification
- **Frequency Analysis**: Track trending topics and technologies
- **Swift-Specific Matching**: Specialized scoring for Swift/iOS relevance

### 📈 **Comprehensive Statistics**
- **Real-time Analytics**: Daily paper processing statistics
- **Historical Trends**: 30-day analysis of paper patterns
- **Category Insights**: Distribution across different research areas
- **Keyword Trends**: Most popular topics and technologies

### 🎨 **Enhanced Slack Experience**
- **Rich Formatting**: Beautiful, structured message layout
- **Smart Notifications**: Contextual information delivery
- **Statistics Integration**: Daily insights alongside paper summaries
- **Empty Day Handling**: Meaningful statistics even when no relevant papers are found

## Logging and Monitoring

- **GitHub Actions**: Complete execution logs available in workflow runs
- **Error Notifications**: Automatic Slack alerts for any issues
- **Comprehensive Database**: Stores papers, summaries, keywords, categories, and statistics
- **Performance Metrics**: Track processing time and API usage

## Performance Optimization

- **Smart Caching**: Avoid reprocessing previously analyzed papers
- **Batch Processing**: Efficient handling of multiple papers
- **API Rate Limiting**: Respectful usage of external APIs
- **Cost Optimization**: Uses GPT-4o-mini for cost-effective analysis

## Important Notes

- OpenAI API usage may incur costs (optimized with GPT-4o-mini)
- Requires stable internet connection for API calls
- Slack workspace admin permissions needed for bot setup
- GitHub Actions provides free automation (usage limits apply)

## License

MIT License

## Contributing

Bug reports and feature requests are welcome through GitHub Issues!

## Support

For questions or support, please open an issue on GitHub or contact the maintainers.

---
