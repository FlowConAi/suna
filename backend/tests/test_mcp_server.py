#!/usr/bin/env python3
"""Test MCP server for integration testing."""

import sys
import json
import asyncio
import logging

# Configure logging to stderr only
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stderr
)
logger = logging.getLogger(__name__)


class TestMCPServer:
    """Simple MCP server for testing."""
    
    def __init__(self):
        self.running = True
        self.request_id_counter = 0
        
    async def handle_request(self, request: dict) -> dict:
        """Handle incoming JSON-RPC request."""
        method = request.get("method")
        params = request.get("params", {})
        request_id = request.get("id")
        
        logger.debug(f"Handling request: {method}")
        
        if method == "initialize":
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {
                    "protocolVersion": "2024-11-05",
                    "serverInfo": {
                        "name": "test-mcp-server",
                        "version": "1.0.0"
                    },
                    "capabilities": {
                        "tools": {}
                    }
                }
            }
            
        elif method == "notifications/initialized":
            # This is a notification, no response needed
            logger.info("Server initialized successfully")
            return None
            
        elif method == "tools/list":
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {
                    "tools": [
                        {
                            "name": "add",
                            "description": "Add two numbers",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "a": {"type": "number", "description": "First number"},
                                    "b": {"type": "number", "description": "Second number"}
                                },
                                "required": ["a", "b"]
                            }
                        },
                        {
                            "name": "echo",
                            "description": "Echo back the input",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "message": {"type": "string", "description": "Message to echo"}
                                },
                                "required": ["message"]
                            }
                        }
                    ]
                }
            }
            
        elif method == "tools/call":
            tool_name = params.get("name")
            tool_args = params.get("arguments", {})
            
            if tool_name == "add":
                result = tool_args.get("a", 0) + tool_args.get("b", 0)
                return {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "result": {
                        "content": [{"type": "text", "text": f"Result: {result}"}],
                        "isError": False
                    }
                }
                
            elif tool_name == "echo":
                message = tool_args.get("message", "")
                return {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "result": {
                        "content": [{"type": "text", "text": f"Echo: {message}"}],
                        "isError": False
                    }
                }
                
            else:
                return {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "error": {
                        "code": -32601,
                        "message": f"Unknown tool: {tool_name}"
                    }
                }
                
        elif method == "shutdown":
            self.running = False
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {"status": "shutting down"}
            }
            
        else:
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "error": {
                    "code": -32601,
                    "message": f"Method not found: {method}"
                }
            }
    
    async def run(self):
        """Run the server, reading from stdin and writing to stdout."""
        logger.info("Test MCP server starting...")
        
        reader = asyncio.StreamReader()
        protocol = asyncio.StreamReaderProtocol(reader)
        
        try:
            await asyncio.get_event_loop().connect_read_pipe(
                lambda: protocol, sys.stdin
            )
            
            while self.running:
                try:
                    # Read line from stdin
                    line = await reader.readline()
                    if not line:
                        logger.info("EOF received, shutting down")
                        break
                    
                    # Parse JSON-RPC request
                    try:
                        request = json.loads(line.decode().strip())
                        logger.debug(f"Received request: {json.dumps(request, indent=2)}")
                    except json.JSONDecodeError as e:
                        logger.error(f"Invalid JSON: {e}")
                        continue
                    
                    # Handle request
                    response = await self.handle_request(request)
                    
                    # Send response if not a notification
                    if response is not None:
                        response_json = json.dumps(response) + "\n"
                        sys.stdout.write(response_json)
                        sys.stdout.flush()
                        logger.debug(f"Sent response: {json.dumps(response, indent=2)}")
                        
                except Exception as e:
                    logger.error(f"Error processing request: {e}", exc_info=True)
                    
        except Exception as e:
            logger.error(f"Server error: {e}", exc_info=True)
        finally:
            logger.info("Test MCP server shutting down")


async def main():
    """Main entry point."""
    server = TestMCPServer()
    await server.run()


if __name__ == "__main__":
    asyncio.run(main())