.DEFAULT_GOAL := help
COMPOSE := docker compose -p irp-dev -f deploy/docker-compose.dev.yml
UV := uv --project backend

.PHONY: help
help: ## 显示可用命令
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) \
		| awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-16s\033[0m %s\n", $$1, $$2}'

.PHONY: up
up: ## 启动本地基础设施（Postgres/Redis/MinIO）
	$(COMPOSE) up -d
	$(COMPOSE) ps

.PHONY: down
down: ## 停止基础设施（保留数据卷）
	$(COMPOSE) down

.PHONY: clean
clean: ## 停止并删除数据卷
	$(COMPOSE) down -v

.PHONY: env
env: ## 从模板生成 backend/.env（已存在则跳过）
	@test -f backend/.env || (cp backend/.env.example backend/.env && echo "已生成 backend/.env")

.PHONY: install
install: env ## 安装前后端依赖
	$(UV) sync --extra dev --extra ocr
	cd frontend && pnpm install

.PHONY: migrate
migrate: ## 执行数据库迁移到最新版本
	cd backend && uv run alembic upgrade head

.PHONY: seed
seed: ## 写入开发种子数据
	cd backend && uv run python -m scripts.seed

.PHONY: api
api: ## 启动后端开发服务器
	cd backend && uv run uvicorn app.main:app --reload --port 8000

.PHONY: worker
worker: ## 启动 Celery worker
	cd backend && uv run celery -A app.worker.celery_app worker -Q ingest,embed,stats -l info

.PHONY: web
web: ## 启动前端开发服务器
	cd frontend && pnpm dev

.PHONY: test
test: ## 运行后端测试
	cd backend && uv run pytest

.PHONY: lint
lint: ## 静态检查（ruff + mypy + eslint + tsc）
	cd backend && uv run ruff check . && uv run ruff format --check . && uv run mypy app
	cd frontend && pnpm lint && pnpm typecheck

.PHONY: fmt
fmt: ## 自动格式化
	cd backend && uv run ruff check --fix . && uv run ruff format .
	cd frontend && pnpm format

.PHONY: openapi
openapi: ## 从后端导出 OpenAPI 并生成前端类型
	cd backend && uv run python -m scripts.export_openapi
	cd frontend && pnpm gen:api

.PHONY: bootstrap
bootstrap: up install migrate seed openapi ## 一键初始化开发环境
	@echo "环境就绪：make api / make web"
