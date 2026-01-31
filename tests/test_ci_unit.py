"""Unit tests for CI operations with mocked GitHub API.

These tests use mocks and don't require GITHUB_TOKEN or network access.
Run with: pytest github-mcp-server/tests/test_ci_unit.py
"""

from datetime import datetime
from unittest.mock import Mock, patch

import pytest
import requests
from github_mcp_server.tools.ci import check_ci_status, get_ci_logs


class TestCheckCIStatus:
    """Unit tests for check_ci_status tool."""

    @patch("github_mcp_server.tools.ci.get_github_client")
    def test_check_ci_status_success(self, mock_get_client: Mock) -> None:
        """Test checking CI status for a branch with successful run."""
        # Setup mocks
        mock_gh = Mock()
        mock_repo = Mock()
        mock_run = Mock()
        mock_workflow = Mock()
        mock_job1 = Mock()
        mock_job2 = Mock()

        # Configure workflow run
        mock_run.id = 123456
        mock_run.workflow_id = 1001
        mock_run.status = "completed"
        mock_run.conclusion = "success"
        mock_run.html_url = "https://github.com/testowner/testrepo/actions/runs/123456"
        mock_run.created_at = datetime(2025, 12, 15, 10, 0, 0)
        mock_run.updated_at = datetime(2025, 12, 15, 10, 30, 0)
        mock_run.head_branch = "main"

        # Configure workflow metadata
        mock_workflow.name = "CI"

        # Configure jobs
        mock_job1.name = "test"
        mock_job1.status = "completed"
        mock_job1.conclusion = "success"
        mock_job1.html_url = "https://github.com/testowner/testrepo/actions/runs/123456/jobs/1"

        mock_job2.name = "lint"
        mock_job2.status = "completed"
        mock_job2.conclusion = "success"
        mock_job2.html_url = "https://github.com/testowner/testrepo/actions/runs/123456/jobs/2"

        mock_run.jobs.return_value = [mock_job1, mock_job2]

        # Setup repository mock
        mock_repo.get_workflow_runs.return_value = [mock_run]
        mock_repo.get_workflow.return_value = mock_workflow
        mock_gh.get_repo.return_value = mock_repo
        mock_get_client.return_value = mock_gh

        # Execute
        result = check_ci_status(branch="main")

        # Verify response structure
        assert isinstance(result, dict)
        assert result["status"] == "completed"
        assert result["conclusion"] == "success"
        assert result["overall_status"] == "completed"
        assert result["overall_conclusion"] == "success"
        assert result["branch"] == "main"
        assert result["total_workflows"] == 1

        # Verify workflows list
        assert len(result["workflows"]) == 1
        workflow = result["workflows"][0]
        assert workflow["name"] == "CI"
        assert workflow["status"] == "completed"
        assert workflow["conclusion"] == "success"
        assert workflow["url"] == "https://github.com/testowner/testrepo/actions/runs/123456"
        assert "created_at" in workflow
        assert "updated_at" in workflow

        # Verify jobs within workflow
        assert len(workflow["jobs"]) == 2
        assert workflow["jobs"][0]["name"] == "test"
        assert workflow["jobs"][0]["conclusion"] == "success"
        assert workflow["jobs"][1]["name"] == "lint"

    @patch("github_mcp_server.tools.ci.get_github_client")
    def test_check_ci_status_no_runs(self, mock_get_client: Mock) -> None:
        """Test checking CI status when no runs exist for branch."""
        mock_gh = Mock()
        mock_repo = Mock()

        # Return empty list (no runs)
        mock_repo.get_workflow_runs.return_value = []
        mock_gh.get_repo.return_value = mock_repo
        mock_get_client.return_value = mock_gh

        # Execute
        result = check_ci_status(branch="nonexistent-branch")

        # Verify
        assert result["status"] == "no_runs"
        assert result["overall_status"] == "no_runs"
        assert result["overall_conclusion"] is None
        assert "No CI runs found" in result["message"]
        assert result["branch"] == "nonexistent-branch"
        assert result["workflows"] == []

    @patch("github_mcp_server.tools.ci.get_github_client")
    def test_check_ci_status_multiple_workflows(self, mock_get_client: Mock) -> None:
        """Test checking CI status with multiple workflows returns all of them."""
        # Setup mocks
        mock_gh = Mock()
        mock_repo = Mock()

        # Create two workflow runs from different workflows
        mock_run1 = Mock()
        mock_run1.id = 123456
        mock_run1.workflow_id = 1001
        mock_run1.status = "completed"
        mock_run1.conclusion = "success"
        mock_run1.html_url = "https://github.com/testowner/testrepo/actions/runs/123456"
        mock_run1.created_at = datetime(2025, 12, 15, 10, 0, 0)
        mock_run1.updated_at = datetime(2025, 12, 15, 10, 30, 0)
        mock_run1.head_branch = "feature-branch"
        mock_run1.jobs.return_value = []

        mock_run2 = Mock()
        mock_run2.id = 123457
        mock_run2.workflow_id = 1002
        mock_run2.status = "completed"
        mock_run2.conclusion = "failure"
        mock_run2.html_url = "https://github.com/testowner/testrepo/actions/runs/123457"
        mock_run2.created_at = datetime(2025, 12, 15, 10, 5, 0)
        mock_run2.updated_at = datetime(2025, 12, 15, 10, 35, 0)
        mock_run2.head_branch = "feature-branch"
        mock_run2.jobs.return_value = []

        # Configure workflow metadata
        mock_workflow1 = Mock()
        mock_workflow1.name = "CI"
        mock_workflow2 = Mock()
        mock_workflow2.name = "Lint"

        def get_workflow_side_effect(workflow_id: int) -> Mock:
            if workflow_id == 1001:
                return mock_workflow1
            return mock_workflow2

        # Setup repository mock
        mock_repo.get_workflow_runs.return_value = [mock_run1, mock_run2]
        mock_repo.get_workflow.side_effect = get_workflow_side_effect
        mock_gh.get_repo.return_value = mock_repo
        mock_get_client.return_value = mock_gh

        # Execute
        result = check_ci_status(branch="feature-branch")

        # Verify overall status reflects the worst case
        assert result["overall_status"] == "completed"
        assert result["overall_conclusion"] == "failure"  # One workflow failed
        assert result["total_workflows"] == 2

        # Verify both workflows are returned
        assert len(result["workflows"]) == 2
        workflow_names = [w["name"] for w in result["workflows"]]
        assert "CI" in workflow_names
        assert "Lint" in workflow_names

    @patch("github_mcp_server.tools.ci.get_github_client")
    def test_check_ci_status_in_progress_workflow(self, mock_get_client: Mock) -> None:
        """Test that overall status is in_progress when any workflow is in progress."""
        # Setup mocks
        mock_gh = Mock()
        mock_repo = Mock()

        # Create two workflow runs - one completed, one in progress
        mock_run1 = Mock()
        mock_run1.id = 123456
        mock_run1.workflow_id = 1001
        mock_run1.status = "completed"
        mock_run1.conclusion = "success"
        mock_run1.html_url = "https://github.com/testowner/testrepo/actions/runs/123456"
        mock_run1.created_at = datetime(2025, 12, 15, 10, 0, 0)
        mock_run1.updated_at = datetime(2025, 12, 15, 10, 30, 0)
        mock_run1.head_branch = "feature-branch"
        mock_run1.jobs.return_value = []

        mock_run2 = Mock()
        mock_run2.id = 123457
        mock_run2.workflow_id = 1002
        mock_run2.status = "in_progress"
        mock_run2.conclusion = None
        mock_run2.html_url = "https://github.com/testowner/testrepo/actions/runs/123457"
        mock_run2.created_at = datetime(2025, 12, 15, 10, 5, 0)
        mock_run2.updated_at = datetime(2025, 12, 15, 10, 35, 0)
        mock_run2.head_branch = "feature-branch"
        mock_run2.jobs.return_value = []

        # Configure workflow metadata
        mock_workflow1 = Mock()
        mock_workflow1.name = "CI"
        mock_workflow2 = Mock()
        mock_workflow2.name = "Deploy"

        def get_workflow_side_effect(workflow_id: int) -> Mock:
            if workflow_id == 1001:
                return mock_workflow1
            return mock_workflow2

        # Setup repository mock
        mock_repo.get_workflow_runs.return_value = [mock_run1, mock_run2]
        mock_repo.get_workflow.side_effect = get_workflow_side_effect
        mock_gh.get_repo.return_value = mock_repo
        mock_get_client.return_value = mock_gh

        # Execute
        result = check_ci_status(branch="feature-branch")

        # Verify overall status is in_progress (most severe non-completed state)
        assert result["overall_status"] == "in_progress"
        # Conclusion is only from completed workflows
        assert result["overall_conclusion"] == "success"
        assert result["total_workflows"] == 2


class TestGetCILogs:
    """Unit tests for get_ci_logs tool."""

    @patch("github_mcp_server.tools.ci.os.getenv")
    @patch("github_mcp_server.tools.ci.requests.get")
    @patch("github_mcp_server.tools.ci.get_github_client")
    def test_get_logs_by_branch_success(
        self,
        mock_get_client: Mock,
        mock_requests_get: Mock,
        mock_getenv: Mock,
    ) -> None:
        """Test getting logs for a specific branch with successful jobs."""
        # Setup mocks
        mock_gh = Mock()
        mock_repo = Mock()
        mock_run = Mock()
        mock_job = Mock()

        # Configure workflow run
        mock_run.id = 123456
        mock_run.status = "completed"
        mock_run.conclusion = "failure"
        mock_run.html_url = "https://github.com/testowner/testrepo/actions/runs/123456"
        mock_run.head_branch = "issue-239-implement-get-ci-logs"

        # Configure job
        mock_job.id = 789
        mock_job.name = "test"
        mock_job.status = "completed"
        mock_job.conclusion = "failure"
        mock_job.html_url = "https://github.com/testowner/testrepo/actions/runs/123456/jobs/789"

        mock_run.jobs.return_value = [mock_job]

        # Setup repository mock
        mock_repo.get_workflow_runs.return_value = [mock_run]
        mock_gh.get_repo.return_value = mock_repo
        mock_get_client.return_value = mock_gh

        # Mock token and HTTP response
        mock_getenv.return_value = "gh_test_token_12345"
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = "Error in test\nFailure reason\nStack trace line 1\nStack trace line 2"
        mock_requests_get.return_value = mock_response

        # Execute
        result = get_ci_logs(branch="issue-239-implement-get-ci-logs", status="failure")

        # Verify response structure
        assert isinstance(result, dict)
        assert result["run_id"] == 123456
        assert result["branch"] == "issue-239-implement-get-ci-logs"
        assert result["status"] == "completed"
        assert result["conclusion"] == "failure"
        assert "run_url" in result
        assert isinstance(result["jobs"], list)
        assert len(result["jobs"]) == 1

        # Verify job details
        job = result["jobs"][0]
        assert job["job_id"] == 789
        assert job["name"] == "test"
        assert job["status"] == "completed"
        assert job["conclusion"] == "failure"
        assert "Error in test" in job["logs"]
        assert "log_url" in job

        # Verify API calls
        mock_requests_get.assert_called_once()
        call_args = mock_requests_get.call_args
        assert "logs" in call_args[0][0]
        assert call_args[1]["headers"]["Authorization"] == "token gh_test_token_12345"

    @patch("github_mcp_server.tools.ci.os.getenv")
    @patch("github_mcp_server.tools.ci.requests.get")
    @patch("github_mcp_server.tools.ci.get_github_client")
    def test_get_logs_by_run_id_success(
        self,
        mock_get_client: Mock,
        mock_requests_get: Mock,
        mock_getenv: Mock,
    ) -> None:
        """Test getting logs for a specific run ID."""
        mock_gh = Mock()
        mock_repo = Mock()
        mock_run = Mock()
        mock_job = Mock()

        # Configure workflow run
        mock_run.id = 987654
        mock_run.status = "completed"
        mock_run.conclusion = "success"
        mock_run.html_url = "https://github.com/testowner/testrepo/actions/runs/987654"
        mock_run.head_branch = "main"

        # Configure job
        mock_job.id = 999
        mock_job.name = "build"
        mock_job.status = "completed"
        mock_job.conclusion = "success"
        mock_job.html_url = "https://github.com/testowner/testrepo/actions/runs/987654/jobs/999"

        mock_run.jobs.return_value = [mock_job]

        # Setup repository mock
        mock_repo.get_workflow_run.return_value = mock_run
        mock_gh.get_repo.return_value = mock_repo
        mock_get_client.return_value = mock_gh

        # Mock token and HTTP response
        mock_getenv.return_value = "gh_test_token_12345"
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = "Build successful\nAll tests passed"
        mock_requests_get.return_value = mock_response

        # Execute
        result = get_ci_logs(run_id=987654, status="all")

        # Verify
        assert result["run_id"] == 987654
        assert result["branch"] == "main"
        assert len(result["jobs"]) == 1
        assert result["jobs"][0]["name"] == "build"
        assert result["jobs"][0]["conclusion"] == "success"

        # Verify API was called with run_id
        mock_repo.get_workflow_run.assert_called_once_with(987654)

    @patch("github_mcp_server.tools.ci.os.getenv")
    @patch("github_mcp_server.tools.ci.requests.get")
    @patch("github_mcp_server.tools.ci.get_github_client")
    def test_get_logs_filter_by_job_name(
        self,
        mock_get_client: Mock,
        mock_requests_get: Mock,
        mock_getenv: Mock,
    ) -> None:
        """Test filtering logs by job name (partial match)."""
        mock_gh = Mock()
        mock_repo = Mock()
        mock_run = Mock()
        mock_job1 = Mock()
        mock_job2 = Mock()
        mock_job3 = Mock()

        # Configure workflow run
        mock_run.id = 111111
        mock_run.status = "completed"
        mock_run.conclusion = "failure"
        mock_run.html_url = "https://github.com/testowner/testrepo/actions/runs/111111"
        mock_run.head_branch = "feature-branch"

        # Configure multiple jobs
        mock_job1.id = 1
        mock_job1.name = "test-unit"
        mock_job1.status = "completed"
        mock_job1.conclusion = "failure"
        mock_job1.html_url = "https://github.com/testowner/testrepo/actions/runs/111111/jobs/1"

        mock_job2.id = 2
        mock_job2.name = "test-integration"
        mock_job2.status = "completed"
        mock_job2.conclusion = "failure"
        mock_job2.html_url = "https://github.com/testowner/testrepo/actions/runs/111111/jobs/2"

        mock_job3.id = 3
        mock_job3.name = "lint"
        mock_job3.status = "completed"
        mock_job3.conclusion = "success"
        mock_job3.html_url = "https://github.com/testowner/testrepo/actions/runs/111111/jobs/3"

        mock_run.jobs.return_value = [mock_job1, mock_job2, mock_job3]

        # Setup repository mock
        mock_repo.get_workflow_runs.return_value = [mock_run]
        mock_gh.get_repo.return_value = mock_repo
        mock_get_client.return_value = mock_gh

        # Mock token and HTTP response
        mock_getenv.return_value = "gh_test_token_12345"
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = "Test failed\nAssertion error"
        mock_requests_get.return_value = mock_response

        # Execute - filter by "test" (should match test-unit and test-integration)
        result = get_ci_logs(branch="feature-branch", job_name="test", status="failure")

        # Verify - only test jobs returned
        assert len(result["jobs"]) == 2
        assert result["jobs"][0]["name"] == "test-unit"
        assert result["jobs"][1]["name"] == "test-integration"

        # Lint job should not be included
        job_names = [job["name"] for job in result["jobs"]]
        assert "lint" not in job_names

    @patch("github_mcp_server.tools.ci.os.getenv")
    @patch("github_mcp_server.tools.ci.requests.get")
    @patch("github_mcp_server.tools.ci.get_github_client")
    def test_get_logs_filter_by_status_failure(
        self,
        mock_get_client: Mock,
        mock_requests_get: Mock,
        mock_getenv: Mock,
    ) -> None:
        """Test filtering logs by failure status."""
        mock_gh = Mock()
        mock_repo = Mock()
        mock_run = Mock()
        mock_job1 = Mock()
        mock_job2 = Mock()

        # Configure workflow run
        mock_run.id = 222222
        mock_run.status = "completed"
        mock_run.conclusion = "failure"
        mock_run.html_url = "https://github.com/testowner/testrepo/actions/runs/222222"
        mock_run.head_branch = "issue-test"

        # One failed job, one successful
        mock_job1.id = 10
        mock_job1.name = "test"
        mock_job1.status = "completed"
        mock_job1.conclusion = "failure"
        mock_job1.html_url = "https://github.com/testowner/testrepo/actions/runs/222222/jobs/10"

        mock_job2.id = 11
        mock_job2.name = "lint"
        mock_job2.status = "completed"
        mock_job2.conclusion = "success"
        mock_job2.html_url = "https://github.com/testowner/testrepo/actions/runs/222222/jobs/11"

        mock_run.jobs.return_value = [mock_job1, mock_job2]

        # Setup repository mock
        mock_repo.get_workflow_runs.return_value = [mock_run]
        mock_gh.get_repo.return_value = mock_repo
        mock_get_client.return_value = mock_gh

        # Mock token and HTTP response
        mock_getenv.return_value = "gh_test_token_12345"
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = "Error"
        mock_requests_get.return_value = mock_response

        # Execute - filter by failure only
        result = get_ci_logs(branch="issue-test", status="failure")

        # Verify - only failed job returned
        assert len(result["jobs"]) == 1
        assert result["jobs"][0]["conclusion"] == "failure"

    @patch("github_mcp_server.tools.ci.os.getenv")
    @patch("github_mcp_server.tools.ci.requests.get")
    @patch("github_mcp_server.tools.ci.get_github_client")
    def test_get_logs_filter_by_status_success(
        self,
        mock_get_client: Mock,
        mock_requests_get: Mock,
        mock_getenv: Mock,
    ) -> None:
        """Test filtering logs by success status."""
        mock_gh = Mock()
        mock_repo = Mock()
        mock_run = Mock()
        mock_job1 = Mock()
        mock_job2 = Mock()

        # Configure workflow run
        mock_run.id = 333333
        mock_run.status = "completed"
        mock_run.conclusion = "success"
        mock_run.html_url = "https://github.com/testowner/testrepo/actions/runs/333333"
        mock_run.head_branch = "main"

        # One successful job, one failed
        mock_job1.id = 20
        mock_job1.name = "test"
        mock_job1.status = "completed"
        mock_job1.conclusion = "failure"
        mock_job1.html_url = "https://github.com/testowner/testrepo/actions/runs/333333/jobs/20"

        mock_job2.id = 21
        mock_job2.name = "lint"
        mock_job2.status = "completed"
        mock_job2.conclusion = "success"
        mock_job2.html_url = "https://github.com/testowner/testrepo/actions/runs/333333/jobs/21"

        mock_run.jobs.return_value = [mock_job1, mock_job2]

        # Setup repository mock
        mock_repo.get_workflow_runs.return_value = [mock_run]
        mock_gh.get_repo.return_value = mock_repo
        mock_get_client.return_value = mock_gh

        # Mock token and HTTP response
        mock_getenv.return_value = "gh_test_token_12345"
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = "Success"
        mock_requests_get.return_value = mock_response

        # Execute - filter by success only
        result = get_ci_logs(branch="main", status="success")

        # Verify - only successful job returned
        assert len(result["jobs"]) == 1
        assert result["jobs"][0]["conclusion"] == "success"

    @patch("github_mcp_server.tools.ci.os.getenv")
    @patch("github_mcp_server.tools.ci.requests.get")
    @patch("github_mcp_server.tools.ci.get_github_client")
    def test_get_logs_filter_by_status_all(
        self,
        mock_get_client: Mock,
        mock_requests_get: Mock,
        mock_getenv: Mock,
    ) -> None:
        """Test filtering logs with 'all' status returns both success and failure."""
        mock_gh = Mock()
        mock_repo = Mock()
        mock_run = Mock()
        mock_job1 = Mock()
        mock_job2 = Mock()

        # Configure workflow run
        mock_run.id = 444444
        mock_run.status = "completed"
        mock_run.conclusion = "failure"
        mock_run.html_url = "https://github.com/testowner/testrepo/actions/runs/444444"
        mock_run.head_branch = "test-branch"

        # Jobs with different conclusions
        mock_job1.id = 30
        mock_job1.name = "test"
        mock_job1.status = "completed"
        mock_job1.conclusion = "failure"
        mock_job1.html_url = "https://github.com/testowner/testrepo/actions/runs/444444/jobs/30"

        mock_job2.id = 31
        mock_job2.name = "lint"
        mock_job2.status = "completed"
        mock_job2.conclusion = "success"
        mock_job2.html_url = "https://github.com/testowner/testrepo/actions/runs/444444/jobs/31"

        mock_run.jobs.return_value = [mock_job1, mock_job2]

        # Setup repository mock
        mock_repo.get_workflow_runs.return_value = [mock_run]
        mock_gh.get_repo.return_value = mock_repo
        mock_get_client.return_value = mock_gh

        # Mock token and HTTP response
        mock_getenv.return_value = "gh_test_token_12345"
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = "Log"
        mock_requests_get.return_value = mock_response

        # Execute - filter by all
        result = get_ci_logs(branch="test-branch", status="all")

        # Verify - both jobs returned
        assert len(result["jobs"]) == 2

    @patch("github_mcp_server.tools.ci.os.getenv")
    @patch("github_mcp_server.tools.ci.requests.get")
    @patch("github_mcp_server.tools.ci.get_github_client")
    def test_get_logs_truncate_to_max_lines(
        self,
        mock_get_client: Mock,
        mock_requests_get: Mock,
        mock_getenv: Mock,
    ) -> None:
        """Test that logs are truncated to max_lines (tail behavior)."""
        mock_gh = Mock()
        mock_repo = Mock()
        mock_run = Mock()
        mock_job = Mock()

        # Configure workflow run
        mock_run.id = 555555
        mock_run.status = "completed"
        mock_run.conclusion = "failure"
        mock_run.html_url = "https://github.com/testowner/testrepo/actions/runs/555555"
        mock_run.head_branch = "test-branch"

        # Configure job
        mock_job.id = 40
        mock_job.name = "test"
        mock_job.status = "completed"
        mock_job.conclusion = "failure"
        mock_job.html_url = "https://github.com/testowner/testrepo/actions/runs/555555/jobs/40"

        mock_run.jobs.return_value = [mock_job]

        # Setup repository mock
        mock_repo.get_workflow_runs.return_value = [mock_run]
        mock_gh.get_repo.return_value = mock_repo
        mock_get_client.return_value = mock_gh

        # Mock token and HTTP response with many lines
        mock_getenv.return_value = "gh_test_token_12345"
        mock_response = Mock()
        mock_response.status_code = 200
        # Create 300 lines of logs
        log_lines = [f"Log line {i}" for i in range(1, 301)]
        mock_response.text = "\n".join(log_lines)
        mock_requests_get.return_value = mock_response

        # Execute with max_lines=50
        result = get_ci_logs(branch="test-branch", status="all", max_lines=50)

        # Verify logs are truncated
        job_logs = result["jobs"][0]["logs"]
        returned_lines = job_logs.split("\n")
        assert len(returned_lines) == 50
        # Should have last 50 lines (tail behavior)
        assert "Log line 251" in job_logs
        assert "Log line 300" in job_logs
        assert "Log line 1" not in job_logs
        assert "Log line 100" not in job_logs

    @patch("github_mcp_server.tools.ci.os.getenv")
    @patch("github_mcp_server.tools.ci.requests.get")
    @patch("github_mcp_server.tools.ci.get_github_client")
    def test_get_logs_http_404_error(
        self,
        mock_get_client: Mock,
        mock_requests_get: Mock,
        mock_getenv: Mock,
    ) -> None:
        """Test handling of HTTP 404 error when logs are unavailable."""
        mock_gh = Mock()
        mock_repo = Mock()
        mock_run = Mock()
        mock_job = Mock()

        # Configure workflow run
        mock_run.id = 666666
        mock_run.status = "completed"
        mock_run.conclusion = "failure"
        mock_run.html_url = "https://github.com/testowner/testrepo/actions/runs/666666"
        mock_run.head_branch = "test-branch"

        # Configure job
        mock_job.id = 50
        mock_job.name = "test"
        mock_job.status = "completed"
        mock_job.conclusion = "failure"
        mock_job.html_url = "https://github.com/testowner/testrepo/actions/runs/666666/jobs/50"

        mock_run.jobs.return_value = [mock_job]

        # Setup repository mock
        mock_repo.get_workflow_runs.return_value = [mock_run]
        mock_gh.get_repo.return_value = mock_repo
        mock_get_client.return_value = mock_gh

        # Mock token and HTTP error response
        mock_getenv.return_value = "gh_test_token_12345"
        mock_response = Mock()
        mock_response.status_code = 404
        mock_requests_get.return_value = mock_response

        # Execute
        result = get_ci_logs(branch="test-branch", status="failure")

        # Verify error message in logs
        assert len(result["jobs"]) == 1
        assert "404" in result["jobs"][0]["logs"]
        assert "not available" in result["jobs"][0]["logs"]

    @patch("github_mcp_server.tools.ci.os.getenv")
    @patch("github_mcp_server.tools.ci.requests.get")
    @patch("github_mcp_server.tools.ci.get_github_client")
    def test_get_logs_request_timeout(
        self,
        mock_get_client: Mock,
        mock_requests_get: Mock,
        mock_getenv: Mock,
    ) -> None:
        """Test handling of request timeout when downloading logs."""
        mock_gh = Mock()
        mock_repo = Mock()
        mock_run = Mock()
        mock_job = Mock()

        # Configure workflow run
        mock_run.id = 777777
        mock_run.status = "completed"
        mock_run.conclusion = "failure"
        mock_run.html_url = "https://github.com/testowner/testrepo/actions/runs/777777"
        mock_run.head_branch = "test-branch"

        # Configure job
        mock_job.id = 60
        mock_job.name = "test"
        mock_job.status = "completed"
        mock_job.conclusion = "failure"
        mock_job.html_url = "https://github.com/testowner/testrepo/actions/runs/777777/jobs/60"

        mock_run.jobs.return_value = [mock_job]

        # Setup repository mock
        mock_repo.get_workflow_runs.return_value = [mock_run]
        mock_gh.get_repo.return_value = mock_repo
        mock_get_client.return_value = mock_gh

        # Mock token and timeout error
        mock_getenv.return_value = "gh_test_token_12345"
        mock_requests_get.side_effect = requests.exceptions.Timeout("Request timeout")

        # Execute
        result = get_ci_logs(branch="test-branch", status="failure")

        # Verify error message in logs
        assert len(result["jobs"]) == 1
        assert "Error downloading logs" in result["jobs"][0]["logs"]
        assert "timeout" in result["jobs"][0]["logs"].lower()

    @patch("github_mcp_server.tools.ci.os.getenv")
    @patch("github_mcp_server.tools.ci.requests.get")
    @patch("github_mcp_server.tools.ci.get_github_client")
    def test_get_logs_connection_error(
        self,
        mock_get_client: Mock,
        mock_requests_get: Mock,
        mock_getenv: Mock,
    ) -> None:
        """Test handling of connection error when downloading logs."""
        mock_gh = Mock()
        mock_repo = Mock()
        mock_run = Mock()
        mock_job = Mock()

        # Configure workflow run
        mock_run.id = 888888
        mock_run.status = "completed"
        mock_run.conclusion = "failure"
        mock_run.html_url = "https://github.com/testowner/testrepo/actions/runs/888888"
        mock_run.head_branch = "test-branch"

        # Configure job
        mock_job.id = 70
        mock_job.name = "test"
        mock_job.status = "completed"
        mock_job.conclusion = "failure"
        mock_job.html_url = "https://github.com/testowner/testrepo/actions/runs/888888/jobs/70"

        mock_run.jobs.return_value = [mock_job]

        # Setup repository mock
        mock_repo.get_workflow_runs.return_value = [mock_run]
        mock_gh.get_repo.return_value = mock_repo
        mock_get_client.return_value = mock_gh

        # Mock token and connection error
        mock_getenv.return_value = "gh_test_token_12345"
        mock_requests_get.side_effect = requests.exceptions.ConnectionError("Connection failed")

        # Execute
        result = get_ci_logs(branch="test-branch", status="failure")

        # Verify error message in logs
        assert len(result["jobs"]) == 1
        assert "Error downloading logs" in result["jobs"][0]["logs"]

    @patch("github_mcp_server.tools.ci.os.getenv")
    @patch("github_mcp_server.tools.ci.requests.get")
    @patch("github_mcp_server.tools.ci.get_github_client")
    def test_get_logs_no_jobs_match_filters(
        self,
        mock_get_client: Mock,
        mock_requests_get: Mock,
        mock_getenv: Mock,
    ) -> None:
        """Test handling when no jobs match the filter criteria."""
        mock_gh = Mock()
        mock_repo = Mock()
        mock_run = Mock()
        mock_job1 = Mock()
        mock_job2 = Mock()

        # Configure workflow run
        mock_run.id = 999999
        mock_run.status = "completed"
        mock_run.conclusion = "failure"
        mock_run.html_url = "https://github.com/testowner/testrepo/actions/runs/999999"
        mock_run.head_branch = "test-branch"

        # Configure jobs - both successful
        mock_job1.id = 80
        mock_job1.name = "test"
        mock_job1.status = "completed"
        mock_job1.conclusion = "success"
        mock_job1.html_url = "https://github.com/testowner/testrepo/actions/runs/999999/jobs/80"

        mock_job2.id = 81
        mock_job2.name = "lint"
        mock_job2.status = "completed"
        mock_job2.conclusion = "success"
        mock_job2.html_url = "https://github.com/testowner/testrepo/actions/runs/999999/jobs/81"

        mock_run.jobs.return_value = [mock_job1, mock_job2]

        # Setup repository mock
        mock_repo.get_workflow_runs.return_value = [mock_run]
        mock_gh.get_repo.return_value = mock_repo
        mock_get_client.return_value = mock_gh

        # Mock token
        mock_getenv.return_value = "gh_test_token_12345"

        # Execute - filter by failure (but all jobs are successful)
        result = get_ci_logs(branch="test-branch", status="failure")

        # Verify - no jobs returned, but response structure is valid
        assert len(result["jobs"]) == 0
        assert result["run_id"] == 999999
        assert result["branch"] == "test-branch"

    @patch("github_mcp_server.tools.ci.os.getenv")
    @patch("github_mcp_server.tools.ci.get_github_client")
    def test_get_logs_neither_branch_nor_run_id_raises_error(
        self,
        mock_get_client: Mock,
        mock_getenv: Mock,
    ) -> None:
        """Test that ValueError is raised when neither branch nor run_id provided."""
        # Execute and verify error
        with pytest.raises(ValueError) as exc_info:
            get_ci_logs()

        assert "Either branch or run_id" in str(exc_info.value)

    @patch("github_mcp_server.tools.ci.os.getenv")
    @patch("github_mcp_server.tools.ci.get_github_client")
    def test_get_logs_both_branch_and_run_id_raises_error(
        self,
        mock_get_client: Mock,
        mock_getenv: Mock,
    ) -> None:
        """Test that ValueError is raised when both branch and run_id provided."""
        # Execute and verify error
        with pytest.raises(ValueError) as exc_info:
            get_ci_logs(branch="main", run_id=123456)

        assert "Cannot provide both" in str(exc_info.value)

    @patch("github_mcp_server.tools.ci.os.getenv")
    @patch("github_mcp_server.tools.ci.get_github_client")
    def test_get_logs_invalid_status_raises_error(
        self,
        mock_get_client: Mock,
        mock_getenv: Mock,
    ) -> None:
        """Test that ValueError is raised for invalid status value."""
        # Execute and verify error
        with pytest.raises(ValueError) as exc_info:
            get_ci_logs(branch="main", status="invalid_status")

        assert "Invalid status" in str(exc_info.value)
        assert "failure" in str(exc_info.value)

    @patch("github_mcp_server.tools.ci.os.getenv")
    @patch("github_mcp_server.tools.ci.get_github_client")
    def test_get_logs_no_runs_for_branch_raises_error(
        self,
        mock_get_client: Mock,
        mock_getenv: Mock,
    ) -> None:
        """Test that ValueError is raised when no runs exist for branch."""
        mock_gh = Mock()
        mock_repo = Mock()

        # Return empty list (no runs)
        mock_repo.get_workflow_runs.return_value = []
        mock_gh.get_repo.return_value = mock_repo
        mock_get_client.return_value = mock_gh

        # Execute and verify error
        with pytest.raises(ValueError) as exc_info:
            get_ci_logs(branch="nonexistent-branch")

        assert "No CI runs found" in str(exc_info.value)

    @patch("github_mcp_server.tools.ci.os.getenv")
    @patch("github_mcp_server.tools.ci.get_github_client")
    def test_get_logs_run_id_not_found_raises_error(
        self,
        mock_get_client: Mock,
        mock_getenv: Mock,
    ) -> None:
        """Test that ValueError is raised when run_id not found."""
        mock_gh = Mock()
        mock_repo = Mock()

        # Simulate run not found
        mock_repo.get_workflow_run.side_effect = Exception("Run not found")
        mock_gh.get_repo.return_value = mock_repo
        mock_get_client.return_value = mock_gh

        # Execute and verify error
        with pytest.raises(ValueError) as exc_info:
            get_ci_logs(run_id=99999)

        assert "not found" in str(exc_info.value)

    @patch("github_mcp_server.tools.ci.os.getenv")
    @patch("github_mcp_server.tools.ci.get_github_client")
    def test_get_logs_github_token_not_set_raises_error(
        self,
        mock_get_client: Mock,
        mock_getenv: Mock,
    ) -> None:
        """Test that ValueError is raised when GITHUB_TOKEN not set."""
        mock_gh = Mock()
        mock_repo = Mock()
        mock_run = Mock()
        mock_job = Mock()

        # Configure workflow run and job
        mock_run.id = 123456
        mock_run.status = "completed"
        mock_run.conclusion = "failure"
        mock_run.html_url = "https://github.com/testowner/testrepo/actions/runs/123456"
        mock_run.head_branch = "test-branch"

        mock_job.id = 789
        mock_job.name = "test"
        mock_run.jobs.return_value = [mock_job]

        mock_repo.get_workflow_runs.return_value = [mock_run]
        mock_gh.get_repo.return_value = mock_repo
        mock_get_client.return_value = mock_gh

        # Mock token as None
        mock_getenv.return_value = None

        # Execute and verify error
        with pytest.raises(ValueError) as exc_info:
            get_ci_logs(branch="test-branch")

        assert "GITHUB_TOKEN" in str(exc_info.value)

    @patch("github_mcp_server.tools.ci.os.getenv")
    @patch("github_mcp_server.tools.ci.requests.get")
    @patch("github_mcp_server.tools.ci.get_github_client")
    def test_get_logs_multiple_jobs_with_logs(
        self,
        mock_get_client: Mock,
        mock_requests_get: Mock,
        mock_getenv: Mock,
    ) -> None:
        """Test getting logs for multiple jobs in a single run."""
        mock_gh = Mock()
        mock_repo = Mock()
        mock_run = Mock()
        mock_job1 = Mock()
        mock_job2 = Mock()
        mock_job3 = Mock()

        # Configure workflow run
        mock_run.id = 111111
        mock_run.status = "completed"
        mock_run.conclusion = "failure"
        mock_run.html_url = "https://github.com/testowner/testrepo/actions/runs/111111"
        mock_run.head_branch = "test-branch"

        # Configure multiple jobs
        mock_job1.id = 1
        mock_job1.name = "test-unit"
        mock_job1.status = "completed"
        mock_job1.conclusion = "failure"
        mock_job1.html_url = "https://github.com/testowner/testrepo/actions/runs/111111/jobs/1"

        mock_job2.id = 2
        mock_job2.name = "test-integration"
        mock_job2.status = "completed"
        mock_job2.conclusion = "failure"
        mock_job2.html_url = "https://github.com/testowner/testrepo/actions/runs/111111/jobs/2"

        mock_job3.id = 3
        mock_job3.name = "lint"
        mock_job3.status = "completed"
        mock_job3.conclusion = "failure"
        mock_job3.html_url = "https://github.com/testowner/testrepo/actions/runs/111111/jobs/3"

        mock_run.jobs.return_value = [mock_job1, mock_job2, mock_job3]

        # Setup repository mock
        mock_repo.get_workflow_runs.return_value = [mock_run]
        mock_gh.get_repo.return_value = mock_repo
        mock_get_client.return_value = mock_gh

        # Mock token and HTTP responses
        mock_getenv.return_value = "gh_test_token_12345"
        mock_response1 = Mock()
        mock_response1.status_code = 200
        mock_response1.text = "Unit test error\nFailure in test 1"

        mock_response2 = Mock()
        mock_response2.status_code = 200
        mock_response2.text = "Integration test error\nFailure in test 2"

        mock_response3 = Mock()
        mock_response3.status_code = 200
        mock_response3.text = "Linting error\nFailure in format"

        mock_requests_get.side_effect = [mock_response1, mock_response2, mock_response3]

        # Execute
        result = get_ci_logs(branch="test-branch", status="all")

        # Verify all jobs included
        assert len(result["jobs"]) == 3
        assert result["jobs"][0]["name"] == "test-unit"
        assert result["jobs"][1]["name"] == "test-integration"
        assert result["jobs"][2]["name"] == "lint"

        # Verify each job has unique logs
        assert "Unit test error" in result["jobs"][0]["logs"]
        assert "Integration test error" in result["jobs"][1]["logs"]
        assert "Linting error" in result["jobs"][2]["logs"]

        # Verify requests were made for all jobs
        assert mock_requests_get.call_count == 3

    @patch("github_mcp_server.tools.ci.os.getenv")
    @patch("github_mcp_server.tools.ci.requests.get")
    @patch("github_mcp_server.tools.ci.get_github_client")
    def test_get_logs_custom_owner_repo(
        self,
        mock_get_client: Mock,
        mock_requests_get: Mock,
        mock_getenv: Mock,
    ) -> None:
        """Test getting logs with custom owner and repo parameters."""
        mock_gh = Mock()
        mock_repo = Mock()
        mock_run = Mock()
        mock_job = Mock()

        # Configure workflow run
        mock_run.id = 123456
        mock_run.status = "completed"
        mock_run.conclusion = "failure"
        mock_run.html_url = "https://github.com/testowner/testrepo/actions/runs/123456"
        mock_run.head_branch = "test-branch"

        # Configure job
        mock_job.id = 789
        mock_job.name = "test"
        mock_job.status = "completed"
        mock_job.conclusion = "failure"
        mock_job.html_url = "https://github.com/testowner/testrepo/actions/runs/123456/jobs/789"

        mock_run.jobs.return_value = [mock_job]

        # Setup repository mock
        mock_repo.get_workflow_runs.return_value = [mock_run]
        mock_gh.get_repo.return_value = mock_repo
        mock_get_client.return_value = mock_gh

        # Mock token and HTTP response
        mock_getenv.return_value = "gh_test_token_12345"
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = "Error"
        mock_requests_get.return_value = mock_response

        # Execute
        result = get_ci_logs(
            branch="test-branch",
            owner="testowner",
            repo="testrepo",
            status="failure",
        )

        # Verify custom owner/repo used
        mock_gh.get_repo.assert_called_once_with("testowner/testrepo")
        assert "testowner/testrepo" in mock_requests_get.call_args[0][0]

        # Verify result is valid
        assert isinstance(result, dict)
        assert "jobs" in result

    @patch("github_mcp_server.tools.ci.os.getenv")
    @patch("github_mcp_server.tools.ci.requests.get")
    @patch("github_mcp_server.tools.ci.get_github_client")
    def test_get_logs_response_structure_complete(
        self,
        mock_get_client: Mock,
        mock_requests_get: Mock,
        mock_getenv: Mock,
    ) -> None:
        """Test that complete response structure is returned with all required fields."""
        mock_gh = Mock()
        mock_repo = Mock()
        mock_run = Mock()
        mock_job = Mock()

        # Configure workflow run
        mock_run.id = 123456
        mock_run.status = "completed"
        mock_run.conclusion = "failure"
        mock_run.html_url = "https://github.com/testowner/testrepo/actions/runs/123456"
        mock_run.head_branch = "test-branch"

        # Configure job
        mock_job.id = 789
        mock_job.name = "test"
        mock_job.status = "completed"
        mock_job.conclusion = "failure"
        mock_job.html_url = "https://github.com/testowner/testrepo/actions/runs/123456/jobs/789"

        mock_run.jobs.return_value = [mock_job]

        # Setup repository mock
        mock_repo.get_workflow_runs.return_value = [mock_run]
        mock_gh.get_repo.return_value = mock_repo
        mock_get_client.return_value = mock_gh

        # Mock token and HTTP response
        mock_getenv.return_value = "gh_test_token_12345"
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = "Error logs"
        mock_requests_get.return_value = mock_response

        # Execute
        result = get_ci_logs(branch="test-branch")

        # Verify all required response fields present
        assert "run_id" in result
        assert "run_url" in result
        assert "branch" in result
        assert "status" in result
        assert "conclusion" in result
        assert "jobs" in result

        # Verify all required job fields present
        job = result["jobs"][0]
        assert "job_id" in job
        assert "name" in job
        assert "status" in job
        assert "conclusion" in job
        assert "logs" in job
        assert "log_url" in job

        # Verify types
        assert isinstance(result["run_id"], int)
        assert isinstance(result["run_url"], str)
        assert isinstance(result["branch"], str)
        assert isinstance(result["status"], str)
        assert isinstance(result["conclusion"], str)
        assert isinstance(result["jobs"], list)
        assert isinstance(job["job_id"], int)
        assert isinstance(job["logs"], str)
