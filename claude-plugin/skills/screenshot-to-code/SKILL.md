---
name: screenshot-to-code
description: Convert screenshots, mockups, and designs into clean, functional frontend code using AI-powered code generation.
---

# Screenshot to Code

Convert screenshots, mockups, Figma designs, and screen recordings into clean, functional code.

## Available MCP Tools

### `screenshot_to_code`
The primary tool. Takes a screenshot/image and generates production-quality frontend code.

**Parameters:**
- `image_data` (required): Base64-encoded image data (screenshot, mockup, or design)
- `stack` (optional): Target framework. One of:
  - `html_tailwind` (default) — HTML + Tailwind CSS
  - `html_css` — HTML + vanilla CSS
  - `react_tailwind` — React + Tailwind CSS
  - `vue_tailwind` — Vue + Tailwind CSS
  - `bootstrap` — HTML + Bootstrap
  - `ionic_tailwind` — Ionic + Tailwind CSS
- `text_prompt` (optional): Additional instructions, e.g. "make the buttons rounded"

**Example usage:**
```
Use screenshot_to_code to convert this screenshot into React + Tailwind code.
```

### `generate_images`
Generate images from text descriptions using Replicate's image models.

**Parameters:**
- `prompts`: List of text descriptions for images to generate

**Requires:** `REPLICATE_API_KEY` environment variable

### `edit_images`
Edit or upscale existing images.

**Parameters:**
- `edits`: List of edit operations, each with:
  - `prompt`: Edit instruction
  - `image_urls`: Source image URLs (main image first, then references)
  - `aspect_ratio` (optional): Target aspect ratio

**Requires:** `REPLICATE_API_KEY` environment variable

### `extract_assets`
Extract visual assets (logos, icons, images) from screenshots using Gemini vision.

**Parameters:**
- `image_data`: Base64-encoded screenshot
- `asset_descriptions`: List of descriptions identifying each asset to extract

**Requires:** `GEMINI_API_KEY` environment variable

### `remove_backgrounds`
Remove backgrounds from images to create transparent PNGs.

**Parameters:**
- `image_urls`: List of image URLs to process

**Requires:** `REPLICATE_API_KEY` environment variable

## Setup

Set the following environment variables before using:

```bash
# At least one LLM key is required:
export OPENAI_API_KEY="sk-..."
export ANTHROPIC_API_KEY="sk-ant-..."
export GEMINI_API_KEY="..."

# Strongly recommended for image features:
export REPLICATE_API_KEY="r8_..."
```

## Tips

1. **Best results**: Use high-quality, full-page screenshots
2. **Stack choice**: `html_tailwind` produces the most concise output; `react_tailwind` is best for component-based projects
3. **Iterative refinement**: Use `text_prompt` to request specific changes after initial generation
4. **Asset extraction**: Use `extract_assets` first to reuse real logos/icons from the original design
5. **Image generation**: Use `generate_images` for placeholder images that `extract_assets` can't isolate
