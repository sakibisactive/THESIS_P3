# Reproduction Guide

This document is the single reference for setting up, running, and
reproducing the E³-Hybrid EV Swarm Routing experiments.

---

## A. Environment Setup

```bash
# Clone the repository
git clone https://github.com/sakibisactive/THESIS_P3.git THESIS
cd THESIS

# Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate
```

---

## B. Dependency Installation

```bash
# Install all Python dependencies
pip install -e .

# Verify SUMO Python bindings are available
# (eclipse-sumo installs traci + sumolib as Python packages)
pip install eclipse-sumo

# System SUMO binary must also be installed separately:
#   Ubuntu/Debian:  sudo apt install sumo sumo-tools
#   macOS:          brew install sumo
#   Windows:        https://sumo.dlr.de/docs/Installing/index.html
```

---

## C. Network File Placement

Place your compiled SUMO network at:

```
data/networks/midtown_manhattan.net.xml
```

Expected SHA256 checksum (for exact reproducibility):

```
c2f5702163acf3377f74e03e4bce9598f17aeab54f245edc3daf12de8bf63275
```

---

## D. Preflight Check

Always run this before starting any experiment:

```bash
python preflight.py
```

A passing result looks like:

```
  ✔  Python 3.12.3
  ✔  SUMO  →  Eclipse SUMO sumo 1.27.1
  ✔  traci
  ✔  sumolib
  ✔  numpy / scipy / matplotlib / pydantic / pyyaml
  ✔  midtown_manhattan.net.xml  (SHA256 ✔)
  ✔  13.7 GB free disk space
  ✔  4 CPU cores detected
  ✔  Write permission → outputs/

  ✔  ALL CHECKS PASSED — ready to run benchmarks.
```

---

## E. Experiment Commands

### Smoke test — 2 runs, ~30 seconds

```bash
python run_thesis.py --preset smoke
```

Verifies end-to-end pipeline works on your machine.

### Light run — 12 runs, ~5 minutes

```bash
python run_thesis.py --preset light
```

Validates metrics, statistics, and plot generation.

### Heavy run — **Full thesis matrix**, 1,440 runs, ~1–2 hours

```bash
python run_thesis.py --preset heavy
```

This is the **recommended command for producing thesis results**.
It runs:
1. Preflight check
2. Algorithm performance profiler
3. Full benchmark matrix (parallel, 4 workers)
4. Statistical analysis and publication-ready figures

### Extreme run — Research-mode parameters, ~4–8 hours

```bash
python run_thesis.py --preset extreme
```

Same matrix as heavy but swarm algorithms run at full depth
(ACO: 50 ants, BCO: 50 bees, PSO: 50 particles).

---

## F. Full Manhattan Benchmark — Manual Commands

If you prefer to run steps individually:

```bash
# Step 1: Preflight
python preflight.py

# Step 2: Profile algorithm routing speeds
.venv/bin/python scripts/profile_algorithms.py

# Step 3: Run the full 1,440-run benchmark matrix
.venv/bin/python scripts/run_benchmarks.py --use-multiprocessing
```

---

## G. Resume from Checkpoint

Runs are checkpointed after every completed seed under `outputs/intermediate/`.
To resume after any interruption, simply re-run the same command:

```bash
python run_thesis.py --preset heavy
# or
.venv/bin/python scripts/run_benchmarks.py --use-multiprocessing
```

To restart from scratch (clears all checkpoints):

```bash
python run_thesis.py --preset heavy --no-resume
# or
.venv/bin/python scripts/run_benchmarks.py --use-multiprocessing --no-resume
```

---

## H. Regenerate Plots and Statistical Tables

Plots and tables are generated automatically at the end of every benchmark
run. If you need to regenerate them from existing checkpoints without
re-running simulations:

```bash
# Run the benchmarks script with --no-resume to skip already-done runs
# and force recompilation of outputs from existing intermediate files
.venv/bin/python scripts/run_benchmarks.py --use-multiprocessing
```

The script detects all completed checkpoints and compiles results without
re-running them.

---

## I. Export Thesis-Ready Figures and Tables

All publication-ready outputs are generated automatically in
`outputs/`. They are saved in three formats:

| Format | Use case            |
|:-------|:--------------------|
| `.pdf` | LaTeX `\includegraphics` |
| `.png` | Word / slides        |
| `.svg` | Editable vector art  |

Copy the files you need:

```bash
# Copy all PDFs to a thesis-figures directory
mkdir -p ~/thesis-figures
cp outputs/*.pdf ~/thesis-figures/

# Copy statistical tables
cp outputs/statistical_tables.md ~/thesis-figures/
```

---

## J. Clean Outputs and Rerun from Scratch

```bash
# Remove all benchmark output and intermediate checkpoints
rm -rf outputs/intermediate/ \
       outputs/benchmark_results.json \
       outputs/benchmark_results.csv \
       outputs/*.pdf outputs/*.png outputs/*.svg \
       outputs/statistical_tables.md \
       outputs/benchmark_manifest.json

# Then rerun
python run_thesis.py --preset heavy
```

---

## K. One-Shot Script

To run the entire pipeline with a single command:

```bash
bash scripts/run_everything.sh            # heavy (default)
bash scripts/run_everything.sh smoke      # quick test
bash scripts/run_everything.sh extreme    # research-mode run
```

---

## L. Expected Output Directory Structure

After a successful `heavy` run:

```
outputs/
├── benchmark_manifest.json            # parameters, git hash, algorithm configs
├── statistical_tables.md              # per-scenario hypothesis test tables
│                                      # (Welch t-test, Mann-Whitney U, Cohen's d)
├── energy_consumption_comparison.pdf  # energy profile bar chart
├── energy_consumption_comparison.png
├── energy_consumption_comparison.svg
├── boxplot_<scenario>.{pdf,png,svg}   # travel-time boxplots (6 scenarios)
├── cdf_<scenario>.{pdf,png,svg}       # cumulative distribution functions
├── emergency_<scenario>.{pdf,png,svg} # ambulance response times
├── intermediate/
│   └── run_<scenario>_<alg>_<N>_seed<S>.json  # per-run raw metrics
└── thesis_results/
    ├── environment_snapshot.json           # OS / Python / SUMO / SHA256 / CPU
    └── reproducibility_manifest.json       # algorithm latency + throughput profile
```

---

## M. Reproducibility Checklist

To guarantee identical results on a new machine:

- [ ] SUMO version: **Eclipse SUMO 1.27.1**
- [ ] Python version: **3.12.x**
- [ ] Network file SHA256: `c2f5702163acf3377f74e03e4bce9598f17aeab54f245edc3daf12de8bf63275`
- [ ] Seeds: **1–10** (fixed, hardcoded in benchmark runner)
- [ ] Swarm parameters: **5 iterations, 5 agents** (evaluation-mode, default)
- [ ] Git commit: check `outputs/benchmark_manifest.json` for the locked hash

---

## N. Unit Tests

```bash
# Run the full test suite (133 tests)
.venv/bin/pytest

# Run with coverage report
.venv/bin/pytest --cov=src --cov-report=term-missing
```
