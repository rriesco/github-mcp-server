"""GitHub issue operations MCP tools.

Provides MCP tools for creating and retrieving GitHub issues with structured responses.
"""

import logging
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any

from ..config.defaults import DEFAULT_REPOSITORY
from ..server import mcp
from ..utils.errors import handle_github_error
from ..utils.github_client import get_github_client

logger = logging.getLogger(__name__)


def _create_single_issue(
    index: int,
    issue_data: dict[str, Any],
    owner: str,
    repo: str,
) -> dict[str, Any]:
    """Create a single issue (internal helper for batch processing)."""
    try:
        gh = get_github_client()
        repository = gh.get_repo(f"{owner}/{repo}")

        title = issue_data.get("title")
        body = issue_data.get("body", "")
        labels = issue_data.get("labels", [])
        milestone_num = issue_data.get("milestone")
        assignees = issue_data.get("assignees", [])

        if not title:
            raise ValueError("title is required")

        create_args: dict[str, Any] = {"title": title, "body": body}

        if labels:
            create_args["labels"] = labels
        if milestone_num:
            create_args["milestone"] = repository.get_milestone(milestone_num)
        if assignees:
            create_args["assignees"] = assignees

        issue = repository.create_issue(**create_args)
        logger.info(f"Created issue #{issue.number}: {title}")

        return {
            "index": index,
            "success": True,
            "data": {
                "issue_number": issue.number,
                "url": issue.html_url,
                "state": issue.state,
                "title": issue.title,
                "labels": [label.name for label in issue.labels],
                "milestone": issue.milestone.title if issue.milestone else None,
            },
        }
    except Exception as e:
        logger.error(f"Failed to create issue at index {index}: {e}")
        error_info = handle_github_error(e)
        return {"index": index, "success": False, "error": error_info.to_dict()}


@mcp.tool()
def create_issues(
    issues: list[dict[str, Any]],
    owner: str = DEFAULT_REPOSITORY.owner,
    repo: str = DEFAULT_REPOSITORY.repo,
    max_workers: int = 5,
) -> dict[str, Any]:
    """Create GitHub issues (1 or more). Parallel execution for multiple.

    Each issue: {title (required), body, labels, milestone, assignees}

    Options:
    - max_workers: parallel workers (default: 5, max: 10)

    Returns: {total, successful, failed, results: [{index, success, data/error}]}
    """
    start_time = time.time()

    if not issues:
        raise ValueError("issues list cannot be empty")
    if len(issues) > 50:
        raise ValueError("Maximum 50 issues per batch")

    max_workers = min(max(1, max_workers), 10)
    results: list[dict[str, Any]] = []

    # Single issue: run directly, multiple: use thread pool
    if len(issues) == 1:
        results.append(_create_single_issue(0, issues[0], owner, repo))
    else:
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {
                executor.submit(_create_single_issue, i, issue, owner, repo): i
                for i, issue in enumerate(issues)
            }
            for future in as_completed(futures):
                results.append(future.result())

    results.sort(key=lambda r: r["index"])

    successful = sum(1 for r in results if r["success"])
    failed = len(results) - successful

    return {
        "total": len(issues),
        "successful": successful,
        "failed": failed,
        "success_rate": f"{(successful / len(issues) * 100):.1f}%",
        "execution_time_seconds": round(time.time() - start_time, 2),
        "results": results,
    }


@mcp.tool()
def get_issue(
    issue_number: int,
    owner: str = DEFAULT_REPOSITORY.owner,
    repo: str = DEFAULT_REPOSITORY.repo,
) -> dict[str, Any]:
    """Retrieve full GitHub issue details including body content.

    Returns: {number, title, body, state, labels, milestone, created_at, updated_at, url}
    """
    try:
        gh = get_github_client()
        repository = gh.get_repo(f"{owner}/{repo}")

        issue = repository.get_issue(issue_number)

        logger.info(f"Retrieved issue #{issue.number}: {issue.title}")

        return {
            "number": issue.number,
            "title": issue.title,
            "body": issue.body,
            "state": issue.state,
            "labels": [label.name for label in issue.labels],
            "milestone": issue.milestone.title if issue.milestone else None,
            "created_at": issue.created_at.isoformat(),
            "updated_at": issue.updated_at.isoformat(),
            "url": issue.html_url,
        }
    except Exception as e:
        logger.error(f"Failed to get issue #{issue_number}: {e}")
        raise handle_github_error(e)


@mcp.tool()
def list_issues(
    state: str = "open",
    labels: list[str] | None = None,
    milestone: str | None = None,
    assignee: str | None = None,
    sort: str = "created",
    direction: str = "desc",
    limit: int = 30,
    owner: str = DEFAULT_REPOSITORY.owner,
    repo: str = DEFAULT_REPOSITORY.repo,
) -> dict[str, Any]:
    """List and filter GitHub issues with pagination.

    Optional filters:
    - state: "open" (default), "closed", or "all"
    - labels: filter by label names
    - milestone: filter by milestone title (not number)
    - assignee: filter by username, or "none" for unassigned
    - sort: "created" (default), "updated", or "comments"
    - limit: max issues to return (default: 30, max: 100)

    Returns: {total, count, issues: [{number, title, state, labels, milestone, assignee, url}]}
    """
    try:
        gh = get_github_client()
        repository = gh.get_repo(f"{owner}/{repo}")

        # Build filter parameters for PyGithub
        filter_params = {
            "state": state,
            "sort": sort,
            "direction": direction,
        }

        # Add optional filters
        if labels:
            filter_params["labels"] = labels

        if milestone:
            # Find milestone by title
            milestones = repository.get_milestones(state="all")
            milestone_obj = None
            for ms in milestones:
                if ms.title == milestone:
                    milestone_obj = ms
                    break

            if milestone_obj is None:
                # No matching milestone found - return empty results
                logger.warning(f"Milestone '{milestone}' not found in {owner}/{repo}")
                return {
                    "total": 0,
                    "count": 0,
                    "issues": [],
                }

            filter_params["milestone"] = milestone_obj

        if assignee is not None:
            filter_params["assignee"] = assignee

        # Fetch issues with filters
        issues_paginated = repository.get_issues(**filter_params)

        # Convert to list with limit
        issues_list = []
        for issue in issues_paginated:
            if len(issues_list) >= limit:
                break
            # Skip pull requests (GitHub API returns them as issues)
            if issue.pull_request is None:
                issues_list.append(issue)

        logger.info(
            f"Retrieved {len(issues_list)} issues from {owner}/{repo} "
            f"(state={state}, labels={labels}, milestone={milestone}, assignee={assignee})"
        )

        # Format response
        formatted_issues = []
        for issue in issues_list:
            formatted_issues.append(
                {
                    "number": issue.number,
                    "title": issue.title,
                    "state": issue.state,
                    "labels": [label.name for label in issue.labels],
                    "milestone": issue.milestone.title if issue.milestone else None,
                    "assignee": issue.assignee.login if issue.assignee else None,
                    "created_at": issue.created_at.isoformat(),
                    "updated_at": issue.updated_at.isoformat(),
                    "url": issue.html_url,
                }
            )

        return {
            "total": len(formatted_issues),
            "count": len(formatted_issues),
            "issues": formatted_issues,
        }

    except Exception as e:
        logger.error(f"Failed to list issues: {e}")
        raise handle_github_error(e)


@mcp.tool()
def close_issue(
    issue_number: int,
    comment: str | None = None,
    state_reason: str | None = None,
    owner: str = DEFAULT_REPOSITORY.owner,
    repo: str = DEFAULT_REPOSITORY.repo,
) -> dict[str, Any]:
    """Close a GitHub issue with optional comment and reason.

    Optional:
    - comment: add closing comment before closing
    - state_reason: "completed" or "not_planned"

    Returns: {number, state, state_reason, comment_added, url}
    """
    try:
        gh = get_github_client()
        repository = gh.get_repo(f"{owner}/{repo}")

        # Get the issue
        issue = repository.get_issue(issue_number)

        comment_added = False

        # Add comment if provided (before closing)
        if comment:
            issue.create_comment(comment)
            comment_added = True
            logger.info(f"Added closing comment to issue #{issue_number}")

        # Close the issue with optional state_reason
        issue.edit(state="closed", state_reason=state_reason)

        logger.info(
            f"Closed issue #{issue_number}"
            + (f" with state_reason='{state_reason}'" if state_reason else "")
        )

        return {
            "number": issue.number,
            "state": issue.state,
            "state_reason": issue.state_reason if hasattr(issue, "state_reason") else state_reason,
            "comment_added": comment_added,
            "url": issue.html_url,
        }
    except Exception as e:
        logger.error(f"Failed to close issue #{issue_number}: {e}")
        raise handle_github_error(e)


logger.info("Issue tools registered: create_issues, get_issue, list_issues, close_issue")
