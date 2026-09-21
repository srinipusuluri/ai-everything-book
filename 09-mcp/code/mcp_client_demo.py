"""
A real MCP client, using the official Python SDK (`pip install mcp`, v2.x).

This launches code/minimal_mcp_server.py as a subprocess and talks to it over
the actual stdio transport: newline-delimited JSON-RPC 2.0 messages on the
child's stdin/stdout. Nothing here is mocked -- `ClientSession` performs the
real `initialize` handshake, and every list/call/read below is a genuine
JSON-RPC round trip to the server process.

    python code/mcp_client_demo.py

We use `ClientSession` (the classic, explicit-handshake API) rather than the
newer high-level `Client` wrapper, specifically so the initialize/initialized
sequence below is visible and inspectable rather than hidden inside a context
manager -- that sequence is the thing this module's notes explain in detail,
and it is still exactly how essentially every deployed MCP server (including
`minimal_mcp_server.py`, run this way) is spoken to today.

A note on protocol versions, because it matters here: the SDK installed by
this repo (mcp>=2.2.0) implements the *current* MCP spec revision, 2026-07-28,
which redesigned initialization around a stateless, per-request model with no
handshake at all (see notes/01-core-concepts.md, section 7). But that SDK
remains fully "dual-era": it still speaks the classic, handshake-based
protocol (2025-06-18, 2025-11-25) that this script and virtually every MCP
server, tutorial, and deployed integration in the wild uses. That is exactly
what happens below -- session.initialize() negotiates the newest classic
revision, "2025-11-25" (the printed InitializeResult shows the exact string
the client and server settled on -- ClientSession negotiates downward from
its own newest supported version if the server asks for an older one). This
script deliberately exercises that classic handshake because it is the
version of the protocol you will actually meet on the ground; the notes cover
what changes if you're targeting a bare 2026-07-28 stateless server instead.
"""

from __future__ import annotations

import asyncio
import json
import os
import sys

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


def rule(title: str) -> None:
    print("\n" + "=" * 78 + f"\n{title}\n" + "=" * 78)


def show(label: str, obj) -> None:
    """Print the structured (JSON-able) representation of a protocol object.

    Every object here is a pydantic model that mirrors the JSON-RPC payload
    on the wire byte-for-byte (camelCase on the wire, snake_case as a Python
    attribute -- see notes/01-core-concepts.md). Dumping it to JSON is not a
    simulation of the protocol message; it *is* the protocol message, just
    already deserialized for you instead of shown as raw bytes.
    """
    if hasattr(obj, "model_dump"):
        payload = obj.model_dump(mode="json", exclude_none=True)
    else:
        payload = obj
    print(f"\n-- {label} --")
    print(json.dumps(payload, indent=2))


SERVER_SCRIPT = os.path.join(os.path.dirname(__file__), "minimal_mcp_server.py")

server_params = StdioServerParameters(
    command=sys.executable,   # launch the server with this same interpreter/venv
    args=[SERVER_SCRIPT],
)


async def run() -> None:
    rule("1. TRANSPORT: launching the server as a stdio subprocess")
    print(f"  Spawning: {sys.executable} {SERVER_SCRIPT}")
    print("  The client owns the child process; messages flow over its stdin/stdout,")
    print("  one JSON-RPC message per line, exactly as notes/01 describes.")

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:

            rule("2. INITIALIZATION HANDSHAKE")
            print("  Client sends: {\"method\": \"initialize\", \"params\": {\"protocolVersion\": ...,")
            print("                 \"capabilities\": {...}, \"clientInfo\": {...}}}")
            init_result = await session.initialize()
            print("  Server responds with its own protocolVersion, capabilities, and identity:")
            show("InitializeResult (the server's handshake reply)", init_result)
            print("\n  Client now sends: {\"method\": \"notifications/initialized\"} (a one-way")
            print("  notification, no response expected) -- ClientSession does this for you")
            print("  inside initialize(). The session is now in the Operation phase.")

            rule("3. TOOLS -- model-controlled: the model decides when to call these")
            tools = await session.list_tools()
            show("tools/list result", tools)

            print("\n  Calling search_catalog(query='herbert') -- a normal hit:")
            ok = await session.call_tool("search_catalog", arguments={"query": "herbert"})
            show("tools/call result (success)", ok)

            print("\n  Calling search_catalog(query='tolkien') -- no match, raises ToolError:")
            bad = await session.call_tool("search_catalog", arguments={"query": "tolkien"})
            show("tools/call result (is_error=True, but still a RESULT, not a protocol error)", bad)
            print(f"  bad.is_error = {bad.is_error}  <- the model reads bad.content and can retry")

            rule("4. RESOURCES -- application-controlled: the HOST decides to load these")
            resources = await session.list_resources()
            show("resources/list result", resources)
            print("\n  Note: list_resources() above did NOT run get_book() for any title --")
            print("  only resources/read for a *specific* URI runs the function.")

            print("\n  Reading books://Dune:")
            book = await session.read_resource("books://Dune")
            show("resources/read result", book)

            rule("5. PROMPTS -- user-controlled: a person picks this from a menu")
            prompts = await session.list_prompts()
            show("prompts/list result", prompts)

            print("\n  Rendering recommend_reading(genre='science fiction'):")
            rendered = await session.get_prompt(
                "recommend_reading", arguments={"genre": "science fiction"}
            )
            show("prompts/get result (becomes one or more chat messages)", rendered)

            rule("6. SHUTDOWN")
            print("  Exiting the `async with` blocks closes the ClientSession, then closes")
            print("  the child's stdin -- the documented stdio shutdown sequence: close stdin,")
            print("  wait for exit, SIGTERM, then SIGKILL if the server refuses to leave.")

    print("\nDone. Every message above was real JSON-RPC 2.0 traffic to a real MCP server.")


if __name__ == "__main__":
    asyncio.run(run())
