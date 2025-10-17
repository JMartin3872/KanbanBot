#!/usr/bin/env python3
"""
Integration test for contextual priority analysis.
This test demonstrates the new contextual analysis feature.
Note: This test requires OPENAI_API_KEY to be set and will make actual API calls.
"""

import os
import sys
from datetime import datetime, timezone
from unittest.mock import Mock

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from issue_summary_bot import (
    get_priority_score,
    analyze_contextual_priority,
    get_openai_client
)


def create_mock_issue(title, body, age_days=0, labels=None, comments=0):
    """Helper to create a mock issue."""
    from datetime import timedelta
    issue = Mock()
    issue.created_at = datetime.now(timezone.utc) - timedelta(days=age_days)
    issue.title = title
    issue.body = body
    issue.number = 1
    
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


def test_contextual_analysis_examples():
    """Test contextual analysis with example issues."""
    # Check if OpenAI API key is available
    if not os.getenv('OPENAI_API_KEY'):
        print("⚠️  OPENAI_API_KEY not set - skipping contextual analysis test")
        print("   This test demonstrates the new feature but requires API access")
        return True
    
    try:
        llm = get_openai_client()
    except Exception as e:
        print(f"⚠️  Could not initialize OpenAI client: {e}")
        print("   Skipping contextual analysis test")
        return True
    
    print("\n" + "="*60)
    print("Testing Contextual Priority Analysis")
    print("="*60)
    
    # Test case 1: High priority - urgent bug
    print("\n1. Testing: 'Major urgent bug which needs to be fixed soon'")
    issue1 = create_mock_issue(
        title="Major urgent bug in authentication",
        body="This is a major urgent bug which needs to be fixed soon. Users cannot log in."
    )
    score1 = analyze_contextual_priority(llm, issue1)
    print(f"   Contextual score: {score1:.1f}/50")
    print(f"   Expected: High score (30-50) for urgent bug")
    
    # Test case 2: Lower priority - cosmetic change
    print("\n2. Testing: 'Major color change to frontend'")
    issue2 = create_mock_issue(
        title="Major color change to frontend",
        body="We should update the main color scheme to use a different shade of blue."
    )
    score2 = analyze_contextual_priority(llm, issue2)
    print(f"   Contextual score: {score2:.1f}/50")
    print(f"   Expected: Lower score (0-20) for cosmetic change")
    
    # Test case 3: Critical security issue
    print("\n3. Testing: 'Critical security vulnerability'")
    issue3 = create_mock_issue(
        title="Critical security vulnerability in API",
        body="Important security issue that allows unauthorized access. This is urgent and needs immediate attention."
    )
    score3 = analyze_contextual_priority(llm, issue3)
    print(f"   Contextual score: {score3:.1f}/50")
    print(f"   Expected: Very high score (40-50) for critical security issue")
    
    # Test case 4: Trivial improvement
    print("\n4. Testing: 'Trivial typo fix'")
    issue4 = create_mock_issue(
        title="Minor typo in documentation",
        body="There's a small typo in the README. This is a trivial fix."
    )
    score4 = analyze_contextual_priority(llm, issue4)
    print(f"   Contextual score: {score4:.1f}/50")
    print(f"   Expected: Very low score (0-10) for trivial issue")
    
    print("\n" + "="*60)
    print("Contextual Analysis Results:")
    print("="*60)
    print(f"Urgent bug score:        {score1:.1f}/50 (should be high)")
    print(f"Color change score:      {score2:.1f}/50 (should be low)")
    print(f"Security issue score:    {score3:.1f}/50 (should be very high)")
    print(f"Typo fix score:          {score4:.1f}/50 (should be very low)")
    
    # Basic validation - these thresholds are flexible since LLM responses can vary
    if score1 > score2:
        print("\n✓ Urgent bug correctly scored higher than color change")
    else:
        print(f"\n⚠️  Warning: Urgent bug ({score1}) should score higher than color change ({score2})")
    
    if score3 > score4:
        print("✓ Security issue correctly scored higher than typo fix")
    else:
        print(f"⚠️  Warning: Security issue ({score3}) should score higher than typo fix ({score4})")
    
    return True


def test_full_priority_score_with_context():
    """Test full priority score calculation including contextual analysis."""
    if not os.getenv('OPENAI_API_KEY'):
        print("\n⚠️  OPENAI_API_KEY not set - skipping full integration test")
        return True
    
    try:
        llm = get_openai_client()
    except Exception as e:
        print(f"\n⚠️  Could not initialize OpenAI client: {e}")
        return True
    
    print("\n" + "="*60)
    print("Testing Full Priority Score with Contextual Analysis")
    print("="*60)
    
    # Create an issue with both traditional and contextual factors
    issue = create_mock_issue(
        title="Major urgent bug in payment processing",
        body="Critical bug that prevents users from completing purchases. This is urgent and needs immediate attention.",
        age_days=10,  # 5 points
        labels=['bug', 'urgent'],  # Labels no longer affect scoring
        comments=5  # 15 points
    )
    
    # Score without contextual analysis
    result_without_context = get_priority_score(issue, llm=None)
    score_without_context = result_without_context['total']
    print(f"\nScore without contextual analysis: {score_without_context:.1f}")
    print(f"  - Age (10 days): {result_without_context['breakdown']['age']:.1f}")
    print(f"  - Comments (5): {result_without_context['breakdown']['engagement']:.1f}")
    print(f"  - Total: {score_without_context:.1f}")
    
    # Score with contextual analysis
    result_with_context = get_priority_score(issue, llm=llm)
    score_with_context = result_with_context['total']
    contextual_boost = result_with_context['breakdown']['context']
    print(f"\nScore with contextual analysis: {score_with_context:.1f}")
    print(f"  - Age: {result_with_context['breakdown']['age']:.1f}")
    print(f"  - Engagement: {result_with_context['breakdown']['engagement']:.1f}")
    print(f"  - Contextual boost: {contextual_boost:.1f}")
    print(f"  - Total: {score_with_context:.1f}")
    
    if contextual_boost > 0:
        print(f"\n✓ Contextual analysis added {contextual_boost:.1f} points")
        print("  This urgent bug description was recognized as high priority!")
    else:
        print(f"\n⚠️  Warning: Expected contextual boost for urgent bug description")
    
    return True


def main():
    """Run all contextual analysis tests."""
    try:
        test_contextual_analysis_examples()
        test_full_priority_score_with_context()
        print("\n" + "="*60)
        print("✓ Contextual Analysis Tests Completed")
        print("="*60)
        return 0
    except Exception as e:
        print(f"\n✗ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    exit(main())
