#!/usr/bin/env bash
# =============================================================================
# install.sh — One-shot setup for Turbo-Noodle
# Usage:
#   ./install.sh [--skip-model] [--skip-tests]
#
# What it does:
#   1. Checks prerequisites (uv, Python ≥3.11, Ollama)
#   2. Installs Python dependencies via uv sync
#   3. Creates .env from .env.example if .env does not exist
#   4. Pulls the configured Ollama model (pass --skip-model to skip)
#   5. Runs the test suite to verify the install (pass --skip-tests to skip)
#   6. Prints next-step instructions
# =============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$SCRIPT_DIR"

# ── Flags ─────────────────────────────────────────────────────────────────────
SKIP_MODEL=false
SKIP_TESTS=false

while [[ $# -gt 0 ]]; do
  case "$1" in
    --skip-model) SKIP_MODEL=true; shift ;;
    --skip-tests) SKIP_TESTS=true; shift ;;
    *)
      echo "Unknown option: $1"
      echo "Usage: $0 [--skip-model] [--skip-tests]"
      exit 1
      ;;
  esac
done

# ── Colours ───────────────────────────────────────────────────────────────────
CYAN='\033[0;36m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BOLD='\033[1m'
NC='\033[0m'

ok()   { echo -e "  ${GREEN}✓${NC} $*"; }
warn() { echo -e "  ${YELLOW}⚠${NC}  $*"; }
fail() { echo -e "  ${RED}✗${NC} $*"; exit 1; }
step() { echo -e "\n${CYAN}${BOLD}▶ $*${NC}"; }

echo -e "${CYAN}${BOLD}"
echo "  🍿  Turbo-Noodle — Install"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo -e "${NC}"

# ── 1. Prerequisites ──────────────────────────────────────────────────────────
step "Checking prerequisites"

# uv
if command -v uv &>/dev/null; then
  ok "uv $(uv --version 2>/dev/null | head -1)"
else
  fail "uv not found. Install it with:  curl -LsSf https://astral.sh/uv/install.sh | sh"
fi

# Python version (uv manages its own; just verify uv can find ≥3.11)
PYTHON_VERSION=$(uv run python -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')" 2>/dev/null || echo "unknown")
PYTHON_MAJOR=$(echo "$PYTHON_VERSION" | cut -d. -f1)
PYTHON_MINOR=$(echo "$PYTHON_VERSION" | cut -d. -f2)
if [[ "$PYTHON_MAJOR" -ge 3 && "$PYTHON_MINOR" -ge 11 ]]; then
  ok "Python $PYTHON_VERSION"
else
  fail "Python 3.11+ required, found $PYTHON_VERSION. Run: uv python install 3.13"
fi

# Ollama (optional at install time — only needed to run the agent)
if command -v ollama &>/dev/null; then
  ok "Ollama $(ollama --version 2>/dev/null | head -1)"
  OLLAMA_AVAILABLE=true
else
  warn "Ollama not found — install from https://ollama.com before starting the server"
  OLLAMA_AVAILABLE=false
fi

# ── 2. Python dependencies ────────────────────────────────────────────────────
step "Installing Python dependencies"
uv sync --quiet
ok "Dependencies installed"

# ── 3. Environment file ───────────────────────────────────────────────────────
step "Setting up .env"
if [[ -f "$PROJECT_ROOT/.env" ]]; then
  ok ".env already exists — skipping"
else
  cp "$PROJECT_ROOT/.env.example" "$PROJECT_ROOT/.env"
  ok "Created .env from .env.example"
  warn "Review .env and set OLLAMA_MODEL / OLLAMA_HOST as needed"
fi

# ── 4. Pull Ollama model ──────────────────────────────────────────────────────
if [[ "$SKIP_MODEL" == false && "$OLLAMA_AVAILABLE" == true ]]; then
  step "Pulling Ollama model"

  # Load .env to read OLLAMA_MODEL
  set -a
  # shellcheck disable=SC1091
  source "$PROJECT_ROOT/.env"
  set +a

  MODEL="${OLLAMA_MODEL:-qwen2.5:14b}"
  echo "  Model: $MODEL"

  if ollama list 2>/dev/null | grep -qF "$MODEL"; then
    ok "Model already present"
  else
    echo "  Downloading — this may take a few minutes…"
    ollama pull "$MODEL"
    ok "Model pulled"
  fi
elif [[ "$SKIP_MODEL" == true ]]; then
  warn "Skipping model pull (--skip-model)"
else
  warn "Skipping model pull (Ollama not installed)"
fi

# ── 5. Test suite ─────────────────────────────────────────────────────────────
if [[ "$SKIP_TESTS" == false ]]; then
  step "Running tests"
  if uv run pytest --tb=short -q 2>&1; then
    ok "All tests passed"
  else
    fail "Tests failed — check the output above"
  fi
else
  warn "Skipping tests (--skip-tests)"
fi

# ── 6. Next steps ─────────────────────────────────────────────────────────────
echo ""
echo -e "${GREEN}${BOLD}✅  Installation complete!${NC}"
echo ""
echo -e "  ${BOLD}Next steps:${NC}"
echo ""
echo -e "  1. Ingest the TMDB dataset (first-time only):"
echo -e "     ${CYAN}./ingest.sh${NC}"
echo ""
echo -e "  2. Start the API server:"
echo -e "     ${CYAN}./server.sh${NC}"
echo ""
echo -e "  3. Open the chat UI  (in a second terminal):"
echo -e "     ${CYAN}./chat_ui.sh${NC}"
echo ""
echo -e "  4. Or talk to the API directly:"
echo -e "     ${CYAN}curl -s -X POST http://localhost:8000/chat \\"
echo -e "       -H 'Content-Type: application/json' \\"
echo -e "       -d '{\"query\": \"Who directed Inception?\"}' | jq${NC}"
echo ""
