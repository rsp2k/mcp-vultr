# mcp-vultr on FastMCP 4.0.x: migration research (2026-09-12)

Research only. Nothing under /home/rpm/claude/mcp-vultr was modified. All experiments ran on
copies in the scratchpad (`pkgcopy*`) against three scratch venvs: `v2` (fastmcp 2.14.7, mcp 1.30.0),
`v3` (fastmcp 3.4.7, mcp 1.30.0), `v4`/`v4b` (fastmcp 4.0.3, mcp 2.2.0).

## TL;DR

Only three things in the runtime path actually break on 4.0.3, and two of them are small. The
`mount(prefix=)` crash is a 28-line rename. `ctx.send_resource_list_changed()` is gone (since 3.x)
and needs a one-line replacement. The big one is the legacy low-level `create_mcp_server()` in
`server.py`: mcp SDK v2 removed the `@server.list_tools()` decorator API entirely, so that ~690-line
block and its five test files are dead on 4.x. Tool names are preserved exactly
(`dns_list_domains` stays `dns_list_domains`), so downstream `mcp__vultr__*` allowlists are safe.
Recommendation: hard cutover to `fastmcp>=4,<5`, drop the legacy low-level server.

## (a) Breaking changes that hit this codebase

| # | Change (version introduced) | Where in mcp-vultr | 4.0.3 behavior | Fix |
|---|---|---|---|---|
| 1 | `mount(prefix=)` removed (deprecated 3.0, removed 4.0). 4.0.3 sig: `mount(server, namespace=None, tool_names=None)` (server/server.py:2308) | `src/mcp_vultr/fastmcp_server.py:104-187`, 28 calls | `TypeError` at startup | s/prefix=/namespace=/ |
| 2 | `Context.send_resource_list_changed()` removed in 3.0 (absent on 3.4.7 and 4.0.3; present on 2.14.7). Replacement: `await ctx.send_notification(mcp.types.ResourceListChangedNotification(method="notifications/resources/list_changed"))` (verified working in-memory, both auto and legacy client modes) | `src/mcp_vultr/notification_manager.py:148`; called from 14 modules (dns, instances, firewall, k8s, lb, users, vpcs, ...) on every mutating tool that receives `ctx` | Swallowed by the bare `except` at :173 and then `print()`ed to **stdout** (:175), which corrupts the stdio JSON-RPC stream on every create/update/delete. Verified: `dns_create_domain` returns OK but emits the warning line | Swap the call; route the except branch and the debug prints (:165-171) to stderr or structlog |
| 3 | mcp SDK v2 (pulled in by fastmcp 4; fastmcp-slim requires `mcp>=2,<3`) removed the decorator API on `mcp.server.lowlevel.Server`. 2.2.0 exposes only `add_request_handler(method, params_type, handler)`, `run`, `create_initialization_options`, `streamable_http_app` | `src/mcp_vultr/server.py:5073-5760` (`create_mcp_server`, `run_server`, `@server.list_resources/read_resource/list_tools/call_tool`), exported from `src/mcp_vultr/__init__.py:28-53` | `AttributeError: 'Server' object has no attribute 'list_resources'` at server.py:5101 | Delete the legacy server (nothing in the shipped entry points uses it; `cli_main.py:13` imports `run_server` from `fastmcp_server`) or port to `add_request_handler` |
| 4 | `get_tools()` -> `list_tools()` returning a list (3.0) | `tests/test_fastmcp_server.py:217`, `.tools["..."]` at :473, :518, :537, :551, :562 | `AttributeError: 'FastMCP' object has no attribute 'get_tools'` | Use `await server.get_tool("name")` + `.fn(...)`, or call the decorated function directly (v3+ decorators return the original function) |
| 5 | `FastMCP.name` is a read-only property on 2.14.7, 3.4.7 and 4.0.3 (no setter) | `src/mcp_vultr/fastmcp_server.py:94` (`mcp.name = ...` in the OAuth branch) | `AttributeError` (pre-existing bug, already broken on 2.x) | Pass the name into `create_oauth_enhanced_server()` instead |
| 6 | Dependency floors: pydantic >= 2.12, starlette >= 1.0.1, httpx2 (FastMCP's own HTTP stack only) | `pyproject.toml` (`pydantic>=2.0.0`, no starlette pin) | Resolver bumps silently; the package's own `httpx` use and `except httpx.*` in server.py:203/219 wrap its own calls and are unaffected | Bump pin to `fastmcp>=4,<5`; optionally raise pydantic floor for honesty |

Things I checked that do NOT break: `FastMCP(name=...)` (all 30 module constructors), `@mcp.tool()`
and `@mcp.tool(name=...)` (117 + 2 sites), `@mcp.resource("scheme://...")` templates, `Context | None`
injection, `mcp.run(transport="stdio"|"sse"|"http")` (Transport literal at mixins/transport.py:195 still
lists all four), arbitrary attribute assignment like `mcp._oauth_middleware = ...` (oauth_server.py:131),
`from mcp.types import Resource, TextContent, Tool` plus camelCase `Tool(inputSchema=...)` construction
(bridged by `fastmcp/_compat.py`, warns once). No `ctx.sample/elicit/list_roots`, `task=True`,
`exclude_args`, `serializer=`, `McpError(ErrorData(...))`, `import_server`, `as_proxy` or
`fastmcp.server.auth.*` usage exists anywhere in src/ or tests/.

Auth (task item 4): `oauth_auth.py`, `api_key_broker.py`, `http_config.py` and `oauth_server.py` import
nothing from `fastmcp.server.auth`. The "middleware" is a plain class holding a PyJWT/JWKS validator,
stored as an attribute on the server; it never hooks the FastMCP middleware chain and no tool actually
invokes it (the `require_permission` decorators are defined but not applied to mounted tools). It is
version-agnostic and imports cleanly on 4.0.3. Native equivalents exist in 4.0.3
(`fastmcp.server.auth.providers.jwt.JWTVerifier`, `providers/keycloak.py`, `FastMCP(auth=...)`) if a real
redesign is ever wanted, but that is out of scope for compatibility.

Pre-existing on every version (noted, not v4-caused): the whole suite is already red on 2.14.7
(207 fail/error, mostly TUI snapshots, client error scenarios, cli, retry, cache); `oauth_server.py`
mounts all 28 sub-servers without a namespace, so the short tool names `list/get/create/update/delete`
collide across modules (4.0.3 logs "Duplicate list_tools component" and keeps the first, so most
modules' CRUD tools are silently shadowed); `run_server` and `run_oauth_server` `print()` banners to
stdout (fastmcp_server.py:231, oauth_server.py:137-144, 258-262), which violates the house rule and the
stdio transport.

## (b) Effort

| Item | Size |
|---|---|
| 1 prefix -> namespace (28 sites) | S (mechanical sed; verified on a copy: 316 tools, all names unchanged) |
| 2 notification replacement + stderr | S (one call + three prints) |
| 3 legacy low-level server | M if deleted (remove 690 lines, update `__init__.py` exports, retire/rewrite 5 test files: `tests/conftest.py:30`, `test_mcp_server.py`, `test_mcp_error_scenarios.py` (3 tests), `test_server.py::TestMCPServer` + `test_validation_tool`, `test_package_validation.py:64-75`); L if ported to `add_request_handler` |
| 4 test_fastmcp_server.py rewrite (11 tests) | S |
| 5 `mcp.name` setter bug | S |
| 6 pin + CHANGELOG/README | S |
| Optional: namespace the oauth_server mounts, stdout -> stderr | S |

Total: about half a day if item 3 is a deletion, one to two days if ported.

## (c) Recommended approach: hard cutover to `fastmcp>=4,<5`

A dual-support shim on `mount()` is trivial (`"namespace" in inspect.signature(mcp.mount).parameters`;
2.14.7 accepts only `prefix`, 3.4.7 accepts both, 4.0.3 only `namespace`). But mount is not the real
fork. The mcp SDK major is welded to the fastmcp major (2.x/3.x -> mcp 1.x, 4.x -> mcp 2.x), and the
low-level `server.py` code only works on mcp 1.x, while `send_resource_list_changed` only exists on
fastmcp 2.x. Supporting 2.x and 4.x together therefore means three conditional code paths in a package
whose published 2.4.1 has been resolving to 4.x anyway. FastMCP 4 is GA (v4.0.0 2026-08-31, v4.0.3
2026-09-05) and 2.14.7 (2026-04-13) is end-of-line. Cut over, bump to a CalVer version, and note in the
CHANGELOG that 2.x/3.x are no longer supported.

## (d) Files to touch

- `pyproject.toml` (dependency pin, version bump)
- `src/mcp_vultr/fastmcp_server.py` (:94 name assignment, :104-187 mounts, :231 print)
- `src/mcp_vultr/notification_manager.py` (:148 call, :165-177 prints)
- `src/mcp_vultr/server.py` (:5073-5760 legacy server: delete or port; keep `VultrDNSServer`, exceptions, `_validate_*` helpers)
- `src/mcp_vultr/__init__.py` (:9-16 docstring, :28-53 `create_mcp_server` export)
- `src/mcp_vultr/oauth_server.py` (prints; optionally add namespaces to the 28 mounts)
- `tests/test_fastmcp_server.py`, `tests/conftest.py`, `tests/test_mcp_server.py`, `tests/test_mcp_error_scenarios.py`, `tests/test_server.py`, `tests/test_package_validation.py`
- `CHANGELOG.md`, `README.md`

## (e) Tool-naming compatibility verdict: SAFE, names are byte-identical

4.0.3 `Namespace` transform (server/transforms/namespace.py:51) builds `f"{prefix}_"` for tool and
prompt names and `protocol://namespace/path` for resource URIs (:79). Verified against the real
`create_dns_mcp` on both versions:

- 2.14.7 `mount(prefix="dns")`: `dns_list_domains`, resources `domains://dns/list`, templates `domains://dns/{domain}`
- 4.0.3 `mount(namespace="dns")`: `dns_list_domains`, resources `domains://dns/list`, templates `domains://dns/{domain}`

Full server on 4.0.3 after the rename: 316 tools, `dns_list_domains` present, `Client.call_tool("dns_list_domains")`
and `read_resource("domains://dns/list")` succeed. `mcp__vultr__dns_list_domains` allowlists need no
change; `tool_names=` is not needed. (No `/` separator appears anywhere in 3.x or 4.x naming.)

## (f) Sources consulted

- https://gofastmcp.com/getting-started/upgrading/from-fastmcp-3 (v3 -> v4; `/development/upgrade-guide` now redirects to the v2 -> v3 page)
- https://gofastmcp.com/getting-started/upgrading/from-fastmcp-2 (v2 -> v3, including the "Removed in v4" deprecation list)
- https://github.com/PrefectHQ/fastmcp/releases (v2.14.7 2026-04-13, v3.0.0 2026-02-18, v4.0.0 2026-08-31, v4.0.1..v4.0.3 through 2026-09-05)
- Installed 4.0.3 source: `fastmcp/server/server.py` (`__init__` :285, `mount` :2308, `tool` :1851), `server/mixins/transport.py` (`run` :108, `http_app` :372), `server/transforms/namespace.py`, `server/context.py`, `_compat.py`, `fastmcp_slim-4.0.3.dist-info/METADATA`
- Live introspection in the scratch venvs (signatures, `hasattr` probes, end-to-end `Client(server)` calls) and two full pytest runs (`v2-results.txt`, `v4-results.txt` in the scratchpad): 42 additional failures on 4.0.3, of which 30 are the low-level server, 11 are `get_tools`, 1 is a TUI snapshot flake
