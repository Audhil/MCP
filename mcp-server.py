from mcp.server.fastmcp import FastMCP

app = FastMCP("Demo of MCP")


@app.tool()
def add(x: int, y: int) -> int:
    """Add two numbers together."""
    return x + y


@app.resource("greeting://{name}")
def get_greeting(name: str) -> str:
    """Return a greeting message."""
    return f"Hello, {name}!"


@app.prompt()
def greet_user(name: str, style: str = "friendly") -> str:
    """Return a greeting message."""
    styles = {
        "friendly": f"Hello, {name}, friendly!",
        "normal": f"Hello, {name}, normal!",
        "formal": f"Good day, {name}, formal!",
        "casual": f"Hello, {name}, casual!",
    }
    return f"{styles.get(style, styles["friendly"])} for someone named: {name}!"
