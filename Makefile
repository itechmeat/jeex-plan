.PHONY: up down restart logs status health clean dev prod rebuild lint lint-fix format check pre-commit docker-lint security-scan sql-lint sql-fix markdown-lint markdown-fix frontend-lint backend-lint frontend-fix backend-fix

# Development commands
dev:
	docker-compose up -d

up:
	docker-compose up -d

down:
	docker-compose down

restart:
	docker-compose restart

# Monitoring commands
logs:
	docker-compose logs -f

status:
	docker-compose ps

health:
	@echo "Checking service health..."
	@curl -s http://localhost:5210/api/v1/health | jq .status || echo "API not responding"
	@curl -s http://localhost:5250/v1/sys/health | jq .initialized || echo "Vault not responding"
	@curl -s http://localhost:5230/ | jq .title || echo "Qdrant not responding"

# Maintenance commands
clean:
	docker-compose down -v
	docker system prune -f

rebuild:
	docker-compose down
	docker-compose build --no-cache
	docker-compose up -d

# Database commands
db-migrate:
	docker-compose exec api alembic upgrade head

db-status:
	docker-compose exec api alembic current

db-shell:
	docker-compose exec postgres psql -U postgres -d jeex_plan

# Development shortcuts
api-logs:
	docker-compose logs -f api

api-shell:
	docker-compose exec api bash

# Redis CLI - requires REDIS_PASSWORD environment variable
# Set REDIS_PASSWORD in your environment or source the root .env/.env.local first
redis-cli:
	docker-compose exec redis redis-cli -a ${REDIS_PASSWORD}

vault-status:
	docker-compose exec vault vault status

# Linting and formatting commands for entire project
lint:
	@echo "🔍 Running all linting checks..."
	@$(MAKE) frontend-lint
	@$(MAKE) backend-lint
	@$(MAKE) sql-lint
	@$(MAKE) docker-lint
	@$(MAKE) markdown-lint
	@echo "✅ All lint checks completed"

frontend-lint:
	@echo "📝 Checking frontend (JS/TS + CSS)..."
	cd frontend && pnpm run lint

frontend-fix:
	@echo "📝 Fixing frontend..."
	cd frontend && pnpm run lint:fix

backend-fix:
	@echo "🗃️ Fixing backend SQL..."
	docker-compose exec api python -m sqlfluff fix .
	@echo "🐍 Fixing backend Python..."
	docker-compose exec api python -m ruff check app --fix --extend-ignore E501,B904,BLE001,G201,ANN001,ANN002,ANN003,ANN201,ANN202,ANN205,RUF012,S101,S104,S105,S107,SIM102,SIM103,UP038,C901,RUF001

backend-lint:
	@echo "🗃️ Checking backend SQL..."
	docker-compose exec api python -m sqlfluff lint .
	@echo "🐍 Checking backend (Python)..."
	docker-compose exec api python -m ruff check app --extend-ignore E501,B904,BLE001,G201,ANN001,ANN002,ANN003,ANN201,ANN202,ANN205,RUF012,S101,S104,S105,S107,SIM102,SIM103,UP038,C901,RUF001

lint-fix:
	@echo "🔧 Fixing all linting issues..."
	@$(MAKE) frontend-fix
	@echo "📋 Fixing markdown..."
	npx markdownlint-cli2 --fix
	@$(MAKE) backend-fix

format:
	@echo "✨ Formatting all code..."
	@echo "📝 Formatting frontend..."
	cd frontend && pnpm run format
	@echo "🐍 Formatting backend..."
	docker-compose exec api ruff format .

check:
	@echo "🔍 Running type checks..."
	@echo "📝 TypeScript checking..."
	cd frontend && pnpm run type-check
	@echo "🐍 Python type checking..."
	docker-compose exec api mypy app/

# Docker linting commands
docker-lint:
	@echo "🐳 Running Docker file linting..."
	@echo "  • Checking backend/Dockerfile..."
	docker run --rm -v $(PWD)/.hadolint.yaml:/.config/hadolint.yaml -i hadolint/hadolint < backend/Dockerfile
	@echo "  • Checking backend/Dockerfile.simple..."
	docker run --rm -v $(PWD)/.hadolint.yaml:/.config/hadolint.yaml -i hadolint/hadolint < backend/Dockerfile.simple
	@echo "✅ Docker linting completed!"

# Security scanning with Checkov
security-scan:
	@echo "🔒 Running security scan with Checkov..."
	docker run --rm -v $(PWD):/tf bridgecrew/checkov -d /tf --framework dockerfile --quiet
	@echo "✅ Security scan completed!"

# SQL linting commands
sql-lint:
	@echo "🗃️ Running SQL linting..."
	docker-compose exec api python -m sqlfluff lint .
	@echo "✅ SQL linting completed!"

sql-fix:
	@echo "🗃️ Fixing SQL issues..."
	docker-compose exec api python -m sqlfluff fix .
	@echo "✅ SQL fixes completed!"

# Markdown linting commands
markdown-lint:
	@echo "📋 Running markdown linting..."
	npx markdownlint-cli2
	@echo "✅ Markdown linting completed!"

markdown-fix:
	@echo "📋 Fixing markdown issues..."
	npx markdownlint-cli2 --fix
	@echo "✅ Markdown fixes completed!"

# Pre-commit checks for entire project
pre-commit:
	@bash .github/hooks/pre-commit
