"""Unit tests for structured error handling.

Tests cover:
- GitHubAPIError dataclass structure
- Error conversion to dictionary format
- HTTP status code handling (404, 403, 401, 422)
- Suggestion generation
- Unknown error fallback
"""

import pytest
from github_mcp_server.utils.errors import GitHubAPIError, handle_github_error


class TestGitHubAPIError:
    """Test GitHubAPIError dataclass."""

    def test_error_creation_with_all_fields(self):
        """Test creating error with all fields."""
        error = GitHubAPIError(
            code="RESOURCE_NOT_FOUND",
            message="Issue #999 not found",
            details={"status": 404, "resource": "issue"},
            suggestions=["Verify the issue number", "Check repository access"],
        )

        assert error.code == "RESOURCE_NOT_FOUND"
        assert error.message == "Issue #999 not found"
        assert error.details == {"status": 404, "resource": "issue"}
        assert len(error.suggestions) == 2

    def test_error_creation_minimal_fields(self):
        """Test creating error with only required fields."""
        error = GitHubAPIError(code="TEST_ERROR", message="Test message")

        assert error.code == "TEST_ERROR"
        assert error.message == "Test message"
        assert error.details is None
        assert error.suggestions == []

    def test_error_to_dict_conversion(self):
        """Test converting error to dictionary format."""
        error = GitHubAPIError(
            code="VALIDATION_FAILED",
            message="Invalid parameters",
            details={"field": "title", "issue": "cannot be empty"},
            suggestions=["Provide a non-empty title"],
        )

        result = error.to_dict()

        assert result["error"] is True
        assert result["code"] == "VALIDATION_FAILED"
        assert result["message"] == "Invalid parameters"
        assert result["details"]["field"] == "title"
        assert len(result["suggestions"]) == 1

    def test_error_to_dict_minimal(self):
        """Test dictionary conversion with minimal fields."""
        error = GitHubAPIError(code="TEST", message="Test")

        result = error.to_dict()

        assert result["error"] is True
        assert result["code"] == "TEST"
        assert result["message"] == "Test"
        assert result["details"] is None
        assert result["suggestions"] == []

    def test_error_exception_behavior(self):
        """Test that error can be raised and caught as exception."""
        error = GitHubAPIError(code="TEST_ERROR", message="Test exception")

        with pytest.raises(GitHubAPIError) as exc_info:
            raise error

        assert str(exc_info.value) == "Test exception"
        assert exc_info.value.code == "TEST_ERROR"


class TestHandleGitHubError:
    """Test handle_github_error function for different error scenarios."""

    def test_handle_404_not_found(self):
        """Test handling 404 Not Found errors."""
        original_error = Exception("404 Not Found: Issue does not exist")

        result = handle_github_error(original_error)

        assert result.code == "RESOURCE_NOT_FOUND"
        assert "404" in str(result.message)
        assert result.details["status"] == 404
        assert len(result.suggestions) > 0
        assert any("exists" in s.lower() for s in result.suggestions)

    def test_handle_403_forbidden(self):
        """Test handling 403 Forbidden errors."""
        original_error = Exception("403 Forbidden: Access denied")

        result = handle_github_error(original_error)

        assert result.code == "FORBIDDEN"
        assert "token" in result.message.lower() or "permissions" in result.message.lower()
        assert result.details["status"] == 403
        assert len(result.suggestions) > 0
        assert any("token" in s.lower() for s in result.suggestions)

    def test_handle_401_unauthorized(self):
        """Test handling 401 Unauthorized errors."""
        original_error = Exception("401 Unauthorized: Bad credentials")

        result = handle_github_error(original_error)

        assert result.code == "UNAUTHORIZED"
        assert "authentication" in result.message.lower() or "failed" in result.message.lower()
        assert result.details["status"] == 401
        assert len(result.suggestions) > 0
        assert any("token" in s.lower() for s in result.suggestions)

    def test_handle_422_validation_failed(self):
        """Test handling 422 Validation Failed errors."""
        original_error = Exception("422 Unprocessable Entity: Validation failed")

        result = handle_github_error(original_error)

        assert result.code == "VALIDATION_FAILED"
        assert "validation" in result.message.lower() or "parameters" in result.message.lower()
        assert result.details["status"] == 422
        assert len(result.suggestions) > 0
        assert any("parameter" in s.lower() for s in result.suggestions)

    def test_handle_unknown_error(self):
        """Test handling unknown/generic errors."""
        original_error = Exception("Something went wrong")

        result = handle_github_error(original_error)

        assert result.code == "GITHUB_API_ERROR"
        assert result.message == "Something went wrong"
        assert "original_error" in result.details

    def test_handle_error_with_multiple_status_codes(self):
        """Test that most specific error code is matched first."""
        # If message contains multiple status codes, should match first pattern
        error_404 = Exception("404 Not Found (also mentions 403)")

        result = handle_github_error(error_404)

        # Should match 404, not 403
        assert result.code == "RESOURCE_NOT_FOUND"

    def test_suggestions_are_actionable(self):
        """Test that suggestions provide actionable guidance."""
        error_404 = Exception("404 Not Found")
        error_403 = Exception("403 Forbidden")
        error_401 = Exception("401 Unauthorized")

        result_404 = handle_github_error(error_404)
        result_403 = handle_github_error(error_403)
        result_401 = handle_github_error(error_401)

        # All should have suggestions
        assert len(result_404.suggestions) > 0
        assert len(result_403.suggestions) > 0
        assert len(result_401.suggestions) > 0

        # Suggestions should be strings
        assert all(isinstance(s, str) for s in result_404.suggestions)
        assert all(isinstance(s, str) for s in result_403.suggestions)
        assert all(isinstance(s, str) for s in result_401.suggestions)

        # Suggestions should be non-empty
        assert all(len(s) > 0 for s in result_404.suggestions)

    def test_error_details_preserved(self):
        """Test that error details are preserved in conversion."""
        original_error = Exception("404 Resource not found")

        result = handle_github_error(original_error)

        assert result.details is not None
        assert "status" in result.details
        assert result.details["status"] == 404


class TestErrorScenarios:
    """Test realistic error scenarios from tool usage."""

    def test_issue_not_found_error(self):
        """Test error when issue doesn't exist."""
        error = Exception("404 Not Found: Issue #999 does not exist")

        result = handle_github_error(error)

        assert result.code == "RESOURCE_NOT_FOUND"
        assert "verify" in " ".join(result.suggestions).lower()

    def test_repository_access_denied(self):
        """Test error when access is denied to repository."""
        error = Exception("403 Forbidden: You do not have access to this repository")

        result = handle_github_error(error)

        assert result.code == "FORBIDDEN"
        assert (
            "permissions" in " ".join(result.suggestions).lower()
            or "token" in " ".join(result.suggestions).lower()
        )

    def test_invalid_token_error(self):
        """Test error when token is invalid."""
        error = Exception("401 Unauthorized: Bad credentials")

        result = handle_github_error(error)

        assert result.code == "UNAUTHORIZED"
        assert "token" in " ".join(result.suggestions).lower()

    def test_validation_error_empty_title(self):
        """Test validation error for empty title."""
        error = Exception("422 Validation Failed: title cannot be blank")

        result = handle_github_error(error)

        assert result.code == "VALIDATION_FAILED"
        assert (
            "parameter" in " ".join(result.suggestions).lower()
            or "field" in " ".join(result.suggestions).lower()
        )

    def test_rate_limit_error(self):
        """Test handling rate limit errors (403)."""
        error = Exception("403 Forbidden: API rate limit exceeded")

        result = handle_github_error(error)

        assert result.code == "FORBIDDEN"
        # Suggestions should mention token or rate limits
        suggestions_text = " ".join(result.suggestions).lower()
        assert (
            "token" in suggestions_text
            or "rate" in suggestions_text
            or "permissions" in suggestions_text
        )


class TestErrorIntegration:
    """Integration tests for error handling in realistic workflows."""

    def test_error_serialization_for_api_response(self):
        """Test that error can be serialized for API responses."""
        error = GitHubAPIError(
            code="RESOURCE_NOT_FOUND",
            message="PR #42 not found",
            details={"pr_number": 42, "repository": "owner/repo"},
            suggestions=["Check PR number", "Verify repository name"],
        )

        # Should be serializable to dict
        error_dict = error.to_dict()

        # Should contain all necessary fields for client
        assert "error" in error_dict
        assert "code" in error_dict
        assert "message" in error_dict
        assert "suggestions" in error_dict

        # Should be JSON-serializable (test with json.dumps)
        import json

        json_str = json.dumps(error_dict)
        assert '"error": true' in json_str.lower()
        assert '"code": "RESOURCE_NOT_FOUND"' in json_str

    def test_error_handling_preserves_context(self):
        """Test that error handling preserves important context."""
        original_error = Exception("404 Not Found: Issue #123 in repo owner/test")

        result = handle_github_error(original_error)

        # Original message should be preserved
        assert "404" in result.message or "Issue" in result.message

        # Status code should be in details
        assert result.details["status"] == 404

    def test_multiple_errors_have_consistent_format(self):
        """Test that all error types return consistent format."""
        errors = [
            Exception("404 Not Found"),
            Exception("403 Forbidden"),
            Exception("401 Unauthorized"),
            Exception("422 Validation Failed"),
            Exception("Unknown error"),
        ]

        results = [handle_github_error(e) for e in errors]

        # All should have same structure
        for result in results:
            assert hasattr(result, "code")
            assert hasattr(result, "message")
            assert hasattr(result, "details")
            assert hasattr(result, "suggestions")

            # All should convert to dict with same keys
            result_dict = result.to_dict()
            assert "error" in result_dict
            assert "code" in result_dict
            assert "message" in result_dict
            assert "details" in result_dict
            assert "suggestions" in result_dict
