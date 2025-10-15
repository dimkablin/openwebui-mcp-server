"""Journal Server - дневник и контекст"""

import click
from mcp.server.fastmcp import FastMCP

from app.healthcheck import add_healthcheck
from app.lifespan import app_lifespan

from .prompts import Prompts
from .resources import Resources
from .tools import Tools


# ---- CLI ----
@click.command(context_settings={"help_option_names": ["-h", "--help"]})
@click.option("--host", default="0.0.0.0", show_default=True, help="Host interface.")
@click.option("--port", default=8003, type=int, show_default=True, help="Port number.")
@click.option(
    "--path",
    default="/journal",
    type=str,
    show_default=True,
    help="URL prefix of mcp server.",
)
def main(host: str = None, port: int = None, path: str = None) -> None:
    """Run Journal MCP server over Streamable HTTP."""
    mcp = FastMCP(
        "journal-server",
        lifespan=app_lifespan,
        host=host,
        port=port,
        streamable_http_path=path,
    )

    # добавляем health check
    add_healthcheck(mcp)

    # Регистрируем все промтпы, ресурсы и тулы в мсп
    Prompts(mcp)
    Resources(mcp)
    Tools(mcp)

    mcp.run(transport="streamable-http")


if __name__ == "__main__":
    main()
