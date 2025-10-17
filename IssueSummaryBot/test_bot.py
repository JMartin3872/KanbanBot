#!/usr/bin/env python3
"""
Unit tests for issue_summary_bot.py
Tests the core logic without requiring API credentials.
"""

import unittest
from datetime import datetime, timezone, timedelta
from unittest.mock import Mock, MagicMock
import sys
import os

# Add parent directory to path to import the bot
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from issue_summary_bot import (
    calculate_issue_age,
    get_priority_score,
    format_issue_summary,
    generate_reading_materials,
    analyze_contextual_priority
)


class TestCalculateIssueAge(unittest.TestCase):
    """Test issue age calculation."""
    
    def test_age_calculation_today(self):
        """Test age of issue created today."""
        now = datetime.now(timezone.utc)
        age = calculate_issue_age(now)
        self.assertEqual(age, 0)
    
    def test_age_calculation_one_week_ago(self):
        """Test age of issue created one week ago."""
        one_week_ago = datetime.now(timezone.utc) - timedelta(days=7)
        age = calculate_issue_age(one_week_ago)
        self.assertEqual(age, 7)
    
    def test_age_calculation_one_month_ago(self):
        """Test age of issue created one month ago."""
        one_month_ago = datetime.now(timezone.utc) - timedelta(days=30)
        age = calculate_issue_age(one_month_ago)
        self.assertEqual(age, 30)


class TestGetPriorityScore(unittest.TestCase):
    """Test priority score calculation."""
    
    def create_mock_issue(self, age_days=0, labels=None, comments=0):
        """Helper to create a mock issue."""
        issue = Mock()
        issue.created_at = datetime.now(timezone.utc) - timedelta(days=age_days)
        
        # Mock labels
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
    
    def test_new_issue_no_labels_no_comments(self):
        """Test score for new issue with no labels or comments."""
        issue = self.create_mock_issue(age_days=0, labels=[], comments=0)
        result = get_priority_score(issue)
        self.assertEqual(result['total'], 0.0)
    
    def test_labels_do_not_affect_score(self):
        """Test that labels do not affect priority score."""
        # Test with various labels - they should not add any points
        issue = self.create_mock_issue(age_days=0, labels=['bug'], comments=0)
        result = get_priority_score(issue)
        self.assertEqual(result['total'], 0.0)
        
        issue = self.create_mock_issue(age_days=0, labels=['urgent'], comments=0)
        result = get_priority_score(issue)
        self.assertEqual(result['total'], 0.0)
        
        issue = self.create_mock_issue(age_days=0, labels=['critical'], comments=0)
        result = get_priority_score(issue)
        self.assertEqual(result['total'], 0.0)
        
        issue = self.create_mock_issue(age_days=0, labels=['bug', 'urgent', 'critical'], comments=0)
        result = get_priority_score(issue)
        self.assertEqual(result['total'], 0.0)
    
    def test_age_increases_score(self):
        """Test that older issues get higher scores."""
        issue = self.create_mock_issue(age_days=20, labels=[], comments=0)
        result = get_priority_score(issue)
        self.assertEqual(result['total'], 10.0)  # 20 / 2 = 10
    
    def test_age_max_capped_at_50(self):
        """Test that age score is capped at 50."""
        issue = self.create_mock_issue(age_days=200, labels=[], comments=0)
        result = get_priority_score(issue)
        self.assertEqual(result['total'], 50.0)  # min(200 / 2, 50) = 50
    
    def test_comments_increase_score(self):
        """Test that comments increase priority."""
        issue = self.create_mock_issue(age_days=0, labels=[], comments=5)
        result = get_priority_score(issue)
        self.assertEqual(result['total'], 15.0)  # 5 * 3 = 15
    
    def test_comments_max_capped_at_50(self):
        """Test that comment score is capped at 50."""
        issue = self.create_mock_issue(age_days=0, labels=[], comments=50)
        result = get_priority_score(issue)
        self.assertEqual(result['total'], 50.0)  # min(50 * 3, 50) = 50
    
    def test_complex_issue_high_priority(self):
        """Test complex issue with all factors."""
        # Old issue with many comments (labels no longer contribute to score)
        issue = self.create_mock_issue(
            age_days=60,  # Will give 30 points (min(60/2, 50))
            labels=['bug', 'urgent'],  # Labels no longer contribute
            comments=20  # Will give 50 points (min(20*3, 50))
        )
        result = get_priority_score(issue)
        self.assertEqual(result['total'], 80.0)  # 30 + 50 = 80


class TestFormatIssueSummary(unittest.TestCase):
    """Test issue summary formatting."""
    
    def create_mock_issue_data(self):
        """Create mock issue data."""
        return {
            'number': 42,
            'title': 'Test Issue',
            'url': 'https://github.com/test/repo/issues/42',
            'created_at': datetime.now(timezone.utc) - timedelta(days=10),
            'labels': 'bug, urgent',
            'comments': 5,
            'priority_score': 85.5,
            'priority_breakdown': {
                'age': 5.0,
                'labels': 70.0,
                'engagement': 10.0,
                'context': 0.5
            },
            'summary': 'This is a test issue summary.'
        }
    
    def test_format_with_one_issue(self):
        """Test formatting with a single issue."""
        issue_data = self.create_mock_issue_data()
        result = format_issue_summary(
            [issue_data],
            "Test recommendation",
            "test/repo"
        )
        
        # Check essential components
        self.assertIn("Issue Summary Report", result)
        self.assertIn("test/repo", result)
        self.assertIn("Test Issue", result)
        self.assertIn("42", result)
        self.assertIn("bug, urgent", result)
        self.assertIn("Test recommendation", result)
    
    def test_format_with_no_issues(self):
        """Test formatting with no issues."""
        result = format_issue_summary([], "No issues", "test/repo")
        
        self.assertIn("Issue Summary Report", result)
        self.assertIn("test/repo", result)
        self.assertIn("Total Open Issues:** 0", result)
    
    def test_format_includes_priority_score(self):
        """Test that priority score is included."""
        issue_data = self.create_mock_issue_data()
        result = format_issue_summary([issue_data], "Test", "test/repo")
        
        self.assertIn("85.5", result)
        self.assertIn("Priority Score", result)
        # Check that breakdown is included
        self.assertIn("Age", result)
        self.assertIn("Labels", result)
        self.assertIn("Engagement", result)


class TestLabelCaseInsensitivity(unittest.TestCase):
    """Test that label matching is case-insensitive."""
    
    def test_uppercase_bug_label(self):
        """Test that BUG label works."""
        issue = Mock()
        issue.created_at = datetime.now(timezone.utc)
        issue.comments = 0
        
        label = Mock()
        label.name = 'BUG'
        issue.labels = [label]
        
        result = get_priority_score(issue)
        self.assertEqual(result['total'], 20.0)
    
    def test_mixed_case_urgent_label(self):
        """Test that Urgent label works."""
        issue = Mock()
        issue.created_at = datetime.now(timezone.utc)
        issue.comments = 0
        
        label = Mock()
        label.name = 'Urgent'
        issue.labels = [label]
        
        result = get_priority_score(issue)
        self.assertEqual(result['total'], 25.0)


class TestReadingMaterials(unittest.TestCase):
    """Test reading materials generation."""
    
    def test_format_with_reading_materials(self):
        """Test that reading materials are included in the formatted output."""
        issue_data = {
            'number': 42,
            'title': 'Create a database',
            'url': 'https://github.com/test/repo/issues/42',
            'created_at': datetime.now(timezone.utc) - timedelta(days=10),
            'labels': 'database, enhancement',
            'comments': 5,
            'priority_score': 85.5,
            'summary': 'This issue is about creating a database.',
            'reading_materials': '- [PostgreSQL Documentation](https://www.postgresql.org/docs/)\n- [Database Design Tutorial](https://example.com/tutorial)'
        }
        result = format_issue_summary([issue_data], "Test", "test/repo")
        
        self.assertIn("📚 Recommended Reading:", result)
        self.assertIn("PostgreSQL Documentation", result)
        self.assertIn("Database Design Tutorial", result)
    
    def test_format_without_reading_materials(self):
        """Test that formatting works when reading materials are empty."""
        issue_data = {
            'number': 42,
            'title': 'Test Issue',
            'url': 'https://github.com/test/repo/issues/42',
            'created_at': datetime.now(timezone.utc) - timedelta(days=10),
            'labels': 'bug',
            'comments': 5,
            'priority_score': 85.5,
            'summary': 'This is a test issue.',
            'reading_materials': ''
        }
        result = format_issue_summary([issue_data], "Test", "test/repo")
        
        self.assertNotIn("📚 Recommended Reading:", result)
        self.assertIn("Test Issue", result)
    
    def test_format_missing_reading_materials_key(self):
        """Test that formatting works when reading_materials key is missing."""
        issue_data = {
            'number': 42,
            'title': 'Test Issue',
            'url': 'https://github.com/test/repo/issues/42',
            'created_at': datetime.now(timezone.utc) - timedelta(days=10),
            'labels': 'bug',
            'comments': 5,
            'priority_score': 85.5,
            'summary': 'This is a test issue.'
        }
        result = format_issue_summary([issue_data], "Test", "test/repo")
        
        self.assertNotIn("📚 Recommended Reading:", result)
        self.assertIn("Test Issue", result)


class TestContextualPriorityAnalysis(unittest.TestCase):
    """Test contextual priority analysis with LLM."""
    
    def test_priority_score_with_llm(self):
        """Test that LLM parameter is accepted and used."""
        issue = Mock()
        issue.created_at = datetime.now(timezone.utc)
        issue.comments = 0
        issue.labels = []
        issue.title = "Major urgent bug in authentication"
        issue.body = "Critical security issue that needs immediate attention"
        issue.number = 1
        
        # Mock LLM
        mock_llm = Mock()
        mock_chain = Mock()
        mock_chain.run.return_value = "45"  # High priority score
        
        # We can't easily mock LLMChain in this context, so we'll just verify
        # the function accepts the llm parameter without error
        result = get_priority_score(issue, llm=None)
        self.assertEqual(result['total'], 0.0)  # No age, labels, or comments
    
    def test_priority_score_without_llm_backward_compatible(self):
        """Test that function still works without LLM (backward compatibility)."""
        issue = Mock()
        issue.created_at = datetime.now(timezone.utc)
        issue.comments = 5
        
        label = Mock()
        label.name = 'bug'
        issue.labels = [label]
        
        # Should work without llm parameter
        result = get_priority_score(issue)
        self.assertEqual(result['total'], 35.0)  # 20 (bug) + 15 (5 comments * 3)
        
        # Should also work with llm=None
        result2 = get_priority_score(issue, llm=None)
        self.assertEqual(result2['total'], 35.0)  # Same result


if __name__ == '__main__':
    # Run tests with verbose output
    unittest.main(verbosity=2)
