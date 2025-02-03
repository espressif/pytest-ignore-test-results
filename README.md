# pytest-ignore-test-results

A pytest plugin that enables selective test result ignoring while maintaining test execution.

## Installation

```bash
pip install -U pytest-ignore-test-results
```

## Features

- Ignore specific test case results using exact names or patterns
- Load ignore patterns from files
- Custom exit codes for different failure scenarios
- Support for child test cases
- Option to ignore "no tests collected" errors

## Usage

### Ignore Test Results by Case Name or Pattern

When using this plugin, test cases will execute normally but their results can be selectively ignored. You have two options for specifying which test results to ignore:

1. Using exact names or patterns directly:

```bash
pytest --ignore-result-cases "test_feature_1" "test_feature_2"
```

```bash
pytest --ignore-result-cases "test_feature_*" "test_integration_*"
```

2. Specifying patterns in files:

```bash
pytest --ignore-result-files ignore_list.txt another_list.txt
```

Example ignore file content (ignore_list.txt):

```
test_feature_1  # This is a comment
test_feature_*
test_integration_suite::test_case_1
```

### Control Exit Codes

The plugin provides fine-grained control over exit codes through two options:

1. `--strict-exit-code`: When enabled, the plugin will return exit code 6 if all failed test cases are ignored. Otherwise, it maintains pytest's original exit code behavior.

```bash
pytest --ignore-result-cases "test_feature_*" --strict-exit-code
```

2. `--ignore-no-tests-collected`: When enabled, this option suppresses "no tests collected" errors and returns exit code 0.

```bash
pytest --ignore-no-tests-collected
```

### Custom Test Case Names

The plugin supports test case name customization through the `pytest_custom_test_case_name` hook:

```python
def pytest_custom_test_case_name(item):
    """
    Args:
        item: pytest item

    Returns:
        str: Custom name for the test case
    """
    return f"custom_name::{item.name}"
```
