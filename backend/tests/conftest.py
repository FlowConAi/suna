"""Test configuration for Suna backend tests."""

import pytest
import asyncio
import os
from typing import Generator
from unittest.mock import Mock, MagicMock, AsyncMock
import tempfile
import json

# Configure pytest for async tests
pytest_plugins = ('pytest_asyncio',)


@pytest.fixture
def mock_redis():
    """Mock Redis client for testing."""
    redis_mock = MagicMock()
    redis_mock.get.return_value = None
    redis_mock.set.return_value = True
    redis_mock.publish.return_value = 1
    redis_mock.rpush.return_value = 1
    redis_mock.lrange.return_value = []
    return redis_mock


@pytest.fixture
def mock_supabase():
    """Mock Supabase client for testing."""
    supabase_mock = MagicMock()
    supabase_mock.table.return_value.select.return_value.execute.return_value.data = []
    return supabase_mock


@pytest.fixture
def test_env():
    """Set up test environment variables."""
    original_env = os.environ.copy()
    os.environ.update({
        'TESTING': 'true',
        'REDIS_HOST': 'localhost',
        'MODEL_TO_USE': 'test-model',
        'ENV_MODE': 'test',
    })
    yield
    os.environ.clear()
    os.environ.update(original_env)


@pytest.fixture
def temp_dir():
    """Create a temporary directory for test files."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        yield tmp_dir


@pytest.fixture
def mock_mcp_client():
    """Mock MCP client for testing."""
    client_mock = AsyncMock()
    client_mock.connect = AsyncMock()
    client_mock.disconnect = AsyncMock()
    client_mock.list_tools = AsyncMock(return_value=[])
    client_mock.call_tool = AsyncMock()
    return client_mock


@pytest.fixture
def sample_mcp_tool():
    """Sample MCP tool definition for testing."""
    return {
        "name": "test_calculator",
        "description": "A simple calculator tool",
        "inputSchema": {
            "type": "object",
            "properties": {
                "expression": {
                    "type": "string",
                    "description": "Mathematical expression to evaluate"
                }
            },
            "required": ["expression"]
        }
    }


@pytest.fixture
def sample_mcp_server_config():
    """Sample MCP server configuration for testing."""
    return {
        "name": "test-server",
        "transport": "stdio",
        "command": "python",
        "args": ["-m", "test_mcp_server"],
        "enabled": True,
        "allowed_tools": ["test_calculator", "test_formatter"],
        "project_scope": "global"  # "global", "project", or specific project IDs
    }


@pytest.fixture
def mock_thread_manager():
    """Mock ThreadManager for testing."""
    from agentpress.tool_registry import ToolRegistry
    
    thread_manager = Mock()
    thread_manager.tool_registry = ToolRegistry()
    thread_manager.add_message = AsyncMock()
    thread_manager.project_id = "test-project-123"
    thread_manager.thread_id = "test-thread-456"
    return thread_manager