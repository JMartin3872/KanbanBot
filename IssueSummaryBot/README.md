# IssueSummaryBot

A GitHub bot that automatically summarizes and prioritizes issues in your repository using AI.

## Features

- 🤖 **Automated Issue Analysis**: Fetches all open issues from your GitHub repository
- 📝 **AI-Powered Summaries**: Uses OpenAI and LangChain to generate concise summaries for each issue
- 📚 **Reading Material Recommendations**: Provides relevant documentation and learning resources for each issue
- 🎯 **Smart Prioritization**: Ranks issues based on:
  - Age of the issue (older issues get higher priority)
  - Labels (bug, urgent, enhancement, etc.)
  - Community engagement (number of comments)
  - **Contextual keyword analysis** (NEW): AI analyzes keywords like "urgent", "bug", "major" in context
    - Example: "Major urgent bug" → high priority vs "Major color change" → lower priority
- 📊 **Summary Reports**: Creates/updates a dedicated issue with a comprehensive report
- ⏰ **Scheduled Execution**: Runs daily via GitHub Actions (also triggers on issue events)

## Setup

### Prerequisites

- A GitHub repository
- OpenAI API key

### Installation

1. **Add the bot to your repository**:
   - Copy `issue_summary_bot.py`, `requirements.txt`, and `.github/workflows/issue_summary.yml` to your repository

2. **Configure GitHub Secrets**:
   - Go to your repository settings → Secrets and variables → Actions
   - Add a new secret: `OPENAI_API_KEY` with your OpenAI API key
   - Note: `GITHUB_TOKEN` is automatically provided by GitHub Actions

3. **Enable GitHub Actions**:
   - Ensure GitHub Actions are enabled in your repository settings

### Usage

The bot runs automatically:
- **Daily** at 9 AM UTC
- When issues are **opened, labeled, closed, or reopened**
- **Manually** via the Actions tab (workflow_dispatch)

You can also run it locally:

```bash
# Install dependencies
pip install -r requirements.txt

# Set environment variables
export GITHUB_TOKEN="your_github_token"
export OPENAI_API_KEY="your_openai_api_key"
export GITHUB_REPOSITORY="owner/repo"

# Run the bot
python issue_summary_bot.py
```

## How It Works

1. **Fetch Issues**: Retrieves all open issues from the repository via GitHub API
2. **Analyze**: For each issue:
   - Extracts metadata (title, labels, age, comments)
   - Generates AI summary using OpenAI
   - Generates relevant reading material recommendations
   - Calculates priority score
3. **Prioritize**: Sorts issues by priority score
4. **Generate Report**: Creates a formatted markdown report with:
   - Priority recommendations
   - Ranked list of issues with summaries
   - Reading material recommendations for each issue
   - Metadata for each issue
5. **Update Issue**: Creates or updates an issue titled "📊 Issue Summary Report"

## Priority Scoring

The bot calculates a priority score with balanced weighting across all factors (each component has a maximum of 50 points):

- **Age**: Older issues receive higher scores (up to 50 points)
- **Engagement**: Each comment adds +3 points (up to 50 points)
- **Contextual Analysis**: AI analyzes title and description for keywords in context (up to 50 points)
  - Keywords like "urgent", "important", "major", "bug", "critical", "trivial", "minor" are evaluated in context
  - Examples:
    - ✅ "Major urgent bug which needs to be fixed soon" → High score (~40-50)
    - ❌ "Major color change to frontend" → Lower score (~5-15)
    - ✅ "Critical security vulnerability" → Very high score (~45-50)
    - ❌ "Trivial typo in docs" → Very low score (~0-5)

**Maximum Total Score**: 150 points (50 + 50 + 50)

This balanced approach ensures that no single factor dominates the priority calculation.

## Tech Stack

- **Python**: Core scripting language
- **PyGithub**: GitHub API integration
- **OpenAI**: AI-powered summarization
- **LangChain**: Structured LLM interactions
- **GitHub Actions**: Automated workflow execution

## Configuration

You can customize the bot by modifying:

- **Scheduling**: Edit the cron expression in `.github/workflows/issue_summary.yml`
- **Priority weights**: Adjust scores in the `get_priority_score()` function
- **AI model**: Change the model in `get_openai_client()` (default: gpt-3.5-turbo)
- **Summary length**: Modify the prompt template in `summarize_issue()`

## License

MIT
