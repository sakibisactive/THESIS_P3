#!/usr/bin/env python3
"""
run_thesis.py — One-command thesis experiment orchestrator.

Presets
-------
  smoke     2 algorithms × 1 scenario × 25 vehicles × 1 seed  (≈ 30 s)
  light     All algorithms × 1 scenario × 25 vehicles × seeds 1-2  (≈ 5 min)
  heavy     Full thesis matrix: all algorithms × all scenarios ×
            all vehicle counts × seeds 1-10  (≈ 1-2 h on 4 cores)
  extreme   Same as heavy but with research-mode parameters (no evaluation
            overrides — significantly longer)

Usage
-----
    python run_thesis.py smoke
    python run_thesis.py light
    python run_thesis.py heavy
    python run_thesis.py heavy --no-resume
    python run_thesis.py extreme --sequential

This script is a thin orchestration wrapper. All benchmark logic lives in
scripts/run_benchmarks.py and scripts/profile_algorithms.py.
"""

import argparse
import pathlib
import subprocess
import sys
import time

REPO_ROOT = pathlib.Path(__file__).resolve().parent
VENV_PYTHON = REPO_ROOT / ".venv" / "bin" / "python"

# Fall back to the active interpreter if the venv hasn't been created yet
PYTHON = str(VENV_PYTHON) if VENV_PYTHON.exists() else sys.executable


# ─────────────────────────────────────────────────────────────────────────────
# Preset definitions
# ─────────────────────────────────────────────────────────────────────────────

PRESETS: dict[str, dict] = {
    "smoke": {
        "description": "Quick pipeline check (~30 s)",
        "benchmark_args": [
            "--algorithms", "Dijkstra,E3-Hybrid",
            "--scenarios", "normal_traffic",
            "--vehicles", "25",
            "--seeds", "1",
            "--no-resume",
        ],
        "profile": False,
        "note": "2 algorithms × 1 scenario × 25 vehicles × 1 seed = 2 runs",
    },
    "light": {
        "description": "Quick multi-seed sanity check (~5 min)",
        "benchmark_args": [
            "--algorithms", "Dijkstra,AStar,E3-Hybrid",
            "--scenarios", "normal_traffic,road_closure",
            "--vehicles", "25",
            "--seeds", "1-2",
        ],
        "profile": False,
        "note": "3 algorithms × 2 scenarios × 25 vehicles × 2 seeds = 12 runs",
    },
    "heavy": {
        "description": "Full thesis benchmark matrix (~1-2 h on 4 cores)",
        "benchmark_args": [
            "--use-multiprocessing",
        ],
        "profile": True,
        "note": "6 algorithms × 6 scenarios × 4 vehicle counts × 10 seeds = 1,440 runs",
    },
    "extreme": {
        "description": "Full matrix with research-mode parameters (much longer)",
        "benchmark_args": [
            "--use-multiprocessing",
            "--research-mode",
        ],
        "profile": True,
        "note": "Same as heavy but with full swarm parameters (ACO 50 ants, etc.)",
    },
}


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

BOLD = "\033[1m"
CYAN = "\033[96m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
RESET = "\033[0m"


def _banner(text: str) -> None:
    width = 64
    print()
    print(BOLD + CYAN + "═" * width + RESET)
    print(BOLD + CYAN + f"  {text}" + RESET)
    print(BOLD + CYAN + "═" * width + RESET)


def _run(cmd: list[str], label: str) -> int:
    """Runs a subprocess, streaming output live. Returns exit code."""
    _banner(label)
    print(f"  $ {' '.join(cmd)}\n")
    result = subprocess.run(cmd, cwd=REPO_ROOT)
    return result.returncode


def _elapsed(seconds: float) -> str:
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    if h:
        return f"{h}h {m}m {s}s"
    if m:
        return f"{m}m {s}s"
    return f"{s}s"


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────

def main() -> int:
    parser = argparse.ArgumentParser(
        description="E³-Hybrid Thesis one-command experiment runner.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="\n".join(
            f"  {name:<10} {meta['description']}\n"
            f"             {YELLOW}{meta['note']}{RESET}"
            for name, meta in PRESETS.items()
        ),
    )
    parser.add_argument(
        "preset",
        choices=list(PRESETS.keys()),
        help="Experiment scale preset.",
    )
    parser.add_argument(
        "--skip-preflight",
        action="store_true",
        help="Skip the system readiness check.",
    )
    parser.add_argument(
        "--no-resume",
        action="store_true",
        help="Discard existing checkpoints and restart from scratch.",
    )
    parser.add_argument(
        "--sequential",
        action="store_true",
        help="Force sequential execution (disables multiprocessing).",
    )
    args = parser.parse_args()

    preset = PRESETS[args.preset]
    wall_start = time.time()

    print(BOLD + "\n  E³-Hybrid Thesis Experiment Runner" + RESET)
    print(f"  Preset : {BOLD}{args.preset}{RESET}  —  {preset['description']}")
    print(f"  Matrix : {preset['note']}")

    # ── 1. Preflight ──────────────────────────────────────────────────────────
    if not args.skip_preflight:
        rc = _run([PYTHON, "preflight.py"], "Step 1 / 4 — Pre-flight System Check")
        if rc != 0:
            print(f"\n{RED}Preflight failed. Fix the issues above, then re-run.{RESET}")
            print("To skip preflight: python run_thesis.py <preset> --skip-preflight\n")
            return 1
    else:
        print(f"\n  {YELLOW}⚠  Preflight skipped (--skip-preflight).{RESET}")

    # ── 2. Algorithm profiling (heavy / extreme only) ─────────────────────────
    if preset["profile"]:
        rc = _run(
            [PYTHON, "scripts/profile_algorithms.py"],
            "Step 2 / 4 — Algorithm Performance Profile",
        )
        if rc != 0:
            print(f"\n{YELLOW}⚠  Profiling failed — continuing anyway.{RESET}")
    else:
        print(f"\n  Skipping profiling for '{args.preset}' preset.")

    # ── 3. Benchmark ──────────────────────────────────────────────────────────
    benchmark_cmd = [PYTHON, "scripts/run_benchmarks.py"]
    extra_args = list(preset["benchmark_args"])

    if args.no_resume and "--no-resume" not in extra_args:
        extra_args.append("--no-resume")
    if args.sequential:
        extra_args = [a for a in extra_args if a != "--use-multiprocessing"]

    benchmark_cmd += extra_args

    step_label = (
        "Step 3 / 4 — Running Benchmark Suite"
        if preset["profile"]
        else "Step 2 / 3 — Running Benchmark Suite"
    )
    rc = _run(benchmark_cmd, step_label)
    if rc != 0:
        print(f"\n{RED}Benchmark run exited with errors (code {rc}).{RESET}")
        print("Intermediate checkpoints are preserved. Re-run to resume.\n")
        return rc

    # ── 4. Done ───────────────────────────────────────────────────────────────
    elapsed = _elapsed(time.time() - wall_start)
    _banner("Complete")
    print(f"  {GREEN}✔  All steps finished in {elapsed}.{RESET}")
    print()
    print("  Output artefacts:")
    outputs = [
        ("outputs/benchmark_manifest.json", "Benchmark manifest (parameters + git hash)"),
        ("outputs/statistical_tables.md",   "Hypothesis tests (Welch t, Mann-Whitney U, Cohen d)"),
        ("outputs/thesis_results/environment_snapshot.json",   "System environment snapshot"),
        ("outputs/thesis_results/reproducibility_manifest.json", "Algorithm profiling results"),
        ("outputs/",                         "Figures (PNG + PDF + SVG) and raw CSV"),
    ]
    for path, desc in outputs:
        exists = (REPO_ROOT / path).exists()
        mark = GREEN + "✔" + RESET if exists else YELLOW + "?" + RESET
        print(f"    {mark}  {path}")
        print(f"         {desc}")
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
