#!/usr/bin/env bash
# Stop Asterion's local servers — only the processes on ports 3000 and 8000.
# Never touches unrelated system processes. (M11.5)
set -euo pipefail

PORTS=(3000 8000)
LABELS=("Frontend (Next.js)" "Backend (FastAPI)")

red()   { printf '\033[31m%s\033[0m\n' "$1"; }
green() { printf '\033[32m%s\033[0m\n' "$1"; }
yellow(){ printf '\033[33m%s\033[0m\n' "$1"; }

stopped_any=false
for i in "${!PORTS[@]}"; do
  port="${PORTS[$i]}"
  label="${LABELS[$i]}"
  pids="$(lsof -ti "tcp:$port" 2>/dev/null || true)"
  if [ -z "$pids" ]; then
    yellow "• Port $port ($label): nothing running"
    continue
  fi
  echo "• Port $port ($label): stopping pids $pids"
  # shellcheck disable=SC2086
  kill $pids 2>/dev/null || true
  sleep 1
  pids="$(lsof -ti "tcp:$port" 2>/dev/null || true)"
  if [ -n "$pids" ]; then
    yellow "  still alive — sending SIGKILL to $pids"
    # shellcheck disable=SC2086
    kill -9 $pids 2>/dev/null || true
  fi
  green "  ✓ port $port freed"
  stopped_any=true
done

if [ "$stopped_any" = true ]; then
  green "Asterion stopped."
else
  yellow "Asterion was not running."
fi
