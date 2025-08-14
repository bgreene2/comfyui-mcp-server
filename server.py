#!/usr/bin/env python3
"""
ComfyUI MCP Server
A Model Context Protocol server for ComfyUI image generation.

This server provides:
- Image generation through ComfyUI
- Support for different aspect ratios
- Markdown image links for easy viewing
"""

import asyncio
import anyio
import datetime
import io
import json
import logging
import os
import re
import requests
import sys
import time
import urllib.parse
import urllib.request
import uuid
import yaml
from pathlib import Path
from typing import Any, Dict, List
from dotenv import load_dotenv
from PIL import Image
import mcp.types as types
from mcp.server import Server
from mcp.server.models import InitializationOptions
import mcp.server.stdio

# Load environment variables from .env file, overriding with os environment variables if present
load_dotenv()

# Get environment variables
comfyui_host = os.getenv("COMFYUI_HOST", "127.0.0.1")
comfyui_port = os.getenv("COMFYUI_PORT", "8188")
output_dir = os.getenv("OUTPUT_DIR", "./output")
image_app_base_url = os.getenv("IMAGE_APP_BASE_URL", "http://127.0.0.1:8081/view")
comfyui_workflow_name = os.getenv("COMFYUI_WORKFLOW_NAME", "flux-krea")
working_dir = os.getenv("WORKING_DIR", None)
if working_dir is None:
    working_dir = os.getcwd()

# Validate required environment variables
required_vars = ["COMFYUI_HOST", "COMFYUI_PORT", "OUTPUT_DIR", "IMAGE_APP_BASE_URL", "COMFYUI_WORKFLOW_NAME"]
missing_vars = [var for var in required_vars if not os.getenv(var)]
if missing_vars:
    raise ValueError(f"Missing required environment variables: {', '.join(missing_vars)}. Please set these in your .env file.")

# Regex for identifying special characters
special_char_pattern = r'[^a-zA-Z0-9_]'

# Mapping of aspect ratio friendly name to aspect ratio
aspect_ratio_aliases = {
    "1:1": "1:1",
    "square": "1:1",
    "16:9": "16:9",
    "widest": "16:9",
    "9:16": "9:16",
    "tallest": "9:16",
    "4:3": "4:3",
    "wide": "4:3",
    "3:4": "3:4",
    "tall": "3:4"
}

# Default image dimensions, if the config file for the workflow doesn't define them
default_aspect_ratios = {
  "16:9": [1280, 720],
  "4:3": [1152, 864],
  "1:1": [1024, 1024],
  "3:4": [864, 1152],
  "9:16": [720, 1280]
}

# Define JSON keys
config_key = 'config'
workflow_key = 'workflow'
aspect_ratios_key = 'aspect_ratios'
save_image_node_key = 'save_image_node'
image_size_nodes_key = 'image_size_nodes'
seed_nodes_key = 'seed_nodes'
prompt_nodes_key = 'prompt_nodes'
inputs_key = 'inputs'
seed_key = 'seed'
noise_seed_key = 'noise_seed'
width_key = 'width'
height_key = 'height'
text_key = 'text'

# Load the workflow and config files
workflow_json_path = os.path.join(working_dir, "workflows", f"{comfyui_workflow_name}.json")
config_yaml_path = os.path.join(working_dir, "workflows", f"{comfyui_workflow_name}.yaml")

# Parse the JSON workflow file
with open(workflow_json_path, 'r') as f:
    workflow_data = json.load(f)

# Parse the YAML config file
with open(config_yaml_path, 'r') as f:
    config_data = yaml.safe_load(f)

# If aspect ratios are not defined in the config, use the default ones
if aspect_ratios_key not in config_data or not config_data[aspect_ratios_key]:
    config_data[aspect_ratios_key] = default_aspect_ratios

# Create the comfyui_workflow dictionary with both workflow and config
comfyui_workflow = {
    workflow_key: workflow_data,
    config_key: config_data
}

def make_random_seed():
    return int(uuid.uuid4().int % 1e10)

def comfyui_generate_image(prompt: str, title: str, aspect_ratio: str) -> tuple:
    client_id = str(uuid.uuid4())

    # Get the image size
    if aspect_ratio not in aspect_ratio_aliases:
        # We were given an invalid aspect ratio. Silently set it to square.
        aspect_ratio = 'square'
    
    aspect_ratio = aspect_ratio_aliases[aspect_ratio]

    width, height = comfyui_workflow[config_key][aspect_ratios_key][aspect_ratio]

    # Build the ComfyUI workflow payload
    prompt_structure = comfyui_workflow[workflow_key]

    for image_size_node in comfyui_workflow[config_key][image_size_nodes_key]:
        if width_key in prompt_structure[image_size_node][inputs_key]:
            prompt_structure[image_size_node][inputs_key][width_key] = width
        if height_key in prompt_structure[image_size_node][inputs_key]:
            prompt_structure[image_size_node][inputs_key][height_key] = height

    for seed_node in comfyui_workflow[config_key][seed_nodes_key]:
        if seed_key in prompt_structure[seed_node][inputs_key]:
            prompt_structure[seed_node][inputs_key][seed_key] = make_random_seed()
        if noise_seed_key in prompt_structure[seed_node][inputs_key]:
            prompt_structure[seed_node][inputs_key][noise_seed_key] = make_random_seed()

    for prompt_node in comfyui_workflow[config_key][prompt_nodes_key]:
        prompt_structure[prompt_node][inputs_key][text_key] = prompt

    # Define functions to interact with ComfyUI API
    def queue_prompt(prompt):
        p = {"prompt": prompt, "client_id": client_id}
        data = json.dumps(p).encode('utf-8')
        req = urllib.request.Request(f"http://{comfyui_host}:{comfyui_port}/prompt", data=data)
        with urllib.request.urlopen(req) as response:
            return json.loads(response.read())

    def get_image(filename, subfolder, folder_type):
        data = {"filename": filename, "subfolder": subfolder, "type": folder_type}
        url_values = urllib.parse.urlencode(data)
        with urllib.request.urlopen(f"http://{comfyui_host}:{comfyui_port}/view?{url_values}") as response:
            return response.read()

    def get_history(prompt_id):
        with urllib.request.urlopen(f"http://{comfyui_host}:{comfyui_port}/history/{prompt_id}") as response:
            return json.loads(response.read())

    # Queue the prompt
    result = queue_prompt(prompt_structure)
    prompt_id = result['prompt_id']

    # Wait for the image generation to complete
    while True:
        history = get_history(prompt_id)
        if prompt_id in history:
            data = history[prompt_id]
            if data.get('is_processing', False):
                time.sleep(1)
            else:
                break
        else:
            time.sleep(1)

    # Retrieve the generated image
    output_images = {}
    history = get_history(prompt_id)[prompt_id]
    for node_id in history['outputs']:
        node_output = history['outputs'][node_id]
        images_output = []
        if 'images' in node_output:
            for image in node_output['images']:
                image_data = get_image(image['filename'], image['subfolder'], image['type'])
                images_output.append(image_data)
        output_images[node_id] = images_output

    # Assuming the image we want is in output_images[]
    images = output_images.get(f"{comfyui_workflow[config_key][save_image_node_key]}", [])
    if images:
        # Save the image to a temporary file
        image_data = images[0]
        image = Image.open(io.BytesIO(image_data))
        image_title = re.sub(special_char_pattern, '-', title)
        formatted_datetime = datetime.datetime.now().strftime("%Y-%m-%d_%H:%M:%S")
        image_filename = f"{formatted_datetime}_{image_title}_{comfyui_workflow_name}.png"
        image_path = os.path.join(output_dir, image_filename)
        os.makedirs(os.path.dirname(image_path), exist_ok=True)
        image.save(image_path)

        return image_filename, f"![{title}]({image_app_base_url}/{image_filename})"
    else:
        return None, "Unspecified error. No image generated."

# MCP Server
app = Server("comfyui-mcp-server")

@app.list_tools()
async def handle_list_tools() -> list[types.Tool]:
    """List available MCP tools"""
    return [
        types.Tool(
            name="image_generate",
            description="Generate an image from a text prompt",
            inputSchema={
                "type": "object",
                "properties": {
                    "prompt": {
                        "type": "string",
                        "description": "The text prompt for the image generation."
                    },
                    "title": {
                        "type": "string",
                        "description": "A short name (2 - 4 words) to title the image."
                    },
                    "aspect_ratio": {
                        "type": "string",
                        "description": "Supported values are 'widest' (16:9), 'wide' (4:3), 'square' (1:1), 'tall' (3:4), and 'tallest' (9:16)."
                    }
                },
                "required": ["prompt", "title", "aspect_ratio"]
            },
        ),
    ]

@app.call_tool()
async def handle_call_tool(name: str, arguments: dict) -> list[types.TextContent]:
    """Handle MCP tool calls"""
    
    if name == "image_generate":
        prompt = arguments.get('prompt')
        title = arguments.get('title')
        aspect_ratio = arguments.get('aspect_ratio')
        
        try:
            image_filename, markdown = await anyio.to_thread.run_sync(
                comfyui_generate_image, prompt, title, aspect_ratio
            )

            # Write prompt to a file named similarly to image_filename, but with .txt extension
            if image_filename:
                prompt_filename = image_filename.replace('.png', '.txt')
                prompt_path = os.path.join(output_dir, prompt_filename)
                with open(prompt_path, 'w') as f:
                    f.write(prompt)

            return [types.TextContent(type="text", text=markdown)]
        except Exception as e:
            return [types.TextContent(
                type="text",
                text=f"Error generating image: {str(e)}"
            )]
    else:
        return [types.TextContent(
            type="text",
            text=f"Unknown tool: {name}"
        )]

async def main():
    """Main server entry point"""
    # Ensure output directory exists
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    
    try:
        async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
            await app.run(
                read_stream,
                write_stream,
                InitializationOptions(
                    server_name="comfyui-mcp-server",
                    server_version="1.0.0",
                    capabilities=types.ServerCapabilities(
                        tools=types.ToolsCapability(listChanged=True)
                    ),
                ),
            )
    except Exception as e:
        print(f"Server error: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())

