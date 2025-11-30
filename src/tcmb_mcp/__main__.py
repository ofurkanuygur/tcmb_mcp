"""Entry point for running TCMB MCP Pro as a module."""

import asyncio
import sys


def main() -> None:
    """Main entry point."""
    from tcmb_mcp.server import run_server

    try:
        asyncio.run(run_server())
    except KeyboardInterrupt:
        sys.exit(0)


if __name__ == "__main__":
    main()
