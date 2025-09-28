# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

JEEX Plan is a multi-agent documentation generation system that transforms raw ideas into professional Markdown documentation packages through AI-powered analysis. It uses a microservices architecture with strict multi-tenant isolation.

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

## Common Development Commands

### Quick Start

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

### Database Operations

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

### Development Workflow

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

### Service Access

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

### Testing

```bash
# Run backend tests
docker-compose exec api pytest

# Run specific test
docker-compose exec api pytest tests/test_models.py

# Frontend tests
cd frontend
npm run test
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

## Important Files

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

### Testing Resources

- `backend/tests/` - Backend test suite
- `backend/tests/conftest.py` - Test configuration and fixtures
- Tests use async pytest and database fixtures

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

## Code Quality and Development Standards

### Git Operations (STRICT)

- **NEVER execute git commands** (git add, git commit, git push, etc.), but you can execute git diff and git status.
- **User handles all git operations manually**
- Claude Code should focus only on code implementation, never version control

### Editor Settings (ABSOLUTE)

- **NEVER create or modify .vscode/settings.json files in subfolders** (frontend/.vscode/, backend/.vscode/, etc.)
- **NEVER create or modify .editorconfig files in subfolders** (frontend/.editorconfig, backend/.editorconfig, etc.)
- **ONLY modify editor settings in the ROOT .vscode/settings.json file**
- **ONLY modify .editorconfig in the ROOT of the project**
- **All editor configuration must be centralized in the project root**
- **Subfolders MUST NOT contain ANY editor-specific configuration files**

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

### Documentation Standards (STRICT)

- **ALL main documentation MUST be in the root README.md** - project overview, setup, commands, architecture
- **Subdirectory README files are ONLY for subdirectory-specific details** - not project-wide information
- **frontend/README.md** - Only frontend-specific setup and development (no backend, Docker, or project overview)
- **backend/README.md** - Only backend-specific details (if needed)
- **.github/hooks/README.md** - Only git hooks technical details (no project overview or general commands)
- **NEVER duplicate project-wide information** across multiple README files
- **Root README.md is the single source of truth** for project documentation
