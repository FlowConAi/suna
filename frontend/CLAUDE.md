# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in the Suna frontend repository.

## Project Overview

Suna is an open-source generalist AI agent that helps users accomplish real-world tasks with natural conversation. The frontend provides a responsive user interface with chat interfaces, project management, agent execution monitoring, and real-time updates from the backend.

## Architecture

The frontend is built with the following technologies and architecture:

1. **Framework**: Next.js 15+ with React 18+ using the App Router
2. **Styling**: Tailwind CSS with shadcn/ui component library
3. **State Management**: Combination of React Context, Zustand, and React Query
4. **Authentication**: Supabase Auth with JWT tokens
5. **Data Fetching**: React Query for caching and state management
6. **Real-time Updates**: Server-Sent Events (SSE) for streaming agent responses
7. **Deployment**: Docker container, configurable for various environments

## Key Files and Directories

- `src/app/`: Next.js App Router pages and layouts
  - `(dashboard)/`: Protected dashboard routes
    - `layout.tsx`: Main dashboard layout with sidebar
    - `agents/[threadId]/`: Agent thread view
    - `dashboard/`: Main dashboard/home view
  - `(home)/`: Public home/landing pages
  - `auth/`: Authentication pages
  - `share/`: Public thread sharing functionality
- `src/components/`: React components
  - `thread/`: Chat thread components
    - `chat-input/`: User input components
    - `content/`: Message rendering
    - `tool-views/`: Renderers for tool results
  - `sidebar/`: Navigation sidebar
  - `ui/`: Common UI components (shadcn)
  - `maintenance/`: Maintenance and error pages
- `src/lib/`: Utility functions and services
  - `api.ts`: API client for backend calls
  - `supabase/`: Supabase client configuration
  - `utils/`: Helper functions
- `src/hooks/`: Custom React hooks
  - `react-query/`: Query hooks for data fetching
  - `use-accounts.ts`: Account management hooks
- `src/contexts/`: React context providers
- `src/providers/`: Provider components for app-wide state

## Main Features

1. **Thread UI**: Real-time chat interface with markdown rendering
2. **Tool Result Visualization**: Custom renderers for different tool results
3. **Project Management**: Creating and managing agent projects
4. **Real-time Updates**: Streaming responses from agents
5. **Authentication**: User login, registration, password reset
6. **Sharing**: Public sharing of conversation threads
7. **Account Management**: Teams, billing, and settings

## Development Commands

```bash
# Navigate to frontend directory
cd frontend

# Install dependencies
npm install

# Run development server
npm run dev

# Build for production
npm run build

# Lint code
npm run lint

# Format code
npm run format
```

## Component Patterns

### 1. Page Components

Located in `src/app/**/page.tsx` files. These are route components that:
- Fetch initial data using React Server Components when possible
- Provide layout structure for the page
- Import and compose client components

### 2. Client Components

Located in `src/components/`. These are interactive components that:
- Use React hooks and state
- Handle user interactions
- Use 'use client' directive at the top
- Fetch data with React Query hooks

### 3. Layout Components

Located in `src/app/**/layout.tsx`. These define shared layouts that:
- Provide navigation structure
- Handle authentication state
- Include error boundaries
- Configure providers

## API Integration

The frontend communicates with the backend through several key functions:

1. **Thread Management**:
   - `getThreads()`: Fetch thread list
   - `getThread(threadId)`: Get thread details
   - `createThread(projectId)`: Create a new thread
   - `addUserMessage(threadId, content)`: Add user message

2. **Agent Execution**:
   - `startAgent(threadId, options)`: Start agent execution
   - `stopAgent(agentRunId)`: Stop agent execution
   - `getAgentStatus(agentRunId)`: Check agent status
   - `streamAgent(agentRunId, callbacks)`: Stream agent responses

3. **Project Management**:
   - `getProjects()`: Fetch project list
   - `getProject(projectId)`: Get project details
   - `createProject(data)`: Create a new project

## State Management

The application uses different state management strategies for different purposes:

1. **Server State**: React Query for API data with caching
2. **UI State**: React state and Context API
3. **Global State**: Zustand stores for cross-component state
4. **Authentication State**: Auth Provider with Supabase

## Error Handling and Maintenance

The app includes multiple error handling mechanisms:

1. **API Error Handling**: Consistent error handling in API functions
2. **Error Boundaries**: React error boundaries for component errors
3. **Maintenance Mode**: Detection and display of maintenance status
   - `components/maintenance/maintenance-page.tsx`: Full-page maintenance UI
   - `components/maintenance-alert.tsx`: Modal alert for high-demand notices
   - API health checks in dashboard layout

## Environment Configuration

Create a `.env.local` file based on `.env.example` with:

```
# Supabase
NEXT_PUBLIC_SUPABASE_URL=your_supabase_url
NEXT_PUBLIC_SUPABASE_ANON_KEY=your_supabase_anon_key

# Backend
NEXT_PUBLIC_BACKEND_URL=http://localhost:8000/api

# Frontend
NEXT_PUBLIC_URL=http://localhost:3000
NEXT_PUBLIC_ENV_MODE=LOCAL
```

## Important UI Components

1. **Thread UI**: `components/thread/` - The main chat interface
   - `ThreadMessages`: Displays conversation messages
   - `ThreadInput`: User input with file attachment support
   - `ToolView`: Renders tool outputs with specialized components

2. **Sidebar**: `components/sidebar/` - Application navigation
   - `SidebarLeft`: Main sidebar with navigation items
   - `ThreadsList`: List of conversation threads
   - `ProjectSelector`: Project selection dropdown

3. **Maintenance**: `components/maintenance/` - System status notifications
   - `MaintenancePage`: Full-page maintenance notice
   - `MaintenanceAlert`: Modal alert for system notices

## Common Development Tasks

### Adding a New Tool View

1. Create a new component in `src/components/thread/tool-views/`
2. Update the `ToolView` component to handle the new tool type
3. Add any necessary styling with Tailwind classes

### Implementing a New API Integration

1. **Add API function** to `src/lib/api.ts`:
   ```typescript
   export async function getMyData(id: string): Promise<MyData> {
     const response = await fetch(
       `${BACKEND_URL}/my-endpoint/${id}`,
       {
         headers: await getAuthHeaders(),
       }
     );
     
     if (!response.ok) {
       throw new Error('Failed to fetch data');
     }
     
     return response.json();
   }
   ```

2. **Create React Query hook** in `src/hooks/react-query/`:
   ```typescript
   export function useMyData(id: string) {
     return useQuery({
       queryKey: ['my-data', id],
       queryFn: () => getMyData(id),
       enabled: !!id,
     });
   }
   ```

3. **Use in component**:
   ```typescript
   function MyComponent({ id }: { id: string }) {
     const { data, isLoading, error } = useMyData(id);
     
     if (isLoading) return <Skeleton />;
     if (error) return <ErrorMessage error={error} />;
     
     return <DataDisplay data={data} />;
   }
   ```

### Adding a New Route

1. Create a new directory in the appropriate section of `src/app/`
2. Add `page.tsx` for the route content:
   ```typescript
   export default async function MyPage() {
     // Server component - can fetch data
     const data = await fetchData();
     
     return (
       <div>
         <ClientComponent data={data} />
       </div>
     );
   }
   ```
3. Add `layout.tsx` if needed for specialized layout
4. Update navigation in sidebar:
   ```typescript
   // components/sidebar/nav-main.tsx
   const navItems = [
     {
       title: 'My New Route',
       url: '/my-route',
       icon: IconComponent,
     },
   ];
   ```

## Debugging Tips

1. **API Connection Issues**:
   - Check backend URL in environment variables
   - Verify API health with health check endpoint
   - Look for CORS or network issues in browser console

2. **Authentication Problems**:
   - Verify Supabase URL and anon key
   - Check authentication state in localStorage
   - Look for JWT expiration issues

3. **Streaming Updates**:
   - Verify EventSource connections in Network tab
   - Check for backend stream endpoint issues
   - Test with simple curl requests to isolate frontend issues

4. **UI Rendering Issues**:
   - Check for React key warnings
   - Verify component props
   - Use React Developer Tools to inspect component tree

## Performance Tips

1. Use React Server Components for data fetching when possible
2. Implement proper React Query caching and invalidation
3. Use windowing for long lists of items
4. Optimize image sizes and apply proper loading strategies
5. Implement code splitting with dynamic imports

## Real-time Streaming Implementation

### EventSource Architecture

The frontend uses EventSource API for Server-Sent Events:

```typescript
// lib/api.ts - streamAgent function
const eventSource = new EventSource(
  `${BACKEND_URL}/agent-run/${agentRunId}/stream?token=${token}`
);

eventSource.onmessage = (event) => {
  const data = JSON.parse(event.data);
  // Process different message types
};
```

### Message Processing

1. **Streaming Text Assembly**:
   - Chunks arrive with sequence numbers
   - Frontend sorts and concatenates chunks
   - Handles out-of-order delivery

2. **Tool Result Handling**:
   - Tool results rendered by specific components
   - Located in `components/thread/tool-views/`
   - Registry pattern for tool view mapping

3. **Status Updates**:
   - Real-time tool execution status
   - Cost tracking and token usage
   - Error propagation

### useAgentStream Hook

Core hook for managing streaming state:

```typescript
const {
  status,
  isStreaming,
  startStream,
  stopStream,
  orderedTextContent,
  toolCall,
  toolCalls
} = useAgentStream({
  onMessage: (message) => { /* handle message */ },
  onError: (error) => { /* handle error */ },
  onClose: () => { /* cleanup */ }
});
```

## Security Considerations

### Authentication
- JWT tokens stored in Supabase Auth
- Bearer token authentication for API calls
- Query parameter auth for SSE endpoints (limitation of EventSource)

### Data Protection
- Sanitize user-generated content before rendering
- Use proper CSP headers (configure in Next.js)
- Validate all API responses

### CORS Configuration
- Backend must allow frontend origin
- Configure in production deployment

## State Management Patterns

### Global State (Zustand)
```typescript
// For cross-component state
const useAppStore = create((set) => ({
  activeThreadId: null,
  setActiveThreadId: (id) => set({ activeThreadId: id })
}));
```

### Server State (React Query)
```typescript
// For API data with caching
const { data, isLoading, error } = useQuery({
  queryKey: ['thread', threadId],
  queryFn: () => getThread(threadId),
  staleTime: 5 * 60 * 1000, // 5 minutes
});
```

### Local State (React)
```typescript
// For component-specific state
const [isOpen, setIsOpen] = useState(false);
```

## Error Handling Patterns

### API Error Handling
```typescript
try {
  const response = await fetch(url);
  if (!response.ok) {
    const error = await response.json();
    throw new APIError(error.message, response.status);
  }
  return response.json();
} catch (error) {
  // Handle network errors
  if (error instanceof TypeError) {
    throw new NetworkError('Connection failed');
  }
  throw error;
}
```

### Component Error Boundaries
```typescript
// app/layout.tsx
<ErrorBoundary fallback={<ErrorFallback />}>
  {children}
</ErrorBoundary>
```

### Maintenance Detection
- Health check in dashboard layout
- Automatic maintenance page display
- High-demand modal alerts

## Testing Setup (Currently Missing)

### Recommended Configuration

1. **Install Dependencies**:
   ```bash
   npm install --save-dev jest @testing-library/react \
     @testing-library/jest-dom @testing-library/user-event \
     ts-jest @types/jest
   ```

2. **Jest Configuration** (`jest.config.js`):
   ```javascript
   module.exports = {
     preset: 'ts-jest',
     testEnvironment: 'jsdom',
     setupFilesAfterEnv: ['<rootDir>/src/test/setup.ts'],
     moduleNameMapper: {
       '^@/(.*)$': '<rootDir>/src/$1',
     },
   };
   ```

3. **Test Structure**:
   ```
   src/
   ├── __tests__/
   │   ├── components/
   │   ├── hooks/
   │   └── utils/
   └── test/
       └── setup.ts
   ```

## Tool View Implementation Guide

### Creating a New Tool View

1. **Create Component** in `components/thread/tool-views/`:
   ```typescript
   interface MyToolViewProps {
     content: any;
     isStreaming?: boolean;
   }
   
   export function MyToolView({ content, isStreaming }: MyToolViewProps) {
     return (
       <div className="tool-result">
         {/* Render tool output */}
       </div>
     );
   }
   ```

2. **Register in ToolViewRegistry**:
   ```typescript
   // tool-views/wrapper/ToolViewRegistry.tsx
   const toolViewMap: Record<string, ComponentType<any>> = {
     'my_tool': MyToolView,
     // ... other tools
   };
   ```

3. **Handle in ToolViewWrapper**:
   - Automatic selection based on tool name
   - Fallback to GenericToolView

## Deployment Considerations

### Environment Variables
```bash
# Production
NEXT_PUBLIC_BACKEND_URL=https://api.suna.so/api
NEXT_PUBLIC_URL=https://suna.so
NEXT_PUBLIC_ENV_MODE=PRODUCTION

# Staging
NEXT_PUBLIC_BACKEND_URL=https://staging-api.suna.so/api
NEXT_PUBLIC_URL=https://staging.suna.so
NEXT_PUBLIC_ENV_MODE=STAGING
```

### Build Optimization
- Enable SWC minification
- Configure image optimization
- Set up CDN for static assets
- Enable gzip compression

### Docker Configuration
- Multi-stage build for smaller images
- Non-root user for security
- Health check endpoint

## Common Development Patterns

### Loading States
```typescript
if (isLoading) {
  return <ThreadSkeleton />;
}
```

### Empty States
```typescript
if (!data || data.length === 0) {
  return <EmptyState message="No threads yet" />;
}
```

### Optimistic Updates
```typescript
const mutation = useMutation({
  mutationFn: updateThread,
  onMutate: async (newData) => {
    // Cancel queries
    await queryClient.cancelQueries(['thread', threadId]);
    
    // Optimistic update
    const previousData = queryClient.getQueryData(['thread', threadId]);
    queryClient.setQueryData(['thread', threadId], newData);
    
    return { previousData };
  },
  onError: (err, newData, context) => {
    // Rollback on error
    queryClient.setQueryData(
      ['thread', threadId], 
      context.previousData
    );
  },
});
```