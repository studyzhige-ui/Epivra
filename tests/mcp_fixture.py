"""Local protocol fixture; never calls a model or external service."""

from mcp.server import MCPServer

server = MCPServer("test-materials")
calls = 0


@server.tool(structured_output=True)
def lookup(query: str) -> dict[str, object]:
    """Return a source record for a fixture query."""
    global calls
    calls += 1
    return {
        "query": query,
        "text": "A complete source record",
        "value": 7,
        "calls": calls,
    }


@server.resource("fixture://material")
def material() -> str:
    return "Original resource text 中文"


if __name__ == "__main__":
    server.run()
