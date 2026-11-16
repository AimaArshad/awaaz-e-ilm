.PHONY: dev dev-local test lint fmt migrate seed clean

dev:
	docker compose up --build

dev-local:
	@echo "Starting backend..."
	cd backend && uvicorn app.main:app --reload --port 8000 &
	@echo "Starting frontend..."
	cd frontend && npm run dev

test:
	@echo "Running backend tests..."
	cd backend && python -m pytest tests/ -v
	@echo "Running frontend tests..."
	cd frontend && npm run test

lint:
	cd backend && ruff check app/ tests/
	cd frontend && npm run lint

fmt:
	cd backend && black app/ tests/ && ruff check --fix app/ tests/
	cd frontend && npm run format

migrate:
	cd backend && alembic upgrade head

seed:
	cd backend && python ../scripts/seed_demo_data.py

clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null; true
	find . -name "*.pyc" -delete 2>/dev/null; true
	cd frontend && rm -rf dist node_modules/.vite
