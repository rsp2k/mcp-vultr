#!/usr/bin/env python3

import asyncio
import sys
import os
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Resource, Tool, TextContent

async def main():
    # Set up API key
    api_key = os.getenv("VULTR_API_KEY")
    if not api_key:
        print("VULTR_API_KEY not set", file=sys.stderr)
        sys.exit(1)
    
    print(f"Starting server with API key: {api_key[:8]}...", file=sys.stderr)
    
    # Create minimal server
    server = Server("vultr-dns-debug")
    
    @server.list_tools()
    async def list_tools() -> list[Tool]:
        return [
            Tool(
                name="test_tool",
                description="A simple test tool",
                inputSchema={
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            )
        ]
    
    @server.call_tool()
    async def call_tool(name: str, arguments: dict) -> list[TextContent]:
        if name == "test_tool":
            return [TextContent(type="text", text="Test tool working!")]
        return [TextContent(type="text", text=f"Unknown tool: {name}")]
    
    print("Server configured, starting stdio...", file=sys.stderr)
    
    try:
        async with stdio_server() as (read_stream, write_stream):
            print("Running server...", file=sys.stderr)
            await server.run(read_stream, write_stream, None)
    except Exception as e:
        print(f"Server error: {e}", file=sys.stderr)
        raise

if __name__ == "__main__":
    asyncio.run(main())