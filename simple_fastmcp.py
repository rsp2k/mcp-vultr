#!/usr/bin/env python3

import sys
import os
from fastmcp import FastMCP

print("SIMPLE FASTMCP SERVER STARTING", file=sys.stderr)

# Create FastMCP server
mcp = FastMCP(name="vultr-dns-simple")

@mcp.tool
def test_tool() -> str:
    """A simple test tool"""
    return "Hello from Vultr DNS MCP!"

@mcp.tool
def list_domains() -> str:
    """List DNS domains"""
    return "This would list your DNS domains"

print("TOOLS REGISTERED, STARTING SERVER", file=sys.stderr)

if __name__ == "__main__":
    print("RUNNING MCP SERVER", file=sys.stderr)
    mcp.run()