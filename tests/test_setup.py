"""Tests for MCP server setup and infrastructure.

Tests basic server initialization, GitHub client authentication, and error handling.
"""

import os
from unittest.mock import MagicMock, patch

import pytest
from github_mcp_server.utils.errors import GitHubAPIError, handle_github_error
from github_mcp_server.utils.github_client import get_github_client, reset_github_client


class TestGitHubClient:
    """Test GitHub client singleton functionality."""

    def setup_method(self) -> None:
        """Reset singleton before each test."""
        reset_github_client()

    def teardown_method(self) -> None:
        """Reset singleton after each test."""
        reset_github_client()

    @patch.dict(os.environ, {"GITHUB_TOKEN": "test_token"})
    @patch("github_mcp_server.utils.github_client.Github")
    def test_get_github_client_success(self, mock_github: MagicMock) -> None:
        """Test successful GitHub client initialization."""
        # Mock authenticated user
        mock_user = MagicMock()
        mock_user.login = "testuser"
        mock_github.return_value.get_user.return_value = mock_user

        # Get client
        client = get_github_client()

        # Verify client was created with token
        mock_github.assert_called_once()
        assert client is not None

    @patch.dict(os.environ, {}, clear=True)
    def test_get_github_client_no_token(self) -> None:
        """Test error when GITHUB_TOKEN is not set."""
        with pytest.raises(ValueError) as exc_info:
            get_github_client()

        assert "GITHUB_TOKEN environment variable not set" in str(exc_info.value)

    @patch.dict(os.environ, {"GITHUB_TOKEN": "invalid_token"})
    @patch("github_mcp_server.utils.github_client.Github")
    def test_get_github_client_auth_failure(self, mock_github: MagicMock) -> None:
        """Test error when authentication fails."""
        # Mock authentication failure
        mock_github.return_value.get_user.side_effect = Exception("Bad credentials")

        with pytest.raises(Exception) as exc_info:
            get_github_client()

        assert "GitHub authentication failed" in str(exc_info.value)

    @patch.dict(os.environ, {"GITHUB_TOKEN": "test_token"})
    @patch("github_mcp_server.utils.github_client.Github")
    def test_get_github_client_singleton(self, mock_github: MagicMock) -> None:
        """Test that get_github_client returns the same instance."""
        # Mock authenticated user
        mock_user = MagicMock()
        mock_user.login = "testuser"
        mock_github.return_value.get_user.return_value = mock_user

        # Get client twice
        client1 = get_github_client()
        client2 = get_github_client()

        # Verify same instance and Github() called only once
        assert client1 is client2
        assert mock_github.call_count == 1


class TestErrorHandling:
    """Test error handling utilities."""

    def test_handle_github_error_404(self) -> None:
        """Test handling of 404 Not Found errors."""
        error = Exception("404 Not Found")
        result = handle_github_error(error)

        assert isinstance(result, GitHubAPIError)
        assert result.code == "RESOURCE_NOT_FOUND"
        assert result.details == {"status": 404}
        assert len(result.suggestions) > 0

    def test_handle_github_error_403(self) -> None:
        """Test handling of 403 Forbidden errors."""
        error = Exception("403 Forbidden")
        result = handle_github_error(error)

        assert isinstance(result, GitHubAPIError)
        assert result.code == "FORBIDDEN"
        assert result.details == {"status": 403}
        assert "github_token" in result.suggestions[0].lower()

    def test_handle_github_error_401(self) -> None:
        """Test handling of 401 Unauthorized errors."""
        error = Exception("401 Unauthorized")
        result = handle_github_error(error)

        assert isinstance(result, GitHubAPIError)
        assert result.code == "UNAUTHORIZED"
        assert result.details == {"status": 401}
        assert "GITHUB_TOKEN" in result.suggestions[0]

    def test_handle_github_error_422(self) -> None:
        """Test handling of 422 Validation Failed errors."""
        error = Exception("422 Validation Failed")
        result = handle_github_error(error)

        assert isinstance(result, GitHubAPIError)
        assert result.code == "VALIDATION_FAILED"
        assert result.details["status"] == 422
        # Additional fields from enhanced error extraction
        assert "field_errors" in result.details
        assert "raw_data" in result.details

    def test_handle_github_error_generic(self) -> None:
        """Test handling of generic errors."""
        error = Exception("Something went wrong")
        result = handle_github_error(error)

        assert isinstance(result, GitHubAPIError)
        assert result.code == "GITHUB_API_ERROR"
        assert "Something went wrong" in result.message

    def test_github_api_error_to_dict(self) -> None:
        """Test GitHubAPIError serialization to dict."""
        error = GitHubAPIError(
            code="TEST_ERROR",
            message="Test message",
            details={"key": "value"},
            suggestions=["Fix it"],
        )

        result = error.to_dict()

        assert result["error"] is True
        assert result["code"] == "TEST_ERROR"
        assert result["message"] == "Test message"
        assert result["details"] == {"key": "value"}
        assert result["suggestions"] == ["Fix it"]
