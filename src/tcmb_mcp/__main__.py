"""Entry point for running TCMB MCP as a module."""

import sys


def main() -> None:
    """Main entry point."""
    from tcmb_mcp.server import run_server

    try:
        run_server()
    except KeyboardInterrupt:
        sys.exit(0)


if __name__ == "__main__":
    main()
