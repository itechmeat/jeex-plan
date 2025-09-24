# JEEX Plan - QWEN Development Context

## Project Overview

JEEX Plan is an AI-powered multi-agent documentation generation system that transforms raw ideas into professional Markdown documentation packages through AI-powered analysis. Built with a microservices architecture, it follows modern development practices with clear separation of concerns between frontend, backend, and supporting services.

The project implements a multi-agent system with specialized AI agents:
- Business Analyst: Extracts and structures project requirements
- Solution Architect: Designs technical architecture
- Project Planner: Creates implementation roadmaps
- Engineering Standards: Defines development guidelines

### Multi-Tenant Architecture

- **Tenant Isolation**: All data operations are scoped by `tenant_id`
- **Server-side Filtering**: Backend enforces tenant isolation, never client-side
- **Database Models**: Uses mixins (TenantMixin, TimestampMixin, SoftDeleteMixin)
- **Repository Pattern**: Automatic tenant filtering in all data access

## Architecture

### Core Services (Backend Only - No Frontend in Docker)

- **API Backend**: FastAPI with Python (Port 5210)
- **PostgreSQL**: Primary database with multi-tenant schema (Port 5220)
- **Qdrant**: Vector database for semantic search (Port 5230)
- **Redis**: Cache and message queue (Port 5240)
- **Vault**: Secrets management (Port 5250)
- **NGINX**: Reverse proxy with TLS
- **OpenTelemetry Collector**: Observability

### Multi-Tenant Architecture

- **Tenant Isolation**: All data operations are scoped by `tenant_id`
- **Server-side Filtering**: Backend enforces tenant isolation, never client-side
- **Database Models**: Uses mixins (TenantMixin, TimestampMixin, SoftDeleteMixin)
- **Repository Pattern**: Automatic tenant filtering in all data access

### Technology Stack
- **Backend**: Python 3.11+, FastAPI, SQLAlchemy, CrewAI, OpenTelemetry
- **Frontend**: React 18+, TypeScript, Vite, Tailwind CSS
- **Database**: PostgreSQL 18+, Qdrant vector database
- **Cache**: Redis 8.2+
- **Infrastructure**: Docker, Docker Compose, Nginx
- **Observability**: OpenTelemetry stack

## Building and Running

### Prerequisites
- Docker and Docker Compose
- Node.js 18+ (for local frontend development)
- Python 3.11+ (for local backend development)

### Quick Start
1. **Setup environment**:
   ```bash
   ./scripts/setup.sh
   ```
   This script creates directories, copies environment files, builds images, starts services, and initializes the database.

2. **Manual startup**:
   ```bash
   docker-compose up -d
   ```

3. **Access the application**:
   - Frontend: http://localhost:5200
   - API: http://localhost:5210
   - API Documentation: http://localhost:5210/docs

### Common Development Commands

#### Quick Start

```bash
# Start all services
make dev
# or
make up

# Check service status
make status

# View logs
make logs

# Health check all services
make health
```

#### Database Operations

```bash
# Apply migrations
make db-migrate

# Check migration status
make db-status

# Database shell
make db-shell

# Create new migration (inside container)
docker-compose exec api alembic revision --autogenerate -m "description"
```

#### Development Workflow

```bash
# Backend development (with hot reload in Docker)
make dev
make api-logs  # Follow API logs

# Frontend development (separate, not in Docker)
cd frontend
npm run dev  # Runs on port 5200

# Full rebuild
make rebuild

# Clean everything
make clean
```

#### Service Access

```bash
# API shell
make api-shell

# Redis CLI
make redis-cli

# Vault status
make vault-status

# Direct service URLs
# API: http://localhost:5210
# API Docs: http://localhost:5210/docs
# Qdrant: http://localhost:5230/
# Vault: http://localhost:5250/
```

#### Testing

```bash
# Run backend tests
docker-compose exec api pytest

# Run specific test
docker-compose exec api pytest tests/test_models.py

# Frontend tests
cd frontend
npm run test
```

### Development Commands

#### Using Makefile
The project includes a comprehensive Makefile with the following commands:
- `make up` - Start all services in detached mode
- `make down` - Stop all services
- `make restart` - Restart all services
- `make logs` - View logs from all services
- `make status` - Check container status
- `make health` - Perform health check on services
- `make clean` - Stop services and clean up Docker system
- `make rebuild` - Rebuild all services from scratch
- `make dev` - Start development environment
- `make prod` - Start production environment

#### Backend Development
```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload
```

#### Frontend Development
```bash
cd frontend
npm install
npm run dev
```

#### Database Migrations
```bash
cd backend
alembic upgrade head
alembic revision --autogenerate -m "description"
```

### Development Docker Compose
For development with hot reload capabilities, use:
```bash
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up -d
```

## Key Architecture Patterns

### Multi-Tenant Data Access

- All models inherit from `TenantMixin` (except `Tenant` itself)
- Repository classes automatically filter by `tenant_id`
- Database constraints ensure tenant isolation
- Example: `UserRepository.get_by_email()` only searches within tenant

### Database Schema

- **Base Models**: Located in `backend/app/models/base.py`
- **Core Models**: Tenant, User, Project, Document
- **Migrations**: Alembic with async SQLAlchemy support
- **Indexes**: Optimized for tenant-scoped queries

### API Structure

- **Authentication**: JWT with refresh tokens
- **Tenant Context**: Extracted from JWT and injected into repositories
- **Health Checks**: Comprehensive service monitoring
- **Error Handling**: Structured error responses

### Development Environment

- **Hot Reload**: Backend runs with `--reload` in development mode
- **Environment Variables**: Set `ENVIRONMENT=development` for dev features
- **Volumes**: Backend code mounted for instant updates
- **No Frontend in Docker**: Frontend runs separately via npm

### Secret Management

- **Vault Integration**: All secrets stored in HashiCorp Vault
- **Environment Variables**: Only for Vault connection
- **Rotation**: Automated JWT secret rotation
- **Development**: Auto-initialization of dev secrets

## Key Configuration Files

### Environment Variables
- `.env` - Main environment configuration
- `frontend/.env` - Frontend-specific environment variables

### Docker Compose Files
- `docker-compose.yml` - Production service definitions
- `docker-compose.dev.yml` - Development overrides with hot reload

### Configuration

- `.env` - Root environment variables for local development (no service-specific `.env` files)
- `frontend/.env` - Frontend environment variables
- `docker-compose.yml` - Service definitions
- `backend/alembic.ini` - Database migration config

### Core Application

- `backend/main.py` - FastAPI application entry point
- `backend/app/models/` - Database models with tenant isolation
- `backend/app/repositories/` - Data access layer
- `backend/app/core/database.py` - Database configuration
- `backend/app/core/vault.py` - Vault client and secret management

### Testing

- `backend/tests/` - Backend test suite
- `backend/tests/conftest.py` - Test configuration and fixtures
- Tests use async pytest and database fixtures

### Backend Dependencies
The backend uses FastAPI with the following main dependencies:
- CrewAI for multi-agent orchestration
- SQLAlchemy and Alembic for database management
- Qdrant client for vector database operations
- Redis for caching
- OpenTelemetry for observability
- Pydantic for data validation

### Frontend Dependencies
The frontend uses React with TypeScript and includes:
- React Router for navigation
- Axios for API communication
- Radix UI components for accessibility
- Lucide React for icons
- SASS for styling

## API Endpoints

### Authentication Endpoints
- `POST /api/v1/auth/login` - User login
- `POST /api/v1/auth/register` - User registration
- `POST /api/v1/auth/refresh` - Refresh token
- `GET /api/v1/auth/me` - Current user info

### Project Management
- `GET /api/v1/` - List projects
- `POST /api/v1/` - Create project
- `GET /api/v1/{project_id}` - Get project details
- `PUT /api/v1/{project_id}` - Update project
- `DELETE /api/v1/{project_id}` - Delete project

### Document Generation
- `POST /api/v1/{project_id}/step1` - Generate description
- `POST /api/v1/{project_id}/step2` - Generate architecture
- `POST /api/v1/{project_id}/step3` - Generate implementation plan
- `POST /api/v1/{project_id}/step4` - Generate standards
- `POST /api/v1/{project_id}/export` - Export documents

### Health Checks
- `GET /api/v1/health` - Comprehensive health check
- `GET /api/v1/health/simple` - Simple health check
- `GET /api/v1/health/ready` - Readiness probe
- `GET /api/v1/health/live` - Liveness probe

## Security Features

### Multi-tenancy
- Strict tenant isolation at all levels
- Database-level separation
- Vector database payload filtering
- Cache key namespacing
- Request context middleware

### Authentication & Authorization
- JWT tokens with refresh mechanism
- OAuth2 integration points
- Role-based access control (RBAC)
- Rate limiting per tenant/project
- API key management

### Data Protection
- TLS encryption for all communications
- Secret management with HashiCorp Vault
- Input validation and sanitization
- Structured logging with sensitive data filtering

## Monitoring & Observability

### OpenTelemetry
- Distributed tracing across all services
- Metrics collection and export
- Structured logging with correlation IDs

### Health Monitoring
- Service health endpoints
- Database connectivity checks
- Redis and Qdrant connectivity
- Vault secrets management

## Critical Development Rules

### Language Requirements (STRICT)

- **ALL project files MUST be written in English only** - including code, comments, documentation, variable names, function names, commit messages, and any text within the codebase
- **Exception**: Non-English markdown files that were originally created in another language should remain in their original language
- **Chat Communication**: ALWAYS respond in the same language the user is communicating in. If the user writes in any language other than English, respond in that exact language - this rule applies ONLY to project files remaining in English, not chat interactions
- **No Mixed Languages**: Never mix English and non-English in the same file

### Package Version Requirements (ABSOLUTE PRIORITY)

**NEVER downgrade package versions below the specifications in `docs/specs.md`. This is the strictest rule in the project.**

Required minimum versions from specs:

- **FastAPI**: 0.116.2+
- **CrewAI**: 0.186.1+
- **Pydantic AI**: 1.0.8+
- **PostgreSQL**: 18+
- **Qdrant**: 1.15.4+
- **Redis**: 8.2+
- **Tenacity**: 9.0+
- **OpenTelemetry**: 1.27+
- **textstat**: 0.7.0+
- **python-markdown**: 3.7+
- **Alembic**: 1.13+

When dependency conflicts occur, resolve by:

1. Finding compatible higher versions
2. Updating conflicting dependencies to newer versions
3. Never downgrading below specified minimums
4. If conflicts persist, follow this escalation process:
   - **First**: Use context7 MCP to research latest compatible versions and solutions
   - **Second**: Use web search to find recent compatibility information and workarounds
   - **Last resort**: Discuss with user before making any changes

## Development Conventions

1. **Code Structure**:
   - Backend code is organized in the `app/` directory with API routes, core logic, and models
   - Frontend code follows component-based architecture with pages, components, and hooks

2. **Testing**:
   - Unit and integration tests in the respective `tests/` directories
   - Use pytest for backend testing
   - Component testing for frontend

3. **Documentation**:
   - API documentation automatically generated via FastAPI
   - Inline code documentation following Python and TypeScript conventions

4. **Environment Management**:
   - Use environment-specific configurations
   - Never commit sensitive data to version control
   - Use Vault for secrets in production

### Multi-Tenancy Rules

- Never access data without tenant context
- All database queries must include tenant filtering
- Vector search payloads must include tenant metadata
- Cache keys must be namespaced by tenant

### Hot Reload Setup

- Backend automatically reloads on code changes in development
- Dockerfile uses conditional command based on `ENVIRONMENT` variable
- Volume mount: `./backend:/app` enables instant updates

### Database Migrations

- Always test migrations in development first
- Use descriptive migration messages
- Verify tenant isolation after schema changes
- Check for proper indexes on tenant_id columns

### Error Handling

- Use structured logging with correlation IDs
- Return tenant-safe error messages
- Implement proper HTTP status codes
- Log security events (failed auth, tenant boundary violations)

## Code Quality and Development Standards

### Git Operations (STRICT)

- **NEVER execute git commands** (git add, git commit, git push, etc.), but you can execute git diff and git status.
- **User handles all git operations manually**
- Claude Code should focus only on code implementation, never version control

### Production Code Requirements (ABSOLUTE)

- **NEVER use hardcoded values, mocks, stubs, or placeholders in production code**
- **All code must be real, functional implementations with actual integrations**
- **If an error occurs, display the actual error - no fallbacks or fake responses**
- **No "TODO", "FIXME", or placeholder comments in production code**

### Docker-First Development (MANDATORY)

- **ALL backend work must be performed inside Docker containers**
- **Execute scripts, commands, and development tasks within Docker environment**
- **Frontend must work outside Docker** (runs via npm/pnpm on host)
- **Use `docker-compose exec` for backend operations**

### Code Architecture Principles (STRICT)

- **Follow DRY (Don't Repeat Yourself) principle**

  - Extract reusable code into utilities, libraries, helpers, or separate files
  - Avoid code duplication across modules
  - Create shared components for common functionality

- **Adhere to SOLID principles when writing code:**
  - **Single Responsibility**: Each class/function has one reason to change
  - **Open/Closed**: Open for extension, closed for modification
  - **Liskov Substitution**: Derived classes must be substitutable for base classes
  - **Interface Segregation**: No code should depend on methods it doesn't use
  - **Dependency Inversion**: Depend on abstractions, not concretions

### Prompt Engineering Standards (CRITICAL)

- **NEVER hardcode specific examples, queries, or responses in LLM prompts**
- **Prompts must be universal and work for any input**
- **Use general patterns and rules, not specific case examples**
- **Design prompts that adapt to different contexts and inputs**
- **Avoid embedding specific domain knowledge in prompt templates**

## Development Notes

### Multi-Tenancy Rules

- Never access data without tenant context
- All database queries must include tenant filtering
- Vector search payloads must include tenant metadata
- Cache keys must be namespaced by tenant

### Hot Reload Setup

- Backend automatically reloads on code changes in development
- Dockerfile uses conditional command based on `ENVIRONMENT` variable
- Volume mount: `./backend:/app` enables instant updates

### Database Migrations

- Always test migrations in development first
- Use descriptive migration messages
- Verify tenant isolation after schema changes
- Check for proper indexes on tenant_id columns

### Error Handling

- Use structured logging with correlation IDs
- Return tenant-safe error messages
- Implement proper HTTP status codes
- Log security events (failed auth, tenant boundary violations)

## Troubleshooting

### Health Checks
Run the health check script to verify all services are running:
```bash
./scripts/health-check.sh
```

Or check individual endpoints:
- API Health: http://localhost:5210/api/v1/health
- Frontend: http://localhost:5200

### Common Issues
- Ensure Docker has sufficient resources allocated (at least 4GB RAM)
- Check environment variables are properly set
- Verify network connectivity between services
- Monitor logs with `docker-compose logs -f [service]`

## Project Directories

- `/backend` - Python FastAPI application with AI agents
- `/frontend` - React + TypeScript SPA
- `/docs` - Project documentation
- `/nginx` - Nginx configuration for reverse proxy
- `/scripts` - Utility scripts for setup and maintenance
- `/htmlcov` - HTML coverage reports