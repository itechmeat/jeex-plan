# JEEX Plan Agent Guidelines

## Mission

- Transform raw user ideas into production-ready Markdown documentation packages.
- Uphold strict multi-tenant isolation and security boundaries across all workflows.
- Coordinate with backend services, data stores, and infrastructure using the patterns described below.

## System Architecture Snapshot

- **API Backend**: FastAPI service (port 5210) orchestrating agent workflows
- **PostgreSQL**: Multi-tenant relational store (port 5220) with tenant-aware mixins
- **Qdrant**: Vector database (port 5230) for semantic retrieval of tenant-scoped content
- **Redis**: Cache and queue broker (port 5240) for coordination and rate control
- **Vault**: Secrets manager (port 5250) for all credentials; local `.env` files only hold Vault access
- **NGINX & OpenTelemetry**: Reverse proxy with TLS termination and observability pipeline

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
pnpm run dev       # Run standalone frontend (Port 5200, outside Docker)
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

- Execute `docker-compose exec api pytest` for backend suites; target ≥80% line coverage
- Use `docker-compose exec api pytest tests/test_models.py` for focused runs
- Run `cd frontend && pnpm run test` for UI coverage (≥70%)
- Run `cd tests && pnpm run test` for E2E test suites (Playwright)
- Use `cd tests && pnpm run test -- auth.spec.ts` for focused E2E scenarios
- Prefer async pytest patterns and reuse fixtures from `backend/tests/conftest.py`

## Secret Handling & Observability

- Store all secrets in Vault; never hardcode credentials or persist them in source control
- Use the root-level `.env` for local development overrides; do not create `backend/.env` files
- When debugging cross-agent flows, enable OpenTelemetry exporters within the local stack
- Regenerate embeddings and fixtures under `tests/fixtures/` whenever schema payloads evolve

## Language & Documentation Rules (Strict)

- Author all repository files—code, prompts, docs—in English. Chat responses may mirror user language
- Do not introduce multilingual content into single files; maintain consistent English terminology

## Development Conduct Restrictions

### Git Operations

- Never execute git commands; source control operations remain manual

### Production Code: NO FALLBACKS, MOCKS, OR STUBS (ZERO TOLERANCE)

**This is the most critical rule.** Better to have explicit TODO than hidden fallback

#### ❌ ABSOLUTELY PROHIBITED in Production Code

##### 1. Fallback Logic

```python
# ❌ WRONG - Default tenant fallback
if not tenant_id:
    tenant_id = get_default_tenant()  # PROHIBITED!

# ❌ WRONG - String conversion fallback
def serialize(value: Any) -> str:
    return str(value)  # Lossy, hides errors

# ❌ WRONG - OR operator fallback
value = data.get("key") or "default_value"
```

##### 2. Mock/Stub Implementations

```python
# ❌ WRONG - Stub that pretends to work
async def send_notification(user_id: str, message: str):
    logger.info(f"Notification sent to {user_id}")  # Not actually sending!
    return True
```

##### 3. Placeholder Values

```python
# ❌ WRONG - Hardcoded placeholder
API_KEY = "placeholder-key-replace-me"
DATABASE_URL = "postgresql://localhost/mydb"
```

##### 4. Generic Error Messages

```python
# ❌ WRONG - Lost original error
except Exception:
    return {"error": "Operation failed"}  # Where's the actual error?
```

#### ✅ REQUIRED Patterns

##### 1. Explicit Requirements (No Defaults)

```python
# ✅ CORRECT - tenant_id is REQUIRED
async def process_document(tenant_id: UUID, doc_id: UUID) -> Document:
    if not tenant_id:
        raise HTTPException(400, "tenant_id is required")
    # Real implementation...
```

##### 2. Strict Type Checking

```python
# ✅ CORRECT - Fail fast on unsupported types
def serialize_for_cache(value: Any) -> str:
    if isinstance(value, (str, int, float, bool, type(None))):
        return value
    raise TypeError(f"Cannot serialize {type(value).__name__}")
```

##### 3. Real Implementations

```python
# ✅ CORRECT - Actual API call
async def send_notification(user_id: str, message: str) -> bool:
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{settings.NOTIFICATION_API}/send",
            json={"user_id": user_id, "message": message}
        )
        response.raise_for_status()
        return True
```

##### 4. Preserve Original Errors

```python
# ✅ CORRECT - Don't hide errors
except HTTPException:
    raise  # Re-raise HTTP exceptions as-is
except Exception as e:
    logger.error("Processing failed", error=str(e), exc_info=True)
    raise  # Preserve original exception
```

#### ✅ ALLOWED (Better Explicit than Hidden)

##### TODO/FIXME Comments for Unimplemented Features

```python
# ✅ ALLOWED - Explicit TODO
async def send_sms(phone: str, message: str) -> bool:
    # TODO: Implement Twilio SMS integration
    raise NotImplementedError("SMS service not yet implemented")
```

**Principle**: Explicit `TODO` > Hidden fallback/mock

#### 🚫 ENFORCEMENT Rules

1. **tenant_id**: Always REQUIRED (UUID, never Optional, never None)
2. **No default tenant**: No creation, no fallback, no "default" slug
3. **No mocks/stubs**: Outside test directories (`tests/`, `__tests__/`)
4. **No placeholders**: Use environment variables and config
5. **TODO/FIXME**: Allowed for genuinely unimplemented features
6. **All implementations**: Production-ready OR explicitly marked TODO
7. **All errors**: Preserve full context and stack traces

#### 🔍 EXCEPTIONS (Legitimate Architectural Patterns)

These fallbacks are **ALLOWED** as proper multi-tier architecture

- ✅ **Vault → Environment variables** (secrets management hierarchy)
- ✅ **JWT → Headers** (dev/test authentication fallback)
- ✅ **Tenant ID → IP address** (rate limiting for anonymous requests)
- ✅ **Primary → Replica** (database/service failover)

### Other Restrictions

- Keep prompts generic and reusable—no embedded domain-specific exemplars
- Adhere to DRY and SOLID principles when extending or refactoring agents and services

## Dependency & Version Policy

- Respect minimum versions documented in `docs/specs.md` (e.g., FastAPI ≥0.116.2, CrewAI ≥0.186.1)
- Resolve conflicts by upgrading related packages; never downgrade below mandated baselines

## Environment Notes

- Backend work executes inside Docker containers; use `docker-compose exec` for shell access
- Frontend development runs locally via pnpm, independent of Docker
- Set `ENVIRONMENT=development` to unlock dev tooling and hot reload inside containers
