# GitHub MCP Server

Python MCP (Model Context Protocol) server for GitHub operations, providing native tool integration with Claude Code and other MCP clients.

## Features

- **16 GitHub Tools**: Issues, PRs, CI status, milestones, and batch operations
- **Native MCP Integration**: Works seamlessly with Claude Code
- **Structured Responses**: Type-safe, well-formatted tool outputs
- **Batch Operations**: Parallel execution for bulk operations
- **Environment-Based Config**: Configure default repository via environment variables

## Installation

### From PyPI

```bash
pip install github-mcp-server
# or with uv
uvx github-mcp-server
```

### From Source

```bash
git clone https://github.com/rriesco/github-mcp-server.git
cd github-mcp-server
uv sync
```

## Configuration

### Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `GITHUB_TOKEN` | Yes | GitHub Personal Access Token with `repo` scope |
| `GITHUB_OWNER` | No | Default repository owner for all operations |
| `GITHUB_REPO` | No | Default repository name for all operations |

### Claude Code Configuration

Add to your MCP configuration (`~/.config/claude-code/mcp-config.json`):

```json
{
  "mcpServers": {
    "github-manager": {
      "type": "stdio",
      "command": "uvx",
      "args": ["github-mcp-server"],
      "env": {
        "GITHUB_TOKEN": "${GITHUB_TOKEN}",
        "GITHUB_OWNER": "your-username",
        "GITHUB_REPO": "your-repo"
      }
    }
  }
}
```

### Getting a GitHub Token

1. Go to https://github.com/settings/tokens
2. Click "Generate new token (classic)"
3. Select scope: `repo` (full repository access)
4. Copy the generated token

## Available Tools

### Issue Operations

| Tool | Description |
|------|-------------|
| `create_issues` | Create one or more issues (parallel execution for multiple) |
| `get_issue` | Get full issue details including body |
| `list_issues` | Query issues with filtering (state, labels, milestone, assignee) |
| `close_issue` | Close an issue with optional comment |

### Pull Request Operations

| Tool | Description |
|------|-------------|
| `create_pr_with_content` | Create PR with structured content (problem, solution, changes) |
| `get_pull_request` | Get PR details including mergeable status |
| `update_pr` | Update PR title, body, base branch, or state |
| `merge_pr` | Merge PR with method selection (squash/merge/rebase) |

### CI/CD Operations

| Tool | Description |
|------|-------------|
| `check_ci_status` | Check workflow run status for a branch |
| `get_ci_logs` | Get CI logs for debugging failed jobs |

### Batch Operations

| Tool | Description |
|------|-------------|
| `batch_update_issues` | Update multiple issues in parallel |
| `batch_add_labels` | Add labels to multiple issues |
| `batch_link_to_project` | Link issues to GitHub Project (v2) |

### Milestone Operations

| Tool | Description |
|------|-------------|
| `create_milestone` | Create a milestone with optional due date |
| `list_milestones` | List milestones with filtering |

## Usage Examples

### Create an Issue

```python
result = create_issues(
    issues=[{
        "title": "Implement feature X",
        "body": "## Description\n\nDetails here...",
        "labels": ["enhancement"],
        "milestone": 1
    }],
    owner="your-username",
    repo="your-repo"
)
```

### Check CI Status

```python
result = check_ci_status(
    branch="feature-branch",
    owner="your-username",
    repo="your-repo"
)
```

### Create a PR

```python
result = create_pr_with_content(
    title="feat: add new feature",
    problem="Current behavior lacks X functionality",
    solution="Implement X using approach Y",
    key_changes="- Added X component\n- Updated Y module",
    issue=42,  # Optional: links to issue #42
    owner="your-username",
    repo="your-repo"
)
```

## Development

### Prerequisites

- Python >= 3.10
- uv (recommended) or pip
- GitHub Personal Access Token

### Setup

```bash
git clone https://github.com/rriesco/github-mcp-server.git
cd github-mcp-server
uv sync
```

### Running Tests

```bash
# Unit tests only (fast)
uv run pytest -m "not integration" -v

# Integration tests (requires GITHUB_TOKEN, TEST_OWNER, TEST_REPO)
uv run pytest -m integration -v

# All tests with coverage
uv run pytest --cov=src --cov-report=term-missing
```

### Type Checking

```bash
uv run mypy src/github_mcp_server --strict
```

## Architecture

```
Claude Code / MCP Client
      |
      | MCP Protocol (stdio)
      v
┌─────────────────────────────┐
│  Python FastMCP Server      │
│  - Tool Registry            │
│  - PyGithub Client          │
│  - Error Handling           │
│  - Type Validation          │
└─────────────┬───────────────┘
              |
              | PyGithub REST API
              v
        GitHub API
```

## Project Structure

```
github-mcp-server/
├── src/github_mcp_server/
│   ├── server.py              # Server entry point
│   ├── tools/
│   │   ├── issues.py          # Issue operations
│   │   ├── pulls.py           # PR operations
│   │   ├── ci.py              # CI operations
│   │   ├── milestones.py      # Milestone operations
│   │   └── batch_operations.py # Batch operations
│   ├── utils/
│   │   ├── github_client.py   # Singleton PyGithub client
│   │   ├── errors.py          # Structured error handling
│   │   └── types.py           # Type definitions
│   └── config/
│       └── defaults.py        # Environment-based defaults
└── tests/
    ├── test_*.py              # Unit tests
    └── integration/           # Integration tests
```

## License

MIT License - see [LICENSE](LICENSE) for details.

## Links

- [MCP Protocol Documentation](https://modelcontextprotocol.io/)
- [PyGithub Documentation](https://pygithub.readthedocs.io/)
- [FastMCP Framework](https://github.com/anthropics/fastmcp)
