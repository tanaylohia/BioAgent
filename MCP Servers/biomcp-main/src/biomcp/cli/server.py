from enum import Enum
from typing import Annotated

import typer
from dotenv import load_dotenv

from .. import logger, mcp_app  # mcp_app is already instantiated in core.py

# Load environment variables from .env file
load_dotenv()

server_app = typer.Typer(help="Server operations")


class ServerMode(str, Enum):
    STDIO = "stdio"
    WORKER = "worker"


@server_app.command("run")
def run_server(
    mode: Annotated[
        ServerMode,
        typer.Option(
            help="Server mode: stdio (local) or worker (Cloudflare Worker/SSE)",
            case_sensitive=False,
        ),
    ] = ServerMode.STDIO,
):
    """Run the BioMCP server with selected transport mode."""

    if mode == ServerMode.STDIO:
        logger.info("Starting MCP server with STDIO transport:")
        mcp_app.run(transport="stdio")
    elif mode == ServerMode.WORKER:
        logger.info("Starting MCP server with Worker/SSE transport")
        try:
            import uvicorn

            from ..workers.worker import app

            uvicorn.run(
                app,
                host="0.0.0.0",  # noqa: S104 - Required for Docker container networking
                port=8000,
                log_level="info",
            )
        except ImportError as e:
            logger.error(f"Failed to start worker/sse mode: {e}")
            raise typer.Exit(1) from e
        except Exception as e:
            logger.error(f"An unexpected error occurred: {e}", exc_info=True)
            raise typer.Exit(1) from e
