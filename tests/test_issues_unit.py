"""Unit tests for issue operations with mocked GitHub API.

These tests use mocks and don't require GITHUB_TOKEN or network access.
Run with: pytest tests/test_issues_unit.py
"""

from datetime import datetime
from unittest.mock import Mock, patch

import pytest
from github import GithubObject

from github_mcp_server.tools.issues import close_issue, create_issues, list_issues


class TestListIssues:
    """Unit tests for list_issues tool."""

    @patch("github_mcp_server.tools.issues.get_github_client")
    def test_list_issues_default_open_state(self, mock_get_client: Mock) -> None:
        """Test listing open issues (default behavior)."""
        # Setup mocks
        mock_gh = Mock()
        mock_repo = Mock()
        mock_issue1 = Mock()
        mock_issue2 = Mock()

        # Configure issue 1
        mock_issue1.number = 123
        mock_issue1.title = "[Phase 4] Feature X"
        mock_issue1.state = "open"
        label1 = Mock()
        label1.name = "type: feature"
        label2 = Mock()
        label2.name = "priority: high"
        mock_issue1.labels = [label1, label2]
        mock_issue1.milestone = Mock(title="Phase 4")
        mock_issue1.assignee = Mock(login="testuser")
        mock_issue1.created_at = datetime(2025, 12, 1, 10, 0, 0)
        mock_issue1.updated_at = datetime(2025, 12, 15, 14, 30, 0)
        mock_issue1.html_url = "https://github.com/test/repo/issues/123"
        mock_issue1.pull_request = None  # Not a PR

        # Configure issue 2
        mock_issue2.number = 124
        mock_issue2.title = "[Phase 4] Feature Y"
        mock_issue2.state = "open"
        label3 = Mock()
        label3.name = "type: bug"
        mock_issue2.labels = [label3]
        mock_issue2.milestone = None
        mock_issue2.assignee = None
        mock_issue2.created_at = datetime(2025, 12, 2, 11, 0, 0)
        mock_issue2.updated_at = datetime(2025, 12, 16, 15, 0, 0)
        mock_issue2.html_url = "https://github.com/test/repo/issues/124"
        mock_issue2.pull_request = None  # Not a PR

        mock_repo.get_issues.return_value = [mock_issue1, mock_issue2]
        mock_gh.get_repo.return_value = mock_repo
        mock_get_client.return_value = mock_gh

        # Execute
        result = list_issues()

        # Verify
        assert result["total"] == 2
        assert result["count"] == 2
        assert len(result["issues"]) == 2

        # Verify first issue
        assert result["issues"][0]["number"] == 123
        assert result["issues"][0]["title"] == "[Phase 4] Feature X"
        assert result["issues"][0]["state"] == "open"
        assert "type: feature" in result["issues"][0]["labels"]
        assert "priority: high" in result["issues"][0]["labels"]
        assert result["issues"][0]["milestone"] == "Phase 4"
        assert result["issues"][0]["assignee"] == "testuser"
        assert result["issues"][0]["url"] == "https://github.com/test/repo/issues/123"

        # Verify GitHub API was called correctly
        mock_repo.get_issues.assert_called_once()
        call_kwargs = mock_repo.get_issues.call_args[1]
        assert call_kwargs["state"] == "open"

    @patch("github_mcp_server.tools.issues.get_github_client")
    def test_list_issues_closed_state(self, mock_get_client: Mock) -> None:
        """Test listing closed issues."""
        mock_gh = Mock()
        mock_repo = Mock()
        mock_issue = Mock()

        mock_issue.number = 100
        mock_issue.title = "Completed Feature"
        mock_issue.state = "closed"
        mock_issue.labels = []
        mock_issue.milestone = None
        mock_issue.assignee = None
        mock_issue.created_at = datetime(2025, 11, 1, 10, 0, 0)
        mock_issue.updated_at = datetime(2025, 11, 15, 14, 30, 0)
        mock_issue.html_url = "https://github.com/test/repo/issues/100"
        mock_issue.pull_request = None  # Not a PR

        mock_repo.get_issues.return_value = [mock_issue]
        mock_gh.get_repo.return_value = mock_repo
        mock_get_client.return_value = mock_gh

        # Execute
        result = list_issues(state="closed")

        # Verify
        assert result["total"] == 1
        assert result["issues"][0]["state"] == "closed"

        # Verify API call
        call_kwargs = mock_repo.get_issues.call_args[1]
        assert call_kwargs["state"] == "closed"

    @patch("github_mcp_server.tools.issues.get_github_client")
    def test_list_issues_all_state(self, mock_get_client: Mock) -> None:
        """Test listing all issues (open + closed)."""
        mock_gh = Mock()
        mock_repo = Mock()

        mock_issue1 = Mock()
        mock_issue1.number = 123
        mock_issue1.title = "Open Issue"
        mock_issue1.state = "open"
        mock_issue1.labels = []
        mock_issue1.milestone = None
        mock_issue1.assignee = None
        mock_issue1.created_at = datetime(2025, 12, 1, 10, 0, 0)
        mock_issue1.updated_at = datetime(2025, 12, 15, 14, 30, 0)
        mock_issue1.html_url = "https://github.com/test/repo/issues/123"
        mock_issue1.pull_request = None  # Not a PR

        mock_issue2 = Mock()
        mock_issue2.number = 100
        mock_issue2.title = "Closed Issue"
        mock_issue2.state = "closed"
        mock_issue2.labels = []
        mock_issue2.milestone = None
        mock_issue2.assignee = None
        mock_issue2.created_at = datetime(2025, 11, 1, 10, 0, 0)
        mock_issue2.updated_at = datetime(2025, 11, 15, 14, 30, 0)
        mock_issue2.html_url = "https://github.com/test/repo/issues/100"
        mock_issue2.pull_request = None  # Not a PR

        mock_repo.get_issues.return_value = [mock_issue1, mock_issue2]
        mock_gh.get_repo.return_value = mock_repo
        mock_get_client.return_value = mock_gh

        # Execute
        result = list_issues(state="all")

        # Verify
        assert result["total"] == 2
        assert result["issues"][0]["state"] == "open"
        assert result["issues"][1]["state"] == "closed"

        # Verify API call
        call_kwargs = mock_repo.get_issues.call_args[1]
        assert call_kwargs["state"] == "all"

    @patch("github_mcp_server.tools.issues.get_github_client")
    def test_list_issues_filter_by_single_label(self, mock_get_client: Mock) -> None:
        """Test filtering issues by a single label."""
        mock_gh = Mock()
        mock_repo = Mock()
        mock_label = Mock()
        mock_label.name = "type: feature"

        mock_issue = Mock()
        mock_issue.number = 123
        mock_issue.title = "Feature Issue"
        mock_issue.state = "open"
        mock_issue.labels = [mock_label]
        mock_issue.milestone = None
        mock_issue.assignee = None
        mock_issue.created_at = datetime(2025, 12, 1, 10, 0, 0)
        mock_issue.updated_at = datetime(2025, 12, 15, 14, 30, 0)
        mock_issue.html_url = "https://github.com/test/repo/issues/123"
        mock_issue.pull_request = None  # Not a PR

        mock_repo.get_issues.return_value = [mock_issue]
        mock_gh.get_repo.return_value = mock_repo
        mock_get_client.return_value = mock_gh

        # Execute
        result = list_issues(labels=["type: feature"])

        # Verify
        assert result["total"] == 1
        assert "type: feature" in result["issues"][0]["labels"]

        # Verify API call
        call_kwargs = mock_repo.get_issues.call_args[1]
        assert call_kwargs["labels"] == ["type: feature"]

    @patch("github_mcp_server.tools.issues.get_github_client")
    def test_list_issues_filter_by_multiple_labels(self, mock_get_client: Mock) -> None:
        """Test filtering issues by multiple labels."""
        mock_gh = Mock()
        mock_repo = Mock()

        mock_issue = Mock()
        mock_issue.number = 123
        mock_issue.title = "High Priority Feature"
        mock_issue.state = "open"
        label1 = Mock()
        label1.name = "type: feature"
        label2 = Mock()
        label2.name = "priority: high"
        mock_issue.labels = [label1, label2]
        mock_issue.milestone = None
        mock_issue.assignee = None
        mock_issue.created_at = datetime(2025, 12, 1, 10, 0, 0)
        mock_issue.updated_at = datetime(2025, 12, 15, 14, 30, 0)
        mock_issue.html_url = "https://github.com/test/repo/issues/123"
        mock_issue.pull_request = None  # Not a PR

        mock_repo.get_issues.return_value = [mock_issue]
        mock_gh.get_repo.return_value = mock_repo
        mock_get_client.return_value = mock_gh

        # Execute
        result = list_issues(labels=["type: feature", "priority: high"])

        # Verify
        assert result["total"] == 1
        assert "type: feature" in result["issues"][0]["labels"]
        assert "priority: high" in result["issues"][0]["labels"]

        # Verify API call
        call_kwargs = mock_repo.get_issues.call_args[1]
        assert call_kwargs["labels"] == ["type: feature", "priority: high"]

    @patch("github_mcp_server.tools.issues.get_github_client")
    def test_list_issues_filter_by_milestone(self, mock_get_client: Mock) -> None:
        """Test filtering issues by milestone."""
        mock_gh = Mock()
        mock_repo = Mock()
        mock_milestone = Mock()
        mock_milestone.title = "Phase 4"
        mock_milestone.number = 7

        mock_issue = Mock()
        mock_issue.number = 123
        mock_issue.title = "Phase 4 Feature"
        mock_issue.state = "open"
        mock_issue.labels = []
        mock_issue.milestone = mock_milestone
        mock_issue.assignee = None
        mock_issue.created_at = datetime(2025, 12, 1, 10, 0, 0)
        mock_issue.updated_at = datetime(2025, 12, 15, 14, 30, 0)
        mock_issue.html_url = "https://github.com/test/repo/issues/123"
        mock_issue.pull_request = None  # Not a PR

        mock_repo.get_issues.return_value = [mock_issue]
        mock_repo.get_milestones.return_value = [mock_milestone]  # Returns list of milestones
        mock_gh.get_repo.return_value = mock_repo
        mock_get_client.return_value = mock_gh

        # Execute
        result = list_issues(milestone="Phase 4")

        # Verify
        assert result["total"] == 1
        assert result["issues"][0]["milestone"] == "Phase 4"

        # Verify API call
        call_kwargs = mock_repo.get_issues.call_args[1]
        assert call_kwargs["milestone"] == mock_milestone

    @patch("github_mcp_server.tools.issues.get_github_client")
    def test_list_issues_filter_by_assignee(self, mock_get_client: Mock) -> None:
        """Test filtering issues by assignee."""
        mock_gh = Mock()
        mock_repo = Mock()
        mock_assignee = Mock()
        mock_assignee.login = "testuser"

        mock_issue = Mock()
        mock_issue.number = 123
        mock_issue.title = "Assigned Issue"
        mock_issue.state = "open"
        mock_issue.labels = []
        mock_issue.milestone = None
        mock_issue.assignee = mock_assignee
        mock_issue.created_at = datetime(2025, 12, 1, 10, 0, 0)
        mock_issue.updated_at = datetime(2025, 12, 15, 14, 30, 0)
        mock_issue.html_url = "https://github.com/test/repo/issues/123"
        mock_issue.pull_request = None  # Not a PR

        mock_repo.get_issues.return_value = [mock_issue]
        mock_gh.get_repo.return_value = mock_repo
        mock_get_client.return_value = mock_gh

        # Execute
        result = list_issues(assignee="testuser")

        # Verify
        assert result["total"] == 1
        assert result["issues"][0]["assignee"] == "testuser"

        # Verify API call
        call_kwargs = mock_repo.get_issues.call_args[1]
        assert call_kwargs["assignee"] == "testuser"

    @patch("github_mcp_server.tools.issues.get_github_client")
    def test_list_issues_filter_unassigned(self, mock_get_client: Mock) -> None:
        """Test filtering for unassigned issues."""
        mock_gh = Mock()
        mock_repo = Mock()

        mock_issue = Mock()
        mock_issue.number = 123
        mock_issue.title = "Unassigned Issue"
        mock_issue.state = "open"
        mock_issue.labels = []
        mock_issue.milestone = None
        mock_issue.assignee = None
        mock_issue.created_at = datetime(2025, 12, 1, 10, 0, 0)
        mock_issue.updated_at = datetime(2025, 12, 15, 14, 30, 0)
        mock_issue.html_url = "https://github.com/test/repo/issues/123"
        mock_issue.pull_request = None  # Not a PR

        mock_repo.get_issues.return_value = [mock_issue]
        mock_gh.get_repo.return_value = mock_repo
        mock_get_client.return_value = mock_gh

        # Execute
        result = list_issues(assignee="none")

        # Verify
        assert result["total"] == 1
        assert result["issues"][0]["assignee"] is None

        # Verify API call
        call_kwargs = mock_repo.get_issues.call_args[1]
        assert call_kwargs["assignee"] == "none"

    @patch("github_mcp_server.tools.issues.get_github_client")
    def test_list_issues_sort_by_updated(self, mock_get_client: Mock) -> None:
        """Test sorting issues by updated timestamp."""
        mock_gh = Mock()
        mock_repo = Mock()
        mock_issue = Mock()

        mock_issue.number = 123
        mock_issue.title = "Test Issue"
        mock_issue.state = "open"
        mock_issue.labels = []
        mock_issue.milestone = None
        mock_issue.assignee = None
        mock_issue.created_at = datetime(2025, 12, 1, 10, 0, 0)
        mock_issue.updated_at = datetime(2025, 12, 15, 14, 30, 0)
        mock_issue.html_url = "https://github.com/test/repo/issues/123"
        mock_issue.pull_request = None  # Not a PR

        mock_repo.get_issues.return_value = [mock_issue]
        mock_gh.get_repo.return_value = mock_repo
        mock_get_client.return_value = mock_gh

        # Execute
        result = list_issues(sort="updated", direction="asc")

        # Verify API call
        call_kwargs = mock_repo.get_issues.call_args[1]
        assert call_kwargs["sort"] == "updated"
        assert call_kwargs["direction"] == "asc"
        assert result is not None

    @patch("github_mcp_server.tools.issues.get_github_client")
    def test_list_issues_pagination_limit(self, mock_get_client: Mock) -> None:
        """Test pagination with limit parameter."""
        mock_gh = Mock()
        mock_repo = Mock()

        # Create 100 mock issues but limit to 10
        mock_issues = []
        for i in range(100):
            mock_issue = Mock()
            mock_issue.number = i + 1
            mock_issue.title = f"Issue {i + 1}"
            mock_issue.state = "open"
            mock_issue.labels = []
            mock_issue.milestone = None
            mock_issue.assignee = None
            mock_issue.created_at = datetime(2025, 12, 1, 10, 0, 0)
            mock_issue.updated_at = datetime(2025, 12, 15, 14, 30, 0)
            mock_issue.html_url = f"https://github.com/test/repo/issues/{i + 1}"
            mock_issue.pull_request = None  # Not a PR
            mock_issues.append(mock_issue)

        # PyGithub returns paginated list - we'll return first 10
        mock_repo.get_issues.return_value = mock_issues[:10]
        mock_gh.get_repo.return_value = mock_repo
        mock_get_client.return_value = mock_gh

        # Execute
        result = list_issues(limit=10)

        # Verify
        assert result["count"] == 10
        assert len(result["issues"]) == 10

    @patch("github_mcp_server.tools.issues.get_github_client")
    def test_list_issues_empty_results(self, mock_get_client: Mock) -> None:
        """Test listing issues when no results match filters."""
        mock_gh = Mock()
        mock_repo = Mock()
        mock_repo.get_issues.return_value = []
        mock_gh.get_repo.return_value = mock_repo
        mock_get_client.return_value = mock_gh

        # Execute
        result = list_issues(labels=["nonexistent-label"])

        # Verify
        assert result["total"] == 0
        assert result["count"] == 0
        assert result["issues"] == []

    @patch("github_mcp_server.tools.issues.get_github_client")
    def test_list_issues_invalid_state_raises_error(self, mock_get_client: Mock) -> None:
        """Test that invalid state value raises error."""
        from github_mcp_server.utils.errors import GitHubAPIError

        mock_gh = Mock()
        mock_repo = Mock()
        mock_repo.get_issues.side_effect = Exception("Invalid state")
        mock_gh.get_repo.return_value = mock_repo
        mock_get_client.return_value = mock_gh

        # Execute and verify error
        with pytest.raises(GitHubAPIError):
            list_issues(state="invalid")

    @patch("github_mcp_server.tools.issues.get_github_client")
    def test_list_issues_nonexistent_milestone_returns_empty(self, mock_get_client: Mock) -> None:
        """Test that non-existent milestone returns empty list."""
        mock_gh = Mock()
        mock_repo = Mock()

        # Mock milestone search returning None (no matching milestone)
        mock_repo.get_milestones.return_value = []
        mock_gh.get_repo.return_value = mock_repo
        mock_get_client.return_value = mock_gh

        # Execute
        result = list_issues(milestone="Nonexistent Milestone")

        # Verify
        assert result["total"] == 0
        assert result["count"] == 0
        assert result["issues"] == []

    @patch("github_mcp_server.tools.issues.get_github_client")
    def test_list_issues_combined_filters(self, mock_get_client: Mock) -> None:
        """Test combining multiple filters together."""
        mock_gh = Mock()
        mock_repo = Mock()
        mock_milestone = Mock()
        mock_milestone.title = "Phase 4"
        mock_milestone.number = 7

        mock_issue = Mock()
        mock_issue.number = 123
        mock_issue.title = "High Priority Phase 4 Feature"
        mock_issue.state = "open"
        label1 = Mock()
        label1.name = "type: feature"
        label2 = Mock()
        label2.name = "priority: high"
        mock_issue.labels = [label1, label2]
        mock_issue.milestone = mock_milestone
        mock_issue.assignee = Mock(login="testuser")
        mock_issue.created_at = datetime(2025, 12, 1, 10, 0, 0)
        mock_issue.updated_at = datetime(2025, 12, 15, 14, 30, 0)
        mock_issue.html_url = "https://github.com/test/repo/issues/123"
        mock_issue.pull_request = None  # Not a PR

        mock_repo.get_issues.return_value = [mock_issue]
        mock_repo.get_milestones.return_value = [mock_milestone]  # Returns list of milestones
        mock_gh.get_repo.return_value = mock_repo
        mock_get_client.return_value = mock_gh

        # Execute with multiple filters
        result = list_issues(
            state="open",
            labels=["type: feature", "priority: high"],
            milestone="Phase 4",
            assignee="testuser",
        )

        # Verify
        assert result["total"] == 1
        assert result["issues"][0]["number"] == 123
        assert "type: feature" in result["issues"][0]["labels"]
        assert "priority: high" in result["issues"][0]["labels"]
        assert result["issues"][0]["milestone"] == "Phase 4"
        assert result["issues"][0]["assignee"] == "testuser"

    @patch("github_mcp_server.tools.issues.get_github_client")
    def test_list_issues_custom_owner_repo(self, mock_get_client: Mock) -> None:
        """Test listing issues from custom owner/repo."""
        mock_gh = Mock()
        mock_repo = Mock()
        mock_issue = Mock()

        mock_issue.number = 1
        mock_issue.title = "Test Issue"
        mock_issue.state = "open"
        mock_issue.labels = []
        mock_issue.milestone = None
        mock_issue.assignee = None
        mock_issue.created_at = datetime(2025, 12, 1, 10, 0, 0)
        mock_issue.updated_at = datetime(2025, 12, 15, 14, 30, 0)
        mock_issue.html_url = "https://github.com/custom/repo/issues/1"
        mock_issue.pull_request = None  # Not a PR

        mock_repo.get_issues.return_value = [mock_issue]
        mock_gh.get_repo.return_value = mock_repo
        mock_get_client.return_value = mock_gh

        # Execute
        result = list_issues(owner="custom", repo="repo")

        # Verify API was called with correct repo
        mock_gh.get_repo.assert_called_once_with("custom/repo")
        assert result is not None


class TestCloseIssue:
    """Unit tests for close_issue tool."""

    @patch("github_mcp_server.tools.issues.get_github_client")
    def test_close_issue_without_comment(self, mock_get_client: Mock) -> None:
        """Test closing issue without adding a comment."""
        # Setup mocks
        mock_gh = Mock()
        mock_repo = Mock()
        mock_issue = Mock()

        mock_issue.number = 123
        mock_issue.state = "closed"
        mock_issue.html_url = "https://github.com/test/repo/issues/123"

        mock_repo.get_issue.return_value = mock_issue
        mock_gh.get_repo.return_value = mock_repo
        mock_get_client.return_value = mock_gh

        # Execute
        result = close_issue(issue_number=123)

        # Verify
        assert result["number"] == 123
        assert result["state"] == "closed"
        assert result["comment_added"] is False
        assert result["url"] == "https://github.com/test/repo/issues/123"

        # Verify API calls
        mock_repo.get_issue.assert_called_once_with(123)
        mock_issue.edit.assert_called_once_with(state="closed", state_reason=GithubObject.NotSet)
        mock_issue.create_comment.assert_not_called()

    @patch("github_mcp_server.tools.issues.get_github_client")
    def test_close_issue_with_comment(self, mock_get_client: Mock) -> None:
        """Test closing issue with a comment."""
        mock_gh = Mock()
        mock_repo = Mock()
        mock_issue = Mock()

        mock_issue.number = 123
        mock_issue.state = "closed"
        mock_issue.html_url = "https://github.com/test/repo/issues/123"

        mock_repo.get_issue.return_value = mock_issue
        mock_gh.get_repo.return_value = mock_repo
        mock_get_client.return_value = mock_gh

        # Execute
        result = close_issue(issue_number=123, comment="Resolved in PR #456")

        # Verify
        assert result["number"] == 123
        assert result["state"] == "closed"
        assert result["comment_added"] is True
        assert result["url"] == "https://github.com/test/repo/issues/123"

        # Verify API calls
        mock_issue.create_comment.assert_called_once_with("Resolved in PR #456")
        mock_issue.edit.assert_called_once_with(state="closed", state_reason=GithubObject.NotSet)

    @patch("github_mcp_server.tools.issues.get_github_client")
    def test_close_issue_with_state_reason_completed(self, mock_get_client: Mock) -> None:
        """Test closing issue with state_reason='completed'."""
        mock_gh = Mock()
        mock_repo = Mock()
        mock_issue = Mock()

        mock_issue.number = 123
        mock_issue.state = "closed"
        mock_issue.state_reason = "completed"
        mock_issue.html_url = "https://github.com/test/repo/issues/123"

        mock_repo.get_issue.return_value = mock_issue
        mock_gh.get_repo.return_value = mock_repo
        mock_get_client.return_value = mock_gh

        # Execute
        result = close_issue(issue_number=123, state_reason="completed")

        # Verify
        assert result["number"] == 123
        assert result["state"] == "closed"
        assert result["state_reason"] == "completed"

        # Verify API call
        mock_issue.edit.assert_called_once_with(state="closed", state_reason="completed")

    @patch("github_mcp_server.tools.issues.get_github_client")
    def test_close_issue_with_state_reason_not_planned(self, mock_get_client: Mock) -> None:
        """Test closing issue with state_reason='not_planned'."""
        mock_gh = Mock()
        mock_repo = Mock()
        mock_issue = Mock()

        mock_issue.number = 123
        mock_issue.state = "closed"
        mock_issue.state_reason = "not_planned"
        mock_issue.html_url = "https://github.com/test/repo/issues/123"

        mock_repo.get_issue.return_value = mock_issue
        mock_gh.get_repo.return_value = mock_repo
        mock_get_client.return_value = mock_gh

        # Execute
        result = close_issue(issue_number=123, state_reason="not_planned")

        # Verify
        assert result["number"] == 123
        assert result["state"] == "closed"
        assert result["state_reason"] == "not_planned"

        # Verify API call
        mock_issue.edit.assert_called_once_with(state="closed", state_reason="not_planned")

    @patch("github_mcp_server.tools.issues.get_github_client")
    def test_close_issue_already_closed(self, mock_get_client: Mock) -> None:
        """Test closing an issue that is already closed."""
        mock_gh = Mock()
        mock_repo = Mock()
        mock_issue = Mock()

        mock_issue.number = 123
        mock_issue.state = "closed"
        mock_issue.state_reason = "completed"
        mock_issue.html_url = "https://github.com/test/repo/issues/123"

        mock_repo.get_issue.return_value = mock_issue
        mock_gh.get_repo.return_value = mock_repo
        mock_get_client.return_value = mock_gh

        # Execute - should not raise error
        result = close_issue(issue_number=123)

        # Verify - returns current state
        assert result["number"] == 123
        assert result["state"] == "closed"
        assert result["url"] == "https://github.com/test/repo/issues/123"

        # Still calls edit (idempotent operation)
        mock_issue.edit.assert_called_once()

    @patch("github_mcp_server.tools.issues.get_github_client")
    def test_close_issue_nonexistent_raises_error(self, mock_get_client: Mock) -> None:
        """Test closing non-existent issue raises error."""
        from github_mcp_server.utils.errors import GitHubAPIError

        mock_gh = Mock()
        mock_repo = Mock()
        mock_repo.get_issue.side_effect = Exception("Issue not found")
        mock_gh.get_repo.return_value = mock_repo
        mock_get_client.return_value = mock_gh

        # Execute and verify error
        with pytest.raises(GitHubAPIError):
            close_issue(issue_number=99999)

    @patch("github_mcp_server.tools.issues.get_github_client")
    def test_close_issue_with_comment_and_state_reason(self, mock_get_client: Mock) -> None:
        """Test closing issue with both comment and state_reason."""
        mock_gh = Mock()
        mock_repo = Mock()
        mock_issue = Mock()

        mock_issue.number = 123
        mock_issue.state = "closed"
        mock_issue.state_reason = "completed"
        mock_issue.html_url = "https://github.com/test/repo/issues/123"

        mock_repo.get_issue.return_value = mock_issue
        mock_gh.get_repo.return_value = mock_repo
        mock_get_client.return_value = mock_gh

        # Execute
        result = close_issue(
            issue_number=123,
            comment="Fixed by implementing new feature",
            state_reason="completed",
        )

        # Verify
        assert result["number"] == 123
        assert result["state"] == "closed"
        assert result["comment_added"] is True
        assert result["state_reason"] == "completed"

        # Verify API calls - comment before closing
        mock_issue.create_comment.assert_called_once_with("Fixed by implementing new feature")
        mock_issue.edit.assert_called_once_with(state="closed", state_reason="completed")

    @patch("github_mcp_server.tools.issues.get_github_client")
    def test_close_issue_custom_owner_repo(self, mock_get_client: Mock) -> None:
        """Test closing issue in custom owner/repo."""
        mock_gh = Mock()
        mock_repo = Mock()
        mock_issue = Mock()

        mock_issue.number = 42
        mock_issue.state = "closed"
        mock_issue.html_url = "https://github.com/custom/repo/issues/42"

        mock_repo.get_issue.return_value = mock_issue
        mock_gh.get_repo.return_value = mock_repo
        mock_get_client.return_value = mock_gh

        # Execute
        result = close_issue(issue_number=42, owner="custom", repo="repo")

        # Verify API was called with correct repo
        mock_gh.get_repo.assert_called_once_with("custom/repo")
        assert result["number"] == 42


class TestCreateIssues:
    """Unit tests for create_issues tool (unified single/batch)."""

    @patch("github_mcp_server.tools.issues.get_github_client")
    def test_create_single_issue_success(self, mock_get_client: Mock) -> None:
        """Test creating a single issue via create_issues."""
        mock_gh = Mock()
        mock_repo = Mock()
        mock_milestone = Mock()
        mock_issue = Mock()

        label_test = Mock()
        label_test.name = "test"

        mock_issue.number = 123
        mock_issue.html_url = "https://github.com/test/repo/issues/123"
        mock_issue.state = "open"
        mock_issue.title = "Test Issue"
        mock_issue.labels = [label_test]
        mock_issue.milestone = mock_milestone
        mock_milestone.title = "v1.0"

        mock_repo.get_milestone.return_value = mock_milestone
        mock_repo.create_issue.return_value = mock_issue
        mock_gh.get_repo.return_value = mock_repo
        mock_get_client.return_value = mock_gh

        result = create_issues(
            issues=[{"title": "Test Issue", "body": "Body", "labels": ["test"], "milestone": 7}]
        )

        assert result["total"] == 1
        assert result["successful"] == 1
        assert result["failed"] == 0
        assert result["results"][0]["success"] is True
        assert result["results"][0]["data"]["issue_number"] == 123

    @patch("github_mcp_server.tools.issues.get_github_client")
    def test_create_multiple_issues_success(self, mock_get_client: Mock) -> None:
        """Test creating multiple issues in batch."""
        mock_gh = Mock()
        mock_repo = Mock()

        def create_issue_side_effect(**kwargs):
            issue_mock = Mock()
            issue_mock.number = 100 + len(mock_repo.create_issue.call_args_list)
            issue_mock.html_url = f"https://github.com/test/repo/issues/{issue_mock.number}"
            issue_mock.state = "open"
            issue_mock.title = kwargs["title"]
            issue_mock.labels = []
            issue_mock.milestone = None
            return issue_mock

        mock_repo.create_issue.side_effect = create_issue_side_effect
        mock_gh.get_repo.return_value = mock_repo
        mock_get_client.return_value = mock_gh

        result = create_issues(
            issues=[
                {"title": "Issue 1"},
                {"title": "Issue 2"},
                {"title": "Issue 3"},
            ]
        )

        assert result["total"] == 3
        assert result["successful"] == 3
        assert result["failed"] == 0
        assert result["success_rate"] == "100.0%"

    def test_create_issues_empty_list_raises_error(self) -> None:
        """Test that empty issues list raises ValueError."""
        with pytest.raises(ValueError, match="cannot be empty"):
            create_issues(issues=[])

    def test_create_issues_too_many_raises_error(self) -> None:
        """Test that exceeding max limit raises ValueError."""
        large_batch = [{"title": f"Issue {i}"} for i in range(51)]

        with pytest.raises(ValueError, match="Maximum 50 issues"):
            create_issues(issues=large_batch)

    @patch("github_mcp_server.tools.issues.get_github_client")
    def test_create_issues_missing_title_fails(self, mock_get_client: Mock) -> None:
        """Test that missing title causes failure in result."""
        result = create_issues(issues=[{"body": "No title"}])

        assert result["total"] == 1
        assert result["successful"] == 0
        assert result["failed"] == 1
        assert result["results"][0]["success"] is False

    @patch("github_mcp_server.tools.issues.get_github_client")
    def test_create_issues_partial_failures(self, mock_get_client: Mock) -> None:
        """Test batch handles partial failures correctly."""
        mock_gh = Mock()
        mock_repo = Mock()

        call_count = [0]

        def create_issue_side_effect(**kwargs):
            call_count[0] += 1
            if call_count[0] == 2:
                raise Exception("API Error")

            issue_mock = Mock()
            issue_mock.number = 100 + call_count[0]
            issue_mock.html_url = f"https://github.com/test/repo/issues/{issue_mock.number}"
            issue_mock.state = "open"
            issue_mock.title = kwargs["title"]
            issue_mock.labels = []
            issue_mock.milestone = None
            return issue_mock

        mock_repo.create_issue.side_effect = create_issue_side_effect
        mock_gh.get_repo.return_value = mock_repo
        mock_get_client.return_value = mock_gh

        result = create_issues(
            issues=[
                {"title": "Issue 1"},
                {"title": "Issue 2"},
                {"title": "Issue 3"},
            ]
        )

        assert result["total"] == 3
        assert result["successful"] == 2
        assert result["failed"] == 1
