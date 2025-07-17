# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.1.0] - 2025-01-16

### Added
- **Zone File Import/Export** - Major new feature for DNS backup and migration
  - `export_zone_file_tool(domain)` - Export domain records as standard DNS zone file format
  - `import_zone_file_tool(domain, zone_data, dry_run)` - Import DNS records from zone file format
  - `dns://domains/{domain}/zone-file` resource for zone file access
  - Support for all standard DNS record types (A, AAAA, CNAME, MX, TXT, NS, SRV)
  - Comprehensive zone file parsing with proper handling of $TTL and $ORIGIN directives
  - Dry-run mode for import validation without making changes
  - Standard zone file format compliance for interoperability

### Features
- **Backup & Migration**: Easy DNS configuration backup and restoration
- **Bulk Operations**: Import multiple records at once from zone files
- **Validation**: Pre-import validation with detailed error reporting
- **Compatibility**: Standard zone file format works with BIND, PowerDNS, and other DNS servers

### Technical
- Added comprehensive zone file parsing engine with quoted string handling
- Proper record type detection and formatting
- Error handling with line-by-line validation feedback
- Support for both tool and resource access patterns

## [1.0.4] - 2025-01-16

### Fixed
- Fixed tool wrappers to properly call underlying VultrDNSServer methods instead of trying to call FunctionResource objects
- Resolved "FunctionResource object is not callable" error in Claude Desktop
- Tool wrappers now directly call `vultr_client.list_domains()`, `vultr_client.get_domain()`, etc.

### Technical
- Changed tool wrapper implementation from calling resource functions to calling the underlying client methods
- Maintains functionality while fixing the callable object error

## [1.0.3] - 2025-01-16

### Added
- Tool wrappers for resource access to ensure Claude Desktop compatibility
  - `list_domains_tool()` - wrapper for dns://domains resource
  - `get_domain_tool()` - wrapper for dns://domains/{domain} resource
  - `list_records_tool()` - wrapper for dns://domains/{domain}/records resource
  - `get_record_tool()` - wrapper for dns://domains/{domain}/records/{record_id} resource
  - `analyze_domain_tool()` - wrapper for dns://domains/{domain}/analysis resource

### Technical
- Hybrid approach: resources for direct MCP access, tools for Claude Desktop compatibility
- Maintains both patterns to support different MCP client implementations

## [1.0.2] - 2025-01-16

### Changed
- Refactored read operations to use MCP resources instead of tools
- List domains endpoint: `@mcp.resource("dns://domains")`
- Get domain endpoint: `@mcp.resource("dns://domains/{domain}")`
- List records endpoint: `@mcp.resource("dns://domains/{domain}/records")`
- Get record endpoint: `@mcp.resource("dns://domains/{domain}/records/{record_id}")`
- Analyze domain endpoint: `@mcp.resource("dns://domains/{domain}/analysis")`

### Improved
- Better alignment with MCP best practices (resources for read, tools for write)
- Enhanced Claude Desktop integration documentation with uvx support

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
