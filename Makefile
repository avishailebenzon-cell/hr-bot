.PHONY: help setup dev test lint clean docker-up docker-down

help:
	@echo "HR Bot - Available commands"
	@echo ""
	@echo "  setup           - Install dependencies and setup environment"
	@echo "  dev             - Run development server"
	@echo "  test            - Run test suite"
	@echo "  lint            - Run code linting"
	@echo "  clean           - Remove cache and build artifacts"
	@echo "  docker-up       - Start Docker containers (PostgreSQL + bot)"
	@echo "  docker-down     - Stop Docker containers"
	@echo "  docker-logs     - View Docker logs"
	@echo "  db-init         - Initialize database schema"
	@echo "  db-reset        - Reset database (development only)"

setup:
	python -m venv venv
	. venv/bin/activate && pip install -r requirements.txt
	cp .env.example .env
	@echo "Setup complete! Edit .env with your credentials"

dev:
	python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000

test:
	pytest -v --cov=. --cov-report=html

lint:
	black .
	isort .
	flake8 .

clean:
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	rm -rf .pytest_cache .coverage htmlcov dist build *.egg-info

docker-up:
	docker-compose up -d
	@echo "Services running:"
	@echo "  - PostgreSQL: localhost:5432"
	@echo "  - HR Bot API: http://localhost:8000"

docker-down:
	docker-compose down

docker-logs:
	docker-compose logs -f hr_bot

db-init:
	psql postgresql://hrbot:hrbot_dev_password@localhost:5432/hr_bot_db < init.sql
	@echo "Database initialized!"

db-reset:
	docker-compose down -v
	docker-compose up -d postgres
	sleep 5
	make db-init
	@echo "Database reset!"

.DEFAULT_GOAL := help
