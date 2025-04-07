# blender_mcp_server.py
from mcp.server.fastmcp import FastMCP, Context, Image
import socket
import json
import asyncio
import logging
from dataclasses import dataclass
from contextlib import asynccontextmanager
from typing import AsyncIterator, Dict, Any, List
import os
from pathlib import Path
import base64
from urllib.parse import urlparse

# Import BIM tools
from .bim_tools import (
    create_bim_element,
    create_floor_plan,
    set_bim_properties,
    process_bim_prompt
)

# Configure logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("BlenderMCPServer")

@dataclass
class BlenderConnection:
    host: str
    port: int
    sock: socket.socket = None
    
    def connect(self) -> bool:
        """Connect to the Blender addon socket server"""
        if self.sock:
            return True
            
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.connect((self.host, self.port))
            logger.info(f"Connected to Blender at {self.host}:{self.port}")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to Blender: {str(e)}")
            self.sock = None
            return False
    
    def disconnect(self):
        """Disconnect from the Blender addon"""
        if self.sock:
            try:
                self.sock.close()
            except Exception as e:
                logger.error(f"Error disconnecting from Blender: {str(e)}")
            finally:
                self.sock = None

    def receive_full_response(self, sock, buffer_size=8192):
        """Receive the complete response, potentially in multiple chunks"""
        chunks = []
        sock.settimeout(15.0)
        
        try:
            while True:
                try:
                    chunk = sock.recv(buffer_size)
                    if not chunk:
                        if not chunks:
                            raise Exception("Connection closed before receiving any data")
                        break
                    
                    chunks.append(chunk)
                    
                    try:
                        data = b''.join(chunks)
                        json.loads(data.decode('utf-8'))
                        logger.info(f"Received complete response ({len(data)} bytes)")
                        return data
                    except json.JSONDecodeError:
                        continue
                except socket.timeout:
                    logger.warning("Socket timeout during chunked receive")
                    break
                except (ConnectionError, BrokenPipeError, ConnectionResetError) as e:
                    logger.error(f"Socket connection error during receive: {str(e)}")
                    raise
        except socket.timeout:
            logger.warning("Socket timeout during chunked receive")
        except Exception as e:
            logger.error(f"Error during receive: {str(e)}")
            raise
            
        if chunks:
            data = b''.join(chunks)
            logger.info(f"Returning data after receive completion ({len(data)} bytes)")
            try:
                json.loads(data.decode('utf-8'))
                return data
            except json.JSONDecodeError:
                raise Exception("Incomplete JSON response received")
        else:
            raise Exception("No data received")

    def send_command(self, command_type: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
        """Send a command to Blender and return the response"""
        if not self.sock and not self.connect():
            raise ConnectionError("Not connected to Blender")
        
        command = {
            "type": command_type,
            "params": params or {}
        }
        
        try:
            logger.info(f"Sending command: {command_type} with params: {params}")
            self.sock.sendall(json.dumps(command).encode('utf-8'))
            logger.info(f"Command sent, waiting for response...")
            
            self.sock.settimeout(15.0)
            response_data = self.receive_full_response(self.sock)
            logger.info(f"Received {len(response_data)} bytes of data")
            
            response = json.loads(response_data.decode('utf-8'))
            logger.info(f"Response parsed, status: {response.get('status', 'unknown')}")
            
            if response.get("status") == "error":
                logger.error(f"Blender error: {response.get('message')}")
                raise Exception(response.get("message", "Unknown error from Blender"))
            
            return response.get("result", {})
        except socket.timeout:
            logger.error("Socket timeout while waiting for response from Blender")
            self.sock = None
            raise Exception("Timeout waiting for Blender response - try simplifying your request")
        except (ConnectionError, BrokenPipeError, ConnectionResetError) as e:
            logger.error(f"Socket connection error: {str(e)}")
            self.sock = None
            raise Exception(f"Connection to Blender lost: {str(e)}")
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON response from Blender: {str(e)}")
            if 'response_data' in locals() and response_data:
                logger.error(f"Raw response (first 200 bytes): {response_data[:200]}")
            raise Exception(f"Invalid response from Blender: {str(e)}")
        except Exception as e:
            logger.error(f"Error communicating with Blender: {str(e)}")
            self.sock = None
            raise Exception(f"Communication error with Blender: {str(e)}")

@asynccontextmanager
async def server_lifespan(server: FastMCP) -> AsyncIterator[Dict[str, Any]]:
    """Manage server startup and shutdown lifecycle"""
    try:
        logger.info("BlenderMCP server starting up")
        try:
            blender = get_blender_connection()
            logger.info("Successfully connected to Blender on startup")
        except Exception as e:
            logger.warning(f"Could not connect to Blender on startup: {str(e)}")
            logger.warning("Make sure the Blender addon is running before using Blender resources or tools")
        
        yield {}
    finally:
        global _blender_connection
        if _blender_connection:
            logger.info("Disconnecting from Blender on shutdown")
            _blender_connection.disconnect()
            _blender_connection = None
        logger.info("BlenderMCP server shut down")

# Create the MCP server with lifespan support
mcp = FastMCP(
    "BlenderMCP",
    description="Blender BIM integration through the Model Context Protocol",
    lifespan=server_lifespan
)

# Global connection for resources
_blender_connection = None

def get_blender_connection():
    """Get or create a persistent Blender connection"""
    global _blender_connection
    
    if _blender_connection is not None:
        try:
            result = _blender_connection.send_command("ping")
            return _blender_connection
        except Exception as e:
            logger.warning(f"Existing connection is no longer valid: {str(e)}")
            try:
                _blender_connection.disconnect()
            except:
                pass
            _blender_connection = None
    
    if _blender_connection is None:
        _blender_connection = BlenderConnection(host="localhost", port=9876)
        if not _blender_connection.connect():
            logger.error("Failed to connect to Blender")
            _blender_connection = None
            raise Exception("Could not connect to Blender. Make sure the Blender addon is running.")
        logger.info("Created new persistent connection to Blender")
    
    return _blender_connection

@mcp.tool()
def create_bim_element_from_prompt(ctx: Context, prompt: str) -> str:
    """
    Create a BIM element from a natural language prompt.
    
    Parameters:
    - prompt: Natural language description of the desired BIM element
    """
    try:
        # Process the prompt to extract parameters
        params = process_bim_prompt(prompt)
        
        # Generate the Blender code
        code = create_bim_element(
            element_type=params["element_type"],
            parameters=params["parameters"],
            location=params["location"],
            rotation=params["rotation"],
            scale=params["scale"]
        )
        
        # Execute the code in Blender
        blender = get_blender_connection()
        result = blender.send_command("execute_code", {"code": code})
        return f"Created BIM element: {result.get('result', '')}"
    except Exception as e:
        logger.error(f"Error creating BIM element: {str(e)}")
        return f"Error creating BIM element: {str(e)}"

@mcp.tool()
def create_floor_plan_from_prompt(ctx: Context, prompt: str) -> str:
    """
    Create a floor plan from a natural language prompt.
    
    Parameters:
    - prompt: Natural language description of the desired floor plan
    """
    try:
        # Process the prompt to extract parameters
        # This is a placeholder - in a real implementation, you would use NLP
        # to extract room sizes, storey height, etc.
        storey_height = 3.0
        room_sizes = [
            {
                "name": "Living Room",
                "walls": [
                    {"id": 1, "location": [0, 0, 0], "rotation": [0, 0, 0]},
                    {"id": 2, "location": [5, 0, 0], "rotation": [0, 0, 1.57]}
                ],
                "openings": [
                    {"type": "DOOR", "id": 1, "location": [2, 0, 0], "rotation": [0, 0, 0]}
                ]
            }
        ]
        
        # Generate the Blender code
        code = create_floor_plan(
            storey_height=storey_height,
            room_sizes=room_sizes
        )
        
        # Execute the code in Blender
        blender = get_blender_connection()
        result = blender.send_command("execute_code", {"code": code})
        return f"Created floor plan: {result.get('result', '')}"
    except Exception as e:
        logger.error(f"Error creating floor plan: {str(e)}")
        return f"Error creating floor plan: {str(e)}"

@mcp.tool()
def set_bim_element_properties(ctx: Context, element_name: str, properties: Dict[str, Any]) -> str:
    """
    Set properties for a BIM element.
    
    Parameters:
    - element_name: Name of the element to modify
    - properties: Dictionary of properties to set
    """
    try:
        # Generate the Blender code
        code = set_bim_properties(element_name, properties)
        
        # Execute the code in Blender
        blender = get_blender_connection()
        result = blender.send_command("execute_code", {"code": code})
        return f"Set properties for {element_name}: {result.get('result', '')}"
    except Exception as e:
        logger.error(f"Error setting BIM properties: {str(e)}")
        return f"Error setting BIM properties: {str(e)}"

@mcp.prompt()
def bim_creation_strategy() -> str:
    """Defines the preferred strategy for creating BIM elements in Blender"""
    return """When creating BIM content in Blender, follow these steps:

    1. First check if the BlenderBIM addon is properly installed and enabled
    2. Use create_bim_element_from_prompt() for creating individual BIM elements
    3. Use create_floor_plan_from_prompt() for creating complete floor plans
    4. Use set_bim_element_properties() to modify properties of existing elements
    
    When creating floor plans:
    - Specify room sizes and layouts clearly
    - Include wall thicknesses and heights
    - Specify door and window locations
    - Consider storey heights and relationships
    
    When creating individual elements:
    - Specify the element type (WALL, DOOR, WINDOW, etc.)
    - Provide location, rotation, and scale if needed
    - Include any specific properties required for the element type
    """

def main():
    """Run the MCP server"""
    mcp.run()

if __name__ == "__main__":
    main()