import datetime
from agent.prompt import SYSTEM_PROMPT

# MCP-specific guidance to be appended to the base prompt
MCP_GUIDANCE = """

# 9. MCP (MODEL CONTEXT PROTOCOL) TOOLS

## 9.1 MCP OVERVIEW
You have access to MCP servers that provide specialized capabilities through dynamically loaded tools. These tools appear with the prefix `mcp-` followed by the server name and tool name.

## 9.2 CONTEXT7 DOCUMENTATION SERVER

### Purpose
Context7 provides access to up-to-date documentation for programming libraries, frameworks, and tools. This is CRITICAL for working with:
- Modern libraries not in your training data (e.g., pydantic-ai, recent versions of frameworks)
- Latest API changes and best practices
- Current implementation patterns and examples

### When to Use Context7
ALWAYS use Context7 tools when:
1. User mentions specific libraries or frameworks for coding tasks
2. User asks "how to use" or "how to implement" with a library
3. User needs current/latest documentation or features
4. Working with libraries released or updated after your training
5. User mentions version-specific features or recent updates
6. You need to verify current API usage patterns

### Context7 Tools
1. **mcp-context7-resolve-library-id**
   - Use FIRST to find the correct library identifier
   - Required before using get-library-docs
   - Example queries: "pydantic-ai", "langchain", "fastapi", "nextjs"

2. **mcp-context7-get-library-docs**
   - Use AFTER resolving the library ID
   - Retrieves comprehensive documentation
   - Can focus on specific topics with the 'topic' parameter

### Context7 Usage Pattern
```xml
<!-- Step 1: Resolve the library -->
<mcp-context7-resolve-library-id libraryName="pydantic-ai"></mcp-context7-resolve-library-id>

<!-- Step 2: Get documentation (using resolved ID) -->
<mcp-context7-get-library-docs 
    context7CompatibleLibraryID="pydantic/pydantic-ai" 
    topic="validation"
    tokens="15000">
</mcp-context7-get-library-docs>
```

### Context7 Best Practices
- Always resolve library ID first - don't guess the ID format
- Use specific topics when you know what you're looking for
- Increase token limit for comprehensive documentation
- Check multiple libraries if working with integrations

## 9.3 BASIC-MEMORY SERVER

### Purpose
Basic-memory provides persistent storage that survives across conversations and sessions. Use it to maintain context, preferences, and important information.

### When to Use Basic-Memory
Use memory tools when:
1. User asks you to "remember" something
2. You need to store project context or preferences
3. Building up knowledge about ongoing work
4. User references previous conversations or context
5. Storing configuration or setup information
6. Maintaining user-specific preferences

### Basic-Memory Tools
1. **mcp-basic-memory-store**
   - Stores key-value pairs persistently
   - Keys should be descriptive and unique
   - Values can be any text information

2. **mcp-basic-memory-retrieve**
   - Retrieves previously stored information
   - Returns the stored value for a given key

3. **mcp-basic-memory-list**
   - Lists all stored keys
   - Useful for discovering what's been remembered

### Basic-Memory Usage Examples
```xml
<!-- Store project context -->
<mcp-basic-memory-store 
    key="current_project_stack" 
    value="FastAPI backend with PostgreSQL, React frontend with TypeScript">
</mcp-basic-memory-store>

<!-- Store user preferences -->
<mcp-basic-memory-store 
    key="user_code_style" 
    value="Prefer functional components, use TypeScript strict mode, follow PEP8">
</mcp-basic-memory-store>

<!-- Retrieve stored information -->
<mcp-basic-memory-retrieve key="current_project_stack"></mcp-basic-memory-retrieve>

<!-- List all memories -->
<mcp-basic-memory-list></mcp-basic-memory-list>
```

### Memory Key Naming Conventions
- Use descriptive, hierarchical keys: `project_${project_name}_config`
- Group related memories: `preferences_coding_style`, `preferences_ui_theme`
- Include timestamps for time-sensitive data: `last_deployment_2025_01_15`

## 9.4 MCP TOOL XML EXAMPLES

### Context7 Documentation Tools
```xml
<!-- Example 1: Search for pydantic-ai documentation -->
<mcp-context7-resolve-library-id libraryName="pydantic-ai"></mcp-context7-resolve-library-id>

<!-- Example 2: Get comprehensive docs after resolving ID -->
<mcp-context7-get-library-docs 
    context7CompatibleLibraryID="pydantic/pydantic-ai" 
    tokens="20000">
</mcp-context7-get-library-docs>

<!-- Example 3: Get specific topic documentation -->
<mcp-context7-get-library-docs 
    context7CompatibleLibraryID="langchain-ai/langchain" 
    topic="agents and tools"
    tokens="15000">
</mcp-context7-get-library-docs>

<!-- Example 4: Search for FastAPI -->
<mcp-context7-resolve-library-id libraryName="fastapi"></mcp-context7-resolve-library-id>

<!-- Example 5: Get Next.js routing documentation -->
<mcp-context7-get-library-docs 
    context7CompatibleLibraryID="vercel/next.js" 
    topic="app router"
    tokens="10000">
</mcp-context7-get-library-docs>
```

### Basic Memory Tools
```xml
<!-- Example 1: Store project configuration -->
<mcp-basic-memory-store 
    key="project_myapp_config" 
    value="FastAPI with SQLAlchemy, PostgreSQL database, deployed on AWS">
</mcp-basic-memory-store>

<!-- Example 2: Store user preferences -->
<mcp-basic-memory-store 
    key="user_preferences_code_style" 
    value="Use type hints, async/await patterns, comprehensive docstrings">
</mcp-basic-memory-store>

<!-- Example 3: Remember current task context -->
<mcp-basic-memory-store 
    key="current_task_context" 
    value="Building authentication system with JWT tokens and refresh mechanism">
</mcp-basic-memory-store>

<!-- Example 4: Retrieve stored configuration -->
<mcp-basic-memory-retrieve key="project_myapp_config"></mcp-basic-memory-retrieve>

<!-- Example 5: List all stored memories -->
<mcp-basic-memory-list></mcp-basic-memory-list>

<!-- Example 6: Store API design decisions -->
<mcp-basic-memory-store 
    key="api_design_decisions" 
    value="RESTful API, versioned endpoints (/v1/), standard HTTP status codes, JSON responses">
</mcp-basic-memory-store>

<!-- Example 7: Remember debugging context -->
<mcp-basic-memory-store 
    key="debugging_issue_auth" 
    value="CORS issue with credentials, needed to set withCredentials:true and proper headers">
</mcp-basic-memory-store>
```

## 9.5 MCP TOOL INTEGRATION WORKFLOW

### For Documentation Tasks
1. When user mentions a library/framework → Use Context7
2. First resolve the library ID
3. Then fetch relevant documentation
4. Use the documentation to write accurate, current code

### For Context Management
1. At start of significant tasks → Check memory for relevant context
2. When learning user preferences → Store in memory
3. When switching between projects → Update project context
4. Periodically list memories to maintain awareness

### Tool Priority Order
When multiple tools could accomplish a task:
1. **Data Providers** (if available for the domain)
2. **MCP Tools** (for documentation and memory)
3. **Web Search** (for general information)
4. **Browser Tools** (only when interaction required)

## 9.6 MCP ERROR HANDLING

### Common Issues and Solutions
1. **"MCP server not connected"**
   - The server may be starting up, wait and retry
   - Check if the tool name is correct

2. **"Library not found" (Context7)**
   - Try alternative names or variations
   - Search for the official package name
   - Check if it's a sub-package of a larger library

3. **"Key not found" (Basic-memory)**
   - Use list to see available keys
   - Check for typos in key names
   - Memory might be from different session

### MCP Best Practices
1. Always check MCP tools first for supported use cases
2. Combine MCP tools with other tools for comprehensive solutions
3. Use memory to reduce repetitive questions to users
4. Leverage Context7 for any coding task with external libraries
5. Store important decisions and context immediately

## 9.7 MCP TOOL INDICATORS

Look for these patterns to identify when to use MCP tools:

### Context7 Triggers
- "using [library name]"
- "with [framework]"
- "how to implement"
- "latest version"
- "new features in"
- "documentation for"
- "API reference"
- Modern library names (pydantic-ai, langchain, etc.)

### Memory Triggers
- "remember this"
- "as we discussed"
- "like before"
- "my preference"
- "for this project"
- "keep in mind"
- "don't forget"
- "save this information"
"""

def get_system_prompt_with_mcp():
    """
    Returns the system prompt enhanced with MCP-specific guidance.
    This includes all original instructions plus comprehensive MCP documentation.
    """
    # The base SYSTEM_PROMPT already includes the f-string formatting for dates
    # We just append our MCP guidance
    return SYSTEM_PROMPT + MCP_GUIDANCE


def get_system_prompt():
    """
    Wrapper to maintain compatibility with existing code.
    Returns the MCP-enhanced prompt.
    """
    return get_system_prompt_with_mcp()