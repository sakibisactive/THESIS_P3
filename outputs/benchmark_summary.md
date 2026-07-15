# Thesis Evaluation: Benchmark Executive Summary

This document summarizes the core performance characteristics of E3-Hybrid compared to traditional and metaheuristic routing baselines (Dijkstra, ACO, PSO, BCO, A*) across all 6 evaluation scenarios.

## Overall Key Findings

### Scenario: Normal Traffic

- **Optimal Travel Time Router:** Dijkstra (Mean: 286.132 s)
- **Optimal Energy Efficiency Router:** PSO (Mean: 21.328 kWh)

| Algorithm | Travel Time (s) | TT Delta (%) | Energy (kWh) | Energy Delta (%) |
| :--- | :---: | :---: | :---: | :---: |
| Dijkstra | 286.132 | +1.03% | 26.809 | +21.59% |
| AStar | 286.132 | +1.03% | 26.809 | +21.59% |
| ACO | 292.725 | -1.24% | 27.573 | +18.21% |
| BCO | 300.602 | -3.83% | 28.062 | +16.15% |
| PSO | 303.984 | -4.90% | 21.328 | +52.83% |
| **E3-Hybrid** | **289.087** | **Baseline** | **32.596** | **Baseline** |

### Scenario: Road Closure

- **Optimal Travel Time Router:** Dijkstra (Mean: 288.491 s)
- **Optimal Energy Efficiency Router:** PSO (Mean: 21.363 kWh)

| Algorithm | Travel Time (s) | TT Delta (%) | Energy (kWh) | Energy Delta (%) |
| :--- | :---: | :---: | :---: | :---: |
| Dijkstra | 288.491 | +0.21% | 26.700 | +22.08% |
| AStar | 288.491 | +0.21% | 26.700 | +22.08% |
| ACO | 296.068 | -2.36% | 27.446 | +18.76% |
| BCO | 303.554 | -4.77% | 27.895 | +16.85% |
| PSO | 307.716 | -6.05% | 21.363 | +52.58% |
| **E3-Hybrid** | **289.087** | **Baseline** | **32.596** | **Baseline** |

### Scenario: Progressive Closures

- **Optimal Travel Time Router:** Dijkstra (Mean: 287.262 s)
- **Optimal Energy Efficiency Router:** PSO (Mean: 21.233 kWh)

| Algorithm | Travel Time (s) | TT Delta (%) | Energy (kWh) | Energy Delta (%) |
| :--- | :---: | :---: | :---: | :---: |
| Dijkstra | 287.262 | +0.43% | 26.047 | +23.50% |
| AStar | 287.262 | +0.43% | 26.047 | +23.50% |
| ACO | 293.435 | -1.68% | 26.879 | +19.68% |
| BCO | 303.082 | -4.81% | 27.448 | +17.20% |
| PSO | 307.514 | -6.18% | 21.233 | +51.50% |
| **E3-Hybrid** | **288.502** | **Baseline** | **32.169** | **Baseline** |

### Scenario: Emergency Incident

- **Optimal Travel Time Router:** Dijkstra (Mean: 286.132 s)
- **Optimal Energy Efficiency Router:** PSO (Mean: 21.328 kWh)

| Algorithm | Travel Time (s) | TT Delta (%) | Energy (kWh) | Energy Delta (%) |
| :--- | :---: | :---: | :---: | :---: |
| Dijkstra | 286.132 | +1.03% | 26.809 | +21.59% |
| AStar | 286.132 | +1.03% | 26.809 | +21.59% |
| ACO | 292.725 | -1.24% | 27.573 | +18.21% |
| BCO | 300.602 | -3.83% | 28.062 | +16.15% |
| PSO | 303.984 | -4.90% | 21.328 | +52.83% |
| **E3-Hybrid** | **289.087** | **Baseline** | **32.596** | **Baseline** |

### Scenario: Infrastructure Failure

- **Optimal Travel Time Router:** Dijkstra (Mean: 286.132 s)
- **Optimal Energy Efficiency Router:** PSO (Mean: 21.328 kWh)

| Algorithm | Travel Time (s) | TT Delta (%) | Energy (kWh) | Energy Delta (%) |
| :--- | :---: | :---: | :---: | :---: |
| Dijkstra | 286.132 | +1.03% | 26.809 | +21.59% |
| AStar | 286.132 | +1.03% | 26.809 | +21.59% |
| ACO | 292.725 | -1.24% | 27.573 | +18.21% |
| BCO | 300.602 | -3.83% | 28.062 | +16.15% |
| PSO | 303.984 | -4.90% | 21.328 | +52.83% |
| **E3-Hybrid** | **289.087** | **Baseline** | **32.596** | **Baseline** |

### Scenario: Communication Blackout

- **Optimal Travel Time Router:** Dijkstra (Mean: 286.132 s)
- **Optimal Energy Efficiency Router:** PSO (Mean: 21.328 kWh)

| Algorithm | Travel Time (s) | TT Delta (%) | Energy (kWh) | Energy Delta (%) |
| :--- | :---: | :---: | :---: | :---: |
| Dijkstra | 286.132 | +1.03% | 26.809 | +21.59% |
| AStar | 286.132 | +1.03% | 26.809 | +21.59% |
| ACO | 292.725 | -1.24% | 27.573 | +18.21% |
| BCO | 300.602 | -3.83% | 28.062 | +16.15% |
| PSO | 303.984 | -4.90% | 21.328 | +52.83% |
| **E3-Hybrid** | **289.087** | **Baseline** | **32.596** | **Baseline** |

