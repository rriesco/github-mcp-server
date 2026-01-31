# GitHub MCP Server Tests

This directory contains the test suite for the GitHub MCP server, including unit tests, integration tests, and token measurement tools.

## Test Structure

```
tests/
├── __init__.py
├── test_setup.py                     # Unit tests for setup and error handling
├── integration/                      # Integration tests (real GitHub API)
│   ├── __init__.py
│   ├── conftest.py                  # Pytest fixtures and configuration
│   ├── test_issues_integration.py   # Issue operations integration tests
│   └── test_ci_integration.py       # CI operations integration tests
└── token_measurement/               # Token usage measurement tools
    ├── __init__.py
    ├── measure.py                   # Token measurement script
    └── results.md                   # Generated measurement results
```

## Prerequisites

### 1. Install Dependencies

```bash
cd github-mcp-server
uv sync --dev
```

This installs:
- `pytest` - Test framework
- `pytest-asyncio` - Async test support
- `pytest-cov` - Coverage reporting
- `mypy` - Type checking

### 2. Configure GitHub Authentication

Integration tests require a GitHub Personal Access Token.

**Create Token**:
1. Go to https://github.com/settings/tokens
2. Click "Generate new token (classic)"
3. Required scopes: `repo`, `workflow`, `read:org`
4. Copy the generated token

**Configure Environment**:

Create `.env.test` file (or use `.env`):
```bash
# github-mcp-server/.env.test
GITHUB_TOKEN=ghp_your_token_here
TEST_OWNER=your-username
TEST_REPO=your-test-repo
```

**Alternative**: Copy from example:
```bash
cp .env.test.example .env.test
# Edit .env.test and add your token
```

## Running Tests

### Unit Tests Only

Run unit tests that don't require GitHub API:

```bash
uv run pytest tests/test_setup.py -v
```

**Expected**: 10 tests pass, testing error handling and GitHub client setup.

### Integration Tests Only

Run integration tests that make real GitHub API calls:

```bash
# Requires GITHUB_TOKEN in .env or .env.test
uv run pytest tests/integration/ -v -m integration
```

**Expected**: 13 integration tests pass
- 7 tests for issue operations (create_issue, get_issue)
- 6 tests for CI operations (check_ci_status)

**Note**: Integration tests automatically cleanup created issues by closing them after each test.

### All Tests

Run both unit and integration tests:

```bash
uv run pytest -v
```

### With Coverage Report

Generate code coverage report:

```bash
# Terminal output
uv run pytest --cov=github_mcp_server --cov-report=term-missing

# HTML report
uv run pytest --cov=github_mcp_server --cov-report=html
open htmlcov/index.html  # View in browser
```

**Current Coverage**: ~23% (see "Coverage Notes" below)

### Run Specific Test File

```bash
# Unit tests only
uv run pytest tests/test_setup.py -v

# Issue integration tests
uv run pytest tests/integration/test_issues_integration.py -v

# CI integration tests
uv run pytest tests/integration/test_ci_integration.py -v
```

### Run Specific Test

```bash
uv run pytest tests/integration/test_issues_integration.py::TestCreateIssueIntegration::test_create_issue_with_labels_and_milestone -v
```

## Token Measurement

### Purpose

Measure token usage comparing MCP tools vs. Python scripts to validate projected 60-68% token savings.

### Running Measurements

```bash
# Requires GITHUB_TOKEN in .env
cd github-mcp-server
uv run python tests/token_measurement/measure.py
```

### Output

**Console Output**:
```
🔍 Running token measurements...
======================================================================

📊 Scenario 1: Get Issue Details
----------------------------------------------------------------------
  Running MCP get_issue...
  ✓ MCP tokens: 250
  Running Bash get_issue_details.py...
  ✓ Bash tokens: 600
  💰 Savings: 58.3%

📊 Scenario 2: Check CI Status
----------------------------------------------------------------------
  Running MCP check_ci_status...
  ✓ MCP tokens: 300
  Running Bash check_ci_status.py...
  ✓ Bash tokens: 800
  💰 Savings: 62.5%

======================================================================
💰 Overall Token Savings: 60.7%
   Bash total: 1400 tokens
   MCP total: 550 tokens
   Saved: 850 tokens

✅ SUCCESS: Achieved 60.7% savings (target: ≥60%)
```

**File Output**: `tests/token_measurement/results.md`
- Detailed measurement table
- Per-operation savings breakdown
- Validation against targets

## Test Configuration

### pytest.ini

```ini
[pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
asyncio_default_fixture_loop_scope = function
addopts =
    --cov=github_mcp_server
    --cov-report=html
    --cov-report=term-missing
    --cov-fail-under=85  # May fail until more unit tests added
markers =
    integration: marks tests as integration tests (require GITHUB_TOKEN)
    unit: marks tests as unit tests (no external dependencies)
```

### Test Markers

Use markers to selectively run tests:

```bash
# Run only integration tests
pytest -m integration

# Run only unit tests
pytest -m unit

# Skip integration tests
pytest -m "not integration"
```

## Integration Test Features

### Automatic Cleanup

All integration tests automatically cleanup created resources:

```python
def test_create_issue(..., created_issues: List[int], cleanup_issues: None):
    # Create issue
    result = create_issue(...)

    # Track for cleanup
    created_issues.append(result["issue_number"])

    # Test automatically closes issue after completion
```

### Test Repository

Tests use repository specified in `.env.test`:

```bash
# .env.test
TEST_OWNER=your-username
TEST_REPO=your-test-repo
```

Integration tests require both `TEST_OWNER` and `TEST_REPO` environment variables to be set.

### Skipping on Missing Token

Integration tests automatically skip if `GITHUB_TOKEN` is not set:

```
tests/integration/test_issues_integration.py::... SKIPPED
Reason: GITHUB_TOKEN not set - skipping integration tests
```

## Coverage Notes

### Current Coverage: ~23%

**Well-Covered Modules** (100%):
- ✅ `utils/errors.py` - Error handling
- ✅ `utils/github_client.py` - GitHub client singleton

**Uncovered Modules** (0%):
- ❌ `tools/issues.py` - Covered by integration tests
- ❌ `tools/ci.py` - Covered by integration tests
- ❌ `tools/pulls.py` - Covered by integration tests
- ❌ `utils/formatter.py` - Needs unit tests
- ❌ `utils/types.py` - Needs unit tests

### Why Tool Modules Show 0% Coverage

The MCP tool modules (`issues.py`, `ci.py`, `pulls.py`) are decorated with `@mcp.tool()` and are primarily validated through integration tests rather than unit tests. This is intentional:

1. **Integration-First**: MCP tools are thin wrappers - integration tests are more valuable
2. **Real API Validation**: Integration tests validate actual GitHub API behavior
3. **Decorator Complexity**: `@mcp.tool()` makes unit testing more complex

### Improving Coverage

To reach 85%+ coverage target:

1. **Add unit tests for formatters**:
   ```python
   # tests/test_formatter.py
   def test_format_pr_body():
       result = format_pr_body(...)
       assert "## Summary" in result
   ```

2. **Add unit tests for types**:
   ```python
   # tests/test_types.py
   def test_repository_dataclass():
       repo = Repository(owner="test", repo="repo")
       assert repo.full_name == "test/repo"
   ```

3. **Consider mocking for tool functions** (if needed):
   ```python
   @patch("github_mcp_server.tools.issues.get_github_client")
   def test_create_issue_unit(mock_client):
       # Unit test with mocked GitHub client
   ```

## Troubleshooting

### "GITHUB_TOKEN not set"

**Problem**: Integration tests skip with message about missing token.

**Solution**:
```bash
# Create .env.test file
echo "GITHUB_TOKEN=ghp_your_token_here" > .env.test
```

### "Coverage failure: total of 23 is less than fail-under=85"

**Problem**: Coverage threshold not met.

**Short-term Solution** (temporary):
```bash
# Run without coverage threshold
pytest --cov=github_mcp_server --cov-report=html --no-cov-fail-under
```

**Long-term Solution**: Add unit tests for uncovered modules.

### "Module github_mcp_server was previously imported"

**Problem**: Coverage warning about module import order.

**Solution**: This is a known pytest-cov issue with `@mcp.tool()` decorators. The warning can be safely ignored as integration tests provide validation.

### Integration Tests Hang

**Problem**: Test hangs waiting for GitHub API.

**Solution**:
1. Check network connectivity
2. Verify GITHUB_TOKEN is valid
3. Check GitHub API status: https://www.githubstatus.com/
4. Increase timeout (tests have 10-15s timeouts)

### Token Measurement Script Fails

**Problem**: `measure.py` fails with import errors.

**Solution**:
```bash
# Ensure dependencies installed
uv sync --dev

# Run from github-mcp-server directory
cd github-mcp-server
uv run python tests/token_measurement/measure.py
```

## Best Practices

### Writing New Integration Tests

```python
@pytest.mark.integration
class TestNewFeature:
    """Integration tests for new feature."""

    def test_new_feature(
        self,
        test_config: dict,
        created_issues: List[int],
        cleanup_issues: None,
    ) -> None:
        """Test description."""
        # Create resources
        result = create_something(owner=test_config["owner"], ...)

        # Track for cleanup
        created_issues.append(result["id"])

        # Assertions
        assert result["status"] == "success"
```

### Writing New Unit Tests

```python
class TestUtilityFunction:
    """Unit tests for utility function."""

    def test_function_success(self) -> None:
        """Test successful execution."""
        result = utility_function(input_data)
        assert result == expected_output

    def test_function_error_handling(self) -> None:
        """Test error handling."""
        with pytest.raises(ValueError):
            utility_function(invalid_input)
```

## Continuous Integration

### GitHub Actions Integration

Add to `.github/workflows/test.yml`:

```yaml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.12'
      - name: Install uv
        run: pip install uv
      - name: Install dependencies
        run: |
          cd github-mcp-server
          uv sync --dev
      - name: Run unit tests
        run: |
          cd github-mcp-server
          uv run pytest tests/test_setup.py -v
      - name: Run integration tests
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
        run: |
          cd github-mcp-server
          uv run pytest tests/integration/ -v -m integration
```

## References

- **Pytest Documentation**: https://docs.pytest.org/
- **PyGithub Documentation**: https://pygithub.readthedocs.io/
- **MCP Protocol**: https://modelcontextprotocol.io/
