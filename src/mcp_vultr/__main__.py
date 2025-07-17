"""
Main entry point for running the Vultr DNS FastMCP server.
"""

import sys
from .fastmcp_server import run_server


if __name__ == "__main__":
    try:
        run_server()
    except KeyboardInterrupt:
        print("Server stopped by user", file=sys.stderr)
        sys.exit(0)
    except Exception as e:
        print(f"Server error: {e}", file=sys.stderr)
        sys.exit(1)