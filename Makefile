.PHONY: dev install

install:
	uv sync
	npm install

dev:
	@echo "Starting FastAPI and Vite dev servers..."
	@trap 'kill 0' SIGINT; \
	uv run uvicorn server.main:app --reload --port 8000 & \
	npm run dev & \
	wait
