# Asterion local developer commands (M11.5).
# Thin wrappers over scripts/*.sh — no product logic here.
.PHONY: start stop health logs restart help scan calibrate expand ipo demo

help:
	@echo "Asterion — local dev commands:"
	@echo "  make start    Start backend (:8000) + frontend (:3000), open /market"
	@echo "  make stop     Stop both servers (only ports 3000/8000)"
	@echo "  make health   Probe backend/frontend/providers + portfolio sanity"
	@echo "  make logs     Tail backend + frontend logs"
	@echo "  make restart  stop then start"
	@echo "  make scan     Run the Opportunity Scanner once (ranked screen)"
	@echo "  make calibrate   Pin the absolute-calibration reference distribution"
	@echo "  make expand ARGS='--starter'   Expand the scannable universe (SEC ingest + score)"
	@echo "  make ipo      Analyze an IPO candidate (SpaceX): verify SEC filing + scorecard"
	@echo "  make demo     Public demo: seed sample data (no DB/keys), then start the app"

scan:
	@cd backend && .venv/bin/python ../scripts/run_scanner.py

calibrate:
	@cd backend && .venv/bin/python ../scripts/build_calibration_profile.py

expand:
	@cd backend && .venv/bin/python ../scripts/expand_universe.py $(ARGS)

ipo:
	@cd backend && .venv/bin/python ../scripts/analyze_ipo_candidate.py SPACEX

demo:
	@cd backend && .venv/bin/python ../scripts/load_demo.py
	@bash scripts/start_asterion.sh

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
