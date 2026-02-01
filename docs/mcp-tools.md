# GitHub MCP Server - Tools Documentation

This document provides comprehensive documentation for all MCP tools provided by the GitHub Manager server.

## Table of Contents

- [Quick Start](#quick-start)
- [Tool Categories](#tool-categories)
  - [Issue Operations](#issue-operations)
  - [Milestone Operations](#milestone-operations)
  - [Batch Operations](#batch-operations)
  - [Pull Request Operations](#pull-request-operations)
  - [CI/CD Operations](#cicd-operations)
- [Common Patterns](#common-patterns)
- [Error Handling](#error-handling)
- [Authentication](#authentication)
- [Performance Guide](#performance-guide)
- [Migration Guide](#migration-guide)
- [Troubleshooting](#troubleshooting)
- [Usage with Claude Code](#usage-with-claude-code)
- [Tool Index](#tool-index)
- [Changelog](#changelog)

---

## Quick Start

Get started with the GitHub MCP Server in 5 minutes:

1. **Configure MCP Server**
   Add to your Claude Code MCP configuration (`.mcp.json` or `~/.config/claude-code/mcp-config.json`):
   ```json
   {
     "mcpServers": {
       "github-manager": {
         "type": "stdio",
         "command": "uvx",
         "args": ["github-mcp-server"],
         "env": {
           "GITHUB_TOKEN": "ghp_your_token_here",
           "GITHUB_OWNER": "your-username",
           "GITHUB_REPO": "your-repo"
         }
       }
     }
   }
   ```

2. **Use from Claude Code**
   The tools are automatically available. Try:
   ```
   "Create an issue titled 'Test Issue' with label 'test' in milestone 1"
   ```

3. **Verify Setup**
   Check that Claude Code can see the tools:
   ```
   "List all available GitHub tools"
   ```

---

## Tool Categories

---

## Issue Operations

### `create_issues`

Create one or more GitHub issues with labels and milestone.

**Parameters:**
- `title` (str, required): Issue title
- `body` (str, required): Issue body in markdown format (200-500 words recommended)
- `labels` (list[str], required): Label names to apply
- `milestone` (int, required): Milestone number
- `owner` (str, optional): Repository owner (uses GITHUB_OWNER env var if set)
- `repo` (str, optional): Repository name (uses GITHUB_REPO env var if set)

**Returns:**
```json
{
  "issue_number": 123,
  "url": "https://github.com/owner/repo/issues/123",
  "state": "open",
  "created_at": "2025-11-12T10:00:00Z",
  "labels": ["type: feature", "priority: high"],
  "milestone": "Phase 1"
}
```

**Example:**
```python
result = create_issues(
    issues=[{
        "title": "[Phase 1.1] Implement data fetcher",
        "body": """## Context
The system needs a robust data fetching layer...

## Implementation Approach
...
    """,
        "labels": ["type: feature", "area: data"],
        "milestone": 7
    }]
)
```

### `get_issue`

Retrieve complete details about a GitHub issue.

**Parameters:**
- `issue_number` (int, required): Issue number to retrieve
- `owner` (str, optional): Repository owner (uses GITHUB_OWNER env var if set)
- `repo` (str, optional): Repository name (uses GITHUB_REPO env var if set)

**Returns:**
```json
{
  "number": 123,
  "title": "[Phase 1.1] Implement data fetcher",
  "body": "## Context\n...",
  "state": "open",
  "labels": ["type: feature"],
  "milestone": "Phase 1",
  "created_at": "2025-11-12T10:00:00Z",
  "updated_at": "2025-11-12T11:00:00Z",
  "url": "https://github.com/owner/repo/issues/123"
}
```

### `list_issues`

List and filter GitHub issues with powerful filtering and sorting capabilities.

**Parameters:**
- `state` (str, optional): Issue state - "open", "closed", or "all" (default: "open")
- `labels` (list[str], optional): List of label names to filter by
- `milestone` (str, optional): Milestone name/title to filter by
- `assignee` (str, optional): GitHub username to filter by, or "none" for unassigned issues
- `sort` (str, optional): Sort field - "created", "updated", or "comments" (default: "created")
- `direction` (str, optional): Sort direction - "asc" or "desc" (default: "desc")
- `limit` (int, optional): Maximum number of issues to return (default: 30, max: 100)
- `owner` (str, optional): Repository owner (uses GITHUB_OWNER env var if set)
- `repo` (str, optional): Repository name (uses GITHUB_REPO env var if set)

**Returns:**
```json
{
  "total": 15,
  "count": 15,
  "issues": [
    {
      "number": 123,
      "title": "[Phase 4] Feature X",
      "state": "open",
      "labels": ["type: feature", "priority: high"],
      "milestone": "Phase 4",
      "assignee": "octocat",
      "created_at": "2025-12-01T10:00:00Z",
      "updated_at": "2025-12-15T14:30:00Z",
      "url": "https://github.com/owner/repo/issues/123"
    }
  ]
}
```

**Examples:**

```python
# List all open issues (default)
result = list_issues()

# List closed issues in a specific milestone
result = list_issues(
    state="closed",
    milestone="Phase 4"
)

# Find unassigned high-priority bugs
result = list_issues(
    labels=["type: bug", "priority: high"],
    assignee="none",
    limit=10
)

# Get recently updated issues
result = list_issues(
    state="all",
    sort="updated",
    direction="desc",
    limit=20
)

# Find all issues assigned to a specific user
result = list_issues(
    assignee="octocat",
    state="open"
)
```

**Use Cases:**
- **Issue Discovery**: Find issues matching specific criteria
- **Status Tracking**: Monitor open/closed issues by milestone
- **Assignment Management**: Find unassigned issues or check user workload
- **Project Planning**: List issues for a specific milestone or phase
- **Triage**: Find high-priority or recently updated issues

**Notes:**
- Returns empty list (not error) when no issues match filters
- Pull requests are automatically excluded from results
- Milestone filter uses milestone title (e.g., "Phase 4"), not number
- Multiple label filters return issues matching ALL specified labels

### `close_issue`

Close a GitHub issue with optional closing comment and state reason.

**Parameters:**
- `issue_number` (int, required): Issue number to close
- `comment` (str, optional): Optional closing comment to add before closing
- `state_reason` (str, optional): State reason - "completed" or "not_planned"
- `owner` (str, optional): Repository owner (uses GITHUB_OWNER env var if set)
- `repo` (str, optional): Repository name (uses GITHUB_REPO env var if set)

**Returns:**
```json
{
  "issue_number": 123,
  "state": "closed",
  "state_reason": "completed",
  "comment_added": true,
  "url": "https://github.com/owner/repo/issues/123"
}
```

**Examples:**

```python
# Close issue without comment
result = close_issue(issue_number=123)
# Returns: state="closed", comment_added=False

# Close with comment
result = close_issue(
    issue_number=123,
    comment="Fixed in PR #456"
)
# Returns: state="closed", comment_added=True

# Close with state reason
result = close_issue(
    issue_number=123,
    state_reason="completed"
)
# Returns: state="closed", state_reason="completed"

# Close with both comment and reason
result = close_issue(
    issue_number=123,
    comment="Implemented in release v2.0",
    state_reason="completed"
)
# Returns: state="closed", state_reason="completed", comment_added=True
```

**Use Cases:**
- **Issue Resolution**: Close issues after completing work
- **Bulk Closure**: Close multiple related issues with consistent messaging
- **State Tracking**: Use state_reason to distinguish completed vs not_planned
- **Audit Trail**: Add closing comments for future reference
- **Automated Workflows**: Close issues when PRs are merged

**State Reasons:**
- `"completed"` - Issue was resolved (work completed)
- `"not_planned"` - Issue closed without resolution (won't fix, duplicate, etc.)
- `None` (default) - No specific reason provided

**Notes:**
- Closing an already-closed issue is a no-op (returns success)
- Comment is added before state change (appears in issue timeline)
- State reason is optional but recommended for clarity
- Use batch_update_issues for closing multiple issues at once

---

## Milestone Operations

Milestone operations enable creating and discovering GitHub milestones for issue organization.

### `create_milestone`

Create a new GitHub milestone with optional due date.

**Parameters:**
- `title` (str, required): Milestone title
- `description` (str, optional): Milestone description in markdown format
- `due_date` (str | None, optional): Due date in ISO 8601 format (e.g., "2025-12-31T23:59:59Z")
- `state` (str, optional): Milestone state - "open" or "closed" (default: "open")
- `owner` (str, optional): Repository owner (uses GITHUB_OWNER env var if set)
- `repo` (str, optional): Repository name (uses GITHUB_REPO env var if set)

**Returns:**
```json
{
  "number": 8,
  "title": "Phase 4: Essential Tools",
  "description": "Implement 8 essential MCP tools for GitHub operations",
  "state": "open",
  "due_on": "2025-12-31T23:59:59",
  "url": "https://github.com/owner/repo/milestone/8"
}
```

**Example:**
```python
# Create milestone without due date
result = create_milestone(
    title="Phase 4: Essential Tools",
    description="Implement 8 essential MCP tools for GitHub operations"
)

# Create milestone with due date
result = create_milestone(
    title="Q1 2026 Release",
    description="All features planned for Q1 2026",
    due_date="2026-03-31T23:59:59Z"
)

# Create closed milestone
result = create_milestone(
    title="Archived Phase",
    description="Completed work from previous phase",
    state="closed"
)
```

**Use Cases:**
- **Project Planning**: Create milestones for development phases
- **Release Management**: Set milestones with due dates for releases
- **Issue Organization**: Create milestones before batch creating issues
- **Sprint Planning**: Create milestones for agile sprints

**Notes:**
- GitHub allows duplicate milestone titles (creates separate milestones)
- `due_date` must be in ISO 8601 format with timezone (Z suffix or +00:00)
- Invalid due_date format raises `GitHubAPIError` with helpful message
- Returns milestone number needed for `create_issue` operations

### `list_milestones`

List repository milestones with filtering and sorting options.

**Parameters:**
- `state` (str, optional): Milestone state - "open", "closed", or "all" (default: "open")
- `sort` (str, optional): Sort field - "due_on" or "completeness" (default: "due_on")
- `direction` (str, optional): Sort direction - "asc" or "desc" (default: "asc")
- `owner` (str, optional): Repository owner (uses GITHUB_OWNER env var if set)
- `repo` (str, optional): Repository name (uses GITHUB_REPO env var if set)

**Returns:**
```json
{
  "total": 8,
  "milestones": [
    {
      "number": 7,
      "title": "GitHub Manager MCP Migration",
      "state": "open",
      "open_issues": 5,
      "closed_issues": 103,
      "due_on": null,
      "url": "https://github.com/owner/repo/milestone/7"
    },
    {
      "number": 8,
      "title": "Phase 4: Essential Tools",
      "state": "open",
      "open_issues": 12,
      "closed_issues": 0,
      "due_on": "2026-01-31T23:59:59",
      "url": "https://github.com/owner/repo/milestone/8"
    }
  ]
}
```

**Example:**
```python
# List all open milestones (default)
result = list_milestones()

# List all milestones (open + closed)
result = list_milestones(state="all")

# List milestones sorted by completeness (most complete first)
result = list_milestones(
    state="all",
    sort="completeness",
    direction="desc"
)

# Find milestone number for issue creation
milestones = list_milestones()
phase_4 = [m for m in milestones["milestones"] if "Phase 4" in m["title"]][0]
milestone_number = phase_4["number"]  # Use this in create_issue
```

**Use Cases:**
- **Milestone Discovery**: Find milestone number for issue creation
- **Progress Tracking**: Monitor open vs closed issues per milestone
- **Release Planning**: View milestones with due dates
- **Cleanup**: Find old closed milestones
- **Status Reports**: List milestones by completion percentage

**Notes:**
- Returns empty list (not error) when no milestones exist
- `due_on` is `null` if milestone has no due date
- Sort by "completeness" orders by percentage of closed issues
- Sort by "due_on" places milestones without due dates last

**Common Pattern: Create Issue with Milestone**
```python
# Step 1: Find milestone number
milestones = list_milestones()
milestone = next(m for m in milestones["milestones"] if m["title"] == "Phase 4")

# Step 2: Use milestone number in create_issues
issue = create_issues(
    issues=[{
        "title": "Implement feature X",
        "body": "...",
        "labels": ["type: feature"],
        "milestone": milestone["number"]
    }]
)
```

---

## Batch Operations

Batch operations allow you to perform multiple GitHub actions in a single call with parallel execution for improved performance.

### Performance Characteristics

- **5x+ faster** than sequential operations for batches of 10+ items
- **Parallel execution** using ThreadPoolExecutor
- **Partial failure handling** - some operations can succeed while others fail
- **Rate limit protection** - maximum 50 items per batch
- **Configurable concurrency** - max_workers parameter (1-10)

### `batch_create_issues`

Create multiple GitHub issues in parallel.

**Parameters:**
- `issues` (list[dict], required): List of issue objects
  - Each object contains: `title`, `body`, `labels`, `milestone`, `assignees` (optional)
- `owner` (str, optional): Repository owner (uses GITHUB_OWNER env var if set)
- `repo` (str, optional): Repository name (uses GITHUB_REPO env var if set)
- `max_workers` (int, optional): Maximum parallel workers (default: 5, max: 10)

**Returns:**
```json
{
  "total": 10,
  "successful": 9,
  "failed": 1,
  "success_rate": "90.0%",
  "execution_time_seconds": 2.3,
  "results": [
    {
      "index": 0,
      "success": true,
      "data": {
        "issue_number": 123,
        "url": "https://github.com/owner/repo/issues/123",
        "state": "open",
        "title": "Issue title",
        "labels": ["test"],
        "milestone": "Phase 1"
      }
    },
    {
      "index": 1,
      "success": false,
      "error": {
        "error": true,
        "code": "VALIDATION_FAILED",
        "message": "Validation failed",
        "details": {...},
        "suggestions": [...]
      }
    }
  ]
}
```

**Example:**
```python
result = batch_create_issues(
    issues=[
        {
            "title": "[Phase 1.1] Implement data fetcher",
            "body": "## Context\n...",
            "labels": ["type: feature", "area: data"],
            "milestone": 7,
        },
        {
            "title": "[Phase 1.2] Add caching layer",
            "body": "## Context\n...",
            "labels": ["type: feature", "priority: high"],
            "milestone": 7,
        },
    ],
    max_workers=5
)

print(f"Created {result['successful']}/{result['total']} issues")
print(f"Execution time: {result['execution_time_seconds']}s")

# Access individual results
for res in result["results"]:
    if res["success"]:
        print(f"Created issue #{res['data']['issue_number']}")
    else:
        print(f"Failed: {res['error']['message']}")
```

**Performance Benchmark:**
- 10 issues: ~2-3 seconds (vs ~5 seconds sequential)
- 20 issues: ~4-5 seconds (vs ~10 seconds sequential)
- Speedup: **5-10x** for typical batches

### `batch_update_issues`

Update multiple GitHub issues in parallel.

**Parameters:**
- `updates` (list[dict], required): List of update objects
  - Each object must contain `issue_number` (int)
  - Optional fields: `title`, `body`, `state`, `labels`, `milestone`, `assignees`
- `owner` (str, optional): Repository owner (uses GITHUB_OWNER env var if set)
- `repo` (str, optional): Repository name (uses GITHUB_REPO env var if set)
- `max_workers` (int, optional): Maximum parallel workers (default: 5, max: 10)

**Returns:** Same format as `batch_create_issues`

**Example:**
```python
result = batch_update_issues(
    updates=[
        {
            "issue_number": 123,
            "state": "closed",
            "labels": ["completed"],
        },
        {
            "issue_number": 124,
            "title": "Updated: New feature name",
            "labels": ["in-progress", "priority: high"],
        },
        {
            "issue_number": 125,
            "milestone": 8,  # Move to next milestone
        },
    ]
)

print(f"Updated {result['successful']}/{result['total']} issues")
```

### `batch_add_labels`

Add labels to multiple GitHub issues in parallel.

**Parameters:**
- `operations` (list[dict], required): List of operation objects
  - Each object must contain: `issue_number` (int), `labels` (list[str])
- `owner` (str, optional): Repository owner (uses GITHUB_OWNER env var if set)
- `repo` (str, optional): Repository name (uses GITHUB_REPO env var if set)
- `max_workers` (int, optional): Maximum parallel workers (default: 5, max: 10)

**Returns:** Same format as `batch_create_issues` with additional fields:
```json
{
  "results": [
    {
      "index": 0,
      "success": true,
      "data": {
        "issue_number": 123,
        "added_labels": ["priority: high", "needs-review"],
        "all_labels": ["test", "priority: high", "needs-review"]
      }
    }
  ]
}
```

**Notes:**
- Labels are **added** to existing labels (not replaced)
- Use `batch_update_issues` with `labels` field to replace all labels

**Example:**
```python
# Add "needs-review" and "priority: high" to issues 123-125
result = batch_add_labels(
    operations=[
        {
            "issue_number": 123,
            "labels": ["needs-review", "priority: high"],
        },
        {
            "issue_number": 124,
            "labels": ["needs-review", "priority: high"],
        },
        {
            "issue_number": 125,
            "labels": ["needs-review", "priority: high"],
        },
    ]
)

# Verify labels were added
for res in result["results"]:
    if res["success"]:
        print(f"Issue #{res['data']['issue_number']}: {res['data']['all_labels']}")
```

### `batch_link_to_project`

Link multiple GitHub issues to a project board in parallel.

**Parameters:**
- `issue_numbers` (list[int], required): List of issue numbers to link
- `project_id` (str, required): GitHub Project node ID (format: "PVT_xxx")
- `owner` (str, optional): Repository owner (uses GITHUB_OWNER env var if set)
- `repo` (str, optional): Repository name (uses GITHUB_REPO env var if set)
- `max_workers` (int, optional): Maximum parallel workers (default: 5, max: 10)

**Returns:** Same format as `batch_create_issues` with additional field:
```json
{
  "results": [
    {
      "index": 0,
      "success": true,
      "data": {
        "issue_number": 123,
        "project_id": "PVT_kwDOABcDEFG",
        "item_id": "PVTI_lADOABcDEFG"
      }
    }
  ]
}
```

**Finding Project ID:**

The project ID is the **node_id** from GitHub's GraphQL API, not the project number.

To find it:
1. Use GitHub GraphQL Explorer: https://docs.github.com/en/graphql/overview/explorer
2. Query:
   ```graphql
   {
     repository(owner: "owner", name: "repo") {
       projectsV2(first: 10) {
         nodes {
           id
           title
           number
         }
       }
     }
   }
   ```
3. Look for the `id` field (format: `PVT_kwDOABcDEFG`)

**Example:**
```python
# Link issues 101-110 to project
result = batch_link_to_project(
    issue_numbers=[101, 102, 103, 104, 105, 106, 107, 108, 109, 110],
    project_id="PVT_kwDOABcDEFG",
)

print(f"Linked {result['successful']}/{result['total']} issues to project")
```

**Requirements:**
- GitHub token must have `project` (write) scope
- User must have write access to the project

---

## Batch Operations - Best Practices

### Error Handling

All batch operations return detailed error information for failed operations:

```python
result = batch_create_issues(issues=[...])

# Check overall success
if result["success_rate"] == "100.0%":
    print("All operations succeeded!")
else:
    # Handle partial failures
    for res in result["results"]:
        if not res["success"]:
            error = res["error"]
            print(f"Operation {res['index']} failed:")
            print(f"  Code: {error['code']}")
            print(f"  Message: {error['message']}")
            print(f"  Suggestions: {error['suggestions']}")
```

### Concurrency Tuning

The `max_workers` parameter controls parallel execution:

- **1 worker**: Sequential execution (slowest, safest)
- **3 workers**: Conservative parallelism (good for testing)
- **5 workers** (default): Balanced performance and API rate limits
- **10 workers** (max): Maximum speed (may hit rate limits with large batches)

**Recommendation**: Use default (5) unless you have specific needs.

### Rate Limiting

- Maximum **50 items per batch** to prevent rate limit issues
- For larger operations, split into multiple batches
- Monitor GitHub API rate limits: https://docs.github.com/en/rest/overview/resources-in-the-rest-api#rate-limiting

Example for large batches:
```python
def create_large_batch(all_issues):
    """Create issues in chunks of 50."""
    chunk_size = 50
    all_results = []

    for i in range(0, len(all_issues), chunk_size):
        chunk = all_issues[i:i+chunk_size]
        result = batch_create_issues(issues=chunk)
        all_results.append(result)

        print(f"Batch {i//chunk_size + 1}: {result['successful']}/{result['total']}")

    return all_results
```

### Performance Comparison

**Sequential vs Batch (10 operations):**

| Method | Time | Throughput |
|--------|------|------------|
| Sequential | ~5.0s | 2 ops/sec |
| Batch (workers=1) | ~5.0s | 2 ops/sec |
| Batch (workers=3) | ~2.5s | 4 ops/sec |
| Batch (workers=5) | ~1.5s | 6.7 ops/sec |
| Batch (workers=10) | ~1.2s | 8.3 ops/sec |

**Speedup: 4-5x** with default settings

---

## Pull Request Operations

### `create_pr_with_content`

Create a pull request with structured, formatted content.

**Parameters:**
- `title` (str, required): PR title (e.g., "feat: implement core MCP tools")
- `issue` (int, required): Issue number this PR closes
- `problem` (str, required): Problem description - why this change is needed (2-4 sentences)
- `solution` (str, required): Solution description - how the change works (4-8 sentences)
- `key_changes` (str, required): Key changes as bulleted markdown list
- `base` (str, optional): Base branch to merge into (default: "main")
- `owner` (str, optional): Repository owner (uses GITHUB_OWNER env var if set)
- `repo` (str, optional): Repository name (uses GITHUB_REPO env var if set)

**Returns:**
```json
{
  "pr_number": 108,
  "url": "https://github.com/owner/repo/pull/108",
  "state": "open",
  "head": "issue-42-add-caching",
  "base": "main",
  "created_at": "2025-11-12T11:45:00Z"
}
```

**Special Features:**
- Auto-detects current git branch as head branch
- Formats body with standard sections (Summary, Problem, Solution, Key Changes)
- Automatically adds "Closes #N" for issue linking
- Includes Claude Code attribution footer

**Example:**
```python
result = create_pr_with_content(
    title="feat: implement Redis caching for API responses",
    issue=42,
    problem="Current implementation makes repeated API calls for same data within short time windows, causing rate limiting and slow response times.",
    solution="Implemented Redis-based caching layer with TTL-based expiration. Cache keys use symbol+date_range hash. Automatic cache invalidation on data updates.",
    key_changes="""
- Added RedisCacheManager with connection pooling
- Implemented cache_key generation with SHA256 hashing
- Added TTL configuration (default: 1 hour for OHLCV data)
- Updated DataFetcher to check cache before API calls
- Added cache invalidation on manual data refresh
    """
)
```

### `get_pull_request`

Retrieve comprehensive details about a pull request including mergeable status and statistics.

**Parameters:**
- `pr_number` (int, required): Pull request number to retrieve
- `owner` (str, optional): Repository owner (uses GITHUB_OWNER env var if set)
- `repo` (str, optional): Repository name (uses GITHUB_REPO env var if set)

**Returns:**
```json
{
  "number": 42,
  "title": "feat: implement feature X",
  "state": "open",
  "merged": false,
  "mergeable": true,
  "mergeable_state": "clean",
  "draft": false,
  "head": "feature-branch",
  "base": "main",
  "commits": 5,
  "additions": 234,
  "deletions": 67,
  "changed_files": 12,
  "created_at": "2025-12-15T10:00:00",
  "updated_at": "2025-12-20T14:30:00",
  "merged_at": null,
  "url": "https://github.com/owner/repo/pull/42"
}
```

**Mergeable States:**
- `clean` - No conflicts, ready to merge
- `dirty` - Merge conflicts present
- `unstable` - Checks failing
- `blocked` - Blocked by required reviews or checks
- `unknown` - GitHub still calculating

**Example:**
```python
# Check if PR is mergeable
result = get_pull_request(pr_number=42)

if result["mergeable"] and result["mergeable_state"] == "clean":
    print(f"PR #{result['number']} is ready to merge!")
    print(f"Stats: +{result['additions']} -{result['deletions']} in {result['changed_files']} files")
else:
    print(f"PR cannot be merged: {result['mergeable_state']}")
```

**Use Cases:**
- **Pre-merge validation**: Check if PR can be safely merged
- **Code review metrics**: Analyze size and scope of changes
- **Merge decision workflows**: Automate merge decisions based on status
- **PR inspection**: Get complete PR details without visiting GitHub UI

### `update_pr`

Update pull request metadata (title, body, base branch, or state).

**Parameters:**
- `pr_number` (int, required): Pull request number to update
- `title` (str, optional): New PR title
- `body` (str, optional): New PR body/description
- `base` (str, optional): New base branch
- `state` (str, optional): New state - "open" or "closed"
- `owner` (str, optional): Repository owner (uses GITHUB_OWNER env var if set)
- `repo` (str, optional): Repository name (uses GITHUB_REPO env var if set)

**Returns:**
```json
{
  "number": 42,
  "title": "Updated title",
  "state": "open",
  "updated_fields": ["title", "body"],
  "url": "https://github.com/owner/repo/pull/42"
}
```

**Special Features:**
- **Partial updates**: Only provided fields are updated; None values ignored
- **Merged PR protection**: Prevents updating merged PRs (raises error)
- **State validation**: Validates state is "open" or "closed"
- **Field tracking**: Returns list of fields that were actually updated

**Examples:**

```python
# Update title only
result = update_pr(
    pr_number=42,
    title="fix: corrected bug description"
)
# Returns: updated_fields=["title"]

# Update multiple fields at once
result = update_pr(
    pr_number=42,
    title="Updated title",
    body="New description with more details",
    state="closed"
)
# Returns: updated_fields=["title", "body", "state"]

# Change base branch (e.g., retarget to different release)
result = update_pr(
    pr_number=42,
    base="release/v2.0"
)
# Returns: updated_fields=["base"]

# Close a PR without merging
result = update_pr(
    pr_number=42,
    state="closed"
)
# Returns: updated_fields=["state"]

# Reopen a closed PR
result = update_pr(
    pr_number=42,
    state="open"
)
# Returns: updated_fields=["state"]
```

**Use Cases:**
- **Title corrections**: Fix typos or update PR titles for clarity
- **Description updates**: Add more context or update implementation notes
- **Base branch changes**: Retarget PR to different release branch
- **PR maintenance**: Close stale PRs or reopen for additional work
- **Bulk PR management**: Update multiple PRs with consistent messaging

**Error Handling:**
```python
# Attempting to update merged PR raises error
try:
    update_pr(pr_number=123, title="New title")
except Exception as e:
    # Error: "Cannot update PR #123: Pull request has been merged"
    pass

# Invalid state value raises ValueError
try:
    update_pr(pr_number=42, state="invalid")
except ValueError as e:
    # Error: "Invalid state 'invalid'. Must be 'open' or 'closed'."
    pass
```

**Notes:**
- Merged PRs cannot be updated (GitHub API limitation)
- Only specified fields are modified; other fields remain unchanged
- Returns empty `updated_fields` list if no parameters provided
- State changes don't affect merge status (use merge API for that)

### `merge_pr`

Merge a pull request with configurable merge method and optional branch deletion.

**Parameters:**
- `pr_number` (int, required): Pull request number to merge
- `merge_method` (str, optional): Merge method - "merge", "squash", or "rebase" (default: "squash")
- `commit_title` (str, optional): Optional custom commit title for squash/merge
- `commit_message` (str, optional): Optional custom commit message for squash/merge
- `delete_branch` (bool, optional): Whether to delete head branch after merge (default: True)
- `owner` (str, optional): Repository owner (uses GITHUB_OWNER env var if set)
- `repo` (str, optional): Repository name (uses GITHUB_REPO env var if set)

**Returns:**
```json
{
  "merged": true,
  "sha": "abc123def456...",
  "message": "Pull request #42 successfully merged",
  "branch_deleted": true
}
```

**Special Features:**
- **Pre-merge validation**: Checks PR is mergeable before attempting merge
- **Multiple merge methods**: Supports merge commit, squash, and rebase
- **Custom commit messages**: Optional custom title and message for squash/merge commits
- **Automatic branch cleanup**: Optionally deletes head branch after successful merge
- **Graceful failure handling**: Merge succeeds even if branch deletion fails (for protected branches)

**Merge Methods:**
- `"squash"` (default) - Combines all commits into one commit on base branch
- `"merge"` - Creates merge commit preserving full history
- `"rebase"` - Rebases and merges commits individually for linear history

**Examples:**

```python
# Merge with default squash method
result = merge_pr(pr_number=42)
# Returns: merged=True, branch_deleted=True

# Merge with merge commit method, keep branch
result = merge_pr(
    pr_number=42,
    merge_method="merge",
    commit_title="Merge feature X into main",
    delete_branch=False
)
# Returns: merged=True, branch_deleted=False

# Merge with rebase for linear history
result = merge_pr(
    pr_number=42,
    merge_method="rebase"
)
# Returns: merged=True (creates linear history)

# Merge with custom commit message
result = merge_pr(
    pr_number=42,
    merge_method="squash",
    commit_title="feat: implement Redis caching",
    commit_message="Closes #42\n\nImplemented caching layer with 80% reduction in API calls"
)
# Returns: merged=True with custom commit message
```

**Pre-Merge Validation:**

The tool automatically validates before merging and provides specific error messages:

```python
# PR with merge conflicts
try:
    merge_pr(pr_number=42)
except Exception as e:
    # Error: "Cannot merge PR #42: Merge conflicts must be resolved before merging"
    pass

# PR blocked by required checks
try:
    merge_pr(pr_number=42)
except Exception as e:
    # Error: "Cannot merge PR #42: Merge is blocked by required checks, reviews, or branch protection rules"
    pass

# PR behind base branch
try:
    merge_pr(pr_number=42)
except Exception as e:
    # Error: "Cannot merge PR #42: Branch must be updated with base branch before merging"
    pass

# Already merged PR
try:
    merge_pr(pr_number=42)
except Exception as e:
    # Error: "Cannot merge PR #42: Pull request was already merged at 2025-12-20T10:00:00Z"
    pass

# Closed PR
try:
    merge_pr(pr_number=42)
except Exception as e:
    # Error: "Cannot merge PR #42: Pull request is closed. Only open pull requests can be merged."
    pass

# Invalid merge method
try:
    merge_pr(pr_number=42, merge_method="invalid")
except ValueError as e:
    # Error: "Invalid merge_method 'invalid'. Must be one of: merge, squash, rebase"
    pass
```

**Use Cases:**
- **Automated PR workflows**: Complete end-to-end PR lifecycle (create → CI → merge)
- **Batch merging**: Merge multiple PRs after CI passes
- **Release automation**: Merge release PRs with specific commit messages
- **Dependency updates**: Auto-merge dependabot PRs after validation
- **Branch cleanup**: Automatically delete feature branches after merge

**Workflow Pattern: Complete PR Lifecycle**

```python
# Step 1: Create PR
pr = create_pr_with_content(
    title="feat: implement feature X",
    issue=42,
    problem="...",
    solution="...",
    key_changes="..."
)

# Step 2: Wait for CI
ci_status = check_ci_status(branch=pr["head"])
while ci_status["overall_status"] != "success":
    time.sleep(30)
    ci_status = check_ci_status(branch=pr["head"])

# Step 3: Check PR is mergeable
pr_status = get_pull_request(pr_number=pr["pr_number"])
if pr_status["mergeable"] and pr_status["mergeable_state"] == "clean":
    # Step 4: Merge
    result = merge_pr(
        pr_number=pr["pr_number"],
        merge_method="squash"
    )
    print(f"✅ Merged PR #{pr['pr_number']}: {result['sha']}")
else:
    print(f"❌ PR not mergeable: {pr_status['mergeable_state']}")
```

**Error States:**

| Mergeable State | Error Message | Action Required |
|----------------|---------------|-----------------|
| `blocked` | Merge is blocked by required checks, reviews, or branch protection rules | Wait for reviews, fix failing checks |
| `dirty` | Merge conflicts must be resolved before merging | Resolve conflicts locally |
| `behind` | Branch must be updated with base branch before merging | Update branch with base (rebase/merge) |
| Already merged | Pull request was already merged at [timestamp] | No action (already completed) |
| Closed | Pull request is closed. Only open pull requests can be merged | Reopen PR if needed |

**Notes:**
- Validates PR is mergeable before attempting merge (prevents API errors)
- Returns merge commit SHA for verification and tracking
- Branch deletion is graceful - merge succeeds even if deletion fails
- Custom commit messages only apply to "squash" and "merge" methods (ignored for "rebase")
- Requires write access to repository and PR must pass all required checks

---

## CI/CD Operations

### `check_ci_status`

Check CI workflow status for a branch.

**Parameters:**
- `branch` (str, required): Branch name to check
- `owner` (str, optional): Repository owner (uses GITHUB_OWNER env var if set)
- `repo` (str, optional): Repository name (uses GITHUB_REPO env var if set)

**Returns:**
```json
{
  "branch": "feature-branch",
  "workflows": [
    {
      "name": "CI",
      "status": "completed",
      "conclusion": "success",
      "url": "https://github.com/owner/repo/actions/runs/12345"
    }
  ],
  "overall_status": "success",
  "all_passing": true
}
```

**Example:**
```python
# Check CI status for a branch
status = check_ci_status(branch="issue-239-implement-get-ci-logs")
print(f"CI Status: {status['overall_status']}")
print(f"All Passing: {status['all_passing']}")
```

---

### `get_ci_logs`

Get CI workflow logs for debugging failed jobs.

Fetches logs from GitHub Actions workflow runs for debugging failed CI. Supports filtering by branch, run ID, job name, and status. Returns truncated logs (tail behavior) for easy debugging.

**Parameters:**
- `branch` (str, optional): Branch name to get logs for (mutually exclusive with run_id)
- `run_id` (int, optional): Workflow run ID to get logs for (mutually exclusive with branch)
- `job_name` (str, optional): Job name to filter by (case-insensitive partial match, e.g., "test", "lint")
- `status` (str, optional): Job status filter - "failure" (default), "success", or "all"
- `max_lines` (int, optional): Maximum number of log lines to return, tail behavior (default: 200)
- `owner` (str, optional): Repository owner (uses GITHUB_OWNER env var if set)
- `repo` (str, optional): Repository name (uses GITHUB_REPO env var if set)

**Returns:**
```json
{
  "run_id": 123456,
  "run_url": "https://github.com/owner/repo/actions/runs/123456",
  "branch": "feature-branch",
  "status": "completed",
  "conclusion": "failure",
  "jobs": [
    {
      "job_id": 789,
      "name": "test",
      "status": "completed",
      "conclusion": "failure",
      "logs": "... (last 200 lines of logs) ...",
      "log_url": "https://github.com/owner/repo/actions/runs/123456/job/789"
    }
  ]
}
```

**Examples:**

```python
# Get logs for failed jobs on a branch
result = get_ci_logs(branch="issue-239-implement-get-ci-logs")
for job in result["jobs"]:
    print(f"Job: {job['name']}")
    print(f"Status: {job['conclusion']}")
    print(f"Logs:\n{job['logs']}")
    print(f"Full logs: {job['log_url']}")

# Get logs for specific run by ID
result = get_ci_logs(run_id=123456, status="all")
print(f"Found {len(result['jobs'])} jobs")

# Filter by job name
result = get_ci_logs(branch="main", job_name="test", status="failure")
# Returns only jobs with "test" in their name that failed

# Get more log lines for detailed debugging
result = get_ci_logs(branch="feature-branch", max_lines=500)
# Returns last 500 lines instead of default 200

# Get all job logs (success and failure)
result = get_ci_logs(branch="feature-branch", status="all")
# Returns logs for all jobs regardless of conclusion
```

**Use Cases:**
- **Debugging Failed CI**: Get error logs when CI fails
- **Test Failure Analysis**: See which tests failed and why
- **Build Error Investigation**: Debug compilation or linting errors
- **Performance Analysis**: Review logs for successful runs
- **CI Optimization**: Identify slow jobs by analyzing successful run logs

**Notes:**
- Either `branch` or `run_id` must be provided (mutually exclusive)
- Logs are truncated to last `max_lines` (tail behavior) - use `log_url` for full logs
- Logs unavailable (HTTP 404) returns message "Logs not available"
- Network errors are handled gracefully with error messages in logs field
- Job name filtering is case-insensitive and matches partial names

**Replaces:**
- `github-manager/get_ci_logs.py` (112 lines)
- `github-manager/get_specific_run_logs.py` (66 lines)

---

## Common Patterns

### Pattern 1: Bulk Issue Creation from Planning Document

When you have a planning document with multiple tasks to convert into issues:

```python
# Read planning document, extract tasks
tasks = parse_planning_doc("phase-2-plan.md")

# Create issues in batch
results = batch_create_issues(
    issues=[{
        "title": task["title"],
        "body": task["description"],
        "labels": task["labels"],
        "milestone": 7
    } for task in tasks],
    max_workers=5
)

print(f"Created {results['success_count']}/{len(tasks)} issues")
```

### Pattern 2: Progressive Issue Updates

Update issues as work progresses:

```python
# Update multiple issues with status changes
updates = [
    {"issue_number": 42, "state": "closed"},
    {"issue_number": 43, "labels": ["in-progress", "priority: high"]},
    {"issue_number": 44, "milestone": 8}
]

results = batch_update_issues(updates=updates)
```

### Pattern 3: Automated PR Workflow

Check CI status before marking PR ready:

```python
# Check CI status
ci_status = check_ci_status(branch="feature-branch")

if ci_status["all_passing"]:
    # CI passed - ready to review
    print("✅ All CI checks passing")
    # Remove draft status, add ready-for-review label
else:
    print("❌ CI failing:", ci_status["workflows"])
```

### Pattern 4: Project Board Management

Link issues to project boards after creation:

```python
# Create issues first
issue_results = batch_create_issues(issues=issue_list)

# Extract successfully created issue numbers
issue_numbers = [r["issue_number"] for r in issue_results["results"] if r["success"]]

# Link to project board
link_results = batch_link_to_project(
    project_id="PVT_xxx",
    issue_numbers=issue_numbers
)
```

### Pattern 5: Label Management Across Issues

Apply consistent labeling across related issues:

```python
# Get all open issues in milestone
issues = list_issues(milestone="Phase 1", state="open")

# Add priority labels
batch_add_labels(
    updates=[{
        "issue_number": issue["number"],
        "labels": ["priority: high", "needs-review"]
    } for issue in issues],
    mode="add"  # Preserves existing labels
)
```

---

## Error Handling

All tools use structured error responses via `GitHubAPIError`:

```json
{
  "error": true,
  "code": "RESOURCE_NOT_FOUND",
  "message": "Issue #999 not found",
  "details": {"status": 404},
  "suggestions": [
    "Verify the issue number",
    "Check repository access"
  ]
}
```

**Common Error Codes:**
- `RESOURCE_NOT_FOUND` (404): Resource doesn't exist
- `UNAUTHORIZED` (401): Invalid or expired token
- `FORBIDDEN` (403): Insufficient permissions
- `VALIDATION_FAILED` (422): Invalid parameters
- `GITHUB_API_ERROR`: General API error

---

## Authentication

All tools require a valid GitHub Personal Access Token (PAT) with appropriate scopes.

**Required Scopes:**
- `repo` - Full repository access (for issues, PRs)
- `project` - Project board access (for batch_link_to_project)
- `workflow` - Workflow access (for CI operations)

**Setup:**
Configure `GITHUB_TOKEN` in your `.mcp.json` environment configuration:
```json
{
  "env": {
    "GITHUB_TOKEN": "ghp_your_token_here"
  }
}
```

---

## Performance Guide

### Batch vs Sequential Operations

**When to use batch operations:**
- Creating/updating 3+ items → Use batch (2-5x faster)
- Single item operations → Use individual tools (simpler)

**Performance Characteristics:**

| Operation | Single | Batch (5 workers) | Speedup |
|-----------|--------|-------------------|---------|
| Create 10 issues | ~10s | ~2s | 5x |
| Update 20 issues | ~20s | ~4s | 5x |
| Add labels to 15 issues | ~15s | ~3s | 5x |

### Optimal Concurrency

**Recommended `max_workers` settings:**
- **1-10 items**: 3 workers (balance speed vs API load)
- **10-30 items**: 5 workers (optimal for most cases)
- **30-50 items**: 10 workers (maximum parallelism)
- **50+ items**: Split into multiple batches of 50

### GitHub API Rate Limits

- **Authenticated**: 5,000 requests/hour
- **Search API**: 30 requests/minute
- **GraphQL API** (projects): 5,000 points/hour

**Monitoring rate limits:**
```python
# Rate limit info is logged automatically
# Check remaining: gh.get_rate_limit()
```

### Best Practices

1. **Use batch operations for bulk work** - 5x faster
2. **Keep batch size ≤ 50 items** - Prevents timeouts
3. **Handle partial failures** - Some operations can succeed while others fail
4. **Monitor rate limits** - Tool logs rate limit consumption
5. **Reuse connections** - PyGithub handles connection pooling automatically

---

## Migration Guide

### From Python Scripts to MCP Tools

**Before (Python scripts):**
```bash
uv run python github-manager/create_issues.py owner repo issues.json
uv run python github-manager/complete_pr_workflow.py --title "..." --issue 42
uv run python github-manager/check_ci_status.py branch-name
```

**After (MCP Tools via Claude Code):**
```
"Create issues from the tasks in planning.md file"
"Create a PR for issue #42 with title 'feat: implement feature'"
"Check CI status for feature-branch"
```

### Migration Mapping

| Python Script | MCP Tool | Notes |
|---------------|----------|-------|
| `create_issues.py` | `batch_create_issues` | Handles JSON parsing automatically |
| `get_issue_details.py` | `get_issue` | Returns formatted details |
| `complete_pr_workflow.py` | `create_pr_with_content` | Simplified workflow |
| `check_ci_status.py` | `check_ci_status` | Same functionality |
| `link_issues_to_project.py` | `batch_link_to_project` | Batch support added |
| `commit_changes.py` + `push_branch.py` | (not MCP tools) | Use git commands directly |

### Advantages of MCP Tools

1. **Natural language interface** - No need to remember exact CLI arguments
2. **Context-aware** - Claude Code understands your repository context
3. **Error recovery** - Claude can fix issues and retry automatically
4. **Batch operations built-in** - 5x performance improvement
5. **No manual JSON editing** - Claude generates issue JSON from descriptions

### When to Still Use Python Scripts

- **CI/CD pipelines** - Scripts are better for automation
- **Complex git operations** - Git commands not available as MCP tools
- **Script-based workflows** - When human interaction isn't needed

---

## Troubleshooting

### Issue: "UNAUTHORIZED" error

**Symptoms:**
```json
{"error": true, "code": "UNAUTHORIZED", "message": "Bad credentials"}
```

**Solutions:**
1. Check `GITHUB_TOKEN` is configured in your `.mcp.json` file
2. Verify token is set correctly (starts with `ghp_`)
3. Regenerate token at: https://github.com/settings/tokens
4. Ensure token has required scopes: `repo`, `project`, `workflow`
5. Restart MCP server after updating configuration

### Issue: "RESOURCE_NOT_FOUND" for milestone

**Symptoms:**
```json
{"error": true, "code": "RESOURCE_NOT_FOUND", "message": "Milestone not found"}
```

**Solutions:**
1. **Use milestone NUMBER, not title** - e.g., `7` not `"Phase 1"`
2. Check milestone exists: Visit `github.com/owner/repo/milestones`
3. Get milestone number from URL: `.../milestones/7` → use `7`
4. List milestones: Use GitHub web UI or API

### Issue: Batch operations timing out

**Symptoms:**
```
Operation timeout after 60 seconds
```

**Solutions:**
1. **Reduce batch size** - Split 100 items into 2 batches of 50
2. **Decrease max_workers** - Try 3 instead of 10
3. **Check network connectivity** - Slow connection causes timeouts
4. **Verify API rate limits** - May be hitting rate limits

### Issue: Partial failures in batch operations

**Symptoms:**
```json
{
  "success_count": 8,
  "failure_count": 2,
  "results": [...]
}
```

**This is NORMAL behavior** - Batch operations continue even if some items fail.

**Solutions:**
1. **Check `results` array** - Identify which items failed
2. **Read error messages** - Each failure has specific error details
3. **Retry failed items** - Extract failed items and retry
4. **Fix issues** - Common: invalid labels, wrong milestone number

### Issue: "VALIDATION_FAILED" errors

**Symptoms:**
```json
{"error": true, "code": "VALIDATION_FAILED", "message": "Validation Failed"}
```

**Common causes:**
1. **Empty title** - Issue title cannot be empty
2. **Invalid labels** - Label doesn't exist in repository
3. **Invalid milestone** - Milestone number doesn't exist
4. **Title too long** - Maximum 256 characters
5. **Too many labels** - Maximum 100 labels per issue

### Issue: Rate limit exceeded

**Symptoms:**
```
API rate limit exceeded
```

**Solutions:**
1. **Wait for rate limit reset** - Limits reset every hour
2. **Use batch operations** - More efficient (fewer API calls)
3. **Check rate limit status** - Logs show remaining requests
4. **Upgrade to GitHub Pro** - Higher rate limits (10,000/hour)

### Issue: Project linking fails

**Symptoms:**
```json
{"error": true, "message": "Could not resolve to a node with the global id"}
```

**Solutions:**
1. **Use correct project ID format** - Must be `PVT_xxx` (GraphQL node ID)
2. **Find project ID**:
   - Visit project board URL
   - Use browser dev tools → Network tab
   - Look for GraphQL queries containing `projectV2` → Find `id` field
3. **Check token scopes** - Ensure `project` scope is enabled
4. **Verify project exists** - Project may have been deleted

### Issue: CI status not updating

**Symptoms:**
```json
{"all_passing": false, "workflows": [{"status": "in_progress"}]}
```

**Solutions:**
1. **Wait for CI to complete** - Workflows take time to run
2. **Check GitHub Actions** - Visit `github.com/owner/repo/actions`
3. **Verify workflow file** - Ensure `.github/workflows/*.yml` exists
4. **Check branch name** - Ensure exact match (case-sensitive)

### Issue: Tools not visible in Claude Code

**Symptoms:**
- Claude says "I don't have access to that tool"
- MCP tools not listed

**Solutions:**
1. **Check MCP server is running** - Should see startup logs
2. **Verify Claude Code configuration** - Check `claude_desktop_config.json`
3. **Restart Claude Code** - Tools loaded at startup
4. **Check server logs** - Look for errors in startup
5. **Verify Python environment** - `uv run` should work

### Getting Help

If issues persist:
1. Check server logs in console output
2. Enable debug logging: Set `LOG_LEVEL=DEBUG` in your `.mcp.json` env configuration
3. Test with individual tools first before batch operations
4. Verify against GitHub API directly: `curl -H "Authorization: token YOUR_TOKEN" https://api.github.com/user`
5. Check the project repository for known issues and solutions

---

## Usage with Claude Code

These tools are automatically available when the GitHub MCP server is configured in Claude Code.

**Example conversation:**
```
User: Create 10 issues for Phase 2 tasks

Claude: I'll use the batch_create_issues tool to create them efficiently.
[Uses batch_create_issues with 10 issue objects]
Result: Created 10/10 issues successfully in 2.1 seconds
```

---

## Tool Index

Quick reference for all available tools:

### Issue Management
- [`create_issues`](#create_issues) - Create one or more issues
- [`get_issue`](#get_issue) - Retrieve issue details
- [`list_issues`](#list_issues) - List and filter issues with advanced queries
- [`close_issue`](#close_issue) - Close an issue with optional comment and state reason

### Milestone Management
- [`create_milestone`](#create_milestone) - Create a new milestone
- [`list_milestones`](#list_milestones) - List and filter milestones

### Pull Requests
- [`create_pr_with_content`](#create_pr_with_content) - Create PR with structured content
- [`get_pull_request`](#get_pull_request) - Retrieve PR details and mergeable status
- [`update_pr`](#update_pr) - Update PR metadata (title, body, base, state)
- [`merge_pr`](#merge_pr) - Merge PR with configurable merge method and branch deletion

### CI/CD
- [`check_ci_status`](#check_ci_status) - Check workflow status for a branch
- [`get_ci_logs`](#get_ci_logs) - Get CI workflow logs for debugging failed jobs

### Batch Operations
- [`batch_create_issues`](#batch_create_issues) - Create multiple issues in parallel
- [`batch_update_issues`](#batch_update_issues) - Update multiple issues in parallel
- [`batch_add_labels`](#batch_add_labels) - Add/set labels for multiple issues
- [`batch_link_to_project`](#batch_link_to_project) - Link issues to project board

### Tool Count
**Total**: 16 tools across 5 categories (4 issue + 2 milestone + 4 PR + 2 CI + 4 batch)

### By Use Case

**Creating Content:**
- `create_issues`, `create_milestone`, `create_pr_with_content`

**Reading Information:**
- `get_issue`, `list_issues`, `list_milestones`, `check_ci_status`

**Updating Content:**
- Bulk only: `batch_update_issues`, `batch_add_labels`

**Project Management:**
- `create_milestone`, `list_milestones`, `batch_link_to_project`

---

## Changelog

### Version 1.6.0 (Phase 4 Complete) ✅
- **Phase 4 Complete**: All 16 tools implemented and tested
- Added `close_issue` tool for issue closure with optional comment and state reason
- Added `get_ci_logs` tool for debugging failed CI jobs
- Comprehensive test suite with >95% coverage
- Complete documentation for all tools
- End-to-end workflow validation complete
- Tool breakdown: 4 issue + 2 milestone + 4 PR + 2 CI + 4 batch operations
- Replaces 8+ Python scripts with native MCP tools

### Version 1.5.0 (Phase 4.6)
- Added `merge_pr` tool for merging pull requests
- Support for three merge methods: squash (default), merge commit, rebase
- Pre-merge validation with specific error messages for unmergeable states
- Optional branch deletion after successful merge
- Custom commit title and message support for squash/merge methods
- Graceful failure handling (merge succeeds even if branch deletion fails)
- Completes PR lifecycle automation: create → CI → merge
- Enables end-to-end PR workflows without manual intervention

### Version 1.4.0 (Phase 4.5)
- Added `get_pull_request` tool for PR inspection and merge validation
- Added `update_pr` tool for PR metadata updates (title, body, base, state)
- Support for partial PR updates (only specified fields modified)
- Merged PR protection (prevents updating merged PRs)
- State validation for PR state changes
- Enables PR maintenance and corrections without manual GitHub UI interaction

### Version 1.3.0 (Phase 4.2)
- Added `create_milestone` tool for milestone creation
- Added `list_milestones` tool for milestone discovery
- Support for milestone filtering by state (open/closed/all)
- Milestone sorting by due_on date or completeness
- ISO 8601 due date support with validation
- Enables seamless milestone selection for issue creation workflows

### Version 1.2.0 (Phase 4.1)
- Added `list_issues` tool for powerful issue discovery and filtering
- Support for filtering by state, labels, milestone, and assignee
- Advanced sorting capabilities (by created, updated, comments)
- Pagination support with configurable limits

### Version 1.1.0 (Phase 3.1)
- Added `batch_create_issues` tool
- Added `batch_update_issues` tool
- Added `batch_add_labels` tool
- Added `batch_link_to_project` tool
- Performance: 5x+ speedup for bulk operations
- Comprehensive error handling for partial failures

### Version 1.0.0 (Phase 1)
- Initial release
- Basic issue operations (`create_issue`, `get_issue`)
- Pull request operations
- CI status checking
