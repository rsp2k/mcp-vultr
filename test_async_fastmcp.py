#!/usr/bin/env python3

import asyncio
import sys
from fastmcp import FastMCP

print("TESTING ASYNC FASTMCP PATTERNS", file=sys.stderr)

# Create FastMCP server
mcp = FastMCP(name="async-test")

@mcp.tool
def sync_tool() -> str:
    """A synchronous test tool"""
    return "Sync tool working"

@mcp.tool
async def async_tool() -> str:
    """An asynchronous test tool"""
    await asyncio.sleep(0.1)  # Simulate async work
    return "Async tool working"

@mcp.tool
async def async_tool_with_params(name: str, count: int = 1) -> dict:
    """An async tool with parameters"""
    await asyncio.sleep(0.1)
    return {
        "message": f"Hello {name}",
        "count": count,
        "status": "async success"
    }

print("TOOLS REGISTERED, STARTING SERVER", file=sys.stderr)

if __name__ == "__main__":
    print("RUNNING ASYNC TEST SERVER", file=sys.stderr)
    mcp.run()