"""GitHub pull request operations MCP tools.

Provides MCP tools for creating pull requests with rich, structured content.
"""

import logging
import subprocess
from typing import Any

from ..config.defaults import DEFAULT_REPOSITORY
from ..server import mcp
from ..utils.errors import handle_github_error
from ..utils.formatter import format_pr_body
from ..utils.github_client import get_github_client

logger = logging.getLogger(__name__)


# Validation constants
MAX_TITLE_LENGTH = 256
MAX_BODY_LENGTH = 65536  # GitHub's limit for PR body


def _validate_pr_inputs(
    title: str,
    problem: str,
    solution: str,
    key_changes: str,
    issue: int | None = None,
) -> None:
    """
    Validate pull request input parameters before making API call.

    Raises:
        ValueError: If any parameter fails validation, with a specific message
                   indicating which parameter is invalid and why.
    """
    errors = []

    # Validate title
    if not title or not title.strip():
        errors.append("'title' cannot be empty")
    elif len(title) > MAX_TITLE_LENGTH:
        errors.append(f"'title' exceeds maximum length of {MAX_TITLE_LENGTH} characters")

    # Validate issue number if provided
    if issue is not None and (not isinstance(issue, int) or issue <= 0):
        errors.append("'issue' must be a positive integer")

    # Validate problem description
    if not problem or not problem.strip():
        errors.append("'problem' cannot be empty - describe why this change is needed")

    # Validate solution description
    if not solution or not solution.strip():
        errors.append("'solution' cannot be empty - describe how the change works")

    # Validate key_changes
    if not key_changes or not key_changes.strip():
        errors.append("'key_changes' cannot be empty - list the main changes made")

    # Check combined body length (approximate)
    estimated_body_length = len(problem) + len(solution) + len(key_changes) + 500  # overhead
    if estimated_body_length > MAX_BODY_LENGTH:
        errors.append(
            f"Combined content exceeds maximum PR body length of {MAX_BODY_LENGTH} characters. "
            f"Estimated length: {estimated_body_length}"
        )

    if errors:
        error_list = "\n  - ".join(errors)
        raise ValueError(f"Invalid PR parameters:\n  - {error_list}")


@mcp.tool()
def create_pr_with_content(
    title: str,
    problem: str,
    solution: str,
    key_changes: str,
    issue: int | None = None,
    base: str = "main",
    owner: str = DEFAULT_REPOSITORY.owner,
    repo: str = DEFAULT_REPOSITORY.repo,
) -> dict[str, Any]:
    """Create a GitHub PR with structured content. Auto-detects current branch as head.

    Required content:
    - problem: why this change is needed (2-4 sentences)
    - solution: how it works (4-8 sentences)
    - key_changes: bulleted markdown list of changes

    Optional:
    - issue: GitHub issue number to close (adds "Closes #N" to PR)

    Returns: {pr_number, url, state, head, base, created_at}
    """
    # Validate inputs before making API call
    _validate_pr_inputs(
        title=title,
        problem=problem,
        solution=solution,
        key_changes=key_changes,
        issue=issue,
    )

    try:
        gh = get_github_client()
        repository = gh.get_repo(f"{owner}/{repo}")

        # Get current branch from git
        result = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            capture_output=True,
            text=True,
            check=True,
        )
        branch = result.stdout.strip()

        logger.info(f"Creating PR from branch: {branch} → {base}")

        # Format PR body with structured content
        body = format_pr_body(
            problem=problem,
            solution=solution,
            key_changes=key_changes,
            issue=issue,
            branch=branch,
        )

        # Create PR
        pr = repository.create_pull(title=title, body=body, head=branch, base=base)

        logger.info(f"Created PR #{pr.number}: {title}")

        return {
            "pr_number": pr.number,
            "url": pr.html_url,
            "state": pr.state,
            "head": pr.head.ref,
            "base": pr.base.ref,
            "created_at": pr.created_at.isoformat(),
        }
    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to get current branch: {e}")
        raise Exception(
            "Failed to determine current branch. "
            "Ensure you are in a git repository and on a valid branch."
        ) from e
    except ValueError:
        # Re-raise validation errors as-is with clear message
        raise
    except Exception as e:
        logger.error(f"Failed to create PR: {e}")
        raise handle_github_error(e) from e


@mcp.tool()
def get_pull_request(
    pr_number: int,
    owner: str = DEFAULT_REPOSITORY.owner,
    repo: str = DEFAULT_REPOSITORY.repo,
) -> dict[str, Any]:
    """Get PR details including mergeable status and statistics.

    Returns: {number, title, state, merged, mergeable, mergeable_state, draft,
              head, base, commits, additions, deletions, changed_files,
              created_at, updated_at, merged_at, url}

    mergeable_state: "clean", "dirty", "unstable", "blocked", or "unknown"
    """
    try:
        gh = get_github_client()
        repository = gh.get_repo(f"{owner}/{repo}")

        logger.info(f"Fetching PR #{pr_number} from {owner}/{repo}")

        # Get PR details
        pr = repository.get_pull(pr_number)

        # Format timestamps as ISO 8601
        created_at = pr.created_at.isoformat() if pr.created_at else None
        updated_at = pr.updated_at.isoformat() if pr.updated_at else None
        merged_at = pr.merged_at.isoformat() if pr.merged_at else None

        logger.info(
            f"Retrieved PR #{pr.number}: {pr.title} "
            f"(state={pr.state}, merged={pr.merged}, mergeable={pr.mergeable})"
        )

        return {
            "number": pr.number,
            "title": pr.title,
            "state": pr.state,
            "merged": pr.merged,
            "mergeable": pr.mergeable,
            "mergeable_state": pr.mergeable_state,
            "draft": pr.draft,
            "head": pr.head.ref,
            "base": pr.base.ref,
            "commits": pr.commits,
            "additions": pr.additions,
            "deletions": pr.deletions,
            "changed_files": pr.changed_files,
            "created_at": created_at,
            "updated_at": updated_at,
            "merged_at": merged_at,
            "url": pr.html_url,
        }
    except Exception as e:
        logger.error(f"Failed to get PR #{pr_number}: {e}")
        raise handle_github_error(e) from e


@mcp.tool()
def update_pr(
    pr_number: int,
    title: str | None = None,
    body: str | None = None,
    base: str | None = None,
    state: str | None = None,
    owner: str = DEFAULT_REPOSITORY.owner,
    repo: str = DEFAULT_REPOSITORY.repo,
) -> dict[str, Any]:
    """Update PR metadata. Only provided fields are updated; None values ignored.

    Optional updates:
    - title: new PR title
    - body: new PR description
    - base: change base branch
    - state: "open" or "closed"

    Returns: {number, title, state, updated_fields, url}

    Note: Cannot update merged PRs.
    """
    try:
        # Validate state if provided
        if state is not None and state not in ["open", "closed"]:
            raise ValueError(f"Invalid state '{state}'. Must be 'open' or 'closed'.")

        gh = get_github_client()
        repository = gh.get_repo(f"{owner}/{repo}")

        logger.info(f"Updating PR #{pr_number} in {owner}/{repo}")

        # Get PR
        pr = repository.get_pull(pr_number)

        # Check if PR is merged - can't update merged PRs
        if pr.merged:
            raise Exception(
                f"Cannot update PR #{pr_number}: Pull request has been merged. "
                "Merged pull requests cannot be modified."
            )

        # Build update dict with only non-None values
        updates = {}
        updated_fields = []

        if title is not None:
            updates["title"] = title
            updated_fields.append("title")

        if body is not None:
            updates["body"] = body
            updated_fields.append("body")

        if base is not None:
            updates["base"] = base
            updated_fields.append("base")

        if state is not None:
            updates["state"] = state
            updated_fields.append("state")

        # Only call edit if there are updates
        if updates:
            pr.edit(**updates)
            logger.info(f"Updated PR #{pr_number}: {', '.join(updated_fields)}")
        else:
            logger.info(f"No updates provided for PR #{pr_number}")

        return {
            "number": pr.number,
            "title": pr.title,
            "state": pr.state,
            "updated_fields": updated_fields,
            "url": pr.html_url,
        }

    except ValueError as e:
        # Re-raise validation errors as-is
        logger.error(f"Validation error: {e}")
        raise
    except Exception as e:
        logger.error(f"Failed to update PR #{pr_number}: {e}")
        raise handle_github_error(e) from e


@mcp.tool()
def merge_pr(
    pr_number: int,
    merge_method: str = "squash",
    commit_title: str | None = None,
    commit_message: str | None = None,
    delete_branch: bool = True,
    owner: str = DEFAULT_REPOSITORY.owner,
    repo: str = DEFAULT_REPOSITORY.repo,
) -> dict[str, Any]:
    """Merge a PR after checking mergeable status.

    Options:
    - merge_method: "squash" (default), "merge", or "rebase"
    - commit_title/commit_message: custom merge commit text (squash/merge only)
    - delete_branch: delete head branch after merge (default: True)

    Returns: {merged, sha, message, branch_deleted}
    """
    try:
        # Validate merge_method
        valid_methods = ["merge", "squash", "rebase"]
        if merge_method not in valid_methods:
            raise ValueError(
                f"Invalid merge_method '{merge_method}'. "
                f"Must be one of: {', '.join(valid_methods)}"
            )

        gh = get_github_client()
        repository = gh.get_repo(f"{owner}/{repo}")

        logger.info(f"Attempting to merge PR #{pr_number} with method '{merge_method}'")

        # Get PR details
        pr = repository.get_pull(pr_number)

        # Pre-merge validation: Check if PR is closed
        if pr.state == "closed" and not pr.merged:
            raise Exception(
                f"Cannot merge PR #{pr_number}: Pull request is closed. "
                "Only open pull requests can be merged."
            )

        # Pre-merge validation: Check if already merged
        if pr.merged:
            raise Exception(
                f"Cannot merge PR #{pr_number}: Pull request was already merged at "
                f"{pr.merged_at.isoformat() if pr.merged_at else 'unknown time'}. "
                f"Merge SHA: {pr.merge_commit_sha or 'unknown'}"
            )

        # Pre-merge validation: Check mergeable status
        if pr.mergeable is False:
            # Provide specific error message based on mergeable_state
            state_messages = {
                "blocked": "Blocked by required checks, reviews, or branch protection",
                "dirty": "Merge conflicts must be resolved before merging",
                "behind": "Branch must be updated with base branch before merging",
            }
            error_detail = state_messages.get(
                pr.mergeable_state, f"Pull request is not mergeable (state: {pr.mergeable_state})"
            )
            raise Exception(
                f"Cannot merge PR #{pr_number}: {error_detail}. "
                "Please resolve the issues before attempting to merge."
            )

        # Store head branch name for deletion
        head_branch = pr.head.ref

        # Merge the PR
        merge_result = pr.merge(
            merge_method=merge_method,
            commit_title=commit_title,
            commit_message=commit_message,
        )

        logger.info(f"Successfully merged PR #{pr_number} with SHA {merge_result.sha}")

        # Delete branch if requested
        branch_deleted = False
        if delete_branch:
            try:
                ref = repository.get_git_ref(f"heads/{head_branch}")
                ref.delete()
                branch_deleted = True
                logger.info(f"Deleted head branch '{head_branch}'")
            except Exception as e:
                logger.warning(f"Failed to delete branch '{head_branch}': {e}")
                # Don't fail the merge if branch deletion fails

        return {
            "merged": True,
            "sha": merge_result.sha,
            "message": f"Pull request #{pr_number} successfully merged",
            "branch_deleted": branch_deleted,
        }

    except ValueError as e:
        # Re-raise validation errors as-is
        logger.error(f"Validation error: {e}")
        raise
    except Exception as e:
        logger.error(f"Failed to merge PR #{pr_number}: {e}")
        raise handle_github_error(e) from e


logger.info("PR tools registered: create_pr_with_content, get_pull_request, update_pr, merge_pr")
