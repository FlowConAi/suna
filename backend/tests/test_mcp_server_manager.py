"""Tests for MCP server manager implementation."""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from agentpress.mcp.server_manager import MCPServerManager, MCPServerManagerError
from agentpress.mcp.client import MCPClient


class TestMCPServerManager:
    """Test cases for MCPServerManager."""

    @pytest.fixture
    def sample_server_configs(self):
        """Sample MCP server configurations."""
        return [
            {
                "name": "calculator-server",
                "transport": "stdio",
                "command": "python",
                "args": ["-m", "calculator_server"],
                "enabled": True,
                "allowed_tools": ["add", "multiply"],
                "project_scope": "global"
            },
            {
                "name": "file-server",
                "transport": "stdio",
                "command": "python",
                "args": ["-m", "file_server"],
                "enabled": True,
                "allowed_tools": None,  # All tools allowed
                "project_scope": "project"
            },
            {
                "name": "disabled-server",
                "transport": "stdio",
                "command": "python",
                "args": ["-m", "disabled_server"],
                "enabled": False,
                "allowed_tools": ["test"],
                "project_scope": "global"
            }
        ]

    @pytest.fixture
    def mock_config(self):
        """Mock configuration with MCP settings."""
        config = Mock()
        config.MCP_ENABLED = True
        config.MCP_SERVERS = [
            {
                "name": "test-server",
                "transport": "stdio",
                "command": "python",
                "args": ["-m", "test_server"],
                "enabled": True,
                "allowed_tools": ["test_tool"],
                "project_scope": "global"
            }
        ]
        return config

    def test_manager_initialization(self, sample_server_configs):
        """Test MCPServerManager initialization."""
        manager = MCPServerManager(sample_server_configs)
        
        assert len(manager.server_configs) == 3
        assert len(manager.clients) == 0
        assert len(manager.connected_clients) == 0

    def test_manager_initialization_empty_config(self):
        """Test manager initialization with empty config."""
        manager = MCPServerManager([])
        
        assert len(manager.server_configs) == 0
        assert len(manager.clients) == 0

    def test_get_enabled_servers(self, sample_server_configs):
        """Test getting enabled server configurations."""
        manager = MCPServerManager(sample_server_configs)
        
        enabled_servers = manager.get_enabled_servers()
        
        assert len(enabled_servers) == 2  # calculator-server and file-server
        server_names = [s["name"] for s in enabled_servers]
        assert "calculator-server" in server_names
        assert "file-server" in server_names
        assert "disabled-server" not in server_names

    def test_get_servers_for_project_global_scope(self, sample_server_configs):
        """Test getting servers for project with global scope."""
        manager = MCPServerManager(sample_server_configs)
        
        project_servers = manager.get_servers_for_project("any-project-id")
        
        # Should include global and project-scoped servers
        assert len(project_servers) == 2
        server_names = [s["name"] for s in project_servers]
        assert "calculator-server" in server_names  # global scope
        assert "file-server" in server_names  # project scope

    def test_get_servers_for_project_specific_scope(self):
        """Test getting servers for specific project scope."""
        configs = [
            {
                "name": "global-server",
                "enabled": True,
                "project_scope": "global"
            },
            {
                "name": "project-specific-server",
                "enabled": True,
                "project_scope": "project-123"
            },
            {
                "name": "other-project-server",
                "enabled": True,
                "project_scope": "project-456"
            }
        ]
        
        manager = MCPServerManager(configs)
        
        # Test for project-123
        project_servers = manager.get_servers_for_project("project-123")
        server_names = [s["name"] for s in project_servers]
        
        assert "global-server" in server_names
        assert "project-specific-server" in server_names
        assert "other-project-server" not in server_names

    @pytest.mark.asyncio
    async def test_connect_to_servers_success(self, sample_server_configs):
        """Test successful connection to servers."""
        manager = MCPServerManager(sample_server_configs)
        
        # Mock successful client connections
        with patch('agentpress.mcp.server_manager.MCPClient') as mock_client_class:
            mock_clients = []
            for _ in range(2):  # Two enabled servers
                mock_client = AsyncMock()
                mock_client.connect = AsyncMock()
                mock_client.connected = True
                mock_client.name = "test-server"
                mock_clients.append(mock_client)
            
            mock_client_class.side_effect = mock_clients
            
            await manager.connect_to_servers("test-project")
            
            assert len(manager.clients) == 2
            assert len(manager.connected_clients) == 2
            
            # Verify all clients were connected
            for client in mock_clients:
                client.connect.assert_called_once()

    @pytest.mark.asyncio
    async def test_connect_to_servers_partial_failure(self, sample_server_configs):
        """Test connection with some servers failing."""
        manager = MCPServerManager(sample_server_configs)
        
        with patch('agentpress.mcp.server_manager.MCPClient') as mock_client_class:
            # First client succeeds, second fails
            mock_client1 = AsyncMock()
            mock_client1.connect = AsyncMock()
            mock_client1.connected = True
            mock_client1.name = "calculator-server"
            
            mock_client2 = AsyncMock()
            mock_client2.connect = AsyncMock(side_effect=Exception("Connection failed"))
            mock_client2.connected = False
            mock_client2.name = "file-server"
            
            mock_client_class.side_effect = [mock_client1, mock_client2]
            
            await manager.connect_to_servers("test-project")
            
            assert len(manager.clients) == 2  # Both clients created
            assert len(manager.connected_clients) == 1  # Only one connected

    @pytest.mark.asyncio
    async def test_disconnect_from_servers(self, sample_server_configs):
        """Test disconnecting from servers."""
        manager = MCPServerManager(sample_server_configs)
        
        # Add mock connected clients
        mock_client1 = AsyncMock()
        mock_client1.disconnect = AsyncMock()
        mock_client1.name = "client1"
        
        mock_client2 = AsyncMock()
        mock_client2.disconnect = AsyncMock()
        mock_client2.name = "client2"
        
        manager.connected_clients = [mock_client1, mock_client2]
        
        await manager.disconnect_from_servers()
        
        mock_client1.disconnect.assert_called_once()
        mock_client2.disconnect.assert_called_once()
        assert len(manager.connected_clients) == 0

    @pytest.mark.asyncio
    async def test_get_available_tools(self, sample_server_configs):
        """Test getting available tools from connected servers."""
        manager = MCPServerManager(sample_server_configs)
        
        # Mock connected clients with tools
        mock_client1 = AsyncMock()
        mock_client1.name = "calculator-server"
        mock_client1.list_tools = AsyncMock(return_value=[
            {"name": "add", "description": "Add numbers"},
            {"name": "multiply", "description": "Multiply numbers"},
            {"name": "divide", "description": "Divide numbers"}  # Not in allowed_tools
        ])
        
        mock_client2 = AsyncMock()
        mock_client2.name = "file-server"
        mock_client2.list_tools = AsyncMock(return_value=[
            {"name": "read_file", "description": "Read file"},
            {"name": "write_file", "description": "Write file"}
        ])
        
        manager.connected_clients = [mock_client1, mock_client2]
        
        tools = await manager.get_available_tools("test-project")
        
        # Should filter tools based on allowed_tools for calculator-server
        assert len(tools) == 4  # 2 from calculator (filtered) + 2 from file (all allowed)
        
        tool_names = [tool["name"] for tool in tools]
        assert "add" in tool_names
        assert "multiply" in tool_names
        assert "divide" not in tool_names  # Filtered out
        assert "read_file" in tool_names
        assert "write_file" in tool_names

    @pytest.mark.asyncio
    async def test_get_available_tools_client_error(self, sample_server_configs):
        """Test getting tools when a client has an error."""
        manager = MCPServerManager(sample_server_configs)
        
        # Mock clients, one with error
        mock_client1 = AsyncMock()
        mock_client1.name = "calculator-server"
        mock_client1.list_tools = AsyncMock(return_value=[
            {"name": "add", "description": "Add numbers"}
        ])
        
        mock_client2 = AsyncMock()
        mock_client2.name = "file-server"
        mock_client2.list_tools = AsyncMock(side_effect=Exception("Server error"))
        
        manager.connected_clients = [mock_client1, mock_client2]
        
        tools = await manager.get_available_tools("test-project")
        
        # Should only return tools from successful client
        assert len(tools) == 1
        assert tools[0]["name"] == "add"

    def test_is_tool_allowed_with_whitelist(self, sample_server_configs):
        """Test tool filtering with allowed_tools whitelist."""
        manager = MCPServerManager(sample_server_configs)
        
        # Find calculator-server config
        calc_config = next(c for c in sample_server_configs if c["name"] == "calculator-server")
        
        assert manager._is_tool_allowed("add", calc_config) is True
        assert manager._is_tool_allowed("multiply", calc_config) is True
        assert manager._is_tool_allowed("divide", calc_config) is False

    def test_is_tool_allowed_no_whitelist(self, sample_server_configs):
        """Test tool filtering with no allowed_tools (all allowed)."""
        manager = MCPServerManager(sample_server_configs)
        
        # Find file-server config (allowed_tools is None)
        file_config = next(c for c in sample_server_configs if c["name"] == "file-server")
        
        assert manager._is_tool_allowed("any_tool", file_config) is True
        assert manager._is_tool_allowed("another_tool", file_config) is True

    @pytest.mark.asyncio
    async def test_call_tool_success(self, sample_server_configs):
        """Test successful tool call through manager."""
        manager = MCPServerManager(sample_server_configs)
        
        # Mock client with the tool
        mock_client = AsyncMock()
        mock_client.name = "calculator-server"
        mock_client.call_tool = AsyncMock(return_value={
            "content": [{"type": "text", "text": "Result: 42"}],
            "isError": False
        })
        
        manager.connected_clients = [mock_client]
        
        # Mock tool lookup
        manager._find_client_for_tool = Mock(return_value=mock_client)
        
        result = await manager.call_tool("add", {"a": 6, "b": 7})
        
        assert result["content"][0]["text"] == "Result: 42"
        mock_client.call_tool.assert_called_once_with("add", {"a": 6, "b": 7})

    @pytest.mark.asyncio
    async def test_call_tool_not_found(self, sample_server_configs):
        """Test tool call when tool is not found."""
        manager = MCPServerManager(sample_server_configs)
        manager.connected_clients = []
        
        with pytest.raises(MCPServerManagerError, match="Tool 'unknown_tool' not found"):
            await manager.call_tool("unknown_tool", {})

    @pytest.mark.asyncio
    async def test_call_tool_client_error(self, sample_server_configs):
        """Test tool call when client returns error."""
        manager = MCPServerManager(sample_server_configs)
        
        mock_client = AsyncMock()
        mock_client.call_tool = AsyncMock(side_effect=Exception("Client error"))
        
        manager._find_client_for_tool = Mock(return_value=mock_client)
        
        with pytest.raises(MCPServerManagerError, match="Error calling tool"):
            await manager.call_tool("test_tool", {})

    def test_find_client_for_tool(self, sample_server_configs):
        """Test finding client that provides a specific tool."""
        manager = MCPServerManager(sample_server_configs)
        
        # Mock clients with different tools
        mock_client1 = Mock()
        mock_client1.name = "calculator-server"
        
        mock_client2 = Mock()
        mock_client2.name = "file-server"
        
        manager.connected_clients = [mock_client1, mock_client2]
        
        # Mock the available tools mapping
        manager._tool_to_client_map = {
            "add": mock_client1,
            "read_file": mock_client2
        }
        
        assert manager._find_client_for_tool("add") == mock_client1
        assert manager._find_client_for_tool("read_file") == mock_client2
        assert manager._find_client_for_tool("unknown_tool") is None

    @pytest.mark.asyncio
    async def test_refresh_tool_mappings(self, sample_server_configs):
        """Test refreshing tool to client mappings."""
        manager = MCPServerManager(sample_server_configs)
        
        # Mock connected clients
        mock_client1 = AsyncMock()
        mock_client1.name = "calculator-server"
        mock_client1.list_tools = AsyncMock(return_value=[
            {"name": "add", "description": "Add numbers"}
        ])
        
        mock_client2 = AsyncMock()
        mock_client2.name = "file-server"
        mock_client2.list_tools = AsyncMock(return_value=[
            {"name": "read_file", "description": "Read file"}
        ])
        
        manager.connected_clients = [mock_client1, mock_client2]
        
        await manager._refresh_tool_mappings("test-project")
        
        assert "add" in manager._tool_to_client_map
        assert "read_file" in manager._tool_to_client_map
        assert manager._tool_to_client_map["add"] == mock_client1
        assert manager._tool_to_client_map["read_file"] == mock_client2

    @pytest.mark.asyncio
    async def test_context_manager(self, sample_server_configs):
        """Test manager as context manager."""
        manager = MCPServerManager(sample_server_configs)
        
        with patch.object(manager, 'connect_to_servers', new_callable=AsyncMock) as mock_connect, \
             patch.object(manager, 'disconnect_from_servers', new_callable=AsyncMock) as mock_disconnect:
            
            async with manager.for_project("test-project") as mgr:
                assert mgr == manager
                mock_connect.assert_called_once_with("test-project")
            
            mock_disconnect.assert_called_once()

    @pytest.mark.asyncio
    async def test_health_check(self, sample_server_configs):
        """Test health check of connected servers."""
        manager = MCPServerManager(sample_server_configs)
        
        # Mock clients with different connection states
        mock_client1 = Mock()
        mock_client1.name = "calculator-server"
        mock_client1.connected = True
        
        mock_client2 = Mock()
        mock_client2.name = "file-server"
        mock_client2.connected = False
        
        manager.connected_clients = [mock_client1]
        manager.clients = [mock_client1, mock_client2]
        
        health_status = await manager.get_health_status()
        
        assert health_status["total_configured"] == 3  # Including disabled server
        assert health_status["enabled"] == 2
        assert health_status["connected"] == 1
        assert health_status["failed"] == 1
        
        assert len(health_status["server_status"]) == 3
        calc_status = next(s for s in health_status["server_status"] if s["name"] == "calculator-server")
        assert calc_status["connected"] is True

    @pytest.mark.asyncio
    async def test_graceful_shutdown(self, sample_server_configs):
        """Test graceful shutdown of manager."""
        manager = MCPServerManager(sample_server_configs)
        
        # Add mock clients
        mock_client1 = AsyncMock()
        mock_client2 = AsyncMock()
        manager.connected_clients = [mock_client1, mock_client2]
        
        await manager.shutdown()
        
        mock_client1.disconnect.assert_called_once()
        mock_client2.disconnect.assert_called_once()
        assert len(manager.connected_clients) == 0
        assert len(manager.clients) == 0

    @pytest.mark.asyncio
    async def test_reconnection_logic(self, sample_server_configs):
        """Test automatic reconnection to failed servers."""
        manager = MCPServerManager(sample_server_configs)
        
        # Mock clients - one fails initially, one succeeds
        mock_client1 = AsyncMock()
        mock_client1.name = "calculator-server"
        mock_client1.connected = False
        
        connect_call_count = 0
        async def mock_connect():
            nonlocal connect_call_count
            connect_call_count += 1
            if connect_call_count == 1:
                raise Exception("Connection failed")
            else:
                mock_client1.connected = True
        
        mock_client1.connect = mock_connect
        
        mock_client2 = AsyncMock()
        mock_client2.name = "file-server"
        mock_client2.connected = True
        mock_client2.connect = AsyncMock()
        
        clients = [mock_client1, mock_client2]
        client_index = 0
        
        def get_client(*args, **kwargs):
            nonlocal client_index
            client = clients[client_index]
            client_index += 1
            return client
        
        with patch('agentpress.mcp.server_manager.MCPClient', side_effect=get_client):
            # First connection attempt - one fails, one succeeds
            await manager.connect_to_servers("test-project")
            assert len(manager.connected_clients) == 1  # Only file-server connected
            
            # Retry connection should succeed for calculator-server
            await manager.retry_failed_connections()
            assert len(manager.connected_clients) == 2  # Both connected now