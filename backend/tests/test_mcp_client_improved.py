"""Improved tests for MCP client with better async handling."""

import pytest
import asyncio
import json
from unittest.mock import Mock, AsyncMock, patch, MagicMock, create_autospec
from agentpress.mcp.client import MCPClient, MCPClientError, MCPConnectionError


class MockStdout:
    """Mock stdout that simulates real subprocess behavior."""
    
    def __init__(self):
        self.lines = []
        self.read_index = 0
        self.closed = False
        
    async def readline(self):
        """Simulate readline with proper async behavior."""
        if self.closed:
            return b''
            
        # Simulate some delay like real I/O
        await asyncio.sleep(0.001)
        
        if self.read_index < len(self.lines):
            line = self.lines[self.read_index]
            self.read_index += 1
            return line
        
        # If no more lines, wait a bit then return empty (EOF)
        await asyncio.sleep(0.01)
        return b''
    
    def add_response(self, response: dict):
        """Add a response to be read."""
        self.lines.append(json.dumps(response).encode() + b'\n')
    
    def close(self):
        """Mark as closed."""
        self.closed = True


class MockStdin:
    """Mock stdin that captures written data."""
    
    def __init__(self):
        self.written_data = []
        
    def write(self, data: bytes):
        """Capture written data."""
        self.written_data.append(data)
        
    async def drain(self):
        """Simulate drain."""
        await asyncio.sleep(0.001)
    
    def get_written_messages(self):
        """Get all written messages as parsed JSON."""
        messages = []
        for data in self.written_data:
            try:
                msg = json.loads(data.decode().strip())
                messages.append(msg)
            except:
                pass
        return messages


class TestMCPClientImproved:
    """Improved test cases for MCPClient with better async handling."""

    @pytest.fixture
    def mock_process(self):
        """Create a more realistic mock process."""
        process = Mock()
        process.stdin = MockStdin()
        process.stdout = MockStdout()
        process.stderr = AsyncMock()
        process.returncode = None
        process.terminate = Mock()
        process.kill = Mock()
        process.wait = AsyncMock()
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

    @pytest.mark.asyncio
    async def test_connect_and_handshake(self, stdio_config, mock_process):
        """Test complete connection and handshake flow."""
        client = MCPClient(stdio_config)
        
        # Prepare handshake responses
        mock_process.stdout.add_response({
            "jsonrpc": "2.0",
            "id": 1,
            "result": {
                "protocolVersion": "2024-11-05",
                "serverInfo": {"name": "test-server", "version": "1.0.0"},
                "capabilities": {"tools": {}}
            }
        })
        
        with patch('asyncio.create_subprocess_exec', return_value=mock_process):
            await client.connect()
            
            # Allow time for async operations
            await asyncio.sleep(0.01)
            
            assert client.connected
            assert client.server_capabilities == {"tools": {}}
            
            # Check handshake messages were sent
            written = mock_process.stdin.get_written_messages()
            assert len(written) >= 1
            
            # Verify initialize request
            init_request = written[0]
            assert init_request["method"] == "initialize"
            assert init_request["params"]["protocolVersion"] == "2024-11-05"
            
            # Clean disconnect
            await client.disconnect()
            assert not client.connected

    @pytest.mark.asyncio
    async def test_send_request_with_response(self, stdio_config, mock_process):
        """Test sending a request and receiving response."""
        client = MCPClient(stdio_config)
        client.connected = True
        client.process = mock_process
        
        # Prepare response
        mock_process.stdout.add_response({
            "jsonrpc": "2.0",
            "id": 1,
            "result": {"status": "ok", "data": "test"}
        })
        
        # Start response handler
        client._response_task = asyncio.create_task(client._handle_stdio_responses())
        
        try:
            # Send request
            result = await asyncio.wait_for(
                client.send_request("test/method", {"param": "value"}),
                timeout=1.0
            )
            
            assert result == {"status": "ok", "data": "test"}
            
            # Verify request was sent
            written = mock_process.stdin.get_written_messages()
            assert len(written) == 1
            assert written[0]["method"] == "test/method"
            assert written[0]["params"] == {"param": "value"}
            
        finally:
            # Clean up
            client.connected = False
            client._response_task.cancel()
            try:
                await client._response_task
            except asyncio.CancelledError:
                pass

    @pytest.mark.asyncio
    async def test_handle_json_rpc_error(self, stdio_config, mock_process):
        """Test handling JSON-RPC error responses."""
        client = MCPClient(stdio_config)
        client.connected = True
        client.process = mock_process
        
        # Prepare error response
        mock_process.stdout.add_response({
            "jsonrpc": "2.0",
            "id": 1,
            "error": {"code": -32601, "message": "Method not found"}
        })
        
        # Start response handler
        client._response_task = asyncio.create_task(client._handle_stdio_responses())
        
        try:
            with pytest.raises(MCPClientError, match="Method not found"):
                await asyncio.wait_for(
                    client.send_request("invalid/method", {}),
                    timeout=1.0
                )
        finally:
            # Clean up
            client.connected = False
            client._response_task.cancel()
            try:
                await client._response_task
            except asyncio.CancelledError:
                pass

    @pytest.mark.asyncio
    async def test_concurrent_requests(self, stdio_config, mock_process):
        """Test handling multiple concurrent requests."""
        client = MCPClient(stdio_config)
        client.connected = True
        client.process = mock_process
        
        # Prepare multiple responses
        mock_process.stdout.add_response({
            "jsonrpc": "2.0",
            "id": 1,
            "result": {"result": "first"}
        })
        mock_process.stdout.add_response({
            "jsonrpc": "2.0",
            "id": 2,
            "result": {"result": "second"}
        })
        
        # Start response handler
        client._response_task = asyncio.create_task(client._handle_stdio_responses())
        
        try:
            # Send concurrent requests
            task1 = asyncio.create_task(client.send_request("test/method1", {}))
            task2 = asyncio.create_task(client.send_request("test/method2", {}))
            
            results = await asyncio.gather(task1, task2)
            
            assert results[0] == {"result": "first"}
            assert results[1] == {"result": "second"}
            
        finally:
            # Clean up
            client.connected = False
            client._response_task.cancel()
            try:
                await client._response_task
            except asyncio.CancelledError:
                pass

    @pytest.mark.asyncio
    async def test_notification_handling(self, stdio_config, mock_process):
        """Test handling notifications from server."""
        client = MCPClient(stdio_config)
        client.connected = True
        client.process = mock_process
        
        # Track notifications
        notifications = []
        original_handle = client._handle_notification
        
        async def track_notification(method, params):
            notifications.append((method, params))
            await original_handle(method, params)
        
        client._handle_notification = track_notification
        
        # Add notification
        mock_process.stdout.add_response({
            "jsonrpc": "2.0",
            "method": "notifications/tools/list_changed"
        })
        
        # Start response handler
        client._response_task = asyncio.create_task(client._handle_stdio_responses())
        
        try:
            # Wait for notification to be processed
            await asyncio.sleep(0.1)
            
            assert len(notifications) == 1
            assert notifications[0][0] == "notifications/tools/list_changed"
            
        finally:
            # Clean up
            client.connected = False
            client._response_task.cancel()
            try:
                await client._response_task
            except asyncio.CancelledError:
                pass

    @pytest.mark.asyncio
    async def test_graceful_disconnect_with_pending_requests(self, stdio_config, mock_process):
        """Test disconnecting while requests are pending."""
        client = MCPClient(stdio_config)
        client.connected = True
        client.process = mock_process
        
        # Start response handler
        client._response_task = asyncio.create_task(client._handle_stdio_responses())
        
        # Send request but don't add response (simulating pending request)
        request_task = asyncio.create_task(client.send_request("test/method", {}))
        
        # Wait a bit
        await asyncio.sleep(0.05)
        
        # Disconnect while request is pending
        await client.disconnect()
        
        # Wait for the task to actually finish (either cancelled or with exception)
        try:
            await request_task
        except (asyncio.CancelledError, MCPClientError):
            # Expected - request was cancelled or errored
            pass
        
        # Now check the state
        assert request_task.done()
        assert not client.connected
        assert len(client._pending_requests) == 0