.PHONY: up down install test lint run

up:
	docker compose -f docker/docker-compose.yml up -d

down:
	docker compose -f docker/docker-compose.yml down -v

install:
	pip install -r requirements.txt

test:
	pytest

lint:
	ruff check chaosProbe tests

run:
	uvicorn chaosProbe.api.main:app --reload --port 8080