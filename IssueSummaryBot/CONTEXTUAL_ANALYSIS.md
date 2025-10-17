# Contextual Keyword Analysis - Implementation Summary

## Overview

This update adds **contextual keyword analysis** to the Issue Summary Bot's priority scoring system. The bot now uses AI to analyze keywords like "urgent", "important", "major", "bug", "critical", "trivial", "minor" in the context they appear, rather than just relying on simple keyword matching.

## What Changed

### 1. New Function: `analyze_contextual_priority()`

Located in `issue_summary_bot.py`, this function:
- Takes an issue's title and description as input
- Uses an LLM (GPT-3.5-turbo) to analyze keywords in context
- Returns a score from 0-50 based on the contextual importance
- Handles errors gracefully by returning 0 if analysis fails

### 2. Updated Function: `get_priority_score()`

The priority scoring function now:
- Accepts an optional `llm` parameter
- Calls `analyze_contextual_priority()` if an LLM is provided
- Maintains backward compatibility (works without LLM)
- Adds contextual score to the total priority score

### 3. Integration in Main Function

The `main()` function now passes the LLM instance to `get_priority_score()`, enabling contextual analysis for all issues.

## Examples

### High Priority (Score: 40-50)
- **Title**: "Major urgent bug in authentication"
- **Description**: "Critical bug that prevents users from logging in. Needs immediate attention."
- **Analysis**: Keywords "major", "urgent", "bug", "critical", "immediate" in context of user authentication failure → Very high priority

### Low Priority (Score: 5-15)
- **Title**: "Major color change to frontend"
- **Description**: "We should update the main color scheme to use a different shade of blue."
- **Analysis**: Keyword "major" in context of cosmetic UI change → Lower priority

### Medium Priority (Score: 20-30)
- **Title**: "Add new feature for user profiles"
- **Description**: "Important enhancement to allow users to customize their profiles."
- **Analysis**: Keyword "important" in context of feature enhancement → Medium priority

### Very Low Priority (Score: 0-10)
- **Title**: "Minor typo in documentation"
- **Description**: "There's a small typo in the README. Trivial fix."
- **Analysis**: Keywords "minor", "trivial" in context of documentation typo → Very low priority

## Priority Score Components

The total priority score is calculated from balanced components (each with max 50 points):

1. **Age** (0-50 points): `min(age_days / 2, 50)`
2. **Labels** (0-50 points, rebalanced for proportionality):
   - Bug: +20
   - Urgent/Critical: +25
   - Enhancement/Feature: +10
   - High Priority: +15
   - Capped at 50 points maximum
3. **Engagement** (0-50 points): `min(comments * 3, 50)`
4. **Contextual Analysis** (0-50 points): AI-determined based on keyword context

**Maximum possible score**: 200 points (50 + 50 + 50 + 50)

This balanced approach ensures no single factor dominates the priority calculation, with contextual analysis having equal weight to other factors.

## Testing

### Unit Tests
- All existing tests pass without modification (backward compatibility)
- New tests verify LLM parameter acceptance
- Tests verify behavior with and without LLM

### Integration Tests
- `test_contextual_analysis.py` demonstrates the feature with real examples
- Requires `OPENAI_API_KEY` to run (gracefully skips if not available)
- Shows contextual analysis scoring different issue types

### Running Tests

```bash
# Run basic tests (no API key needed)
python test_simple.py
python test_bot.py

# Run contextual analysis demo (requires OPENAI_API_KEY)
export OPENAI_API_KEY="your-key-here"
python test_contextual_analysis.py
```

## Cost Considerations

The contextual analysis feature adds one additional OpenAI API call per issue:
- **Model**: GPT-3.5-turbo
- **Cost**: ~$0.001 per issue
- **For 20 issues**: ~$0.02 per run
- **Daily runs for a month**: ~$0.60/month

This is in addition to the existing API calls for:
- Issue summarization (~$0.001 per issue)
- Reading materials generation (~$0.001 per issue)
- Priority recommendation (~$0.001 per batch)

**Total estimated cost for 20 issues, daily runs**:
- Previous: ~$1.80/month
- With contextual analysis: ~$2.40/month

## Configuration

### Enable/Disable Contextual Analysis

Contextual analysis is enabled by default. To disable it:

```python
# In main() function, change:
'priority_score': get_priority_score(issue, llm),

# To:
'priority_score': get_priority_score(issue, llm=None),
```

### Customize Score Ranges

Edit the prompt in `analyze_contextual_priority()`:

```python
template="""...
Respond with ONLY a number from 0 to 50, where:
- 0-10: Trivial or minor issues
- 11-25: Medium priority        # Adjust these ranges
- 26-40: High priority           # to your preferences
- 41-50: Critical/Urgent
...
```

### Customize Keywords

The prompt currently looks for common keywords. To emphasize specific keywords:

```python
template="""Analyze the following GitHub issue title and description to determine its priority based on the context of keywords like "urgent", "important", "major", "bug", "critical", "trivial", "minor", etc.

# Add your custom keywords:
# Special attention to: "security", "vulnerability", "data loss", etc.
...
```

## Backward Compatibility

The implementation maintains full backward compatibility:
- The `llm` parameter defaults to `None`
- All existing tests pass without modification
- The bot works with or without contextual analysis
- No breaking changes to the API or function signatures

## Future Enhancements

Potential improvements:
1. Cache contextual analysis results to reduce API calls
2. Add configurable keyword weights
3. Support custom prompts per repository
4. Add sentiment analysis for urgency detection
5. Multi-language support for keyword detection

## Troubleshooting

### Contextual score is 0 for all issues
- Check that `OPENAI_API_KEY` is set correctly
- Check logs for API errors
- Verify the LLM instance is being passed to `get_priority_score()`

### Unexpected scores
- Review the prompt in `analyze_contextual_priority()`
- Check the issue title and description for context clues
- The LLM may interpret context differently than expected

### API rate limits or costs
- Reduce the frequency of bot runs
- Disable contextual analysis for less critical repositories
- Use caching to avoid re-analyzing unchanged issues

## Documentation

- **README.md**: Updated with feature description and examples
- **CONFIGURATION.md**: Updated with configuration details and customization options
- **test_contextual_analysis.py**: Demonstrates the feature with examples

## Conclusion

The contextual keyword analysis feature provides more nuanced and accurate priority scoring by understanding the context in which keywords appear. This helps teams focus on truly urgent issues while avoiding false positives from keywords used in non-critical contexts.
