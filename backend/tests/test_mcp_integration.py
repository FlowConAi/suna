"""Integration tests for MCP client with a real server."""

import pytest
import asyncio
import sys
import os
from pathlib import Path
from agentpress.mcp.client import MCPClient
from agentpress.mcp.tool_wrapper import MCPToolWrapper
from agentpress.mcp.server_manager import MCPServerManager
from agentpress.mcp.tool_gateway import MCPToolGateway
from agentpress.tool_registry import ToolRegistry


class TestMCPIntegration:
    """Integration tests using a real MCP server process."""
    
    @pytest.fixture
    def test_server_config(self):
        """Configuration for test MCP server."""
        test_server_path = Path(__file__).parent / "test_mcp_server.py"
        return {
            "name": "test-integration-server",
            "transport": "stdio",
            "command": sys.executable,  # Use current Python interpreter
            "args": [str(test_server_path)],
            "enabled": True,
            "allowed_tools": None,  # Allow all tools
            "project_scope": "global"
        }
    
    @pytest.mark.asyncio
    async def test_full_handshake_and_tool_list(self, test_server_config):
        """Test complete handshake and tool listing with real server."""
        client = MCPClient(test_server_config)
        
        try:
            # Connect to server
            await client.connect()
            assert client.connected
            assert client.server_capabilities == {"tools": {}}
            
            # List tools
            tools = await client.list_tools()
            assert len(tools) == 2
            
            tool_names = [tool["name"] for tool in tools]
            assert "add" in tool_names
            assert "echo" in tool_names
            
            # Verify tool schemas
            add_tool = next(t for t in tools if t["name"] == "add")
            assert add_tool["description"] == "Add two numbers"
            assert "a" in add_tool["inputSchema"]["properties"]
            assert "b" in add_tool["inputSchema"]["properties"]
            
        finally:
            # Disconnect
            await client.disconnect()
            assert not client.connected
    
    @pytest.mark.asyncio
    async def test_tool_execution(self, test_server_config):
        """Test executing tools on the server."""
        client = MCPClient(test_server_config)
        
        try:
            await client.connect()
            
            # Test add tool
            result = await client.call_tool("add", {"a": 5, "b": 3})
            assert result["content"][0]["text"] == "Result: 8"
            assert result["isError"] is False
            
            # Test echo tool
            result = await client.call_tool("echo", {"message": "Hello MCP!"})
            assert result["content"][0]["text"] == "Echo: Hello MCP!"
            assert result["isError"] is False
            
            # Test unknown tool
            try:
                result = await client.call_tool("unknown", {})
                # If we get a result, it should indicate an error
                assert result.get("isError", False) or "error" in str(result)
            except Exception as e:
                # Expected - unknown tool should raise an error
                assert "Unknown tool" in str(e)
            
        finally:
            await client.disconnect()
    
    @pytest.mark.asyncio
    async def test_tool_wrapper_integration(self, test_server_config):
        """Test MCPToolWrapper with real server."""
        client = MCPClient(test_server_config)
        
        try:
            await client.connect()
            
            # Get tool definition
            tools = await client.list_tools()
            add_tool_def = next(t for t in tools if t["name"] == "add")
            
            # Create wrapper
            wrapper = MCPToolWrapper(client, add_tool_def)
            
            # Test OpenAPI schema generation
            openapi_schema = wrapper.get_openapi_schema()
            assert openapi_schema["function"]["name"] == "mcp_test_integration_server_add"
            assert "Add two numbers" in openapi_schema["function"]["description"]
            
            # Test XML schema generation
            xml_schema = wrapper.get_xml_schema()
            assert xml_schema.tag_name == "mcp-test-integration-server-add"
            
            # Test tool execution through wrapper
            result = await wrapper.call_tool(a=10, b=20)
            assert result.success is True
            assert "Result: 30" in result.output
            
            # Test with missing arguments
            result = await wrapper.call_tool(a=10)  # Missing 'b'
            assert result.success is False
            assert "Missing required argument" in result.output
            
        finally:
            await client.disconnect()
    
    @pytest.mark.asyncio
    async def test_server_manager_integration(self, test_server_config):
        """Test MCPServerManager with real server."""
        configs = [test_server_config]
        manager = MCPServerManager(configs)
        
        try:
            # Connect to servers
            await manager.connect_to_servers("test-project")
            assert len(manager.connected_clients) == 1
            
            # Get available tools
            tools = await manager.get_available_tools("test-project")
            assert len(tools) == 2
            
            # Call tool through manager
            result = await manager.call_tool("add", {"a": 15, "b": 25})
            assert result["content"][0]["text"] == "Result: 40"
            
            # Test health status
            health = await manager.get_health_status()
            assert health["connected"] == 1
            assert health["server_status"][0]["connected"] is True
            
        finally:
            await manager.disconnect_from_servers()
    
    @pytest.mark.asyncio
    async def test_tool_gateway_integration(self, test_server_config):
        """Test MCPToolGateway with real server."""
        # Setup
        configs = [test_server_config]
        manager = MCPServerManager(configs)
        registry = ToolRegistry()
        
        gateway_config = {
            "enabled": True,
            "tool_gating": {
                "mode": "selective",
                "allowed_tools": ["add"],  # Only allow 'add' tool
                "blocked_tools": ["echo"]
            }
        }
        
        gateway = MCPToolGateway(manager, registry, gateway_config)
        
        try:
            # Connect and register tools
            await manager.connect_to_servers("test-project")
            
            # Create a mock thread_manager for testing
            class MockThreadManager:
                pass
            
            mock_thread_manager = MockThreadManager()
            await gateway.register_mcp_tools("test-project", thread_manager=mock_thread_manager)
            
            # Check that only 'add' tool was registered
            openapi_schemas = registry.get_openapi_schemas()
            assert len(openapi_schemas) == 1
            assert "mcp_test_integration_server_add" in str(openapi_schemas[0])
            
            # Get tool info
            info = await gateway.get_mcp_tool_info("test-project")
            assert len(info["available_tools"]) == 2  # Both tools available
            assert len(info["allowed_tools"]) == 1   # Only 'add' allowed
            assert info["allowed_tools"][0]["name"] == "add"
            
        finally:
            await gateway.unregister_mcp_tools()
            await manager.disconnect_from_servers()
    
    @pytest.mark.asyncio
    async def test_concurrent_operations(self, test_server_config):
        """Test concurrent operations with real server."""
        client = MCPClient(test_server_config)
        
        try:
            await client.connect()
            
            # Execute multiple tools concurrently
            tasks = [
                client.call_tool("add", {"a": i, "b": i + 1})
                for i in range(5)
            ]
            
            results = await asyncio.gather(*tasks)
            
            # Verify all results
            for i, result in enumerate(results):
                expected = f"Result: {i + (i + 1)}"
                assert result["content"][0]["text"] == expected
                
        finally:
            await client.disconnect()
    
    @pytest.mark.asyncio 
    async def test_error_handling_with_real_server(self, test_server_config):
        """Test error handling scenarios with real server."""
        client = MCPClient(test_server_config)
        
        try:
            await client.connect()
            
            # Test method not found
            try:
                await client.send_request("unknown/method", {})
                assert False, "Should have raised error"
            except Exception as e:
                assert "Method not found" in str(e)
            
            # Connection should still be valid
            assert client.connected
            
            # Should still be able to call tools
            result = await client.call_tool("echo", {"message": "Still working"})
            assert "Echo: Still working" in result["content"][0]["text"]
            
        finally:
            await client.disconnect()
    
    @pytest.mark.asyncio
    async def test_graceful_shutdown(self, test_server_config):
        """Test graceful server shutdown."""
        client = MCPClient(test_server_config)
        
        try:
            await client.connect()
            
            # Send shutdown command
            result = await client.send_request("shutdown", {})
            assert result["status"] == "shutting down"
            
            # Server should close connection
            await asyncio.sleep(0.1)
            
            # Further operations should fail
            try:
                await client.call_tool("echo", {"message": "test"})
            except:
                # Expected - server has shut down
                pass
                
        finally:
            # Ensure cleanup even if server already shut down
            client.connected = False
            if client.process:
                try:
                    client.process.terminate()
                except ProcessLookupError:
                    # Process already terminated
                    pass