#!/usr/bin/env python3
"""
run_thesis.py — One-command thesis experiment orchestrator.

Usage
-----
    python run_thesis.py --preset smoke
    python run_thesis.py --preset light
    python run_thesis.py --preset heavy
    python run_thesis.py --preset extreme
    python run_thesis.py --preset heavy --no-resume
    python run_thesis.py --preset heavy --sequential
    python run_thesis.py --preset heavy --skip-preflight

This is a thin orchestration wrapper. All benchmark logic lives in:
  • scripts/run_benchmarks.py    — benchmark execution engine
  • scripts/profile_algorithms.py — routing latency profiler
  • preflight.py                 — environment verification
"""

import argparse
import os
import pathlib
import subprocess
import sys
import textwrap
import time

# Set default log level to WARNING to keep the console clean and show only progress/errors
os.environ.setdefault("THESIS_LOG_LEVEL", "WARNING")

REPO_ROOT = pathlib.Path(__file__).resolve().parent
VENV_PYTHON = REPO_ROOT / ".venv" / "bin" / "python"
PYTHON = str(VENV_PYTHON) if VENV_PYTHON.exists() else sys.executable

_USE_COLOR = sys.stdout.isatty()
BOLD   = "\033[1m"  if _USE_COLOR else ""
CYAN   = "\033[96m" if _USE_COLOR else ""
GREEN  = "\033[92m" if _USE_COLOR else ""
YELLOW = "\033[93m" if _USE_COLOR else ""
RED    = "\033[91m" if _USE_COLOR else ""
DIM    = "\033[2m"  if _USE_COLOR else ""
RESET  = "\033[0m"  if _USE_COLOR else ""

WIDTH = 64

# ─────────────────────────────────────────────────────────────────────────────
# Preset definitions
# ─────────────────────────────────────────────────────────────────────────────

PRESETS: dict[str, dict] = {
    "smoke": {
        "runtime":     "~30 seconds",
        "description": "Quick pipeline sanity check — 2 runs",
        "matrix":      "2 algorithms × 1 scenario × 25 vehicles × 1 seed",
        "benchmark_args": [
            "--test-run",
            "--no-resume",
        ],
        "run_profiler": False,
    },
    "light": {
        "runtime":     "~5 minutes",
        "description": "Multi-seed validation check — 12 runs",
        "matrix":      "3 algorithms × 2 scenarios × 25 vehicles × 2 seeds",
        "benchmark_args": [
            "--algorithms", "Dijkstra,AStar,E3-Hybrid",
            "--scenarios",  "normal_traffic,road_closure",
            "--vehicles",   "25",
            "--seeds",      "1-2",
        ],
        "run_profiler": False,
    },
    "heavy": {
        "runtime":     "~1–2 hours on 4 CPU cores",
        "description": "Full thesis benchmark matrix — 1,440 runs",
        "matrix":      "6 algorithms × 6 scenarios × 4 vehicle counts × 10 seeds",
        "benchmark_args": [
            "--use-multiprocessing",
        ],
        "run_profiler": True,
    },
    "extreme": {
        "runtime":     "~4–8 hours on 4 CPU cores",
        "description": "Full matrix with research-mode swarm parameters",
        "matrix":      "Same as heavy — ACO/BCO/PSO/E3 run at full iteration depth",
        "benchmark_args": [
            "--use-multiprocessing",
            "--research-mode",
        ],
        "run_profiler": True,
    },
    "stress": {
        "runtime":     "~1–2 hours on 4 CPU cores",
        "description": "Thesis stress testing matrix — 300 runs",
        "matrix":      "6 algorithms × 5 stress scenarios × 1 vehicle count (1000) × 10 seeds",
        "benchmark_args": [
            "--use-multiprocessing",
            "--algorithms", "Dijkstra,AStar,ACO,BCO,PSO,E3-Hybrid",
            "--scenarios", "stress_normal,stress_closures,stress_blackout,stress_failures,stress_ambulance",
            "--vehicles", "1000",
            "--output-dir", "outputs/stress_results",
        ],
        "run_profiler": False,
    },
    "ablation": {
        "runtime":     "~1–2 hours on 4 CPU cores",
        "description": "E3-Hybrid ablation analysis — 720 runs",
        "matrix":      "6 E3 variants × 6 scenarios × 2 vehicle counts × 10 seeds",
        "benchmark_args": [
            "--use-multiprocessing",
            "--algorithms", "E3-Hybrid,E3-Hybrid-NoACO,E3-Hybrid-NoBCO,E3-Hybrid-NoPSO,E3-Hybrid-NoElite,E3-Hybrid-WithAdaptive",
            "--scenarios", "normal_traffic,road_closure,progressive_closures,emergency_incident,infrastructure_failure,communication_blackout",
            "--vehicles", "100,200",
            "--output-dir", "outputs/ablation_results",
        ],
        "run_profiler": False,
    },
    "sensitivity": {
        "runtime":     "~1–2 hours on 4 CPU cores",
        "description": "Objective weights sensitivity analysis — 600 runs",
        "matrix":      "5 weight configurations × 6 scenarios × 2 vehicle counts × 10 seeds",
        "benchmark_args": [
            "--use-multiprocessing",
            "--algorithms", "E3-Hybrid-WTime,E3-Hybrid-WEnergy,E3-Hybrid-WSafety,E3-Hybrid-Balanced,E3-Hybrid-Thesis",
            "--scenarios", "normal_traffic,road_closure,progressive_closures,emergency_incident,infrastructure_failure,communication_blackout",
            "--vehicles", "100,200",
            "--output-dir", "outputs/sensitivity_results",
        ],
        "run_profiler": False,
    },
    "complete": {
        "runtime":     "~4–8 hours on 4 CPU cores",
        "description": "Entire evaluation suite (heavy + stress + ablation + sensitivity) — 3,060 runs total",
        "matrix":      "Baseline (1,440) + Stress (300) + Ablation (720) + Sensitivity (600)",
        "sub_presets": ["heavy", "stress", "ablation", "sensitivity"],
        "run_profiler": True,
    },
}

# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _banner(text: str) -> None:
    print()
    print(BOLD + CYAN + "═" * WIDTH + RESET)
    print(BOLD + CYAN + f"  {text}" + RESET)
    print(BOLD + CYAN + "═" * WIDTH + RESET)


def _run(cmd: list[str], label: str) -> int:
    _banner(label)
    print(f"  {DIM}$ {' '.join(cmd)}{RESET}\n")
    return subprocess.run(cmd, cwd=REPO_ROOT).returncode


def _elapsed(seconds: float) -> str:
    h, rem = divmod(int(seconds), 3600)
    m, s = divmod(rem, 60)
    if h:
        return f"{h}h {m}m {s}s"
    if m:
        return f"{m}m {s}s"
    return f"{s}s"


def _preset_table() -> str:
    lines = []
    for name, meta in PRESETS.items():
        lines.append(f"  --preset {name:<10}  {meta['runtime']}")
        lines.append(f"             {meta['description']}")
        lines.append(f"             {DIM}{meta['matrix']}{RESET}")
        lines.append("")
    return "\n".join(lines)


# ─────────────────────────────────────────────────────────────────────────────
# Argument parsing
# ─────────────────────────────────────────────────────────────────────────────

def build_parser() -> argparse.ArgumentParser:
    epilog = textwrap.dedent(f"""
presets
-------
{_preset_table()}
examples
--------
  python run_thesis.py --preset smoke              # quick 2-run pipeline check
  python run_thesis.py --preset light              # 12-run validation run
  python run_thesis.py --preset heavy              # full 1,440-run thesis matrix
  python run_thesis.py --preset heavy --no-resume  # restart from scratch
  python run_thesis.py --preset heavy --sequential # single-core execution

resume from checkpoint
----------------------
  Interrupted runs are checkpointed after every completed seed.
  Re-run the same command to pick up where you left off:
    python run_thesis.py --preset heavy

plot / report only (no benchmark)
-----------------------------------
  python scripts/run_benchmarks.py --use-multiprocessing  # run benchmarks
  # Plots and tables are generated automatically at the end of every run.
""")

    parser = argparse.ArgumentParser(
        prog="run_thesis.py",
        description="E³-Hybrid Thesis — one-command experiment runner.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=epilog,
    )
    parser.add_argument(
        "--preset",
        required=True,
        choices=list(PRESETS.keys()),
        metavar="PRESET",
        help="Experiment scale: smoke | light | heavy | extreme | stress | ablation | sensitivity | complete",
    )
    parser.add_argument(
        "--skip-preflight",
        action="store_true",
        help="Skip the environment check (not recommended).",
    )
    parser.add_argument(
        "--no-resume",
        action="store_true",
        help="Discard existing checkpoints and restart from scratch.",
    )
    parser.add_argument(
        "--sequential",
        action="store_true",
        help="Disable multiprocessing — run seeds one at a time.",
    )
    return parser


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────

def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    preset = PRESETS[args.preset]
    wall_start = time.time()

    print(BOLD + "\n  E³-Hybrid Thesis Experiment Runner" + RESET)
    print(f"  Preset  : {BOLD}{args.preset}{RESET}  —  {preset['description']}")
    print(f"  Matrix  : {preset['matrix']}")
    print(f"  Runtime : {preset['runtime']}")

    has_preflight = 1 if not args.skip_preflight else 0
    has_profiler = 1 if preset["run_profiler"] else 0
    sub_presets = preset.get("sub_presets", [args.preset])
    num_benchmarks = len(sub_presets)
    total_steps = has_preflight + has_profiler + num_benchmarks
    step = 1

    # ── Step 1: Preflight ─────────────────────────────────────────────────────
    if not args.skip_preflight:
        rc = _run([PYTHON, "preflight.py"], f"Step {step}/{total_steps} — Pre-flight System Check")
        step += 1
        if rc != 0:
            print(f"\n{RED}Preflight failed. Fix the issues listed above, then re-run.{RESET}")
            print(f"{DIM}To skip preflight: python run_thesis.py --preset {args.preset} --skip-preflight{RESET}\n")
            return 1
    else:
        print(f"\n  {YELLOW}⚠  Preflight skipped (--skip-preflight).{RESET}")
        step += 1

    # ── Step 2: Algorithm profiler (heavy/extreme only) ───────────────────────
    if preset["run_profiler"]:
        rc = _run(
            [PYTHON, "scripts/profile_algorithms.py"],
            f"Step {step}/{total_steps} — Algorithm Performance Profile",
        )
        step += 1
        if rc != 0:
            print(f"\n{YELLOW}⚠  Profiling failed — continuing to benchmark.{RESET}")

    # ── Step 3+: Benchmark Suites ─────────────────────────────────────────────
    for sub in sub_presets:
        sub_preset_cfg = PRESETS[sub]
        benchmark_cmd = [PYTHON, "scripts/run_benchmarks.py"]
        extra = list(sub_preset_cfg["benchmark_args"])

        if args.no_resume and "--no-resume" not in extra:
            extra.append("--no-resume")
        if args.sequential:
            extra = [a for a in extra if a != "--use-multiprocessing"]

        benchmark_cmd += extra
        rc = _run(benchmark_cmd, f"Step {step}/{total_steps} — Benchmark Suite ({sub})")
        step += 1
        if rc != 0:
            print(f"\n{RED}Benchmark ({sub}) exited with errors (code {rc}).{RESET}")
            print(f"Intermediate checkpoints are preserved. Re-run to resume.\n")
            return rc

    # ── Done ──────────────────────────────────────────────────────────────────
    elapsed = _elapsed(time.time() - wall_start)
    _banner("All Steps Complete")
    print(f"  {GREEN}✔  Finished in {elapsed}.{RESET}\n")

    print("  Generated artefacts:")
    for sub in sub_presets:
        sub_preset_cfg = PRESETS[sub]
        extra = list(sub_preset_cfg["benchmark_args"])
        out_dir = "outputs"
        for idx, arg in enumerate(extra):
            if arg == "--output-dir" and idx + 1 < len(extra):
                out_dir = extra[idx + 1]
                break

        if out_dir == "outputs":
            outputs = [
                ("outputs/benchmark_results.json",                    "Benchmark results JSON"),
                ("outputs/statistical_tables.md",                      "Statistical hypothesis tables"),
                ("outputs/energy_consumption_comparison.pdf",          "Energy comparison figure"),
                ("outputs/thesis_results/environment_snapshot.json",   "Environment snapshot"),
                ("outputs/thesis_results/reproducibility_manifest.json","Reproducibility manifest"),
            ]
        else:
            outputs = [
                (f"{out_dir}/benchmark_results.json",                  "Benchmark results JSON"),
                (f"{out_dir}/statistical_tables.md",                   "Statistical hypothesis tables"),
                (f"{out_dir}/benchmark_summary.md",                    "Benchmark executive summary"),
                (f"{out_dir}/reproducibility_manifest.json",            "Reproducibility manifest"),
            ]
        print(f"\n  {BOLD}[Preset: {sub}]{RESET}")
        for rel, desc in outputs:
            exists = (REPO_ROOT / rel).exists()
            mark = f"{GREEN}✔{RESET}" if exists else f"{YELLOW}?{RESET}"
            print(f"    {mark}  {rel}")
            print(f"       {DIM}{desc}{RESET}")
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
