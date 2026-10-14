"""
Screenshot-to-Code MCP Server

Exposes the screenshot-to-code pipeline as MCP tools for Claude Code,
Claude Desktop, and other MCP-compatible clients.

Runs on stdio transport by default.
"""

import os
import sys

# ---------------------------------------------------------------------------
# Bootstrap: add the backend package to sys.path so we can reuse existing
# codegen, prompt, and image-generation modules without duplication.
# ---------------------------------------------------------------------------
_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
_BACKEND_DIR = os.path.normpath(os.path.join(_THIS_DIR, "..", "..", "backend"))
if _BACKEND_DIR not in sys.path:
    sys.path.insert(0, _BACKEND_DIR)

# Load .env from the backend directory (API keys, etc.)
from dotenv import load_dotenv  # noqa: E402

load_dotenv(os.path.join(_BACKEND_DIR, ".env"))

from mcp.server import MCPServer  # noqa: E402

from tools.screenshot_to_code import register_screenshot_tools  # noqa: E402
from tools.image_tools import register_image_tools  # noqa: E402
from tools.asset_tools import register_asset_tools  # noqa: E402

# ---------------------------------------------------------------------------
# Create and configure the MCP server
# ---------------------------------------------------------------------------
mcp = MCPServer("screenshot-to-code")


# Register all tool groups
register_screenshot_tools(mcp)
register_image_tools(mcp)
register_asset_tools(mcp)


# ---------------------------------------------------------------------------
# Resources: expose useful context to the LLM
# ---------------------------------------------------------------------------
@mcp.resource("info://screenshot-to-code/supported-stacks")
def get_supported_stacks() -> str:
    """List all supported output stacks for code generation."""
    return (
        "Supported stacks:\n"
        "- html_tailwind: HTML + Tailwind CSS\n"
        "- html_css: HTML + vanilla CSS\n"
        "- react_tailwind: React + Tailwind CSS\n"
        "- vue_tailwind: Vue + Tailwind CSS\n"
        "- bootstrap: HTML + Bootstrap\n"
        "- ionic_tailwind: Ionic + Tailwind CSS"
    )


@mcp.resource("info://screenshot-to-code/capabilities")
def get_capabilities() -> str:
    """Describe current capabilities based on configured API keys."""
    lines = ["Screenshot-to-Code Capabilities:"]

    openai_key = os.environ.get("OPENAI_API_KEY")
    anthropic_key = os.environ.get("ANTHROPIC_API_KEY")
    gemini_key = os.environ.get("GEMINI_API_KEY")
    replicate_key = os.environ.get("REPLICATE_API_KEY")

    if openai_key:
        lines.append("✅ OpenAI models available (GPT code generation)")
    else:
        lines.append("❌ OpenAI not configured")

    if anthropic_key:
        lines.append("✅ Anthropic models available (Claude code generation)")
    else:
        lines.append("❌ Anthropic not configured")

    if gemini_key:
        lines.append("✅ Gemini available (asset extraction, code generation)")
    else:
        lines.append("❌ Gemini not configured (asset extraction unavailable)")

    if replicate_key:
        lines.append("✅ Replicate available (image generation, editing, bg removal)")
    else:
        lines.append("❌ Replicate not configured (image tools unavailable)")

    if not any([openai_key, anthropic_key, gemini_key]):
        lines.append(
            "\n⚠️  At least one LLM key (OPENAI_API_KEY, ANTHROPIC_API_KEY, "
            "or GEMINI_API_KEY) is required for code generation."
        )

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Prompts: pre-built prompt templates
# ---------------------------------------------------------------------------
@mcp.prompt()
def screenshot_to_code_prompt(
    description: str = "a website screenshot",
    stack: str = "html_tailwind",
) -> str:
    """Generate a prompt for converting a screenshot to code."""
    return (
        f"Please use the screenshot_to_code tool to convert the provided "
        f"screenshot of {description} into clean, functional {stack} code. "
        f"After generation, review the output and suggest any improvements."
    )


@mcp.prompt()
def design_to_code_prompt(
    description: str = "a design mockup",
    stack: str = "react_tailwind",
    requirements: str = "",
) -> str:
    """Generate a prompt for converting a design mockup to code with requirements."""
    base = (
        f"Convert the provided design mockup ({description}) into production-quality "
        f"{stack} code using the screenshot_to_code tool."
    )
    if requirements:
        base += f"\n\nAdditional requirements:\n{requirements}"
    return base


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    mcp.run()
