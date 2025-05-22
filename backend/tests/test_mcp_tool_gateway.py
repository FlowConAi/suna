"""Tests for MCP tool gateway integration."""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from agentpress.mcp.tool_gateway import MCPToolGateway, MCPToolGatewayError
from agentpress.tool_registry import ToolRegistry
from agentpress.tool import ToolResult


class TestMCPToolGateway:
    """Test cases for MCPToolGateway."""

    @pytest.fixture
    def mock_server_manager(self):
        """Mock MCP server manager."""
        manager = AsyncMock()
        manager.get_available_tools = AsyncMock(return_value=[])
        manager.call_tool = AsyncMock()
        return manager

    @pytest.fixture
    def mock_tool_registry(self):
        """Mock tool registry."""
        registry = Mock(spec=ToolRegistry)
        registry.register_tool = Mock()
        registry.get_openapi_schemas = Mock(return_value=[])
        registry.get_xml_schemas = Mock(return_value=[])
        return registry

    @pytest.fixture
    def sample_mcp_tools(self):
        """Sample MCP tools from multiple servers."""
        return [
            {
                "name": "calculator",
                "description": "Perform calculations",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "expression": {"type": "string"}
                    },
                    "required": ["expression"]
                },
                "_server_name": "math-server",
                "_client": AsyncMock()
            },
            {
                "name": "file_reader",
                "description": "Read file contents",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string"}
                    },
                    "required": ["path"]
                },
                "_server_name": "file-server",
                "_client": AsyncMock()
            }
        ]

    @pytest.fixture
    def mcp_config(self):
        """MCP configuration for testing."""
        return {
            "enabled": True,
            "tool_gating": {
                "mode": "selective",  # "all", "selective", "none"
                "allowed_servers": ["math-server"],
                "allowed_tools": ["calculator", "file_reader"],
                "blocked_tools": ["dangerous_tool"]
            },
            "project_overrides": {
                "project-123": {
                    "allowed_servers": ["math-server", "file-server"],
                    "blocked_tools": []
                }
            }
        }

    def test_gateway_initialization(self, mock_server_manager, mock_tool_registry, mcp_config):
        """Test MCPToolGateway initialization."""
        gateway = MCPToolGateway(mock_server_manager, mock_tool_registry, mcp_config)
        
        assert gateway.server_manager == mock_server_manager
        assert gateway.tool_registry == mock_tool_registry
        assert gateway.config == mcp_config
        assert len(gateway.registered_tools) == 0

    def test_gateway_initialization_disabled(self, mock_server_manager, mock_tool_registry):
        """Test gateway initialization when MCP is disabled."""
        config = {"enabled": False}
        gateway = MCPToolGateway(mock_server_manager, mock_tool_registry, config)
        
        assert gateway.enabled is False

    @pytest.mark.asyncio
    async def test_register_tools_selective_mode(self, mock_server_manager, mock_tool_registry, 
                                                 sample_mcp_tools, mcp_config):
        """Test registering tools in selective mode."""
        gateway = MCPToolGateway(mock_server_manager, mock_tool_registry, mcp_config)
        
        # Mock server manager to return sample tools
        mock_server_manager.get_available_tools.return_value = sample_mcp_tools
        
        await gateway.register_mcp_tools("test-project")
        
        # Should register allowed tools only
        assert mock_tool_registry.register_tool.call_count == 1  # Only calculator allowed
        
        # Verify the registered tool
        call_args = mock_tool_registry.register_tool.call_args_list[0]
        tool_class = call_args[0][0]
        assert hasattr(tool_class(), 'mcp_math_server_calculator')

    @pytest.mark.asyncio
    async def test_register_tools_all_mode(self, mock_server_manager, mock_tool_registry, 
                                          sample_mcp_tools):
        """Test registering tools in 'all' mode."""
        config = {
            "enabled": True,
            "tool_gating": {"mode": "all"}
        }
        gateway = MCPToolGateway(mock_server_manager, mock_tool_registry, config)
        
        mock_server_manager.get_available_tools.return_value = sample_mcp_tools
        
        await gateway.register_mcp_tools("test-project")
        
        # Should register all tools
        assert mock_tool_registry.register_tool.call_count == 2

    @pytest.mark.asyncio
    async def test_register_tools_none_mode(self, mock_server_manager, mock_tool_registry, 
                                           sample_mcp_tools):
        """Test registering tools in 'none' mode."""
        config = {
            "enabled": True,
            "tool_gating": {"mode": "none"}
        }
        gateway = MCPToolGateway(mock_server_manager, mock_tool_registry, config)
        
        mock_server_manager.get_available_tools.return_value = sample_mcp_tools
        
        await gateway.register_mcp_tools("test-project")
        
        # Should register no tools
        assert mock_tool_registry.register_tool.call_count == 0

    @pytest.mark.asyncio
    async def test_register_tools_project_override(self, mock_server_manager, mock_tool_registry, 
                                                   sample_mcp_tools, mcp_config):
        """Test tool registration with project-specific overrides."""
        gateway = MCPToolGateway(mock_server_manager, mock_tool_registry, mcp_config)
        
        mock_server_manager.get_available_tools.return_value = sample_mcp_tools
        
        # Use project with overrides
        await gateway.register_mcp_tools("project-123")
        
        # Should register both tools (override allows file-server)
        assert mock_tool_registry.register_tool.call_count == 2

    @pytest.mark.asyncio
    async def test_register_tools_blocked_tools(self, mock_server_manager, mock_tool_registry, mcp_config):
        """Test tool registration with blocked tools."""
        gateway = MCPToolGateway(mock_server_manager, mock_tool_registry, mcp_config)
        
        # Add a blocked tool to the sample tools
        tools_with_blocked = [
            {
                "name": "dangerous_tool",
                "description": "A dangerous tool",
                "inputSchema": {"type": "object"},
                "_server_name": "math-server",
                "_client": AsyncMock()
            }
        ]
        
        mock_server_manager.get_available_tools.return_value = tools_with_blocked
        
        await gateway.register_mcp_tools("test-project")
        
        # Should not register the blocked tool
        assert mock_tool_registry.register_tool.call_count == 0

    def test_is_tool_allowed_selective_mode(self, mock_server_manager, mock_tool_registry, mcp_config):
        """Test tool permission checking in selective mode."""
        gateway = MCPToolGateway(mock_server_manager, mock_tool_registry, mcp_config)
        
        tool_info = {
            "name": "calculator",
            "_server_name": "math-server"
        }
        
        # Should be allowed (in allowed_tools and allowed_servers)
        assert gateway._is_tool_allowed(tool_info, "test-project") is True
        
        # Test blocked tool
        blocked_tool = {
            "name": "dangerous_tool",
            "_server_name": "math-server"
        }
        assert gateway._is_tool_allowed(blocked_tool, "test-project") is False
        
        # Test tool from disallowed server
        disallowed_server_tool = {
            "name": "file_reader",
            "_server_name": "file-server"
        }
        assert gateway._is_tool_allowed(disallowed_server_tool, "test-project") is False

    def test_is_tool_allowed_with_project_override(self, mock_server_manager, mock_tool_registry, mcp_config):
        """Test tool permission with project-specific overrides."""
        gateway = MCPToolGateway(mock_server_manager, mock_tool_registry, mcp_config)
        
        # Tool from file-server should be allowed for project-123 (has override)
        tool_info = {
            "name": "file_reader",
            "_server_name": "file-server"
        }
        
        assert gateway._is_tool_allowed(tool_info, "project-123") is True
        assert gateway._is_tool_allowed(tool_info, "other-project") is False

    def test_get_effective_config_default(self, mock_server_manager, mock_tool_registry, mcp_config):
        """Test getting effective configuration for default project."""
        gateway = MCPToolGateway(mock_server_manager, mock_tool_registry, mcp_config)
        
        effective_config = gateway._get_effective_config("test-project")
        
        assert effective_config["allowed_servers"] == ["math-server"]
        assert effective_config["blocked_tools"] == ["dangerous_tool"]

    def test_get_effective_config_with_override(self, mock_server_manager, mock_tool_registry, mcp_config):
        """Test getting effective configuration with project override."""
        gateway = MCPToolGateway(mock_server_manager, mock_tool_registry, mcp_config)
        
        effective_config = gateway._get_effective_config("project-123")
        
        assert effective_config["allowed_servers"] == ["math-server", "file-server"]
        assert effective_config["blocked_tools"] == []  # Override clears blocked tools

    @pytest.mark.asyncio
    async def test_unregister_tools(self, mock_server_manager, mock_tool_registry, 
                                   sample_mcp_tools, mcp_config):
        """Test unregistering MCP tools."""
        gateway = MCPToolGateway(mock_server_manager, mock_tool_registry, mcp_config)
        
        # First register some tools
        mock_server_manager.get_available_tools.return_value = sample_mcp_tools
        await gateway.register_mcp_tools("test-project")
        
        # Track registered tools
        registered_tool_classes = [call[0][0] for call in mock_tool_registry.register_tool.call_args_list]
        gateway.registered_tools = [tool_class() for tool_class in registered_tool_classes]
        
        # Mock unregister method
        mock_tool_registry.unregister_tool = Mock()
        
        await gateway.unregister_mcp_tools()
        
        # Should unregister all registered tools
        assert mock_tool_registry.unregister_tool.call_count == len(gateway.registered_tools)
        assert len(gateway.registered_tools) == 0

    @pytest.mark.asyncio
    async def test_refresh_tools(self, mock_server_manager, mock_tool_registry, 
                                sample_mcp_tools, mcp_config):
        """Test refreshing MCP tools."""
        gateway = MCPToolGateway(mock_server_manager, mock_tool_registry, mcp_config)
        
        # Mock unregister and register methods
        gateway.unregister_mcp_tools = AsyncMock()
        gateway.register_mcp_tools = AsyncMock()
        
        await gateway.refresh_tools("test-project")
        
        gateway.unregister_mcp_tools.assert_called_once()
        gateway.register_mcp_tools.assert_called_once_with("test-project")

    @pytest.mark.asyncio
    async def test_get_tool_info(self, mock_server_manager, mock_tool_registry, 
                                sample_mcp_tools, mcp_config):
        """Test getting information about registered MCP tools."""
        gateway = MCPToolGateway(mock_server_manager, mock_tool_registry, mcp_config)
        
        mock_server_manager.get_available_tools.return_value = sample_mcp_tools
        await gateway.register_mcp_tools("test-project")
        
        tool_info = await gateway.get_mcp_tool_info("test-project")
        
        assert "available_tools" in tool_info
        assert "registered_tools" in tool_info
        assert "config" in tool_info
        
        # Should have the calculator tool in available
        available_names = [tool["name"] for tool in tool_info["available_tools"]]
        assert "calculator" in available_names

    @pytest.mark.asyncio
    async def test_disabled_gateway_operations(self, mock_server_manager, mock_tool_registry):
        """Test that disabled gateway doesn't perform operations."""
        config = {"enabled": False}
        gateway = MCPToolGateway(mock_server_manager, mock_tool_registry, config)
        
        # All operations should be no-ops
        await gateway.register_mcp_tools("test-project")
        await gateway.unregister_mcp_tools()
        await gateway.refresh_tools("test-project")
        
        # No tools should be registered
        mock_tool_registry.register_tool.assert_not_called()

    @pytest.mark.asyncio
    async def test_error_handling_during_registration(self, mock_server_manager, mock_tool_registry, mcp_config):
        """Test error handling during tool registration."""
        gateway = MCPToolGateway(mock_server_manager, mock_tool_registry, mcp_config)
        
        # Mock server manager to raise an error
        mock_server_manager.get_available_tools.side_effect = Exception("Server error")
        
        with pytest.raises(MCPToolGatewayError, match="Failed to register MCP tools"):
            await gateway.register_mcp_tools("test-project")

    @pytest.mark.asyncio
    async def test_partial_registration_failure(self, mock_server_manager, mock_tool_registry, 
                                               sample_mcp_tools, mcp_config):
        """Test handling partial failures during tool registration."""
        gateway = MCPToolGateway(mock_server_manager, mock_tool_registry, mcp_config)
        
        mock_server_manager.get_available_tools.return_value = sample_mcp_tools
        
        # Mock registry to fail on second registration
        mock_tool_registry.register_tool.side_effect = [None, Exception("Registration failed")]
        
        # Should not raise error but log the failure
        await gateway.register_mcp_tools("test-project")
        
        # First tool should still be tracked as registered
        assert len(gateway.registered_tools) == 1

    @pytest.mark.asyncio
    async def test_tool_discovery_and_caching(self, mock_server_manager, mock_tool_registry, 
                                              sample_mcp_tools, mcp_config):
        """Test tool discovery with caching."""
        gateway = MCPToolGateway(mock_server_manager, mock_tool_registry, mcp_config)
        
        mock_server_manager.get_available_tools.return_value = sample_mcp_tools
        
        # First call should fetch from server
        tools1 = await gateway._discover_available_tools("test-project", use_cache=True)
        
        # Second call should use cache (mock should only be called once)
        tools2 = await gateway._discover_available_tools("test-project", use_cache=True)
        
        assert tools1 == tools2
        mock_server_manager.get_available_tools.assert_called_once()

    @pytest.mark.asyncio
    async def test_tool_versioning_support(self, mock_server_manager, mock_tool_registry, mcp_config):
        """Test handling tools with version information."""
        gateway = MCPToolGateway(mock_server_manager, mock_tool_registry, mcp_config)
        
        versioned_tools = [
            {
                "name": "calculator",
                "description": "Perform calculations",
                "version": "1.2.0",
                "inputSchema": {"type": "object"},
                "_server_name": "math-server",
                "_client": AsyncMock()
            }
        ]
        
        mock_server_manager.get_available_tools.return_value = versioned_tools
        
        await gateway.register_mcp_tools("test-project")
        
        # Should handle versioned tools correctly
        assert mock_tool_registry.register_tool.call_count == 1

    @pytest.mark.asyncio
    async def test_dynamic_tool_updates(self, mock_server_manager, mock_tool_registry, 
                                       sample_mcp_tools, mcp_config):
        """Test handling dynamic tool updates from MCP servers."""
        gateway = MCPToolGateway(mock_server_manager, mock_tool_registry, mcp_config)
        
        # Initial registration
        mock_server_manager.get_available_tools.return_value = sample_mcp_tools
        await gateway.register_mcp_tools("test-project")
        
        initial_count = mock_tool_registry.register_tool.call_count
        
        # Simulate tool list change
        updated_tools = sample_mcp_tools + [{
            "name": "new_tool",
            "description": "A new tool",
            "inputSchema": {"type": "object"},
            "_server_name": "math-server",
            "_client": AsyncMock()
        }]
        
        mock_server_manager.get_available_tools.return_value = updated_tools
        
        # Refresh should detect and register new tool
        await gateway.refresh_tools("test-project")
        
        # Should have more registrations after refresh
        assert mock_tool_registry.register_tool.call_count > initial_count

    @pytest.mark.asyncio
    async def test_context_manager_integration(self, mock_server_manager, mock_tool_registry, mcp_config):
        """Test gateway as context manager for automatic cleanup."""
        gateway = MCPToolGateway(mock_server_manager, mock_tool_registry, mcp_config)
        
        gateway.register_mcp_tools = AsyncMock()
        gateway.unregister_mcp_tools = AsyncMock()
        
        async with gateway.for_project("test-project") as gw:
            assert gw == gateway
            gateway.register_mcp_tools.assert_called_once_with("test-project")
        
        gateway.unregister_mcp_tools.assert_called_once()