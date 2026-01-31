# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2025-01-31

### Added

- Initial release as standalone package
- **Issue Operations**: `create_issues`, `get_issue`, `list_issues`, `close_issue`
- **Pull Request Operations**: `create_pr_with_content`, `get_pull_request`, `update_pr`, `merge_pr`
- **CI/CD Operations**: `check_ci_status`, `get_ci_logs`
- **Batch Operations**: `batch_update_issues`, `batch_add_labels`, `batch_link_to_project`
- **Milestone Operations**: `create_milestone`, `list_milestones`
- Environment-based configuration for default owner/repo
- Comprehensive test suite with unit and integration tests
- Full documentation and usage examples
