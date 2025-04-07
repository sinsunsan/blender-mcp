# BlenderMCP - Blender BIM Model Context Protocol Integration

BlenderMCP connects Blender to Claude AI through the Model Context Protocol (MCP), allowing Claude to directly interact with and control Blender for creating and manipulating BIM (Building Information Modeling) elements and floor plans.

### Join the Community

Give feedback, get inspired, and build on top of the MCP: [Discord](https://discord.gg/z5apgR8TFU)

### Supporters

**Top supporters:**

[CodeRabbit](https://www.coderabbit.ai/)

**All supporters:**

[Support this project](https://github.com/sponsors/ahujasid)

## Release notes (1.1.0)

- Added support for BIM element creation and manipulation
- Added support for floor plan generation from natural language prompts
- For newcomers, you can go straight to Installation. For existing users, see the points below
- Download the latest addon.py file and replace the older one, then add it to Blender
- Delete the MCP server from Claude and add it back again, and you should be good to go!

## Features

- **Two-way communication**: Connect Claude AI to Blender through a socket-based server
- **BIM element creation**: Create walls, doors, windows, and other BIM elements
- **Floor plan generation**: Generate complete floor plans from natural language descriptions
- **BIM properties**: Set and modify properties for BIM elements
- **Code execution**: Run arbitrary Python code in Blender from Claude

## Components

The system consists of two main components:

1. **Blender Addon (`addon.py`)**: A Blender addon that creates a socket server within Blender to receive and execute commands
2. **MCP Server (`src/blender_mcp/server.py`)**: A Python server that implements the Model Context Protocol and connects to the Blender addon

## Installation

### Prerequisites

- Blender 3.0 or newer
- Python 3.10 or newer
- BlenderBIM Addon installed and enabled
- uv package manager:

**If you're on Mac, please install uv as**

```bash
brew install uv
```

**On Windows**

```bash
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
```

and then

```bash
set Path=C:\Users\nntra\.local\bin;%Path%
```

Otherwise installation instructions are on their website: [Install uv](https://docs.astral.sh/uv/getting-started/installation/)

**⚠️ Do not proceed before installing UV**

### Claude for Desktop Integration

[Watch the setup instruction video](https://www.youtube.com/watch?v=neoK_WMq92g) (Assuming you have already installed uv)

Go to Claude > Settings > Developer > Edit Config > claude_desktop_config.json to include the following:

```json
{
  "mcpServers": {
    "blender": {
      "command": "uvx",
      "args": ["blender-mcp"]
    }
  }
}
```

### Cursor integration

Run blender-mcp without installing it permanently through uvx. Go to Cursor Settings > MCP and paste this as a command.

```bash
uvx blender-mcp
```

For Windows users, go to Settings > MCP > Add Server, add a new server with the following settings:

```json
{
  "mcpServers": {
    "blender": {
      "command": "cmd",
      "args": ["/c", "uvx", "blender-mcp"]
    }
  }
}
```

[Cursor setup video](https://www.youtube.com/watch?v=wgWsJshecac)

**⚠️ Only run one instance of the MCP server (either on Cursor or Claude Desktop), not both**

### Installing the Blender Addon

1. Download the `addon.py` file from this repo
1. Open Blender
1. Go to Edit > Preferences > Add-ons
1. Click "Install..." and select the `addon.py` file
1. Enable the addon by checking the box next to "Interface: Blender MCP"

## Usage

### Starting the Connection

![BlenderMCP in the sidebar](assets/addon-instructions.png)

1. In Blender, go to the 3D View sidebar (press N if not visible)
2. Find the "BlenderMCP" tab
3. Click "Connect to Claude"
4. Make sure the MCP server is running in your terminal

### Using with Claude

Once the config file has been set on Claude, and the addon is running on Blender, you will see a hammer icon with tools for the Blender MCP.

![BlenderMCP in the sidebar](assets/hammer-icon.png)

#### Capabilities

- Create BIM elements (walls, doors, windows, etc.)
- Generate floor plans from natural language descriptions
- Set and modify BIM properties
- Execute any Python code in Blender

### Example Commands

Here are some examples of what you can ask Claude to do:

- "Create a floor plan with a living room, kitchen, and two bedrooms"
- "Add a door between the living room and kitchen"
- "Create a window in the north wall of the living room"
- "Set the wall thickness to 0.2 meters"
- "Create a second storey with the same floor plan"
- "Add a staircase connecting the two storeys"

## Troubleshooting

- **Connection issues**: Make sure the Blender addon server is running, and the MCP server is configured on Claude, DO NOT run the uvx command in the terminal. Sometimes, the first command won't go through but after that it starts working.
- **Timeout errors**: Try simplifying your requests or breaking them into smaller steps
- **Have you tried turning it off and on again?**: If you're still having connection errors, try restarting both Claude and the Blender server

## Technical Details

### Communication Protocol

The system uses a simple JSON-based protocol over TCP sockets:

- **Commands** are sent as JSON objects with a `type` and optional `params`
- **Responses** are JSON objects with a `status` and `result` or `message`

## Limitations & Security Considerations

- The `execute_blender_code` tool allows running arbitrary Python code in Blender, which can be powerful but potentially dangerous. Use with caution in production environments. ALWAYS save your work before using it.
- Complex operations might need to be broken down into smaller steps

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## Disclaimer

This is a third-party integration and not made by Blender. Made by [Siddharth](https://x.com/sidahuj)

### Update the plugin - How to test

When you make changes to the MCP plugin, follow these steps to test the updates:

1. **Code Changes**:

   - Save your changes to the relevant files (e.g., `bim_tools.py`, `server.py`)
   - If you modified `addon.py`, you'll need to reinstall it in Blender

2. **Restart the MCP Server**:

   - Stop the current MCP server (if running)
   - Start it again with your updated code
   - The changes will be immediately available for testing

3. **In Blender**:

   - Make sure the BlenderMCP addon is enabled
   - Click "Connect to Claude" in the sidebar
   - Test your new functionality through Claude

4. **Testing Tips**:
   - Start with simple commands to verify the connection
   - Use the logging output to debug any issues
   - If changes don't appear, try restarting both the MCP server and Blender

Remember: Changes to the server code take effect immediately after restarting the MCP server, while changes to `addon.py` require a Blender restart.
