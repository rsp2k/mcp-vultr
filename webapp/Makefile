# Service Collection Webapp Management
.PHONY: help build up down logs clean dev prod restart backend frontend worker db migrate \
        ssl-check caddy-reload caddy-logs caddy-validate ssl-renew network-check \
        emergency-stop emergency-restart monitor logs-all security-check health-check \
        quick-dev quick-prod

# Default environment
ENV ?= development

help: ## Show this help message
	@echo "Service Collection Webapp Commands:"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'

# Development Commands
dev: ## Start development environment with hot reload
	@echo "🚀 Starting development environment..."
	@DEV_MODE=true docker compose up --build -d
	@echo "⏳ Waiting for services to start..."
	@sleep 5
	@make health-check
	@echo "✅ Development environment started"
	@echo "📊 Dashboard: https://$${DOMAIN:-mcp-vultr.l.supported.systems}"
	@echo "🔧 API: https://api.$${DOMAIN:-mcp-vultr.l.supported.systems}"
	@echo "🗄️  PgAdmin: https://admin.$${DOMAIN:-mcp-vultr.l.supported.systems}"

prod: ## Start production environment
	@echo "🚀 Starting production environment..."
	@DEV_MODE=false docker compose up --build -d
	@echo "⏳ Waiting for services to start..."
	@sleep 10
	@make health-check
	@make ssl-check
	@echo "✅ Production environment started"

up: ## Start all services
	docker compose up -d

down: ## Stop all services
	docker compose down

restart: ## Restart all services
	docker compose restart

build: ## Build all images
	docker compose build

logs: ## Show logs for all services
	docker compose logs -f

# Individual Service Commands
backend: ## Start only backend services (API + Worker + DB)
	docker compose up -d postgres backend worker

frontend: ## Start only frontend
	docker compose up -d frontend

worker: ## Start only background worker
	docker compose up -d worker

db: ## Start only database
	docker compose up -d postgres

# Database Commands
migrate: ## Run database migrations
	docker compose exec backend python -m alembic upgrade head

migrate-create: ## Create new migration (usage: make migrate-create MESSAGE="description")
	docker compose exec backend python -m alembic revision --autogenerate -m "$(MESSAGE)"

db-reset: ## Reset database (WARNING: destroys all data)
	@echo "⚠️  This will destroy all database data. Are you sure? [y/N]" && read ans && [ $${ans:-N} = y ]
	docker compose down postgres
	docker volume rm mcp-vultr-webapp_postgres_data
	docker compose up -d postgres

# Development Tools
shell-backend: ## Open shell in backend container
	docker compose exec backend bash

shell-frontend: ## Open shell in frontend container
	docker compose exec frontend sh

shell-db: ## Open PostgreSQL shell
	docker compose exec postgres psql -U service_collections -d service_collections

# Monitoring & Debugging
status: ## Show status of all services
	docker compose ps

health: ## Check health of all services
	@echo "🏥 Service Health Check:"
	@docker compose ps --format "table {{.Name}}\t{{.Status}}\t{{.Ports}}"

health-check: ## Internal health check (used by other commands)
	@echo "🏥 Checking service health..."
	@docker compose ps --format "table {{.Name}}\t{{.Status}}" | grep -v "Up" | grep -v "NAME" | wc -l | xargs -I {} sh -c 'if [ {} -gt 0 ]; then echo "⚠️  Some services are not running properly"; docker compose ps; else echo "✅ All services running"; fi'

logs-backend: ## Show backend logs
	docker compose logs -f backend

logs-frontend: ## Show frontend logs
	docker compose logs -f frontend

logs-worker: ## Show worker logs
	docker compose logs -f worker

logs-db: ## Show database logs
	docker compose logs -f postgres

# Cleanup Commands
clean: ## Clean up containers and images
	docker compose down --volumes --rmi local

clean-all: ## Clean up everything including volumes
	docker compose down --volumes --rmi all
	docker volume prune -f

# Production Deployment
deploy: ## Deploy to production (builds and starts prod environment)
	@echo "🚀 Deploying to production..."
	@git pull origin main
	@DEV_MODE=false docker compose pull
	@DEV_MODE=false docker compose up --build -d
	@echo "✅ Production deployment complete"

# Backup & Restore
backup-db: ## Backup database
	@mkdir -p backups
	@docker compose exec postgres pg_dump -U service_collections service_collections > backups/backup_$(shell date +%Y%m%d_%H%M%S).sql
	@echo "✅ Database backup created in backups/"

restore-db: ## Restore database from backup (usage: make restore-db BACKUP=backup_file.sql)
	@if [ -z "$(BACKUP)" ]; then echo "Usage: make restore-db BACKUP=backup_file.sql"; exit 1; fi
	@docker compose exec -T postgres psql -U service_collections -d service_collections < $(BACKUP)
	@echo "✅ Database restored from $(BACKUP)"

# Testing
test: ## Run all tests
	docker compose exec backend python -m pytest tests/ -v

test-backend: ## Run backend tests only
	docker compose exec backend python -m pytest tests/backend/ -v

test-integration: ## Run integration tests
	docker compose exec backend python -m pytest tests/integration/ -v

# Initial Setup
# SSL & Reverse Proxy Management
ssl-check: ## Check SSL certificate status
	@echo "🔒 Checking SSL certificate status..."
	@echo "Certificate info for $${DOMAIN:-mcp-vultr.l.supported.systems}:"
	@timeout 10 openssl s_client -connect $${DOMAIN:-mcp-vultr.l.supported.systems}:443 -servername $${DOMAIN:-mcp-vultr.l.supported.systems} 2>/dev/null | openssl x509 -noout -dates 2>/dev/null || echo "❌ SSL check failed (certificate may be pending)"

caddy-reload: ## Reload Caddy configuration
	@echo "🔄 Reloading Caddy configuration..."
	@docker compose exec caddy caddy reload --config /etc/caddy/Caddyfile

caddy-logs: ## Show Caddy logs
	@docker compose logs -f caddy

caddy-validate: ## Validate Caddyfile syntax
	@echo "✅ Validating Caddyfile syntax..."
	@docker compose exec caddy caddy validate --config /etc/caddy/Caddyfile

ssl-renew: ## Force SSL certificate renewal
	@echo "🔄 Forcing SSL certificate renewal..."
	@docker compose exec caddy caddy reload --config /etc/caddy/Caddyfile

# Network & Connectivity
network-check: ## Check network connectivity between services
	@echo "🌐 Checking network connectivity..."
	@echo "Backend to Postgres:"
	@docker compose exec backend ping -c 1 postgres || echo "❌ Backend cannot reach Postgres"
	@echo "Frontend to Backend:"
	@docker compose exec frontend wget -q --spider http://backend:8000/health || echo "❌ Frontend cannot reach Backend"
	@echo "Caddy to Backend:"
	@docker compose exec caddy wget -q --spider http://backend:8000/health || echo "❌ Caddy cannot reach Backend"
	@echo "Caddy to Frontend:"
	@docker compose exec caddy wget -q --spider http://frontend:80 || echo "❌ Caddy cannot reach Frontend"

# Emergency Commands
emergency-stop: ## Emergency stop - kill all containers
	@echo "🚨 Emergency stop - killing all containers..."
	@docker compose kill

emergency-restart: ## Emergency restart
	@echo "🚨 Emergency restart..."
	@make emergency-stop
	@sleep 2
	@make prod

# Enhanced Monitoring
monitor: ## Monitor services in real-time
	@echo "📊 Starting real-time service monitoring..."
	@watch -n 2 'make status && echo "" && docker stats --no-stream'

logs-all: ## Show all logs with timestamps
	@docker compose logs --timestamps

# Security
security-check: ## Basic security check
	@echo "🔐 Running basic security checks..."
	@echo "Checking for exposed ports:"
	@docker compose ps --format "table {{.Name}}\t{{.Ports}}" | grep "0.0.0.0"
	@echo ""
	@echo "Checking Caddy security headers:"
	@timeout 10 curl -s -I https://$${DOMAIN:-mcp-vultr.l.supported.systems} | grep -E "(Strict-Transport-Security|X-Frame-Options|X-Content-Type-Options)" || echo "⚠️  Some security headers missing"

# Initial Setup
setup: ## Initial project setup
	@echo "🔧 Setting up Service Collection Webapp..."
	@docker compose build
	@docker compose up -d postgres
	@echo "⏳ Waiting for database..."
	@sleep 10
	@docker compose exec backend python -m alembic upgrade head
	@echo "✅ Setup complete! Run 'make dev' to start development environment"

# Quick deployment helpers
quick-dev: ## Quick development start (build + migrate + start)
	@make dev
	@make migrate
	@echo "🚀 Development environment ready!"

quick-prod: ## Quick production deployment (build + migrate + start + ssl check)
	@make prod
	@make migrate
	@make ssl-check
	@echo "🌟 Production environment deployed!"