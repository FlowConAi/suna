"""MCP client implementation for connecting to MCP servers."""

import asyncio
import json
import logging
import os
from typing import Dict, Any, List, Optional, Union
from dataclasses import dataclass
import uuid


logger = logging.getLogger(__name__)


class MCPClientError(Exception):
    """Base exception for MCP client errors."""
    pass


class MCPConnectionError(MCPClientError):
    """Exception for MCP connection errors."""
    pass


@dataclass
class MCPMessage:
    """Represents an MCP JSON-RPC message."""
    jsonrpc: str = "2.0"
    id: Optional[Union[str, int]] = None
    method: Optional[str] = None
    params: Optional[Dict[str, Any]] = None
    result: Optional[Any] = None
    error: Optional[Dict[str, Any]] = None


class MCPClient:
    """Client for connecting to MCP servers via STDIO or HTTP."""
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize MCP client with configuration.
        
        Args:
            config: Server configuration with transport, command, etc.
        """
        self.name = config["name"]
        self.transport_type = config["transport"]
        self.config = config
        
        if self.transport_type == "stdio":
            self.command = config["command"]
            self.args = config.get("args", [])
            self.process = None
        elif self.transport_type == "http":
            self.url = config["url"]
            self.session = None
        else:
            raise MCPClientError(f"Unsupported transport: {self.transport_type}")
            
        self.connected = False
        self.server_capabilities = {}
        self._request_id = 0
        self._pending_requests: Dict[int, asyncio.Future] = {}
        
    async def connect(self) -> None:
        """Connect to the MCP server."""
        try:
            if self.transport_type == "stdio":
                await self._connect_stdio()
            elif self.transport_type == "http":
                await self._connect_http()
                
            # Mark as connected before initialization so we can send requests
            self.connected = True
            
            try:
                await self._initialize_connection()
                logger.info(f"Connected to MCP server: {self.name}")
            except Exception as e:
                # If initialization fails, mark as disconnected
                self.connected = False
                raise
                
        except Exception as e:
            logger.error(f"Failed to connect to MCP server {self.name}: {e}")
            raise MCPConnectionError(f"Failed to connect to MCP server {self.name}: {e}")
    
    async def _connect_stdio(self) -> None:
        """Connect using STDIO transport."""
        try:
            # Get environment variables from config if provided
            env = None
            if "env" in self.config and self.config["env"]:
                # Start with current environment and update with provided vars
                env = os.environ.copy()
                env.update(self.config["env"])
            
            self.process = await asyncio.create_subprocess_exec(
                self.command,
                *self.args,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=env
            )
        except Exception as e:
            raise MCPConnectionError(f"Failed to start MCP server process: {e}")
    
    async def _connect_http(self) -> None:
        """Connect using HTTP transport."""
        # TODO: Implement HTTP transport
        raise MCPClientError("HTTP transport not yet implemented")
    
    async def _initialize_connection(self) -> None:
        """Perform MCP initialization handshake."""
        # Send initialize request
        client_capabilities = {
            "tools": {},
            "resources": {},
            "prompts": {}
        }
        
        init_request = {
            "protocolVersion": "2024-11-05",
            "capabilities": client_capabilities,
            "clientInfo": {
                "name": "suna-agent",
                "version": "1.0.0"
            }
        }
        
        try:
            init_response = await self.send_request("initialize", init_request)
            self.server_capabilities = init_response.get("capabilities", {})
            
            # Send initialized notification
            await self._send_notification("notifications/initialized")
            
        except Exception as e:
            raise MCPConnectionError(f"Initialization failed: {e}")
    
    async def disconnect(self) -> None:
        """Disconnect from the MCP server."""
        self.connected = False
        
        # Cancel all pending requests
        for request_id, future in self._pending_requests.items():
            if not future.done():
                future.cancel()
        
        # Cancel response handler task if running
        if hasattr(self, '_response_task') and not self._response_task.done():
            self._response_task.cancel()
            try:
                await self._response_task
            except asyncio.CancelledError:
                pass
        
        if self.transport_type == "stdio" and self.process:
            self.process.terminate()
            try:
                await asyncio.wait_for(self.process.wait(), timeout=5.0)
            except asyncio.TimeoutError:
                self.process.kill()
                await self.process.wait()
            self.process = None
            
        self._pending_requests.clear()
        logger.info(f"Disconnected from MCP server: {self.name}")
    
    async def list_tools(self) -> List[Dict[str, Any]]:
        """List available tools from the server."""
        if not self.connected:
            raise MCPClientError("Client not connected")
            
        response = await self.send_request("tools/list", {})
        return response.get("tools", [])
    
    async def call_tool(self, name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Call a tool on the server.
        
        Args:
            name: Tool name to call
            arguments: Arguments to pass to the tool
            
        Returns:
            Tool execution result
        """
        if not self.connected:
            raise MCPClientError("Client not connected")
            
        params = {
            "name": name,
            "arguments": arguments
        }
        
        return await self.send_request("tools/call", params)
    
    async def send_request(self, method: str, params: Dict[str, Any], 
                          timeout: float = 30.0) -> Any:
        """Send a JSON-RPC request and wait for response.
        
        Args:
            method: RPC method name
            params: Method parameters
            timeout: Request timeout in seconds
            
        Returns:
            Response result
        """
        if not self.connected:
            raise MCPClientError("Client not connected")
            
        self._request_id += 1
        request_id = self._request_id
        
        request = {
            "jsonrpc": "2.0",
            "id": request_id,
            "method": method,
            "params": params
        }
        
        # Create future for response
        future = asyncio.Future()
        self._pending_requests[request_id] = future
        
        try:
            # Send request
            await self._send_message(request)
            
            # Wait for response
            response = await asyncio.wait_for(future, timeout=timeout)
            
            if "error" in response:
                error = response["error"]
                raise MCPClientError(f"RPC error: {error.get('message', 'Unknown error')}")
                
            return response.get("result")
            
        except asyncio.TimeoutError:
            raise MCPClientError(f"Request timeout after {timeout} seconds")
        except asyncio.CancelledError:
            # Request was cancelled (e.g., during disconnect)
            raise
        finally:
            self._pending_requests.pop(request_id, None)
    
    async def _send_notification(self, method: str, params: Optional[Dict[str, Any]] = None) -> None:
        """Send a notification (no response expected)."""
        notification = {
            "jsonrpc": "2.0",
            "method": method
        }
        if params:
            notification["params"] = params
            
        await self._send_message(notification)
    
    async def _send_message(self, message: Dict[str, Any]) -> None:
        """Send a message to the server."""
        if self.transport_type == "stdio":
            await self._send_stdio_message(message)
        elif self.transport_type == "http":
            await self._send_http_message(message)
    
    async def _send_stdio_message(self, message: Dict[str, Any]) -> None:
        """Send message via STDIO transport."""
        if not self.process or not self.process.stdin:
            raise MCPClientError("STDIO transport not available")
            
        # Start response handling if not already running
        if not hasattr(self, '_response_task') or self._response_task.done():
            self._response_task = asyncio.create_task(self._handle_stdio_responses())
            
        message_json = json.dumps(message) + "\n"
        self.process.stdin.write(message_json.encode())
        await self.process.stdin.drain()
    
    async def _send_http_message(self, message: Dict[str, Any]) -> None:
        """Send message via HTTP transport."""
        # TODO: Implement HTTP transport
        raise MCPClientError("HTTP transport not yet implemented")
    
    async def _handle_stdio_responses(self) -> None:
        """Handle incoming responses from STDIO."""
        try:
            while self.connected and self.process and self.process.stdout:
                try:
                    line = await self.process.stdout.readline()
                    if not line:
                        break
                        
                    try:
                        response = json.loads(line.decode().strip())
                        await self._handle_response(response)
                    except json.JSONDecodeError as e:
                        logger.warning(f"Invalid JSON from MCP server {self.name}: {e}")
                    except Exception as e:
                        logger.error(f"Error handling response from {self.name}: {e}")
                except asyncio.CancelledError:
                    # Task was cancelled, exit cleanly
                    break
                except Exception as e:
                    logger.error(f"Error reading from {self.name}: {e}")
                    break
                    
        except Exception as e:
            logger.error(f"Response handler error for {self.name}: {e}")
    
    async def _handle_response(self, response: Dict[str, Any]) -> None:
        """Handle a received response or notification."""
        if "id" in response:
            # This is a response to a request
            request_id = response["id"]
            if request_id in self._pending_requests:
                future = self._pending_requests[request_id]
                if not future.done():
                    future.set_result(response)
        else:
            # This is a notification
            method = response.get("method")
            if method:
                await self._handle_notification(method, response.get("params", {}))
    
    async def _handle_notification(self, method: str, params: Dict[str, Any]) -> None:
        """Handle incoming notification from server."""
        logger.debug(f"Received notification from {self.name}: {method}")
        
        # Handle specific notifications
        if method == "notifications/tools/list_changed":
            # Tools list has changed
            logger.info(f"Tools list changed on server {self.name}")
    
    async def __aenter__(self):
        """Context manager entry."""
        await self.connect()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        await self.disconnect()