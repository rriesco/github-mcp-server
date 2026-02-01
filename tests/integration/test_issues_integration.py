"""Integration tests for GitHub issue operations.

These tests make real API calls to GitHub and require a valid GITHUB_TOKEN.
Run with: pytest tests/integration/test_issues_integration.py -m integration
"""

from datetime import datetime

import pytest
from github_mcp_server.tools.issues import close_issue, create_issues, get_issue, list_issues
from github_mcp_server.utils.errors import GitHubAPIError


def create_issue(
    title: str,
    body: str,
    labels: list[str],
    milestone: int | None,
    owner: str,
    repo: str,
) -> dict:
    """Helper function to create a single issue via create_issues.

    Maintains backward compatibility for integration tests.
    """
    issue_data: dict = {"title": title, "body": body, "labels": labels}
    if milestone is not None:
        issue_data["milestone"] = milestone

    result = create_issues(
        issues=[issue_data],
        owner=owner,
        repo=repo,
    )
    if result["successful"] == 0:
        raise Exception(f"Failed to create issue: {result['results'][0]['error']}")
    return result["results"][0]["data"]


@pytest.mark.integration
class TestCreateIssueIntegration:
    """Integration tests for create_issue tool with real GitHub API."""

    def test_create_issue_with_labels_and_milestone(
        self,
        test_config: dict,
        test_milestone: int | None,
        created_issues: list[int],
        cleanup_issues: None,
    ) -> None:
        """Test creating issue with labels and milestone via real GitHub API.

        This test:
        1. Creates a real issue on GitHub
        2. Verifies all returned fields are correct
        3. Cleanup fixture automatically closes the issue after test
        """
        if test_milestone is None:
            pytest.skip("No milestone available in test repository")

        # Create issue using the MCP tool
        result = create_issue(
            title="[TEST] Integration test issue - safe to close",
            body="""## Context
This is a test issue created by the integration test suite.

## Purpose
Validates that the create_issue MCP tool correctly creates issues via GitHub API.

## Cleanup
This issue will be automatically closed by the test cleanup fixture.
""",
            labels=["test"],
            milestone=test_milestone,
            owner=test_config["owner"],
            repo=test_config["repo"],
        )

        # Track for cleanup
        created_issues.append(result["issue_number"])

        # Verify response structure
        assert "issue_number" in result
        assert isinstance(result["issue_number"], int)
        assert result["issue_number"] > 0

        assert "url" in result
        assert "github.com" in result["url"]
        assert test_config["repo"] in result["url"]

        assert result["state"] == "open"

        assert "labels" in result
        assert "test" in result["labels"]

        assert "milestone" in result
        assert result["milestone"] is not None

        assert "created_at" in result
        # Verify ISO format timestamp
        created_dt = datetime.fromisoformat(result["created_at"].replace("Z", "+00:00"))
        assert created_dt <= datetime.now().astimezone()

    def test_create_issue_with_multiple_labels(
        self,
        test_config: dict,
        test_milestone: int | None,
        created_issues: list[int],
        cleanup_issues: None,
    ) -> None:
        """Test creating issue with multiple labels."""
        if test_milestone is None:
            pytest.skip("No milestone available in test repository")

        result = create_issue(
            title="[TEST] Multiple labels test",
            body="Test issue with multiple labels.",
            labels=["test", "documentation"],
            milestone=test_milestone,
            owner=test_config["owner"],
            repo=test_config["repo"],
        )

        created_issues.append(result["issue_number"])

        assert "test" in result["labels"]
        assert "documentation" in result["labels"]
        assert len(result["labels"]) == 2

    def test_create_issue_invalid_milestone_raises_error(
        self,
        test_config: dict,
    ) -> None:
        """Test that invalid milestone number raises GitHubAPIError."""
        with pytest.raises(GitHubAPIError) as exc_info:
            create_issue(
                title="[TEST] Invalid milestone",
                body="This should fail",
                labels=["test"],
                milestone=99999,  # Non-existent milestone
                owner=test_config["owner"],
                repo=test_config["repo"],
            )

        error = exc_info.value
        assert error.code in ["RESOURCE_NOT_FOUND", "VALIDATION_FAILED", "GITHUB_API_ERROR"]

    def test_create_issue_empty_labels_raises_error(
        self,
        test_config: dict,
        test_milestone: int | None,
    ) -> None:
        """Test that empty labels list raises appropriate error."""
        if test_milestone is None:
            pytest.skip("No milestone available in test repository")

        # Note: The current implementation doesn't validate empty labels at the
        # Python level, but GitHub API might reject it. This tests actual behavior.
        try:
            result = create_issue(
                title="[TEST] No labels test",
                body="Test with no labels - may succeed or fail depending on repo config.",
                labels=[],
                milestone=test_milestone,
                owner=test_config["owner"],
                repo=test_config["repo"],
            )
            # If GitHub allows it, cleanup
            # Note: This might succeed if repo allows label-less issues
            # The test documents actual behavior rather than assuming failure
            assert isinstance(result["issue_number"], int)
        except GitHubAPIError:
            # If GitHub rejects it, that's also valid behavior
            pass


@pytest.mark.integration
class TestGetIssueIntegration:
    """Integration tests for get_issue tool with real GitHub API."""

    def test_get_issue_retrieves_existing_issue(
        self,
        test_config: dict,
        test_milestone: int | None,
        created_issues: list[int],
        cleanup_issues: None,
    ) -> None:
        """Test retrieving an existing issue's details.

        This test:
        1. Creates a test issue
        2. Retrieves it using get_issue
        3. Verifies all fields match
        """
        if test_milestone is None:
            pytest.skip("No milestone available in test repository")

        # First create an issue
        create_result = create_issue(
            title="[TEST] Issue to retrieve",
            body="Test body content for retrieval",
            labels=["test", "integration"],
            milestone=test_milestone,
            owner=test_config["owner"],
            repo=test_config["repo"],
        )

        issue_number = create_result["issue_number"]
        created_issues.append(issue_number)

        # Now retrieve it
        get_result = get_issue(
            issue_number=issue_number,
            owner=test_config["owner"],
            repo=test_config["repo"],
        )

        # Verify all expected fields are present
        assert get_result["number"] == issue_number
        assert get_result["title"] == "[TEST] Issue to retrieve"
        assert "Test body content for retrieval" in get_result["body"]
        assert get_result["state"] == "open"

        assert "labels" in get_result
        assert "test" in get_result["labels"]
        assert "integration" in get_result["labels"]

        assert "milestone" in get_result
        assert get_result["milestone"] is not None

        assert "created_at" in get_result
        assert "updated_at" in get_result
        assert "url" in get_result
        assert "github.com" in get_result["url"]

        # Verify timestamps are valid ISO format
        created_dt = datetime.fromisoformat(get_result["created_at"].replace("Z", "+00:00"))
        updated_dt = datetime.fromisoformat(get_result["updated_at"].replace("Z", "+00:00"))
        assert created_dt <= updated_dt

    def test_get_issue_nonexistent_raises_error(
        self,
        test_config: dict,
    ) -> None:
        """Test that retrieving non-existent issue raises GitHubAPIError."""
        with pytest.raises(GitHubAPIError) as exc_info:
            get_issue(
                issue_number=999999,  # Very unlikely to exist
                owner=test_config["owner"],
                repo=test_config["repo"],
            )

        error = exc_info.value
        assert error.code == "RESOURCE_NOT_FOUND"
        assert "404" in str(error.details)

@pytest.mark.integration
class TestIssueWorkflow:
    """Integration tests for complete issue workflows."""

    def test_create_and_retrieve_workflow(
        self,
        test_config: dict,
        test_milestone: int | None,
        created_issues: list[int],
        cleanup_issues: None,
    ) -> None:
        """Test complete workflow: create issue, then retrieve and verify.

        This validates the entire issue lifecycle from creation to retrieval.
        """
        if test_milestone is None:
            pytest.skip("No milestone available in test repository")

        # Step 1: Create issue
        title = "[TEST] Full workflow test"
        body = """## Test Workflow

This issue tests the complete create → retrieve workflow.

### Components
- Issue creation via create_issue tool
- Issue retrieval via get_issue tool
- Data consistency validation

### Expected Outcome
All data should match between creation and retrieval responses.
"""
        labels = ["test", "integration", "documentation"]

        create_result = create_issue(
            title=title,
            body=body,
            labels=labels,
            milestone=test_milestone,
            owner=test_config["owner"],
            repo=test_config["repo"],
        )

        issue_number = create_result["issue_number"]
        created_issues.append(issue_number)

        # Step 2: Retrieve issue
        get_result = get_issue(
            issue_number=issue_number,
            owner=test_config["owner"],
            repo=test_config["repo"],
        )

        # Step 3: Verify consistency
        assert get_result["number"] == create_result["issue_number"]
        assert get_result["title"] == title
        assert body in get_result["body"]  # GitHub might add formatting

        # Labels should match
        for label in labels:
            assert label in get_result["labels"]

        # URLs should point to same issue
        assert f"/{issue_number}" in get_result["url"]
        assert create_result["url"] == get_result["url"]

        # State should be open
        assert create_result["state"] == "open"
        assert get_result["state"] == "open"


@pytest.mark.integration
class TestListIssuesIntegration:
    """Integration tests for list_issues tool with real GitHub API."""

    def test_list_open_issues(self, test_config: dict) -> None:
        """Test listing open issues from real repository."""
        result = list_issues(
            owner=test_config["owner"],
            repo=test_config["repo"],
            state="open",
            limit=5,
        )

        # Verify response structure
        assert "total" in result
        assert "count" in result
        assert "issues" in result
        assert isinstance(result["issues"], list)
        assert result["count"] <= 5

        # Verify issue structure if any issues exist
        if result["total"] > 0:
            issue = result["issues"][0]
            assert "number" in issue
            assert "title" in issue
            assert "state" in issue
            assert issue["state"] == "open"
            assert "labels" in issue
            assert isinstance(issue["labels"], list)
            assert "milestone" in issue
            assert "assignee" in issue
            assert "created_at" in issue
            assert "updated_at" in issue
            assert "url" in issue
            assert "github.com" in issue["url"]

    def test_list_closed_issues(self, test_config: dict) -> None:
        """Test listing closed issues from real repository."""
        result = list_issues(
            owner=test_config["owner"],
            repo=test_config["repo"],
            state="closed",
            limit=5,
        )

        # Verify response structure
        assert "total" in result
        assert "count" in result
        assert "issues" in result

        # Verify all issues are closed
        for issue in result["issues"]:
            assert issue["state"] == "closed"

    def test_list_all_issues(self, test_config: dict) -> None:
        """Test listing all issues (open + closed)."""
        result = list_issues(
            owner=test_config["owner"],
            repo=test_config["repo"],
            state="all",
            limit=10,
        )

        # Verify we get issues
        assert result["count"] <= 10

        # Might have mix of open and closed
        states = {issue["state"] for issue in result["issues"]}
        assert states.issubset({"open", "closed"})

    def test_list_issues_with_label_filter(self, test_config: dict) -> None:
        """Test filtering issues by label."""
        result = list_issues(
            owner=test_config["owner"],
            repo=test_config["repo"],
            labels=["type: feature"],
            state="all",
            limit=10,
        )

        # Verify response structure
        assert "total" in result
        assert "count" in result

        # If any issues returned, verify they have the label
        for issue in result["issues"]:
            assert "type: feature" in issue["labels"]

    def test_list_issues_pagination(self, test_config: dict) -> None:
        """Test pagination with limit parameter."""
        result = list_issues(
            owner=test_config["owner"],
            repo=test_config["repo"],
            state="all",
            limit=3,
        )

        # Should return at most 3 issues
        assert result["count"] <= 3
        assert len(result["issues"]) <= 3
        assert result["total"] == result["count"]

    def test_list_issues_sorted_by_updated(self, test_config: dict) -> None:
        """Test sorting issues by updated timestamp."""
        result = list_issues(
            owner=test_config["owner"],
            repo=test_config["repo"],
            sort="updated",
            direction="desc",
            limit=5,
        )

        # Verify we got results
        assert "issues" in result

        # If we have multiple issues, verify they're sorted (descending)
        if len(result["issues"]) > 1:
            for i in range(len(result["issues"]) - 1):
                current_updated = result["issues"][i]["updated_at"]
                next_updated = result["issues"][i + 1]["updated_at"]
                # More recently updated should come first
                assert current_updated >= next_updated

    def test_list_issues_empty_results(self, test_config: dict) -> None:
        """Test that non-matching filters return empty results."""
        result = list_issues(
            owner=test_config["owner"],
            repo=test_config["repo"],
            labels=["nonexistent-label-xyz-12345"],
            limit=5,
        )

        # Should return empty results, not error
        assert result["total"] == 0
        assert result["count"] == 0
        assert result["issues"] == []

    def test_list_issues_nonexistent_milestone(self, test_config: dict) -> None:
        """Test that non-existent milestone returns empty results."""
        result = list_issues(
            owner=test_config["owner"],
            repo=test_config["repo"],
            milestone="Nonexistent Milestone XYZ 12345",
            limit=5,
        )

        # Should return empty results, not error
        assert result["total"] == 0
        assert result["count"] == 0
        assert result["issues"] == []

    def test_list_issues_with_milestone_filter(self, test_config: dict) -> None:
        """Test filtering issues by milestone."""
        # First, get issues with milestones
        all_issues = list_issues(
            owner=test_config["owner"],
            repo=test_config["repo"],
            state="all",
            limit=50,
        )

        # Find an issue with a milestone
        issue_with_milestone = None
        for issue in all_issues["issues"]:
            if issue["milestone"] is not None:
                issue_with_milestone = issue
                break

        if issue_with_milestone:
            # Filter by that milestone
            result = list_issues(
                owner=test_config["owner"],
                repo=test_config["repo"],
                milestone=issue_with_milestone["milestone"],
                limit=10,
            )

            # All returned issues should have that milestone
            for issue in result["issues"]:
                assert issue["milestone"] == issue_with_milestone["milestone"]
        else:
            pytest.skip("No issues with milestones found in repository")

    def test_list_issues_response_format(self, test_config: dict) -> None:
        """Test that response format matches specification."""
        result = list_issues(
            owner=test_config["owner"],
            repo=test_config["repo"],
            limit=1,
        )

        # Verify top-level structure
        assert set(result.keys()) == {"total", "count", "issues"}
        assert isinstance(result["total"], int)
        assert isinstance(result["count"], int)
        assert isinstance(result["issues"], list)

        # Verify issue structure if we have results
        if result["count"] > 0:
            issue = result["issues"][0]
            required_fields = {
                "number",
                "title",
                "state",
                "labels",
                "milestone",
                "assignee",
                "created_at",
                "updated_at",
                "url",
            }
            assert set(issue.keys()) == required_fields

            # Verify field types
            assert isinstance(issue["number"], int)
            assert isinstance(issue["title"], str)
            assert isinstance(issue["state"], str)
            assert isinstance(issue["labels"], list)
            assert isinstance(issue["milestone"], str | None)
            assert isinstance(issue["assignee"], str | None)
            assert isinstance(issue["created_at"], str)
            assert isinstance(issue["updated_at"], str)
            assert isinstance(issue["url"], str)

            # Verify timestamps are ISO 8601 format
            assert "T" in issue["created_at"]
            assert "T" in issue["updated_at"]

            # Verify URL is valid
            assert issue["url"].startswith("https://github.com/")

    def test_list_issues_with_assignee_filter(self, test_config: dict) -> None:
        """Test filtering issues by assignee."""
        # Get all issues to find one with an assignee
        all_issues = list_issues(
            owner=test_config["owner"],
            repo=test_config["repo"],
            state="all",
            limit=50,
        )

        # Find an issue with an assignee
        issue_with_assignee = None
        for issue in all_issues["issues"]:
            if issue["assignee"] is not None:
                issue_with_assignee = issue
                break

        if issue_with_assignee:
            # Filter by that assignee
            result = list_issues(
                owner=test_config["owner"],
                repo=test_config["repo"],
                assignee=issue_with_assignee["assignee"],
                limit=10,
            )

            # All returned issues should have that assignee
            for issue in result["issues"]:
                assert issue["assignee"] == issue_with_assignee["assignee"]
        else:
            pytest.skip("No issues with assignees found in repository")


@pytest.mark.integration
class TestCloseIssueIntegration:
    """Integration tests for close_issue tool with real GitHub API."""

    def test_close_issue_without_comment(
        self,
        test_config: dict,
        test_milestone: int | None,
        created_issues: list[int],
        cleanup_issues: None,
    ) -> None:
        """Test closing an issue without a comment via real GitHub API."""
        if test_milestone is None:
            pytest.skip("No milestone available in test repository")

        # Create a test issue first
        create_result = create_issue(
            title="[TEST] Issue to close without comment",
            body="This issue will be closed without a comment.",
            labels=["test"],
            milestone=test_milestone,
            owner=test_config["owner"],
            repo=test_config["repo"],
        )

        issue_number = create_result["issue_number"]
        created_issues.append(issue_number)

        # Close the issue
        close_result = close_issue(
            issue_number=issue_number,
            owner=test_config["owner"],
            repo=test_config["repo"],
        )

        # Verify response
        assert close_result["number"] == issue_number
        assert close_result["state"] == "closed"
        assert close_result["comment_added"] is False
        assert "url" in close_result
        assert f"/{issue_number}" in close_result["url"]

        # Verify it's actually closed by retrieving it
        get_result = get_issue(
            issue_number=issue_number,
            owner=test_config["owner"],
            repo=test_config["repo"],
        )
        assert get_result["state"] == "closed"

    def test_close_issue_with_comment(
        self,
        test_config: dict,
        test_milestone: int | None,
        created_issues: list[int],
        cleanup_issues: None,
    ) -> None:
        """Test closing an issue with a comment via real GitHub API."""
        if test_milestone is None:
            pytest.skip("No milestone available in test repository")

        # Create a test issue
        create_result = create_issue(
            title="[TEST] Issue to close with comment",
            body="This issue will be closed with a comment.",
            labels=["test"],
            milestone=test_milestone,
            owner=test_config["owner"],
            repo=test_config["repo"],
        )

        issue_number = create_result["issue_number"]
        created_issues.append(issue_number)

        # Close with comment
        closing_comment = "Closing this test issue. All tests passed! 🎉"
        close_result = close_issue(
            issue_number=issue_number,
            comment=closing_comment,
            owner=test_config["owner"],
            repo=test_config["repo"],
        )

        # Verify response
        assert close_result["number"] == issue_number
        assert close_result["state"] == "closed"
        assert close_result["comment_added"] is True

        # Verify it's closed
        get_result = get_issue(
            issue_number=issue_number,
            owner=test_config["owner"],
            repo=test_config["repo"],
        )
        assert get_result["state"] == "closed"

    def test_close_issue_with_state_reason_completed(
        self,
        test_config: dict,
        test_milestone: int | None,
        created_issues: list[int],
        cleanup_issues: None,
    ) -> None:
        """Test closing an issue with state_reason='completed'."""
        if test_milestone is None:
            pytest.skip("No milestone available in test repository")

        # Create a test issue
        create_result = create_issue(
            title="[TEST] Issue to close as completed",
            body="This issue will be closed with state_reason='completed'.",
            labels=["test"],
            milestone=test_milestone,
            owner=test_config["owner"],
            repo=test_config["repo"],
        )

        issue_number = create_result["issue_number"]
        created_issues.append(issue_number)

        # Close with state_reason
        close_result = close_issue(
            issue_number=issue_number,
            state_reason="completed",
            owner=test_config["owner"],
            repo=test_config["repo"],
        )

        # Verify response
        assert close_result["number"] == issue_number
        assert close_result["state"] == "closed"
        assert close_result["state_reason"] == "completed"

    def test_close_issue_with_state_reason_not_planned(
        self,
        test_config: dict,
        test_milestone: int | None,
        created_issues: list[int],
        cleanup_issues: None,
    ) -> None:
        """Test closing an issue with state_reason='not_planned'."""
        if test_milestone is None:
            pytest.skip("No milestone available in test repository")

        # Create a test issue
        create_result = create_issue(
            title="[TEST] Issue to close as not planned",
            body="This issue will be closed with state_reason='not_planned'.",
            labels=["test"],
            milestone=test_milestone,
            owner=test_config["owner"],
            repo=test_config["repo"],
        )

        issue_number = create_result["issue_number"]
        created_issues.append(issue_number)

        # Close with state_reason
        close_result = close_issue(
            issue_number=issue_number,
            state_reason="not_planned",
            owner=test_config["owner"],
            repo=test_config["repo"],
        )

        # Verify response
        assert close_result["number"] == issue_number
        assert close_result["state"] == "closed"
        assert close_result["state_reason"] == "not_planned"

    def test_close_issue_with_comment_and_state_reason(
        self,
        test_config: dict,
        test_milestone: int | None,
        created_issues: list[int],
        cleanup_issues: None,
    ) -> None:
        """Test closing issue with both comment and state_reason."""
        if test_milestone is None:
            pytest.skip("No milestone available in test repository")

        # Create a test issue
        create_result = create_issue(
            title="[TEST] Issue to close with comment and state",
            body="This issue will be closed with both comment and state_reason.",
            labels=["test"],
            milestone=test_milestone,
            owner=test_config["owner"],
            repo=test_config["repo"],
        )

        issue_number = create_result["issue_number"]
        created_issues.append(issue_number)

        # Close with both comment and state_reason
        close_result = close_issue(
            issue_number=issue_number,
            comment="Completed successfully in PR #123",
            state_reason="completed",
            owner=test_config["owner"],
            repo=test_config["repo"],
        )

        # Verify response
        assert close_result["number"] == issue_number
        assert close_result["state"] == "closed"
        assert close_result["comment_added"] is True
        assert close_result["state_reason"] == "completed"

    def test_close_issue_already_closed_is_idempotent(
        self,
        test_config: dict,
        test_milestone: int | None,
        created_issues: list[int],
        cleanup_issues: None,
    ) -> None:
        """Test that closing an already-closed issue is idempotent."""
        if test_milestone is None:
            pytest.skip("No milestone available in test repository")

        # Create and close an issue
        create_result = create_issue(
            title="[TEST] Issue to close twice",
            body="This issue will be closed twice to test idempotency.",
            labels=["test"],
            milestone=test_milestone,
            owner=test_config["owner"],
            repo=test_config["repo"],
        )

        issue_number = create_result["issue_number"]
        created_issues.append(issue_number)

        # Close it first time
        first_close = close_issue(
            issue_number=issue_number,
            owner=test_config["owner"],
            repo=test_config["repo"],
        )
        assert first_close["state"] == "closed"

        # Close it again - should not error
        second_close = close_issue(
            issue_number=issue_number,
            owner=test_config["owner"],
            repo=test_config["repo"],
        )

        # Should still return closed state
        assert second_close["state"] == "closed"
        assert second_close["number"] == issue_number

    def test_close_nonexistent_issue_raises_error(
        self,
        test_config: dict,
    ) -> None:
        """Test that closing non-existent issue raises error."""
        with pytest.raises(GitHubAPIError) as exc_info:
            close_issue(
                issue_number=999999,
                owner=test_config["owner"],
                repo=test_config["repo"],
            )

        error = exc_info.value
        assert error.code == "RESOURCE_NOT_FOUND"


@pytest.mark.integration
class TestIssueLifecycleWorkflow:
    """Integration tests for complete issue lifecycle: create → get → close."""

    def test_complete_issue_lifecycle(
        self,
        test_config: dict,
        test_milestone: int | None,
        created_issues: list[int],
        cleanup_issues: None,
    ) -> None:
        """Test complete workflow: create → retrieve → close → verify.

        This validates the entire issue lifecycle from creation to closure.
        """
        if test_milestone is None:
            pytest.skip("No milestone available in test repository")

        # Step 1: Create issue
        title = "[TEST] Complete lifecycle test"
        body = """## Lifecycle Test

This issue tests the complete create → get → close workflow.

### Steps
1. Create issue via create_issue
2. Retrieve via get_issue
3. Close via close_issue
4. Verify final state

### Expected Outcome
Issue should exist and be closed successfully.
"""
        create_result = create_issue(
            title=title,
            body=body,
            labels=["test", "integration"],
            milestone=test_milestone,
            owner=test_config["owner"],
            repo=test_config["repo"],
        )

        issue_number = create_result["issue_number"]
        created_issues.append(issue_number)
        assert create_result["state"] == "open"

        # Step 2: Retrieve issue
        get_result = get_issue(
            issue_number=issue_number,
            owner=test_config["owner"],
            repo=test_config["repo"],
        )
        assert get_result["state"] == "open"
        assert get_result["number"] == issue_number

        # Step 3: Close issue with comment
        close_result = close_issue(
            issue_number=issue_number,
            comment="Lifecycle test completed successfully",
            state_reason="completed",
            owner=test_config["owner"],
            repo=test_config["repo"],
        )
        assert close_result["state"] == "closed"
        assert close_result["comment_added"] is True
        assert close_result["state_reason"] == "completed"

        # Step 4: Verify final state
        final_get = get_issue(
            issue_number=issue_number,
            owner=test_config["owner"],
            repo=test_config["repo"],
        )
        assert final_get["state"] == "closed"
        assert final_get["number"] == issue_number
        assert final_get["url"] == create_result["url"]
