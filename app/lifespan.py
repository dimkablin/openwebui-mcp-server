"""
Main MCP server implementation.
This file initializes the FastMCP server and imports all tools, resources, and prompts.
"""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass

from mcp.server.fastmcp import FastMCP

# Import config management
from app.config import load_config


@dataclass
class AppContext:
    """
    Type-safe application context container.
    Store any application-wide state or connections here.
    """

    config: dict


@asynccontextmanager
async def app_lifespan(server_: FastMCP) -> AsyncIterator[AppContext]:
    """
    Application lifecycle manager.
    Handles startup and shutdown operations with proper resource management.

    Args:
        server: The FastMCP server instance

    Yields:
        The application context with initialized resources
    """
    # Load configuration
    config = load_config()

    # Initialize connections and resources
    print(f"🚀 Server {server_.name} starting up...")

    try:
        # Create and yield the app context
        yield AppContext(config=config)
    finally:
        # Clean up resources on shutdown
        print("🛑 Server shutting down...")
