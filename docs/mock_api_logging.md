# Mock API Logging Documentation

## Overview
The mcp-vultr test suite includes comprehensive mock API logging capabilities for debugging and analyzing test behavior. This system tracks all mock API calls during testing, providing detailed insights into API usage patterns.

## Features

### Core Capabilities
- **Call Tracking**: Records every mock API call with timestamp, arguments, and results
- **Error Monitoring**: Tracks failed API calls and error types
- **Statistics**: Generates comprehensive summaries of API usage
- **Domain Analysis**: Tracks operations per domain
- **Record Type Analysis**: Monitors DNS record types being created/updated
- **Console Output**: Optional real-time logging with success/failure indicators
- **File Output**: Optional JSON logging to file for detailed analysis

### Logging Components

#### MockAPILogger Class
Main logging class located in `tests/mock_api_logger.py`:
- Tracks call history with detailed metadata
- Provides summary statistics
- Supports both console and file output
- Thread-safe operation

#### Integration with Test Fixtures
The logger integrates seamlessly with pytest fixtures through `conftest.py`:
- Automatically wraps mock clients when `MOCK_API_LOGGING=true`
- Preserves original mock behavior while adding logging
- Works with both sync and async mock methods

## Usage

### Running Tests with Logging

#### Method 1: Environment Variable
```bash
# Enable logging for any test run
export MOCK_API_LOGGING=true
uv run pytest tests/

# Or inline
MOCK_API_LOGGING=true uv run pytest tests/test_client.py
```

#### Method 2: Using the Helper Script
```bash
# Run all core tests with logging
python test_with_logging.py

# Run specific test file
python test_with_logging.py tests/test_client.py

# Run with verbose output
python test_with_logging.py tests/test_client.py --verbose
```

### Output Examples

#### Console Output
When enabled, the logger provides real-time feedback:
```
✅ Mock API Call #1: list_domains
   Args: (), Kwargs: {}
✅ Mock API Call #2: create_record
   Args: ('example.com',), Kwargs: {'type': 'A', 'name': 'www', 'data': '192.168.1.1'}
❌ Mock API Call #3: delete_domain
   Args: ('protected.com',), Kwargs: {}
   Error: Domain is protected
```

#### Summary Statistics
At the end of test runs, a comprehensive summary is displayed:
```
============================================================
MOCK API CALL SUMMARY
============================================================
Total Calls: 24
Unique Methods: 9
Success Rate: 95.8%
Errors: 1

Method Call Counts:
  create_domain: 2
  create_record: 11
  delete_domain: 2
  delete_record: 1
  get_domain: 2
  get_record: 1
  list_domains: 2
  list_records: 2
  update_record: 1

Domain Operations:
  example.com: 4 operations
  newdomain.com: 2 operations
  test.com: 3 operations

Record Types Created/Updated:
  A: 5
  MX: 2
  TXT: 3
  CNAME: 1
============================================================
```

### Programmatic Access

#### Getting Call History
```python
from tests.mock_api_logger import mock_api_logger

# After running tests
history = mock_api_logger.call_history
for call in history:
    print(f"{call['timestamp']}: {call['method']} - {call['result']}")
```

#### Getting Summary Statistics
```python
from tests.mock_api_logger import get_mock_api_summary

summary = get_mock_api_summary()
print(f"Total API calls: {summary['total_calls']}")
print(f"Success rate: {summary['success_rate']}")
```

#### Clearing Logs
```python
from tests.mock_api_logger import clear_mock_api_logs

# Clear logs between test runs
clear_mock_api_logs()
```

### File-Based Logging

Enable file logging for persistent analysis:
```python
from tests.mock_api_logger import enable_mock_api_logging

# Enable with file output
enable_mock_api_logging(console=True, log_file="api_calls.jsonl")
```

The log file contains JSON Lines format with one call per line:
```json
{"timestamp": "2024-12-20T10:30:45", "call_number": 1, "method": "list_domains", "args": "()", "kwargs": "{}", "result": "[{'domain': 'example.com'}]", "error": null}
```

## Use Cases

### 1. Debugging Test Failures
When a test fails unexpectedly, enable logging to see exactly which API calls were made:
```bash
MOCK_API_LOGGING=true uv run pytest tests/test_client.py::test_failing -xvs
```

### 2. Performance Analysis
Track the number of API calls to identify inefficient code:
```python
# Run tests and check if too many calls are being made
python test_with_logging.py tests/test_client.py
# Look for redundant calls in the summary
```

### 3. Coverage Verification
Ensure all API endpoints are being tested:
```python
# Run full test suite
python test_with_logging.py
# Check "Unique Methods" count in summary
```

### 4. Integration Testing
Verify that the correct sequence of API calls occurs:
```python
# Enable file logging
MOCK_API_LOGGING=true uv run pytest tests/test_integration.py
# Analyze the call sequence in the log file
```

## Configuration Options

### MockAPILogger Constructor
```python
MockAPILogger(
    log_file=None,       # Path to log file (optional)
    console_output=False # Enable console output
)
```

### Environment Variables
- `MOCK_API_LOGGING`: Set to "true" to enable logging
- `MOCK_API_LOG_FILE`: Optional path for log file output

## Best Practices

1. **Use sparingly in CI/CD**: Logging adds overhead, enable only when debugging
2. **Clear logs between test runs**: Use `clear_mock_api_logs()` for clean state
3. **File logging for complex scenarios**: Use file output when debugging complex test failures
4. **Console logging for quick checks**: Use console output for immediate feedback
5. **Analyze patterns**: Look for redundant calls or inefficient API usage

## Troubleshooting

### Logging Not Appearing
- Ensure `MOCK_API_LOGGING=true` is set
- Check that the mock fixture is using `logged_mock()` wrapper
- Verify the test is using the mocked client, not a real API client

### Performance Impact
- Disable console output for large test suites
- Use file logging with post-test analysis for better performance
- Clear logs regularly to prevent memory buildup

### Missing API Calls
- Some async operations may not be logged if not properly awaited
- Ensure all mock methods are listed in the `methods_to_log` array

## Future Enhancements

Potential improvements for the logging system:
- Web dashboard for interactive analysis
- Integration with APM tools
- Automatic performance regression detection
- GraphQL query analysis
- Request/response body recording
- Latency simulation and analysis