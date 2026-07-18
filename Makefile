

up:
	docker compose up -d

down:
	docker compose down

build:
	docker compose build

logs:
	docker compose logs -f

ps:
	docker compose ps

backend:
	docker compose exec backend bash

frontend:
	docker compose exec frontend bash

db:
	docker compose exec postgres psql -U investment investment_os

clean:
	docker compose down -v
