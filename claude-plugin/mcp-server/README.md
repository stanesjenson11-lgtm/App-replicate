# Screenshot to Code — MCP Server

An MCP (Model Context Protocol) server that exposes the screenshot-to-code
pipeline as tools consumable by Claude Code, Claude Desktop, and any other
MCP-compatible client.

## Quick Start

```bash
cd claude-plugin/mcp-server
pip install "mcp[cli]"       # or: poetry install
python server.py             # runs on stdio transport
```

## Tools

| Tool | Description |
|------|-------------|
| `screenshot_to_code` | Convert a screenshot/mockup into frontend code |
| `generate_images` | Generate images from text prompts (Replicate) |
| `edit_images` | Edit or upscale existing images (Replicate) |
| `extract_assets` | Extract visual assets from screenshots (Gemini) |
| `remove_backgrounds` | Remove image backgrounds (Replicate) |

## Environment Variables

```bash
# At least one LLM provider key:
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
GEMINI_API_KEY=...

# For image tools:
REPLICATE_API_KEY=r8_...
```

## Architecture

The MCP server imports directly from the existing `backend/` modules,
avoiding code duplication. It adds `backend/` to `sys.path` at startup
so all existing codegen, prompt, and image pipelines are reused as-is.
