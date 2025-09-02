# Dice Rolling MCP Server

This is a simple example MCP server that implements standard Dice Notation
parsing for rolling dice.

## Building

This project was built with the `uv` package/environment manager for Python on
Python version 3.13.

## Running

You can run the server on STDIO with a simply `python main.py` call but you'll
be better off using the `fastmcp` CLI:

```bash
uv run fastmcp run main.py:mcp
```

This will run via STDIO transport by default.

## Testing

You can test this server with:

```bash
uv run fastmcp dev main.py:mcp
```
