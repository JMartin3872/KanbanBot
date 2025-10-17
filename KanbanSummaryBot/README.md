# Kanban Summary Bot

A GitHub Actions bot that summarizes issues from a GitHub Project board and posts the summary to GitHub Discussions.

## Features

- Fetches issues from GitHub Projects V2 boards
- Groups issues by column: Backlog, Ready, In progress, In review, Done
- Posts formatted summary to GitHub Discussions under "Kanban Summaries" category
- Manually triggered via GitHub Actions with configurable project and board names

## Usage

### Running via GitHub Actions

1. Go to the "Actions" tab in your repository
2. Select "Kanban Summary Bot" from the workflows list
3. Click "Run workflow"
4. (Optional) Enter custom parameters or use the defaults:
   - **Project Name**: Defaults to "ai-test" (the test project for this repository)
   - **Board Name**: Defaults to "kanban-board" (the test board)
5. Click "Run workflow" button

The bot will:
1. Fetch all issues from the specified project
2. Group them by their status column
3. Create a new discussion in the "Kanban Summaries" category with the formatted summary

### Running Locally

You can also run the bot locally for testing:

```bash
# Set environment variables
export GITHUB_TOKEN="your_github_token"
export GITHUB_REPOSITORY="owner/repo"
export PROJECT_NAME="ai-test"  # Default project name
export BOARD_NAME="kanban-board"  # Default board name

# Run the bot
python kanban_summary_bot.py
```

Or pass parameters as command-line arguments:

```bash
python kanban_summary_bot.py owner/repo "Project Name" "Board Name"
```

## Requirements

- Python 3.11+
- PyGithub
- requests
- python-dotenv

Install dependencies:
```bash
pip install -r requirements.txt
```

## Configuration

The bot requires the following:

1. **GitHub Token**: Provided automatically in GitHub Actions via `secrets.GITHUB_TOKEN`
2. **Discussion Category**: A discussion category named "Kanban Summaries" must exist in your repository
3. **GitHub Project**: The project must be accessible to the repository (organization or repository project)

### Permissions

The GitHub Actions workflow requires the following permissions:
- `issues: read` - To read issue information
- `contents: read` - To checkout the repository
- `discussions: write` - To create discussions

## Output Format

The bot generates a markdown summary with:

- Project and board information
- Timestamp of generation
- Total issue count
- Issues grouped by column (Backlog, Ready, In progress, In review, Done)
- For each issue:
  - Issue number and title (linked)
  - Labels
  - State (OPEN/CLOSED)

Example output:

```markdown
# Kanban Board Summary

**Project:** ai-test  
**Board:** kanban-board  
**Generated:** 2025-10-17 08:00:00 UTC  
**Total Issues:** 5

## 📋 Backlog (2)

- [#1: Add new feature](https://github.com/owner/repo/issues/1)
  - **Labels:** enhancement
  - **Status:** OPEN
  
## ✅ Ready (1)

- [#2: Fix bug](https://github.com/owner/repo/issues/2)
  - **Labels:** bug, priority
  - **Status:** OPEN
  
...
```

## Testing

Run the included tests to validate the bot's logic:

```bash
python test_simple.py
```

## Tech Stack

- **Python**: Core scripting language
- **PyGithub**: GitHub API integration
- **GitHub GraphQL API**: For accessing Projects V2 and Discussions
- **GitHub Actions**: Automated workflow execution

## Future Enhancements

The bot is designed to be extensible for future features:
- OpenAI integration for AI-powered issue summarization
- LangChain for structured LLM interactions
- Trend analysis and recommendations
- Automated scheduling of summaries
