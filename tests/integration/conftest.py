"""Pytest configuration and fixtures for integration tests.

Provides test configuration, GitHub client setup, and cleanup utilities.
"""

import os
from collections.abc import Generator
from pathlib import Path

import pytest
from dotenv import load_dotenv
from github import Auth, Github
from github.Repository import Repository

# Load test environment variables
TEST_ENV_FILE = Path(__file__).parent.parent.parent / ".env.test"
if TEST_ENV_FILE.exists():
    load_dotenv(TEST_ENV_FILE)
else:
    # Fall back to regular .env for local development
    load_dotenv()


@pytest.fixture(scope="session")
def test_config() -> dict:
    """Provide test configuration from environment variables.

    Returns:
        Dictionary with test configuration including owner, repo, and token.

    Raises:
        pytest.skip: If GITHUB_TOKEN is not set (skips integration tests).
    """
    token = os.getenv("GITHUB_TOKEN")
    if not token:
        pytest.skip("GITHUB_TOKEN not set - skipping integration tests")

    owner = os.getenv("TEST_OWNER")
    repo = os.getenv("TEST_REPO")
    if not owner or not repo:
        pytest.skip("TEST_OWNER and TEST_REPO must be set for integration tests")

    return {
        "owner": owner,
        "repo": repo,
        "token": token,
    }


@pytest.fixture(scope="session")
def github_client(test_config: dict) -> Github:
    """Provide authenticated GitHub client for integration tests.

    Args:
        test_config: Test configuration fixture.

    Returns:
        Authenticated PyGithub client instance.
    """
    auth = Auth.Token(test_config["token"])
    return Github(auth=auth)


@pytest.fixture(scope="session")
def test_repository(github_client: Github, test_config: dict) -> Repository:
    """Provide test repository instance.

    Args:
        github_client: Authenticated GitHub client.
        test_config: Test configuration fixture.

    Returns:
        PyGithub Repository instance for the test repository.
    """
    return github_client.get_repo(f"{test_config['owner']}/{test_config['repo']}")


@pytest.fixture
def created_issues() -> Generator[list[int], None, None]:
    """Track created issue numbers for cleanup.

    Yields:
        List to store issue numbers created during tests.

    Note:
        Issues are automatically closed after the test completes.
    """
    issues: list[int] = []
    yield issues


@pytest.fixture
def cleanup_issues(
    test_repository: Repository, created_issues: list[int]
) -> Generator[None, None, None]:
    """Cleanup fixture that closes created issues after tests.

    Args:
        test_repository: Test repository instance.
        created_issues: List of issue numbers to cleanup.

    Note:
        This fixture runs after the test completes, closing all tracked issues.
    """
    yield

    # Cleanup: close all created issues
    for issue_number in created_issues:
        try:
            issue = test_repository.get_issue(issue_number)
            issue.edit(state="closed")
            print(f"✓ Cleaned up test issue #{issue_number}")
        except Exception as e:
            print(f"⚠ Warning: Failed to cleanup issue #{issue_number}: {e}")


@pytest.fixture
def created_milestones() -> Generator[list[int], None, None]:
    """Track created milestone numbers for cleanup.

    Yields:
        List to store milestone numbers created during tests.

    Note:
        Milestones can be manually closed after test (not auto-closed to avoid accidents).
    """
    milestones: list[int] = []
    yield milestones


@pytest.fixture
def cleanup_milestones(
    test_repository: Repository, created_milestones: list[int]
) -> Generator[None, None, None]:
    """Cleanup fixture that closes created milestones after tests.

    Args:
        test_repository: Test repository instance.
        created_milestones: List of milestone numbers to cleanup.

    Note:
        This fixture runs after the test completes, closing all tracked milestones.
        Milestones are closed rather than deleted to preserve history.
    """
    yield

    # Cleanup: close all created milestones
    for milestone_number in created_milestones:
        try:
            milestone = test_repository.get_milestone(milestone_number)
            milestone.edit(title=milestone.title, state="closed")
            print(f"✓ Cleaned up test milestone #{milestone_number}")
        except Exception as e:
            print(f"⚠ Warning: Failed to cleanup milestone #{milestone_number}: {e}")


def assert_issue_properties(
    issue_data: dict,
    expected_title: str | None = None,
    expected_labels: list[str] | None = None,
    expected_state: str = "open",
) -> None:
    """Helper to assert common issue properties.

    Args:
        issue_data: Issue data dictionary from tool response.
        expected_title: Expected issue title (optional).
        expected_labels: Expected label names (optional).
        expected_state: Expected issue state (default: "open").
    """
    assert "issue_number" in issue_data
    assert issue_data["issue_number"] > 0
    assert "url" in issue_data
    assert "github.com" in issue_data["url"]
    assert issue_data["state"] == expected_state

    if expected_title:
        assert issue_data["title"] == expected_title

    if expected_labels:
        assert "labels" in issue_data
        for label in expected_labels:
            assert label in issue_data["labels"]

    assert "created_at" in issue_data
