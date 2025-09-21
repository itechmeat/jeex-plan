# Repository Guidelines

## Project Structure & Module Organization

Keep canonical context in `docs/` (current `about.md`, `architecture.md`). Implement the wizard UI under `apps/frontend` (React + Vite + TypeScript); expose API services in `services/api` (FastAPI) with dependency-injected gateways for PostgreSQL, Redis, and Qdrant. Maintain Crew AI role definitions and prompt contracts inside `agents/`, reusing validation models from `packages/schemas`. Mirror every runtime module in `tests/` (e.g. `tests/frontend`, `tests/api`) and keep deployment assets in `infra/` for Docker Compose, Terraform, and monitoring configs.

## Build, Test, and Development Commands

Run `pnpm install && pnpm dev` inside `apps/frontend` to serve the four-step wizard locally. Start the backend with `uvicorn services.api.main:app --reload` after exporting `.env` secrets. Execute `pytest` for unit and service tests, and `pytest -m integration` when containers for Postgres/Qdrant/Redis are available. Use `docker compose -f infra/compose.yml up --build` to exercise the full stack with SSE streaming.

## Coding Style & Naming Conventions

Adopt TypeScript strict mode, 2-space indentation, camelCase functions, PascalCase components, and colocated CSS modules. Python modules use 4-space indentation, type hints, and `ruff`/`black` (line length 100) before committing. Keep markdown outputs in English, wrap prose at ~100 characters, and prefer filename patterns like `description.md` and `rules.md` by tenant/project.

## Testing Guidelines

Target ≥80% line coverage for backend services and ≥70% for frontend components; track via `pytest --cov` and `pnpm test -- --coverage`. Name Python tests `test_<feature>.py` and scope agent contracts under `tests/agents/test_<agent>.py`. Frontend specs live alongside components as `<Component>.spec.tsx`. Record new fixtures in `tests/fixtures/` and refresh seeded embeddings whenever schema payloads change.

## Commit & Pull Request Guidelines

The history is clean so far; follow Conventional Commits (`feat:`, `fix:`, `docs:`) to keep automation simple. Reference the related document or issue in the body, note migrations or schema bumps explicitly, and attach before/after screenshots for UI work. Pull requests should describe tenant-isolation impacts, list manual verification steps, and tag reviewers responsible for adjacent agents or infrastructure.

## Security & Configuration Tips

Never commit `.env` or downloaded archives; share through the secret manager noted in `docs/architecture.md`. Keep per-tenant isolation by enforcing `tenant_id` and `project_id` filters in every Qdrant/query interface. Validate agent outputs against Pydantic schemas before persistence, and enable OpenTelemetry exporters in local stacks when debugging cross-agent flows.
