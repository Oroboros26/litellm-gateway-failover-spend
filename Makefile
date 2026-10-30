ENV = set -a; [ -f .env ] && . ./.env; set +a
.PHONY: run keys test eval failover
run:
	docker compose up -d --build
keys:
	@$(ENV); python -m gateway.keys
test:
	pytest -q
eval:
	@$(ENV); python -m eval.loadtest && python -m eval.spend
failover:
	@$(ENV); python -m eval.failover
