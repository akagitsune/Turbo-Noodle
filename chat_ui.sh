#!/usr/bin/env bash
# =============================================================================
# chat_ui.sh — Launch the Turbo-Noodle Streamlit chat interface
# Usage:
#   ./scripts/chat_ui.sh [--port PORT] [--server-port API_PORT]
#
# Defaults: Streamlit port=8501, API expected on localhost:8000
# =============================================================================

set -euo pipefail

# ── Resolve project root ──────────────────────────────────────────────────────
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$SCRIPT_DIR"

# ── Defaults ──────────────────────────────────────────────────────────────────
STREAMLIT_PORT="8501"
API_PORT="8000"

# ── Parse optional arguments ──────────────────────────────────────────────────
while [[ $# -gt 0 ]]; do
  case "$1" in
    --port)        STREAMLIT_PORT="$2"; shift 2 ;;
    --server-port) API_PORT="$2";       shift 2 ;;
    *)
      echo "Unknown option: $1"
      echo "Usage: $0 [--port STREAMLIT_PORT] [--server-port API_PORT]"
      exit 1
      ;;
  esac
done

# ── Colours ───────────────────────────────────────────────────────────────────
CYAN='\033[0;36m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${CYAN}🍿 Turbo-Noodle — Streamlit Chat UI${NC}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# ── Load .env if present ──────────────────────────────────────────────────────
if [[ -f "$PROJECT_ROOT/.env" ]]; then
  echo "📄 Loading environment from .env"
  set -a
  # shellcheck disable=SC1091
  source "$PROJECT_ROOT/.env"
  set +a
fi

# ── Optional: check if the API server is reachable ────────────────────────────
API_URL="http://localhost:$API_PORT/health"
echo -n "🔍 Checking API server at $API_URL … "
if curl -sf --max-time 3 "$API_URL" > /dev/null 2>&1; then
  echo -e "${GREEN}online ✓${NC}"
else
  echo -e "${YELLOW}not reachable ⚠${NC}"
  echo -e "   ${YELLOW}The UI will still start but chat will be disabled until the server is running.${NC}"
  echo -e "   Start the server with: ${CYAN}./scripts/server.sh${NC}"
fi

echo ""
echo -e "🌐 Streamlit port : ${GREEN}$STREAMLIT_PORT${NC}"
echo -e "🔌 API port       : ${GREEN}$API_PORT${NC}"
echo ""
echo -e "${CYAN}⏳ Launching Streamlit…${NC}"
echo -e "   Chat UI → ${GREEN}http://localhost:$STREAMLIT_PORT${NC}"
echo ""

export CHAT_API_URL="http://localhost:$API_PORT"

exec uv run streamlit run scripts/chat_ui.py \
  --server.port "$STREAMLIT_PORT" \
  --server.headless true \
  --browser.gatherUsageStats false
