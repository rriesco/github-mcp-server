"""Common type definitions using TypedDict and dataclasses.

Provides structured types for MCP tool responses and internal data structures.
"""

from dataclasses import dataclass
from typing import Any, TypedDict


class IssueResponse(TypedDict):
    """
    Response format for issue operations.

    Attributes:
        number: Issue number
        title: Issue title
        state: Issue state (open, closed)
        url: HTML URL to the issue
        body: Optional issue body/description
    """

    number: int
    title: str
    state: str
    url: str
    body: str | None


class PRResponse(TypedDict):
    """
    Response format for pull request operations.

    Attributes:
        number: PR number
        title: PR title
        state: PR state (open, closed, merged)
        url: HTML URL to the PR
        mergeable: Whether the PR can be merged (None if not yet computed)
    """

    number: int
    title: str
    state: str
    url: str
    mergeable: bool | None


class CIStatusResponse(TypedDict):
    """
    Response format for CI status checks.

    Attributes:
        status: Overall status (queued, in_progress, completed)
        conclusion: Final conclusion if completed (success, failure, cancelled)
        workflows: List of workflow run details
    """

    status: str
    conclusion: str | None
    workflows: list[dict[str, Any]]


@dataclass(frozen=True)
class RepositoryConfig:
    """
    Repository configuration for GitHub operations.

    Attributes:
        owner: Repository owner username
        repo: Repository name
    """

    owner: str
    repo: str

    @property
    def full_name(self) -> str:
        """
        Get full repository name in 'owner/repo' format.

        Returns:
            Full repository name
        """
        return f"{self.owner}/{self.repo}"
