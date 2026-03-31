#!/usr/bin/env bash
# =============================================================================
# ingest.sh — Run the Turbo-Noodle data ingestion pipeline
# Usage:
#   ./scripts/ingest.sh [MOVIES_CSV] [CREDITS_CSV]
#
# Defaults to the TMDB CSV files in the project root.
# =============================================================================

set -euo pipefail

# ── Resolve project root ──────────────────────────────────────────────────────
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$SCRIPT_DIR"

# ── CSV paths (override via arguments) ────────────────────────────────────────
MOVIES_CSV="${1:-$PROJECT_ROOT/tmdb_5000_movies.csv}"
CREDITS_CSV="${2:-$PROJECT_ROOT/tmdb_5000_credits.csv}"

# ── Colours ───────────────────────────────────────────────────────────────────
CYAN='\033[0;36m'
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m' # No Colour

echo -e "${CYAN}🍿 Turbo-Noodle — Data Ingestion${NC}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# ── Pre-flight checks ─────────────────────────────────────────────────────────
if [[ ! -f "$MOVIES_CSV" ]]; then
  echo -e "${RED}✗ Movies CSV not found: $MOVIES_CSV${NC}"
  echo "  Pass the path as the first argument, e.g.:"
  echo "  ./scripts/ingest.sh /path/to/tmdb_5000_movies.csv /path/to/tmdb_5000_credits.csv"
  exit 1
fi

if [[ ! -f "$CREDITS_CSV" ]]; then
  echo -e "${RED}✗ Credits CSV not found: $CREDITS_CSV${NC}"
  echo "  Pass the path as the second argument, e.g.:"
  echo "  ./scripts/ingest.sh /path/to/tmdb_5000_movies.csv /path/to/tmdb_5000_credits.csv"
  exit 1
fi

# ── Load .env if present ──────────────────────────────────────────────────────
if [[ -f "$PROJECT_ROOT/.env" ]]; then
  echo "📄 Loading environment from .env"
  set -a
  # shellcheck disable=SC1091
  source "$PROJECT_ROOT/.env"
  set +a
fi

echo "📂 Movies  : $MOVIES_CSV"
echo "📂 Credits : $CREDITS_CSV"
echo ""

echo -e "${CYAN}⏳ Starting ingestion…${NC}"
START_TIME=$(date +%s)

# Remove stale database so ingestion always starts clean
DB_FILE="$PROJECT_ROOT/movies.db"
if [[ -f "$DB_FILE" ]]; then
  echo "🗑️  Removing existing database: $DB_FILE"
  rm -f "$DB_FILE"
fi

uv run python -m src.data.ingest "$MOVIES_CSV" "$CREDITS_CSV"

END_TIME=$(date +%s)
ELAPSED=$(( END_TIME - START_TIME ))

echo ""
echo -e "${GREEN}✅ Ingestion finished in ${ELAPSED}s${NC}"
