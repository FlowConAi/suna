"""Tests for MCP tool wrapper implementation."""

import pytest
import json
from unittest.mock import Mock, AsyncMock, patch
from agentpress.tool import ToolResult
from agentpress.mcp.tool_wrapper import MCPToolWrapper, MCPToolWrapperError


class TestMCPToolWrapper:
    """Test cases for MCPToolWrapper."""

    @pytest.fixture
    def mock_mcp_client(self):
        """Mock MCP client."""
        client = AsyncMock()
        client.name = "test-server"
        client.connected = True
        return client

    @pytest.fixture
    def sample_mcp_tool_def(self):
        """Sample MCP tool definition."""
        return {
            "name": "calculate",
            "description": "Perform mathematical calculations",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "expression": {
                        "type": "string",
                        "description": "Mathematical expression to evaluate"
                    },
                    "precision": {
                        "type": "integer",
                        "description": "Number of decimal places",
                        "default": 2
                    }
                },
                "required": ["expression"]
            }
        }

    @pytest.fixture
    def complex_mcp_tool_def(self):
        """Complex MCP tool definition with nested schema."""
        return {
            "name": "data_processor",
            "description": "Process data with various options",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "data": {
                        "type": "array",
                        "items": {"type": "number"},
                        "description": "Array of numbers to process"
                    },
                    "options": {
                        "type": "object",
                        "properties": {
                            "operation": {
                                "type": "string",
                                "enum": ["sum", "mean", "median"],
                                "description": "Operation to perform"
                            },
                            "round_result": {
                                "type": "boolean",
                                "default": True
                            }
                        },
                        "required": ["operation"]
                    }
                },
                "required": ["data", "options"]
            }
        }

    def test_wrapper_initialization(self, mock_mcp_client, sample_mcp_tool_def):
        """Test MCPToolWrapper initialization."""
        wrapper = MCPToolWrapper(mock_mcp_client, sample_mcp_tool_def)
        
        assert wrapper.mcp_client == mock_mcp_client
        assert wrapper.tool_definition == sample_mcp_tool_def
        assert wrapper.tool_name == "calculate"
        assert wrapper.server_name == "test-server"

    def test_wrapper_initialization_missing_name(self, mock_mcp_client):
        """Test wrapper initialization with missing tool name."""
        invalid_tool_def = {
            "description": "A tool without a name",
            "inputSchema": {"type": "object"}
        }
        
        with pytest.raises(MCPToolWrapperError, match="Tool definition must include 'name'"):
            MCPToolWrapper(mock_mcp_client, invalid_tool_def)

    def test_wrapper_initialization_missing_schema(self, mock_mcp_client):
        """Test wrapper initialization with missing input schema."""
        invalid_tool_def = {
            "name": "test_tool",
            "description": "A tool without schema"
        }
        
        with pytest.raises(MCPToolWrapperError, match="Tool definition must include 'inputSchema'"):
            MCPToolWrapper(mock_mcp_client, invalid_tool_def)

    def test_get_openapi_schema(self, mock_mcp_client, sample_mcp_tool_def):
        """Test OpenAPI schema generation."""
        wrapper = MCPToolWrapper(mock_mcp_client, sample_mcp_tool_def)
        schema = wrapper.get_openapi_schema()
        
        expected_schema = {
            "type": "function",
            "function": {
                "name": "mcp_test_server_calculate",
                "description": "Perform mathematical calculations (via MCP server: test-server)",
                "parameters": sample_mcp_tool_def["inputSchema"]
            }
        }
        
        assert schema == expected_schema

    def test_get_xml_schema(self, mock_mcp_client, sample_mcp_tool_def):
        """Test XML schema generation."""
        wrapper = MCPToolWrapper(mock_mcp_client, sample_mcp_tool_def)
        schema = wrapper.get_xml_schema()
        
        assert schema.tag_name == "mcp-test-server-calculate"
        # XMLTagSchema doesn't have description attribute
        
        # Check parameter mappings
        param_names = [mapping.param_name for mapping in schema.mappings]
        assert "expression" in param_names
        assert "precision" in param_names

    def test_get_xml_schema_complex(self, mock_mcp_client, complex_mcp_tool_def):
        """Test XML schema generation for complex nested schema."""
        wrapper = MCPToolWrapper(mock_mcp_client, complex_mcp_tool_def)
        schema = wrapper.get_xml_schema()
        
        assert schema.tag_name == "mcp-test-server-data_processor"
        
        # Check that nested objects are flattened
        param_names = [mapping.param_name for mapping in schema.mappings]
        assert "data" in param_names
        assert "options_operation" in param_names
        assert "options_round_result" in param_names

    @pytest.mark.asyncio
    async def test_call_tool_success(self, mock_mcp_client, sample_mcp_tool_def):
        """Test successful tool call."""
        wrapper = MCPToolWrapper(mock_mcp_client, sample_mcp_tool_def)
        
        # Mock successful MCP response
        mock_mcp_client.call_tool.return_value = {
            "content": [{"type": "text", "text": "Result: 42"}],
            "isError": False
        }
        
        result = await wrapper.call_tool(expression="6*7", precision=0)
        
        assert isinstance(result, ToolResult)
        assert result.success is True
        assert "Result: 42" in result.output
        
        # Verify MCP client was called correctly
        mock_mcp_client.call_tool.assert_called_once_with(
            "calculate",
            {"expression": "6*7", "precision": 0}
        )

    @pytest.mark.asyncio
    async def test_call_tool_mcp_error(self, mock_mcp_client, sample_mcp_tool_def):
        """Test tool call with MCP error response."""
        wrapper = MCPToolWrapper(mock_mcp_client, sample_mcp_tool_def)
        
        # Mock MCP error response
        mock_mcp_client.call_tool.return_value = {
            "content": [{"type": "text", "text": "Invalid expression"}],
            "isError": True
        }
        
        result = await wrapper.call_tool(expression="invalid")
        
        assert isinstance(result, ToolResult)
        assert result.success is False
        assert "Invalid expression" in result.output

    @pytest.mark.asyncio
    async def test_call_tool_client_disconnected(self, mock_mcp_client, sample_mcp_tool_def):
        """Test tool call when MCP client is disconnected."""
        wrapper = MCPToolWrapper(mock_mcp_client, sample_mcp_tool_def)
        mock_mcp_client.connected = False
        
        result = await wrapper.call_tool(expression="6*7")
        
        assert isinstance(result, ToolResult)
        assert result.success is False
        assert "MCP server test-server is not connected" in result.output

    @pytest.mark.asyncio
    async def test_call_tool_client_exception(self, mock_mcp_client, sample_mcp_tool_def):
        """Test tool call with client exception."""
        wrapper = MCPToolWrapper(mock_mcp_client, sample_mcp_tool_def)
        
        # Mock client exception
        mock_mcp_client.call_tool.side_effect = Exception("Connection lost")
        
        result = await wrapper.call_tool(expression="6*7")
        
        assert isinstance(result, ToolResult)
        assert result.success is False
        assert "Error calling MCP tool" in result.output
        assert "Connection lost" in result.output

    @pytest.mark.asyncio
    async def test_call_tool_argument_validation(self, mock_mcp_client, sample_mcp_tool_def):
        """Test tool call with missing required arguments."""
        wrapper = MCPToolWrapper(mock_mcp_client, sample_mcp_tool_def)
        
        # Call without required 'expression' argument
        result = await wrapper.call_tool(precision=2)
        
        assert isinstance(result, ToolResult)
        assert result.success is False
        assert "Missing required argument" in result.output
        assert "expression" in result.output

    @pytest.mark.asyncio
    async def test_call_tool_with_defaults(self, mock_mcp_client, sample_mcp_tool_def):
        """Test tool call uses default values for optional parameters."""
        wrapper = MCPToolWrapper(mock_mcp_client, sample_mcp_tool_def)
        
        mock_mcp_client.call_tool.return_value = {
            "content": [{"type": "text", "text": "42.00"}],
            "isError": False
        }
        
        result = await wrapper.call_tool(expression="6*7")
        
        # Should use default precision=2
        mock_mcp_client.call_tool.assert_called_once_with(
            "calculate",
            {"expression": "6*7", "precision": 2}
        )

    def test_format_mcp_response_text_content(self, mock_mcp_client, sample_mcp_tool_def):
        """Test formatting MCP response with text content."""
        wrapper = MCPToolWrapper(mock_mcp_client, sample_mcp_tool_def)
        
        mcp_response = {
            "content": [
                {"type": "text", "text": "First line"},
                {"type": "text", "text": "Second line"}
            ]
        }
        
        formatted = wrapper._format_mcp_response(mcp_response)
        assert formatted == "First line\nSecond line"

    def test_format_mcp_response_mixed_content(self, mock_mcp_client, sample_mcp_tool_def):
        """Test formatting MCP response with mixed content types."""
        wrapper = MCPToolWrapper(mock_mcp_client, sample_mcp_tool_def)
        
        mcp_response = {
            "content": [
                {"type": "text", "text": "Text content"},
                {"type": "image", "data": "base64data", "mimeType": "image/png"},
                {"type": "resource", "resource": {"uri": "file:///path/to/file"}}
            ]
        }
        
        formatted = wrapper._format_mcp_response(mcp_response)
        assert "Text content" in formatted
        assert "Image (image/png)" in formatted
        assert "Resource: file:///path/to/file" in formatted

    def test_format_mcp_response_empty_content(self, mock_mcp_client, sample_mcp_tool_def):
        """Test formatting MCP response with empty content."""
        wrapper = MCPToolWrapper(mock_mcp_client, sample_mcp_tool_def)
        
        mcp_response = {"content": []}
        
        formatted = wrapper._format_mcp_response(mcp_response)
        assert formatted == "(No output)"

    def test_validate_arguments_success(self, mock_mcp_client, sample_mcp_tool_def):
        """Test successful argument validation."""
        wrapper = MCPToolWrapper(mock_mcp_client, sample_mcp_tool_def)
        
        # Valid arguments
        is_valid, error = wrapper._validate_arguments({"expression": "6*7", "precision": 2})
        assert is_valid is True
        assert error is None

    def test_validate_arguments_missing_required(self, mock_mcp_client, sample_mcp_tool_def):
        """Test argument validation with missing required field."""
        wrapper = MCPToolWrapper(mock_mcp_client, sample_mcp_tool_def)
        
        # Missing required 'expression'
        is_valid, error = wrapper._validate_arguments({"precision": 2})
        assert is_valid is False
        assert "Missing required argument: expression" in error

    def test_validate_arguments_wrong_type(self, mock_mcp_client, sample_mcp_tool_def):
        """Test argument validation with wrong type."""
        wrapper = MCPToolWrapper(mock_mcp_client, sample_mcp_tool_def)
        
        # Wrong type for precision (should be integer)
        is_valid, error = wrapper._validate_arguments({"expression": "6*7", "precision": "two"})
        assert is_valid is False
        assert "Invalid type for argument precision" in error

    def test_apply_defaults(self, mock_mcp_client, sample_mcp_tool_def):
        """Test applying default values to arguments."""
        wrapper = MCPToolWrapper(mock_mcp_client, sample_mcp_tool_def)
        
        args = {"expression": "6*7"}
        wrapper._apply_defaults(args)
        
        assert args["precision"] == 2  # Default value applied

    def test_flatten_nested_schema(self, mock_mcp_client, complex_mcp_tool_def):
        """Test flattening nested JSON schema for XML format."""
        wrapper = MCPToolWrapper(mock_mcp_client, complex_mcp_tool_def)
        
        flattened = wrapper._flatten_schema_for_xml(complex_mcp_tool_def["inputSchema"])
        
        expected_params = {
            "data": {"type": "array", "description": "Array of numbers to process"},
            "options_operation": {"type": "string", "description": "Operation to perform"},
            "options_round_result": {"type": "boolean", "description": "Default: True"}
        }
        
        for param_name, param_def in expected_params.items():
            assert param_name in flattened
            assert flattened[param_name]["type"] == param_def["type"]

    def test_schema_name_generation(self, mock_mcp_client):
        """Test schema name generation for different tool names."""
        test_cases = [
            ("simple_tool", "mcp-test-server-simple_tool"),
            ("tool.with.dots", "mcp-test-server-tool_with_dots"),
            ("UPPERCASE_TOOL", "mcp-test-server-uppercase_tool"),
            ("tool_with_123_numbers", "mcp-test-server-tool_with_123_numbers")
        ]
        
        for tool_name, expected_schema_name in test_cases:
            tool_def = {
                "name": tool_name,
                "description": "Test tool",
                "inputSchema": {"type": "object", "properties": {}}
            }
            wrapper = MCPToolWrapper(mock_mcp_client, tool_def)
            schema = wrapper.get_xml_schema()
            assert schema.tag_name == expected_schema_name

    def test_get_suna_tool_class(self, mock_mcp_client, sample_mcp_tool_def):
        """Test generating Suna Tool class from MCP tool."""
        wrapper = MCPToolWrapper(mock_mcp_client, sample_mcp_tool_def)
        
        tool_class = wrapper.get_suna_tool_class()
        
        # Verify the class has the right methods
        assert hasattr(tool_class, 'mcp_test_server_calculate')
        
        # Verify the class has schemas registered
        tool_instance = tool_class(project_id="test-project", thread_manager=None)
        # Get schemas from the instance method
        schemas = tool_instance.get_schemas()
        assert 'mcp_test_server_calculate' in schemas
        assert len(schemas['mcp_test_server_calculate']) == 2  # XML and OpenAPI

    @pytest.mark.asyncio
    async def test_generated_tool_execution(self, mock_mcp_client, sample_mcp_tool_def):
        """Test execution of generated Suna tool."""
        wrapper = MCPToolWrapper(mock_mcp_client, sample_mcp_tool_def)
        
        # Mock successful MCP response
        mock_mcp_client.call_tool.return_value = {
            "content": [{"type": "text", "text": "Result: 42"}],
            "isError": False
        }
        
        tool_class = wrapper.get_suna_tool_class()
        tool_instance = tool_class(project_id="test-project", thread_manager=None)
        
        # Call the generated method
        result = await tool_instance.mcp_test_server_calculate(expression="6*7")
        
        assert isinstance(result, ToolResult)
        assert result.success is True
        assert "Result: 42" in result.output