# Thesis Evaluation: Benchmark Executive Summary

This document summarizes the core performance characteristics of E3-Hybrid compared to traditional and metaheuristic routing baselines (Dijkstra, ACO, PSO, BCO, A*) across all 6 evaluation scenarios.

## Overall Key Findings

### Scenario: Stress Normal

- **Optimal Travel Time Router:** PSO (Mean: 144.288 s)
- **Optimal Energy Efficiency Router:** PSO (Mean: 135.784 kWh)

| Algorithm | Travel Time (s) | TT Delta (%) | Energy (kWh) | Energy Delta (%) |
| :--- | :---: | :---: | :---: | :---: |
| Dijkstra | 166.897 | -7.17% | 172.400 | +8.65% |
| AStar | 166.897 | -7.17% | 172.400 | +8.65% |
| ACO | 154.855 | +0.05% | 170.395 | +9.93% |
| BCO | 167.912 | -7.73% | 178.943 | +4.68% |
| PSO | 144.288 | +7.38% | 135.784 | +37.95% |
| **E3-Hybrid** | **154.938** | **Baseline** | **187.315** | **Baseline** |

### Scenario: Stress Closures

- **Optimal Travel Time Router:** PSO (Mean: 143.547 s)
- **Optimal Energy Efficiency Router:** PSO (Mean: 134.357 kWh)

| Algorithm | Travel Time (s) | TT Delta (%) | Energy (kWh) | Energy Delta (%) |
| :--- | :---: | :---: | :---: | :---: |
| Dijkstra | 165.883 | -6.60% | 170.949 | +9.57% |
| AStar | 165.883 | -6.60% | 170.949 | +9.57% |
| ACO | 153.015 | +1.26% | 167.882 | +11.58% |
| BCO | 165.805 | -6.55% | 174.620 | +7.27% |
| PSO | 143.547 | +7.94% | 134.357 | +39.42% |
| **E3-Hybrid** | **154.938** | **Baseline** | **187.315** | **Baseline** |

### Scenario: Stress Blackout

- **Optimal Travel Time Router:** PSO (Mean: 144.288 s)
- **Optimal Energy Efficiency Router:** PSO (Mean: 135.784 kWh)

| Algorithm | Travel Time (s) | TT Delta (%) | Energy (kWh) | Energy Delta (%) |
| :--- | :---: | :---: | :---: | :---: |
| Dijkstra | 166.897 | -7.17% | 172.400 | +8.65% |
| AStar | 166.897 | -7.17% | 172.400 | +8.65% |
| ACO | 154.855 | +0.05% | 170.395 | +9.93% |
| BCO | 167.912 | -7.73% | 178.943 | +4.68% |
| PSO | 144.288 | +7.38% | 135.784 | +37.95% |
| **E3-Hybrid** | **154.938** | **Baseline** | **187.315** | **Baseline** |

### Scenario: Stress Failures

- **Optimal Travel Time Router:** PSO (Mean: 135.252 s)
- **Optimal Energy Efficiency Router:** PSO (Mean: 108.768 kWh)

| Algorithm | Travel Time (s) | TT Delta (%) | Energy (kWh) | Energy Delta (%) |
| :--- | :---: | :---: | :---: | :---: |
| Dijkstra | 154.153 | -9.68% | 130.038 | +0.37% |
| AStar | 154.153 | -9.68% | 130.038 | +0.37% |
| ACO | 145.582 | -4.36% | 131.819 | -0.98% |
| BCO | 161.541 | -13.81% | 139.065 | -6.14% |
| PSO | 135.252 | +2.95% | 108.768 | +20.00% |
| **E3-Hybrid** | **139.236** | **Baseline** | **130.521** | **Baseline** |

### Scenario: Stress Ambulance

- **Optimal Travel Time Router:** PSO (Mean: 144.288 s)
- **Optimal Energy Efficiency Router:** PSO (Mean: 135.784 kWh)

| Algorithm | Travel Time (s) | TT Delta (%) | Energy (kWh) | Energy Delta (%) |
| :--- | :---: | :---: | :---: | :---: |
| Dijkstra | 166.897 | -7.17% | 172.400 | +8.65% |
| AStar | 166.897 | -7.17% | 172.400 | +8.65% |
| ACO | 154.855 | +0.05% | 170.395 | +9.93% |
| BCO | 167.912 | -7.73% | 178.943 | +4.68% |
| PSO | 144.288 | +7.38% | 135.784 | +37.95% |
| **E3-Hybrid** | **154.938** | **Baseline** | **187.315** | **Baseline** |

