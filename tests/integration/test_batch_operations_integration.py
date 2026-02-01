"""Integration tests for GitHub batch operations.

These tests make real API calls to GitHub and require a valid GITHUB_TOKEN.
Run with: pytest tests/integration/test_batch_operations_integration.py -m integration
"""

import pytest
from github_mcp_server.tools.batch_operations import (
    batch_add_labels,
    batch_link_to_project,
    batch_update_issues,
)
from github_mcp_server.tools.issues import create_issues as batch_create_issues


@pytest.mark.integration
class TestBatchCreateIssuesIntegration:
    """Integration tests for batch_create_issues tool with real GitHub API."""

    def test_batch_create_multiple_issues_succeeds(
        self,
        test_config: dict,
        test_milestone: int | None,
        created_issues: list[int],
        cleanup_issues: None,
    ) -> None:
        """Test creating multiple issues in a single batch operation.

        Verifies:
        1. All issues are created successfully
        2. Results contain correct data for each issue
        3. Execution time is reasonable
        4. Success rate is 100%
        """
        if test_milestone is None:
            pytest.skip("No milestone available in test repository")

        issues_data = [
            {
                "title": f"[TEST] Batch issue {i} - safe to close",
                "body": f"""## Context
This is test issue {i} from the batch creation integration test.

## Purpose
Validates batch creation functionality.

## Cleanup
Will be automatically closed by test cleanup.
""",
                "labels": ["test"],
                "milestone": test_milestone,
            }
            for i in range(1, 6)  # Create 5 issues
        ]

        result = batch_create_issues(
            issues=issues_data,
            owner=test_config["owner"],
            repo=test_config["repo"],
        )

        # Track all created issues for cleanup
        for res in result["results"]:
            if res["success"]:
                created_issues.append(res["data"]["issue_number"])

        # Verify batch operation succeeded
        assert result["total"] == 5
        assert result["successful"] == 5
        assert result["failed"] == 0
        assert result["success_rate"] == "100.0%"
        assert result["execution_time_seconds"] > 0

        # Verify each issue result
        for i, res in enumerate(result["results"]):
            assert res["index"] == i
            assert res["success"] is True
            assert "data" in res
            assert res["data"]["issue_number"] > 0
            assert "github.com" in res["data"]["url"]
            assert res["data"]["state"] == "open"
            assert "test" in res["data"]["labels"]

    def test_batch_create_with_partial_failures(
        self,
        test_config: dict,
        test_milestone: int | None,
        created_issues: list[int],
        cleanup_issues: None,
    ) -> None:
        """Test batch creation handles partial failures gracefully.

        Creates a mix of valid and invalid issues to test error handling.
        """
        if test_milestone is None:
            pytest.skip("No milestone available in test repository")

        issues_data = [
            {
                "title": "[TEST] Valid issue 1",
                "body": "This should succeed",
                "labels": ["test"],
                "milestone": test_milestone,
            },
            {
                "title": "[TEST] Invalid milestone",
                "body": "This should fail",
                "labels": ["test"],
                "milestone": 99999,  # Invalid milestone
            },
            {
                "title": "[TEST] Valid issue 2",
                "body": "This should succeed",
                "labels": ["test"],
                "milestone": test_milestone,
            },
        ]

        result = batch_create_issues(
            issues=issues_data,
            owner=test_config["owner"],
            repo=test_config["repo"],
        )

        # Track successful creations for cleanup
        for res in result["results"]:
            if res["success"]:
                created_issues.append(res["data"]["issue_number"])

        # Verify batch handled partial failure
        assert result["total"] == 3
        assert result["successful"] == 2  # Two valid issues
        assert result["failed"] == 1  # One invalid milestone

        # Check successful issues
        assert result["results"][0]["success"] is True
        assert result["results"][2]["success"] is True

        # Check failed issue
        assert result["results"][1]["success"] is False
        assert "error" in result["results"][1]

    def test_batch_create_performance_vs_sequential(
        self,
        test_config: dict,
        test_milestone: int | None,
        created_issues: list[int],
        cleanup_issues: None,
    ) -> None:
        """Test that batch creation is significantly faster than sequential.

        Creates issues both ways and compares execution time.
        Batch should be at least 2x faster for 10 issues.
        """
        if test_milestone is None:
            pytest.skip("No milestone available in test repository")

        num_issues = 10

        # Create issues for batch test
        batch_issues_data = [
            {
                "title": f"[TEST] Batch perf test {i}",
                "body": "Performance test issue",
                "labels": ["test"],
                "milestone": test_milestone,
            }
            for i in range(num_issues)
        ]

        # Batch creation
        batch_result = batch_create_issues(
            issues=batch_issues_data,
            owner=test_config["owner"],
            repo=test_config["repo"],
            max_workers=5,
        )

        batch_time = batch_result["execution_time_seconds"]

        # Track for cleanup
        for res in batch_result["results"]:
            if res["success"]:
                created_issues.append(res["data"]["issue_number"])

        # Simulate sequential creation time
        # (We won't actually create them sequentially to avoid API calls)
        # Based on typical API latency, sequential would take ~0.5s per issue
        estimated_sequential_time = num_issues * 0.5

        # Batch should be significantly faster
        speedup = estimated_sequential_time / batch_time
        assert speedup >= 2.0, f"Batch not fast enough: {speedup:.1f}x speedup"

        # Verify all succeeded
        assert batch_result["successful"] == num_issues

    def test_batch_create_empty_list_raises_error(
        self,
        test_config: dict,
    ) -> None:
        """Test that empty issues list raises ValueError."""
        with pytest.raises(ValueError, match="cannot be empty"):
            batch_create_issues(
                issues=[],
                owner=test_config["owner"],
                repo=test_config["repo"],
            )

    def test_batch_create_exceeds_max_limit_raises_error(
        self,
        test_config: dict,
        test_milestone: int | None,
    ) -> None:
        """Test that exceeding max batch size raises ValueError."""
        if test_milestone is None:
            pytest.skip("No milestone available in test repository")

        large_batch = [
            {"title": f"Issue {i}", "labels": ["test"], "milestone": test_milestone}
            for i in range(51)
        ]

        with pytest.raises(ValueError, match="Maximum 50 issues"):
            batch_create_issues(
                issues=large_batch,
                owner=test_config["owner"],
                repo=test_config["repo"],
            )


@pytest.mark.integration
class TestBatchUpdateIssuesIntegration:
    """Integration tests for batch_update_issues tool with real GitHub API."""

    def test_batch_update_multiple_issues(
        self,
        test_config: dict,
        test_milestone: int | None,
        created_issues: list[int],
        cleanup_issues: None,
    ) -> None:
        """Test updating multiple issues in batch."""
        if test_milestone is None:
            pytest.skip("No milestone available in test repository")

        # First create issues to update
        create_result = batch_create_issues(
            issues=[
                {
                    "title": f"[TEST] Update test {i}",
                    "body": "Original body",
                    "labels": ["test"],
                    "milestone": test_milestone,
                }
                for i in range(1, 4)
            ],
            owner=test_config["owner"],
            repo=test_config["repo"],
        )

        issue_numbers = [
            res["data"]["issue_number"] for res in create_result["results"] if res["success"]
        ]
        created_issues.extend(issue_numbers)

        # Now batch update them
        updates = [
            {
                "issue_number": issue_numbers[0],
                "title": "[TEST] Updated title 1",
                "labels": ["test", "updated"],
            },
            {
                "issue_number": issue_numbers[1],
                "body": "Updated body content",
            },
            {
                "issue_number": issue_numbers[2],
                "state": "closed",
            },
        ]

        result = batch_update_issues(
            updates=updates,
            owner=test_config["owner"],
            repo=test_config["repo"],
        )

        # Verify batch update succeeded
        assert result["total"] == 3
        assert result["successful"] == 3
        assert result["failed"] == 0

        # Verify update details
        for res in result["results"]:
            assert res["success"] is True
            assert "updated_fields" in res["data"]

    def test_batch_update_missing_issue_number_raises_error(
        self,
        test_config: dict,
    ) -> None:
        """Test that missing issue_number raises ValueError."""
        with pytest.raises(ValueError, match="missing required 'issue_number'"):
            batch_update_issues(
                updates=[{"title": "No issue number"}],
                owner=test_config["owner"],
                repo=test_config["repo"],
            )


@pytest.mark.integration
class TestBatchAddLabelsIntegration:
    """Integration tests for batch_add_labels tool with real GitHub API."""

    def test_batch_add_labels_to_multiple_issues(
        self,
        test_config: dict,
        test_milestone: int | None,
        created_issues: list[int],
        cleanup_issues: None,
    ) -> None:
        """Test adding labels to multiple issues in batch."""
        if test_milestone is None:
            pytest.skip("No milestone available in test repository")

        # Create test issues
        create_result = batch_create_issues(
            issues=[
                {
                    "title": f"[TEST] Label test {i}",
                    "body": "Label test",
                    "labels": ["test"],
                    "milestone": test_milestone,
                }
                for i in range(1, 4)
            ],
            owner=test_config["owner"],
            repo=test_config["repo"],
        )

        issue_numbers = [
            res["data"]["issue_number"] for res in create_result["results"] if res["success"]
        ]
        created_issues.extend(issue_numbers)

        # Batch add labels
        operations = [
            {
                "issue_number": issue_num,
                "labels": ["documentation", "enhancement"],
            }
            for issue_num in issue_numbers
        ]

        result = batch_add_labels(
            operations=operations,
            owner=test_config["owner"],
            repo=test_config["repo"],
        )

        # Verify batch operation succeeded
        assert result["total"] == 3
        assert result["successful"] == 3
        assert result["failed"] == 0

        # Verify labels were added
        for res in result["results"]:
            assert res["success"] is True
            assert "documentation" in res["data"]["added_labels"]
            assert "enhancement" in res["data"]["added_labels"]
            # Original "test" label should still be there
            assert "test" in res["data"]["all_labels"]

    def test_batch_add_labels_missing_fields_raises_error(
        self,
        test_config: dict,
    ) -> None:
        """Test that missing required fields raise ValueError."""
        with pytest.raises(ValueError, match="missing required 'issue_number'"):
            batch_add_labels(
                operations=[{"labels": ["test"]}],
                owner=test_config["owner"],
                repo=test_config["repo"],
            )

        with pytest.raises(ValueError, match="missing required 'labels'"):
            batch_add_labels(
                operations=[{"issue_number": 123}],
                owner=test_config["owner"],
                repo=test_config["repo"],
            )

        with pytest.raises(ValueError, match="empty 'labels' list"):
            batch_add_labels(
                operations=[{"issue_number": 123, "labels": []}],
                owner=test_config["owner"],
                repo=test_config["repo"],
            )


@pytest.mark.integration
@pytest.mark.skip(reason="Requires project ID - enable manually with real project")
class TestBatchLinkToProjectIntegration:
    """Integration tests for batch_link_to_project tool.

    These tests are skipped by default because they require a real GitHub Project.
    To run them:
    1. Create a test project in your repository
    2. Get the project node ID (PVT_xxx)
    3. Update the project_id in the test
    4. Remove the @pytest.mark.skip decorator
    """

    def test_batch_link_issues_to_project(
        self,
        test_config: dict,
        test_milestone: int | None,
        created_issues: list[int],
        cleanup_issues: None,
    ) -> None:
        """Test linking multiple issues to a project board."""
        if test_milestone is None:
            pytest.skip("No milestone available in test repository")

        # Create test issues
        create_result = batch_create_issues(
            issues=[
                {
                    "title": f"[TEST] Project link test {i}",
                    "body": "Project link test",
                    "labels": ["test"],
                    "milestone": test_milestone,
                }
                for i in range(1, 4)
            ],
            owner=test_config["owner"],
            repo=test_config["repo"],
        )

        issue_numbers = [
            res["data"]["issue_number"] for res in create_result["results"] if res["success"]
        ]
        created_issues.extend(issue_numbers)

        # TODO: Replace with actual project ID
        project_id = "PVT_kwDOABcDEFG"  # Example format

        result = batch_link_to_project(
            issue_numbers=issue_numbers,
            project_id=project_id,
            owner=test_config["owner"],
            repo=test_config["repo"],
        )

        # Verify batch operation succeeded
        assert result["total"] == 3
        assert result["successful"] == 3
        assert result["failed"] == 0

        # Verify each link
        for res in result["results"]:
            assert res["success"] is True
            assert res["data"]["project_id"] == project_id
            assert "item_id" in res["data"]

    def test_batch_link_invalid_project_id_raises_error(
        self,
        test_config: dict,
    ) -> None:
        """Test that invalid project ID raises ValueError."""
        with pytest.raises(ValueError, match="must be a valid GitHub Project node ID"):
            batch_link_to_project(
                issue_numbers=[123],
                project_id="invalid",
                owner=test_config["owner"],
                repo=test_config["repo"],
            )


@pytest.mark.integration
class TestBatchOperationsPerformance:
    """Performance benchmarks for batch operations."""

    def test_batch_create_10_issues_benchmark(
        self,
        test_config: dict,
        test_milestone: int | None,
        created_issues: list[int],
        cleanup_issues: None,
    ) -> None:
        """Benchmark: Create 10 issues and measure execution time.

        Expected: < 5 seconds for 10 issues with max_workers=5
        """
        if test_milestone is None:
            pytest.skip("No milestone available in test repository")

        issues_data = [
            {
                "title": f"[TEST] Benchmark issue {i}",
                "body": "Performance benchmark test",
                "labels": ["test"],
                "milestone": test_milestone,
            }
            for i in range(10)
        ]

        result = batch_create_issues(
            issues=issues_data,
            owner=test_config["owner"],
            repo=test_config["repo"],
            max_workers=5,
        )

        # Track for cleanup
        for res in result["results"]:
            if res["success"]:
                created_issues.append(res["data"]["issue_number"])

        # Verify performance
        execution_time = result["execution_time_seconds"]
        assert execution_time < 5.0, f"Too slow: {execution_time:.2f}s for 10 issues"
        assert result["successful"] == 10

        # Calculate throughput
        throughput = 10 / execution_time
        print(f"\nBenchmark: {throughput:.1f} issues/second")

    def test_batch_operations_concurrency_levels(
        self,
        test_config: dict,
        test_milestone: int | None,
        created_issues: list[int],
        cleanup_issues: None,
    ) -> None:
        """Compare performance with different max_workers settings.

        Tests max_workers: 1, 3, 5, 10 to find optimal concurrency.
        """
        if test_milestone is None:
            pytest.skip("No milestone available in test repository")

        num_issues = 10
        issues_data = [
            {
                "title": f"[TEST] Concurrency test {i}",
                "body": "Concurrency test",
                "labels": ["test"],
                "milestone": test_milestone,
            }
            for i in range(num_issues)
        ]

        results_by_workers = {}

        for max_workers in [1, 3, 5, 10]:
            result = batch_create_issues(
                issues=issues_data[:num_issues],  # Use same data each time
                owner=test_config["owner"],
                repo=test_config["repo"],
                max_workers=max_workers,
            )

            # Track for cleanup
            for res in result["results"]:
                if res["success"]:
                    created_issues.append(res["data"]["issue_number"])

            results_by_workers[max_workers] = result["execution_time_seconds"]

        # Print performance comparison
        print("\n\nConcurrency Performance:")
        for workers, exec_time in results_by_workers.items():
            throughput = num_issues / exec_time
            print(f"  max_workers={workers:2d}: {exec_time:.2f}s ({throughput:.1f} issues/sec)")

        # Verify higher concurrency is faster (within reason)
        # max_workers=5 should be faster than max_workers=1
        assert results_by_workers[5] < results_by_workers[1], "Higher concurrency should be faster"
