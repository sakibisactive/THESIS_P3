# Thesis Evaluation: Benchmark Executive Summary

This document summarizes the core performance characteristics of E3-Hybrid compared to traditional and metaheuristic routing baselines (Dijkstra, ACO, PSO, BCO, A*) across all 6 evaluation scenarios.

## Overall Key Findings

### Scenario: Normal Traffic

- **Optimal Travel Time Router:** ACO (Mean: 289.103 s)
- **Optimal Energy Efficiency Router:** PSO (Mean: 21.616 kWh)

| Algorithm | Travel Time (s) | TT Delta (%) | Energy (kWh) | Energy Delta (%) |
| :--- | :---: | :---: | :---: | :---: |
| Dijkstra | 294.827 | -0.88% | 27.843 | -11.33% |
| AStar | 294.827 | -0.88% | 27.843 | -11.33% |
| ACO | 289.103 | +1.08% | 27.280 | -9.50% |
| BCO | 293.579 | -0.46% | 26.682 | -7.47% |
| PSO | 303.726 | -3.79% | 21.616 | +14.21% |
| **E3-Hybrid** | **292.226** | **Baseline** | **24.689** | **Baseline** |

### Scenario: Road Closure

- **Optimal Travel Time Router:** ACO (Mean: 291.554 s)
- **Optimal Energy Efficiency Router:** PSO (Mean: 21.614 kWh)

| Algorithm | Travel Time (s) | TT Delta (%) | Energy (kWh) | Energy Delta (%) |
| :--- | :---: | :---: | :---: | :---: |
| Dijkstra | 296.914 | -1.16% | 27.785 | -11.99% |
| AStar | 296.914 | -1.16% | 27.785 | -11.99% |
| ACO | 291.554 | +0.66% | 27.109 | -9.80% |
| BCO | 294.740 | -0.43% | 26.472 | -7.63% |
| PSO | 305.412 | -3.91% | 21.614 | +13.14% |
| **E3-Hybrid** | **293.465** | **Baseline** | **24.454** | **Baseline** |

### Scenario: Progressive Closures

- **Optimal Travel Time Router:** ACO (Mean: 290.513 s)
- **Optimal Energy Efficiency Router:** PSO (Mean: 21.458 kWh)

| Algorithm | Travel Time (s) | TT Delta (%) | Energy (kWh) | Energy Delta (%) |
| :--- | :---: | :---: | :---: | :---: |
| Dijkstra | 296.046 | -1.10% | 27.287 | -11.12% |
| AStar | 296.046 | -1.10% | 27.287 | -11.12% |
| ACO | 290.513 | +0.78% | 26.883 | -9.79% |
| BCO | 293.422 | -0.22% | 26.157 | -7.28% |
| PSO | 304.680 | -3.91% | 21.458 | +13.02% |
| **E3-Hybrid** | **292.781** | **Baseline** | **24.252** | **Baseline** |

### Scenario: Emergency Incident

- **Optimal Travel Time Router:** ACO (Mean: 289.103 s)
- **Optimal Energy Efficiency Router:** PSO (Mean: 21.616 kWh)

| Algorithm | Travel Time (s) | TT Delta (%) | Energy (kWh) | Energy Delta (%) |
| :--- | :---: | :---: | :---: | :---: |
| Dijkstra | 294.827 | -0.88% | 27.843 | -11.33% |
| AStar | 294.827 | -0.88% | 27.843 | -11.33% |
| ACO | 289.103 | +1.08% | 27.280 | -9.50% |
| BCO | 293.579 | -0.46% | 26.682 | -7.47% |
| PSO | 303.726 | -3.79% | 21.616 | +14.21% |
| **E3-Hybrid** | **292.226** | **Baseline** | **24.689** | **Baseline** |

### Scenario: Infrastructure Failure

- **Optimal Travel Time Router:** ACO (Mean: 289.103 s)
- **Optimal Energy Efficiency Router:** PSO (Mean: 21.616 kWh)

| Algorithm | Travel Time (s) | TT Delta (%) | Energy (kWh) | Energy Delta (%) |
| :--- | :---: | :---: | :---: | :---: |
| Dijkstra | 294.827 | -0.88% | 27.843 | -11.33% |
| AStar | 294.827 | -0.88% | 27.843 | -11.33% |
| ACO | 289.103 | +1.08% | 27.280 | -9.50% |
| BCO | 293.579 | -0.46% | 26.682 | -7.47% |
| PSO | 303.726 | -3.79% | 21.616 | +14.21% |
| **E3-Hybrid** | **292.226** | **Baseline** | **24.689** | **Baseline** |

### Scenario: Communication Blackout

- **Optimal Travel Time Router:** ACO (Mean: 289.103 s)
- **Optimal Energy Efficiency Router:** PSO (Mean: 21.616 kWh)

| Algorithm | Travel Time (s) | TT Delta (%) | Energy (kWh) | Energy Delta (%) |
| :--- | :---: | :---: | :---: | :---: |
| Dijkstra | 294.827 | -0.88% | 27.843 | -11.33% |
| AStar | 294.827 | -0.88% | 27.843 | -11.33% |
| ACO | 289.103 | +1.08% | 27.280 | -9.50% |
| BCO | 293.579 | -0.46% | 26.682 | -7.47% |
| PSO | 303.726 | -3.79% | 21.616 | +14.21% |
| **E3-Hybrid** | **292.226** | **Baseline** | **24.689** | **Baseline** |

