# JEEX Plan

> Turn ideas into docs.

JEEX Plan is a multi-agent documentation generation system that transforms raw ideas into professional Markdown documentation packages through AI-powered analysis.

## 🏗️ Architecture Overview

This implementation follows a microservices architecture with the following components:

### Core Services

- **Frontend**: React + TypeScript SPA (Port 5200)
- **API Backend**: FastAPI with Python (Port 5210)
- **PostgreSQL**: Primary database (Port 5220)
- **Qdrant**: Vector database for semantic search (Port 5230)
- **Redis**: Cache and message queue (Port 5240)
- **Vault**: Secrets management (Port 5250)

### Multi-Agent System

- **Business Analyst**: Extracts and structures project requirements
- **Solution Architect**: Designs technical architecture
- **Project Planner**: Creates implementation roadmaps
- **Engineering Standards**: Defines development guidelines

## 🚀 Quick Start

### Prerequisites

- Docker and Docker Compose
- Node.js 18+ and pnpm (for frontend development)
- Python 3.11+ (for backend development)

### Setup

1. **Clone the repository**

   ```bash
   git clone <repository-url>
   cd jeex-plan
   ```

2. **Setup git hooks**

   ```bash
   ./scripts/setup-git-hooks.sh
   ```

3. **Start all services**

   ```bash
   make dev
   # or
   make up
   ```

4. **Setup frontend dependencies**

   ```bash
   cd frontend
   pnpm install
   ```

5. **Access the application**
   - Frontend: <http://localhost:5200> (runs separately via `pnpm run dev`)
   - API: <http://localhost:5210>
   - API Documentation: <http://localhost:5210/docs>

### Environment Configuration

Create `.env` file in project root:

```bash
cp .env.example .env
```

Create `frontend/.env` file:

```bash
cd frontend
cp .env.example .env
```

## 🛠️ Development

### Quick Commands (Makefile)

```bash
# Start all services
make dev
make up

# Monitor services
make status        # Check service status
make logs          # Follow all logs
make health        # Health check all services

# Development shortcuts
make api-logs      # Follow API logs only
make api-shell     # Access API container shell
make redis-cli     # Redis CLI access

# Maintenance
make restart       # Restart all services
make rebuild       # Full rebuild
make clean         # Clean all containers and volumes
```

### Frontend Development

Frontend runs **outside Docker** on the host:

```bash
cd frontend
pnpm install
pnpm run dev       # Runs on http://localhost:5200
```

### Backend Development

Backend runs **inside Docker** with hot reload:

```bash
make dev           # Start with hot reload
make api-logs      # Watch logs
make api-shell     # Access container for debugging
```

### Database Operations

```bash
# Migrations
make db-migrate    # Apply pending migrations
make db-status     # Check migration status
make db-shell      # PostgreSQL shell

# Create new migration (inside container)
docker-compose exec api alembic revision --autogenerate -m "description"
```

## 🏥 Health Checks

```bash
# Check all services
make health

# Individual service monitoring
make status        # Docker container status
make logs          # All service logs
```

Or access individual endpoints:

- API Health: <http://localhost:5210/api/v1/health>
- Frontend: <http://localhost:5200>
- Qdrant: <http://localhost:5230/>
- Vault: <http://localhost:5250/>

## 📊 Monitoring

### Service Endpoints

- **Frontend**: <http://localhost:5200>
- **API**: <http://localhost:5210>
- **API Docs**: <http://localhost:5210/docs>
- **Database**: localhost:5220
- **Qdrant**: <http://localhost:5230>
- **Redis**: localhost:5240
- **Vault**: <http://localhost:5250>

### Development Tools

- **pgAdmin**: Access via `make db-shell`
- **Qdrant UI**: <http://localhost:5230>
- **Vault UI**: <http://localhost:5250>
- **Redis CLI**: `make redis-cli`

## 🔧 Code Quality & Development Standards

### Automated Linting System

The project uses comprehensive automated linting with pre-commit hooks:

```bash
# Run all linting checks
make lint           # Frontend + Markdown + Backend
make lint-fix       # Auto-fix frontend/backend/sql issues
make format         # Format all code
make check          # Type checking
make frontend-lint  # Frontend ESLint + Stylelint
make backend-lint   # Backend Ruff + SQLFluff
make frontend-fix   # Auto-fix frontend lint issues
make backend-fix    # Auto-fix backend lint issues

# Specific checks
make docker-lint    # Docker best practices (Hadolint)
make security-scan  # Security scanning (Checkov)
make pre-commit     # Manual pre-commit check
```

### Pre-commit Hooks

Git hooks automatically run before every commit:

- **Frontend**: Biome (JS/TS), Stylelint (CSS), TypeScript checking
- **Backend**: Ruff (Python linting/formatting), MyPy (type checking)
- **Docker**: Hadolint (best practices), Checkov (security)

Setup hooks:

```bash
./scripts/setup-git-hooks.sh
```

### Tech Stack

**Frontend:**

- React 19+ with TypeScript
- TanStack Query for server state
- CSS Modules with CSS Nesting
- Radix UI components
- Vite for build tooling
- Biome for linting/formatting
- Stylelint for CSS linting

**Backend:**

- FastAPI with Python 3.11+
- SQLAlchemy (async) with PostgreSQL
- Alembic for migrations
- Ruff for linting/formatting
- MyPy for type checking

**Infrastructure:**

- Docker Compose for development
- NGINX reverse proxy
- HashiCorp Vault for secrets
- OpenTelemetry for observability

## 🔧 Configuration

### Environment Variables

Root `.env` file:

```env
# Database
POSTGRES_HOST=localhost
POSTGRES_PORT=5220
POSTGRES_DB=jeex_plan
POSTGRES_USER=postgres
POSTGRES_PASSWORD=your_secure_password

# Redis
REDIS_HOST=localhost
REDIS_PORT=5240
REDIS_PASSWORD=your_redis_password

# Vault
VAULT_ADDR=http://localhost:5250
VAULT_TOKEN=your_vault_token

# Environment
ENVIRONMENT=development
```

Frontend `.env` file:

```env
VITE_API_BASE_URL=http://localhost:5210
VITE_APP_TITLE=JEEX Plan
VITE_ENVIRONMENT=development
VITE_BRAND_TITLE=JEEX Plan
VITE_BRAND_SUBTITLE=Documentation Generator
```

**Security**: Real secrets should be provided through Vault or gitignored `.env.local` files.

### Multi-tenancy

The system enforces strict tenant isolation:

- **Server-side filtering**: All data access automatically scoped by tenant
- **Database models**: TenantMixin ensures tenant separation
- **Repository pattern**: Automatic tenant filtering in data layer
- **Vector search**: Tenant metadata filtering
- **Cache keys**: Namespaced by tenant ID
- **JWT context**: Tenant information embedded in tokens

### Authentication

- JWT-based authentication with refresh tokens
- Automatic token refresh every 15 minutes
- Protected routes with authentication checks
- Tenant isolation enforced server-side

## 📚 API Documentation

Full API documentation available at: <http://localhost:5210/docs>

### Authentication Endpoints

- `POST /auth/login` - User authentication
- `POST /auth/logout` - User logout
- `POST /auth/refresh` - Token refresh
- `GET /auth/me` - Get current user

### Project Management

- `GET /projects` - List projects (paginated)
- `GET /projects/{id}` - Get project details
- `POST /projects` - Create new project
- `PUT /projects/{id}` - Update project
- `DELETE /projects/{id}` - Delete project
- `POST /projects/{id}/process` - Start project processing

### Document Management

- `GET /projects/{id}/documents` - List project documents
- `GET /projects/{id}/documents/{doc_id}` - Get document
- `PUT /projects/{id}/documents/{doc_id}` - Update document
- `POST /projects/{id}/documents/{doc_id}/regenerate` - Regenerate document

### Real-time Features

- **SSE** `/projects/{id}/progress` - Real-time progress updates
- Automatic reconnection with exponential backoff
- Live progress indicators during processing

### Health Checks

- `GET /health` - Comprehensive health status
- Individual service health monitoring
- Database connectivity checks
- Redis and Qdrant connectivity
- Vault secrets management status

## 🎨 Frontend Architecture

### Component Structure

```text
src/
├── components/
│   ├── ui/                    # Reusable UI components (Button, Input, etc.)
│   ├── Layout/                # Main application layout
│   ├── Wizard/                # Multi-step wizard component
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
├── services/
│   └── api.ts                 # API client and methods
├── styles/
│   ├── variables.css         # Global design tokens
│   └── utility-classes.css   # Shared composition helpers
└── types/
    └── api.ts                 # TypeScript type definitions
```

### State Management

- **Authentication**: Context API with JWT tokens
- **Server State**: TanStack Query for caching and synchronization
- **Real-time Updates**: Server-Sent Events (SSE) for progress tracking
- **Form State**: Local component state for wizard steps

### Styling System

- **CSS Modules**: Component-scoped styling
- **CSS Custom Properties**: Design tokens and theming
- **CSS Nesting**: Modern nested selector syntax
- **Utility Classes**: Shared composition helpers
- **Responsive Design**: Mobile-first approach
- **Dark Mode**: Automatic theme switching

## 🔒 Security

### Multi-tenancy Safeguards

- Strict tenant isolation at all levels
- Server-side payload filtering for vector search
- Database row-level security with tenant constraints
- Cache key namespacing by tenant ID
- JWT tokens containing tenant context

### Authentication & Authorization

- JWT tokens with automatic refresh mechanism
- Secure token storage and rotation
- Protected routes with authentication checks
- Tenant isolation enforced server-side

### Data Protection

- TLS encryption for all communications
- Secret management with HashiCorp Vault
- Input validation and sanitization
- Structured logging with sensitive data filtering
- No cross-tenant data access possible

## 📈 Monitoring & Observability

### OpenTelemetry

- Distributed tracing across all services
- Metrics collection and export
- Structured logging with correlation IDs

### Health Monitoring

- Service health endpoints
- Database connectivity checks
- Redis and Qdrant connectivity
- Vault secrets management

### Performance

- Response time monitoring
- Error rate tracking
- Resource utilization metrics
- Custom business metrics

## 🚀 Deployment

### Production Architecture

- **Backend**: Docker containers with FastAPI
- **Frontend**: Static build served via NGINX
- **Database**: PostgreSQL with multi-tenant schema
- **Vector Database**: Qdrant for semantic search
- **Cache**: Redis for session and application cache
- **Secrets**: HashiCorp Vault for credential management
- **Proxy**: NGINX with TLS termination

### Production Considerations

- Environment-specific configurations via Vault
- TLS encryption for all communications
- Automated backup and disaster recovery
- Monitoring and alerting with OpenTelemetry
- Multi-tenant isolation at all layers

### Infrastructure

- Container orchestration (Docker Compose or Kubernetes)
- Load balancing and auto-scaling
- Database clustering and read replicas
- CDN for static frontend assets
- Observability with distributed tracing

## 🤝 Contributing

### Development Workflow

1. **Setup environment**

   ```bash
   git clone <repository-url>
   cd jeex-plan
   ./scripts/setup-git-hooks.sh
   make dev
   ```

2. **Create feature branch**

   ```bash
   git checkout -b feature/your-feature-name
   ```

3. **Make your changes**
   - Follow existing code patterns and conventions
   - Use the established tech stack (React, FastAPI, etc.)
   - Maintain multi-tenant architecture principles

4. **Quality checks**

   ```bash
   make lint          # Run all linting
   make check         # Type checking
   make pre-commit    # Full pre-commit checks
   ```

5. **Commit and push**
   - Pre-commit hooks will automatically run
   - Ensure all checks pass before committing
   - Write clear commit messages

6. **Submit pull request**
   - Include description of changes
   - Reference any related issues
   - Ensure CI/CD checks pass

### Code Standards

- **Frontend**: Biome for JS/TS, Stylelint for CSS
- **Backend**: Ruff for Python linting/formatting, MyPy for types
- **Infrastructure**: Hadolint for Docker, Checkov for security
- All standards enforced via pre-commit hooks

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🆘 Support

For issues and questions:

- Create an issue on GitHub
- Check the documentation
- Review the API documentation at `/docs`

---

## Built with ❤️ for the developer community
