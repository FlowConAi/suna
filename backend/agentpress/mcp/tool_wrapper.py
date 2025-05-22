"""MCP tool wrapper for integrating MCP tools with Suna's tool system."""

import re
import logging
from typing import Dict, Any, List, Optional, Type, Union
from agentpress.tool import Tool, ToolResult, ToolSchema, XMLTagSchema, SchemaType, openapi_schema, xml_schema


logger = logging.getLogger(__name__)


class MCPToolWrapperError(Exception):
    """Exception for MCP tool wrapper errors."""
    pass


class MCPToolWrapper:
    """Wraps an MCP tool to integrate with Suna's tool system."""
    
    def __init__(self, mcp_client, tool_definition: Dict[str, Any]):
        """Initialize MCP tool wrapper.
        
        Args:
            mcp_client: Connected MCP client instance
            tool_definition: MCP tool definition from tools/list
        """
        self.mcp_client = mcp_client
        self.tool_definition = tool_definition
        
        if "name" not in tool_definition:
            raise MCPToolWrapperError("Tool definition must include 'name'")
        if "inputSchema" not in tool_definition:
            raise MCPToolWrapperError("Tool definition must include 'inputSchema'")
            
        self.tool_name = tool_definition["name"]
        self.server_name = mcp_client.name
        self.description = tool_definition.get("description", f"MCP tool: {self.tool_name}")
        self.input_schema = tool_definition["inputSchema"]
    
    def get_openapi_schema(self) -> Dict[str, Any]:
        """Generate OpenAPI schema for this MCP tool."""
        function_name = f"mcp_{self._normalize_name(self.server_name)}_{self._normalize_name(self.tool_name)}"
        
        return {
            "type": "function",
            "function": {
                "name": function_name,
                "description": f"{self.description} (via MCP server: {self.server_name})",
                "parameters": self.input_schema
            }
        }
    
    def get_xml_schema(self) -> XMLTagSchema:
        """Generate XML schema for this MCP tool."""
        tag_name = f"mcp-{self._normalize_name(self.server_name)}-{self._normalize_name(self.tool_name)}"
        
        # Flatten nested schema for XML format
        flattened_params = self._flatten_schema_for_xml(self.input_schema)
        
        mappings = []
        for param_name, param_def in flattened_params.items():
            # Use attributes for simple types, content for complex
            node_type = "attribute" if param_def.get("type") in ["string", "number", "integer", "boolean"] else "content"
            
            mappings.append({
                "param_name": param_name,
                "node_type": node_type,
                "path": "."
            })
        
        example = f"<{tag_name}>{self._generate_xml_example(flattened_params)}</{tag_name}>"
        
        return XMLTagSchema(
            tag_name=tag_name,
            description=f"{self.description} (via MCP server: {self.server_name})",
            mappings=mappings,
            example=example
        )
    
    def get_suna_tool_class(self) -> Type[Tool]:
        """Generate a Suna Tool class for this MCP tool."""
        class_name = f"MCP{self._normalize_name(self.server_name, capitalize=True)}{self._normalize_name(self.tool_name, capitalize=True)}Tool"
        
        # Create method name
        method_name = f"mcp_{self._normalize_name(self.server_name)}_{self._normalize_name(self.tool_name)}"
        
        # Get schemas
        openapi_schema = self.get_openapi_schema()
        xml_schema = self.get_xml_schema()
        
        async def tool_method(self, **kwargs) -> ToolResult:
            """Generated method for MCP tool."""
            return await wrapper.call_tool(**kwargs)
        
        # Create the class dynamically
        wrapper = self  # Capture wrapper in closure
        
        class_dict = {
            method_name: tool_method,
            "_mcp_wrapper": wrapper,
            "_mcp_tool_name": self.tool_name,
            "_mcp_server_name": self.server_name
        }
        
        # Add schema decorators
        tool_method = openapi_schema_decorator(openapi_schema)(tool_method)
        tool_method = xml_schema_decorator(xml_schema)(tool_method)
        class_dict[method_name] = tool_method
        
        # Create the class
        tool_class = type(class_name, (Tool,), class_dict)
        
        return tool_class
    
    async def call_tool(self, **kwargs) -> ToolResult:
        """Execute the MCP tool with given arguments.
        
        Args:
            **kwargs: Tool arguments
            
        Returns:
            ToolResult with execution result
        """
        try:
            if not self.mcp_client.connected:
                return self.fail_response(f"MCP server {self.server_name} is not connected")
            
            # Validate arguments
            is_valid, error = self._validate_arguments(kwargs)
            if not is_valid:
                return self.fail_response(error)
            
            # Apply default values
            self._apply_defaults(kwargs)
            
            # Call the MCP tool
            result = await self.mcp_client.call_tool(self.tool_name, kwargs)
            
            # Check if MCP tool returned an error
            if result.get("isError", False):
                error_msg = self._format_mcp_response(result)
                return self.fail_response(f"MCP tool error: {error_msg}")
            
            # Format successful response
            formatted_result = self._format_mcp_response(result)
            return self.success_response(formatted_result)
            
        except Exception as e:
            logger.error(f"Error calling MCP tool {self.tool_name} on {self.server_name}: {e}")
            return self.fail_response(f"Error calling MCP tool {self.tool_name}: {str(e)}")
    
    def success_response(self, data: Union[Dict[str, Any], str]) -> ToolResult:
        """Create a successful tool result."""
        if isinstance(data, dict):
            formatted_data = str(data)
        else:
            formatted_data = data
        return ToolResult(success=True, output=formatted_data)
    
    def fail_response(self, msg: str) -> ToolResult:
        """Create a failed tool result."""
        return ToolResult(success=False, output=msg)
    
    def _validate_arguments(self, arguments: Dict[str, Any]) -> tuple[bool, Optional[str]]:
        """Validate arguments against the tool's input schema.
        
        Returns:
            Tuple of (is_valid, error_message)
        """
        schema = self.input_schema
        
        # Check required properties
        required = schema.get("required", [])
        for req_prop in required:
            if req_prop not in arguments:
                return False, f"Missing required argument: {req_prop}"
        
        # Basic type checking
        properties = schema.get("properties", {})
        for arg_name, arg_value in arguments.items():
            if arg_name in properties:
                prop_schema = properties[arg_name]
                expected_type = prop_schema.get("type")
                
                if not self._check_type(arg_value, expected_type):
                    return False, f"Invalid type for argument {arg_name}: expected {expected_type}"
        
        return True, None
    
    def _check_type(self, value: Any, expected_type: str) -> bool:
        """Check if value matches expected JSON schema type."""
        if expected_type == "string":
            return isinstance(value, str)
        elif expected_type == "integer":
            return isinstance(value, int)
        elif expected_type == "number":
            return isinstance(value, (int, float))
        elif expected_type == "boolean":
            return isinstance(value, bool)
        elif expected_type == "array":
            return isinstance(value, list)
        elif expected_type == "object":
            return isinstance(value, dict)
        return True  # Unknown type, assume valid
    
    def _apply_defaults(self, arguments: Dict[str, Any]) -> None:
        """Apply default values from schema to arguments."""
        properties = self.input_schema.get("properties", {})
        
        for prop_name, prop_schema in properties.items():
            if prop_name not in arguments and "default" in prop_schema:
                arguments[prop_name] = prop_schema["default"]
    
    def _format_mcp_response(self, response: Dict[str, Any]) -> str:
        """Format MCP response content for display."""
        content_items = response.get("content", [])
        
        if not content_items:
            return "(No output)"
        
        formatted_parts = []
        for item in content_items:
            item_type = item.get("type", "text")
            
            if item_type == "text":
                formatted_parts.append(item.get("text", ""))
            elif item_type == "image":
                mime_type = item.get("mimeType", "unknown")
                formatted_parts.append(f"Image ({mime_type})")
            elif item_type == "resource":
                resource = item.get("resource", {})
                uri = resource.get("uri", "unknown")
                formatted_parts.append(f"Resource: {uri}")
            else:
                formatted_parts.append(f"[{item_type} content]")
        
        return "\n".join(formatted_parts)
    
    def _flatten_schema_for_xml(self, schema: Dict[str, Any], prefix: str = "") -> Dict[str, Any]:
        """Flatten nested JSON schema for XML representation."""
        flattened = {}
        properties = schema.get("properties", {})
        
        for prop_name, prop_schema in properties.items():
            full_name = f"{prefix}_{prop_name}" if prefix else prop_name
            
            if prop_schema.get("type") == "object":
                # Recursively flatten nested objects
                nested = self._flatten_schema_for_xml(prop_schema, full_name)
                flattened.update(nested)
            else:
                # Copy property with default info
                flattened_prop = prop_schema.copy()
                if "default" in flattened_prop:
                    # Add default to description
                    desc = flattened_prop.get("description", "")
                    default_val = flattened_prop["default"]
                    flattened_prop["description"] = f"{desc} Default: {default_val}".strip()
                
                flattened[full_name] = flattened_prop
        
        return flattened
    
    def _generate_xml_example(self, flattened_params: Dict[str, Any]) -> str:
        """Generate XML example content from flattened parameters."""
        examples = []
        for param_name, param_def in flattened_params.items():
            param_type = param_def.get("type", "string")
            if param_type == "string":
                examples.append(f'{param_name}="example_value"')
            elif param_type in ["integer", "number"]:
                examples.append(f'{param_name}="42"')
            elif param_type == "boolean":
                examples.append(f'{param_name}="true"')
        
        return " " + " ".join(examples) if examples else ""
    
    def _normalize_name(self, name: str, capitalize: bool = False) -> str:
        """Normalize name for use in identifiers."""
        # Replace non-alphanumeric with underscores
        normalized = re.sub(r'[^a-zA-Z0-9]', '_', name.lower())
        # Remove multiple consecutive underscores
        normalized = re.sub(r'_+', '_', normalized)
        # Remove leading/trailing underscores
        normalized = normalized.strip('_')
        
        if capitalize:
            # Capitalize each part for class names
            parts = normalized.split('_')
            normalized = ''.join(part.capitalize() for part in parts if part)
        
        return normalized


def openapi_schema_decorator(schema: Dict[str, Any]):
    """Decorator to add OpenAPI schema to a method."""
    def decorator(func):
        if not hasattr(func, '_tool_schemas'):
            func._tool_schemas = []
        
        tool_schema = ToolSchema(
            schema_type=SchemaType.OPENAPI,
            schema=schema
        )
        func._tool_schemas.append(tool_schema)
        return func
    return decorator


def xml_schema_decorator(schema: XMLTagSchema):
    """Decorator to add XML schema to a method."""
    def decorator(func):
        if not hasattr(func, '_tool_schemas'):
            func._tool_schemas = []
        
        tool_schema = ToolSchema(
            schema_type=SchemaType.XML,
            schema=schema
        )
        func._tool_schemas.append(tool_schema)
        return func
    return decorator