"""
Sample MCP resources implementation.
This file contains example resource implementations to demonstrate different patterns.
"""

import datetime as dt
import os
from pathlib import Path
from typing import Any, Dict

from mcp.server.fastmcp import Context, FastMCP


class Resources:
    """
    Resource provider that registers instance methods as MCP resources.

    Usage:
        resources = Resources(mcp)  # registers resources on init
    """

    def __init__(self, mcp_instance: FastMCP) -> None:
        mcp_instance.resource(
            uri="resource://{name}/details",
            name="Example resource with metadata",
            description=
                "Return the provided name, current server time, and the request ID.",
            mime_type="application/json",
        )(self.get_details)

        mcp_instance.resource(
            uri="file://{path}.md",
            name="Markdown file reader",
            description=(
                "Read a .md file from the configured RESOURCE_DIR "
                "(default: ./resources). Paths are validated to prevent "
                "directory traversal."
            ),
            mime_type="text/markdown",
        )(self.file_resource)

    async def get_details(self, name: str, ctx: Context) -> Dict[str, Any]:
        """Return structured details for a given name."""
        return {
            "name": name,
            "time": dt.datetime.now(dt.timezone.utc).isoformat(),
            "request_id": getattr(ctx, "request_id", None),
        }

    def file_resource(self, path: str) -> str:
        """
        Read a markdown file from RESOURCE_DIR (default: ./resources/<path>.md).
        Validates the path to avoid traversal.
        """
        base_dir = os.environ.get("RESOURCE_DIR", "resources")
        base = Path(base_dir).resolve()

        # Normalize & validate input path
        candidate = (base / f"{path}.md").resolve()
        if base not in candidate.parents and candidate != base:
            return f"Invalid path: {path}"

        if not candidate.is_file():
            return f"File not found: {path}.md"

        try:
            return candidate.read_text(encoding="utf-8")
        except Exception as e:  # noqa: BLE001 (простой ответ пользователю)
            return f"Error reading file: {e}"
