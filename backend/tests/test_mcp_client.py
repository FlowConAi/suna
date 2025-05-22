"""Tests for MCP client implementation."""

import pytest
import asyncio
import json
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from agentpress.mcp.client import MCPClient, MCPClientError, MCPConnectionError


class TestMCPClient:
    """Test cases for MCPClient."""

    @pytest.fixture
    def mock_process(self):
        """Mock subprocess for STDIO transport."""
        process = AsyncMock()
        process.stdin = AsyncMock()
        process.stdout = AsyncMock()
        process.stderr = AsyncMock()
        process.returncode = None
        return process

    @pytest.fixture
    def stdio_config(self):
        """STDIO transport configuration."""
        return {
            "transport": "stdio",
            "command": "python",
            "args": ["-m", "test_server"],
            "name": "test-server"
        }

    @pytest.fixture
    def http_config(self):
        """HTTP transport configuration."""
        return {
            "transport": "http",
            "url": "http://localhost:8080/mcp",
            "name": "test-server"
        }

    @pytest.mark.asyncio
    async def test_init_stdio_client(self, stdio_config):
        """Test initialization of STDIO MCP client."""
        client = MCPClient(stdio_config)
        
        assert client.name == "test-server"
        assert client.transport_type == "stdio"
        assert client.command == "python"
        assert client.args == ["-m", "test_server"]
        assert not client.connected

    @pytest.mark.asyncio
    async def test_init_http_client(self, http_config):
        """Test initialization of HTTP MCP client."""
        client = MCPClient(http_config)
        
        assert client.name == "test-server"
        assert client.transport_type == "http"
        assert client.url == "http://localhost:8080/mcp"
        assert not client.connected

    @pytest.mark.asyncio
    async def test_invalid_transport_raises_error(self):
        """Test that invalid transport raises error."""
        config = {
            "transport": "invalid",
            "name": "test-server"
        }
        
        with pytest.raises(MCPClientError, match="Unsupported transport"):
            MCPClient(config)

    @pytest.mark.asyncio
    async def test_connect_stdio_success(self, stdio_config, mock_process):
        """Test successful STDIO connection."""
        client = MCPClient(stdio_config)
        
        with patch('asyncio.create_subprocess_exec', return_value=mock_process):
            # Mock successful initialization handshake
            mock_process.stdout.readline.side_effect = [
                b'{"jsonrpc": "2.0", "id": 1, "result": {"protocolVersion": "2024-11-05", "capabilities": {"tools": {}}}}\n',
                b'{"jsonrpc": "2.0", "method": "notifications/initialized"}\n'
            ]
            
            await client.connect()
            
            assert client.connected
            assert client.process == mock_process

    @pytest.mark.asyncio
    async def test_connect_stdio_initialization_failure(self, stdio_config, mock_process):
        """Test STDIO connection initialization failure."""
        client = MCPClient(stdio_config)
        
        with patch('asyncio.create_subprocess_exec', return_value=mock_process):
            # Mock failed initialization
            mock_process.stdout.readline.side_effect = [
                b'{"jsonrpc": "2.0", "id": 1, "error": {"code": -1, "message": "Server error"}}\n'
            ]
            
            with pytest.raises(MCPConnectionError, match="Initialization failed"):
                await client.connect()
            
            assert not client.connected

    @pytest.mark.asyncio
    async def test_connect_stdio_process_failure(self, stdio_config):
        """Test STDIO connection process creation failure."""
        client = MCPClient(stdio_config)
        
        with patch('asyncio.create_subprocess_exec', side_effect=FileNotFoundError("Command not found")):
            with pytest.raises(MCPConnectionError, match="Failed to start MCP server process"):
                await client.connect()
            
            assert not client.connected

    @pytest.mark.asyncio
    async def test_disconnect_stdio(self, stdio_config, mock_process):
        """Test STDIO disconnection."""
        client = MCPClient(stdio_config)
        client.process = mock_process
        client.connected = True
        
        await client.disconnect()
        
        mock_process.terminate.assert_called_once()
        assert not client.connected
        assert client.process is None

    @pytest.mark.asyncio
    async def test_list_tools_success(self, stdio_config, sample_mcp_tool):
        """Test successful tool listing."""
        client = MCPClient(stdio_config)
        client.connected = True
        
        # Mock the send_request method
        client.send_request = AsyncMock(return_value={
            "tools": [sample_mcp_tool]
        })
        
        tools = await client.list_tools()
        
        assert len(tools) == 1
        assert tools[0]["name"] == "test_calculator"
        client.send_request.assert_called_once_with("tools/list", {})

    @pytest.mark.asyncio
    async def test_list_tools_not_connected(self, stdio_config):
        """Test tool listing when not connected."""
        client = MCPClient(stdio_config)
        
        with pytest.raises(MCPClientError, match="Client not connected"):
            await client.list_tools()

    @pytest.mark.asyncio
    async def test_call_tool_success(self, stdio_config):
        """Test successful tool call."""
        client = MCPClient(stdio_config)
        client.connected = True
        
        # Mock the send_request method
        expected_result = {
            "content": [{"type": "text", "text": "42"}],
            "isError": False
        }
        client.send_request = AsyncMock(return_value=expected_result)
        
        result = await client.call_tool("test_calculator", {"expression": "6*7"})
        
        assert result == expected_result
        client.send_request.assert_called_once_with("tools/call", {
            "name": "test_calculator",
            "arguments": {"expression": "6*7"}
        })

    @pytest.mark.asyncio
    async def test_call_tool_with_error(self, stdio_config):
        """Test tool call that returns error."""
        client = MCPClient(stdio_config)
        client.connected = True
        
        # Mock error response
        error_result = {
            "content": [{"type": "text", "text": "Division by zero"}],
            "isError": True
        }
        client.send_request = AsyncMock(return_value=error_result)
        
        result = await client.call_tool("test_calculator", {"expression": "1/0"})
        
        assert result["isError"] is True
        assert "Division by zero" in result["content"][0]["text"]

    @pytest.mark.asyncio
    async def test_call_tool_not_connected(self, stdio_config):
        """Test tool call when not connected."""
        client = MCPClient(stdio_config)
        
        with pytest.raises(MCPClientError, match="Client not connected"):
            await client.call_tool("test_tool", {})

    @pytest.mark.asyncio
    async def test_send_request_stdio(self, stdio_config, mock_process):
        """Test sending request via STDIO."""
        client = MCPClient(stdio_config)
        client.process = mock_process
        client.connected = True
        client._request_id = 0
        
        # Mock response
        response = {"jsonrpc": "2.0", "id": 1, "result": {"status": "ok"}}
        mock_process.stdout.readline.return_value = json.dumps(response).encode() + b'\n'
        
        result = await client.send_request("test/method", {"param": "value"})
        
        assert result == {"status": "ok"}
        
        # Verify request was sent
        expected_request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "test/method",
            "params": {"param": "value"}
        }
        mock_process.stdin.write.assert_called_once()
        written_data = mock_process.stdin.write.call_args[0][0]
        assert json.loads(written_data.decode().strip()) == expected_request

    @pytest.mark.asyncio
    async def test_send_request_json_rpc_error(self, stdio_config, mock_process):
        """Test handling JSON-RPC error response."""
        client = MCPClient(stdio_config)
        client.process = mock_process
        client.connected = True
        client._request_id = 0
        
        # Mock error response
        error_response = {
            "jsonrpc": "2.0",
            "id": 1,
            "error": {"code": -32601, "message": "Method not found"}
        }
        mock_process.stdout.readline.return_value = json.dumps(error_response).encode() + b'\n'
        
        with pytest.raises(MCPClientError, match="Method not found"):
            await client.send_request("invalid/method", {})

    @pytest.mark.asyncio
    async def test_send_request_timeout(self, stdio_config, mock_process):
        """Test request timeout handling."""
        client = MCPClient(stdio_config)
        client.process = mock_process
        client.connected = True
        client._request_id = 0
        
        # Mock timeout
        mock_process.stdout.readline.side_effect = asyncio.TimeoutError()
        
        with pytest.raises(MCPClientError, match="Request timeout"):
            await client.send_request("test/method", {}, timeout=0.1)

    @pytest.mark.asyncio
    async def test_context_manager(self, stdio_config, mock_process):
        """Test client as context manager."""
        with patch('asyncio.create_subprocess_exec', return_value=mock_process):
            # Mock successful initialization
            mock_process.stdout.readline.side_effect = [
                b'{"jsonrpc": "2.0", "id": 1, "result": {"protocolVersion": "2024-11-05", "capabilities": {"tools": {}}}}\n',
                b'{"jsonrpc": "2.0", "method": "notifications/initialized"}\n'
            ]
            
            async with MCPClient(stdio_config) as client:
                assert client.connected
            
            # Should be disconnected after context
            mock_process.terminate.assert_called_once()

    @pytest.mark.asyncio
    async def test_server_capabilities_parsing(self, stdio_config, mock_process):
        """Test parsing server capabilities during initialization."""
        client = MCPClient(stdio_config)
        
        with patch('asyncio.create_subprocess_exec', return_value=mock_process):
            # Mock initialization with capabilities
            capabilities = {
                "tools": {"listChanged": True},
                "resources": {"subscribe": True, "listChanged": True},
                "prompts": {"listChanged": True}
            }
            init_response = {
                "jsonrpc": "2.0",
                "id": 1,
                "result": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": capabilities
                }
            }
            mock_process.stdout.readline.side_effect = [
                json.dumps(init_response).encode() + b'\n',
                b'{"jsonrpc": "2.0", "method": "notifications/initialized"}\n'
            ]
            
            await client.connect()
            
            assert client.server_capabilities == capabilities
            assert client.connected

    @pytest.mark.asyncio
    async def test_concurrent_requests(self, stdio_config, mock_process):
        """Test handling concurrent requests."""
        client = MCPClient(stdio_config)
        client.process = mock_process
        client.connected = True
        client._request_id = 0
        
        # Mock responses for concurrent requests
        responses = [
            {"jsonrpc": "2.0", "id": 1, "result": {"result": "first"}},
            {"jsonrpc": "2.0", "id": 2, "result": {"result": "second"}},
        ]
        
        async def mock_readline():
            if responses:
                response = responses.pop(0)
                return json.dumps(response).encode() + b'\n'
            await asyncio.sleep(0.1)  # Simulate delay
            return b''
        
        mock_process.stdout.readline.side_effect = mock_readline
        
        # Send concurrent requests
        task1 = asyncio.create_task(client.send_request("test/method1", {}))
        task2 = asyncio.create_task(client.send_request("test/method2", {}))
        
        result1, result2 = await asyncio.gather(task1, task2)
        
        assert result1["result"] == "first"
        assert result2["result"] == "second"