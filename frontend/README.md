# JEEX Plan Frontend

React + TypeScript frontend application for the JEEX Plan multi-agent documentation generation system.

## Overview

This is a modern React application built with:

- **React 19+** with TypeScript
- **TanStack Query** for server state management
- **React Router** for navigation
- **SCSS Modules** for styling
- **Radix UI** for accessible UI components
- **Vite** for development and build tooling

## Features

### Implemented (Epic 06)

✅ **Task 06.1: React Application Foundation**

- React + TypeScript + Vite setup on port 5200
- Routing system with protected routes
- Context API for authentication state
- HTTP client configuration with authentication

✅ **Task 06.2: Four-Step Wizard Interface**

- Wizard navigation with progress indicator
- Step 1: Project description input form
- Step 2: Architecture preferences interface
- Step 3: Planning configuration options
- Step 4: Standards customization interface

✅ **Task 06.3: Real-time Progress Integration**

- SSE client implementation for progress streaming
- Progress bars and status indicators
- Connection management and reconnection logic

✅ **Task 06.4: Document Management Interface**

- Markdown preview component with syntax highlighting
- Document diff visualization interface
- Version history browser
- Iterative editing interface for refinements

✅ **Task 06.5: Project Management Dashboard**

- Project list with filtering and search
- Project creation workflow
- Project settings and collaboration management
- Recent activity and status overview

✅ **Task 06.6: User Experience Enhancements**

- Responsive design for various screen sizes
- Loading states and error handling UX
- Keyboard shortcuts and accessibility features
- Toast notifications and user feedback system

## Architecture

### Directory Structure

```
src/
├── components/
│   ├── ui/                    # Reusable UI components
│   ├── Layout/                # Main application layout
│   ├── Wizard/                # Project creation wizard
│   └── ProjectWizard/         # Complete project wizard flow
├── contexts/
│   └── AuthContext.tsx        # Authentication context
├── hooks/
│   ├── useProjects.ts         # Project management hooks
│   ├── useDocuments.ts        # Document management hooks
│   └── useProgress.ts         # Real-time progress hooks
├── pages/
│   ├── Login/                 # Authentication page
│   ├── Dashboard/             # Main dashboard
│   └── Projects/              # Projects listing
├── providers/
│   └── QueryProvider.tsx      # TanStack Query provider
├── services/
│   └── api.ts                 # API client and methods
├── styles/
│   ├── variables.scss         # SCSS variables
│   └── mixins.scss           # SCSS mixins
└── types/
    └── api.ts                 # TypeScript type definitions
```

### Key Components

- **AuthContext**: Manages user authentication state
- **Layout**: Main application layout with navigation
- **Wizard**: Reusable multi-step wizard component
- **ProjectWizard**: Complete project creation workflow
- **Dashboard**: Main dashboard with project overview
- **Projects**: Project listing and management

### State Management

- **Authentication**: Context API with JWT tokens
- **Server State**: TanStack Query for caching and synchronization
- **Real-time Updates**: Server-Sent Events (SSE) for progress tracking
- **Form State**: Local component state for wizard steps

## API Integration

### Endpoints

The frontend integrates with the following backend API endpoints:

- `POST /auth/login` - User authentication
- `POST /auth/logout` - User logout
- `POST /auth/refresh` - Token refresh
- `GET /auth/me` - Get current user
- `GET /projects` - List projects (paginated)
- `GET /projects/{id}` - Get project details
- `POST /projects` - Create new project
- `PUT /projects/{id}` - Update project
- `DELETE /projects/{id}` - Delete project
- `POST /projects/{id}/process` - Start project processing
- `GET /projects/{id}/documents` - List project documents
- `GET /projects/{id}/documents/{doc_id}` - Get document
- `PUT /projects/{id}/documents/{doc_id}` - Update document
- `POST /projects/{id}/documents/{doc_id}/regenerate` - Regenerate document
- `GET /health` - Health status
- **SSE** `/projects/{id}/progress` - Real-time progress updates

### Authentication

- JWT-based authentication with refresh tokens
- Automatic token refresh every 15 minutes
- Protected routes with authentication checks
- Tenant isolation enforced server-side

### Real-time Features

- Server-Sent Events (SSE) for progress updates
- Automatic reconnection with exponential backoff
- Real-time document generation status
- Live progress indicators during processing

## Development

### Prerequisites

- Node.js 18+
- pnpm package manager

### Setup

```bash
cd frontend
pnpm install
```

### Development Server

```bash
pnpm run dev
# Server runs on http://localhost:5200
```

### Build

```bash
pnpm run build
pnpm run preview
```

### Code Quality

```bash
pnpm run lint          # ESLint
pnpm run lint:fix      # Fix ESLint issues
pnpm run type-check    # TypeScript checking
pnpm run format        # Prettier formatting
```

## Environment Variables

Create a `.env` file in the frontend directory:

```env
VITE_API_BASE_URL=http://localhost:5210
VITE_APP_TITLE=JEEX Plan
VITE_ENVIRONMENT=development
VITE_BRAND_TITLE=JEEX Plan
VITE_BRAND_SUBTITLE=Documentation Generator
```

`VITE_BRAND_TITLE` and `VITE_BRAND_SUBTITLE` feed the application shell via `src/config/appConfig.ts`. Both keys fall back to `JEEX Plan` and `Documentation Generator` when unset, ensuring local development continues to work without additional configuration.

## Styling

### SCSS Modules

All components use SCSS modules for styling:

```scss
// Component.module.scss
@import '../../../styles/variables.scss';
@import '../../../styles/mixins.scss';

.container {
  @include flex-center;
  padding: $spacing-lg;
}
```

### Design System

- **Colors**: CSS custom properties with dark mode support
- **Typography**: Consistent font scales and line heights
- **Spacing**: 8px base unit scaling system
- **Components**: Radix UI primitives with custom styling
- **Responsive**: Mobile-first responsive design

### Theme

The application supports both light and dark themes with CSS custom properties:

```scss
:root {
  --color-primary: #3b82f6;
  --color-background: #ffffff;
  --color-text-primary: #1e293b;
  // ... more variables
}

@media (prefers-color-scheme: dark) {
  :root {
    --color-background: #0f172a;
    --color-text-primary: #f8fafc;
    // ... dark mode overrides
  }
}
```

## Multi-tenant Architecture

The frontend enforces multi-tenant isolation through:

- Server-side tenant filtering (never client-side)
- JWT tokens containing tenant context
- All API calls automatically scoped by tenant
- No cross-tenant data access possible

## Performance

- Code splitting with React.lazy()
- TanStack Query for intelligent caching
- Optimistic updates for better UX
- Debounced search and filtering
- Lazy loading of heavy components

## Accessibility

- Radix UI primitives for ARIA compliance
- Keyboard navigation support
- Screen reader optimizations
- Focus management in modals and wizards
- High contrast color schemes

## Browser Support

- Modern evergreen browsers (Chrome, Firefox, Safari, Edge)
- ES2022+ features
- CSS Grid and Flexbox layouts
- WebSocket/SSE support required

## Production Considerations

- Environment-specific API URLs
- Error boundary implementations
- Analytics integration points
- Performance monitoring hooks
- Security headers via NGINX proxy
