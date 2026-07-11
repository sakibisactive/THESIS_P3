# E³-Hybrid EV Swarm Routing Simulator

A research simulator for evaluating ACO, BCO, PSO, and the E³-Hybrid algorithm
on large-scale electric vehicle routing in urban road networks under dynamic
disruption scenarios.

---

## Quick Start — One-Command Reproducibility

### 1. Install dependencies

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

> SUMO must also be installed separately and available on `$PATH`.
> Download from: https://sumo.dlr.de/docs/Installing/index.html

### 2. Place the network file

```
data/
└── networks/
    └── midtown_manhattan.net.xml   ← put your compiled SUMO .net.xml here
```

### 3. Verify your environment

```bash
python preflight.py
```

Expected output when everything is ready:

```
  ✔  Python 3.12.3
  ✔  Eclipse SUMO sumo 1.27.1
  ✔  all dependencies
  ✔  midtown_manhattan.net.xml  (SHA256 verified)
  ✔  14.4 GB free disk space
  ✔  4 CPU cores
  ✔  Write permission → outputs/

  ✔  ALL CHECKS PASSED — ready to run benchmarks.
```

---

## Running Experiments

All experiments are launched through `run_thesis.py`. Choose a preset:

| Preset    | Description                                                   | Approx. Time |
|:----------|:--------------------------------------------------------------|:-------------|
| `smoke`   | 2 algorithms × 1 scenario × 25 vehicles × 1 seed (2 runs)    | ~30 s        |
| `light`   | 3 algorithms × 2 scenarios × 25 vehicles × 2 seeds (12 runs) | ~5 min       |
| `heavy`   | **Full thesis matrix** — 6×6×4×10 = 1,440 runs               | ~1–2 h       |
| `extreme` | Same as heavy, research-mode swarm parameters                 | ~4–8 h       |

### Run the full thesis benchmark (recommended)

```bash
python run_thesis.py heavy
```

This single command will:
1. Run `preflight.py` to verify your environment.
2. Profile all 6 routing algorithms and save `reproducibility_manifest.json`.
3. Execute the full 1,440-run Manhattan benchmark matrix in parallel (4 workers).
4. Generate consolidated CSV, statistical tables (Welch t-test, Mann-Whitney U,
   Cohen's d), and publication-ready figures (PNG + PDF + SVG).

### Quick smoke test (verify the pipeline works)

```bash
python run_thesis.py smoke
```

### Resume after interruption

Intermediate results are checkpointed after every completed run under
`outputs/intermediate/`. Simply re-run the same command to resume:

```bash
python run_thesis.py heavy          # resumes automatically
python run_thesis.py heavy --no-resume  # starts from scratch
```

### Force sequential execution (low-memory machines)

```bash
python run_thesis.py heavy --sequential
```

---

## Output Artefacts

After a successful `heavy` run, the following files are generated:

```
outputs/
├── benchmark_manifest.json            # parameters, git commit, algorithm configs
├── statistical_tables.md              # per-scenario hypothesis test tables
├── energy_consumption_comparison.{png,pdf,svg}
├── boxplot_<scenario>.{png,pdf,svg}   # travel-time boxplots per scenario
├── cdf_<scenario>.{png,pdf,svg}       # cumulative distribution functions
├── emergency_<scenario>.{png,pdf,svg} # ambulance response-time plots
├── intermediate/
│   └── run_<scenario>_<alg>_<N>_seed<S>.json   # per-run raw metrics
└── thesis_results/
    ├── environment_snapshot.json      # OS, Python, SUMO, SHA256, CPU info
    └── reproducibility_manifest.json  # algorithm latency/throughput profile
```

---

## Reproducing Results Exactly

To reproduce the published thesis results on a new machine:

1. Install the same SUMO version: **Eclipse SUMO 1.27.1**
2. Place `midtown_manhattan.net.xml` and verify the SHA256 checksum:
   ```
   c2f5702163acf3377f74e03e4bce9598f17aeab54f245edc3daf12de8bf63275
   ```
3. Check out the tagged commit:
   ```bash
   git checkout v0.4-phase4.1-complete   # or the final submission tag
   ```
4. Run:
   ```bash
   python run_thesis.py heavy
   ```

Seeds 1–10 are deterministically fixed. All swarm parameters are locked in
`outputs/benchmark_manifest.json` at the start of each run.

---

## Algorithm Overview

| Algorithm  | Class            | Reference |
|:-----------|:-----------------|:----------|
| Dijkstra   | `DijkstraRouter` | Classic shortest-path baseline |
| A\*        | `AStarRouter`    | Heuristic-guided search with EV energy cost |
| ACO        | `ACORouter`      | Ant Colony System with pheromone evaporation |
| BCO        | `BCORouter`      | Bee Colony Optimization with Waggle-Dance loyalty |
| PSO        | `PSORouter`      | Discrete PSO via Edge Priority Encoding |
| E³-Hybrid  | `E3HybridRouter` | ACO + BCO + PSO with shared Information Blackboard |

---

## Project Structure

```
THESIS/
├── preflight.py                  ← run this first
├── run_thesis.py                 ← main experiment entry point
├── configs/benchmarks/           ← scenario YAML files
├── data/networks/                ← SUMO network files
├── docs/IMPLEMENTATION_STATUS.md ← phase completion checklist
├── outputs/                      ← all generated artefacts
├── scripts/
│   ├── run_benchmarks.py         ← benchmark orchestrator
│   ├── profile_algorithms.py     ← algorithm latency profiler
│   └── generate_benchmark_configs.py
├── src/
│   ├── core/                     ← network, vehicle, battery models
│   ├── routing/                  ← all 6 routing algorithms
│   ├── communication/            ← V2X simulation layer
│   ├── emergency/                ← incident/failure/ambulance system
│   ├── evaluation/               ← metrics, statistics, plotting
│   └── sumo_adapter/             ← TraCI SUMO integration
└── tests/                        ← 133 unit tests (pytest)
```
