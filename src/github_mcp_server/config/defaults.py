"""Default configuration values for GitHub operations.

Provides default repository settings from environment variables.
Users can set GITHUB_OWNER and GITHUB_REPO environment variables
to configure default repository for all operations.
"""

import os

from ..utils.types import RepositoryConfig

# Default repository configuration from environment variables
# If not set, defaults to empty string (tools will require explicit values)
DEFAULT_OWNER = os.getenv("GITHUB_OWNER", "")
DEFAULT_REPO = os.getenv("GITHUB_REPO", "")

# Create default repository config instance
DEFAULT_REPOSITORY = RepositoryConfig(owner=DEFAULT_OWNER, repo=DEFAULT_REPO)
