"""MCP tool gateway for integrating MCP tools with Suna's tool gating system."""

import logging
from typing import Dict, List, Any, Optional, Type
from .server_manager import MCPServerManager
from .tool_wrapper import MCPToolWrapper
from agentpress.tool_registry import ToolRegistry
from agentpress.tool import Tool


logger = logging.getLogger(__name__)


class MCPToolGatewayError(Exception):
    """Exception for MCP tool gateway errors."""
    pass


class MCPToolGateway:
    """Gateway for managing MCP tools with Suna's tool gating system."""
    
    def __init__(self, server_manager: MCPServerManager, tool_registry: ToolRegistry, 
                 config: Dict[str, Any]):
        """Initialize MCP tool gateway.
        
        Args:
            server_manager: MCP server manager instance
            tool_registry: Suna tool registry instance
            config: MCP configuration with gating settings
        """
        self.server_manager = server_manager
        self.tool_registry = tool_registry
        self.config = config
        self.enabled = config.get("enabled", True)
        self.registered_tools: List[Any] = []
        self._tool_cache: Dict[str, List[Dict[str, Any]]] = {}
    
    async def register_mcp_tools(self, project_id: str, thread_manager=None) -> None:
        """Register MCP tools for a specific project based on gating rules.
        
        Args:
            project_id: Project identifier
            thread_manager: Optional thread manager for tool initialization
        """
        if not self.enabled:
            logger.info("MCP integration is disabled")
            return
        
        try:
            # Get available tools from MCP servers
            available_tools = await self._discover_available_tools(project_id)
            
            # Filter tools based on gating configuration
            allowed_tools = self._filter_tools_by_gating(available_tools, project_id)
            
            logger.info(f"Registering {len(allowed_tools)} MCP tools for project {project_id}")
            
            # Store project_id and thread_manager for tool registration
            self._current_project_id = project_id
            self._current_thread_manager = thread_manager
            
            # Register each allowed tool
            for tool_info in allowed_tools:
                try:
                    await self._register_single_tool(tool_info)
                except Exception as e:
                    logger.error(f"Failed to register MCP tool {tool_info['name']}: {e}")
                    
        except Exception as e:
            logger.error(f"Failed to register MCP tools: {e}")
            raise MCPToolGatewayError(f"Failed to register MCP tools: {e}")
    
    async def _discover_available_tools(self, project_id: str, use_cache: bool = True) -> List[Dict[str, Any]]:
        """Discover available tools from MCP servers.
        
        Args:
            project_id: Project identifier
            use_cache: Whether to use cached tool list
            
        Returns:
            List of available tools
        """
        if use_cache and project_id in self._tool_cache:
            return self._tool_cache[project_id]
        
        tools = await self.server_manager.get_available_tools(project_id)
        self._tool_cache[project_id] = tools
        return tools
    
    def _filter_tools_by_gating(self, tools: List[Dict[str, Any]], project_id: str) -> List[Dict[str, Any]]:
        """Filter tools based on gating configuration.
        
        Args:
            tools: List of available tools
            project_id: Project identifier
            
        Returns:
            List of allowed tools
        """
        gating_config = self.config.get("tool_gating", {})
        mode = gating_config.get("mode", "all")
        
        if mode == "none":
            return []
        elif mode == "all":
            return [tool for tool in tools if self._is_tool_allowed(tool, project_id)]
        elif mode == "selective":
            return [tool for tool in tools if self._is_tool_allowed(tool, project_id)]
        else:
            logger.warning(f"Unknown gating mode: {mode}, defaulting to 'all'")
            return tools
    
    def _is_tool_allowed(self, tool_info: Dict[str, Any], project_id: str) -> bool:
        """Check if a tool is allowed based on gating rules.
        
        Args:
            tool_info: Tool information including name and server
            project_id: Project identifier
            
        Returns:
            True if tool is allowed
        """
        effective_config = self._get_effective_config(project_id)
        
        tool_name = tool_info["name"]
        server_name = tool_info.get("_server_name", "")
        
        # Check if tool is explicitly blocked
        blocked_tools = effective_config.get("blocked_tools", [])
        if tool_name in blocked_tools:
            return False
        
        # Check server allowlist
        allowed_servers = effective_config.get("allowed_servers")
        if allowed_servers is not None and server_name not in allowed_servers:
            return False
        
        # Check tool allowlist
        allowed_tools = effective_config.get("allowed_tools")
        if allowed_tools is not None and tool_name not in allowed_tools:
            return False
        
        return True
    
    def _get_effective_config(self, project_id: str) -> Dict[str, Any]:
        """Get effective configuration for a project, including overrides.
        
        Args:
            project_id: Project identifier
            
        Returns:
            Effective configuration dictionary
        """
        # Start with base gating config
        base_config = self.config.get("tool_gating", {}).copy()
        
        # Apply project-specific overrides
        project_overrides = self.config.get("project_overrides", {})
        if project_id in project_overrides:
            override = project_overrides[project_id]
            base_config.update(override)
        
        return base_config
    
    async def _register_single_tool(self, tool_info: Dict[str, Any]) -> None:
        """Register a single MCP tool with the tool registry.
        
        Args:
            tool_info: Tool information from MCP server
        """
        # Get the MCP client from tool info
        mcp_client = tool_info.pop("_client", None)
        if not mcp_client:
            raise MCPToolGatewayError(f"No MCP client found for tool {tool_info['name']}")
        
        # Create wrapper for the tool
        wrapper = MCPToolWrapper(mcp_client, tool_info)
        
        # Generate Suna tool class
        tool_class = wrapper.get_suna_tool_class()
        
        # Register with tool registry, passing required arguments
        register_kwargs = {}
        if hasattr(self, '_current_project_id'):
            register_kwargs['project_id'] = self._current_project_id
        if hasattr(self, '_current_thread_manager') and self._current_thread_manager:
            register_kwargs['thread_manager'] = self._current_thread_manager
            
        self.tool_registry.register_tool(tool_class, **register_kwargs)
        
        # Track registered tool class (not instance)
        self.registered_tools.append(tool_class)
        
        logger.debug(f"Registered MCP tool: {tool_info['name']} from {mcp_client.name}")
    
    async def unregister_mcp_tools(self) -> None:
        """Unregister all MCP tools from the registry."""
        if not self.enabled:
            return
        
        logger.info(f"Unregistering {len(self.registered_tools)} MCP tools")
        
        # Unregister each tool
        for tool in self.registered_tools:
            try:
                self.tool_registry.unregister_tool(tool)
            except Exception as e:
                logger.warning(f"Failed to unregister tool: {e}")
        
        self.registered_tools.clear()
        self._tool_cache.clear()
    
    async def refresh_tools(self, project_id: str) -> None:
        """Refresh MCP tools by unregistering and re-registering.
        
        Args:
            project_id: Project identifier
        """
        if not self.enabled:
            return
        
        logger.info(f"Refreshing MCP tools for project {project_id}")
        
        # Clear cache to force re-discovery
        self._tool_cache.pop(project_id, None)
        
        # Unregister existing tools
        await self.unregister_mcp_tools()
        
        # Re-register tools
        await self.register_mcp_tools(project_id)
    
    async def get_mcp_tool_info(self, project_id: str) -> Dict[str, Any]:
        """Get information about MCP tools for a project.
        
        Args:
            project_id: Project identifier
            
        Returns:
            Dictionary with tool information
        """
        available_tools = await self._discover_available_tools(project_id)
        allowed_tools = self._filter_tools_by_gating(available_tools, project_id)
        
        return {
            "enabled": self.enabled,
            "available_tools": available_tools,
            "allowed_tools": allowed_tools,
            "registered_tools": [
                {
                    "class_name": tool.__class__.__name__,
                    "mcp_tool_name": getattr(tool, "_mcp_tool_name", "unknown"),
                    "mcp_server_name": getattr(tool, "_mcp_server_name", "unknown")
                }
                for tool in self.registered_tools
            ],
            "config": self._get_effective_config(project_id)
        }
    
    def get_enabled_tool_classes(self) -> List[Type[Tool]]:
        """Get list of registered tool classes.
        
        Returns:
            List of tool classes that have been registered
        """
        return self.registered_tools
    
    def enable_tools(self, pattern: str) -> None:
        """Enable tools matching a pattern.
        
        Args:
            pattern: Tool name pattern (supports wildcards)
        """
        # This would be implemented based on the gating configuration
        # For now, it's a placeholder that doesn't affect registered_tools
        logger.debug(f"Enabling tools matching pattern: {pattern}")
    
    def disable_tools(self, pattern: str) -> None:
        """Disable tools matching a pattern.
        
        Args:
            pattern: Tool name pattern (supports wildcards)
        """
        # This would be implemented based on the gating configuration
        # For now, it's a placeholder that doesn't affect registered_tools
        logger.debug(f"Disabling tools matching pattern: {pattern}")
    
    async def cleanup(self) -> None:
        """Cleanup all resources including unregistering tools and disconnecting servers."""
        await self.unregister_mcp_tools()
        await self.server_manager.disconnect_all()
    
    def for_project(self, project_id: str):
        """Context manager for project-scoped tool registration.
        
        Args:
            project_id: Project identifier
            
        Returns:
            Self for use in async with
        """
        return ProjectScopedGateway(self, project_id)


class ProjectScopedGateway:
    """Context manager for project-scoped MCP tool gateway."""
    
    def __init__(self, gateway: MCPToolGateway, project_id: str):
        self.gateway = gateway
        self.project_id = project_id
    
    async def __aenter__(self):
        await self.gateway.register_mcp_tools(self.project_id)
        return self.gateway
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.gateway.unregister_mcp_tools()