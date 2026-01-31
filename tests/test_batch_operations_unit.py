"""Unit tests for batch operations with mocked GitHub API.

These tests use mocks and don't require GITHUB_TOKEN or network access.
Run with: pytest tests/test_batch_operations_unit.py
"""

from unittest.mock import Mock, patch

import pytest
from github_mcp_server.tools.batch_operations import (
    BatchOperationResult,
    BatchResponse,
    batch_add_labels,
    batch_link_to_project,
    batch_update_issues,
)


class TestBatchOperationResult:
    """Unit tests for BatchOperationResult dataclass."""

    def test_success_result_to_dict(self) -> None:
        """Test converting successful result to dictionary."""
        result = BatchOperationResult(
            index=0,
            success=True,
            data={"issue_number": 123, "url": "https://github.com/test/repo/issues/123"},
        )

        result_dict = result.to_dict()

        assert result_dict["index"] == 0
        assert result_dict["success"] is True
        assert result_dict["data"]["issue_number"] == 123
        assert "error" not in result_dict

    def test_failure_result_to_dict(self) -> None:
        """Test converting failed result to dictionary."""
        result = BatchOperationResult(
            index=1,
            success=False,
            error={
                "code": "RESOURCE_NOT_FOUND",
                "message": "Issue not found",
            },
        )

        result_dict = result.to_dict()

        assert result_dict["index"] == 1
        assert result_dict["success"] is False
        assert result_dict["error"]["code"] == "RESOURCE_NOT_FOUND"
        assert "data" not in result_dict


class TestBatchResponse:
    """Unit tests for BatchResponse dataclass."""

    def test_batch_response_to_dict(self) -> None:
        """Test converting batch response to dictionary."""
        results = [
            BatchOperationResult(index=0, success=True, data={"issue_number": 1}),
            BatchOperationResult(index=1, success=True, data={"issue_number": 2}),
            BatchOperationResult(index=2, success=False, error={"code": "ERROR"}),
        ]

        response = BatchResponse(
            total=3,
            successful=2,
            failed=1,
            results=results,
            execution_time_seconds=1.5,
        )

        response_dict = response.to_dict()

        assert response_dict["total"] == 3
        assert response_dict["successful"] == 2
        assert response_dict["failed"] == 1
        assert response_dict["success_rate"] == "66.7%"
        assert response_dict["execution_time_seconds"] == 1.5
        assert len(response_dict["results"]) == 3

    def test_batch_response_zero_total(self) -> None:
        """Test success rate calculation with zero operations."""
        response = BatchResponse(total=0, successful=0, failed=0)

        response_dict = response.to_dict()

        assert response_dict["success_rate"] == "0%"


class TestBatchUpdateIssues:
    """Unit tests for batch_update_issues tool."""

    @patch("github_mcp_server.tools.batch_operations.get_github_client")
    def test_batch_update_issues_success(self, mock_get_client: Mock) -> None:
        """Test successful batch update."""
        mock_gh = Mock()
        mock_repo = Mock()
        mock_issue = Mock()
        mock_issue.number = 123
        mock_issue.html_url = "https://github.com/test/repo/issues/123"

        mock_repo.get_issue.return_value = mock_issue
        mock_gh.get_repo.return_value = mock_repo
        mock_get_client.return_value = mock_gh

        result = batch_update_issues(
            updates=[
                {"issue_number": 123, "title": "New Title"},
                {"issue_number": 124, "state": "closed"},
            ],
            owner="test",
            repo="repo",
        )

        assert result["total"] == 2
        assert result["successful"] == 2
        assert result["failed"] == 0

    def test_batch_update_issues_missing_issue_number_raises_error(self) -> None:
        """Test that missing issue_number raises ValueError."""
        with pytest.raises(ValueError, match="missing required 'issue_number'"):
            batch_update_issues(
                updates=[{"title": "No issue number"}],
                owner="test",
                repo="repo",
            )


class TestBatchAddLabels:
    """Unit tests for batch_add_labels tool."""

    @patch("github_mcp_server.tools.batch_operations.get_github_client")
    def test_batch_add_labels_success(self, mock_get_client: Mock) -> None:
        """Test successful batch label addition."""
        mock_gh = Mock()
        mock_repo = Mock()
        mock_issue = Mock()
        mock_issue.number = 123
        mock_issue.labels = [Mock(name="test"), Mock(name="new")]

        mock_repo.get_issue.return_value = mock_issue
        mock_gh.get_repo.return_value = mock_repo
        mock_get_client.return_value = mock_gh

        result = batch_add_labels(
            operations=[
                {"issue_number": 123, "labels": ["new", "enhancement"]},
            ],
            owner="test",
            repo="repo",
        )

        assert result["total"] == 1
        assert result["successful"] == 1
        assert result["failed"] == 0

        # Verify add_to_labels was called
        mock_issue.add_to_labels.assert_called_once_with("new", "enhancement")

    def test_batch_add_labels_missing_fields_raises_error(self) -> None:
        """Test that missing required fields raise ValueError."""
        with pytest.raises(ValueError, match="missing required 'issue_number'"):
            batch_add_labels(
                operations=[{"labels": ["test"]}],
                owner="test",
                repo="repo",
            )

        with pytest.raises(ValueError, match="missing required 'labels'"):
            batch_add_labels(
                operations=[{"issue_number": 123}],
                owner="test",
                repo="repo",
            )

        with pytest.raises(ValueError, match="empty 'labels' list"):
            batch_add_labels(
                operations=[{"issue_number": 123, "labels": []}],
                owner="test",
                repo="repo",
            )


class TestBatchLinkToProject:
    """Unit tests for batch_link_to_project tool."""

    def test_batch_link_invalid_project_id_raises_error(self) -> None:
        """Test that invalid project ID raises ValueError."""
        with pytest.raises(ValueError, match="must be a valid GitHub Project node ID"):
            batch_link_to_project(
                issue_numbers=[123],
                project_id="invalid",
                owner="test",
                repo="repo",
            )

        with pytest.raises(ValueError, match="must be a valid GitHub Project node ID"):
            batch_link_to_project(
                issue_numbers=[123],
                project_id="",
                owner="test",
                repo="repo",
            )

    def test_batch_link_empty_list_raises_error(self) -> None:
        """Test that empty issue list raises ValueError."""
        with pytest.raises(ValueError, match="cannot be empty"):
            batch_link_to_project(
                issue_numbers=[],
                project_id="PVT_test",
                owner="test",
                repo="repo",
            )


class TestBatchOperationsMaxWorkers:
    """Test that max_workers parameter is properly clamped."""

    @patch("github_mcp_server.tools.batch_operations.get_github_client")
    def test_max_workers_clamped_to_range(self, mock_get_client: Mock) -> None:
        """Test that max_workers is clamped to 1-10 range via batch_update_issues."""
        mock_gh = Mock()
        mock_repo = Mock()
        mock_issue = Mock()
        mock_issue.number = 123
        mock_issue.html_url = "https://github.com/test/repo/issues/123"

        mock_repo.get_issue.return_value = mock_issue
        mock_gh.get_repo.return_value = mock_repo
        mock_get_client.return_value = mock_gh

        # Test with max_workers=0 (should be clamped to 1)
        result = batch_update_issues(
            updates=[{"issue_number": 123, "title": "Test"}],
            max_workers=0,
        )
        assert result["successful"] == 1

        # Test with max_workers=100 (should be clamped to 10)
        result = batch_update_issues(
            updates=[{"issue_number": 123, "title": "Test"}],
            max_workers=100,
        )
        assert result["successful"] == 1
