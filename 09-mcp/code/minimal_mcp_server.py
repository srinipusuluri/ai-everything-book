"""
A real MCP server, using the official Python SDK (`pip install mcp`, v2.x).

This is not a simulation. `MCPServer` speaks the actual Model Context Protocol:
JSON-RPC 2.0 messages, the standard `initialize` handshake, and the three
wire methods (`tools/list`/`tools/call`, `resources/list`/`resources/read`,
`prompts/list`/`prompts/get`) exactly as any MCP client -- Claude Desktop,
Claude Code, an IDE plugin, or the client script next to this file -- expects.

Run it standalone to see it idle on stdio (Ctrl+C to quit):
    python code/minimal_mcp_server.py
Run it *from* a client to see it actually do something:
    python code/mcp_client_demo.py

--------------------------------------------------------------------------
THE ONE THING TO INTERNALISE: each primitive has a different CONTROL LOCUS
--------------------------------------------------------------------------
  TOOL      -> the MODEL decides when to call it.        ~ a POST endpoint.
  RESOURCE  -> the APPLICATION (host) decides to load it. ~ a GET endpoint.
  PROMPT    -> the USER decides to invoke it.             a menu item / slash command.

Mixing these up is the most common MCP design mistake: putting a
"read this file" action behind a Tool (now the model has to *think* to fetch
context that should have just been there) or putting an irreversible action
behind a Resource (nothing stops a host from silently loading it into every
conversation -- resources are meant to be read without side effects).
"""

from __future__ import annotations

from mcp.server import MCPServer
from mcp.server.mcpserver.exceptions import ResourceNotFoundError, ToolError

# ---------------------------------------------------------------------------
# A tiny in-memory "backend". In a real server this would be a database, a
# filesystem, a SaaS API -- an MCP server is a thin, standardised adapter in
# front of something that already exists. It invents no new backend concepts.
# ---------------------------------------------------------------------------
CATALOG: dict[str, dict[str, str]] = {
    "Dune": {"author": "Frank Herbert", "genre": "science fiction", "year": "1965"},
    "Neuromancer": {"author": "William Gibson", "genre": "science fiction", "year": "1984"},
    "The Left Hand of Darkness": {"author": "Ursula K. Le Guin", "genre": "science fiction", "year": "1969"},
}

mcp = MCPServer(
    name="bookshelf",
    title="Bookshelf Catalog Server",
    instructions=(
        "Gives access to a small book catalog. Use the search_catalog tool to find a book "
        "by keyword; read a books:// resource to get one entry verbatim; use the "
        "recommend_reading prompt to start a recommendation conversation."
    ),
)


# ---------------------------------------------------------------------------
# TOOL -- model-controlled action, like a POST endpoint.
#
# The model reads `search_catalog`'s NAME and DOCSTRING to decide whether and
# when to call it, and its type hints to build the JSON Schema it must supply
# arguments against. There is no separate schema to keep in sync by hand --
# that is the whole point of the decorator-based SDK. The description you
# write here is not documentation for humans; it is the interface the model
# reasons over, so vague verbs ("process", "handle") make the model guess.
# ---------------------------------------------------------------------------
@mcp.tool()
def search_catalog(query: str) -> str:
    """Search the book catalog by title, author, or genre (case-insensitive substring match)."""
    q = query.lower()
    hits = [
        title
        for title, info in CATALOG.items()
        if q in title.lower() or q in info["author"].lower() or q in info["genre"].lower()
    ]
    if not hits:
        # ToolError -> the call still SUCCEEDS at the protocol level (a
        # JSON-RPC result, not an error), but the result carries
        # is_error=True and this exact message in `content`. The MODEL
        # reads that message and can retry with a better query -- this is
        # what "an error the model can act on" means in practice. Never
        # just `return` an error string: a returned string has
        # is_error=False, so the model (and every client UI) reads it as
        # a successful answer.
        raise ToolError(f"No catalog entries match {query!r}. Try a broader term.")
    return f"Found {len(hits)} match(es): " + "; ".join(hits)


# ---------------------------------------------------------------------------
# RESOURCE -- application-controlled context, like a GET endpoint.
#
# The model never "calls" a resource. The HOST decides when to read
# `books://{title}` and put its contents in front of the model -- because the
# user clicked it, because the host's own retrieval logic picked it, because
# it's pinned in a project config. The URI is the address; nothing here is a
# verb. Listing (`resources/list`) is cheap and does not run this function --
# it only runs when a specific URI is actually read.
# ---------------------------------------------------------------------------
@mcp.resource("books://{title}")
def get_book(title: str) -> str:
    """The catalog entry for one book, addressed by exact title."""
    if title not in CATALOG:
        # ResourceNotFoundError -> the SDK turns this into the protocol
        # error the spec assigns to a missing resource (JSON-RPC code
        # -32602, with the requested URI echoed back in `error.data`).
        # Unlike a tool, a resource read has no "succeeded but flagged
        # is_error" path: it either returns contents or the request fails.
        raise ResourceNotFoundError(f"No book titled {title!r} in the catalog.")
    info = CATALOG[title]
    return f"{title} by {info['author']} ({info['year']}), genre: {info['genre']}"


# ---------------------------------------------------------------------------
# PROMPT -- user-controlled workflow, a template the person picks.
#
# A prompt is not something the model reaches for on its own and not
# something the host silently loads. It shows up as a slash command or a
# menu item; the USER chooses it and fills in `genre`, and the rendered
# text is inserted into the conversation as if they had typed it themselves.
# ---------------------------------------------------------------------------
@mcp.prompt(title="Recommend a book")
def recommend_reading(genre: str = "science fiction") -> str:
    """Ask for a reading recommendation in a given genre from the catalog."""
    matches = [t for t, info in CATALOG.items() if genre.lower() in info["genre"].lower()]
    if matches:
        return (
            f"From this catalog, recommend one {genre} book among {matches} and explain "
            f"in two sentences why it's a good starting point for a new reader of the genre."
        )
    return f"None of the catalog's books are tagged {genre!r}. Suggest a close genre from the catalog instead."


if __name__ == "__main__":
    # stdio is the transport for a server launched as a local subprocess by
    # its host (Claude Desktop, Claude Code, an IDE) -- messages travel over
    # this process's stdin/stdout, one JSON-RPC message per line. This is
    # the default transport for MCPServer.run(); see notes/01-core-concepts.md
    # for when you'd reach for Streamable HTTP (a remote, shared server)
    # instead.
    mcp.run(transport="stdio")
