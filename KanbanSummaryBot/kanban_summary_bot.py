#!/usr/bin/env python3
"""
Kanban Summary Bot
Fetches issues from a GitHub Project board and posts a summary to GitHub Discussions.
"""

import os
import sys
import json
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
import requests
from github import Github


def get_github_token() -> str:
    """Get GitHub token from environment."""
    github_token = os.getenv('GITHUB_TOKEN')
    if not github_token:
        raise ValueError("GITHUB_TOKEN environment variable is required")
    return github_token


def get_github_client() -> Github:
    """Initialize GitHub client with token from environment."""
    return Github(get_github_token())


def execute_graphql_query(query: str, variables: Dict[str, Any]) -> Dict[str, Any]:
    """Execute a GraphQL query against the GitHub API."""
    token = get_github_token()
    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json',
    }
    
    response = requests.post(
        'https://api.github.com/graphql',
        headers=headers,
        json={'query': query, 'variables': variables}
    )
    
    if response.status_code != 200:
        raise Exception(f"GraphQL query failed with status {response.status_code}: {response.text}")
    
    data = response.json()
    
    if 'errors' in data:
        raise Exception(f"GraphQL query returned errors: {json.dumps(data['errors'], indent=2)}")
    
    return data['data']


def get_organization_projects(org_name: str, project_name: str) -> Optional[Dict[str, Any]]:
    """Get project by name from an organization."""
    query = """
    query($org: String!, $projectName: String!) {
      organization(login: $org) {
        projectsV2(first: 20, query: $projectName) {
          nodes {
            id
            title
            number
          }
        }
      }
    }
    """
    
    variables = {
        'org': org_name,
        'projectName': project_name
    }
    
    data = execute_graphql_query(query, variables)
    
    if not data.get('organization'):
        return None
    
    projects = data['organization']['projectsV2']['nodes']
    
    # Find exact match (case-insensitive)
    for project in projects:
        if project['title'].lower() == project_name.lower():
            return project
    
    return None


def get_repository_projects(owner: str, repo: str, project_name: str) -> Optional[Dict[str, Any]]:
    """Get project by name from a repository."""
    query = """
    query($owner: String!, $repo: String!, $projectName: String!) {
      repository(owner: $owner, name: $repo) {
        projectsV2(first: 20, query: $projectName) {
          nodes {
            id
            title
            number
          }
        }
      }
    }
    """
    
    variables = {
        'owner': owner,
        'repo': repo,
        'projectName': project_name
    }
    
    data = execute_graphql_query(query, variables)
    
    if not data.get('repository'):
        return None
    
    projects = data['repository']['projectsV2']['nodes']
    
    # Find exact match (case-insensitive)
    for project in projects:
        if project['title'].lower() == project_name.lower():
            return project
    
    return None


def get_project_items(project_id: str, board_name: Optional[str] = None) -> Dict[str, List[Dict[str, Any]]]:
    """Get all items from a project, grouped by status column."""
    query = """
    query($projectId: ID!, $cursor: String) {
      node(id: $projectId) {
        ... on ProjectV2 {
          items(first: 100, after: $cursor) {
            pageInfo {
              hasNextPage
              endCursor
            }
            nodes {
              id
              content {
                ... on Issue {
                  number
                  title
                  url
                  state
                  labels(first: 10) {
                    nodes {
                      name
                    }
                  }
                  createdAt
                  updatedAt
                }
              }
              fieldValues(first: 20) {
                nodes {
                  ... on ProjectV2ItemFieldSingleSelectValue {
                    name
                    field {
                      ... on ProjectV2SingleSelectField {
                        name
                      }
                    }
                  }
                }
              }
            }
          }
        }
      }
    }
    """
    
    all_items = []
    cursor = None
    has_next_page = True
    
    while has_next_page:
        variables = {
            'projectId': project_id,
            'cursor': cursor
        }
        
        data = execute_graphql_query(query, variables)
        
        if not data.get('node') or not data['node'].get('items'):
            break
        
        items_data = data['node']['items']
        all_items.extend(items_data['nodes'])
        
        page_info = items_data['pageInfo']
        has_next_page = page_info['hasNextPage']
        cursor = page_info['endCursor']
    
    # Group items by status column
    columns = {
        'Backlog': [],
        'Ready': [],
        'In progress': [],
        'In review': [],
        'Done': []
    }
    
    for item in all_items:
        if not item.get('content'):
            continue
        
        # Extract status from field values
        status = 'Backlog'  # Default
        for field_value in item.get('fieldValues', {}).get('nodes', []):
            if field_value and 'field' in field_value:
                field_name = field_value['field'].get('name', '')
                if field_name.lower() in ['status', 'state']:
                    status = field_value.get('name', 'Backlog')
                    break
        
        # Only include issues (not PRs or other content types)
        content = item['content']
        if 'number' not in content:
            continue
        
        issue_data = {
            'number': content['number'],
            'title': content['title'],
            'url': content['url'],
            'state': content['state'],
            'labels': [label['name'] for label in content.get('labels', {}).get('nodes', [])],
            'created_at': content['createdAt'],
            'updated_at': content['updatedAt']
        }
        
        # Add to appropriate column if it exists
        if status in columns:
            columns[status].append(issue_data)
    
    return columns


def get_discussion_category_id(repo_name: str, category_name: str) -> Optional[str]:
    """Get the ID of a discussion category by name."""
    owner, repo = repo_name.split('/')
    
    query = """
    query($owner: String!, $repo: String!) {
      repository(owner: $owner, name: $repo) {
        discussionCategories(first: 20) {
          nodes {
            id
            name
          }
        }
      }
    }
    """
    
    variables = {
        'owner': owner,
        'repo': repo
    }
    
    data = execute_graphql_query(query, variables)
    
    if not data.get('repository'):
        return None
    
    categories = data['repository']['discussionCategories']['nodes']
    
    for category in categories:
        if category['name'].lower() == category_name.lower():
            return category['id']
    
    return None


def create_discussion(repo_name: str, category_id: str, title: str, body: str) -> str:
    """Create a new discussion in the repository."""
    owner, repo = repo_name.split('/')
    
    # First get the repository ID
    query = """
    query($owner: String!, $repo: String!) {
      repository(owner: $owner, name: $repo) {
        id
      }
    }
    """
    
    variables = {
        'owner': owner,
        'repo': repo
    }
    
    data = execute_graphql_query(query, variables)
    repository_id = data['repository']['id']
    
    # Create the discussion
    mutation = """
    mutation($repositoryId: ID!, $categoryId: ID!, $title: String!, $body: String!) {
      createDiscussion(input: {
        repositoryId: $repositoryId,
        categoryId: $categoryId,
        title: $title,
        body: $body
      }) {
        discussion {
          id
          url
        }
      }
    }
    """
    
    variables = {
        'repositoryId': repository_id,
        'categoryId': category_id,
        'title': title,
        'body': body
    }
    
    data = execute_graphql_query(mutation, variables)
    return data['createDiscussion']['discussion']['url']


def format_kanban_summary(columns: Dict[str, List[Dict[str, Any]]], project_name: str, board_name: str) -> str:
    """Format the kanban board summary."""
    timestamp = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')
    
    # Count total issues
    total_issues = sum(len(issues) for issues in columns.values())
    
    report = f"""# Kanban Board Summary

**Project:** {project_name}  
**Board:** {board_name}  
**Generated:** {timestamp}  
**Total Issues:** {total_issues}

"""
    
    # Define column order and emojis
    column_config = [
        ('Backlog', '📋'),
        ('Ready', '✅'),
        ('In progress', '🔄'),
        ('In review', '👀'),
        ('Done', '✔️')
    ]
    
    for column_name, emoji in column_config:
        issues = columns.get(column_name, [])
        count = len(issues)
        
        report += f"## {emoji} {column_name} ({count})\n\n"
        
        if not issues:
            report += "*No issues in this column*\n\n"
        else:
            for issue in issues:
                labels_str = ', '.join(issue['labels']) if issue['labels'] else 'no labels'
                report += f"- [#{issue['number']}: {issue['title']}]({issue['url']})\n"
                report += f"  - **Labels:** {labels_str}\n"
                report += f"  - **Status:** {issue['state']}\n"
            report += "\n"
    
    report += "---\n\n"
    report += "*This summary was automatically generated by the Kanban Summary Bot.*\n"
    
    return report


def main():
    """Main function to run the kanban summary bot."""
    # Get parameters from environment or command line
    repo_name = os.getenv('GITHUB_REPOSITORY')
    project_name = os.getenv('PROJECT_NAME')
    board_name = os.getenv('BOARD_NAME', 'kanban-board')
    
    # Also support command line arguments
    if len(sys.argv) > 1:
        repo_name = sys.argv[1]
    if len(sys.argv) > 2:
        project_name = sys.argv[2]
    if len(sys.argv) > 3:
        board_name = sys.argv[3]
    
    if not repo_name:
        print("Error: Repository name not provided. Set GITHUB_REPOSITORY env var or pass as argument.", file=sys.stderr)
        sys.exit(1)
    
    if not project_name:
        print("Error: Project name not provided. Set PROJECT_NAME env var or pass as second argument.", file=sys.stderr)
        sys.exit(1)
    
    print(f"Fetching Kanban board from project '{project_name}' in repository {repo_name}...")
    
    try:
        # Parse repository name
        owner, repo = repo_name.split('/')
        
        # Try to find the project (first in org, then in repo)
        project = get_organization_projects(owner, project_name)
        
        if not project:
            project = get_repository_projects(owner, repo, project_name)
        
        if not project:
            print(f"Error: Project '{project_name}' not found in organization '{owner}' or repository '{repo_name}'.", file=sys.stderr)
            sys.exit(1)
        
        print(f"Found project: {project['title']} (#{project['number']})")
        
        # Get project items grouped by column
        columns = get_project_items(project['id'], board_name)
        
        # Count total issues
        total_issues = sum(len(issues) for issues in columns.values())
        print(f"Found {total_issues} issues across all columns")
        
        # Format the summary
        summary_content = format_kanban_summary(columns, project['title'], board_name)
        
        # Get the discussion category ID
        category_id = get_discussion_category_id(repo_name, 'Kanban Summaries')
        
        if not category_id:
            print("Error: Discussion category 'Kanban Summaries' not found.", file=sys.stderr)
            sys.exit(1)
        
        # Create the discussion
        discussion_title = f"Kanban Summary: {project['title']} - {datetime.now(timezone.utc).strftime('%Y-%m-%d')}"
        discussion_url = create_discussion(repo_name, category_id, discussion_title, summary_content)
        
        print(f"Successfully created discussion: {discussion_url}")
        
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
