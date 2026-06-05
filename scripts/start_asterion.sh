#!/usr/bin/env bash
# Asterion one-command local launcher (M11.5).
# Starts FastAPI (:8000) + Next.js (:3000), waits for both to answer 200,
# opens the market page, prints a clean status summary. Dev convenience only —
# no product logic, no .env mutation, no secrets printed.
set -euo pipefail

# ── locate project root (this script lives in <root>/scripts) ──────────────
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKEND="$ROOT/backend"
FRONTEND="$ROOT/frontend"
LOGS="$ROOT/logs"
BACKEND_PORT=8000
FRONTEND_PORT=3000
BACKEND_URL="http://localhost:$BACKEND_PORT"
FRONTEND_URL="http://localhost:$FRONTEND_PORT"
MARKET_URL="$FRONTEND_URL/market"
HEALTH_PATH="/api/system/providers"

red()   { printf '\033[31m%s\033[0m\n' "$1"; }
green() { printf '\033[32m%s\033[0m\n' "$1"; }
yellow(){ printf '\033[33m%s\033[0m\n' "$1"; }
die()   { red "✗ $1"; exit 1; }

# ── preflight: required files/dirs (fail loud, name the exact missing path) ─
[ -d "$BACKEND" ]  || die "backend directory missing: $BACKEND"
[ -d "$FRONTEND" ] || die "frontend directory missing: $FRONTEND"
if [ ! -f "$BACKEND/.env" ]; then
  red "✗ Missing required file: $BACKEND/.env"
  yellow "  Copy the template and fill it in:  cp $ROOT/.env.example $BACKEND/.env"
  exit 1
fi
[ -d "$BACKEND/.venv" ] || die "Python venv missing: $BACKEND/.venv  (run: cd backend && python3 -m venv .venv && .venv/bin/pip install -e .)"
[ -x "$BACKEND/.venv/bin/python" ] || die "venv python not executable: $BACKEND/.venv/bin/python"
[ -d "$FRONTEND/node_modules" ] || die "Node deps missing: $FRONTEND/node_modules  (run: cd frontend && npm install)"

mkdir -p "$LOGS"

# ── free stale ports (only the two we own) ─────────────────────────────────
kill_port() {
  local port="$1"
  local pids
  pids="$(lsof -ti "tcp:$port" 2>/dev/null || true)"
  if [ -n "$pids" ]; then
    yellow "• Port $port busy (pids: $pids) — stopping stale process"
    # shellcheck disable=SC2086
    kill $pids 2>/dev/null || true
    sleep 1
    pids="$(lsof -ti "tcp:$port" 2>/dev/null || true)"
    if [ -n "$pids" ]; then
      # shellcheck disable=SC2086
      kill -9 $pids 2>/dev/null || true
    fi
  fi
}
kill_port "$BACKEND_PORT"
kill_port "$FRONTEND_PORT"

# ── start backend ──────────────────────────────────────────────────────────
echo "• Starting backend (FastAPI) on :$BACKEND_PORT …"
(
  cd "$BACKEND"
  exec .venv/bin/python -m uvicorn app.main:app --host 0.0.0.0 --port "$BACKEND_PORT"
) >"$LOGS/backend.log" 2>&1 &
BACKEND_PID=$!

# ── start frontend ─────────────────────────────────────────────────────────
echo "• Starting frontend (Next.js) on :$FRONTEND_PORT …"
(
  cd "$FRONTEND"
  exec npm run dev
) >"$LOGS/frontend.log" 2>&1 &
FRONTEND_PID=$!

# ── wait for HTTP 200 from both ────────────────────────────────────────────
wait_for_200() {
  local url="$1" name="$2" pid="$3" tries=60 code
  for _ in $(seq 1 "$tries"); do
    if ! kill -0 "$pid" 2>/dev/null; then
      red "✗ $name process exited early — see logs"
      return 1
    fi
    code="$(curl -s -o /dev/null -w '%{http_code}' --max-time 3 "$url" 2>/dev/null || echo 000)"
    if [ "$code" = "200" ]; then
      green "✓ $name up ($url → 200)"
      return 0
    fi
    sleep 1
  done
  red "✗ $name did not return 200 in time ($url)"
  return 1
}

ok=true
wait_for_200 "$BACKEND_URL$HEALTH_PATH" "Backend" "$BACKEND_PID" || ok=false
wait_for_200 "$MARKET_URL" "Frontend" "$FRONTEND_PID" || ok=false

if [ "$ok" != true ]; then
  red "One or more servers failed to start. Tail the logs:"
  echo "  tail -n 40 $LOGS/backend.log"
  echo "  tail -n 40 $LOGS/frontend.log"
  exit 1
fi

# ── open the market page (best effort) ─────────────────────────────────────
if command -v open >/dev/null 2>&1; then
  open "$MARKET_URL" >/dev/null 2>&1 || true
  BROWSER_OPENED="yes (macOS open)"
else
  BROWSER_OPENED="no (open this URL manually)"
fi

# ── summary ────────────────────────────────────────────────────────────────
echo
green "Asterion is running."
echo "  Backend:  $BACKEND_URL   (pid $BACKEND_PID)"
echo "  Frontend: $FRONTEND_URL   (pid $FRONTEND_PID)"
echo "  Market:   $MARKET_URL"
echo "  Logs:     $LOGS/backend.log, $LOGS/frontend.log"
echo "  Browser:  $BROWSER_OPENED"
echo
echo "  Stop with:   make stop   (or scripts/stop_asterion.sh)"
echo "  Health:      make health (or scripts/health_asterion.sh)"
