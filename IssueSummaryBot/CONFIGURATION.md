# Configuration Guide

This guide explains how to configure and customize the Issue Summary Bot for your repository.

## Required Secrets

The bot requires the following secrets to be configured in your GitHub repository:

### 1. OPENAI_API_KEY

**Required**: Yes  
**Description**: Your OpenAI API key for generating summaries and recommendations.

**How to get it**:
1. Sign up at [OpenAI](https://platform.openai.com/)
2. Navigate to API keys section
3. Create a new secret key
4. Copy the key (you won't be able to see it again!)

**How to add it to GitHub**:
1. Go to your repository on GitHub
2. Click Settings → Secrets and variables → Actions
3. Click "New repository secret"
4. Name: `OPENAI_API_KEY`
5. Value: Paste your OpenAI API key
6. Click "Add secret"

### 2. GITHUB_TOKEN

**Required**: Yes (automatically provided)  
**Description**: Used to authenticate with GitHub API to fetch and create issues.

**Note**: This token is automatically provided by GitHub Actions. You don't need to create or configure it manually.

## Workflow Customization

### Scheduling

By default, the bot runs:
- **Daily** at 9 AM UTC
- When **issues are opened, labeled, closed, or reopened**
- **Manually** via workflow dispatch

To change the schedule, edit `.github/workflows/issue_summary.yml`:

```yaml
on:
  schedule:
    - cron: '0 9 * * *'  # Change this cron expression
```

Common cron examples:
- `0 */6 * * *` - Every 6 hours
- `0 0 * * 1` - Every Monday at midnight
- `0 12 * * 1-5` - Weekdays at noon

### Trigger Events

To change which issue events trigger the bot:

```yaml
on:
  issues:
    types: [opened, labeled, closed, reopened]  # Customize these events
```

Available event types:
- `opened` - New issues
- `edited` - Issue edited
- `deleted` - Issue deleted
- `transferred` - Issue transferred
- `pinned` / `unpinned` - Issue pinned/unpinned
- `closed` / `reopened` - Issue state changes
- `assigned` / `unassigned` - Assignee changes
- `labeled` / `unlabeled` - Label changes
- `locked` / `unlocked` - Issue locked/unlocked
- `milestoned` / `demilestoned` - Milestone changes

## Bot Customization

### Priority Scoring

The bot uses **balanced scoring** across all factors, with each component having equal maximum weight (50 points).

Priority scores are calculated based on:
1. **Age**: Older issues get higher priority (max 50 points)
2. **Engagement**: Comments indicate importance (max 50 points)
3. **Contextual Analysis**: AI analyzes title and description for keywords in context (max 50 points)

**Maximum Total Score**: 150 points (50 + 50 + 50)

**How Contextual Analysis Works:**

The bot analyzes keywords like "urgent", "important", "major", "bug", "critical", "trivial", "minor" in the context they're used:
- ✅ "Major urgent bug which needs to be fixed soon" → High priority
- ❌ "Major color change to frontend" → Lower priority

To customize weights, edit `get_priority_score()` in `issue_summary_bot.py`:

```python
def get_priority_score(issue, llm=None) -> float:
    score = 0.0
    
    # Customize age factor
    age_days = calculate_issue_age(issue.created_at)
    score += min(age_days / 2, 50)  # Change divisor or max
    
    # Customize comment weight (balanced with other factors)
    score += min(issue.comments * 3, 50)  # Change multiplier or max
    
    # Contextual analysis (if llm is provided)
    if llm is not None:
        contextual_score = analyze_contextual_priority(llm, issue)
        score += contextual_score  # Max 50 points based on context
    
    return score
```

To disable contextual analysis, pass `llm=None` to `get_priority_score()`.

### AI Model

To change the OpenAI model, edit `get_openai_client()`:

```python
def get_openai_client() -> ChatOpenAI:
    return ChatOpenAI(
        model="gpt-4",  # Options: gpt-3.5-turbo, gpt-4, gpt-4-turbo-preview
        temperature=0.3,  # 0.0-1.0 (lower = more focused)
        openai_api_key=openai_api_key
    )
```

**Note**: GPT-4 provides better summaries but costs more. GPT-3.5-turbo is the default for cost-effectiveness.

### Summary Length

To adjust summary length, edit the prompt in `summarize_issue()`:

```python
template="""Summarize the following GitHub issue in 2-3 concise sentences:
# Change to: "in 1-2 sentences" or "in a paragraph"
```

### Report Title

To change the summary issue title, edit `create_or_update_summary_issue()`:

```python
summary_title = "📊 Issue Summary Report"  # Customize this
```

### Report Labels

To change the labels applied to the summary issue:

```python
new_issue = repo.create_issue(
    title=summary_title,
    body=summary_content,
    labels=['bot', 'summary']  # Customize these
)
```

## Cost Considerations

### OpenAI API Costs

The bot uses the OpenAI API, which has associated costs:

- **GPT-3.5-turbo** (default): ~$0.001 per issue
- **GPT-4**: ~$0.03 per issue

For a repository with 20 issues, running daily:
- GPT-3.5-turbo: ~$0.60/month
- GPT-4: ~$18/month

### Optimization Tips

1. **Use GPT-3.5-turbo** for regular summaries
2. **Adjust schedule** to run less frequently (e.g., weekly instead of daily)
3. **Limit triggers** to only essential events (e.g., remove label changes)
4. **Set up billing alerts** in your OpenAI account

## Testing

### Manual Testing

Run the workflow manually to test configuration:

1. Go to your repository on GitHub
2. Click "Actions" tab
3. Select "Issue Summary Bot" workflow
4. Click "Run workflow" button
5. Check the run logs for errors

### Local Testing

Test the bot locally before deploying:

```bash
# Install dependencies
pip install -r requirements.txt

# Set environment variables
export GITHUB_TOKEN="your_personal_access_token"
export OPENAI_API_KEY="your_openai_api_key"
export GITHUB_REPOSITORY="owner/repo"

# Run the bot
python issue_summary_bot.py
```

**Note**: Use a personal access token with `repo` scope for local testing.

## Troubleshooting

### Common Issues

**"OPENAI_API_KEY environment variable is required"**
- Ensure you've added the secret to GitHub Actions
- Check the secret name is exactly `OPENAI_API_KEY`

**"GITHUB_TOKEN environment variable is required"**
- This should be automatically provided by GitHub Actions
- If running locally, create a personal access token

**"Rate limit exceeded"**
- GitHub API has rate limits (5000 requests/hour)
- OpenAI has rate limits (varies by plan)
- Consider reducing execution frequency

**"Permission denied"**
- Ensure workflow has correct permissions in YAML
- Check repository settings allow Actions to create issues

### Debugging

Enable debug logging by adding to workflow:

```yaml
- name: Run Issue Summary Bot
  env:
    GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
    OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
    GITHUB_REPOSITORY: ${{ github.repository }}
    PYTHONUNBUFFERED: 1  # Add this for better logging
  run: |
    python -u issue_summary_bot.py  # -u for unbuffered output
```

## Security Best Practices

1. **Never commit API keys** to the repository
2. **Use repository secrets** for sensitive data
3. **Limit token permissions** to minimum required
4. **Regularly rotate** API keys
5. **Monitor API usage** for unexpected activity
6. **Review bot permissions** periodically

## Support

For issues or questions:
1. Check the [README](README.md)
2. Review [example output](EXAMPLE_OUTPUT.md)
3. Open an issue in the repository
