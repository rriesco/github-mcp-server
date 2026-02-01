"""GitHub batch operations MCP tools.

Provides MCP tools for performing batch operations on multiple GitHub resources
efficiently with parallel execution and comprehensive error handling.
"""

import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from typing import Any

from ..config.defaults import DEFAULT_REPOSITORY
from ..server import mcp
from ..utils.errors import handle_github_error
from ..utils.github_client import get_github_client

logger = logging.getLogger(__name__)


@dataclass
class BatchOperationResult:
    """Result of a single operation within a batch.

    Attributes:
        index: Position in the original batch request
        success: Whether the operation succeeded
        data: Result data if successful, None if failed
        error: Error information if failed, None if successful
    """

    index: int
    success: bool
    data: dict[str, Any] | None = None
    error: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert result to dictionary format."""
        result: dict[str, Any] = {
            "index": self.index,
            "success": self.success,
        }
        if self.success:
            result["data"] = self.data
        else:
            result["error"] = self.error
        return result


@dataclass
class BatchResponse:
    """Response from a batch operation.

    Attributes:
        total: Total number of operations attempted
        successful: Number of successful operations
        failed: Number of failed operations
        results: List of individual operation results
        execution_time_seconds: Time taken to execute the batch
    """

    total: int
    successful: int
    failed: int
    results: list[BatchOperationResult] = field(default_factory=list)
    execution_time_seconds: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        """Convert response to dictionary format."""
        return {
            "total": self.total,
            "successful": self.successful,
            "failed": self.failed,
            "success_rate": (
                f"{(self.successful / self.total * 100):.1f}%" if self.total > 0 else "0%"
            ),
            "execution_time_seconds": round(self.execution_time_seconds, 2),
            "results": [r.to_dict() for r in self.results],
        }


def _update_single_issue(
    index: int,
    issue_number: int,
    updates: dict[str, Any],
    owner: str,
    repo: str,
) -> BatchOperationResult:
    """
    Update a single issue as part of batch operation.

    Args:
        index: Position in batch
        issue_number: Issue number to update
        updates: Fields to update (title, body, state, labels, milestone, assignees)
        owner: Repository owner
        repo: Repository name

    Returns:
        BatchOperationResult with success/failure information
    """
    try:
        gh = get_github_client()
        repository = gh.get_repo(f"{owner}/{repo}")
        issue = repository.get_issue(issue_number)

        # Update allowed fields
        if "title" in updates:
            issue.edit(title=updates["title"])

        if "body" in updates:
            issue.edit(body=updates["body"])

        if "state" in updates:
            issue.edit(state=updates["state"])

        if "labels" in updates:
            issue.edit(labels=updates["labels"])

        if "milestone" in updates:
            if updates["milestone"] is None:
                issue.edit(milestone=None)
            else:
                milestone_obj = repository.get_milestone(updates["milestone"])
                issue.edit(milestone=milestone_obj)

        if "assignees" in updates:
            issue.edit(assignees=updates["assignees"])

        logger.info(f"Batch[{index}]: Updated issue #{issue_number}")

        return BatchOperationResult(
            index=index,
            success=True,
            data={
                "issue_number": issue.number,
                "url": issue.html_url,
                "updated_fields": list(updates.keys()),
            },
        )

    except Exception as e:
        logger.error(f"Batch[{index}]: Failed to update issue #{issue_number}: {e}")
        error_info = handle_github_error(e)
        return BatchOperationResult(index=index, success=False, error=error_info.to_dict())


@mcp.tool()
def batch_update_issues(
    updates: list[dict[str, Any]],
    owner: str = DEFAULT_REPOSITORY.owner,
    repo: str = DEFAULT_REPOSITORY.repo,
    max_workers: int = 5,
) -> dict[str, Any]:
    """Update multiple GitHub issues in parallel (max 50 per batch).

    Each update object: {issue_number (required), title, body, state, labels, milestone, assignees}
    Note: labels/assignees replace existing (not append).

    Returns: {total, successful, failed, success_rate, execution_time_seconds, results}
    """
    import time

    start_time = time.time()

    # Validate inputs
    if not updates:
        raise ValueError("updates list cannot be empty")

    if len(updates) > 50:
        raise ValueError("Maximum 50 updates per batch (rate limiting protection)")

    # Validate each update has issue_number
    for i, update in enumerate(updates):
        if "issue_number" not in update:
            raise ValueError(f"Update at index {i} missing required 'issue_number' field")

    # Limit max_workers to reasonable range
    max_workers = min(max(1, max_workers), 10)

    logger.info(f"Starting batch update of {len(updates)} issues with {max_workers} workers")

    results: list[BatchOperationResult] = []

    # Execute in parallel using ThreadPoolExecutor
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Submit all tasks
        future_to_index = {
            executor.submit(
                _update_single_issue,
                index,
                update["issue_number"],
                {k: v for k, v in update.items() if k != "issue_number"},
                owner,
                repo,
            ): index
            for index, update in enumerate(updates)
        }

        # Collect results as they complete
        for future in as_completed(future_to_index):
            result = future.result()
            results.append(result)

    # Sort results by original index
    results.sort(key=lambda r: r.index)

    # Calculate statistics
    successful = sum(1 for r in results if r.success)
    failed = sum(1 for r in results if not r.success)
    execution_time = time.time() - start_time

    response = BatchResponse(
        total=len(updates),
        successful=successful,
        failed=failed,
        results=results,
        execution_time_seconds=execution_time,
    )

    logger.info(
        f"Batch update completed: {successful}/{len(updates)} successful "
        f"in {execution_time:.2f}s"
    )

    return response.to_dict()


def _add_labels_to_issue(
    index: int,
    issue_number: int,
    labels: list[str],
    owner: str,
    repo: str,
) -> BatchOperationResult:
    """
    Add labels to a single issue as part of batch operation.

    Args:
        index: Position in batch
        issue_number: Issue number to add labels to
        labels: Label names to add
        owner: Repository owner
        repo: Repository name

    Returns:
        BatchOperationResult with success/failure information
    """
    try:
        gh = get_github_client()
        repository = gh.get_repo(f"{owner}/{repo}")
        issue = repository.get_issue(issue_number)

        # Add labels (preserves existing labels)
        issue.add_to_labels(*labels)

        logger.info(f"Batch[{index}]: Added {len(labels)} labels to issue #{issue_number}")

        return BatchOperationResult(
            index=index,
            success=True,
            data={
                "issue_number": issue.number,
                "added_labels": labels,
                "all_labels": [label.name for label in issue.labels],
            },
        )

    except Exception as e:
        logger.error(f"Batch[{index}]: Failed to add labels to issue #{issue_number}: {e}")
        error_info = handle_github_error(e)
        return BatchOperationResult(index=index, success=False, error=error_info.to_dict())


@mcp.tool()
def batch_add_labels(
    operations: list[dict[str, Any]],
    owner: str = DEFAULT_REPOSITORY.owner,
    repo: str = DEFAULT_REPOSITORY.repo,
    max_workers: int = 5,
) -> dict[str, Any]:
    """Add labels to multiple issues in parallel. Labels are ADDED (not replaced).

    Each operation: {issue_number (required), labels (required)}

    Returns: {total, successful, failed, success_rate, execution_time_seconds, results}
    """
    import time

    start_time = time.time()

    # Validate inputs
    if not operations:
        raise ValueError("operations list cannot be empty")

    if len(operations) > 50:
        raise ValueError("Maximum 50 operations per batch (rate limiting protection)")

    # Validate each operation has required fields
    for i, op in enumerate(operations):
        if "issue_number" not in op:
            raise ValueError(f"Operation at index {i} missing required 'issue_number' field")
        if "labels" not in op:
            raise ValueError(f"Operation at index {i} missing required 'labels' field")
        if not op["labels"]:
            raise ValueError(f"Operation at index {i} has empty 'labels' list")

    # Limit max_workers to reasonable range
    max_workers = min(max(1, max_workers), 10)

    logger.info(
        f"Starting batch label addition for {len(operations)} issues with {max_workers} workers"
    )

    results: list[BatchOperationResult] = []

    # Execute in parallel using ThreadPoolExecutor
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Submit all tasks
        future_to_index = {
            executor.submit(
                _add_labels_to_issue,
                index,
                op["issue_number"],
                op["labels"],
                owner,
                repo,
            ): index
            for index, op in enumerate(operations)
        }

        # Collect results as they complete
        for future in as_completed(future_to_index):
            result = future.result()
            results.append(result)

    # Sort results by original index
    results.sort(key=lambda r: r.index)

    # Calculate statistics
    successful = sum(1 for r in results if r.success)
    failed = sum(1 for r in results if not r.success)
    execution_time = time.time() - start_time

    response = BatchResponse(
        total=len(operations),
        successful=successful,
        failed=failed,
        results=results,
        execution_time_seconds=execution_time,
    )

    logger.info(
        f"Batch label addition completed: {successful}/{len(operations)} successful "
        f"in {execution_time:.2f}s"
    )

    return response.to_dict()


def _link_issue_to_project(
    index: int,
    issue_number: int,
    project_id: str,
    owner: str,
    repo: str,
) -> BatchOperationResult:
    """
    Link a single issue to a project as part of batch operation.

    Args:
        index: Position in batch
        issue_number: Issue number to link
        project_id: Project node ID (e.g., "PVT_kwDOABcD")
        owner: Repository owner
        repo: Repository name

    Returns:
        BatchOperationResult with success/failure information
    """
    try:
        gh = get_github_client()
        repository = gh.get_repo(f"{owner}/{repo}")
        issue = repository.get_issue(issue_number)

        # Use GraphQL to add issue to project
        # Note: PyGithub doesn't have direct project v2 support, so we use GraphQL
        query = """
        mutation($projectId: ID!, $contentId: ID!) {
          addProjectV2ItemById(input: {projectId: $projectId, contentId: $contentId}) {
            item {
              id
            }
          }
        }
        """

        variables = {
            "projectId": project_id,
            "contentId": issue.node_id,
        }

        # Execute GraphQL mutation
        # Note: Accessing PyGithub internal API for GraphQL support
        requester = getattr(gh, "_Github__requester")
        result = requester.requestJsonAndCheck(
            "POST",
            "/graphql",
            input={"query": query, "variables": variables},
        )

        logger.info(f"Batch[{index}]: Linked issue #{issue_number} to project {project_id}")

        return BatchOperationResult(
            index=index,
            success=True,
            data={
                "issue_number": issue.number,
                "project_id": project_id,
                "item_id": result[1]["data"]["addProjectV2ItemById"]["item"]["id"],
            },
        )

    except Exception as e:
        logger.error(f"Batch[{index}]: Failed to link issue #{issue_number} to project: {e}")
        error_info = handle_github_error(e)
        return BatchOperationResult(index=index, success=False, error=error_info.to_dict())


@mcp.tool()
def batch_link_to_project(
    issue_numbers: list[int],
    project_id: str,
    owner: str = DEFAULT_REPOSITORY.owner,
    repo: str = DEFAULT_REPOSITORY.repo,
    max_workers: int = 5,
) -> dict[str, Any]:
    """Link multiple issues to a GitHub Project (v2) board in parallel.

    project_id: Project node ID starting with "PVT_" (from GraphQL API, not project number)
    Requires token with project (write) scope.

    Returns: {total, successful, failed, success_rate, execution_time_seconds, results}
    """
    import time

    start_time = time.time()

    # Validate inputs
    if not issue_numbers:
        raise ValueError("issue_numbers list cannot be empty")

    if len(issue_numbers) > 50:
        raise ValueError("Maximum 50 issues per batch (rate limiting protection)")

    if not project_id or not project_id.startswith("PVT_"):
        raise ValueError("project_id must be a valid GitHub Project node ID (starts with 'PVT_')")

    # Limit max_workers to reasonable range
    max_workers = min(max(1, max_workers), 10)

    logger.info(
        f"Starting batch project linking for {len(issue_numbers)} issues "
        f"to project {project_id} with {max_workers} workers"
    )

    results: list[BatchOperationResult] = []

    # Execute in parallel using ThreadPoolExecutor
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Submit all tasks
        future_to_index = {
            executor.submit(
                _link_issue_to_project,
                index,
                issue_number,
                project_id,
                owner,
                repo,
            ): index
            for index, issue_number in enumerate(issue_numbers)
        }

        # Collect results as they complete
        for future in as_completed(future_to_index):
            result = future.result()
            results.append(result)

    # Sort results by original index
    results.sort(key=lambda r: r.index)

    # Calculate statistics
    successful = sum(1 for r in results if r.success)
    failed = sum(1 for r in results if not r.success)
    execution_time = time.time() - start_time

    response = BatchResponse(
        total=len(issue_numbers),
        successful=successful,
        failed=failed,
        results=results,
        execution_time_seconds=execution_time,
    )

    logger.info(
        f"Batch project linking completed: {successful}/{len(issue_numbers)} successful "
        f"in {execution_time:.2f}s"
    )

    return response.to_dict()


logger.info(
    "Batch operation tools registered: batch_update_issues, "
    "batch_add_labels, batch_link_to_project"
)
