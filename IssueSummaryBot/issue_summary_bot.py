#!/usr/bin/env python3
"""
Issue Summary Bot
Fetches, summarizes, and prioritizes GitHub issues using OpenAI and LangChain.
"""

import os
import sys
from datetime import datetime, timezone
from typing import List, Dict, Any
from github import Github
from openai import OpenAI
from langchain_openai import ChatOpenAI
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain
import json


def get_github_client() -> Github:
    """Initialize GitHub client with token from environment."""
    github_token = os.getenv('GITHUB_TOKEN')
    if not github_token:
        raise ValueError("GITHUB_TOKEN environment variable is required")
    return Github(github_token)


def get_openai_client() -> ChatOpenAI:
    """Initialize OpenAI client with API key from environment."""
    openai_api_key = os.getenv('OPENAI_API_KEY')
    if not openai_api_key:
        raise ValueError("OPENAI_API_KEY environment variable is required")
    return ChatOpenAI(
        model="gpt-3.5-turbo",
        temperature=0.3,
        openai_api_key=openai_api_key
    )


def fetch_open_issues(repo_name: str) -> List[Any]:
    """Fetch all open issues from the repository."""
    github = get_github_client()
    repo = github.get_repo(repo_name)
    issues = repo.get_issues(state='open')
    
    # Filter out pull requests (GitHub API includes PRs as issues)
    return [issue for issue in issues if not issue.pull_request]


def calculate_issue_age(created_at) -> int:
    """Calculate the age of an issue in days."""
    now = datetime.now(timezone.utc)
    age = now - created_at
    return age.days


def analyze_contextual_priority(llm: ChatOpenAI, issue) -> float:
    """
    Analyze the title and description contextually to determine priority based on keywords.
    Returns a score from 0-50 based on the contextual importance of keywords like
    urgent, important, major, bug, critical, trivial, minor, etc.
    """
    prompt_template = PromptTemplate(
        input_variables=["title", "body"],
        template="""Analyze the following GitHub issue title and description to determine its priority based on the context of keywords like "urgent", "important", "major", "bug", "critical", "trivial", "minor", etc.

Title: {title}
Description: {body}

Consider:
- Keywords in context (e.g., "Major urgent bug" is high priority, "Major color change" is lower priority)
- The severity implied by the combination of words
- Whether the issue describes a critical problem or a minor enhancement

Respond with ONLY a number from 0 to 50, where:
- 0-10: Trivial or minor issues (e.g., cosmetic changes, small enhancements)
- 11-25: Medium priority (e.g., regular features, non-critical bugs)
- 26-40: High priority (e.g., important features, bugs affecting functionality)
- 41-50: Critical/Urgent (e.g., major bugs, urgent fixes, critical issues)

Score:"""
    )
    
    chain = LLMChain(llm=llm, prompt=prompt_template)
    
    body_preview = issue.body[:500] if issue.body else "No description provided"
    
    try:
        result = chain.run(
            title=issue.title,
            body=body_preview
        )
        # Extract numeric score from the result
        score_str = result.strip().split()[0]  # Get first word/number
        score = float(score_str)
        # Ensure score is within bounds
        return max(0.0, min(score, 50.0))
    except Exception as e:
        print(f"Error analyzing contextual priority for issue #{issue.number}: {e}", file=sys.stderr)
        # Return 0 if analysis fails - fall back to other factors
        return 0.0


def get_priority_score(issue, llm=None):
    """
    Calculate a priority score for an issue based on:
    - Age (older issues get higher priority)
    - Engagement (comments indicate importance)
    - Contextual analysis of title/description (keywords in context)
    
    Returns:
        dict or float: If return_breakdown=False (for backward compatibility),
                      returns just the score as a float.
                      Otherwise returns a dict with 'total' and 'breakdown'.
    """
    # Age factor (older issues get more points, max 50 points)
    age_days = calculate_issue_age(issue.created_at)
    age_score = min(age_days / 2, 50)
    
    # Engagement factor (increased max to 50 points for better balance)
    engagement_score = min(issue.comments * 3, 50)
    
    # Contextual analysis factor (analyze title and description for keywords in context)
    # This is optional - only if llm is provided (to maintain backward compatibility with tests)
    contextual_score = 0.0
    if llm is not None:
        contextual_score = analyze_contextual_priority(llm, issue)
    
    total_score = age_score + engagement_score + contextual_score
    
    # Return breakdown as a dict
    return {
        'total': total_score,
        'breakdown': {
            'age': age_score,
            'engagement': engagement_score,
            'context': contextual_score
        }
    }


def summarize_issue(llm: ChatOpenAI, issue) -> str:
    """Summarize a single issue using LangChain and OpenAI."""
    prompt_template = PromptTemplate(
        input_variables=["title", "body", "labels"],
        template="""Summarize the following GitHub issue in 2-3 concise sentences:

Title: {title}
Labels: {labels}
Body: {body}

Summary:"""
    )
    
    chain = LLMChain(llm=llm, prompt=prompt_template)
    
    labels_str = ", ".join([label.name for label in issue.labels]) if issue.labels else "None"
    body_preview = issue.body[:500] if issue.body else "No description provided"
    
    try:
        result = chain.run(
            title=issue.title,
            labels=labels_str,
            body=body_preview
        )
        return result.strip()
    except Exception as e:
        print(f"Error summarizing issue #{issue.number}: {e}", file=sys.stderr)
        return f"Unable to generate summary. {issue.title}"


def generate_reading_materials(llm: ChatOpenAI, issue) -> str:
    """Generate relevant reading material recommendations based on the issue content."""
    prompt_template = PromptTemplate(
        input_variables=["title", "body", "labels"],
        template="""Based on the following GitHub issue, suggest 2-3 relevant learning resources or documentation links that would help someone work on this issue. Focus on official documentation, tutorials, or authoritative sources. Format as a brief markdown list.

Title: {title}
Labels: {labels}
Body: {body}

Reading Materials:"""
    )
    
    chain = LLMChain(llm=llm, prompt=prompt_template)
    
    labels_str = ", ".join([label.name for label in issue.labels]) if issue.labels else "None"
    body_preview = issue.body[:500] if issue.body else "No description provided"
    
    try:
        result = chain.run(
            title=issue.title,
            labels=labels_str,
            body=body_preview
        )
        return result.strip()
    except Exception as e:
        print(f"Error generating reading materials for issue #{issue.number}: {e}", file=sys.stderr)
        return ""


def generate_priority_recommendation(llm: ChatOpenAI, prioritized_issues: List[Dict]) -> str:
    """Generate overall recommendation for which issues to work on next."""
    if not prioritized_issues:
        return "No open issues to prioritize."
    
    top_issues = prioritized_issues[:5]
    issues_context = "\n".join([
        f"- Issue #{issue['number']}: {issue['title']} (Score: {issue['priority_score']:.1f}, Labels: {issue['labels']})"
        for issue in top_issues
    ])
    
    prompt_template = PromptTemplate(
        input_variables=["issues"],
        template="""Based on the following prioritized GitHub issues, provide a brief recommendation (2-3 sentences) on which issues should be tackled first and why:

{issues}

Recommendation:"""
    )
    
    chain = LLMChain(llm=llm, prompt=prompt_template)
    
    try:
        result = chain.run(issues=issues_context)
        return result.strip()
    except Exception as e:
        print(f"Error generating recommendation: {e}", file=sys.stderr)
        return "Unable to generate recommendation at this time."


def format_issue_summary(prioritized_issues: List[Dict], recommendation: str, repo_name: str) -> str:
    """Format the issue summary report."""
    report = f"""# Issue Summary Report

**Repository:** {repo_name}  
**Generated:** {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}  
**Total Open Issues:** {len(prioritized_issues)}

## 🎯 Priority Recommendation

{recommendation}

## 📋 Prioritized Issues

"""
    
    for idx, issue in enumerate(prioritized_issues, 1):
        age_days = calculate_issue_age(issue['created_at'])
        labels_str = issue['labels'] if issue['labels'] else "none"
        
        reading_materials = issue.get('reading_materials', '')
        reading_section = f"\n\n**📚 Recommended Reading:**\n{reading_materials}\n" if reading_materials else ""
        
        # Format priority score with breakdown
        breakdown = issue.get('priority_breakdown', {})
        age_val = breakdown.get('age', 0.0)
        engagement_val = breakdown.get('engagement', 0.0)
        context_val = breakdown.get('context', 0.0)
        
        priority_display = f"{issue['priority_score']:.1f}"
        if breakdown:  # Only show breakdown if it exists
            priority_display += f" ({age_val:.1f} Age, {engagement_val:.1f} Engagement"
            if context_val > 0:
                priority_display += f", {context_val:.1f} Context analysis"
            priority_display += ")"
        
        report += f"""### {idx}. [{issue['title']}]({issue['url']})

**Issue #** {issue['number']}  
**Priority Score:** {priority_display}  
**Labels:** {labels_str}  
**Age:** {age_days} days  
**Comments:** {issue['comments']}  

**Summary:** {issue['summary']}{reading_section}

---

"""
    
    return report


def create_or_update_summary_issue(repo_name: str, summary_content: str):
    """Create or update the issue summary issue in the repository."""
    github = get_github_client()
    repo = github.get_repo(repo_name)
    
    # Look for existing summary issue
    summary_title = "📊 Issue Summary Report"
    existing_issue = None
    
    for issue in repo.get_issues(state='open'):
        if issue.title == summary_title:
            existing_issue = issue
            break
    
    if existing_issue:
        # Update existing issue
        existing_issue.edit(body=summary_content)
        print(f"Updated existing summary issue: {existing_issue.html_url}")
    else:
        # Create new issue
        new_issue = repo.create_issue(
            title=summary_title,
            body=summary_content,
            labels=['bot', 'summary']
        )
        print(f"Created new summary issue: {new_issue.html_url}")


def main():
    """Main function to run the issue summary bot."""
    # Get repository name from environment or command line
    repo_name = os.getenv('GITHUB_REPOSITORY')
    if not repo_name and len(sys.argv) > 1:
        repo_name = sys.argv[1]
    
    if not repo_name:
        print("Error: Repository name not provided. Set GITHUB_REPOSITORY env var or pass as argument.", file=sys.stderr)
        sys.exit(1)
    
    print(f"Fetching issues from {repo_name}...")
    
    try:
        # Fetch issues
        issues = fetch_open_issues(repo_name)
        
        if not issues:
            print("No open issues found.")
            summary_content = f"""# Issue Summary Report

**Repository:** {repo_name}  
**Generated:** {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}  

## Status

✅ No open issues found! Great job keeping the backlog clean.
"""
            create_or_update_summary_issue(repo_name, summary_content)
            return
        
        print(f"Found {len(issues)} open issues. Analyzing...")
        
        # Initialize OpenAI client
        llm = get_openai_client()
        
        # Process and prioritize issues
        prioritized_issues = []
        for issue in issues:
            # Skip the summary issue itself
            if "Issue Summary Report" in issue.title:
                continue
            
            priority_result = get_priority_score(issue, llm)
            issue_data = {
                'number': issue.number,
                'title': issue.title,
                'url': issue.html_url,
                'created_at': issue.created_at,
                'labels': ", ".join([label.name for label in issue.labels]) if issue.labels else "",
                'comments': issue.comments,
                'priority_score': priority_result['total'],
                'priority_breakdown': priority_result['breakdown'],
                'summary': summarize_issue(llm, issue),
                'reading_materials': generate_reading_materials(llm, issue)
            }
            prioritized_issues.append(issue_data)
        
        # Sort by priority score (highest first)
        prioritized_issues.sort(key=lambda x: x['priority_score'], reverse=True)
        
        # Generate recommendation
        recommendation = generate_priority_recommendation(llm, prioritized_issues)
        
        # Format and create summary
        summary_content = format_issue_summary(prioritized_issues, recommendation, repo_name)
        
        # Create or update the summary issue
        create_or_update_summary_issue(repo_name, summary_content)
        
        print("Issue summary completed successfully!")
        
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
