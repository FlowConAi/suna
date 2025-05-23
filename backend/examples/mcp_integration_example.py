"""Example of integrating MCP servers with Suna agents.

This example demonstrates how to:
1. Configure MCP servers
2. Set up tool gating
3. Add MCP tools to an agent
"""

import asyncio
from agentpress.thread_manager import ThreadManager
from agentpress.mcp import setup_mcp_tools, cleanup_mcp_tools


async def main():
    """Example of using MCP integration with Suna."""
    
    # Initialize thread manager (normally done in agent setup)
    thread_manager = ThreadManager(db=None)  # Use your actual DB connection
    
    # MCP configuration - this could come from environment or database
    mcp_config = {
        "servers": [
            {
                "name": "filesystem",
                "command": "npx",
                "args": ["-y", "@modelcontextprotocol/server-filesystem"],
                "env": {
                    "WORKSPACE_DIR": "/path/to/workspace"
                }
            },
            {
                "name": "github",
                "command": "npx", 
                "args": ["-y", "@modelcontextprotocol/server-github"],
                "env": {
                    "GITHUB_TOKEN": "your-github-token"
                }
            }
        ],
        # Tool gating configuration
        "tool_whitelist": None,  # None means all tools are allowed
        "tool_blacklist": ["dangerous_operation"]  # Blacklist specific tools
    }
    
    # Project ID for this agent session
    project_id = "example-project-123"
    
    try:
        # Set up MCP tools
        print("Setting up MCP tools...")
        tool_gateway = await setup_mcp_tools(
            thread_manager=thread_manager,
            project_id=project_id,
            mcp_config=mcp_config
        )
        
        # At this point, all MCP tools are registered with the thread_manager
        # and can be used by the agent just like native Suna tools
        
        # Get information about registered tools
        openapi_tools = thread_manager.tool_registry.get_openapi_schemas()
        xml_tools = thread_manager.tool_registry.get_xml_examples()
        
        print(f"\nRegistered {len(openapi_tools)} OpenAPI tools:")
        for tool in openapi_tools:
            print(f"  - {tool['function']['name']}")
            
        print(f"\nRegistered {len(xml_tools)} XML tools:")
        for tag_name in xml_tools:
            print(f"  - <{tag_name}>")
            
        # Example: Execute an MCP tool (if filesystem server is connected)
        # This would normally be done by the agent in response to user requests
        available_functions = thread_manager.tool_registry.get_available_functions()
        
        if "mcp_filesystem_read_file" in available_functions:
            print("\nTesting filesystem read tool...")
            read_file_func = available_functions["mcp_filesystem_read_file"]
            result = await read_file_func(path="/etc/hosts")
            print(f"Result: {result}")
            
    finally:
        # Clean up MCP connections
        print("\nCleaning up MCP tools...")
        await cleanup_mcp_tools(tool_gateway)
        print("Done!")


# Example with project-specific tool gating
async def project_specific_example():
    """Example showing project-specific tool configurations."""
    
    thread_manager = ThreadManager(db=None)
    
    # Different projects can have different tool access
    project_configs = {
        "secure-project": {
            "servers": [
                {
                    "name": "filesystem",
                    "command": "npx",
                    "args": ["-y", "@modelcontextprotocol/server-filesystem"],
                    "env": {
                        "WORKSPACE_DIR": "/secure/workspace",
                        "ALLOWED_PATHS": "/secure/workspace"  # Restrict access
                    }
                }
            ],
            "tool_whitelist": ["mcp_filesystem_read_file"],  # Only allow reading
            "tool_blacklist": []
        },
        "dev-project": {
            "servers": [
                {
                    "name": "filesystem",
                    "command": "npx",
                    "args": ["-y", "@modelcontextprotocol/server-filesystem"],
                    "env": {
                        "WORKSPACE_DIR": "/dev/workspace"
                    }
                },
                {
                    "name": "postgres",
                    "command": "npx",
                    "args": ["-y", "@modelcontextprotocol/server-postgres"],
                    "env": {
                        "DATABASE_URL": "postgresql://user:pass@localhost/devdb"
                    }
                }
            ],
            "tool_whitelist": None,  # Allow all tools
            "tool_blacklist": []
        }
    }
    
    # Set up tools for each project
    for project_id, config in project_configs.items():
        print(f"\nSetting up MCP tools for project: {project_id}")
        tool_gateway = await setup_mcp_tools(
            thread_manager=thread_manager,
            project_id=project_id,
            mcp_config=config
        )
        
        # Tools are now available for this project
        # In practice, each project would have its own agent instance
        
        await cleanup_mcp_tools(tool_gateway)


if __name__ == "__main__":
    # Run the basic example
    asyncio.run(main())
    
    # Run the project-specific example
    # asyncio.run(project_specific_example())