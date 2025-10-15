# mcp_server/tools/__init__.py
from __future__ import annotations

import asyncio

from mcp.server.fastmcp import Context, FastMCP


class Tools:
    """
    Tool provider that registers instance methods as MCP tools.

    Usage:
        Tools(mcp)  # registers tools on init
    """

    def __init__(self, mcp_instance: FastMCP) -> None:
        # echo(message: str) -> str
        mcp_instance.add_tool(
            self.echo,
            name="echo",
            description=
                "Echo back the provided message (useful for connectivity checks).",
        )

        # calculate(a: float, b: float, operation: str = 'add') -> float
        mcp_instance.add_tool(
            self.calculate,
            name="calculate",
            description=(
                "Perform a basic arithmetic operation on two numbers. "
                "Supported operations: add, subtract, multiply, divide."
            ),
        )

        # long_task(iterations: int, ctx: Context) -> str  (reports progress)
        mcp_instance.add_tool(
            self.long_task,
            name="long_task",
            description=
                "Run a long-running operation and report progress to the client.",
        )

        # fetch_data(url: str, ctx: Context) -> str
        mcp_instance.add_tool(
            self.fetch_data,
            name="fetch_data",
            description=
                "Fetch text data from the given URL and return the response body.",
        )

    # -------- tool methods --------

    def echo(self, message: str) -> str:
        """Echo a message back."""
        return f"Echo: {message}"

    async def calculate(self, a: float, b: float, operation: str = "add") -> float:
        """Perform a calculation on two numbers."""
        if operation == "add":
            return a + b
        if operation == "subtract":
            return a - b
        if operation == "multiply":
            return a * b
        if operation == "divide":
            if b == 0:
                raise ValueError("Cannot divide by zero")
            return a / b
        raise ValueError(f"Unknown operation: {operation!r}")

    async def long_task(self, iterations: int, ctx: Context) -> str:
        """A long-running task that reports progress via Context."""
        ctx.info(f"Starting long task with {iterations} iterations")
        for i in range(iterations):
            ctx.debug(f"Processing iteration {i + 1}/{iterations}")
            await ctx.report_progress(
                i, iterations, message=f"Processing {i + 1}/{iterations}"
            )
            await asyncio.sleep(0.1)
        ctx.info("Long task completed")
        return f"Completed {iterations} iterations"

    async def fetch_data(self, url: str, ctx: Context) -> str:
        """
        Fetch data from a URL and return the
        response text (handles common errors).
        """
        import httpx

        try:
            ctx.info(f"Fetching data from {url}")
            async with httpx.AsyncClient() as client:
                resp = await client.get(url, timeout=10.0)
                resp.raise_for_status()
                return resp.text
        except httpx.RequestError as e:
            msg = f"Connection error: {e}"
            ctx.error(msg)
            return msg
        except httpx.HTTPStatusError as e:
            msg = f"HTTP error {e.response.status_code}: {e.response.reason_phrase}"
            ctx.error(msg)
            return msg
        except Exception as e:  # noqa: BLE001
            msg = f"Unexpected error: {e}"
            ctx.error(msg)
            return msg
