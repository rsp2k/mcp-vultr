"""
Guard against tools calling their decorated siblings.

`@mcp.tool()` does not return the function it decorates on every FastMCP
version. On 2.x it returns a non-callable `FunctionTool`, so a tool whose body
calls a sibling tool by name dies at runtime with
"'FunctionTool' object is not callable". On 4.x the decorator returns the
original function and the same code works by accident.

That difference is the whole reason for the static check below: the runtime
tests only fail on 2.x, so on 4.x they would pass while the code is still
wrong. The fix in every case is to extract the shared body into a plain
`_private` helper that both the tool and its callers invoke.

Found in the wild 2026-09-13: `get_startup_script_content` was broken in the
published package, along with five other tools.
"""

import ast
import json
import uuid
from pathlib import Path
from unittest.mock import AsyncMock

import pytest
from fastmcp import Client

SRC = Path(__file__).parent.parent / "src" / "mcp_vultr"

#: Decorators that replace the function with a framework object on some versions.
REGISTERING_DECORATORS = {"tool", "resource", "prompt"}


def _decorator_kind(node: ast.expr) -> str | None:
    """Return 'tool'/'resource'/'prompt' if this decorator registers with FastMCP."""
    # @mcp.tool  ->  Attribute;  @mcp.tool() / @mcp.resource("uri") -> Call
    if isinstance(node, ast.Call):
        node = node.func
    if isinstance(node, ast.Attribute) and node.attr in REGISTERING_DECORATORS:
        value = node.value
        if isinstance(value, ast.Name) and value.id == "mcp":
            return node.attr
    return None


def _registered_names(tree: ast.AST) -> set[str]:
    """Names bound to a FastMCP-registered object rather than a plain function."""
    names = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.AsyncFunctionDef | ast.FunctionDef):
            if any(_decorator_kind(d) for d in node.decorator_list):
                names.add(node.name)
    return names


def _internal_calls_to(tree: ast.AST, names: set[str]) -> list[tuple[str, int]]:
    """Find direct calls to any of `names`, ignoring the definitions themselves."""
    violations = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if isinstance(func, ast.Name) and func.id in names:
            violations.append((func.id, node.lineno))
    return violations


def _module_files() -> list[Path]:
    return sorted(p for p in SRC.glob("*.py") if not p.name.startswith("__"))


@pytest.mark.unit
@pytest.mark.parametrize("path", _module_files(), ids=lambda p: p.name)
def test_no_tool_calls_a_decorated_sibling(path):
    """
    A tool body must never call another @mcp.tool/@mcp.resource by name.

    Docstring examples are invisible to this check, which is the point of
    using the AST rather than grepping: only real call expressions count.
    """
    tree = ast.parse(path.read_text())
    registered = _registered_names(tree)
    if not registered:
        pytest.skip("no FastMCP-registered functions in this module")

    violations = _internal_calls_to(tree, registered)
    assert not violations, (
        f"{path.name} calls decorated sibling(s) directly: "
        + ", ".join(f"{name}() at line {line}" for name, line in violations)
        + ". Extract the shared body into a plain _helper and call that instead; "
        "the decorator does not return a callable on FastMCP 2.x."
    )


# --- Runtime coverage for the six that were actually broken -------------------
# These pass vacuously on FastMCP 4 (where the decorator returns the function),
# so they complement rather than replace the static check above.

SCRIPT_ID = str(uuid.uuid4())
GATEWAY_ID = str(uuid.uuid4())


async def _call(mcp, tool_name, args):
    async with Client(mcp) as client:
        return await client.call_tool(tool_name, args)


@pytest.mark.mcp
async def test_get_startup_script_content_reads_the_script():
    from mcp_vultr.startup_scripts import create_startup_scripts_mcp

    client = AsyncMock()
    client.get_startup_script.return_value = {"id": SCRIPT_ID, "script": "#!/bin/sh\necho hi"}

    result = await _call(
        create_startup_scripts_mcp(client),
        "get_startup_script_content",
        {"script_identifier": SCRIPT_ID},
    )

    assert "echo hi" in result.content[0].text
    client.get_startup_script.assert_awaited_once_with(SCRIPT_ID)


@pytest.mark.mcp
@pytest.mark.parametrize(
    ("tool_name", "expected_type"),
    [("list_vc2_plans", "vc2"), ("list_vhf_plans", "vhf"), ("list_voc_plans", "voc")],
)
async def test_per_type_plan_tools_delegate(tool_name, expected_type):
    from mcp_vultr.plans import create_plans_mcp

    client = AsyncMock()
    client.list_plans.return_value = [
        {"id": f"{expected_type}-1c-1gb", "vcpu_count": 1, "ram": 1024,
         "disk": 25, "monthly_cost": 5, "locations": ["ewr"]}
    ]

    result = await _call(create_plans_mcp(client), tool_name, {})

    assert f"{expected_type}-1c-1gb" in result.content[0].text
    client.list_plans.assert_awaited_once_with(expected_type)


@pytest.mark.mcp
async def test_deployment_guide_resolves_the_application():
    from mcp_vultr.marketplace import create_marketplace_mcp

    client = AsyncMock()
    client.list_applications.return_value = [
        {"id": 1, "name": "WordPress", "short_name": "wordpress",
         "type": "marketplace", "image_id": "wordpress"}
    ]

    result = await _call(
        create_marketplace_mcp(client),
        "get_application_deployment_guide",
        {"app_id": "wordpress"},
    )

    assert "WordPress" in result.content[0].text


@pytest.mark.mcp
async def test_gateway_status_tool_and_resource_agree():
    """The resource and the tool share one helper, so they must return the same payload."""
    from mcp_vultr.storage_gateways import create_storage_gateways_mcp

    client = AsyncMock()
    client.get_storage_gateway.return_value = {
        "id": GATEWAY_ID, "label": "gw", "status": "active", "health": "healthy",
        "export_config": [], "network_config": {"primary": {}},
    }
    mcp = create_storage_gateways_mcp(client)

    async with Client(mcp) as c:
        via_tool = await c.call_tool("get_gateway_status", {"gateway_identifier": GATEWAY_ID})
        via_resource = await c.read_resource(f"storage-gateways://{GATEWAY_ID}/status")

    assert via_tool.data["operational_status"]["is_active"] is True
    # Compare parsed payloads: the tool and the resource serialize through
    # different encoders, so the JSON spacing differs on FastMCP 4.
    assert json.loads(via_resource[0].text) == json.loads(via_tool.content[0].text)
