# Backend Setup Notes

This backend expects a Vault token to be provided through environment variables. The application fails fast if the token is missing outside development environments. Use the instructions below to run the stack locally and prepare other environments.

## Required Environment Variables

- `VAULT_DEV_ROOT_TOKEN_ID` – root token used by the Vault dev container. Only needed for development.
- `VAULT_TOKEN` – token the backend uses to talk to Vault. Required in every environment.

For local development you can use the same value for both variables.

## Local Development Workflow

1. **Pick a dev token** – e.g. `vault-dev-root-token-123`. Treat it as sensitive.
2. **Create a local env file** (ignored by git):
   ```bash
   cat > backend/.env.local <<'ENV'
   VAULT_DEV_ROOT_TOKEN_ID=vault-dev-root-token-123
   VAULT_TOKEN=vault-dev-root-token-123
   ENV
   ```
3. **Load the variables** before starting Docker:
   ```bash
   source backend/.env.local
   docker compose up
   ```
   The `vault` service will boot with `VAULT_DEV_ROOT_TOKEN_ID`, and the backend will read `VAULT_TOKEN`. If you skip `source`, export both variables manually in your shell.

When the backend starts it logs a warning if `ENVIRONMENT` is set to `development` and a placeholder token is being used. Any other environment without `VAULT_TOKEN` causes a `RuntimeError` during startup.

## Regenerating a Dev Token

If you want to rotate the dev token:

1. Stop the stack: `docker compose down`.
2. Update `VAULT_DEV_ROOT_TOKEN_ID` / `VAULT_TOKEN` in `backend/.env.local` (or your shell exports).
3. Start the stack again. The Vault dev container reinitializes itself with the new token.

## Non-Development Environments

- Provision `VAULT_TOKEN` via the platform’s secret manager (GitHub Actions Secrets, GitLab CI variables, AWS SSM, etc.).
- Inject the variable into the backend container (for Docker Compose use `environment:` entries, for Kubernetes use secrets/env vars, etc.).
- Do **not** rely on dev-mode defaults in production or staging.

### Creating a Token from an Existing Vault Instance

If you have access to a running Vault and its root token:

```bash
export VAULT_ADDR="https://your-vault-host"
vault login <root_token>
vault token create -policy=default -ttl=24h
```

Copy the `token` field from the command output and set it as `VAULT_TOKEN` in the target environment. Adjust policies and TTL to match your deployment requirements.

## Troubleshooting

- **Backend exits on startup with `RuntimeError: VAULT_TOKEN environment variable must be set`** – export `VAULT_TOKEN` (and `VAULT_DEV_ROOT_TOKEN_ID` when using the dev container) before launching.
- **Vault client warns about placeholder token** – you are in development mode without a token. Set real values to silence the warning if needed.
- **Need to inspect secrets** – with the dev token exported, you can run `vault kv list secret/` or other CLI commands within the `vault` container (`docker compose exec vault sh`).

Keep tokens out of version control and rotate them regularly.
