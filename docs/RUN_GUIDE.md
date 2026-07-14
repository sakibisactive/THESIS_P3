# Reproduction & Run Guide

This document is the single reference for setting up, running, and reproducing the E³-Hybrid EV Swarm Routing experiments.

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

Always run this before starting any experiment to verify your system's hardware, software, files, and paths:

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
Verifies end-to-end pipeline works on your machine:
```bash
python run_thesis.py --preset smoke
```

### Light run — 12 runs, ~5 minutes
Validates metrics, statistics, and plot generation:
```bash
python run_thesis.py --preset light
```

### Heavy run — **Full thesis matrix**, 1,440 runs, ~1.5 hours on 4 CPU cores
This is the **command for producing the final baseline thesis results**.
```bash
python run_thesis.py --preset heavy
```
It automatically executes:
1. Preflight check
2. Algorithm performance profiler (`scripts/profile_algorithms.py`)
3. Full benchmark matrix in parallel using multiprocessing (4 workers)
4. Pairwise statistical analysis (Welch's t-test, Mann-Whitney U, Cohen's d)
5. Statistical table compilation and publication-ready figures

### Extreme run — Research-mode parameters, ~4–8 hours
Same matrix as heavy but swarm algorithms run at full depth without resource clamps:
```bash
python run_thesis.py --preset extreme
```
*(Swarm sizes: ACO: 50 ants, BCO: 50 bees, PSO: 50 particles. Iterations: 50 iterations).*

---

## F. Full Manhattan Benchmark — Manual Command & Controls

To manually run the full benchmark from the command line:

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

---

## H. Clean Restart

To discard all intermediate run files and start the benchmark fresh from the beginning (clearing all checkpoints):

```bash
# Run with --no-resume flag
python run_thesis.py --preset heavy --no-resume
# or
.venv/bin/python scripts/run_benchmarks.py --use-multiprocessing --no-resume
```

---

## I. Plot and Statistical Table Generation

Plots and tables are generated automatically at the end of every benchmark run. To force-regenerate them from existing checkpoints without re-running simulations:

```bash
# Recompile outputs from existing intermediate files
.venv/bin/python scripts/run_benchmarks.py --use-multiprocessing
```

The script detects all completed checkpoints under `outputs/intermediate/` and compiles results without executing SUMO.

---

## J. Troubleshooting Commands

If you run into issues during the run, use these diagnostic tools:

```bash
# 1. Verify SUMO environment variables and paths
which sumo
sumo --version

# 2. Check Python virtual environment activation and dependencies
which python
pip list

# 3. Clean up blocked/zombie TraCI port locks from aborted runs
killall sumo sumo-gui 2>/dev/null || true

# 4. Wipe intermediate outputs to force a clean slate
rm -rf outputs/intermediate/ outputs/benchmark_results.json outputs/benchmark_results.csv
```

---

## K. Packaging Thesis-Ready Figures and Tables

To package all publication-ready outputs, statistical reports, and reproducibility files into a single compressed tarball:

```bash
# Create archive of thesis-ready results
tar -czvf v1.0-thesis-results.tar.gz \
    outputs/*.pdf \
    outputs/*.png \
    outputs/*.svg \
    outputs/statistical_tables.md \
    outputs/benchmark_results.csv \
    outputs/reproducibility_manifest.json
```

---

## L. Expected Output Directory Structure

After a successful `heavy` run, your `outputs/` directory will look like this:

```
outputs/
├── benchmark_results.json             # Consolidated results for all completed runs
├── benchmark_results.csv              # Consolidated CSV table of metrics
├── benchmark_manifest.json            # Parameters, git hash, and algorithm configurations
├── statistical_tables.md              # Per-scenario hypothesis test tables:
│                                      #   - Pairwise Reroute Significance (vs Dijkstra)
│                                      #   - E3-Hybrid Pairwise Significance (vs ACO, Dijkstra, PSO)
├── reproducibility_manifest.json      # OS, Python, SUMO, CPU, network SHA256, dependencies
├── energy_consumption_comparison.pdf  # Overall energy consumption comparison plot
├── energy_consumption_comparison.png
├── energy_consumption_comparison.svg
├── boxplot_<scenario>.{pdf,png,svg}   # Travel-time boxplots (6 scenarios)
├── cdf_<scenario>.{pdf,png,svg}       # Cumulative distribution functions
├── emergency_<scenario>.{pdf,png,svg} # Ambulance response times
├── intermediate/
│   └── run_<scenario>_<alg>_<N>_seed<S>.json  # Per-run raw metrics
└── thesis_results/
    ├── environment_snapshot.json      # Profiler system environment snapshot
    └── reproducibility_manifest.json  # Algorithm latency and throughput profile
```

---

## M. Reproducibility Checklist

To guarantee identical results on a new machine:

- [ ] **SUMO version:** Eclipse SUMO 1.27.1
- [ ] **Python version:** 3.12.x
- [ ] **Network file SHA256:** `c2f5702163acf3377f74e03e4bce9598f17aeab54f245edc3daf12de8bf63275`
- [ ] **Seeds:** 1–10 (fixed, hardcoded in benchmark runner)
- [ ] **Swarm parameters (Evaluation Mode Overrides):**
  - ACO: 5 ants, 5 iterations
  - BCO: 5 bees, 5 iterations
  - PSO: 5 particles, 5 iterations
  - **E3-Hybrid: 15 iterations**
- [ ] **Git commit/tag:** Tag `v1.0-thesis-baseline` checked out locally.

---

## N. Unit Tests

```bash
# Run the full test suite (136 tests)
.venv/bin/pytest

# Run with coverage report
.venv/bin/pytest --cov=src --cov-report=term-missing
```
