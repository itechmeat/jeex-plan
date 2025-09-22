.PHONY: up down restart logs status health clean dev prod rebuild

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
# Set REDIS_PASSWORD in your environment or source backend/.env first
redis-cli:
	docker-compose exec redis redis-cli -a ${REDIS_PASSWORD}

vault-status:
	docker-compose exec vault vault status