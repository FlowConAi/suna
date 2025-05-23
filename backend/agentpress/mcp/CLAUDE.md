# MCP (Model Context Protocol) Integration

This directory contains the Model Context Protocol integration for Suna, enabling the agent to connect to external MCP servers and use their tools seamlessly within the AgentPress framework.

## Overview

The MCP integration allows Suna to:
- Connect to any MCP-compliant server (e.g., filesystem access, database connections, API integrations)
- Dynamically discover and register tools from MCP servers
- Use MCP tools alongside native Suna tools with unified handling
- Support multiple concurrent MCP server connections
- Apply tool gating rules (whitelist/blacklist) for security

## Architecture

### Core Components

1. **MCPClient** (`client.py`)
   - Handles low-level communication with MCP servers
   - Supports STDIO and HTTP transports
   - Manages JSON-RPC protocol for MCP communication
   - Handles server lifecycle (connect, disconnect, health checks)

2. **MCPServerManager** (`server_manager.py`)
   - Manages multiple MCP client connections
   - Handles project-scoped server configurations
   - Provides connection pooling and retry logic
   - Maps tools to their respective MCP clients

3. **MCPToolGateway** (`tool_gateway.py`)
   - Bridge between MCP tools and AgentPress tool system
   - Applies tool filtering (whitelist/blacklist)
   - Handles tool discovery and registration
   - Manages tool caching for performance

4. **MCPToolWrapper** (`tool_wrapper.py`)
   - Wraps MCP tools as AgentPress-compatible tool classes
   - Handles parameter mapping and validation
   - Provides both OpenAPI and XML schemas
   - Manages tool execution through MCP protocol

5. **Integration Module** (`integration.py`)
   - High-level API for setting up MCP tools
   - Handles configuration and initialization
   - Provides cleanup functions

## Configuration

MCP servers are configured in the agent's run.py file:

```python
mcp_config = {
    "servers": [
        {
            "name": "context7",
            "transport": "stdio",  # or "http"
            "command": "npx",
            "args": ["-y", "@upstash/context7-mcp@latest"],
            "enabled": True,
            "project_scope": "global",  # or "project_id"
            "tool_whitelist": None,  # List of allowed tools
            "tool_blacklist": []     # List of blocked tools
        }
    ],
    "tool_whitelist": None,  # Global whitelist
    "tool_blacklist": []     # Global blacklist
}
```

### Server Configuration Options

- **name**: Unique identifier for the server
- **transport**: Communication method ("stdio" or "http")
- **command**: Executable to run (for stdio transport)
- **args**: Command arguments
- **url**: Server URL (for http transport)
- **env**: Environment variables for the server process
- **enabled**: Whether the server is active
- **project_scope**: "global" or specific project ID
- **tool_whitelist/blacklist**: Server-specific tool filtering

## Tool Discovery and Registration

1. **Discovery Process**:
   - MCPClient sends `tools/list` request to server
   - Server returns available tools with schemas
   - Tools are cached per project for performance

2. **Registration**:
   - MCPToolWrapper creates dynamic tool classes
   - Each tool gets unique XML tag and OpenAPI schema
   - Tools are registered with ThreadManager
   - Tool descriptions include "(via MCP server: {name})"

3. **Schema Handling**:
   - MCP tools provide their own schemas
   - Wrapper adds both XML and OpenAPI formats
   - Parameter mapping handles nested structures
   - Type conversion ensures compatibility

## Tool Execution Flow

1. Agent calls tool through normal AgentPress flow
2. MCPToolWrapper receives the call
3. Parameters are validated and formatted
4. Request sent to MCP server via JSON-RPC
5. Response processed and returned to agent
6. Errors handled gracefully with fallbacks

## Error Handling

The integration includes robust error handling:

1. **Connection Failures**: 
   - Servers that fail to connect don't block others
   - Agent continues without failed servers
   - Retry logic for transient failures

2. **Tool Execution Errors**:
   - MCP errors converted to AgentPress format
   - Detailed error messages for debugging
   - Graceful degradation when tools fail

3. **Setup Failures**:
   - If MCP setup fails, agent continues normally
   - Error logged but doesn't crash agent
   - Fallback to non-MCP tools

## Security Considerations

1. **Tool Gating**:
   - Global and per-server whitelists/blacklists
   - Tools filtered before registration
   - Prevents unauthorized tool access

2. **Process Isolation**:
   - STDIO servers run as separate processes
   - Limited environment variable exposure
   - Controlled resource access

3. **Input Validation**:
   - All tool inputs validated against schemas
   - Parameter sanitization before execution
   - Type checking and bounds validation

## Usage Examples

### Adding a New MCP Server

1. Add server configuration to `run.py`:
```python
{
    "name": "my-server",
    "transport": "stdio",
    "command": "my-mcp-server",
    "args": ["--config", "path/to/config"],
    "enabled": True
}
```

2. Ensure the server executable is available in the Docker container
3. The server's tools will be automatically discovered and registered

### Creating Custom MCP Servers

MCP servers must implement:
- JSON-RPC protocol over STDIO or HTTP
- `initialize` method for handshake
- `tools/list` method for discovery
- `tools/call` method for execution

## Testing

Test scripts are provided:
- `test_mcp_client.py`: Unit tests for client
- `test_mcp_integration.py`: Integration tests
- `test_mcp_server_manager.py`: Server management tests
- `test_mcp_tool_wrapper.py`: Tool wrapping tests

## Common MCP Servers

1. **context7**: Documentation lookup
   - Provides up-to-date library documentation
   - Requires: `npx` command
   - Tools: `resolve-library-id`, `get-library-docs`

2. **basic-memory**: Persistent storage
   - Stores notes and context across sessions
   - Requires: `uvx` command
   - Tools: `write_note`, `read_note`, `search_notes`, etc.

## Troubleshooting

1. **"Command not found" errors**:
   - Ensure npx/uvx installed in Docker image
   - Check PATH environment variable
   - Verify command in server config

2. **"Failed to connect" errors**:
   - Check server executable exists
   - Verify transport configuration
   - Check server logs for errors

3. **Tools not appearing**:
   - Verify server connected successfully
   - Check tool whitelist/blacklist
   - Ensure proper MCP protocol implementation

## Future Enhancements

1. **Persistent Connections**: 
   - Connection pooling across agent runs
   - Reduced startup latency

2. **Dynamic Server Management**:
   - Add/remove servers at runtime
   - Hot-reload configurations

3. **Enhanced Security**:
   - Sandboxed server execution
   - Fine-grained permission controls

4. **Performance Optimizations**:
   - Parallel tool discovery
   - Smarter caching strategies