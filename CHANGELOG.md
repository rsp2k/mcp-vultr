# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.1] - 2024-12-20

### Fixed
- Fixed FastMCP server initialization by removing unsupported parameters
- Corrected MCP server creation to use proper FastMCP constructor
- Resolved "unexpected keyword argument 'description'" error

### Changed
- Simplified FastMCP initialization to use only the name parameter
- Updated server creation to be compatible with current FastMCP version

## [1.0.0] - 2024-12-20

### Added
- Initial release of Vultr DNS MCP package
- Complete MCP server implementation for Vultr DNS management
- Python client library for direct DNS operations
- Command-line interface for DNS management
- Support for all major DNS record types (A, AAAA, CNAME, MX, TXT, NS, SRV)
- DNS record validation and configuration analysis
- MCP resources for client discovery
- Comprehensive error handling and logging
- Natural language interface through MCP tools
- Convenience methods for common DNS operations
- Setup utilities for websites and email
- Full test suite with pytest
- Type hints and mypy support
- CI/CD configuration for automated testing
- Comprehensive documentation and examples

### Features
- **Domain Management**: List, create, delete, and get domain details
- **DNS Records**: Full CRUD operations for all record types
- **Validation**: Pre-creation validation with helpful suggestions
- **Analysis**: Configuration analysis with security recommendations
- **CLI Tools**: Complete command-line interface
- **MCP Integration**: Full Model Context Protocol server
- **Python API**: Direct async Python client
- **Error Handling**: Robust error handling with actionable messages

### Supported Operations
- Domain listing and management
- DNS record creation, updating, and deletion
- Record validation before creation
- DNS configuration analysis
- Batch operations for common setups
- Natural language DNS management through MCP

### Documentation
- Complete API documentation
- Usage examples and tutorials
- MCP integration guides
- CLI reference
- Development guidelines
