"""
Image generation, editing, and background removal MCP tools.

These tools wrap the existing Replicate-backed image pipeline from the
screenshot-to-code backend.
"""

import asyncio
import os
from typing import Any, Dict, List, Optional

from mcp.server import MCPServer

# Backend imports (backend/ is on sys.path via server.py)
from config import REPLICATE_API_KEY
from image_generation.generation import process_tasks
from image_generation.replicate import (
    P_IMAGE_EDIT_ASPECT_RATIOS,
    PImageEditAspectRatio,
    edit_image as edit_image_once,
    remove_background as remove_background_once,
)


def _require_replicate_key() -> str:
    """Return the Replicate API key or raise a clear error."""
    key = REPLICATE_API_KEY or os.environ.get("REPLICATE_API_KEY")
    if not key:
        raise ValueError(
            "REPLICATE_API_KEY is required for image tools. "
            "Set it in backend/.env or as an environment variable."
        )
    return key


def register_image_tools(mcp: MCPServer) -> None:
    """Register image generation, editing, and background removal tools."""

    @mcp.tool()
    async def generate_images(prompts: list[str]) -> str:
        """Generate images from text descriptions using Replicate's image models.

        Args:
            prompts: List of text descriptions for images to generate.
                     Each prompt produces one image. Be descriptive —
                     include details about appearance, style, colors, etc.

        Returns:
            Newline-separated list of generated image URLs, or error messages
            for failed generations.
        """
        try:
            api_key = _require_replicate_key()
        except ValueError as e:
            return str(e)

        if not prompts:
            return "Error: At least one prompt is required."

        try:
            results = await process_tasks(
                prompts=prompts,
                api_key=api_key,
                _base_url=None,
                _model="replicate",
            )

            output_lines: List[str] = []
            for i, (prompt, url) in enumerate(zip(prompts, results)):
                if url:
                    output_lines.append(f"Image {i + 1}: {url}")
                else:
                    output_lines.append(f"Image {i + 1}: FAILED — prompt was: {prompt}")

            return "\n".join(output_lines)
        except Exception as e:
            return f"Error generating images: {str(e)}"

    @mcp.tool()
    async def edit_images(edits: list[dict]) -> str:
        """Edit or upscale one or more images using Replicate.

        Args:
            edits: List of edit operations. Each edit is a dict with:
                   - prompt (str, required): Clear edit instruction
                   - image_urls (list[str], required): Source image URLs
                     (main image first, then references)
                   - aspect_ratio (str, optional): Target aspect ratio.
                     One of: match_input_image, 1:1, 16:9, 9:16, 4:3, 3:4, 3:2, 2:3

        Returns:
            Newline-separated list of edited image URLs.
        """
        try:
            api_key = _require_replicate_key()
        except ValueError as e:
            return str(e)

        if not edits:
            return "Error: At least one edit operation is required."

        output_lines: List[str] = []
        tasks = []

        for i, edit in enumerate(edits):
            prompt = edit.get("prompt", "")
            image_urls = edit.get("image_urls", [])
            aspect_ratio = edit.get("aspect_ratio", "match_input_image")

            if not prompt:
                output_lines.append(f"Edit {i + 1}: SKIPPED — missing prompt")
                continue
            if not image_urls:
                output_lines.append(f"Edit {i + 1}: SKIPPED — missing image_urls")
                continue

            # Validate aspect ratio
            valid_ratios = list(P_IMAGE_EDIT_ASPECT_RATIOS)
            if aspect_ratio not in valid_ratios:
                aspect_ratio = "match_input_image"

            tasks.append((i, prompt, image_urls, aspect_ratio))

        async def run_single_edit(
            index: int,
            prompt: str,
            image_urls: list[str],
            aspect_ratio: str,
        ) -> str:
            try:
                result_url = await edit_image_once(
                    prompt=prompt,
                    image_urls=image_urls,
                    api_token=api_key,
                    aspect_ratio=aspect_ratio,  # type: ignore[arg-type]
                )
                return f"Edit {index + 1}: {result_url}"
            except Exception as e:
                return f"Edit {index + 1}: FAILED — {str(e)}"

        if tasks:
            results = await asyncio.gather(
                *[run_single_edit(i, p, u, a) for i, p, u, a in tasks]
            )
            output_lines.extend(results)

        return "\n".join(output_lines) if output_lines else "No edits were processed."

    @mcp.tool()
    async def remove_backgrounds(image_urls: list[str]) -> str:
        """Remove backgrounds from one or more images, producing transparent PNGs.

        Args:
            image_urls: List of image URLs to process.

        Returns:
            Newline-separated list of processed image URLs with transparent
            backgrounds, in the same order as the input.
        """
        try:
            api_key = _require_replicate_key()
        except ValueError as e:
            return str(e)

        if not image_urls:
            return "Error: At least one image URL is required."

        async def remove_single(index: int, url: str) -> str:
            try:
                result_url = await remove_background_once(url, api_key)
                return f"Image {index + 1}: {result_url}"
            except Exception as e:
                return f"Image {index + 1}: FAILED — {str(e)}"

        results = await asyncio.gather(
            *[remove_single(i, url) for i, url in enumerate(image_urls)]
        )
        return "\n".join(results)
