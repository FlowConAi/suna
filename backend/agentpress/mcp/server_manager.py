"""MCP server manager for handling multiple MCP server connections."""

import asyncio
import logging
from typing import Dict, List, Any, Optional
from .client import MCPClient, MCPClientError


logger = logging.getLogger(__name__)


class MCPServerManagerError(Exception):
    """Exception for MCP server manager errors."""
    pass


class MCPServerManager:
    """Manages connections to multiple MCP servers."""
    
    def __init__(self, server_configs: List[Dict[str, Any]]):
        """Initialize server manager with configurations.
        
        Args:
            server_configs: List of MCP server configurations
        """
        self.server_configs = server_configs
        self.clients: List[MCPClient] = []
        self.connected_clients: List[MCPClient] = []
        self._tool_to_client_map: Dict[str, MCPClient] = {}
        self._current_project_id: Optional[str] = None
    
    def get_enabled_servers(self) -> List[Dict[str, Any]]:
        """Get list of enabled server configurations."""
        return [config for config in self.server_configs if config.get("enabled", True)]
    
    def get_servers_for_project(self, project_id: str) -> List[Dict[str, Any]]:
        """Get server configurations applicable to a project.
        
        Args:
            project_id: Project identifier
            
        Returns:
            List of applicable server configurations
        """
        applicable_servers = []
        
        for config in self.get_enabled_servers():
            scope = config.get("project_scope", "global")
            
            if scope == "global":
                applicable_servers.append(config)
            elif scope == "project":
                applicable_servers.append(config)
            elif scope == project_id:
                applicable_servers.append(config)
        
        return applicable_servers
    
    async def connect_to_servers(self, project_id: str) -> None:
        """Connect to MCP servers for a specific project.
        
        Args:
            project_id: Project identifier
        """
        self._current_project_id = project_id
        applicable_configs = self.get_servers_for_project(project_id)
        
        logger.info(f"Connecting to {len(applicable_configs)} MCP servers for project {project_id}")
        
        # Create and connect clients
        connection_tasks = []
        for config in applicable_configs:
            client = MCPClient(config)
            self.clients.append(client)
            connection_tasks.append(self._connect_client_safely(client))
        
        # Wait for all connections (don't fail if some servers are unavailable)
        if connection_tasks:
            await asyncio.gather(*connection_tasks, return_exceptions=True)
        
        # Update connected clients list
        self.connected_clients = [client for client in self.clients if client.connected]
        
        logger.info(f"Successfully connected to {len(self.connected_clients)}/{len(self.clients)} MCP servers")
        
        # Build tool mapping
        if self.connected_clients:
            await self._refresh_tool_mappings(project_id)
    
    async def _connect_client_safely(self, client: MCPClient) -> None:
        """Connect to a client with error handling."""
        try:
            await client.connect()
            logger.info(f"Connected to MCP server: {client.name}")
        except Exception as e:
            logger.warning(f"Failed to connect to MCP server {client.name}: {e}")
    
    async def disconnect_from_servers(self) -> None:
        """Disconnect from all connected servers."""
        disconnect_tasks = []
        for client in self.connected_clients:
            disconnect_tasks.append(self._disconnect_client_safely(client))
        
        if disconnect_tasks:
            await asyncio.gather(*disconnect_tasks, return_exceptions=True)
        
        self.connected_clients.clear()
        self.clients.clear()
        self._tool_to_client_map.clear()
        logger.info("Disconnected from all MCP servers")
    
    async def _disconnect_client_safely(self, client: MCPClient) -> None:
        """Disconnect from a client with error handling."""
        try:
            await client.disconnect()
        except Exception as e:
            logger.warning(f"Error disconnecting from {client.name}: {e}")
    
    async def get_available_tools(self, project_id: str) -> List[Dict[str, Any]]:
        """Get all available tools from connected servers.
        
        Args:
            project_id: Project identifier for filtering
            
        Returns:
            List of available tool definitions
        """
        all_tools = []
        
        for client in self.connected_clients:
            try:
                tools = await client.list_tools()
                
                # Find server config for filtering
                server_config = next(
                    (config for config in self.server_configs if config["name"] == client.name),
                    {}
                )
                
                # Filter tools based on allowed_tools
                for tool in tools:
                    if self._is_tool_allowed(tool["name"], server_config):
                        # Add metadata about the server
                        tool["_server_name"] = client.name
                        tool["_client"] = client
                        all_tools.append(tool)
                        
            except Exception as e:
                logger.warning(f"Failed to get tools from {client.name}: {e}")
        
        return all_tools
    
    def _is_tool_allowed(self, tool_name: str, server_config: Dict[str, Any]) -> bool:
        """Check if a tool is allowed based on server configuration.
        
        Args:
            tool_name: Name of the tool
            server_config: Server configuration
            
        Returns:
            True if tool is allowed
        """
        allowed_tools = server_config.get("allowed_tools")
        
        # If no allowed_tools specified, all tools are allowed
        if allowed_tools is None:
            return True
        
        return tool_name in allowed_tools
    
    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Call a tool through the appropriate MCP server.
        
        Args:
            tool_name: Name of the tool to call
            arguments: Tool arguments
            
        Returns:
            Tool execution result
        """
        client = self._find_client_for_tool(tool_name)
        if not client:
            raise MCPServerManagerError(f"Tool '{tool_name}' not found in any connected MCP server")
        
        try:
            return await client.call_tool(tool_name, arguments)
        except Exception as e:
            raise MCPServerManagerError(f"Error calling tool '{tool_name}': {e}")
    
    def _find_client_for_tool(self, tool_name: str) -> Optional[MCPClient]:
        """Find the client that provides a specific tool.
        
        Args:
            tool_name: Name of the tool
            
        Returns:
            Client that provides the tool, or None if not found
        """
        return self._tool_to_client_map.get(tool_name)
    
    async def _refresh_tool_mappings(self, project_id: str) -> None:
        """Refresh the mapping of tools to clients."""
        self._tool_to_client_map.clear()
        
        for client in self.connected_clients:
            try:
                tools = await client.list_tools()
                server_config = next(
                    (config for config in self.server_configs if config["name"] == client.name),
                    {}
                )
                
                for tool in tools:
                    tool_name = tool["name"]
                    if self._is_tool_allowed(tool_name, server_config):
                        self._tool_to_client_map[tool_name] = client
                        
            except Exception as e:
                logger.warning(f"Failed to refresh tools from {client.name}: {e}")
    
    async def get_health_status(self) -> Dict[str, Any]:
        """Get health status of all configured servers.
        
        Returns:
            Dictionary with health information
        """
        total_configured = len(self.server_configs)
        enabled = len(self.get_enabled_servers())
        connected = len(self.connected_clients)
        failed = len(self.clients) - connected
        
        server_status = []
        for config in self.server_configs:
            client = next((c for c in self.clients if c.name == config["name"]), None)
            status = {
                "name": config["name"],
                "enabled": config.get("enabled", True),
                "connected": client.connected if client else False,
                "transport": config.get("transport", "unknown")
            }
            server_status.append(status)
        
        return {
            "total_configured": total_configured,
            "enabled": enabled,
            "connected": connected,
            "failed": failed,
            "server_status": server_status
        }
    
    async def retry_failed_connections(self) -> None:
        """Retry connections for failed servers."""
        if not self._current_project_id:
            logger.warning("No current project set, cannot retry connections")
            return
        
        failed_clients = [client for client in self.clients if not client.connected]
        
        if not failed_clients:
            return
        
        logger.info(f"Retrying {len(failed_clients)} failed MCP server connections")
        
        retry_tasks = [self._connect_client_safely(client) for client in failed_clients]
        await asyncio.gather(*retry_tasks, return_exceptions=True)
        
        # Update connected clients
        self.connected_clients = [client for client in self.clients if client.connected]
        
        # Refresh tool mappings
        if self.connected_clients:
            await self._refresh_tool_mappings(self._current_project_id)
    
    async def shutdown(self) -> None:
        """Gracefully shutdown the manager and all connections."""
        await self.disconnect_from_servers()
        logger.info("MCP server manager shutdown complete")
    
    async def for_project(self, project_id: str):
        """Context manager for project-scoped server management.
        
        Args:
            project_id: Project identifier
            
        Returns:
            Self for use in async with
        """
        return ProjectScopedManager(self, project_id)


class ProjectScopedManager:
    """Context manager for project-scoped MCP server management."""
    
    def __init__(self, manager: MCPServerManager, project_id: str):
        self.manager = manager
        self.project_id = project_id
    
    async def __aenter__(self):
        await self.manager.connect_to_servers(self.project_id)
        return self.manager
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.manager.disconnect_from_servers()