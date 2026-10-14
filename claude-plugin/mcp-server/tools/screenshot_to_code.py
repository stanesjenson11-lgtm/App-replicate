"""
screenshot_to_code MCP tool

The core tool that converts a screenshot/image into frontend code by
driving the existing backend pipeline end-to-end.
"""

import asyncio
import base64
import os
from typing import Any, Dict, List, Optional

from mcp.server import MCPServer

# These imports come from the backend (added to sys.path in server.py)
from config import (
    ANTHROPIC_API_KEY,
    GEMINI_API_KEY,
    OPENAI_API_KEY,
    OPENAI_BASE_URL,
    REPLICATE_API_KEY,
)
from llm import Llm
from prompts.pipeline import build_prompt_messages
from prompts.prompt_types import Stack, UserTurnInput
from agent.engine import AgentEngine


# Default model preferences per provider
_DEFAULT_MODELS: Dict[str, Llm] = {
    "gemini": Llm.GEMINI_3_FLASH_PREVIEW_HIGH,
    "anthropic": Llm.CLAUDE_OPUS_4_8_MEDIUM,
    "openai": Llm.GPT_5_5_LOW,
}


def _pick_model() -> Llm:
    """Choose the best available model based on configured API keys."""
    if GEMINI_API_KEY:
        return _DEFAULT_MODELS["gemini"]
    if ANTHROPIC_API_KEY:
        return _DEFAULT_MODELS["anthropic"]
    if OPENAI_API_KEY:
        return _DEFAULT_MODELS["openai"]
    raise ValueError(
        "No LLM API key configured. Set at least one of: "
        "OPENAI_API_KEY, ANTHROPIC_API_KEY, GEMINI_API_KEY"
    )


def register_screenshot_tools(mcp: MCPServer) -> None:
    """Register the screenshot_to_code tool with the MCP server."""

    @mcp.tool()
    async def screenshot_to_code(
        image_data: str,
        stack: str = "html_tailwind",
        text_prompt: str = "",
    ) -> str:
        """Convert a screenshot or design mockup into clean, functional frontend code.

        Args:
            image_data: Base64-encoded image data (PNG, JPEG, or WebP).
                        Can optionally include the data URI prefix
                        (e.g. "data:image/png;base64,...").
            stack: Target output stack. One of: html_tailwind, html_css,
                   react_tailwind, vue_tailwind, bootstrap, ionic_tailwind.
            text_prompt: Optional additional instructions for the generation
                         (e.g. "make the buttons rounded", "use a dark theme").

        Returns:
            The generated HTML/code as a string.
        """
        # Validate stack
        valid_stacks = [
            "html_css",
            "html_tailwind",
            "react_tailwind",
            "bootstrap",
            "ionic_tailwind",
            "vue_tailwind",
        ]
        if stack not in valid_stacks:
            return f"Error: Invalid stack '{stack}'. Must be one of: {', '.join(valid_stacks)}"

        # Normalize image data — ensure it has the data URI prefix
        if not image_data.startswith("data:"):
            # Try to detect image type from base64 header
            image_data = f"data:image/png;base64,{image_data}"

        # Build the prompt input
        prompt: UserTurnInput = {
            "text": text_prompt or "Convert this screenshot to code.",
            "images": [image_data],
            "videos": [],
        }

        # Build prompt messages using the existing pipeline
        try:
            prompt_messages = await build_prompt_messages(
                stack=stack,  # type: ignore[arg-type]
                input_mode="image",
                generation_type="create",
                prompt=prompt,
                history=[],
                file_state=None,
                image_generation_enabled=bool(REPLICATE_API_KEY),
            )
        except Exception as e:
            return f"Error building prompt: {str(e)}"

        # Pick the best available model
        try:
            model = _pick_model()
        except ValueError as e:
            return str(e)

        # Collector for generated code — the MCP tool doesn't use WebSocket,
        # so we capture the final output via a lightweight message sink.
        generated_code: List[str] = []

        async def noop_send_message(
            msg_type: str,
            value: Optional[str],
            variant_index: int,
            data: Optional[Dict[str, Any]],
            event_id: Optional[str],
        ) -> None:
            """Capture setCode messages; discard everything else."""
            if msg_type == "setCode" and value:
                generated_code.clear()
                generated_code.append(value)

        # Run the agent engine
        try:
            engine = AgentEngine(
                send_message=noop_send_message,
                variant_index=0,
                openai_api_key=OPENAI_API_KEY,
                openai_base_url=OPENAI_BASE_URL,
                anthropic_api_key=ANTHROPIC_API_KEY,
                gemini_api_key=GEMINI_API_KEY,
                replicate_api_key=REPLICATE_API_KEY,
                should_generate_images=bool(REPLICATE_API_KEY),
                should_extract_assets=bool(GEMINI_API_KEY),
            )
            result = await engine.run(model, prompt_messages)
            return result if result else "Error: No code was generated."
        except Exception as e:
            return f"Error during code generation: {str(e)}"

    @mcp.tool()
    async def update_code(
        current_code: str,
        instruction: str,
        stack: str = "html_tailwind",
    ) -> str:
        """Update existing frontend code based on an instruction.

        Args:
            current_code: The current HTML/code to modify.
            instruction: Description of what to change
                         (e.g. "change the header color to blue").
            stack: The stack of the existing code.

        Returns:
            The updated HTML/code as a string.
        """
        valid_stacks = [
            "html_css",
            "html_tailwind",
            "react_tailwind",
            "bootstrap",
            "ionic_tailwind",
            "vue_tailwind",
        ]
        if stack not in valid_stacks:
            return f"Error: Invalid stack '{stack}'. Must be one of: {', '.join(valid_stacks)}"

        prompt: UserTurnInput = {
            "text": instruction,
            "images": [],
            "videos": [],
        }

        file_state = {"path": "index.html", "content": current_code}

        try:
            prompt_messages = await build_prompt_messages(
                stack=stack,  # type: ignore[arg-type]
                input_mode="text",
                generation_type="update",
                prompt=prompt,
                history=[],
                file_state=file_state,
                image_generation_enabled=bool(REPLICATE_API_KEY),
            )
        except Exception as e:
            return f"Error building prompt: {str(e)}"

        try:
            model = _pick_model()
        except ValueError as e:
            return str(e)

        async def noop_send_message(
            msg_type: str,
            value: Optional[str],
            variant_index: int,
            data: Optional[Dict[str, Any]],
            event_id: Optional[str],
        ) -> None:
            pass

        try:
            engine = AgentEngine(
                send_message=noop_send_message,
                variant_index=0,
                openai_api_key=OPENAI_API_KEY,
                openai_base_url=OPENAI_BASE_URL,
                anthropic_api_key=ANTHROPIC_API_KEY,
                gemini_api_key=GEMINI_API_KEY,
                replicate_api_key=REPLICATE_API_KEY,
                should_generate_images=bool(REPLICATE_API_KEY),
                should_extract_assets=False,
                initial_file_state=file_state,
            )
            result = await engine.run(model, prompt_messages)
            return result if result else "Error: No updated code was generated."
        except Exception as e:
            return f"Error during code update: {str(e)}"
