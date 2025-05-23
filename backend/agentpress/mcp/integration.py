"""Integration module for adding MCP tools to Suna agents."""

import logging
from typing import Dict, Any, List, Optional
from agentpress.mcp.server_manager import MCPServerManager
from agentpress.mcp.tool_gateway import MCPToolGateway
from agentpress.thread_manager import ThreadManager


logger = logging.getLogger(__name__)


async def setup_mcp_tools(
    thread_manager: ThreadManager,
    project_id: str,
    mcp_config: Optional[Dict[str, Any]] = None
) -> MCPToolGateway:
    """Set up MCP tools for an agent based on configuration.
    
    Args:
        thread_manager: The thread manager to add tools to
        project_id: The project ID for context
        mcp_config: Optional MCP configuration. If not provided, will use default servers.
        
    Returns:
        MCPToolGateway instance managing the MCP tools
    """
    if mcp_config is None:
        # Default configuration - can be overridden by environment or database
        mcp_config = {
            "servers": [
                # Example MCP server configuration
                # {
                #     "name": "filesystem",
                #     "command": "npx",
                #     "args": ["-y", "@modelcontextprotocol/server-filesystem"],
                #     "env": {"WORKSPACE_DIR": "/path/to/workspace"}
                # }
            ],
            "tool_whitelist": None,  # Enable all tools by default
            "tool_blacklist": []     # No tools blacklisted by default
        }
    
    # Create server manager and tool gateway
    server_manager = MCPServerManager()
    tool_gateway = MCPToolGateway(server_manager)
    
    # Connect to configured servers
    servers = mcp_config.get("servers", [])
    for server_config in servers:
        try:
            name = server_config.get("name")
            command = server_config.get("command")
            args = server_config.get("args", [])
            env = server_config.get("env", {})
            
            if not name or not command:
                logger.warning(f"Skipping invalid server config: {server_config}")
                continue
                
            logger.info(f"Connecting to MCP server: {name}")
            await server_manager.connect_server(
                name=name,
                command=command,
                args=args,
                env=env
            )
            
        except Exception as e:
            logger.error(f"Failed to connect to MCP server {server_config.get('name')}: {e}")
            # Continue with other servers even if one fails
    
    # Configure tool filtering (this is handled internally by tool_gateway)
    whitelist = mcp_config.get("tool_whitelist")
    blacklist = mcp_config.get("tool_blacklist", [])
    
    # Register MCP tools - this will handle filtering internally
    await tool_gateway.register_mcp_tools(project_id, thread_manager)
    
    # Get the registered tool classes
    tool_classes = tool_gateway.get_enabled_tool_classes()
    
    logger.info(f"Successfully set up {len(tool_classes)} MCP tools")
    
    return tool_gateway


async def cleanup_mcp_tools(tool_gateway: MCPToolGateway):
    """Clean up MCP tools and disconnect servers.
    
    Args:
        tool_gateway: The tool gateway to clean up
    """
    try:
        await tool_gateway.cleanup()
        logger.info("Successfully cleaned up MCP tools")
    except Exception as e:
        logger.error(f"Error cleaning up MCP tools: {e}")