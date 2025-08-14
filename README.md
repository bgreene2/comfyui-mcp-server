# ComfyUI MCP Server

This repository contains an MCP (Model Context Protocol) server for generating images using the ComfyUI API. It allows you to generate images from text prompts through an LLM interface.

## Features

- Generate images from text prompts using various ComfyUI workflows
- Supports multiple aspect ratios (square, landscape, portrait)
- Automatic image saving with timestamped filenames
- Web-based image gallery for viewing generated images
- Cross-platform compatibility (Windows, macOS, Linux)

## Prerequisites

- Python 3.8 or higher
- ComfyUI with API enabled
- Pre-configured ComfyUI workflows

## Installation

1. Clone this repository:
   ```bash
   git clone https://github.com/bgreene2/comfyui-mcp-server.git
   cd comfyui-mcp-server
   ```

2. Install the required dependencies for the server:
   ```bash
   pip install -r server_requirements.txt
   ```

3. If you plan to use the image hosting app, install its dependencies:
   ```bash
   pip install -r image_host_requirements.txt
   ```

## Setup

### 1. Configure ComfyUI

1. In ComfyUI, create and configure your desired image generation workflow
2. Export your workflow for API usage (Save as "Workflow API format")
3. Copy the exported JSON file to the `workflows/` directory
4. Create a corresponding YAML configuration file with the same name (but with `.yaml` extension)

### 2. Create Workflow Configuration

Create a YAML file in the `workflows/` directory with the same name as your workflow JSON file. This file should contain:

```yaml
aspect_ratios:
  "16:9": [1280, 720]   # widest
  "4:3": [1152, 864]    # wide
  "1:1": [1024, 1024]   # square
  "3:4": [864, 1152]    # tall
  "9:16": [720, 1280]   # tallest
save_image_node: '9'          # ID of the Save Image node
image_size_nodes: ['27']      # List of node IDs for width/height settings
seed_nodes: ['31']            # List of node IDs for seed settings
prompt_nodes: ['45']          # List of node IDs for prompt settings
```

Update the node IDs to match those in your ComfyUI workflow.

### 3. Configure Aspect Ratios (Optional)

You can customize the image dimensions for each aspect ratio in the YAML configuration file. If not specified, the following defaults will be used:
- **16:9 (widest)**: 1280×720
- **4:3 (wide)**: 1152×864
- **1:1 (square)**: 1024×1024
- **3:4 (tall)**: 864×1152
- **9:16 (tallest)**: 720×1280

## Usage

### Starting the MCP Server

Create a `.env` file based on `env.example` and set the required environment variables:

```bash
cp env.example .env
# Edit .env to match your setup
```

If you need to specify a custom working directory (where workflow files are located), uncomment and modify the `WORKING_DIR` line in your `.env` file.

Then run the server:

```bash
fastmcp run /path/to/server.py
```

#### Environment Variables:

- `COMFYUI_HOST`: Hostname or IP address of ComfyUI API (e.g., `127.0.0.1`)
- `COMFYUI_PORT`: Port number of ComfyUI API (e.g., `8188`)
- `OUTPUT_DIR`: Directory where generated images will be saved
- `IMAGE_APP_BASE_URL`: URL where generated images will be served from
- `COMFYUI_WORKFLOW_NAME`: Name of the ComfyUI workflow (without extension)
- `WORKING_DIR`: (Optional) Directory where the server resides (parent directory of 'server.py' and 'workflows/'). Defaults to the current working directory.

All environment variables except `WORKING_DIR` are required and must be set.

### Starting the Image Hosting App (Optional)

The image hosting app provides a web-based gallery for viewing generated images:

```bash
python image_host.py --output-dir /path/to/output
```

The gallery will be available at `http://0.0.0.0:8081`.

### Example MCP Configuration

Create a `.env` file and set the required environment variables, then use this configuration:

```json
{
  "mcpServers": {
    "image-generation": {
      "command": "python",
      "args": [
        "/path/to/server.py"
      ]
    }
  }
}
```

## Using the Image Generation Tool

Once the server is running, you can use the `image_generate` tool with the following parameters:

- `prompt`: The text prompt for the image generation
- `title`: A short name (2-4 words) to title the image
- `aspect_ratio`: Supported values:
  - `"widest"` (16:9)
  - `"wide"` (4:3)
  - `"square"` (1:1)
  - `"tall"` (3:4)
  - `"tallest"` (9:16)

Example tool call:
```json
{
  "tool": "image_generate",
  "params": {
    "prompt": "A beautiful sunset over the mountains",
    "title": "Mountain Sunset",
    "aspect_ratio": "wide"
  }
}
```

## File Structure

```
comfyui-mcp-server/
├── server.py                 # Main MCP server implementation
├── image_host.py             # Image gallery web app
├── server_requirements.txt   # Dependencies for server.py
├── image_host_requirements.txt # Dependencies for image_host.py
├── workflows/                # Workflow configurations
│   ├── *.json               # ComfyUI workflow files
│   └── *.yaml               # Workflow configuration files
└── README.md
```

## Troubleshooting

1. **Connection Issues**: Ensure ComfyUI is running and the API is enabled
2. **Workflow Errors**: Verify that node IDs in the YAML configuration match those in your ComfyUI workflow
3. **Permission Errors**: Ensure the output directory is writable
4. **Missing Dependencies**: Run `pip install -r server_requirements.txt` to install all required packages

