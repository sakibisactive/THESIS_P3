# E³-Hybrid Thesis Commands Cheat Sheet

Here are all the commands grouped together for quick copy-and-paste execution.

---

## 1. Setup & Installation
Run these commands to set up the Python virtual environment and install all dependencies:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
pip install eclipse-sumo
```

---

## 2. Preflight Check
Verify that Python, SUMO, bindings, the Manhattan network file, disk space, and write permissions are correct:

```bash
python preflight.py
```

---

## 3. Profiling Routing Algorithms
Measure routing latencies, peak memory (RSS), and routes per second for all algorithms:

```bash
.venv/bin/python scripts/profile_algorithms.py
```

---

## 4. One-Shot Presets (Recommended)
Run the automated pipeline with one of the predefined presets:

```bash
# Smoke test (2 runs, ~30 seconds)
python run_thesis.py --preset smoke

# Light validation (12 runs, ~5 minutes)
python run_thesis.py --preset light

# Heavy run: Full Thesis Matrix (1,440 runs, ~1-2 hours)
python run_thesis.py --preset heavy

# Extreme run: Research parameters (1,440 runs, ~4-8 hours)
python run_thesis.py --preset extreme
```

---

## 5. Manual Execution & Custom Matrix
Run steps manually using the underlying execution engine:

```bash
.venv/bin/python scripts/run_benchmarks.py --use-multiprocessing
```

To run only specific algorithms or seeds:
```bash
.venv/bin/python scripts/run_benchmarks.py --use-multiprocessing --algorithms Dijkstra,E3-Hybrid --seeds 1-5
```

---

## 6. Interrupt & Resume
If the simulation is interrupted (e.g., due to a power outage or system shutdown), you can resume exactly where you left off. Checkpointing is **automatically active by default**:

```bash
# Resume heavy preset from the last saved checkpoint
python run_thesis.py --preset heavy

# Resume manual run from the last saved checkpoint
.venv/bin/python scripts/run_benchmarks.py --use-multiprocessing
```

To **discard all checkpoints** and restart completely from scratch:
```bash
# Restart preset from scratch
python run_thesis.py --preset heavy --no-resume

# Restart manual run from scratch
.venv/bin/python scripts/run_benchmarks.py --use-multiprocessing --no-resume
```

---

## 7. Output Management & Cleaning
To remove all intermediate checkpoints, consolidated results, and plots:

```bash
rm -rf outputs/intermediate/ \
       outputs/benchmark_results.json \
       outputs/benchmark_results.csv \
       outputs/*.pdf outputs/*.png outputs/*.svg \
       outputs/statistical_tables.md \
       outputs/benchmark_manifest.json
```
