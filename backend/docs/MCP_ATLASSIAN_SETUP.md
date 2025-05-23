# Atlassian MCP Server Setup Guide

This guide explains how to set up and use the Atlassian MCP (Model Context Protocol) server integration in Suna, which enables the agent to interact with Jira and Confluence.

## Overview

The Atlassian MCP integration allows Suna to:
- Search and read Confluence pages
- Search, create, and manage Jira issues
- Access both Cloud and Server/Data Center deployments
- Maintain secure authentication via API tokens

## Prerequisites

1. **Docker**: The Atlassian MCP server runs as a Docker container
2. **Atlassian API Tokens**: You'll need API tokens for authentication
3. **Atlassian Instance URLs**: URLs for your Jira and/or Confluence instances

## Setup Instructions

### 1. Generate API Tokens

#### For Atlassian Cloud:
1. Go to [https://id.atlassian.com/manage-profile/security/api-tokens](https://id.atlassian.com/manage-profile/security/api-tokens)
2. Click "Create API token"
3. Give it a descriptive name (e.g., "Suna MCP Integration")
4. Copy the token immediately (you won't be able to see it again)

#### For Server/Data Center:
1. Navigate to your profile settings
2. Look for "Personal Access Tokens" or similar
3. Create a new token with appropriate permissions
4. Copy the token

### 2. Configure Environment Variables

Add the following to your `backend/.env` file:

```bash
# Confluence Configuration (optional - only if using Confluence)
CONFLUENCE_URL=https://your-company.atlassian.net/wiki
CONFLUENCE_USERNAME=your.email@company.com
CONFLUENCE_API_TOKEN=your_confluence_api_token_here

# Jira Configuration (optional - only if using Jira)
JIRA_URL=https://your-company.atlassian.net
JIRA_USERNAME=your.email@company.com
JIRA_API_TOKEN=your_jira_api_token_here
```

**Note**: You can configure just Jira, just Confluence, or both. The integration will only enable if at least one set of credentials is provided.

### 3. Verify Docker Setup

Ensure Docker is running and can pull the Atlassian MCP image:

```bash
docker pull ghcr.io/sooperset/mcp-atlassian:latest
```

## Available Tools

Once configured, the following tools become available to the agent:

### Confluence Tools

1. **confluence_search**
   - Search Confluence content using CQL (Confluence Query Language)
   - Example: "Search for pages about API documentation"

2. **confluence_get_page**
   - Retrieve the full content of a specific Confluence page
   - Example: "Get the content of the page with ID 12345"

### Jira Tools

1. **jira_search**
   - Search for Jira issues using JQL (Jira Query Language)
   - Example: "Find all open bugs assigned to me"

2. **jira_get_issue**
   - Get detailed information about a specific Jira issue
   - Example: "Show me the details of PROJ-123"

3. **jira_create_issue**
   - Create new Jira issues
   - Example: "Create a bug ticket for the login issue"

## Usage Examples

### Example Prompts for the Agent

1. **Confluence Search**:
   - "Search Confluence for documentation about our API endpoints"
   - "Find all pages in the Engineering space updated this week"

2. **Jira Operations**:
   - "Show me all critical bugs in the PROJ project"
   - "Create a new task for implementing user authentication"
   - "What's the status of PROJ-456?"

### Advanced Configuration

You can customize which tools are available by modifying the `ENABLED_TOOLS` environment variable in the MCP configuration:

```python
# In backend/agent/run.py
"-e", "ENABLED_TOOLS=confluence_search,jira_search",  # Only enable search tools
```

## Security Considerations

1. **API Token Storage**: Never commit API tokens to version control
2. **Permissions**: The integration respects your Atlassian permissions - it can only access what your account can access
3. **Read-Only Mode**: You can enable read-only mode to prevent write operations
4. **Project/Space Filtering**: Consider limiting access to specific projects or spaces

## Troubleshooting

### Common Issues

1. **"Authentication failed" errors**:
   - Verify your API token is correct
   - Check that your username matches the account that created the token
   - For Cloud: Use your email address as username
   - For Server: Use your regular username

2. **"Cannot connect to Docker" errors**:
   - Ensure Docker Desktop is running
   - Check Docker permissions
   - Try running `docker ps` to verify Docker is accessible

3. **Tools not appearing**:
   - Check that environment variables are set correctly
   - Verify at least one of JIRA_URL or CONFLUENCE_URL is configured
   - Check agent logs for MCP connection errors

### Debug Mode

To enable verbose logging for troubleshooting:

```python
# Add to the atlassian server config in run.py
"env": {
    # ... other env vars ...
    "LOG_LEVEL": "DEBUG"
}
```

## Limitations

1. **Rate Limits**: Atlassian APIs have rate limits - the integration handles these gracefully
2. **Large Results**: Search results are limited to prevent overwhelming the context
3. **Attachments**: File attachments are not currently supported
4. **Rich Content**: Some Confluence formatting may be simplified

## Best Practices

1. **Use Specific Searches**: Provide specific search criteria to get relevant results
2. **Project/Space Context**: Mention the project key or space name when possible
3. **Incremental Updates**: For large changes, break them into smaller operations
4. **Error Handling**: The agent will report any API errors - check credentials if you see authentication errors

## Support

For issues specific to the Atlassian MCP integration:
- Check the [mcp-atlassian repository](https://github.com/sooperset/mcp-atlassian)
- Review Atlassian API documentation
- Enable debug logging for detailed error messages