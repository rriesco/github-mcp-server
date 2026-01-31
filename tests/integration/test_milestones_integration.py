"""Integration tests for GitHub milestone operations.

These tests make real API calls to GitHub and require a valid GITHUB_TOKEN.
Run with: pytest tests/integration/test_milestones_integration.py -m integration
"""

from datetime import datetime

import pytest
from github_mcp_server.tools.milestones import create_milestone, list_milestones


@pytest.mark.integration
class TestListMilestonesIntegration:
    """Integration tests for list_milestones tool with real GitHub API."""

    def test_list_open_milestones(self, test_config: dict) -> None:
        """Test listing open milestones from real repository."""
        result = list_milestones(
            owner=test_config["owner"],
            repo=test_config["repo"],
            state="open",
        )

        # Verify response structure
        assert "total" in result
        assert "milestones" in result
        assert isinstance(result["milestones"], list)

        # Verify milestone structure if any milestones exist
        if result["total"] > 0:
            milestone = result["milestones"][0]
            assert "number" in milestone
            assert "title" in milestone
            assert "state" in milestone
            assert milestone["state"] == "open"
            assert "open_issues" in milestone
            assert "closed_issues" in milestone
            assert isinstance(milestone["open_issues"], int)
            assert isinstance(milestone["closed_issues"], int)
            assert "due_on" in milestone
            assert "url" in milestone
            assert "github.com" in milestone["url"]

    def test_list_closed_milestones(self, test_config: dict) -> None:
        """Test listing closed milestones from real repository."""
        result = list_milestones(
            owner=test_config["owner"],
            repo=test_config["repo"],
            state="closed",
        )

        # Verify response structure
        assert "total" in result
        assert "milestones" in result

        # Verify all milestones are closed
        for milestone in result["milestones"]:
            assert milestone["state"] == "closed"

    def test_list_all_milestones(self, test_config: dict) -> None:
        """Test listing all milestones (open + closed)."""
        result = list_milestones(
            owner=test_config["owner"],
            repo=test_config["repo"],
            state="all",
        )

        # Verify we get milestones
        assert "total" in result
        assert "milestones" in result

        # Might have mix of open and closed
        states = {milestone["state"] for milestone in result["milestones"]}
        assert states.issubset({"open", "closed"})

    def test_list_milestones_sorted_by_due_on(self, test_config: dict) -> None:
        """Test sorting milestones by due_on date (ascending)."""
        result = list_milestones(
            owner=test_config["owner"],
            repo=test_config["repo"],
            sort="due_on",
            direction="asc",
        )

        # Verify we got results
        assert "milestones" in result

        # If we have multiple milestones with due dates, verify they're sorted
        milestones_with_due = [m for m in result["milestones"] if m["due_on"]]
        if len(milestones_with_due) > 1:
            for i in range(len(milestones_with_due) - 1):
                current_due = milestones_with_due[i]["due_on"]
                next_due = milestones_with_due[i + 1]["due_on"]
                # Earlier due dates should come first (ascending)
                assert current_due <= next_due

    def test_list_milestones_sorted_by_completeness(self, test_config: dict) -> None:
        """Test sorting milestones by completeness."""
        result = list_milestones(
            owner=test_config["owner"],
            repo=test_config["repo"],
            sort="completeness",
            direction="desc",
        )

        # Verify we got results
        assert "milestones" in result
        assert isinstance(result["milestones"], list)

    def test_list_milestones_empty_repository(self, test_config: dict) -> None:
        """Test listing milestones when repository has no milestones.

        Note: This test may not fail if the repository has milestones.
        It's here to document the expected behavior when no milestones exist.
        """
        # Create a filter that should return no results
        result = list_milestones(
            owner=test_config["owner"],
            repo=test_config["repo"],
            state="closed",
        )

        # Should return empty results, not error (if no closed milestones)
        assert "total" in result
        assert "milestones" in result
        assert isinstance(result["milestones"], list)

    def test_list_milestones_response_format(self, test_config: dict) -> None:
        """Test that response format matches specification."""
        result = list_milestones(
            owner=test_config["owner"],
            repo=test_config["repo"],
        )

        # Verify top-level structure
        assert set(result.keys()) == {"total", "milestones"}
        assert isinstance(result["total"], int)
        assert isinstance(result["milestones"], list)

        # Verify milestone structure if we have results
        if result["total"] > 0:
            milestone = result["milestones"][0]
            required_fields = {
                "number",
                "title",
                "state",
                "open_issues",
                "closed_issues",
                "due_on",
                "url",
            }
            assert set(milestone.keys()) == required_fields

            # Verify field types
            assert isinstance(milestone["number"], int)
            assert isinstance(milestone["title"], str)
            assert isinstance(milestone["state"], str)
            assert isinstance(milestone["open_issues"], int)
            assert isinstance(milestone["closed_issues"], int)
            assert isinstance(milestone["due_on"], (str, type(None)))
            assert isinstance(milestone["url"], str)

            # Verify due_on is ISO 8601 format if present
            if milestone["due_on"]:
                assert "T" in milestone["due_on"]
                # Should be parseable as datetime
                datetime.fromisoformat(milestone["due_on"].replace("Z", "+00:00"))

            # Verify URL is valid
            assert milestone["url"].startswith("https://github.com/")


@pytest.mark.integration
class TestCreateMilestoneIntegration:
    """Integration tests for create_milestone tool with real GitHub API.

    WARNING: These tests create real milestones on GitHub.
    They should be run carefully and milestones should be cleaned up manually if needed.
    """

    def test_create_milestone_basic(
        self,
        test_config: dict,
        created_milestones: list[int],
        cleanup_milestones: None,
    ) -> None:
        """Test creating a milestone with title and description only.

        This test:
        1. Creates a real milestone on GitHub
        2. Verifies all returned fields are correct
        3. Cleanup fixture can close the milestone after test (manual)
        """
        # Create milestone using the MCP tool
        result = create_milestone(
            title="[TEST] Integration test milestone - safe to close",
            description="This is a test milestone created by the integration test suite.",
            owner=test_config["owner"],
            repo=test_config["repo"],
        )

        # Track for potential cleanup
        created_milestones.append(result["number"])

        # Verify response structure
        assert "number" in result
        assert isinstance(result["number"], int)
        assert result["number"] > 0

        assert "title" in result
        assert result["title"] == "[TEST] Integration test milestone - safe to close"

        assert "description" in result
        assert "test milestone" in result["description"].lower()

        assert "state" in result
        assert result["state"] == "open"

        assert "due_on" in result
        assert result["due_on"] is None  # No due date set

        assert "url" in result
        assert "github.com" in result["url"]
        assert test_config["repo"] in result["url"]

    def test_create_milestone_with_due_date(
        self,
        test_config: dict,
        created_milestones: list[int],
        cleanup_milestones: None,
    ) -> None:
        """Test creating a milestone with due date."""
        due_date = "2026-12-31T23:59:59Z"

        result = create_milestone(
            title="[TEST] Milestone with due date",
            description="Test milestone with due date set",
            due_date=due_date,
            owner=test_config["owner"],
            repo=test_config["repo"],
        )

        created_milestones.append(result["number"])

        assert result["due_on"] is not None
        # Verify it's a valid ISO timestamp
        parsed_due = datetime.fromisoformat(result["due_on"].replace("Z", "+00:00"))
        assert parsed_due.year == 2026
        assert parsed_due.month == 12
        assert parsed_due.day == 31

    def test_create_milestone_invalid_due_date_format(
        self,
        test_config: dict,
    ) -> None:
        """Test that invalid due date format raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            create_milestone(
                title="[TEST] Invalid due date",
                description="Should fail",
                due_date="invalid-date-format",
                owner=test_config["owner"],
                repo=test_config["repo"],
            )

        error = exc_info.value
        assert "Invalid ISO 8601" in str(error)

    def test_create_milestone_duplicate_title(
        self,
        test_config: dict,
        created_milestones: list[int],
        cleanup_milestones: None,
    ) -> None:
        """Test that creating duplicate milestone raises error.

        Note: GitHub allows duplicate milestone titles, so this test
        documents actual behavior rather than testing rejection.
        """
        title = "[TEST] Duplicate milestone test"

        # Create first milestone
        result1 = create_milestone(
            title=title,
            description="First milestone",
            owner=test_config["owner"],
            repo=test_config["repo"],
        )
        created_milestones.append(result1["number"])

        # Try to create second milestone with same title
        # GitHub actually allows this, so we verify it succeeds
        result2 = create_milestone(
            title=title,
            description="Second milestone with same title",
            owner=test_config["owner"],
            repo=test_config["repo"],
        )
        created_milestones.append(result2["number"])

        # Both should succeed with different numbers
        assert result1["number"] != result2["number"]
        assert result1["title"] == result2["title"]


@pytest.mark.integration
class TestMilestoneWorkflow:
    """Integration tests for complete milestone workflows."""

    def test_create_and_list_workflow(
        self,
        test_config: dict,
        created_milestones: list[int],
        cleanup_milestones: None,
    ) -> None:
        """Test complete workflow: create milestone, then list and verify.

        This validates the entire milestone lifecycle from creation to listing.
        """
        # Step 1: Create milestone
        title = "[TEST] Full workflow test milestone"
        description = "This milestone tests the complete create → list workflow."

        create_result = create_milestone(
            title=title,
            description=description,
            owner=test_config["owner"],
            repo=test_config["repo"],
        )

        milestone_number = create_result["number"]
        created_milestones.append(milestone_number)

        # Step 2: List milestones
        list_result = list_milestones(
            owner=test_config["owner"],
            repo=test_config["repo"],
            state="open",
        )

        # Step 3: Verify our milestone is in the list
        found = False
        for milestone in list_result["milestones"]:
            if milestone["number"] == milestone_number:
                found = True
                assert milestone["title"] == title
                assert milestone["state"] == "open"
                break

        assert found, f"Created milestone #{milestone_number} not found in list"

    def test_list_milestones_for_issue_creation(self, test_config: dict) -> None:
        """Test listing milestones to get milestone number for issue creation.

        This simulates the real use case: user needs to find milestone number
        to use when creating issues.
        """
        # List all milestones
        result = list_milestones(
            owner=test_config["owner"],
            repo=test_config["repo"],
            state="all",
        )

        # Should have at least one milestone (Phase 0 milestone #7 should exist)
        assert result["total"] > 0

        # Verify we can extract milestone numbers
        milestone_numbers = [m["number"] for m in result["milestones"]]
        assert all(isinstance(num, int) for num in milestone_numbers)
        assert all(num > 0 for num in milestone_numbers)

        # Verify milestone titles are available for selection
        milestone_titles = [m["title"] for m in result["milestones"]]
        assert all(isinstance(title, str) for title in milestone_titles)
        assert all(len(title) > 0 for title in milestone_titles)
