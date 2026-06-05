# Asterion local developer commands (M11.5).
# Thin wrappers over scripts/*.sh — no product logic here.
.PHONY: start stop health logs restart help scan expand

help:
	@echo "Asterion — local dev commands:"
	@echo "  make start    Start backend (:8000) + frontend (:3000), open /market"
	@echo "  make stop     Stop both servers (only ports 3000/8000)"
	@echo "  make health   Probe backend/frontend/providers + portfolio sanity"
	@echo "  make logs     Tail backend + frontend logs"
	@echo "  make restart  stop then start"
	@echo "  make scan     Run the Opportunity Scanner once (ranked screen)"
	@echo "  make expand ARGS='--starter'   Expand the scannable universe (SEC ingest + score)"

scan:
	@cd backend && .venv/bin/python ../scripts/run_scanner.py

expand:
	@cd backend && .venv/bin/python ../scripts/expand_universe.py $(ARGS)

start:
	@bash scripts/start_asterion.sh

stop:
	@bash scripts/stop_asterion.sh

health:
	@bash scripts/health_asterion.sh

restart: stop start

logs:
	@echo "Tailing logs/backend.log + logs/frontend.log (Ctrl-C to quit) …"
	@touch logs/backend.log logs/frontend.log
	@tail -n 40 -f logs/backend.log logs/frontend.log
