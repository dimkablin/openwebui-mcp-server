"""Healthcheck router for mcp servers"""

from mcp.server.fastmcp import FastMCP
from starlette.requests import Request
from starlette.responses import PlainTextResponse


def add_healthcheck(mcp: FastMCP, path: str = "/health") -> FastMCP:
    """Registers a tiny /healthz endpoint: GET/HEAD → 200 OK."""
    if not path.startswith("/"):
        path = "/" + path

    @mcp.custom_route(
        path, methods=["GET", "HEAD"], name="health", include_in_schema=False
    )
    async def _health(_: Request) -> PlainTextResponse:
        return PlainTextResponse("OK", status_code=200)

    return mcp
