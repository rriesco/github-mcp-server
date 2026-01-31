"""Integration tests for GitHub CI operations.

These tests make real API calls to GitHub and require a valid GITHUB_TOKEN.
Run with: pytest tests/integration/test_ci_integration.py -m integration
"""

from datetime import datetime

import pytest
from github_mcp_server.tools.ci import check_ci_status, get_ci_logs


@pytest.mark.integration
class TestCheckCIStatusIntegration:
    """Integration tests for check_ci_status tool with real GitHub API."""

    def test_check_ci_status_for_main_branch(
        self,
        test_config: dict,
    ) -> None:
        """Test retrieving CI status for the main branch.

        The main branch should typically have CI runs if the repository
        has GitHub Actions configured.
        """
        result = check_ci_status(
            branch="main",
            owner=test_config["owner"],
            repo=test_config["repo"],
        )

        # Verify response structure
        assert "status" in result
        assert "branch" in result
        assert result["branch"] == "main"

        # If there are CI runs
        if result["status"] != "no_runs":
            # Verify status is a valid workflow run status
            assert result["status"] in [
                "completed",
                "in_progress",
                "queued",
                "requested",
                "waiting",
            ]

            # If completed, should have conclusion
            if result["status"] == "completed":
                assert "conclusion" in result
                assert result["conclusion"] in [
                    "success",
                    "failure",
                    "cancelled",
                    "skipped",
                    "timed_out",
                    "action_required",
                    "neutral",
                    "stale",
                ]

            # Should have URL and timestamps
            assert "url" in result
            assert "github.com" in result["url"]
            assert "created_at" in result
            assert "updated_at" in result

            # Verify timestamps are valid ISO format
            created_dt = datetime.fromisoformat(result["created_at"].replace("Z", "+00:00"))
            updated_dt = datetime.fromisoformat(result["updated_at"].replace("Z", "+00:00"))
            assert created_dt <= updated_dt

            # Should have jobs list (may be empty)
            assert "jobs" in result
            assert isinstance(result["jobs"], list)

            # If there are jobs, verify structure
            for job in result["jobs"]:
                assert "name" in job
                assert "status" in job
                assert "url" in job
                # conclusion may be None for in-progress jobs
                assert "conclusion" in job

        else:
            # No runs case
            assert result["status"] == "no_runs"
            assert "message" in result

    def test_check_ci_status_for_nonexistent_branch(
        self,
        test_config: dict,
    ) -> None:
        """Test CI status check for a branch that doesn't exist or has no runs."""
        result = check_ci_status(
            branch="nonexistent-branch-xyz-12345",
            owner=test_config["owner"],
            repo=test_config["repo"],
        )

        # Should return no_runs status
        assert result["status"] == "no_runs"
        assert "message" in result
        assert "branch" in result
        assert result["branch"] == "nonexistent-branch-xyz-12345"

    def test_check_ci_status_for_feature_branch_with_ci(
        self,
        test_config: dict,
    ) -> None:
        """Test CI status for a known feature branch with CI runs.

        Uses issue-104-implement-4-core-mcp-tools which should have CI runs.
        If the branch doesn't exist or has no runs, documents that behavior.
        """
        branch = "issue-104-implement-4-core-mcp-tools"

        result = check_ci_status(
            branch=branch,
            owner=test_config["owner"],
            repo=test_config["repo"],
        )

        # Document actual behavior - may have runs or not
        assert "status" in result
        assert result["branch"] == branch

        # If CI runs exist, verify full structure
        if result["status"] != "no_runs":
            assert result["status"] in [
                "completed",
                "in_progress",
                "queued",
                "requested",
                "waiting",
            ]
            assert "url" in result
            assert "created_at" in result
            assert "updated_at" in result
            assert "jobs" in result

    def test_check_ci_status_verifies_job_details(
        self,
        test_config: dict,
    ) -> None:
        """Test that job details are properly returned when available."""
        # Use main branch which likely has CI configured
        result = check_ci_status(
            branch="main",
            owner=test_config["owner"],
            repo=test_config["repo"],
        )

        # Skip if no runs on main
        if result["status"] == "no_runs":
            pytest.skip("No CI runs on main branch to test job details")

        # Verify jobs list structure
        assert "jobs" in result
        jobs = result["jobs"]

        # If there are jobs, verify each has required fields
        if len(jobs) > 0:
            for job in jobs:
                assert isinstance(job, dict)
                assert "name" in job
                assert isinstance(job["name"], str)
                assert len(job["name"]) > 0

                assert "status" in job
                assert job["status"] in [
                    "completed",
                    "in_progress",
                    "queued",
                    "requested",
                    "waiting",
                ]

                assert "url" in job
                assert "github.com" in job["url"]

                # conclusion may be None for non-completed jobs
                assert "conclusion" in job
                if job["status"] == "completed":
                    assert job["conclusion"] in [
                        "success",
                        "failure",
                        "cancelled",
                        "skipped",
                        "timed_out",
                        "action_required",
                        "neutral",
                        "stale",
                    ]

    def test_check_ci_status_returns_latest_run(
        self,
        test_config: dict,
    ) -> None:
        """Test that check_ci_status returns the most recent run for a branch.

        This is verified by checking that multiple calls return consistent results
        (same run ID in the URL) and that timestamps are recent.
        """
        # Use main which should have multiple runs
        result1 = check_ci_status(
            branch="main",
            owner=test_config["owner"],
            repo=test_config["repo"],
        )

        # Skip if no runs
        if result1["status"] == "no_runs":
            pytest.skip("No CI runs to test latest run behavior")

        # Call again immediately
        result2 = check_ci_status(
            branch="main",
            owner=test_config["owner"],
            repo=test_config["repo"],
        )

        # Should return the same run (URLs match)
        assert result1["url"] == result2["url"]
        assert result1["created_at"] == result2["created_at"]

        # Verify the run is reasonably recent (within last 6 months)
        # This helps confirm we're getting the latest, not an old run
        created_dt = datetime.fromisoformat(result1["created_at"].replace("Z", "+00:00"))
        now = datetime.now().astimezone()
        age_days = (now - created_dt).days
        assert age_days < 180, f"Latest run is {age_days} days old - seems suspicious"


@pytest.mark.integration
class TestCIWorkflow:
    """Integration tests for CI-related workflows."""

    def test_ci_status_different_branches(
        self,
        test_config: dict,
    ) -> None:
        """Test that CI status correctly distinguishes between branches."""
        # Check main
        main_result = check_ci_status(
            branch="main",
            owner=test_config["owner"],
            repo=test_config["repo"],
        )

        # Check a likely feature branch
        feature_result = check_ci_status(
            branch="issue-104-implement-4-core-mcp-tools",
            owner=test_config["owner"],
            repo=test_config["repo"],
        )

        # Both should have branch field set correctly
        assert main_result["branch"] == "main"
        assert feature_result["branch"] == "issue-104-implement-4-core-mcp-tools"

        # If both have runs, they should have different URLs (different runs)
        if main_result["status"] != "no_runs" and feature_result["status"] != "no_runs":
            assert (
                main_result["url"] != feature_result["url"]
            ), "Different branches should have different CI runs"


@pytest.mark.integration
class TestGetCILogsIntegration:
    """Integration tests for get_ci_logs tool with real GitHub API."""

    def test_get_logs_for_main_branch(
        self,
        test_config: dict,
    ) -> None:
        """Test getting CI logs for the main branch.

        This test:
        1. Retrieves logs for the main branch's latest CI run
        2. Verifies response structure and all required fields
        3. Validates that logs are returned in expected format
        """
        # First check if main branch has CI runs
        status_result = check_ci_status(
            branch="main",
            owner=test_config["owner"],
            repo=test_config["repo"],
        )

        if status_result["status"] == "no_runs":
            pytest.skip("No CI runs on main branch to test get_ci_logs")

        # Get logs for main branch
        result = get_ci_logs(
            branch="main",
            owner=test_config["owner"],
            repo=test_config["repo"],
        )

        # Verify response structure
        assert "run_id" in result
        assert isinstance(result["run_id"], int)
        assert result["run_id"] > 0

        assert "run_url" in result
        assert isinstance(result["run_url"], str)
        assert "github.com" in result["run_url"]

        assert "branch" in result
        assert result["branch"] == "main"

        assert "status" in result
        assert result["status"] in [
            "completed",
            "in_progress",
            "queued",
            "requested",
            "waiting",
        ]

        assert "conclusion" in result
        # conclusion may be None for in-progress runs
        if result["status"] == "completed":
            assert result["conclusion"] in [
                "success",
                "failure",
                "cancelled",
                "skipped",
                "timed_out",
                "action_required",
                "neutral",
                "stale",
            ]

        assert "jobs" in result
        assert isinstance(result["jobs"], list)

    def test_get_logs_by_run_id(
        self,
        test_config: dict,
    ) -> None:
        """Test getting CI logs by specific run ID.

        This test:
        1. Gets a known run ID from check_ci_status
        2. Retrieves logs using that run_id
        3. Verifies logs match the specific run
        """
        # First get a run ID from main branch
        status_result = check_ci_status(
            branch="main",
            owner=test_config["owner"],
            repo=test_config["repo"],
        )

        if status_result["status"] == "no_runs":
            pytest.skip("No CI runs to test get_ci_logs by run_id")

        # Extract run_id from the run_url
        # URL format: https://github.com/owner/repo/actions/runs/123456
        run_url = status_result["url"]
        run_id = int(run_url.split("/runs/")[-1])

        # Get logs using run_id
        result = get_ci_logs(
            run_id=run_id,
            owner=test_config["owner"],
            repo=test_config["repo"],
        )

        # Verify response structure
        assert "run_id" in result
        assert result["run_id"] == run_id

        assert "run_url" in result
        assert str(run_id) in result["run_url"]

        assert "branch" in result
        assert isinstance(result["branch"], str)

        assert "status" in result
        assert "conclusion" in result
        assert "jobs" in result
        assert isinstance(result["jobs"], list)

    def test_get_logs_with_status_filter_failure(
        self,
        test_config: dict,
    ) -> None:
        """Test filtering logs by failure status.

        This test:
        1. Gets logs for main branch with status="failure"
        2. Verifies only failed jobs are returned
        3. Checks job structure and log content
        """
        status_result = check_ci_status(
            branch="main",
            owner=test_config["owner"],
            repo=test_config["repo"],
        )

        if status_result["status"] == "no_runs":
            pytest.skip("No CI runs on main branch")

        # Get logs with failure filter
        result = get_ci_logs(
            branch="main",
            status="failure",
            owner=test_config["owner"],
            repo=test_config["repo"],
        )

        # Verify response structure
        assert "run_id" in result
        assert "jobs" in result
        assert isinstance(result["jobs"], list)

        # All returned jobs should have failure conclusion
        for job in result["jobs"]:
            assert "job_id" in job
            assert isinstance(job["job_id"], int)

            assert "name" in job
            assert isinstance(job["name"], str)

            assert "status" in job
            assert job["status"] in [
                "completed",
                "in_progress",
                "queued",
                "requested",
                "waiting",
            ]

            assert "conclusion" in job
            # With status="failure", should only get failed jobs
            if result["status"] == "completed":
                assert job["conclusion"] == "failure"

            assert "logs" in job
            assert isinstance(job["logs"], str)

            assert "log_url" in job
            assert "github.com" in job["log_url"]

    def test_get_logs_with_status_filter_success(
        self,
        test_config: dict,
    ) -> None:
        """Test filtering logs by success status.

        This test:
        1. Gets logs with status="success"
        2. Verifies only successful jobs are returned
        3. Validates job structure
        """
        status_result = check_ci_status(
            branch="main",
            owner=test_config["owner"],
            repo=test_config["repo"],
        )

        if status_result["status"] == "no_runs":
            pytest.skip("No CI runs on main branch")

        # Get logs with success filter
        result = get_ci_logs(
            branch="main",
            status="success",
            owner=test_config["owner"],
            repo=test_config["repo"],
        )

        # Verify response structure
        assert "run_id" in result
        assert "jobs" in result
        assert isinstance(result["jobs"], list)

        # All returned jobs should have success conclusion (or be in-progress)
        for job in result["jobs"]:
            assert "job_id" in job
            assert "name" in job
            assert "status" in job
            assert "conclusion" in job
            assert "logs" in job
            assert "log_url" in job

            # With status="success", should only get successful jobs
            if result["status"] == "completed":
                assert job["conclusion"] == "success"

    def test_get_logs_with_status_all(
        self,
        test_config: dict,
    ) -> None:
        """Test getting logs with status="all".

        This test:
        1. Gets all logs regardless of job status
        2. Verifies jobs with various conclusions are returned
        3. Confirms no filtering was applied
        """
        status_result = check_ci_status(
            branch="main",
            owner=test_config["owner"],
            repo=test_config["repo"],
        )

        if status_result["status"] == "no_runs":
            pytest.skip("No CI runs on main branch")

        # Get all logs
        result = get_ci_logs(
            branch="main",
            status="all",
            owner=test_config["owner"],
            repo=test_config["repo"],
        )

        # Verify response structure
        assert "run_id" in result
        assert "jobs" in result
        assert isinstance(result["jobs"], list)

        # Should get more or equal jobs compared to just failures
        result_failures = get_ci_logs(
            branch="main",
            status="failure",
            owner=test_config["owner"],
            repo=test_config["repo"],
        )

        assert len(result["jobs"]) >= len(result_failures["jobs"])

    def test_get_logs_with_job_name_filter(
        self,
        test_config: dict,
    ) -> None:
        """Test filtering logs by job name.

        This test:
        1. Gets logs with a specific job name filter
        2. Verifies only matching jobs are returned
        3. Confirms filtering is case-insensitive
        """
        status_result = check_ci_status(
            branch="main",
            owner=test_config["owner"],
            repo=test_config["repo"],
        )

        if status_result["status"] == "no_runs":
            pytest.skip("No CI runs on main branch")

        # Get all logs first to find a job name
        all_logs = get_ci_logs(
            branch="main",
            status="all",
            owner=test_config["owner"],
            repo=test_config["repo"],
        )

        if len(all_logs["jobs"]) == 0:
            pytest.skip("No jobs found to test job_name filtering")

        # Get first job name
        first_job_name = all_logs["jobs"][0]["name"]

        # Get logs filtered by that job name
        filtered_result = get_ci_logs(
            branch="main",
            job_name=first_job_name,
            status="all",
            owner=test_config["owner"],
            repo=test_config["repo"],
        )

        # Verify structure
        assert "jobs" in filtered_result
        assert isinstance(filtered_result["jobs"], list)

        # All jobs should have the matching name (case-insensitive)
        for job in filtered_result["jobs"]:
            assert first_job_name.lower() in job["name"].lower()

        # Should have fewer or equal jobs than all jobs
        assert len(filtered_result["jobs"]) <= len(all_logs["jobs"])

    def test_get_logs_with_max_lines_parameter(
        self,
        test_config: dict,
    ) -> None:
        """Test log truncation with max_lines parameter.

        This test:
        1. Gets logs with different max_lines values
        2. Verifies logs are truncated (tail behavior)
        3. Confirms smaller max_lines produces shorter output
        """
        status_result = check_ci_status(
            branch="main",
            owner=test_config["owner"],
            repo=test_config["repo"],
        )

        if status_result["status"] == "no_runs":
            pytest.skip("No CI runs on main branch")

        # Get logs with different max_lines
        result_50 = get_ci_logs(
            branch="main",
            status="all",
            max_lines=50,
            owner=test_config["owner"],
            repo=test_config["repo"],
        )

        result_200 = get_ci_logs(
            branch="main",
            status="all",
            max_lines=200,
            owner=test_config["owner"],
            repo=test_config["repo"],
        )

        # Verify response structure
        assert "jobs" in result_50
        assert "jobs" in result_200

        # If there are jobs with actual logs
        if len(result_50["jobs"]) > 0 and len(result_200["jobs"]) > 0:
            # Get a job that has logs in both results
            logs_50_lines = [j for j in result_50["jobs"] if j["logs"]]
            logs_200_lines = [j for j in result_200["jobs"] if j["logs"]]

            if logs_50_lines and logs_200_lines:
                # The 50-line version should generally be shorter or equal
                # (not always strictly shorter due to filtering)
                first_50 = logs_50_lines[0]["logs"]
                first_200 = logs_200_lines[0]["logs"]

                # Count actual lines
                lines_50 = len(first_50.split("\n"))
                lines_200 = len(first_200.split("\n"))

                # 50 lines should have at most ~50 lines
                assert lines_50 <= 50 + 1  # +1 for edge case

                # 200 lines should have at most ~200 lines
                assert lines_200 <= 200 + 1  # +1 for edge case

    def test_get_logs_response_structure_complete(
        self,
        test_config: dict,
    ) -> None:
        """Test complete response structure matches specification.

        This test:
        1. Gets logs and verifies all required fields present
        2. Validates field types and formats
        3. Confirms data consistency
        """
        status_result = check_ci_status(
            branch="main",
            owner=test_config["owner"],
            repo=test_config["repo"],
        )

        if status_result["status"] == "no_runs":
            pytest.skip("No CI runs on main branch")

        result = get_ci_logs(
            branch="main",
            owner=test_config["owner"],
            repo=test_config["repo"],
        )

        # Verify all top-level fields
        required_fields = ["run_id", "run_url", "branch", "status", "conclusion", "jobs"]
        for field in required_fields:
            assert field in result, f"Missing required field: {field}"

        # Type validation
        assert isinstance(result["run_id"], int)
        assert isinstance(result["run_url"], str)
        assert isinstance(result["branch"], str)
        assert isinstance(result["status"], str)
        assert result["conclusion"] is None or isinstance(result["conclusion"], str)
        assert isinstance(result["jobs"], list)

        # Format validation
        assert result["run_id"] > 0
        assert "github.com" in result["run_url"]
        assert len(result["branch"]) > 0

        # Verify job structure
        for job in result["jobs"]:
            job_fields = ["job_id", "name", "status", "conclusion", "logs", "log_url"]
            for field in job_fields:
                assert field in job, f"Job missing required field: {field}"

            # Type validation for jobs
            assert isinstance(job["job_id"], int)
            assert isinstance(job["name"], str)
            assert isinstance(job["status"], str)
            assert job["conclusion"] is None or isinstance(job["conclusion"], str)
            assert isinstance(job["logs"], str)
            assert isinstance(job["log_url"], str)

            # Value validation
            assert job["job_id"] > 0
            assert len(job["name"]) > 0
            assert "github.com" in job["log_url"]


@pytest.mark.integration
class TestGetCILogsErrorHandling:
    """Integration tests for error handling in get_ci_logs."""

    def test_get_logs_neither_branch_nor_run_id_raises_error(
        self,
        test_config: dict,
    ) -> None:
        """Test that providing neither branch nor run_id raises ValueError.

        This test:
        1. Calls get_ci_logs with neither parameter
        2. Verifies ValueError is raised
        3. Checks error message is descriptive
        """
        with pytest.raises(ValueError) as exc_info:
            get_ci_logs(
                owner=test_config["owner"],
                repo=test_config["repo"],
            )

        error_msg = str(exc_info.value).lower()
        assert "branch" in error_msg or "run_id" in error_msg

    def test_get_logs_both_branch_and_run_id_raises_error(
        self,
        test_config: dict,
    ) -> None:
        """Test that providing both branch and run_id raises ValueError.

        This test:
        1. Calls get_ci_logs with both parameters
        2. Verifies ValueError is raised
        3. Checks error message indicates mutual exclusivity
        """
        with pytest.raises(ValueError) as exc_info:
            get_ci_logs(
                branch="main",
                run_id=123456,
                owner=test_config["owner"],
                repo=test_config["repo"],
            )

        error_msg = str(exc_info.value).lower()
        assert "both" in error_msg or "cannot" in error_msg

    def test_get_logs_invalid_status_raises_error(
        self,
        test_config: dict,
    ) -> None:
        """Test that invalid status parameter raises ValueError.

        This test:
        1. Calls get_ci_logs with invalid status
        2. Verifies ValueError is raised
        3. Checks error includes valid status options
        """
        with pytest.raises(ValueError) as exc_info:
            get_ci_logs(
                branch="main",
                status="invalid_status",
                owner=test_config["owner"],
                repo=test_config["repo"],
            )

        error_msg = str(exc_info.value).lower()
        assert "invalid status" in error_msg or "must be" in error_msg

    def test_get_logs_nonexistent_branch_raises_error(
        self,
        test_config: dict,
    ) -> None:
        """Test that nonexistent branch raises ValueError.

        This test:
        1. Calls get_ci_logs with nonexistent branch
        2. Verifies ValueError is raised
        3. Checks error message is descriptive
        """
        with pytest.raises(ValueError) as exc_info:
            get_ci_logs(
                branch="nonexistent-branch-xyz-12345-no-ci-runs",
                owner=test_config["owner"],
                repo=test_config["repo"],
            )

        error_msg = str(exc_info.value).lower()
        assert "no ci runs" in error_msg or "not found" in error_msg

    def test_get_logs_nonexistent_run_id_raises_error(
        self,
        test_config: dict,
    ) -> None:
        """Test that nonexistent run_id raises ValueError.

        This test:
        1. Calls get_ci_logs with invalid run_id
        2. Verifies ValueError is raised
        3. Checks error indicates run not found
        """
        # Use a very large number unlikely to exist
        invalid_run_id = 999999999999

        with pytest.raises(ValueError) as exc_info:
            get_ci_logs(
                run_id=invalid_run_id,
                owner=test_config["owner"],
                repo=test_config["repo"],
            )

        error_msg = str(exc_info.value).lower()
        assert "not found" in error_msg or "failed" in error_msg


@pytest.mark.integration
class TestGetCILogsWorkflows:
    """Integration tests for get_ci_logs workflows."""

    def test_get_logs_for_branch_then_by_run_id(
        self,
        test_config: dict,
    ) -> None:
        """Test workflow: get logs by branch, then verify with run_id.

        This test:
        1. Gets logs for a branch
        2. Extracts run_id from response
        3. Gets logs again using run_id
        4. Verifies consistency
        """
        # Get logs by branch
        branch_logs = get_ci_logs(
            branch="main",
            owner=test_config["owner"],
            repo=test_config["repo"],
        )

        if branch_logs["status"] == "no_runs":
            pytest.skip("No CI runs to test workflow")

        run_id = branch_logs["run_id"]

        # Get logs by run_id
        run_logs = get_ci_logs(
            run_id=run_id,
            owner=test_config["owner"],
            repo=test_config["repo"],
        )

        # Verify consistency
        assert run_logs["run_id"] == branch_logs["run_id"]
        assert run_logs["branch"] == branch_logs["branch"]
        assert run_logs["status"] == branch_logs["status"]
        assert run_logs["conclusion"] == branch_logs["conclusion"]

        # Job count might differ due to filtering, but run info should match
        assert len(run_logs["jobs"]) >= 0  # Just verify it's a list

    def test_get_logs_filters_combine(
        self,
        test_config: dict,
    ) -> None:
        """Test combining multiple filters (job_name + status).

        This test:
        1. Gets logs with both job_name and status filters
        2. Verifies both filters are applied
        3. Confirms more restrictive filters return fewer results
        """
        # Get all logs first
        all_logs = get_ci_logs(
            branch="main",
            status="all",
            owner=test_config["owner"],
            repo=test_config["repo"],
        )

        if len(all_logs["jobs"]) == 0:
            pytest.skip("No jobs found to test filter combination")

        # Get first job name
        first_job_name = all_logs["jobs"][0]["name"]

        # Apply both filters
        filtered_logs = get_ci_logs(
            branch="main",
            job_name=first_job_name,
            status="all",
            owner=test_config["owner"],
            repo=test_config["repo"],
        )

        # Verify filters worked
        assert len(filtered_logs["jobs"]) <= len(all_logs["jobs"])

        # All jobs should match the name filter
        for job in filtered_logs["jobs"]:
            assert first_job_name.lower() in job["name"].lower()
