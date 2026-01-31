"""Structured error handling for GitHub API operations.

Provides custom error classes and utilities for handling GitHub API errors
with actionable error messages and troubleshooting suggestions.
"""

import logging
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class GitHubAPIError(Exception):
    """
    Custom error class for GitHub API errors with structured information.

    Attributes:
        code: Error code for categorization (e.g., "RESOURCE_NOT_FOUND")
        message: Human-readable error message
        details: Optional additional error details
        suggestions: Optional troubleshooting suggestions

    Example:
        >>> error = GitHubAPIError(
        ...     code="RESOURCE_NOT_FOUND",
        ...     message="Issue #999 not found",
        ...     details={"status": 404},
        ...     suggestions=["Verify the issue number", "Check repository access"]
        ... )
        >>> error.to_dict()
        {'error': True, 'code': 'RESOURCE_NOT_FOUND', ...}
    """

    code: str
    message: str
    details: dict[str, Any] | None = None
    suggestions: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        """Initialize the exception base class."""
        super().__init__(self.message)

    def to_dict(self) -> dict[str, Any]:
        """
        Convert error to dictionary for structured responses.

        Returns:
            Dictionary with error information including code, message, details, and suggestions
        """
        return {
            "error": True,
            "code": self.code,
            "message": self.message,
            "details": self.details,
            "suggestions": self.suggestions,
        }


def _extract_validation_errors(data: Any) -> tuple[str, list[str]]:
    """
    Extract detailed validation error messages from GitHub API response.

    Args:
        data: Response data from GithubException (typically a dict)

    Returns:
        Tuple of (main_message, list_of_field_errors)
    """
    if not isinstance(data, dict):
        return "Validation failed", []

    # GitHub API returns errors in different formats
    message = data.get("message", "Validation failed")
    errors = data.get("errors", [])

    field_errors = []
    for error in errors:
        if isinstance(error, dict):
            field = error.get("field", "unknown")
            code = error.get("code", "invalid")
            error_message = error.get("message", "")

            if error_message:
                field_errors.append(f"Field '{field}': {error_message}")
            elif code == "missing_field":
                field_errors.append(f"Field '{field}' is required but missing")
            elif code == "invalid":
                field_errors.append(f"Field '{field}' has an invalid value")
            elif code == "already_exists":
                field_errors.append(f"Field '{field}' already exists (duplicate)")
            elif code == "custom":
                field_errors.append(f"Field '{field}': custom validation error")
            else:
                field_errors.append(f"Field '{field}': {code}")
        elif isinstance(error, str):
            field_errors.append(error)

    return message, field_errors


def handle_github_error(error: Exception) -> GitHubAPIError:
    """
    Handle GitHub API errors and convert to structured GitHubAPIError.

    Provides specific error codes and actionable suggestions based on
    exception types and HTTP status codes. For validation errors (422),
    extracts detailed field-level error information from PyGithub's
    GithubException.data property.

    Args:
        error: Exception from PyGithub API call (typically GithubException)

    Returns:
        GitHubAPIError with structured information including detailed
        validation messages when available

    Example:
        >>> try:
        ...     repo.get_issue(999)
        ... except Exception as e:
        ...     structured_error = handle_github_error(e)
        ...     print(structured_error.to_dict())
    """
    # Try to extract status and data from GithubException
    status = None
    data = None

    # Check if this is a GithubException with status and data attributes
    if hasattr(error, "status"):
        status = error.status
    if hasattr(error, "data"):
        data = error.data

    error_str = str(error)

    # Handle based on status code
    if status == 404 or "404" in error_str:
        return GitHubAPIError(
            code="RESOURCE_NOT_FOUND",
            message=str(error),
            details={"status": 404},
            suggestions=["Verify the resource exists", "Check you have access to this repository"],
        )

    if status == 403 or "403" in error_str:
        return GitHubAPIError(
            code="FORBIDDEN",
            message="Access denied. Check token permissions.",
            details={"status": 403},
            suggestions=[
                "Verify GITHUB_TOKEN has required scopes",
                "Check repository access permissions",
            ],
        )

    if status == 401 or "401" in error_str:
        return GitHubAPIError(
            code="UNAUTHORIZED",
            message="Authentication failed.",
            details={"status": 401},
            suggestions=["Verify GITHUB_TOKEN is valid", "Token may have expired"],
        )

    if status == 422 or "422" in error_str:
        # Extract detailed validation errors
        main_message, field_errors = _extract_validation_errors(data)

        # Build detailed message
        if field_errors:
            detailed_message = f"{main_message}:\n" + "\n".join(f"  - {e}" for e in field_errors)
        else:
            detailed_message = main_message

        suggestions = [
            "Review the parameter values in your request",
            "Check GitHub API documentation for required fields and formats",
        ]

        # Add specific suggestions based on field errors
        if any("title" in e.lower() for e in field_errors):
            suggestions.append("PR title must be non-empty and not exceed 256 characters")
        if any("body" in e.lower() for e in field_errors):
            suggestions.append("PR body must not exceed 65536 characters")
        if any("head" in e.lower() for e in field_errors):
            suggestions.append("Ensure the head branch exists and has been pushed to remote")
        if any("base" in e.lower() for e in field_errors):
            suggestions.append("Ensure the base branch exists in the repository")

        return GitHubAPIError(
            code="VALIDATION_FAILED",
            message=detailed_message,
            details={"status": 422, "field_errors": field_errors, "raw_data": data},
            suggestions=suggestions,
        )

    return GitHubAPIError(
        code="GITHUB_API_ERROR",
        message=str(error),
        details={"original_error": type(error).__name__},
    )
