"""
Asset extraction MCP tool.

Wraps the existing Gemini-based asset extraction pipeline to extract
visual assets (logos, icons, images) from screenshots.
"""

import base64
import os
from typing import Any, Dict, List

from mcp.server import MCPServer

# Backend imports (backend/ is on sys.path via server.py)
from config import GEMINI_API_KEY
from asset_extraction import (
    extract_assets as run_asset_extraction,
    AssetDetection,
)


def register_asset_tools(mcp: MCPServer) -> None:
    """Register asset extraction tools with the MCP server."""

    @mcp.tool()
    async def extract_assets(
        image_data: str,
        asset_descriptions: list[str],
    ) -> str:
        """Extract visual assets from a screenshot using Gemini vision.

        Identifies and crops individual visual elements (logos, icons, images,
        illustrations) from the input screenshot based on your descriptions.

        Args:
            image_data: Base64-encoded screenshot image (PNG, JPEG, or WebP).
                        Can optionally include the data URI prefix.
            asset_descriptions: List of descriptions identifying each asset
                                to extract. Be specific about location,
                                appearance, and context. For example:
                                - "The blue logo in the top-left header"
                                - "The hero image of a mountain landscape"
                                - "The small cart icon next to the price"

        Returns:
            Summary of extracted assets with their URLs, or error details
            for assets that could not be isolated.
        """
        gemini_key = GEMINI_API_KEY or os.environ.get("GEMINI_API_KEY")
        if not gemini_key:
            return (
                "Error: GEMINI_API_KEY is required for asset extraction. "
                "Set it in backend/.env or as an environment variable."
            )

        if not asset_descriptions:
            return "Error: At least one asset_description is required."

        # Normalize image data
        if not image_data.startswith("data:"):
            image_data = f"data:image/png;base64,{image_data}"

        # Build the arguments in the format expected by the backend
        tool_args: Dict[str, Any] = {
            "asset_descriptions": asset_descriptions,
        }

        try:
            # Import and use the backend's extract_assets tool runner
            from agent.tools.extract_assets import run_extract_assets
            from agent.tools.types import ToolExecutionResult

            result: ToolExecutionResult = await run_extract_assets(
                args=tool_args,
                gemini_api_key=gemini_key,
                input_images=[image_data],
                asset_base_url="",
            )

            if not result.ok:
                error_info = result.result if isinstance(result.result, dict) else {}
                return f"Asset extraction failed: {error_info.get('error', 'Unknown error')}"

            # Format the results for the MCP response
            output_lines = ["Extracted assets:"]
            if isinstance(result.result, dict):
                assets = result.result.get("assets", [])
                if isinstance(assets, list):
                    for i, asset in enumerate(assets):
                        if isinstance(asset, dict):
                            status = asset.get("status", "unknown")
                            url = asset.get("public_url", "")
                            desc = asset.get("description", f"Asset {i + 1}")
                            if status == "resolved" and url:
                                output_lines.append(
                                    f"  ✅ {desc}: {url}"
                                )
                            else:
                                reason = asset.get("reason", "Could not isolate")
                                output_lines.append(
                                    f"  ❌ {desc}: {reason}"
                                )

                # Include summary if available
                summary = result.summary
                if isinstance(summary, dict):
                    resolved = summary.get("resolved", 0)
                    total = summary.get("total", 0)
                    output_lines.append(f"\nResolved {resolved}/{total} assets.")

            return "\n".join(output_lines)

        except Exception as e:
            return f"Error extracting assets: {str(e)}"
