#!/usr/bin/env bash
# Asterion health check (M11.5). Probes backend + frontend, reports provider
# configuration (configured? — never prints keys), and sanity-checks the live
# portfolio total so an inflated/broken valuation is caught. Green/yellow/red.
set -uo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKEND_URL="http://localhost:8000"
FRONTEND_URL="http://localhost:3000"
PROVIDERS_URL="$BACKEND_URL/api/system/providers"
LIVE_URL="$BACKEND_URL/api/portfolio/live"
MARKET_URL="$FRONTEND_URL/market"

# Expected total for the personal book (~$1.1k). Override via env if needed.
EXPECTED_MIN="${ASTERION_PORTFOLIO_MIN:-500}"
EXPECTED_MAX="${ASTERION_PORTFOLIO_MAX:-50000}"

# JSON parser: prefer the backend venv python, else system python3.
PY="$ROOT/backend/.venv/bin/python"
[ -x "$PY" ] || PY="$(command -v python3 || true)"

red()    { printf '\033[31m%s\033[0m\n' "$1"; }
green()  { printf '\033[32m%s\033[0m\n' "$1"; }
yellow() { printf '\033[33m%s\033[0m\n' "$1"; }

overall=0  # 0 green, 1 yellow, 2 red
bump() { [ "$1" -gt "$overall" ] && overall="$1"; return 0; }

http_code() { curl -s -o /dev/null -w '%{http_code}' --max-time 5 "$1" 2>/dev/null || echo 000; }
fetch()     { curl -s --max-time 5 "$1" 2>/dev/null || echo ""; }

echo "Asterion health — $(date '+%Y-%m-%d %H:%M:%S')"
echo "──────────────────────────────────────────────"

# ── backend providers endpoint ─────────────────────────────────────────────
code="$(http_code "$PROVIDERS_URL")"
if [ "$code" = "200" ]; then
  green "✓ Backend /api/system/providers → 200"
else
  red "✗ Backend /api/system/providers → $code (is it running? make start)"
  bump 2
fi

# ── provider configuration (configured booleans only — no secrets) ─────────
providers_json="$(fetch "$PROVIDERS_URL")"
if [ -n "$providers_json" ] && [ -n "$PY" ]; then
  for prov in finnhub fmp fred; do
    conf="$(printf '%s' "$providers_json" | "$PY" -c \
      "import sys,json;d=json.load(sys.stdin);print(d.get('$prov',{}).get('configured'))" 2>/dev/null || echo "")"
    if [ "$conf" = "True" ]; then
      green "  • $prov: configured"
    else
      yellow "  • $prov: not configured (optional — falls back)"
      bump 1
    fi
  done
fi

# ── live portfolio + total sanity ──────────────────────────────────────────
code="$(http_code "$LIVE_URL")"
if [ "$code" = "200" ]; then
  green "✓ Backend /api/portfolio/live → 200"
  live_json="$(fetch "$LIVE_URL")"
  total="$(printf '%s' "$live_json" | "$PY" -c \
    "import sys,json;d=json.load(sys.stdin);print(d.get('total_value') or 0)" 2>/dev/null || echo 0)"
  in_range="$("$PY" -c \
    "t=float('$total');print('yes' if $EXPECTED_MIN<=t<=$EXPECTED_MAX else 'no')" 2>/dev/null || echo no)"
  if [ "$in_range" = "yes" ]; then
    green "  • Portfolio total \$$total — within expected [\$$EXPECTED_MIN, \$$EXPECTED_MAX]"
  else
    red "  • Portfolio total \$$total — OUTSIDE [\$$EXPECTED_MIN, \$$EXPECTED_MAX] (inflated/broken?)"
    bump 2
  fi
else
  red "✗ Backend /api/portfolio/live → $code"
  bump 2
fi

# ── frontend market page ───────────────────────────────────────────────────
code="$(http_code "$MARKET_URL")"
if [ "$code" = "200" ]; then
  green "✓ Frontend /market → 200"
else
  red "✗ Frontend /market → $code (is it running? make start)"
  bump 2
fi

echo "──────────────────────────────────────────────"
case "$overall" in
  0) green  "STATUS: GREEN — all systems healthy"; exit 0 ;;
  1) yellow "STATUS: YELLOW — running, some optional providers unconfigured"; exit 0 ;;
  *) red    "STATUS: RED — something is down (see above)"; exit 1 ;;
esac
