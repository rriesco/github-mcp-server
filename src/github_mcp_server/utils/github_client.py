"""GitHub client utilities."""

import logging
import os

from github import Auth, Github
from github.Repository import Repository

logger = logging.getLogger(__name__)

_github_instance: Github | None = None


def get_github_client() -> Github:
    """Get authenticated GitHub client (singleton)."""
    global _github_instance

    if _github_instance is None:
        token = os.getenv("GITHUB_TOKEN")

        if not token:
            raise ValueError(
                "GITHUB_TOKEN environment variable not set. "
                "Please create .env file with GITHUB_TOKEN=ghp_..."
            )

        auth = Auth.Token(token)
        _github_instance = Github(auth=auth)

        # Verify authentication
        try:
            user = _github_instance.get_user()
            logger.info(f"✅ Authenticated as: {user.login}")
        except Exception as e:
            raise Exception(
                f"GitHub authentication failed: {str(e)}. Check GITHUB_TOKEN is valid."
            ) from e

    return _github_instance


def get_repository(owner: str, repo: str) -> Repository:
    """Get authenticated repository instance."""
    gh = get_github_client()
    return gh.get_repo(f"{owner}/{repo}")


def reset_github_client() -> None:
    """Reset GitHub client singleton (for testing)."""
    global _github_instance
    _github_instance = None
