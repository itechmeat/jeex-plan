# JEEX Plan Agent Guidelines

## Mission

- Transform raw user ideas into production-ready Markdown documentation packages.
- Uphold strict multi-tenant isolation and security boundaries across all workflows.
- Coordinate with backend services, data stores, and infrastructure using the patterns described below.

## System Architecture Snapshot

- **API Backend**: FastAPI service (port 5210) orchestrating agent workflows.
- **PostgreSQL**: Multi-tenant relational store (port 5220) with tenant-aware mixins.
- **Qdrant**: Vector database (port 5230) for semantic retrieval of tenant-scoped content.
- **Redis**: Cache and queue broker (port 5240) for coordination and rate control.
- **Vault**: Secrets manager (port 5250) for all credentials; local `.env` files only hold Vault access.
- **NGINX & OpenTelemetry**: Reverse proxy with TLS termination and observability pipeline.

## Multi-Tenant Operating Rules

- Every operation must include `tenant_id` (and `project_id` where applicable) from request context.
- Repository classes and vector payloads already enforce tenant scoping—never bypass them.
- Cache keys, logs, and telemetry data must carry tenant identifiers to avoid cross-tenant leakage.
- Maintain soft-delete and timestamp conventions supplied by `TenantMixin`, `TimestampMixin`, and `SoftDeleteMixin`.

## Preferred Development Workflow

```bash
make dev          # Launch core backend services with hot reload
make up           # Bootstrap full docker environment
make status       # Verify container health
make logs         # Stream aggregated service logs
make api-logs     # Follow API-specific events
make clean        # Reset development artifacts

cd frontend
npm run dev       # Run standalone frontend (Port 5200, outside Docker)
```

## Database Operations

```bash
make db-migrate   # Apply pending migrations
make db-status    # Inspect migration history
make db-shell     # Open a database shell

# Create a migration from inside the API container
docker-compose exec api alembic revision --autogenerate -m "description"
```

## Service Access Shortcuts

```bash
make api-shell    # Interactive FastAPI shell
make redis-cli    # Redis CLI inside container
make vault-status # Check Vault readiness
# Direct URLs
# API:        http://localhost:5210
# API Docs:   http://localhost:5210/docs
# Qdrant UI:  http://localhost:5230/
# Vault UI:   http://localhost:5250/
```

## Testing Expectations

- Execute `docker-compose exec api pytest` for backend suites; target ≥80% line coverage.
- Use `docker-compose exec api pytest tests/test_models.py` for focused runs.
- Run `cd frontend && pnpm run test` for UI coverage (≥70%).
- Prefer async pytest patterns and reuse fixtures from `backend/tests/conftest.py`.

## Secret Handling & Observability

- Store all secrets in Vault; never hardcode credentials or persist them in source control.
- Use the root-level `.env` for local development overrides; do not create `backend/.env` files.
- When debugging cross-agent flows, enable OpenTelemetry exporters within the local stack.
- Regenerate embeddings and fixtures under `tests/fixtures/` whenever schema payloads evolve.

## Language & Documentation Rules (Strict)

- Author all repository files—code, prompts, docs—in English. Chat responses may mirror user language.
- Do not introduce multilingual content into single files; maintain consistent English terminology.

## Development Conduct Restrictions

- Never execute git commands; source control operations remain manual.
- Avoid hardcoded values, placeholders, or mocked data in production modules.
- Expose real error messages; do not fabricate fallbacks or mask failures.
- Keep prompts generic and reusable—no embedded domain-specific exemplars.
- Adhere to DRY and SOLID principles when extending or refactoring agents and services.

## Dependency & Version Policy

- Respect minimum versions documented in `docs/specs.md` (e.g., FastAPI ≥0.116.2, CrewAI ≥0.186.1).
- Resolve conflicts by upgrading related packages; never downgrade below mandated baselines.

## Environment Notes

- Backend work executes inside Docker containers; use `docker-compose exec` for shell access.
- Frontend development runs locally via npm/pnpm, independent of Docker.
- Set `ENVIRONMENT=development` to unlock dev tooling and hot reload inside containers.
