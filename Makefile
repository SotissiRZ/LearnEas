.PHONY: help build up down logs ps restart dev dev-down migrate seed superuser shell backend-shell nginx-reload clean

help:
	@echo "KalanPro — commandes Docker disponibles :"
	@echo "  make build         Construit les images (production)"
	@echo "  make up            Démarre toute la stack en arrière-plan (production)"
	@echo "  make down          Arrête et supprime les conteneurs (production)"
	@echo "  make logs          Suit les logs de tous les services"
	@echo "  make ps            Liste les conteneurs actifs"
	@echo "  make restart       Redémarre tous les services"
	@echo "  make dev           Démarre la stack de développement (hot-reload)"
	@echo "  make dev-down      Arrête la stack de développement"
	@echo "  make migrate       Applique les migrations Django"
	@echo "  make seed          Insère les données de démonstration"
	@echo "  make superuser     Crée un compte administrateur Django"
	@echo "  make backend-shell Ouvre un shell dans le conteneur backend"
	@echo "  make clean         Supprime conteneurs + volumes (⚠️ perte de données)"

build:
	docker compose build

up:
	docker compose up -d
	@echo "Application disponible sur http://localhost"

down:
	docker compose down

logs:
	docker compose logs -f

ps:
	docker compose ps

restart:
	docker compose restart

dev:
	docker compose -f docker-compose.dev.yml up --build

dev-down:
	docker compose -f docker-compose.dev.yml down

migrate:
	docker compose exec backend python manage.py migrate

seed:
	docker compose exec backend python manage.py seed_demo

superuser:
	docker compose exec backend python manage.py createsuperuser

backend-shell:
	docker compose exec backend bash

clean:
	docker compose down -v
