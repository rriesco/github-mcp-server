"""Unit tests for milestone operations with mocked GitHub API.

These tests use mocks and don't require GITHUB_TOKEN or network access.
Run with: pytest tests/test_milestones_unit.py
"""

from datetime import datetime
from unittest.mock import Mock, patch

import pytest
from github_mcp_server.tools.milestones import create_milestone, list_milestones


class TestCreateMilestone:
    """Unit tests for create_milestone tool."""

    @patch("github_mcp_server.tools.milestones.get_github_client")
    def test_create_milestone_basic(self, mock_get_client: Mock) -> None:
        """Test creating a milestone with title and description only."""
        # Setup mocks
        mock_gh = Mock()
        mock_repo = Mock()
        mock_milestone = Mock()

        # Configure milestone
        mock_milestone.number = 8
        mock_milestone.title = "Phase 4: Essential Tools"
        mock_milestone.description = "Implement 8 essential MCP tools"
        mock_milestone.state = "open"
        mock_milestone.due_on = None
        mock_milestone.html_url = "https://github.com/testowner/testrepo/milestone/8"

        mock_repo.create_milestone.return_value = mock_milestone
        mock_gh.get_repo.return_value = mock_repo
        mock_get_client.return_value = mock_gh

        # Execute
        result = create_milestone(
            title="Phase 4: Essential Tools",
            description="Implement 8 essential MCP tools",
        )

        # Verify
        assert result["number"] == 8
        assert result["title"] == "Phase 4: Essential Tools"
        assert result["description"] == "Implement 8 essential MCP tools"
        assert result["state"] == "open"
        assert result["due_on"] is None
        assert result["url"] == "https://github.com/testowner/testrepo/milestone/8"

        # Verify GitHub API was called correctly
        mock_repo.create_milestone.assert_called_once()
        call_args = mock_repo.create_milestone.call_args[1]
        assert call_args["title"] == "Phase 4: Essential Tools"
        assert call_args["description"] == "Implement 8 essential MCP tools"
        assert call_args["state"] == "open"
        assert "due_on" not in call_args or call_args["due_on"] is None

    @patch("github_mcp_server.tools.milestones.get_github_client")
    def test_create_milestone_with_due_date(self, mock_get_client: Mock) -> None:
        """Test creating a milestone with due date."""
        mock_gh = Mock()
        mock_repo = Mock()
        mock_milestone = Mock()

        # Configure milestone with due date
        mock_milestone.number = 9
        mock_milestone.title = "Q1 2026 Release"
        mock_milestone.description = "All features for Q1"
        mock_milestone.state = "open"
        mock_milestone.due_on = datetime(2026, 3, 31, 23, 59, 59)
        mock_milestone.html_url = "https://github.com/testowner/testrepo/milestone/9"

        mock_repo.create_milestone.return_value = mock_milestone
        mock_gh.get_repo.return_value = mock_repo
        mock_get_client.return_value = mock_gh

        # Execute
        result = create_milestone(
            title="Q1 2026 Release",
            description="All features for Q1",
            due_date="2026-03-31T23:59:59Z",
        )

        # Verify
        assert result["number"] == 9
        assert result["title"] == "Q1 2026 Release"
        assert result["due_on"] == "2026-03-31T23:59:59"

        # Verify GitHub API was called with parsed date
        mock_repo.create_milestone.assert_called_once()

    @patch("github_mcp_server.tools.milestones.get_github_client")
    def test_create_milestone_duplicate_error(self, mock_get_client: Mock) -> None:
        """Test creating a duplicate milestone raises error."""
        from github import GithubException
        from github_mcp_server.utils.errors import GitHubAPIError

        mock_gh = Mock()
        mock_repo = Mock()

        # Simulate duplicate milestone error (422)
        mock_repo.create_milestone.side_effect = GithubException(
            422, {"message": "Validation Failed"}, None
        )
        mock_gh.get_repo.return_value = mock_repo
        mock_get_client.return_value = mock_gh

        # Execute and verify error
        with pytest.raises(GitHubAPIError):
            create_milestone(title="Existing Milestone", description="This already exists")

    @patch("github_mcp_server.tools.milestones.get_github_client")
    def test_create_milestone_invalid_due_date_format(self, mock_get_client: Mock) -> None:
        """Test creating milestone with invalid due date format raises error."""
        from github_mcp_server.utils.errors import GitHubAPIError

        mock_gh = Mock()
        mock_repo = Mock()
        mock_gh.get_repo.return_value = mock_repo
        mock_get_client.return_value = mock_gh

        # Execute and verify error (ValueError is wrapped in GitHubAPIError)
        with pytest.raises(GitHubAPIError) as exc_info:
            create_milestone(
                title="Test Milestone",
                description="Test",
                due_date="invalid-date-format",
            )

        # Verify the error message contains the expected text
        assert "Invalid ISO 8601" in str(exc_info.value)

    @patch("github_mcp_server.tools.milestones.get_github_client")
    def test_create_milestone_custom_owner_repo(self, mock_get_client: Mock) -> None:
        """Test creating milestone in custom owner/repo."""
        mock_gh = Mock()
        mock_repo = Mock()
        mock_milestone = Mock()

        mock_milestone.number = 1
        mock_milestone.title = "v1.0"
        mock_milestone.description = "First release"
        mock_milestone.state = "open"
        mock_milestone.due_on = None
        mock_milestone.html_url = "https://github.com/custom/repo/milestone/1"

        mock_repo.create_milestone.return_value = mock_milestone
        mock_gh.get_repo.return_value = mock_repo
        mock_get_client.return_value = mock_gh

        # Execute
        result = create_milestone(
            title="v1.0", description="First release", owner="custom", repo="repo"
        )

        # Verify API was called with correct repo
        mock_gh.get_repo.assert_called_once_with("custom/repo")
        assert result["number"] == 1

    @patch("github_mcp_server.tools.milestones.get_github_client")
    def test_create_milestone_closed_state(self, mock_get_client: Mock) -> None:
        """Test creating a closed milestone."""
        mock_gh = Mock()
        mock_repo = Mock()
        mock_milestone = Mock()

        mock_milestone.number = 10
        mock_milestone.title = "Archived Milestone"
        mock_milestone.description = "Old completed work"
        mock_milestone.state = "closed"
        mock_milestone.due_on = None
        mock_milestone.html_url = "https://github.com/testowner/testrepo/milestone/10"

        mock_repo.create_milestone.return_value = mock_milestone
        mock_gh.get_repo.return_value = mock_repo
        mock_get_client.return_value = mock_gh

        # Execute
        result = create_milestone(
            title="Archived Milestone",
            description="Old completed work",
            state="closed",
        )

        # Verify
        assert result["state"] == "closed"

        # Verify API call
        call_args = mock_repo.create_milestone.call_args[1]
        assert call_args["state"] == "closed"


class TestListMilestones:
    """Unit tests for list_milestones tool."""

    @patch("github_mcp_server.tools.milestones.get_github_client")
    def test_list_milestones_default_open(self, mock_get_client: Mock) -> None:
        """Test listing open milestones (default behavior)."""
        mock_gh = Mock()
        mock_repo = Mock()

        # Create mock milestones
        mock_milestone1 = Mock()
        mock_milestone1.number = 7
        mock_milestone1.title = "GitHub Manager MCP Migration"
        mock_milestone1.state = "open"
        mock_milestone1.open_issues = 5
        mock_milestone1.closed_issues = 103
        mock_milestone1.due_on = None
        mock_milestone1.html_url = "https://github.com/testowner/testrepo/milestone/7"

        mock_milestone2 = Mock()
        mock_milestone2.number = 8
        mock_milestone2.title = "Phase 4: Essential Tools"
        mock_milestone2.state = "open"
        mock_milestone2.open_issues = 12
        mock_milestone2.closed_issues = 0
        mock_milestone2.due_on = datetime(2026, 1, 31, 23, 59, 59)
        mock_milestone2.html_url = "https://github.com/testowner/testrepo/milestone/8"

        mock_repo.get_milestones.return_value = [mock_milestone1, mock_milestone2]
        mock_gh.get_repo.return_value = mock_repo
        mock_get_client.return_value = mock_gh

        # Execute
        result = list_milestones()

        # Verify
        assert result["total"] == 2
        assert len(result["milestones"]) == 2

        # Verify first milestone
        assert result["milestones"][0]["number"] == 7
        assert result["milestones"][0]["title"] == "GitHub Manager MCP Migration"
        assert result["milestones"][0]["state"] == "open"
        assert result["milestones"][0]["open_issues"] == 5
        assert result["milestones"][0]["closed_issues"] == 103
        assert result["milestones"][0]["due_on"] is None

        # Verify second milestone
        assert result["milestones"][1]["number"] == 8
        assert result["milestones"][1]["title"] == "Phase 4: Essential Tools"
        assert result["milestones"][1]["due_on"] == "2026-01-31T23:59:59"

        # Verify API call
        mock_repo.get_milestones.assert_called_once()
        call_kwargs = mock_repo.get_milestones.call_args[1]
        assert call_kwargs["state"] == "open"
        assert call_kwargs["sort"] == "due_on"
        assert call_kwargs["direction"] == "asc"

    @patch("github_mcp_server.tools.milestones.get_github_client")
    def test_list_milestones_closed(self, mock_get_client: Mock) -> None:
        """Test listing closed milestones."""
        mock_gh = Mock()
        mock_repo = Mock()

        mock_milestone = Mock()
        mock_milestone.number = 1
        mock_milestone.title = "Phase 1: Foundation"
        mock_milestone.state = "closed"
        mock_milestone.open_issues = 0
        mock_milestone.closed_issues = 50
        mock_milestone.due_on = None
        mock_milestone.html_url = "https://github.com/testowner/testrepo/milestone/1"

        mock_repo.get_milestones.return_value = [mock_milestone]
        mock_gh.get_repo.return_value = mock_repo
        mock_get_client.return_value = mock_gh

        # Execute
        result = list_milestones(state="closed")

        # Verify
        assert result["total"] == 1
        assert result["milestones"][0]["state"] == "closed"
        assert result["milestones"][0]["open_issues"] == 0

        # Verify API call
        call_kwargs = mock_repo.get_milestones.call_args[1]
        assert call_kwargs["state"] == "closed"

    @patch("github_mcp_server.tools.milestones.get_github_client")
    def test_list_milestones_all(self, mock_get_client: Mock) -> None:
        """Test listing all milestones (open + closed)."""
        mock_gh = Mock()
        mock_repo = Mock()

        mock_open = Mock()
        mock_open.number = 7
        mock_open.title = "Open Milestone"
        mock_open.state = "open"
        mock_open.open_issues = 5
        mock_open.closed_issues = 10
        mock_open.due_on = None
        mock_open.html_url = "https://github.com/testowner/testrepo/milestone/7"

        mock_closed = Mock()
        mock_closed.number = 1
        mock_closed.title = "Closed Milestone"
        mock_closed.state = "closed"
        mock_closed.open_issues = 0
        mock_closed.closed_issues = 50
        mock_closed.due_on = None
        mock_closed.html_url = "https://github.com/testowner/testrepo/milestone/1"

        mock_repo.get_milestones.return_value = [mock_open, mock_closed]
        mock_gh.get_repo.return_value = mock_repo
        mock_get_client.return_value = mock_gh

        # Execute
        result = list_milestones(state="all")

        # Verify
        assert result["total"] == 2
        assert result["milestones"][0]["state"] == "open"
        assert result["milestones"][1]["state"] == "closed"

        # Verify API call
        call_kwargs = mock_repo.get_milestones.call_args[1]
        assert call_kwargs["state"] == "all"

    @patch("github_mcp_server.tools.milestones.get_github_client")
    def test_list_milestones_sort_by_completeness(self, mock_get_client: Mock) -> None:
        """Test sorting milestones by completeness."""
        mock_gh = Mock()
        mock_repo = Mock()
        mock_milestone = Mock()

        mock_milestone.number = 7
        mock_milestone.title = "Test Milestone"
        mock_milestone.state = "open"
        mock_milestone.open_issues = 5
        mock_milestone.closed_issues = 95
        mock_milestone.due_on = None
        mock_milestone.html_url = "https://github.com/testowner/testrepo/milestone/7"

        mock_repo.get_milestones.return_value = [mock_milestone]
        mock_gh.get_repo.return_value = mock_repo
        mock_get_client.return_value = mock_gh

        # Execute
        result = list_milestones(sort="completeness", direction="desc")

        # Verify API call
        call_kwargs = mock_repo.get_milestones.call_args[1]
        assert call_kwargs["sort"] == "completeness"
        assert call_kwargs["direction"] == "desc"
        assert result is not None

    @patch("github_mcp_server.tools.milestones.get_github_client")
    def test_list_milestones_empty_repository(self, mock_get_client: Mock) -> None:
        """Test listing milestones from repository with no milestones."""
        mock_gh = Mock()
        mock_repo = Mock()
        mock_repo.get_milestones.return_value = []
        mock_gh.get_repo.return_value = mock_repo
        mock_get_client.return_value = mock_gh

        # Execute
        result = list_milestones()

        # Verify
        assert result["total"] == 0
        assert result["milestones"] == []

    @patch("github_mcp_server.tools.milestones.get_github_client")
    def test_list_milestones_custom_owner_repo(self, mock_get_client: Mock) -> None:
        """Test listing milestones from custom owner/repo."""
        mock_gh = Mock()
        mock_repo = Mock()

        mock_milestone = Mock()
        mock_milestone.number = 1
        mock_milestone.title = "v1.0"
        mock_milestone.state = "open"
        mock_milestone.open_issues = 3
        mock_milestone.closed_issues = 7
        mock_milestone.due_on = None
        mock_milestone.html_url = "https://github.com/custom/repo/milestone/1"

        mock_repo.get_milestones.return_value = [mock_milestone]
        mock_gh.get_repo.return_value = mock_repo
        mock_get_client.return_value = mock_gh

        # Execute
        result = list_milestones(owner="custom", repo="repo")

        # Verify API was called with correct repo
        mock_gh.get_repo.assert_called_once_with("custom/repo")
        assert result["total"] == 1

    @patch("github_mcp_server.tools.milestones.get_github_client")
    def test_list_milestones_api_error(self, mock_get_client: Mock) -> None:
        """Test that API errors are properly handled."""
        from github_mcp_server.utils.errors import GitHubAPIError

        mock_gh = Mock()
        mock_repo = Mock()
        mock_repo.get_milestones.side_effect = Exception("API Error")
        mock_gh.get_repo.return_value = mock_repo
        mock_get_client.return_value = mock_gh

        # Execute and verify error
        with pytest.raises(GitHubAPIError):
            list_milestones()
