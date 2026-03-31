#!/usr/bin/env bash
# =============================================================================
# server.sh — Start the Turbo-Noodle FastAPI server (uvicorn)
# Usage:
#   ./scripts/server.sh [--host HOST] [--port PORT] [--reload]
#
# Defaults: host=0.0.0.0, port=8000
# =============================================================================

set -euo pipefail

# ── Resolve project root ──────────────────────────────────────────────────────
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$SCRIPT_DIR"

# ── Defaults ──────────────────────────────────────────────────────────────────
HOST="0.0.0.0"
PORT="8000"
RELOAD_FLAG="--reload"

# ── Parse optional arguments ──────────────────────────────────────────────────
while [[ $# -gt 0 ]]; do
  case "$1" in
    --host)      HOST="$2"; shift 2 ;;
    --port)      PORT="$2"; shift 2 ;;
    --reload)    RELOAD_FLAG="--reload"; shift ;;
    --no-reload) RELOAD_FLAG=""; shift ;;
    *)
      echo "Unknown option: $1"
      echo "Usage: $0 [--host HOST] [--port PORT] [--reload|--no-reload]"
      exit 1
      ;;
  esac
done

# ── Colours ───────────────────────────────────────────────────────────────────
CYAN='\033[0;36m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${CYAN}🍿 Turbo-Noodle — FastAPI Server${NC}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# ── Load .env if present ──────────────────────────────────────────────────────
if [[ -f "$PROJECT_ROOT/.env" ]]; then
  echo "📄 Loading environment from .env"
  set -a
  # shellcheck disable=SC1091
  source "$PROJECT_ROOT/.env"
  set +a
fi

echo -e "🌐 Host   : ${GREEN}$HOST${NC}"
echo -e "🔌 Port   : ${GREEN}$PORT${NC}"
if [[ -n "$RELOAD_FLAG" ]]; then
  echo -e "🔄 Reload : ${YELLOW}enabled${NC}"
fi
echo ""
echo -e "${CYAN}⏳ Starting server…${NC}"
echo -e "   API docs   → ${GREEN}http://localhost:$PORT/docs${NC}"
echo -e "   Health     → ${GREEN}http://localhost:$PORT/health${NC}"
echo ""

exec uv run uvicorn src.app.main:app \
  --host "$HOST" \
  --port "$PORT" \
  --log-level debug \
  $RELOAD_FLAG
