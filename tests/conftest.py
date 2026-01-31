"""Root pytest configuration for github-mcp-server tests.

Sets up environment variables for default owner/repo used in unit tests.
"""

import importlib
import os

import pytest


def pytest_configure(config: pytest.Config) -> None:
    """Set up test environment before tests run."""
    # Set default owner/repo for unit tests
    # These are used by defaults.py when tools are called without explicit owner/repo
    os.environ["GITHUB_OWNER"] = "testowner"
    os.environ["GITHUB_REPO"] = "testrepo"

    # Reload the defaults module to pick up the new environment variables
    # This is needed because defaults.py evaluates os.getenv at import time
    import github_mcp_server.config.defaults as defaults_module

    importlib.reload(defaults_module)
