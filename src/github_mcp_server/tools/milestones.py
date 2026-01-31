"""GitHub milestone operations MCP tools.

Provides MCP tools for creating and listing GitHub milestones with structured responses.
"""

import logging
from datetime import datetime
from typing import Any

from ..config.defaults import DEFAULT_REPOSITORY
from ..server import mcp
from ..utils.errors import handle_github_error
from ..utils.github_client import get_github_client

logger = logging.getLogger(__name__)


@mcp.tool()
def create_milestone(
    title: str,
    description: str = "",
    due_date: str | None = None,
    state: str = "open",
    owner: str = DEFAULT_REPOSITORY.owner,
    repo: str = DEFAULT_REPOSITORY.repo,
) -> dict[str, Any]:
    """Create a GitHub milestone.

    Optional:
    - description: markdown description
    - due_date: ISO 8601 format (e.g., "2025-12-31T23:59:59Z")
    - state: "open" (default) or "closed"

    Returns: {number, title, description, state, due_on, url}
    """
    try:
        gh = get_github_client()
        repository = gh.get_repo(f"{owner}/{repo}")

        # Parse due_date if provided
        due_on = None
        if due_date:
            try:
                # Parse ISO 8601 format
                due_on = datetime.fromisoformat(due_date.replace("Z", "+00:00"))
            except ValueError as e:
                logger.error(f"Invalid due_date format: {due_date}")
                raise ValueError(
                    f"Invalid ISO 8601 date format: {due_date}. "
                    f"Expected format: YYYY-MM-DDTHH:MM:SSZ (e.g., 2025-12-31T23:59:59Z)"
                ) from e

        # Create milestone
        create_kwargs = {
            "title": title,
            "state": state,
            "description": description,
        }
        if due_on:
            create_kwargs["due_on"] = due_on

        milestone = repository.create_milestone(**create_kwargs)

        logger.info(f"Created milestone #{milestone.number}: {title}")

        return {
            "number": milestone.number,
            "title": milestone.title,
            "description": milestone.description or "",
            "state": milestone.state,
            "due_on": milestone.due_on.isoformat() if milestone.due_on else None,
            "url": milestone.html_url,
        }
    except Exception as e:
        logger.error(f"Failed to create milestone: {e}")
        raise handle_github_error(e)


@mcp.tool()
def list_milestones(
    state: str = "open",
    sort: str = "due_on",
    direction: str = "asc",
    owner: str = DEFAULT_REPOSITORY.owner,
    repo: str = DEFAULT_REPOSITORY.repo,
) -> dict[str, Any]:
    """List repository milestones with filtering and sorting.

    Options:
    - state: "open" (default), "closed", or "all"
    - sort: "due_on" (default) or "completeness"
    - direction: "asc" (default) or "desc"

    Returns: {total, milestones: [{number, title, state, open_issues, closed_issues, due_on, url}]}
    """
    try:
        gh = get_github_client()
        repository = gh.get_repo(f"{owner}/{repo}")

        # Fetch milestones with filters
        milestones_paginated = repository.get_milestones(
            state=state, sort=sort, direction=direction
        )

        # Convert to list
        milestones_list = list(milestones_paginated)

        logger.info(
            f"Retrieved {len(milestones_list)} milestones from {owner}/{repo} "
            f"(state={state}, sort={sort}, direction={direction})"
        )

        # Format response
        formatted_milestones = []
        for milestone in milestones_list:
            formatted_milestones.append(
                {
                    "number": milestone.number,
                    "title": milestone.title,
                    "state": milestone.state,
                    "open_issues": milestone.open_issues,
                    "closed_issues": milestone.closed_issues,
                    "due_on": (milestone.due_on.isoformat() if milestone.due_on else None),
                    "url": milestone.html_url,
                }
            )

        return {
            "total": len(formatted_milestones),
            "milestones": formatted_milestones,
        }

    except Exception as e:
        logger.error(f"Failed to list milestones: {e}")
        raise handle_github_error(e)


logger.info("Milestone tools registered: create_milestone, list_milestones")
