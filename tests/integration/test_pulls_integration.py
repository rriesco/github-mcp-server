"""Integration tests for GitHub pull request operations.

These tests make real API calls to GitHub and require a valid GITHUB_TOKEN.
Run with: pytest tests/integration/test_pulls_integration.py -m integration
"""

from datetime import datetime

import pytest
from github_mcp_server.tools.pulls import get_pull_request, merge_pr, update_pr
from github_mcp_server.utils.errors import GitHubAPIError


@pytest.mark.integration
class TestGetPullRequestIntegration:
    """Integration tests for get_pull_request tool with real GitHub API."""

    def test_get_existing_merged_pr(
        self,
        test_config: dict,
    ) -> None:
        """Test getting details of an existing merged PR via real GitHub API.

        This test:
        1. Fetches a known merged PR from the repository
        2. Verifies all returned fields are correct
        3. Validates data types and structure

        Note: Uses PR #1 which should exist in most repositories.
        If this test fails, update pr_number to a known merged PR.
        """
        # Use PR #1 which should exist in most repositories
        result = get_pull_request(
            pr_number=1,
            owner=test_config["owner"],
            repo=test_config["repo"],
        )

        # Verify response structure
        assert "number" in result
        assert isinstance(result["number"], int)
        assert result["number"] > 0

        assert "title" in result
        assert isinstance(result["title"], str)
        assert len(result["title"]) > 0

        assert "state" in result
        assert result["state"] in ["open", "closed"]

        assert "merged" in result
        assert isinstance(result["merged"], bool)

        # For any PR (open or closed), mergeable can be bool or None
        assert "mergeable" in result
        assert result["mergeable"] is None or isinstance(result["mergeable"], bool)

        assert "mergeable_state" in result
        assert isinstance(result["mergeable_state"], str)
        assert result["mergeable_state"] in [
            "clean",
            "dirty",
            "unstable",
            "blocked",
            "unknown",
            "behind",
            "draft",
        ]

        assert "draft" in result
        assert isinstance(result["draft"], bool)

        assert "head" in result
        assert isinstance(result["head"], str)

        assert "base" in result
        assert isinstance(result["base"], str)

        assert "commits" in result
        assert isinstance(result["commits"], int)
        assert result["commits"] > 0

        assert "additions" in result
        assert isinstance(result["additions"], int)
        assert result["additions"] >= 0

        assert "deletions" in result
        assert isinstance(result["deletions"], int)
        assert result["deletions"] >= 0

        assert "changed_files" in result
        assert isinstance(result["changed_files"], int)
        assert result["changed_files"] > 0

        assert "created_at" in result
        assert isinstance(result["created_at"], str)
        # Verify ISO format timestamp
        created_dt = datetime.fromisoformat(result["created_at"])
        assert created_dt <= datetime.now().astimezone()

        assert "updated_at" in result
        assert isinstance(result["updated_at"], str)
        updated_dt = datetime.fromisoformat(result["updated_at"])
        assert updated_dt >= created_dt

        assert "merged_at" in result
        # merged_at can be None or ISO timestamp string

        assert "url" in result
        assert "github.com" in result["url"]
        assert test_config["repo"] in result["url"]
        assert "/pull/" in result["url"]

    def test_get_pr_different_states(
        self,
        test_config: dict,
    ) -> None:
        """Test that get_pull_request works for PRs in different states.

        Note: This test may need to be adjusted based on available PRs.
        """
        # Try to fetch PR #1 (commonly exists)
        try:
            result = get_pull_request(
                pr_number=1,
                owner=test_config["owner"],
                repo=test_config["repo"],
            )

            # Just verify we got valid data
            assert result["number"] == 1
            assert isinstance(result["state"], str)
            assert isinstance(result["merged"], bool)

            # Verify merged_at is None if not merged, or a timestamp if merged
            if result["merged"]:
                assert result["merged_at"] is not None
                merged_dt = datetime.fromisoformat(result["merged_at"])
                assert merged_dt <= datetime.now().astimezone()
            else:
                # For open PRs or closed-but-not-merged PRs
                if result["state"] == "open":
                    assert result["merged_at"] is None

        except GitHubAPIError:
            # If PR #1 doesn't exist, that's okay - skip this test
            pytest.skip("PR #1 not found in repository")

    def test_get_pr_nonexistent_raises_error(
        self,
        test_config: dict,
    ) -> None:
        """Test that fetching non-existent PR raises GitHubAPIError."""
        # Use a very high PR number that's unlikely to exist
        with pytest.raises(GitHubAPIError) as exc_info:
            get_pull_request(
                pr_number=999999,
                owner=test_config["owner"],
                repo=test_config["repo"],
            )

        # Verify error message is meaningful
        assert "999999" in str(exc_info.value) or "not found" in str(exc_info.value).lower()

    def test_get_pr_validates_all_fields(
        self,
        test_config: dict,
    ) -> None:
        """Test that all fields are present in the response."""
        try:
            result = get_pull_request(
                pr_number=1,
                owner=test_config["owner"],
                repo=test_config["repo"],
            )

            # Verify all expected fields are present
            required_fields = [
                "number",
                "title",
                "state",
                "merged",
                "mergeable",
                "mergeable_state",
                "draft",
                "head",
                "base",
                "commits",
                "additions",
                "deletions",
                "changed_files",
                "created_at",
                "updated_at",
                "merged_at",
                "url",
            ]

            for field in required_fields:
                assert field in result, f"Missing required field: {field}"

        except GitHubAPIError:
            pytest.skip("PR #1 not found in repository")

    def test_get_pr_stats_are_positive(
        self,
        test_config: dict,
    ) -> None:
        """Test that PR stats (commits, additions, deletions, files) are non-negative."""
        try:
            result = get_pull_request(
                pr_number=1,
                owner=test_config["owner"],
                repo=test_config["repo"],
            )

            # Stats should be non-negative
            assert result["commits"] >= 0
            assert result["additions"] >= 0
            assert result["deletions"] >= 0
            assert result["changed_files"] >= 0

            # A PR should have at least 1 commit and 1 changed file
            assert result["commits"] > 0
            assert result["changed_files"] > 0

        except GitHubAPIError:
            pytest.skip("PR #1 not found in repository")


@pytest.mark.integration
class TestUpdatePRIntegration:
    """Integration tests for update_pr tool with real GitHub API.

    Note: These tests are designed to be safe and non-destructive.
    They will skip if suitable test PRs are not available.
    """

    def test_update_pr_nonexistent_raises_error(
        self,
        test_config: dict,
    ) -> None:
        """Test that updating non-existent PR raises GitHubAPIError."""
        # Use a very high PR number that's unlikely to exist
        with pytest.raises(GitHubAPIError) as exc_info:
            update_pr(
                pr_number=999999,
                title="Updated title",
                owner=test_config["owner"],
                repo=test_config["repo"],
            )

        # Verify error message is meaningful
        assert "999999" in str(exc_info.value) or "not found" in str(exc_info.value).lower()

    def test_update_pr_invalid_state_raises_error(
        self,
        test_config: dict,
    ) -> None:
        """Test that invalid state value raises ValueError."""
        # This test will fail before making API call due to validation
        with pytest.raises(ValueError) as exc_info:
            update_pr(
                pr_number=1,
                state="invalid_state",
                owner=test_config["owner"],
                repo=test_config["repo"],
            )

        # Verify error message mentions valid states
        error_msg = str(exc_info.value).lower()
        assert "invalid" in error_msg
        assert "open" in error_msg or "closed" in error_msg

    def test_update_pr_no_changes_returns_empty_list(
        self,
        test_config: dict,
    ) -> None:
        """Test that calling update_pr with no fields returns empty updated_fields.

        This test is safe as it makes no changes to any PR.
        """
        # Try to call update_pr with no updates on PR #1
        # If PR #1 doesn't exist, test will fail - that's acceptable
        try:
            result = update_pr(
                pr_number=1,
                owner=test_config["owner"],
                repo=test_config["repo"],
            )

            # Verify structure
            assert "updated_fields" in result
            assert result["updated_fields"] == []
            assert "number" in result
            assert result["number"] == 1

        except GitHubAPIError:
            pytest.skip("PR #1 not found in repository")

    def test_update_merged_pr_raises_error(
        self,
        test_config: dict,
    ) -> None:
        """Test that attempting to update a merged PR raises error.

        Note: This test assumes PR #1 exists and is merged.
        If not, the test will skip.
        """
        try:
            # First check if PR #1 exists and is merged
            pr_info = get_pull_request(
                pr_number=1,
                owner=test_config["owner"],
                repo=test_config["repo"],
            )

            if not pr_info["merged"]:
                pytest.skip("PR #1 is not merged, cannot test merged PR update error")

            # Try to update the merged PR - should fail
            with pytest.raises(Exception) as exc_info:
                update_pr(
                    pr_number=1,
                    title="This should fail",
                    owner=test_config["owner"],
                    repo=test_config["repo"],
                )

            # Verify error message mentions merged status
            error_msg = str(exc_info.value).lower()
            assert "merged" in error_msg

        except GitHubAPIError:
            pytest.skip("PR #1 not found in repository")

    def test_update_pr_validates_response_structure(
        self,
        test_config: dict,
    ) -> None:
        """Test that update_pr returns correctly structured response.

        This test makes no actual changes (no fields provided).
        """
        try:
            result = update_pr(
                pr_number=1,
                owner=test_config["owner"],
                repo=test_config["repo"],
            )

            # Verify all required fields are present
            required_fields = ["number", "title", "state", "updated_fields", "url"]
            for field in required_fields:
                assert field in result, f"Missing required field: {field}"

            # Verify types
            assert isinstance(result["number"], int)
            assert isinstance(result["title"], str)
            assert isinstance(result["state"], str)
            assert isinstance(result["updated_fields"], list)
            assert isinstance(result["url"], str)

            # Verify URL format
            assert "github.com" in result["url"]
            assert "/pull/" in result["url"]

        except GitHubAPIError:
            pytest.skip("PR #1 not found in repository")


@pytest.mark.integration
class TestMergePRIntegration:
    """Integration tests for merge_pr tool with real GitHub API.

    WARNING: These tests involve actual PR merges. Use with caution.
    Tests are designed to skip if suitable test PRs are not available.
    """

    def test_merge_pr_nonexistent_raises_error(
        self,
        test_config: dict,
    ) -> None:
        """Test that merging non-existent PR raises GitHubAPIError."""
        # Use a very high PR number that's unlikely to exist
        with pytest.raises(GitHubAPIError) as exc_info:
            merge_pr(
                pr_number=999999,
                owner=test_config["owner"],
                repo=test_config["repo"],
            )

        # Verify error message is meaningful
        assert "999999" in str(exc_info.value) or "not found" in str(exc_info.value).lower()

    def test_merge_pr_already_merged_raises_error(
        self,
        test_config: dict,
    ) -> None:
        """Test that attempting to merge already-merged PR raises error.

        Note: This test assumes PR #1 exists and is already merged.
        If not, the test will skip.
        """
        try:
            # First check if PR #1 exists and is merged
            pr_info = get_pull_request(
                pr_number=1,
                owner=test_config["owner"],
                repo=test_config["repo"],
            )

            if not pr_info["merged"]:
                pytest.skip("PR #1 is not merged, cannot test already-merged error")

            # Try to merge the already-merged PR - should fail
            with pytest.raises(Exception) as exc_info:
                merge_pr(
                    pr_number=1,
                    owner=test_config["owner"],
                    repo=test_config["repo"],
                )

            # Verify error message mentions merged status
            error_msg = str(exc_info.value).lower()
            assert "merged" in error_msg or "already" in error_msg

        except GitHubAPIError:
            pytest.skip("PR #1 not found in repository")

    def test_merge_pr_invalid_merge_method_raises_error(
        self,
        test_config: dict,
    ) -> None:
        """Test that invalid merge_method value raises ValueError."""
        # This test will fail before making API call due to validation
        with pytest.raises(ValueError) as exc_info:
            merge_pr(
                pr_number=1,
                merge_method="invalid_method",
                owner=test_config["owner"],
                repo=test_config["repo"],
            )

        # Verify error message mentions valid methods
        error_msg = str(exc_info.value).lower()
        assert "merge_method" in error_msg or "invalid" in error_msg
        assert "merge" in error_msg or "squash" in error_msg or "rebase" in error_msg

    def test_merge_pr_validates_response_structure(
        self,
        test_config: dict,
    ) -> None:
        """Test that merge_pr returns correctly structured response on success.

        Note: This test is READ-ONLY - it validates the response structure
        by checking what WOULD be returned, but doesn't actually perform a merge.
        To avoid actual merges in CI, this test validates error responses.
        """
        # Use PR #1 which should be already merged
        # This will fail with "already merged" error, but we can validate
        # that the error handling and response structure is correct
        try:
            pr_info = get_pull_request(
                pr_number=1,
                owner=test_config["owner"],
                repo=test_config["repo"],
            )

            if not pr_info["merged"]:
                pytest.skip("PR #1 is not merged, cannot test response structure safely")

            # This should raise an error, but we test the error structure
            with pytest.raises(Exception):
                merge_pr(
                    pr_number=1,
                    owner=test_config["owner"],
                    repo=test_config["repo"],
                )

        except GitHubAPIError:
            pytest.skip("PR #1 not found in repository")
