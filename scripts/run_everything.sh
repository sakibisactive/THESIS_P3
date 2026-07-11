#!/usr/bin/env bash
# =============================================================================
# scripts/run_everything.sh
# Full end-to-end thesis pipeline in one script.
#
# Usage:
#   bash scripts/run_everything.sh            # heavy preset (default)
#   bash scripts/run_everything.sh smoke      # quick test
#   bash scripts/run_everything.sh light      # validation run
#   bash scripts/run_everything.sh extreme    # full research-mode run
# =============================================================================

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

PRESET="${1:-heavy}"
PYTHON="${REPO_ROOT}/.venv/bin/python"

if [[ ! -f "$PYTHON" ]]; then
    PYTHON="$(command -v python3 || command -v python)"
fi

echo ""
echo "════════════════════════════════════════════════════════════"
echo "  E³-Hybrid Thesis — Full Pipeline Runner"
echo "  Preset : $PRESET"
echo "  Python : $PYTHON"
echo "════════════════════════════════════════════════════════════"
echo ""

# ── 1. Preflight ──────────────────────────────────────────────────────────────
echo "── Step 1: Pre-flight check ─────────────────────────────────"
"$PYTHON" preflight.py
echo ""

# ── 2. Algorithm profiler ─────────────────────────────────────────────────────
echo "── Step 2: Algorithm performance profile ────────────────────"
"$PYTHON" scripts/profile_algorithms.py
echo ""

# ── 3. Benchmark ─────────────────────────────────────────────────────────────
echo "── Step 3: Benchmark suite ($PRESET) ────────────────────────"
"$PYTHON" run_thesis.py --preset "$PRESET" --skip-preflight
echo ""

echo "════════════════════════════════════════════════════════════"
echo "  Pipeline complete. Results are in: outputs/"
echo "════════════════════════════════════════════════════════════"
