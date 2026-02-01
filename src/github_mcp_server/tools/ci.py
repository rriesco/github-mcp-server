"""GitHub CI operations MCP tools.

Provides MCP tools for checking CI workflow status and results.
"""

import logging
import os
from typing import Any

import requests

from ..config.defaults import DEFAULT_REPOSITORY
from ..server import mcp
from ..utils.errors import handle_github_error
from ..utils.github_client import get_github_client

logger = logging.getLogger(__name__)


@mcp.tool()
def check_ci_status(
    branch: str,
    owner: str = DEFAULT_REPOSITORY.owner,
    repo: str = DEFAULT_REPOSITORY.repo,
) -> dict[str, Any]:
    """Check CI workflow status for a branch. Returns overall and per-workflow status.

    Returns: {overall_status, overall_conclusion, branch, workflows: [{name, status, conclusion, url, jobs}]}

    If no CI runs found, returns status="no_runs".
    """
    try:
        gh = get_github_client()
        repository = gh.get_repo(f"{owner}/{repo}")

        # Get all workflow runs for branch
        # PyGithub's get_workflow_runs() doesn't filter by branch directly,
        # so we get all runs and filter
        all_runs = repository.get_workflow_runs()
        runs = [run for run in all_runs if run.head_branch == branch]

        if not runs:
            logger.info(f"No CI runs found for branch: {branch}")
            return {
                "status": "no_runs",
                "overall_status": "no_runs",
                "overall_conclusion": None,
                "message": f"No CI runs found for branch: {branch}",
                "branch": branch,
                "workflows": [],
            }

        # Group runs by workflow_id and get the latest run for each workflow
        workflows_latest: dict[int, Any] = {}
        for run in runs:
            workflow_id = run.workflow_id
            if workflow_id not in workflows_latest:
                workflows_latest[workflow_id] = run
            # runs are already ordered by created_at desc, so first one is latest

        logger.info(f"Found {len(workflows_latest)} workflows for branch: {branch}")

        # Build workflow details list
        workflows_list = []
        for workflow_id, latest_run in workflows_latest.items():
            # Get workflow name
            try:
                workflow = repository.get_workflow(workflow_id)
                workflow_name = workflow.name
            except Exception:
                workflow_name = f"Workflow {workflow_id}"

            # Get jobs for this run
            jobs_list = []
            try:
                jobs = latest_run.jobs()
                for job in jobs:
                    jobs_list.append(
                        {
                            "name": job.name,
                            "status": job.status,
                            "conclusion": job.conclusion,
                            "url": job.html_url,
                        }
                    )
            except Exception as job_error:
                logger.warning(f"Could not fetch jobs for workflow {workflow_name}: {job_error}")
                jobs_list = []

            workflows_list.append(
                {
                    "workflow_id": workflow_id,
                    "name": workflow_name,
                    "status": latest_run.status,
                    "conclusion": latest_run.conclusion,
                    "url": latest_run.html_url,
                    "created_at": latest_run.created_at.isoformat(),
                    "updated_at": latest_run.updated_at.isoformat(),
                    "jobs": jobs_list,
                }
            )

        # Calculate overall status and conclusion
        # Overall status: "completed" only if all are completed, else the most severe
        statuses = [w["status"] for w in workflows_list]
        if all(s == "completed" for s in statuses):
            overall_status = "completed"
        elif any(s == "in_progress" for s in statuses):
            overall_status = "in_progress"
        elif any(s == "queued" for s in statuses):
            overall_status = "queued"
        else:
            overall_status = statuses[0] if statuses else "unknown"

        # Overall conclusion: "success" only if all succeeded, else "failure" if any failed
        conclusions = [w["conclusion"] for w in workflows_list if w["conclusion"] is not None]
        if not conclusions:
            overall_conclusion = None
        elif any(c == "failure" for c in conclusions):
            overall_conclusion = "failure"
        elif any(c == "cancelled" for c in conclusions):
            overall_conclusion = "cancelled"
        elif all(c == "success" for c in conclusions):
            overall_conclusion = "success"
        else:
            overall_conclusion = conclusions[0]

        logger.info(f"CI status for {branch}: {overall_status}/{overall_conclusion}")

        return {
            "status": overall_status,  # Keep for backward compatibility
            "conclusion": overall_conclusion,  # Keep for backward compatibility
            "overall_status": overall_status,
            "overall_conclusion": overall_conclusion,
            "branch": branch,
            "workflows": workflows_list,
            "total_workflows": len(workflows_list),
        }
    except Exception as e:
        logger.error(f"Failed to check CI status for {branch}: {e}")
        raise handle_github_error(e)


@mcp.tool()
def get_ci_logs(
    branch: str | None = None,
    run_id: int | None = None,
    job_name: str | None = None,
    status: str = "failure",
    max_lines: int = 200,
    owner: str = DEFAULT_REPOSITORY.owner,
    repo: str = DEFAULT_REPOSITORY.repo,
) -> dict[str, Any]:
    """Get CI workflow logs for debugging failed jobs.

    Provide either branch OR run_id (not both).

    Optional filters:
    - job_name: filter by job name (e.g., "test", "lint")
    - status: "failure" (default), "success", or "all"
    - max_lines: tail N lines of logs (default: 200)

    Returns: {run_id, run_url, branch, status, conclusion, jobs: [{job_id, name, status, conclusion, logs, log_url}]}
    """
    try:
        # Validate parameters
        if branch is None and run_id is None:
            raise ValueError("Either branch or run_id must be provided")
        if branch is not None and run_id is not None:
            raise ValueError("Cannot provide both branch and run_id")

        # Validate status parameter
        valid_statuses = ["failure", "success", "all"]
        if status not in valid_statuses:
            raise ValueError(
                f"Invalid status: {status}. Must be one of: {', '.join(valid_statuses)}"
            )

        gh = get_github_client()
        repository = gh.get_repo(f"{owner}/{repo}")

        # Get workflow run
        if run_id is not None:
            # Get run by ID
            try:
                workflow_run = repository.get_workflow_run(run_id)
                logger.info(f"Retrieved workflow run {run_id}")
            except Exception as e:
                logger.error(f"Failed to get workflow run {run_id}: {e}")
                raise ValueError(f"Workflow run {run_id} not found") from e
        else:
            # Get latest run for branch (reuse logic from check_ci_status)
            all_runs = repository.get_workflow_runs()
            runs = [run for run in all_runs if run.head_branch == branch]

            if len(runs) == 0:
                logger.info(f"No CI runs found for branch: {branch}")
                raise ValueError(f"No CI runs found for branch: {branch}")

            workflow_run = runs[0]
            logger.info(f"Retrieved latest workflow run for branch {branch}")

        # Get jobs for the run
        jobs = workflow_run.jobs()

        # Filter jobs
        filtered_jobs = []
        for job in jobs:
            # Filter by job name if provided
            if job_name and job_name.lower() not in job.name.lower():
                continue

            # Filter by status
            if status == "failure" and job.conclusion != "failure":
                continue
            elif status == "success" and job.conclusion != "success":
                continue
            # "all" means no filtering by conclusion

            filtered_jobs.append(job)

        logger.info(
            f"Found {len(filtered_jobs)} jobs matching filters "
            f"(job_name={job_name}, status={status})"
        )

        # Get token for authenticated requests
        token = os.getenv("GITHUB_TOKEN")
        if not token:
            raise ValueError("GITHUB_TOKEN environment variable not set")

        # Fetch logs for each job
        jobs_with_logs = []
        for job in filtered_jobs:
            # Download logs using GitHub API
            log_url = f"https://api.github.com/repos/{owner}/{repo}/actions/jobs/{job.id}/logs"
            headers = {
                "Authorization": f"token {token}",
                "Accept": "application/vnd.github.v3+json",
            }

            try:
                response = requests.get(log_url, headers=headers, allow_redirects=True, timeout=30)
                if response.status_code == 200:
                    full_logs = response.text
                    # Truncate to last max_lines (tail behavior)
                    log_lines = full_logs.split("\n")
                    truncated_logs = "\n".join(log_lines[-max_lines:])
                    logger.debug(f"Downloaded {len(log_lines)} lines of logs for job {job.id}")
                else:
                    truncated_logs = f"Logs not available (HTTP {response.status_code})"
                    logger.warning(
                        f"Failed to download logs for job {job.id}: {response.status_code}"
                    )
            except requests.exceptions.RequestException as e:
                truncated_logs = f"Error downloading logs: {str(e)}"
                logger.error(f"Request error downloading logs for job {job.id}: {e}")

            jobs_with_logs.append(
                {
                    "job_id": job.id,
                    "name": job.name,
                    "status": job.status,
                    "conclusion": job.conclusion,
                    "logs": truncated_logs,
                    "log_url": job.html_url,
                }
            )

        return {
            "run_id": workflow_run.id,
            "run_url": workflow_run.html_url,
            "branch": workflow_run.head_branch,
            "status": workflow_run.status,
            "conclusion": workflow_run.conclusion,
            "jobs": jobs_with_logs,
        }

    except ValueError:
        # Re-raise validation errors without wrapping
        raise
    except Exception as e:
        logger.error(f"Failed to get CI logs: {e}")
        raise handle_github_error(e)


logger.info("CI tools registered: check_ci_status, get_ci_logs")
