"""Unit tests for pull request operations with mocked GitHub API.

These tests use mocks and don't require GITHUB_TOKEN or network access.
Run with: pytest tests/test_pulls_unit.py
"""

from datetime import datetime
from unittest.mock import Mock, patch

import pytest
from github_mcp_server.tools.pulls import get_pull_request, merge_pr, update_pr


class TestGetPullRequest:
    """Unit tests for get_pull_request tool."""

    @patch("github_mcp_server.tools.pulls.get_github_client")
    def test_get_open_pr(self, mock_get_client: Mock) -> None:
        """Test getting details of an open pull request."""
        # Setup mocks
        mock_gh = Mock()
        mock_repo = Mock()
        mock_pr = Mock()

        # Configure PR mock
        mock_pr.number = 42
        mock_pr.title = "feat: implement feature X"
        mock_pr.state = "open"
        mock_pr.merged = False
        mock_pr.mergeable = True
        mock_pr.mergeable_state = "clean"
        mock_pr.draft = False
        mock_pr.head.ref = "feature-branch"
        mock_pr.base.ref = "main"
        mock_pr.commits = 5
        mock_pr.additions = 234
        mock_pr.deletions = 67
        mock_pr.changed_files = 12
        mock_pr.created_at = datetime(2025, 12, 15, 10, 0, 0)
        mock_pr.updated_at = datetime(2025, 12, 20, 14, 30, 0)
        mock_pr.merged_at = None
        mock_pr.html_url = "https://github.com/testowner/testrepo/pull/42"

        mock_repo.get_pull.return_value = mock_pr
        mock_gh.get_repo.return_value = mock_repo
        mock_get_client.return_value = mock_gh

        # Execute
        result = get_pull_request(pr_number=42)

        # Verify
        assert result["number"] == 42
        assert result["title"] == "feat: implement feature X"
        assert result["state"] == "open"
        assert result["merged"] is False
        assert result["mergeable"] is True
        assert result["mergeable_state"] == "clean"
        assert result["draft"] is False
        assert result["head"] == "feature-branch"
        assert result["base"] == "main"
        assert result["commits"] == 5
        assert result["additions"] == 234
        assert result["deletions"] == 67
        assert result["changed_files"] == 12
        assert result["created_at"] == "2025-12-15T10:00:00"
        assert result["updated_at"] == "2025-12-20T14:30:00"
        assert result["merged_at"] is None
        assert result["url"] == "https://github.com/testowner/testrepo/pull/42"

        # Verify API calls
        mock_gh.get_repo.assert_called_once_with("testowner/testrepo")
        mock_repo.get_pull.assert_called_once_with(42)

    @patch("github_mcp_server.tools.pulls.get_github_client")
    def test_get_merged_pr(self, mock_get_client: Mock) -> None:
        """Test getting details of a merged pull request."""
        mock_gh = Mock()
        mock_repo = Mock()
        mock_pr = Mock()

        # Configure merged PR mock
        mock_pr.number = 100
        mock_pr.title = "fix: resolve bug in feature X"
        mock_pr.state = "closed"
        mock_pr.merged = True
        mock_pr.mergeable = None  # None for merged PRs
        mock_pr.mergeable_state = "clean"
        mock_pr.draft = False
        mock_pr.head.ref = "fix-bug"
        mock_pr.base.ref = "main"
        mock_pr.commits = 3
        mock_pr.additions = 50
        mock_pr.deletions = 30
        mock_pr.changed_files = 5
        mock_pr.created_at = datetime(2025, 12, 10, 9, 0, 0)
        mock_pr.updated_at = datetime(2025, 12, 12, 16, 0, 0)
        mock_pr.merged_at = datetime(2025, 12, 12, 16, 0, 0)
        mock_pr.html_url = "https://github.com/testowner/testrepo/pull/100"

        mock_repo.get_pull.return_value = mock_pr
        mock_gh.get_repo.return_value = mock_repo
        mock_get_client.return_value = mock_gh

        # Execute
        result = get_pull_request(pr_number=100)

        # Verify
        assert result["number"] == 100
        assert result["state"] == "closed"
        assert result["merged"] is True
        assert result["mergeable"] is None
        assert result["merged_at"] == "2025-12-12T16:00:00"

    @patch("github_mcp_server.tools.pulls.get_github_client")
    def test_get_closed_not_merged_pr(self, mock_get_client: Mock) -> None:
        """Test getting details of a closed but not merged PR."""
        mock_gh = Mock()
        mock_repo = Mock()
        mock_pr = Mock()

        # Configure closed (not merged) PR mock
        mock_pr.number = 50
        mock_pr.title = "WIP: experimental feature"
        mock_pr.state = "closed"
        mock_pr.merged = False
        mock_pr.mergeable = None
        mock_pr.mergeable_state = "dirty"
        mock_pr.draft = True
        mock_pr.head.ref = "experimental"
        mock_pr.base.ref = "main"
        mock_pr.commits = 2
        mock_pr.additions = 100
        mock_pr.deletions = 20
        mock_pr.changed_files = 3
        mock_pr.created_at = datetime(2025, 12, 5, 10, 0, 0)
        mock_pr.updated_at = datetime(2025, 12, 8, 15, 0, 0)
        mock_pr.merged_at = None
        mock_pr.html_url = "https://github.com/testowner/testrepo/pull/50"

        mock_repo.get_pull.return_value = mock_pr
        mock_gh.get_repo.return_value = mock_repo
        mock_get_client.return_value = mock_gh

        # Execute
        result = get_pull_request(pr_number=50)

        # Verify
        assert result["state"] == "closed"
        assert result["merged"] is False
        assert result["merged_at"] is None
        assert result["draft"] is True

    @patch("github_mcp_server.tools.pulls.get_github_client")
    def test_get_draft_pr(self, mock_get_client: Mock) -> None:
        """Test getting details of a draft pull request."""
        mock_gh = Mock()
        mock_repo = Mock()
        mock_pr = Mock()

        mock_pr.number = 75
        mock_pr.title = "WIP: Add new feature Y"
        mock_pr.state = "open"
        mock_pr.merged = False
        mock_pr.mergeable = True
        mock_pr.mergeable_state = "clean"
        mock_pr.draft = True
        mock_pr.head.ref = "feature-y"
        mock_pr.base.ref = "develop"
        mock_pr.commits = 10
        mock_pr.additions = 500
        mock_pr.deletions = 100
        mock_pr.changed_files = 20
        mock_pr.created_at = datetime(2025, 12, 18, 11, 30, 0)
        mock_pr.updated_at = datetime(2025, 12, 21, 9, 0, 0)
        mock_pr.merged_at = None
        mock_pr.html_url = "https://github.com/testowner/testrepo/pull/75"

        mock_repo.get_pull.return_value = mock_pr
        mock_gh.get_repo.return_value = mock_repo
        mock_get_client.return_value = mock_gh

        # Execute
        result = get_pull_request(pr_number=75)

        # Verify
        assert result["draft"] is True
        assert result["state"] == "open"
        assert result["base"] == "develop"
        assert result["commits"] == 10
        assert result["changed_files"] == 20

    @patch("github_mcp_server.tools.pulls.get_github_client")
    def test_get_pr_mergeable_unknown(self, mock_get_client: Mock) -> None:
        """Test getting PR when mergeable status is still being calculated (None)."""
        mock_gh = Mock()
        mock_repo = Mock()
        mock_pr = Mock()

        mock_pr.number = 88
        mock_pr.title = "feat: new feature"
        mock_pr.state = "open"
        mock_pr.merged = False
        mock_pr.mergeable = None  # GitHub still calculating
        mock_pr.mergeable_state = "unknown"
        mock_pr.draft = False
        mock_pr.head.ref = "feature-z"
        mock_pr.base.ref = "main"
        mock_pr.commits = 1
        mock_pr.additions = 10
        mock_pr.deletions = 5
        mock_pr.changed_files = 2
        mock_pr.created_at = datetime(2025, 12, 21, 14, 0, 0)
        mock_pr.updated_at = datetime(2025, 12, 21, 14, 5, 0)
        mock_pr.merged_at = None
        mock_pr.html_url = "https://github.com/testowner/testrepo/pull/88"

        mock_repo.get_pull.return_value = mock_pr
        mock_gh.get_repo.return_value = mock_repo
        mock_get_client.return_value = mock_gh

        # Execute
        result = get_pull_request(pr_number=88)

        # Verify
        assert result["mergeable"] is None
        assert result["mergeable_state"] == "unknown"

    @patch("github_mcp_server.tools.pulls.get_github_client")
    def test_get_pr_not_mergeable(self, mock_get_client: Mock) -> None:
        """Test getting PR that has merge conflicts."""
        mock_gh = Mock()
        mock_repo = Mock()
        mock_pr = Mock()

        mock_pr.number = 99
        mock_pr.title = "fix: conflicting changes"
        mock_pr.state = "open"
        mock_pr.merged = False
        mock_pr.mergeable = False
        mock_pr.mergeable_state = "dirty"
        mock_pr.draft = False
        mock_pr.head.ref = "conflicting-branch"
        mock_pr.base.ref = "main"
        mock_pr.commits = 4
        mock_pr.additions = 80
        mock_pr.deletions = 40
        mock_pr.changed_files = 8
        mock_pr.created_at = datetime(2025, 12, 1, 10, 0, 0)
        mock_pr.updated_at = datetime(2025, 12, 20, 11, 0, 0)
        mock_pr.merged_at = None
        mock_pr.html_url = "https://github.com/testowner/testrepo/pull/99"

        mock_repo.get_pull.return_value = mock_pr
        mock_gh.get_repo.return_value = mock_repo
        mock_get_client.return_value = mock_gh

        # Execute
        result = get_pull_request(pr_number=99)

        # Verify
        assert result["mergeable"] is False
        assert result["mergeable_state"] == "dirty"

    @patch("github_mcp_server.tools.pulls.get_github_client")
    def test_get_pr_nonexistent_raises_error(self, mock_get_client: Mock) -> None:
        """Test getting non-existent PR raises error."""
        from github_mcp_server.utils.errors import GitHubAPIError

        mock_gh = Mock()
        mock_repo = Mock()
        mock_repo.get_pull.side_effect = Exception("Pull request not found")
        mock_gh.get_repo.return_value = mock_repo
        mock_get_client.return_value = mock_gh

        # Execute and verify error
        with pytest.raises(GitHubAPIError):
            get_pull_request(pr_number=99999)

    @patch("github_mcp_server.tools.pulls.get_github_client")
    def test_get_pr_custom_owner_repo(self, mock_get_client: Mock) -> None:
        """Test getting PR from custom owner/repo."""
        mock_gh = Mock()
        mock_repo = Mock()
        mock_pr = Mock()

        mock_pr.number = 1
        mock_pr.title = "Test PR"
        mock_pr.state = "open"
        mock_pr.merged = False
        mock_pr.mergeable = True
        mock_pr.mergeable_state = "clean"
        mock_pr.draft = False
        mock_pr.head.ref = "test"
        mock_pr.base.ref = "main"
        mock_pr.commits = 1
        mock_pr.additions = 10
        mock_pr.deletions = 5
        mock_pr.changed_files = 2
        mock_pr.created_at = datetime(2025, 12, 1, 10, 0, 0)
        mock_pr.updated_at = datetime(2025, 12, 1, 10, 30, 0)
        mock_pr.merged_at = None
        mock_pr.html_url = "https://github.com/custom/repo/pull/1"

        mock_repo.get_pull.return_value = mock_pr
        mock_gh.get_repo.return_value = mock_repo
        mock_get_client.return_value = mock_gh

        # Execute
        result = get_pull_request(pr_number=1, owner="custom", repo="repo")

        # Verify API was called with correct repo
        mock_gh.get_repo.assert_called_once_with("custom/repo")
        assert result["url"] == "https://github.com/custom/repo/pull/1"

    @patch("github_mcp_server.tools.pulls.get_github_client")
    def test_get_pr_with_all_mergeable_states(self, mock_get_client: Mock) -> None:
        """Test various mergeable_state values."""
        mock_gh = Mock()
        mock_repo = Mock()
        mock_get_client.return_value = mock_gh
        mock_gh.get_repo.return_value = mock_repo

        # Test different mergeable states
        test_states = [
            "clean",  # No conflicts, ready to merge
            "dirty",  # Merge conflicts
            "unstable",  # Checks failing
            "blocked",  # Blocked by required reviews
            "unknown",  # GitHub calculating
        ]

        for state in test_states:
            mock_pr = Mock()
            mock_pr.number = 123
            mock_pr.title = f"PR with {state} state"
            mock_pr.state = "open"
            mock_pr.merged = False
            mock_pr.mergeable = state == "clean"
            mock_pr.mergeable_state = state
            mock_pr.draft = False
            mock_pr.head.ref = "test"
            mock_pr.base.ref = "main"
            mock_pr.commits = 1
            mock_pr.additions = 10
            mock_pr.deletions = 5
            mock_pr.changed_files = 2
            mock_pr.created_at = datetime(2025, 12, 1, 10, 0, 0)
            mock_pr.updated_at = datetime(2025, 12, 1, 10, 30, 0)
            mock_pr.merged_at = None
            mock_pr.html_url = "https://github.com/test/repo/pull/123"

            mock_repo.get_pull.return_value = mock_pr

            result = get_pull_request(pr_number=123)
            assert result["mergeable_state"] == state


class TestUpdatePR:
    """Unit tests for update_pr tool."""

    @patch("github_mcp_server.tools.pulls.get_github_client")
    def test_update_title_only(self, mock_get_client: Mock) -> None:
        """Test updating only the PR title."""
        # Setup mocks
        mock_gh = Mock()
        mock_repo = Mock()
        mock_pr = Mock()

        # Configure PR mock
        mock_pr.number = 42
        mock_pr.title = "Updated title"
        mock_pr.state = "open"
        mock_pr.merged = False
        mock_pr.html_url = "https://github.com/testowner/testrepo/pull/42"
        mock_pr.edit = Mock()

        mock_repo.get_pull.return_value = mock_pr
        mock_gh.get_repo.return_value = mock_repo
        mock_get_client.return_value = mock_gh

        # Execute
        result = update_pr(pr_number=42, title="Updated title")

        # Verify
        assert result["number"] == 42
        assert result["title"] == "Updated title"
        assert result["state"] == "open"
        assert result["updated_fields"] == ["title"]
        assert "github.com" in result["url"]

        # Verify edit was called with correct parameters
        mock_pr.edit.assert_called_once_with(title="Updated title")
        mock_repo.get_pull.assert_called_once_with(42)

    @patch("github_mcp_server.tools.pulls.get_github_client")
    def test_update_body_only(self, mock_get_client: Mock) -> None:
        """Test updating only the PR body."""
        mock_gh = Mock()
        mock_repo = Mock()
        mock_pr = Mock()

        mock_pr.number = 42
        mock_pr.title = "Original title"
        mock_pr.state = "open"
        mock_pr.merged = False
        mock_pr.html_url = "https://github.com/testowner/testrepo/pull/42"
        mock_pr.edit = Mock()

        mock_repo.get_pull.return_value = mock_pr
        mock_gh.get_repo.return_value = mock_repo
        mock_get_client.return_value = mock_gh

        # Execute
        new_body = "Updated description with more details"
        result = update_pr(pr_number=42, body=new_body)

        # Verify
        assert result["updated_fields"] == ["body"]
        mock_pr.edit.assert_called_once_with(body=new_body)

    @patch("github_mcp_server.tools.pulls.get_github_client")
    def test_update_base_branch(self, mock_get_client: Mock) -> None:
        """Test changing the base branch."""
        mock_gh = Mock()
        mock_repo = Mock()
        mock_pr = Mock()

        mock_pr.number = 42
        mock_pr.title = "Test PR"
        mock_pr.state = "open"
        mock_pr.merged = False
        mock_pr.html_url = "https://github.com/testowner/testrepo/pull/42"
        mock_pr.edit = Mock()

        mock_repo.get_pull.return_value = mock_pr
        mock_gh.get_repo.return_value = mock_repo
        mock_get_client.return_value = mock_gh

        # Execute
        result = update_pr(pr_number=42, base="develop")

        # Verify
        assert result["updated_fields"] == ["base"]
        mock_pr.edit.assert_called_once_with(base="develop")

    @patch("github_mcp_server.tools.pulls.get_github_client")
    def test_close_pr_via_state(self, mock_get_client: Mock) -> None:
        """Test closing a PR by setting state to 'closed'."""
        mock_gh = Mock()
        mock_repo = Mock()
        mock_pr = Mock()

        mock_pr.number = 42
        mock_pr.title = "Test PR"
        mock_pr.state = "closed"
        mock_pr.merged = False
        mock_pr.html_url = "https://github.com/testowner/testrepo/pull/42"
        mock_pr.edit = Mock()

        mock_repo.get_pull.return_value = mock_pr
        mock_gh.get_repo.return_value = mock_repo
        mock_get_client.return_value = mock_gh

        # Execute
        result = update_pr(pr_number=42, state="closed")

        # Verify
        assert result["state"] == "closed"
        assert result["updated_fields"] == ["state"]
        mock_pr.edit.assert_called_once_with(state="closed")

    @patch("github_mcp_server.tools.pulls.get_github_client")
    def test_reopen_pr_via_state(self, mock_get_client: Mock) -> None:
        """Test reopening a closed PR by setting state to 'open'."""
        mock_gh = Mock()
        mock_repo = Mock()
        mock_pr = Mock()

        mock_pr.number = 42
        mock_pr.title = "Test PR"
        mock_pr.state = "open"
        mock_pr.merged = False
        mock_pr.html_url = "https://github.com/testowner/testrepo/pull/42"
        mock_pr.edit = Mock()

        mock_repo.get_pull.return_value = mock_pr
        mock_gh.get_repo.return_value = mock_repo
        mock_get_client.return_value = mock_gh

        # Execute
        result = update_pr(pr_number=42, state="open")

        # Verify
        assert result["state"] == "open"
        assert result["updated_fields"] == ["state"]
        mock_pr.edit.assert_called_once_with(state="open")

    @patch("github_mcp_server.tools.pulls.get_github_client")
    def test_update_multiple_fields(self, mock_get_client: Mock) -> None:
        """Test updating multiple fields at once."""
        mock_gh = Mock()
        mock_repo = Mock()
        mock_pr = Mock()

        mock_pr.number = 42
        mock_pr.title = "New title"
        mock_pr.state = "closed"
        mock_pr.merged = False
        mock_pr.html_url = "https://github.com/testowner/testrepo/pull/42"
        mock_pr.edit = Mock()

        mock_repo.get_pull.return_value = mock_pr
        mock_gh.get_repo.return_value = mock_repo
        mock_get_client.return_value = mock_gh

        # Execute
        result = update_pr(
            pr_number=42,
            title="New title",
            body="New description",
            base="develop",
            state="closed",
        )

        # Verify all fields in updated_fields
        assert set(result["updated_fields"]) == {"title", "body", "base", "state"}
        assert result["title"] == "New title"
        assert result["state"] == "closed"

        # Verify edit was called with all parameters
        mock_pr.edit.assert_called_once_with(
            title="New title",
            body="New description",
            base="develop",
            state="closed",
        )

    @patch("github_mcp_server.tools.pulls.get_github_client")
    def test_update_merged_pr_raises_error(self, mock_get_client: Mock) -> None:
        """Test that updating a merged PR raises an error."""
        mock_gh = Mock()
        mock_repo = Mock()
        mock_pr = Mock()

        # Configure as merged PR
        mock_pr.number = 42
        mock_pr.merged = True

        mock_repo.get_pull.return_value = mock_pr
        mock_gh.get_repo.return_value = mock_repo
        mock_get_client.return_value = mock_gh

        # Execute and verify error
        with pytest.raises(Exception) as exc_info:
            update_pr(pr_number=42, title="New title")

        assert "merged" in str(exc_info.value).lower()
        assert "42" in str(exc_info.value)

    @patch("github_mcp_server.tools.pulls.get_github_client")
    def test_invalid_state_raises_error(self, mock_get_client: Mock) -> None:
        """Test that invalid state value raises ValueError."""
        mock_gh = Mock()
        mock_repo = Mock()
        mock_pr = Mock()

        mock_pr.merged = False
        mock_repo.get_pull.return_value = mock_pr
        mock_gh.get_repo.return_value = mock_repo
        mock_get_client.return_value = mock_gh

        # Execute and verify error
        with pytest.raises(ValueError) as exc_info:
            update_pr(pr_number=42, state="invalid")

        assert "invalid" in str(exc_info.value).lower()
        assert "open" in str(exc_info.value) or "closed" in str(exc_info.value)

    @patch("github_mcp_server.tools.pulls.get_github_client")
    def test_nonexistent_pr_raises_error(self, mock_get_client: Mock) -> None:
        """Test that updating non-existent PR raises error."""
        from github_mcp_server.utils.errors import GitHubAPIError

        mock_gh = Mock()
        mock_repo = Mock()
        mock_repo.get_pull.side_effect = Exception("Pull request not found")
        mock_gh.get_repo.return_value = mock_repo
        mock_get_client.return_value = mock_gh

        # Execute and verify error
        with pytest.raises(GitHubAPIError):
            update_pr(pr_number=99999, title="New title")

    @patch("github_mcp_server.tools.pulls.get_github_client")
    def test_no_updates_provided(self, mock_get_client: Mock) -> None:
        """Test calling update_pr with no fields to update."""
        mock_gh = Mock()
        mock_repo = Mock()
        mock_pr = Mock()

        mock_pr.number = 42
        mock_pr.title = "Original title"
        mock_pr.state = "open"
        mock_pr.merged = False
        mock_pr.html_url = "https://github.com/testowner/testrepo/pull/42"
        mock_pr.edit = Mock()

        mock_repo.get_pull.return_value = mock_pr
        mock_gh.get_repo.return_value = mock_repo
        mock_get_client.return_value = mock_gh

        # Execute
        result = update_pr(pr_number=42)

        # Verify
        assert result["updated_fields"] == []
        # edit should not be called when no updates provided
        mock_pr.edit.assert_not_called()

    @patch("github_mcp_server.tools.pulls.get_github_client")
    def test_update_with_custom_owner_repo(self, mock_get_client: Mock) -> None:
        """Test updating PR in custom owner/repo."""
        mock_gh = Mock()
        mock_repo = Mock()
        mock_pr = Mock()

        mock_pr.number = 1
        mock_pr.title = "Updated"
        mock_pr.state = "open"
        mock_pr.merged = False
        mock_pr.html_url = "https://github.com/custom/repo/pull/1"
        mock_pr.edit = Mock()

        mock_repo.get_pull.return_value = mock_pr
        mock_gh.get_repo.return_value = mock_repo
        mock_get_client.return_value = mock_gh

        # Execute
        result = update_pr(
            pr_number=1,
            title="Updated",
            owner="custom",
            repo="repo",
        )

        # Verify API was called with correct repo
        mock_gh.get_repo.assert_called_once_with("custom/repo")
        assert "custom/repo" in result["url"]

    @patch("github_mcp_server.tools.pulls.get_github_client")
    def test_update_partial_fields_preserves_others(self, mock_get_client: Mock) -> None:
        """Test that updating some fields doesn't affect others."""
        mock_gh = Mock()
        mock_repo = Mock()
        mock_pr = Mock()

        mock_pr.number = 42
        mock_pr.title = "New title"
        mock_pr.state = "open"
        mock_pr.merged = False
        mock_pr.html_url = "https://github.com/testowner/testrepo/pull/42"
        mock_pr.edit = Mock()

        mock_repo.get_pull.return_value = mock_pr
        mock_gh.get_repo.return_value = mock_repo
        mock_get_client.return_value = mock_gh

        # Execute - only update title, not body or state
        update_pr(pr_number=42, title="New title")

        # Verify only title was passed to edit
        mock_pr.edit.assert_called_once_with(title="New title")
        # Body and state should not be in the update call
        call_kwargs = mock_pr.edit.call_args[1]
        assert "title" in call_kwargs
        assert "body" not in call_kwargs
        assert "state" not in call_kwargs
        assert "base" not in call_kwargs


class TestMergePR:
    """Unit tests for merge_pr tool."""

    @patch("github_mcp_server.tools.pulls.get_github_client")
    def test_merge_pr_with_squash_default(self, mock_get_client: Mock) -> None:
        """Test merging PR with default squash method."""
        # Setup mocks
        mock_gh = Mock()
        mock_repo = Mock()
        mock_pr = Mock()

        # Configure PR mock as mergeable
        mock_pr.number = 42
        mock_pr.state = "open"
        mock_pr.merged = False
        mock_pr.mergeable = True
        mock_pr.mergeable_state = "clean"
        mock_pr.head.ref = "feature-branch"
        mock_pr.base.ref = "main"

        # Configure merge response
        merge_response = Mock()
        merge_response.merged = True
        merge_response.sha = "abc123def456"
        merge_response.message = "Squashed and merged"
        mock_pr.merge.return_value = merge_response

        mock_repo.get_pull.return_value = mock_pr
        mock_gh.get_repo.return_value = mock_repo
        mock_get_client.return_value = mock_gh

        # Execute
        result = merge_pr(pr_number=42)

        # Verify
        assert result["merged"] is True
        assert result["sha"] == "abc123def456"
        assert result["message"] == "Pull request #42 successfully merged"
        assert result["branch_deleted"] is True

        # Verify merge was called with correct parameters
        mock_pr.merge.assert_called_once_with(
            merge_method="squash", commit_title=None, commit_message=None
        )
        mock_repo.get_pull.assert_called_once_with(42)

    @patch("github_mcp_server.tools.pulls.get_github_client")
    def test_merge_pr_with_merge_method(self, mock_get_client: Mock) -> None:
        """Test merging PR using 'merge' method (create merge commit)."""
        mock_gh = Mock()
        mock_repo = Mock()
        mock_pr = Mock()

        mock_pr.number = 100
        mock_pr.state = "open"
        mock_pr.merged = False
        mock_pr.mergeable = True
        mock_pr.mergeable_state = "clean"
        mock_pr.head.ref = "feature-x"
        mock_pr.base.ref = "main"

        merge_response = Mock()
        merge_response.merged = True
        merge_response.sha = "xyz789abc123"
        merge_response.message = "Pull request merged"
        mock_pr.merge.return_value = merge_response

        mock_repo.get_pull.return_value = mock_pr
        mock_gh.get_repo.return_value = mock_repo
        mock_get_client.return_value = mock_gh

        # Execute
        result = merge_pr(pr_number=100, merge_method="merge")

        # Verify
        assert result["merged"] is True
        assert result["sha"] == "xyz789abc123"
        mock_pr.merge.assert_called_once_with(
            merge_method="merge", commit_title=None, commit_message=None
        )

    @patch("github_mcp_server.tools.pulls.get_github_client")
    def test_merge_pr_with_rebase_method(self, mock_get_client: Mock) -> None:
        """Test merging PR using 'rebase' method."""
        mock_gh = Mock()
        mock_repo = Mock()
        mock_pr = Mock()

        mock_pr.number = 75
        mock_pr.state = "open"
        mock_pr.merged = False
        mock_pr.mergeable = True
        mock_pr.mergeable_state = "clean"
        mock_pr.head.ref = "fix-bug"
        mock_pr.base.ref = "main"

        merge_response = Mock()
        merge_response.merged = True
        merge_response.sha = "def456ghi789"
        merge_response.message = "Rebased and merged"
        mock_pr.merge.return_value = merge_response

        mock_repo.get_pull.return_value = mock_pr
        mock_gh.get_repo.return_value = mock_repo
        mock_get_client.return_value = mock_gh

        # Execute
        result = merge_pr(pr_number=75, merge_method="rebase")

        # Verify
        assert result["merged"] is True
        assert result["sha"] == "def456ghi789"
        mock_pr.merge.assert_called_once_with(
            merge_method="rebase", commit_title=None, commit_message=None
        )

    @patch("github_mcp_server.tools.pulls.get_github_client")
    def test_merge_pr_with_custom_commit_title_and_message(self, mock_get_client: Mock) -> None:
        """Test merging PR with custom commit title and message."""
        mock_gh = Mock()
        mock_repo = Mock()
        mock_pr = Mock()

        mock_pr.number = 50
        mock_pr.state = "open"
        mock_pr.merged = False
        mock_pr.mergeable = True
        mock_pr.mergeable_state = "clean"
        mock_pr.head.ref = "feature-y"
        mock_pr.base.ref = "main"

        merge_response = Mock()
        merge_response.merged = True
        merge_response.sha = "ghi789jkl012"
        merge_response.message = "Custom merge commit"
        mock_pr.merge.return_value = merge_response

        mock_repo.get_pull.return_value = mock_pr
        mock_gh.get_repo.return_value = mock_repo
        mock_get_client.return_value = mock_gh

        # Execute
        result = merge_pr(
            pr_number=50,
            merge_method="squash",
            commit_title="feat: Add custom feature",
            commit_message="Detailed description of changes",
        )

        # Verify
        assert result["merged"] is True
        mock_pr.merge.assert_called_once_with(
            merge_method="squash",
            commit_title="feat: Add custom feature",
            commit_message="Detailed description of changes",
        )

    @patch("github_mcp_server.tools.pulls.get_github_client")
    def test_merge_pr_keep_branch(self, mock_get_client: Mock) -> None:
        """Test merging PR without deleting the head branch."""
        mock_gh = Mock()
        mock_repo = Mock()
        mock_pr = Mock()

        mock_pr.number = 35
        mock_pr.state = "open"
        mock_pr.merged = False
        mock_pr.mergeable = True
        mock_pr.mergeable_state = "clean"
        mock_pr.head.ref = "feature-keep"
        mock_pr.base.ref = "main"

        merge_response = Mock()
        merge_response.merged = True
        merge_response.sha = "jkl012mno345"
        merge_response.message = "Merged (branch kept)"
        mock_pr.merge.return_value = merge_response

        mock_repo.get_pull.return_value = mock_pr
        mock_gh.get_repo.return_value = mock_repo
        mock_get_client.return_value = mock_gh

        # Execute
        result = merge_pr(pr_number=35, delete_branch=False)

        # Verify
        assert result["merged"] is True
        assert result["branch_deleted"] is False
        mock_pr.merge.assert_called_once_with(
            merge_method="squash", commit_title=None, commit_message=None
        )

    @patch("github_mcp_server.tools.pulls.get_github_client")
    def test_merge_pr_not_mergeable_blocked(self, mock_get_client: Mock) -> None:
        """Test merging PR that is blocked raises error."""
        mock_gh = Mock()
        mock_repo = Mock()
        mock_pr = Mock()

        mock_pr.number = 42
        mock_pr.state = "open"
        mock_pr.merged = False
        mock_pr.mergeable = False
        mock_pr.mergeable_state = "blocked"
        mock_pr.head.ref = "feature-blocked"
        mock_pr.base.ref = "main"

        mock_repo.get_pull.return_value = mock_pr
        mock_gh.get_repo.return_value = mock_repo
        mock_get_client.return_value = mock_gh

        # Execute and verify error
        with pytest.raises(Exception) as exc_info:
            merge_pr(pr_number=42)

        error_msg = str(exc_info.value).lower()
        assert "blocked" in error_msg or "not mergeable" in error_msg

    @patch("github_mcp_server.tools.pulls.get_github_client")
    def test_merge_pr_not_mergeable_dirty_conflicts(self, mock_get_client: Mock) -> None:
        """Test merging PR with conflicts raises error."""
        mock_gh = Mock()
        mock_repo = Mock()
        mock_pr = Mock()

        mock_pr.number = 99
        mock_pr.state = "open"
        mock_pr.merged = False
        mock_pr.mergeable = False
        mock_pr.mergeable_state = "dirty"
        mock_pr.head.ref = "feature-conflicting"
        mock_pr.base.ref = "main"

        mock_repo.get_pull.return_value = mock_pr
        mock_gh.get_repo.return_value = mock_repo
        mock_get_client.return_value = mock_gh

        # Execute and verify error
        with pytest.raises(Exception) as exc_info:
            merge_pr(pr_number=99)

        error_msg = str(exc_info.value).lower()
        assert "conflict" in error_msg or "dirty" in error_msg or "not mergeable" in error_msg

    @patch("github_mcp_server.tools.pulls.get_github_client")
    def test_merge_pr_not_mergeable_behind(self, mock_get_client: Mock) -> None:
        """Test merging PR that is behind the base branch raises error."""
        mock_gh = Mock()
        mock_repo = Mock()
        mock_pr = Mock()

        mock_pr.number = 88
        mock_pr.state = "open"
        mock_pr.merged = False
        mock_pr.mergeable = False
        mock_pr.mergeable_state = "behind"
        mock_pr.head.ref = "feature-behind"
        mock_pr.base.ref = "main"

        mock_repo.get_pull.return_value = mock_pr
        mock_gh.get_repo.return_value = mock_repo
        mock_get_client.return_value = mock_gh

        # Execute and verify error
        with pytest.raises(Exception) as exc_info:
            merge_pr(pr_number=88)

        error_msg = str(exc_info.value).lower()
        assert "branch must be updated" in error_msg or "base branch" in error_msg

    @patch("github_mcp_server.tools.pulls.get_github_client")
    def test_merge_pr_already_merged_raises_error(self, mock_get_client: Mock) -> None:
        """Test that merging an already merged PR raises error."""
        mock_gh = Mock()
        mock_repo = Mock()
        mock_pr = Mock()

        mock_pr.number = 100
        mock_pr.state = "closed"
        mock_pr.merged = True
        mock_pr.mergeable = None
        mock_pr.mergeable_state = "clean"
        mock_pr.head.ref = "already-merged"
        mock_pr.base.ref = "main"

        mock_repo.get_pull.return_value = mock_pr
        mock_gh.get_repo.return_value = mock_repo
        mock_get_client.return_value = mock_gh

        # Execute and verify error
        with pytest.raises(Exception) as exc_info:
            merge_pr(pr_number=100)

        error_msg = str(exc_info.value).lower()
        assert "merged" in error_msg or "already" in error_msg

    @patch("github_mcp_server.tools.pulls.get_github_client")
    def test_merge_pr_closed_raises_error(self, mock_get_client: Mock) -> None:
        """Test that merging a closed PR raises error."""
        mock_gh = Mock()
        mock_repo = Mock()
        mock_pr = Mock()

        mock_pr.number = 77
        mock_pr.state = "closed"
        mock_pr.merged = False
        mock_pr.mergeable = None
        mock_pr.mergeable_state = "dirty"
        mock_pr.head.ref = "closed-pr"
        mock_pr.base.ref = "main"

        mock_repo.get_pull.return_value = mock_pr
        mock_gh.get_repo.return_value = mock_repo
        mock_get_client.return_value = mock_gh

        # Execute and verify error
        with pytest.raises(Exception) as exc_info:
            merge_pr(pr_number=77)

        error_msg = str(exc_info.value).lower()
        assert "closed" in error_msg or "state" in error_msg

    @patch("github_mcp_server.tools.pulls.get_github_client")
    def test_merge_pr_invalid_merge_method_raises_error(self, mock_get_client: Mock) -> None:
        """Test that invalid merge_method value raises ValueError."""
        mock_gh = Mock()
        mock_repo = Mock()
        mock_pr = Mock()

        mock_pr.number = 42
        mock_pr.state = "open"
        mock_pr.merged = False
        mock_pr.mergeable = True
        mock_pr.mergeable_state = "clean"

        mock_repo.get_pull.return_value = mock_pr
        mock_gh.get_repo.return_value = mock_repo
        mock_get_client.return_value = mock_gh

        # Execute and verify error
        with pytest.raises(ValueError) as exc_info:
            merge_pr(pr_number=42, merge_method="invalid_method")

        error_msg = str(exc_info.value).lower()
        assert "merge_method" in error_msg or "invalid" in error_msg
        assert "merge" in error_msg or "squash" in error_msg or "rebase" in error_msg

    @patch("github_mcp_server.tools.pulls.get_github_client")
    def test_merge_pr_nonexistent_raises_error(self, mock_get_client: Mock) -> None:
        """Test that merging non-existent PR raises error."""
        from github_mcp_server.utils.errors import GitHubAPIError

        mock_gh = Mock()
        mock_repo = Mock()
        mock_repo.get_pull.side_effect = Exception("Pull request not found")
        mock_gh.get_repo.return_value = mock_repo
        mock_get_client.return_value = mock_gh

        # Execute and verify error
        with pytest.raises(GitHubAPIError):
            merge_pr(pr_number=99999)

    @patch("github_mcp_server.tools.pulls.get_github_client")
    def test_merge_pr_custom_owner_repo(self, mock_get_client: Mock) -> None:
        """Test merging PR in custom owner/repo."""
        mock_gh = Mock()
        mock_repo = Mock()
        mock_pr = Mock()

        mock_pr.number = 5
        mock_pr.state = "open"
        mock_pr.merged = False
        mock_pr.mergeable = True
        mock_pr.mergeable_state = "clean"
        mock_pr.head.ref = "custom-feature"
        mock_pr.base.ref = "main"

        merge_response = Mock()
        merge_response.merged = True
        merge_response.sha = "mno345pqr678"
        merge_response.message = "Merged in custom repo"
        mock_pr.merge.return_value = merge_response

        mock_repo.get_pull.return_value = mock_pr
        mock_gh.get_repo.return_value = mock_repo
        mock_get_client.return_value = mock_gh

        # Execute
        result = merge_pr(pr_number=5, owner="custom", repo="repo")

        # Verify API was called with correct repo
        mock_gh.get_repo.assert_called_once_with("custom/repo")
        assert result["merged"] is True
        mock_repo.get_pull.assert_called_once_with(5)

    @patch("github_mcp_server.tools.pulls.get_github_client")
    def test_merge_pr_returns_correct_structure(self, mock_get_client: Mock) -> None:
        """Test that merge_pr returns all required fields in correct structure."""
        mock_gh = Mock()
        mock_repo = Mock()
        mock_pr = Mock()

        mock_pr.number = 42
        mock_pr.state = "open"
        mock_pr.merged = False
        mock_pr.mergeable = True
        mock_pr.mergeable_state = "clean"
        mock_pr.head.ref = "feature-test"
        mock_pr.base.ref = "main"

        merge_response = Mock()
        merge_response.merged = True
        merge_response.sha = "pqr678stu901"
        merge_response.message = "Test message"
        mock_pr.merge.return_value = merge_response

        mock_repo.get_pull.return_value = mock_pr
        mock_gh.get_repo.return_value = mock_repo
        mock_get_client.return_value = mock_gh

        # Execute
        result = merge_pr(pr_number=42)

        # Verify structure - all required keys present
        assert isinstance(result, dict)
        assert "merged" in result
        assert "sha" in result
        assert "message" in result
        assert "branch_deleted" in result

        # Verify types
        assert isinstance(result["merged"], bool)
        assert isinstance(result["sha"], str)
        assert isinstance(result["message"], str)
        assert isinstance(result["branch_deleted"], bool)

        # Verify values
        assert result["merged"] is True
        assert len(result["sha"]) > 0
        assert len(result["message"]) > 0
        assert result["branch_deleted"] is True

    @patch("github_mcp_server.tools.pulls.get_github_client")
    def test_merge_pr_all_merge_methods(self, mock_get_client: Mock) -> None:
        """Test all valid merge methods are accepted."""
        mock_gh = Mock()
        mock_repo = Mock()
        mock_get_client.return_value = mock_gh
        mock_gh.get_repo.return_value = mock_repo

        merge_methods = ["squash", "merge", "rebase"]

        for method in merge_methods:
            mock_pr = Mock()
            mock_pr.number = 50
            mock_pr.state = "open"
            mock_pr.merged = False
            mock_pr.mergeable = True
            mock_pr.mergeable_state = "clean"
            mock_pr.head.ref = f"feature-{method}"
            mock_pr.base.ref = "main"

            merge_response = Mock()
            merge_response.merged = True
            merge_response.sha = f"sha_{method}"
            merge_response.message = f"Merged with {method}"
            mock_pr.merge.return_value = merge_response

            mock_repo.get_pull.return_value = mock_pr

            # Execute
            result = merge_pr(pr_number=50, merge_method=method)

            # Verify
            assert result["merged"] is True
            assert result["sha"] == f"sha_{method}"
            mock_pr.merge.assert_called_with(
                merge_method=method, commit_title=None, commit_message=None
            )
