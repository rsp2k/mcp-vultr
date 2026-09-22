# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project uses [CalVer](https://calver.org/) (`YYYY.MM.DD`, PEP 440) from 2026.09.12 onward;
earlier releases followed Semantic Versioning.

## [Unreleased]

### Added
- **Automatic backup schedules.** `backup_get_schedule` and
  `backup_set_schedule` read and write the per-instance schedule
  (`/instances/{id}/backup-schedule`), plus a
  `backups://schedule/{instance}` resource. Types are `daily`, `weekly`,
  `monthly`, `daily_alt_even` and `daily_alt_odd`; all times are UTC.
  The `backups` module previously carried a comment saying no backup
  management tools were available in the API, which was not correct.
- `backup_list_all` and `backup_get` expose the existing backup
  resources as tools as well.
- `VultrDNSServer.get_backup_schedule()` and `set_backup_schedule()`.

### Changed
- `backup_set_schedule` **refuses an instance name that matches more
  than one instance** and names the candidates, rather than acting on
  whichever comes first. Reported from a decommission where a live and a
  retired host both answered to the same hostname. The existing
  instance tools still resolve first-match; this is the pattern they
  should move to.
- Schedule arguments are validated before the call: unknown type, hour
  outside 0-23, day-of-month outside 1-28, and weekly or monthly
  without its day selector are all rejected locally with a message
  saying what to pass. `dow` is deliberately not range-checked, because
  Vultr's own tooling documents it inconsistently (0-6 in the CLI, 1-7
  elsewhere); read the schedule back to confirm the day.

## [2026.09.21] - 2026-09-21

### Fixed
- **Six tools crashed with `'FunctionTool' object is not callable`.**
  `@mcp.tool()` returns a `FunctionTool` on FastMCP 2.x, not the function
  it decorates, so any tool whose body called a sibling tool by name
  failed the moment it was invoked. Affected
  `get_startup_script_content`, `list_vc2_plans`, `list_vhf_plans`,
  `list_voc_plans`, `get_application_deployment_guide`, and the
  `storage-gateways://{id}/status` resource. Each shared body moved into
  a plain helper that the tool and its callers both call, so the fix
  does not depend on what the decorator returns. Tool names, resource
  URIs and templates are unchanged.
- **A successful write was followed by stale reads.** Nothing on the
  write path invalidated the response cache, so a create or delete was
  followed by up to the cache TTL (300s by default) of listings that did
  not reflect it. Reported from live use: two firewall rules were created
  successfully and were reachable, while the rule listing kept returning
  the pre-create result. That reads as a *failed* write rather than a
  stale one, and the obvious recovery is to issue the create again,
  which ends in duplicate grants; the same shape on a delete invites a
  second delete.

  Every successful non-GET now invalidates the reads it can affect.
  Invalidation happens in `VultrDNSServer._make_request`, so it covers
  every resource rather than only DNS, and it matches on whole path
  segments: writing to `/firewalls/g1/rules` clears that listing and
  `/firewalls`, and leaves `/firewalls/g2/rules` alone.
  `CacheManager.get_stats()` gained an `invalidations` counter.

## [2026.09.12] - 2026-09-12

Versioning switches to CalVer (`YYYY.MM.DD`, PEP 440) from this release
on. The date says when the package was last tested against the Vultr
API and the FastMCP framework, which is the question people actually
ask when something misbehaves. PEP 440 orders `2026.09.12` after every
`2.x` release, so upgrades resolve normally.

### Fixed
- **Server crashed at startup under FastMCP 4.** The dependency was
  declared as `fastmcp>=0.1.0`, so fresh installs (`uvx mcp-vultr`)
  resolved FastMCP 4.0.x, where `FastMCP.mount()` takes `namespace=`
  instead of `prefix=`. Every sub-server mount raised
  `TypeError: mount() got an unexpected keyword argument 'prefix'`
  before the server spoke MCP, and clients only saw
  `MCP error -32000: Connection closed`. The dependency is now pinned to
  `fastmcp>=2.11,<3`. A follow-up release migrates to FastMCP 4.

### Added
- **SOCKS5 and HTTP proxy support via `VULTR_PROXY`.** Set
  `VULTR_PROXY=socks5h://127.0.0.1:1080` (or `socks5://`, `http://`,
  `https://`) to route every outbound Vultr API call through a proxy.
  Useful when the API is only reachable from an allowlisted network,
  paired with `ssh -D`.
- `VULTR_PROXY=direct` (also `none` / `off`) forces a direct connection
  and ignores ambient `HTTP_PROXY` / `ALL_PROXY` variables. Previously
  those variables were silently honoured by httpx's `trust_env` default
  with no way to opt out and no way to see that it was happening.
- New `mcp_vultr.http_config` module centralising httpx client
  configuration. All four `httpx.AsyncClient` construction sites
  (`server.py`, `api_key_broker.py` ×2, `oauth_auth.py`) now resolve
  proxy settings identically through `client_kwargs()`.
- `http_config.describe()` reports the active proxy configuration, and
  proxy credentials are redacted from all log output.

### Changed
- Dependency bumped from `httpx>=0.24.0` to `httpx[socks]>=0.26.0`. The
  `socks` extra pulls in `socksio` for SOCKS5 support; 0.26 is the floor
  for the modern singular `proxy=` client argument (`proxies=` was
  removed in httpx 0.28).

## [2.4.1] - 2026-05-19

### Fixed
- **Critical: `dns_update_record` corrupted records on partial updates.**
  The MCP wrapper in `dns.py` passed positional args to a client method
  whose signature required `record_type` at position 3 — but the wrapper
  had no such parameter. Every positional arg shifted left by one: a
  caller passing only `data=...` ended up writing that IP into the
  `name` field of the target record (renaming the record) while leaving
  the actual `data` unchanged.
- Dropped the `record_type` parameter from `VultrDNSServer.update_record`
  and `VultrDNSClient.update_record` entirely. Vultr's PATCH endpoint
  does not allow changing a record's type after creation, so the field
  was dead weight (and was the source of the positional misalignment).
- All fields except `domain` and `record_id` are now properly optional;
  only provided fields are sent in the PATCH payload, matching Vultr's
  PATCH semantics.
- The legacy low-level MCP `update_dns_record` tool schema in
  `server.py` had `record_type, name, data` listed as required;
  corrected to only require `domain` and `record_id`.

### Test
- Updated `test_update_record` in `test_vultr_server.py` and
  `test_update_record_method` in `test_client.py` to reflect the
  corrected signatures.
- Fixed a pre-existing test bug in `test_client_error_scenarios.py`
  that passed `data=` to `client.update_record` (its kwarg is `value=`).

## [2.4.0] - 2026-05-19

### Added
- **SSH Keys**: `ssh_key_list` and `ssh_key_get` tools for direct invocation
  (previously only available as MCP resources). The `list` tool supports
  `format="compact"` (default, `name<TAB>id` per line) or `format="json"`.
  The `get` tool resolves by name or UUID and emits a friendly
  "Available SSH keys: …" listing on a miss.
- **DNS**: `dns_list_domains` tool with `format="compact"` (default) or
  `format="json"`, mirroring the existing `dns_list_records` pattern.

### Fixed
- **Zone-file export** (RFC 1035 compliance):
  - Synthesizes an SOA record at the top of every exported zone (Vultr
    manages SOA internally and doesn't return it via `/records`).
  - Fully-qualifies MX, NS, CNAME, SRV, and PTR rdata (appends trailing
    dot so `$ORIGIN` isn't accidentally re-appended on import).
  - Splits TXT records over 255 characters into multiple quoted strings.
  - Apex records now render as `@` instead of an empty owner (which means
    "same as previous line" in zone-file grammar).

### Security / Hygiene
- Replaced two illustrative UUIDs in README CLI examples with
  RFC-style `00000000-...` placeholders.

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
