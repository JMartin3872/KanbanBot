#!/usr/bin/env python3
"""
Simple validation tests for issue_summary_bot.py logic.
These tests validate the core logic without requiring API dependencies.
"""

from datetime import datetime, timezone, timedelta
from unittest.mock import Mock

# Mock the external dependencies
import sys
from unittest.mock import MagicMock

sys.modules['github'] = MagicMock()
sys.modules['openai'] = MagicMock()
sys.modules['langchain'] = MagicMock()
sys.modules['langchain_openai'] = MagicMock()
sys.modules['langchain.prompts'] = MagicMock()
sys.modules['langchain.chains'] = MagicMock()

# Now we can import the bot
from issue_summary_bot import calculate_issue_age, get_priority_score


def test_calculate_age():
    """Test age calculation."""
    print("Testing calculate_issue_age...")
    
    # Test today
    now = datetime.now(timezone.utc)
    assert calculate_issue_age(now) == 0, "Age today should be 0"
    
    # Test 7 days ago
    week_ago = datetime.now(timezone.utc) - timedelta(days=7)
    assert calculate_issue_age(week_ago) == 7, "Age should be 7 days"
    
    # Test 30 days ago
    month_ago = datetime.now(timezone.utc) - timedelta(days=30)
    assert calculate_issue_age(month_ago) == 30, "Age should be 30 days"
    
    print("✓ calculate_issue_age tests passed")


def create_mock_issue(age_days=0, labels=None, comments=0):
    """Helper to create a mock issue."""
    issue = Mock()
    issue.created_at = datetime.now(timezone.utc) - timedelta(days=age_days)
    
    if labels:
        mock_labels = []
        for label_name in labels:
            label = Mock()
            label.name = label_name
            mock_labels.append(label)
        issue.labels = mock_labels
    else:
        issue.labels = []
    
    issue.comments = comments
    return issue


def test_priority_score():
    """Test priority score calculation."""
    print("\nTesting get_priority_score...")
    
    # Test new issue, no labels, no comments
    issue = create_mock_issue(age_days=0, labels=[], comments=0)
    result = get_priority_score(issue)
    score = result['total']
    assert score == 0.0, f"Expected 0.0, got {score}"
    print("  ✓ New issue with no labels/comments = 0.0")
    
    # Test age scoring
    issue = create_mock_issue(age_days=20, labels=[], comments=0)
    result = get_priority_score(issue)
    score = result['total']
    assert score == 10.0, f"Expected 10.0, got {score}"
    assert result['breakdown']['age'] == 10.0, "Age breakdown should be 10.0"
    print("  ✓ 20 days old = 10.0")
    
    # Test age cap
    issue = create_mock_issue(age_days=200, labels=[], comments=0)
    result = get_priority_score(issue)
    score = result['total']
    assert score == 50.0, f"Expected 50.0, got {score}"
    print("  ✓ Very old issue capped at 50.0")
    
    # Test comments
    issue = create_mock_issue(age_days=0, labels=[], comments=5)
    result = get_priority_score(issue)
    score = result['total']
    assert score == 15.0, f"Expected 15.0, got {score}"
    assert result['breakdown']['engagement'] == 15.0, "Engagement breakdown should be 15.0"
    print("  ✓ 5 comments = 15.0")
    
    # Test comments cap
    issue = create_mock_issue(age_days=0, labels=[], comments=50)
    result = get_priority_score(issue)
    score = result['total']
    assert score == 50.0, f"Expected 50.0, got {score}"
    print("  ✓ Many comments capped at 50.0")
    
    # Test complex issue with age and comments (labels no longer contribute)
    issue = create_mock_issue(age_days=60, labels=['bug', 'urgent'], comments=20)
    result = get_priority_score(issue)
    score = result['total']
    # Expected: 30 (age) + 50 (comments capped) = 80
    assert score == 80.0, f"Expected 80.0, got {score}"
    assert result['breakdown']['age'] == 30.0, "Age breakdown should be 30.0"
    assert result['breakdown']['engagement'] == 50.0, "Engagement breakdown should be 50.0"
    print("  ✓ Complex issue (old issue with comments) = 80.0")
    
    print("✓ get_priority_score tests passed")


def main():
    """Run all tests."""
    print("="*60)
    print("Running Issue Summary Bot Logic Tests")
    print("="*60)
    
    try:
        test_calculate_age()
        test_priority_score()
        
        print("\n" + "="*60)
        print("✓ ALL TESTS PASSED!")
        print("="*60)
        return 0
    except AssertionError as e:
        print(f"\n✗ TEST FAILED: {e}")
        return 1
    except Exception as e:
        print(f"\n✗ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    exit(main())
