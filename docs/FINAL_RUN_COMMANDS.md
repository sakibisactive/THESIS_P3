# E3-Hybrid Swarm Routing: Final Run Commands Guide

This document is a comprehensive, single-source command-line guide for setting up, running, resuming, force-regenerating, and packaging the E3-Hybrid Thesis evaluation experiments.

---

## 1. Environment & Setup Verification

Verify that your system dependencies, Python environment, and SUMO installations are correctly configured:

```bash
# 1. Check Python virtual environment activation and location
which python
python --version

# 2. Check SUMO binary installation and path configuration
which sumo
sumo --version

# 3. Check installed python dependencies
pip list | grep -E "traci|sumolib|numpy|scipy|matplotlib|pydantic|pyyaml"

# 4. Clean up any zombie TraCI/SUMO processes from previous runs
killall sumo sumo-gui 2>/dev/null || true
```

---

## 2. Preflight Check

Always execute the preflight script before launching any experiment runs to validate file paths, write permissions, and network checksum integrity:

```bash
python preflight.py
```

---

## 3. Preset Benchmark Execution Commands

Run the thesis benchmark runner using the pipeline wrapper (`run_thesis.py`). The presets configure the duration, scale, and resource usage:

### A. Smoke Test (Fast Dry-Run)
* **Goal**: Validate that the simulation and routing pipeline executes end-to-end.
* **Scale**: 2 runs, ~30 seconds.
```bash
python run_thesis.py --preset smoke
```

### B. Light Run
* **Goal**: Verify metrics, statistical table compilation, and plot exports with a small sample.
* **Scale**: 12 runs, ~5 minutes.
```bash
python run_thesis.py --preset light
```

### C. Heavy Run (Full Thesis Evaluation Matrix)
* **Goal**: Execute the **official 1,440-run thesis baseline benchmark matrix** using evaluations overrides (max_iterations = 15 for E3-Hybrid, and max_iterations = 5 for ACO, BCO, PSO).
* **Scale**: 1,440 runs, parallel execution using multiprocessing (4 cores), ~1.5 hours.
```bash
python run_thesis.py --preset heavy
```

### D. Extreme Run
* **Goal**: Run the full matrix without resource clamps (runs swarm algorithms with 50 iterations and 50 agents).
* **Scale**: 1,440 runs, ~4–8 hours.
```bash
python run_thesis.py --preset extreme
```

---

## 4. Checkpoint & Resume Commands

Simulation runs are automatically cached on a per-seed basis under `outputs/intermediate/`. If the heavy benchmark run is interrupted:

### Resume Execution (Preserving completed runs)
To safely resume and skip already completed runs, re-execute the preset command:
```bash
python run_thesis.py --preset heavy
```
Alternatively, call the benchmark script directly:
```bash
.venv/bin/python scripts/run_benchmarks.py --use-multiprocessing
```

---

## 5. Clean Restart Command

To discard existing checkpoint caches and regenerate all 1,440 runs completely from scratch:

```bash
python run_thesis.py --preset heavy --no-resume
```
Or directly via the runner script:
```bash
.venv/bin/python scripts/run_benchmarks.py --use-multiprocessing --no-resume
```

---

## 6. Report and Plot Force-Regeneration

If you want to force-regenerate the consolidated datasets, statistical significance tables, and plots from the cached checkpoints under `outputs/intermediate/` **without re-running any simulations**:

```bash
.venv/bin/python scripts/run_benchmarks.py --use-multiprocessing
```

This will automatically:
1. Scan `outputs/intermediate/` for completed seed JSONs.
2. Validate each checkpoint against the schema.
3. Consolidate results into `outputs/benchmark_results.json` and `outputs/benchmark_results.csv`.
4. Run hypothesis tests (Welch t-test, Mann-Whitney U, Cohen's d) and write `outputs/statistical_tables.md`.
5. Export comparative boxplots, CDFs, and ambulance response time curves.
6. Generate the reproducibility manifests.

---

## 7. Integrity Checksums

To verify the integrity of the generated consolidated datasets, calculate and compare their SHA256 checksums:

```bash
# Calculate SHA256 of the compiled benchmark outputs
sha256sum outputs/benchmark_results.json
sha256sum outputs/benchmark_results.csv
sha256sum outputs/statistical_tables.md
sha256sum outputs/reproducibility_manifest.json
```

---

## 8. Packaging & Archiving Outputs

Once the evaluation is complete and verification checksums are confirmed, pack the publication-ready figures, tables, datasets, and manifests into a single compressed tarball:

```bash
tar -czvf v1.0-thesis-results.tar.gz \
    outputs/*.pdf \
    outputs/*.png \
    outputs/*.svg \
    outputs/statistical_tables.md \
    outputs/benchmark_summary.md \
    outputs/benchmark_results.csv \
    outputs/reproducibility_manifest.json
```
