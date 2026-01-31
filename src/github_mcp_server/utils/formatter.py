"""Response formatting utilities for MCP tools.

Provides functions to format structured data into markdown and other formats
for consistent tool responses.
"""


def format_pr_body(
    problem: str,
    solution: str,
    key_changes: str,
    branch: str,
    issue: int | None = None,
) -> str:
    """Format a PR body with structured content.

    Args:
        problem: Why this change is needed (2-4 sentences)
        solution: How the solution works (4-8 sentences)
        key_changes: Bulleted markdown list of changes
        branch: Branch name
        issue: Optional issue number this PR closes

    Returns:
        Formatted markdown string for the PR body
    """
    # Build summary section
    if issue:
        summary = f"Closes #{issue}"
        closes_line = f"- **Closes**: #{issue}"
    else:
        summary = "Internal improvement"
        closes_line = ""

    # Build technical details
    tech_details = f"- **Branch**: `{branch}`"
    if closes_line:
        tech_details += f"\n{closes_line}"

    return f"""## Summary

{summary}

## Problem

{problem}

## Solution

{solution}

## Key Changes

{key_changes}

## Technical Details

{tech_details}

---
🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>"""
