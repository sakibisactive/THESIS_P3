# Thesis Evaluation: Benchmark Executive Summary

This document summarizes the core performance characteristics of E3-Hybrid compared to traditional and metaheuristic routing baselines (Dijkstra, ACO, PSO, BCO, A*) across all 6 evaluation scenarios.

## Overall Key Findings

### Scenario: Normal Traffic

- **Optimal Travel Time Router:** E3-Hybrid-NoPSO (Mean: 269.806 s)
- **Optimal Energy Efficiency Router:** E3-Hybrid-NoBCO (Mean: 33.701 kWh)

| Algorithm | Travel Time (s) | TT Delta (%) | Energy (kWh) | Energy Delta (%) |
| :--- | :---: | :---: | :---: | :---: |
| **E3-Hybrid** | **278.392** | **Baseline** | **51.721** | **Baseline** |
| E3-Hybrid-NoACO | 282.066 | -1.30% | 39.231 | +31.84% |
| E3-Hybrid-NoBCO | 271.448 | +2.56% | 33.701 | +53.47% |
| E3-Hybrid-NoPSO | 269.806 | +3.18% | 43.197 | +19.73% |
| E3-Hybrid-NoElite | 279.230 | -0.30% | 51.850 | -0.25% |
| E3-Hybrid-WithAdaptive | 278.392 | +0.00% | 51.721 | +0.00% |

### Scenario: Road Closure

- **Optimal Travel Time Router:** E3-Hybrid-NoPSO (Mean: 269.266 s)
- **Optimal Energy Efficiency Router:** E3-Hybrid-NoBCO (Mean: 33.335 kWh)

| Algorithm | Travel Time (s) | TT Delta (%) | Energy (kWh) | Energy Delta (%) |
| :--- | :---: | :---: | :---: | :---: |
| **E3-Hybrid** | **278.392** | **Baseline** | **51.721** | **Baseline** |
| E3-Hybrid-NoACO | 283.135 | -1.68% | 38.520 | +34.27% |
| E3-Hybrid-NoBCO | 272.594 | +2.13% | 33.335 | +55.15% |
| E3-Hybrid-NoPSO | 269.266 | +3.39% | 42.145 | +22.72% |
| E3-Hybrid-NoElite | 279.230 | -0.30% | 51.850 | -0.25% |
| E3-Hybrid-WithAdaptive | 278.392 | +0.00% | 51.721 | +0.00% |

### Scenario: Progressive Closures

- **Optimal Travel Time Router:** E3-Hybrid-NoPSO (Mean: 269.922 s)
- **Optimal Energy Efficiency Router:** E3-Hybrid-NoBCO (Mean: 33.080 kWh)

| Algorithm | Travel Time (s) | TT Delta (%) | Energy (kWh) | Energy Delta (%) |
| :--- | :---: | :---: | :---: | :---: |
| **E3-Hybrid** | **277.222** | **Baseline** | **50.868** | **Baseline** |
| E3-Hybrid-NoACO | 282.539 | -1.88% | 38.073 | +33.60% |
| E3-Hybrid-NoBCO | 271.678 | +2.04% | 33.080 | +53.77% |
| E3-Hybrid-NoPSO | 269.922 | +2.70% | 41.511 | +22.54% |
| E3-Hybrid-NoElite | 277.672 | -0.16% | 50.786 | +0.16% |
| E3-Hybrid-WithAdaptive | 277.222 | +0.00% | 50.868 | +0.00% |

### Scenario: Emergency Incident

- **Optimal Travel Time Router:** E3-Hybrid-NoPSO (Mean: 269.806 s)
- **Optimal Energy Efficiency Router:** E3-Hybrid-NoBCO (Mean: 33.701 kWh)

| Algorithm | Travel Time (s) | TT Delta (%) | Energy (kWh) | Energy Delta (%) |
| :--- | :---: | :---: | :---: | :---: |
| **E3-Hybrid** | **278.392** | **Baseline** | **51.721** | **Baseline** |
| E3-Hybrid-NoACO | 282.066 | -1.30% | 39.231 | +31.84% |
| E3-Hybrid-NoBCO | 271.448 | +2.56% | 33.701 | +53.47% |
| E3-Hybrid-NoPSO | 269.806 | +3.18% | 43.197 | +19.73% |
| E3-Hybrid-NoElite | 279.230 | -0.30% | 51.850 | -0.25% |
| E3-Hybrid-WithAdaptive | 278.392 | +0.00% | 51.721 | +0.00% |

### Scenario: Infrastructure Failure

- **Optimal Travel Time Router:** E3-Hybrid-NoPSO (Mean: 269.806 s)
- **Optimal Energy Efficiency Router:** E3-Hybrid-NoBCO (Mean: 33.701 kWh)

| Algorithm | Travel Time (s) | TT Delta (%) | Energy (kWh) | Energy Delta (%) |
| :--- | :---: | :---: | :---: | :---: |
| **E3-Hybrid** | **278.392** | **Baseline** | **51.721** | **Baseline** |
| E3-Hybrid-NoACO | 282.066 | -1.30% | 39.231 | +31.84% |
| E3-Hybrid-NoBCO | 271.448 | +2.56% | 33.701 | +53.47% |
| E3-Hybrid-NoPSO | 269.806 | +3.18% | 43.197 | +19.73% |
| E3-Hybrid-NoElite | 279.230 | -0.30% | 51.850 | -0.25% |
| E3-Hybrid-WithAdaptive | 278.392 | +0.00% | 51.721 | +0.00% |

### Scenario: Communication Blackout

- **Optimal Travel Time Router:** E3-Hybrid-NoPSO (Mean: 269.806 s)
- **Optimal Energy Efficiency Router:** E3-Hybrid-NoBCO (Mean: 33.701 kWh)

| Algorithm | Travel Time (s) | TT Delta (%) | Energy (kWh) | Energy Delta (%) |
| :--- | :---: | :---: | :---: | :---: |
| **E3-Hybrid** | **278.392** | **Baseline** | **51.721** | **Baseline** |
| E3-Hybrid-NoACO | 282.066 | -1.30% | 39.231 | +31.84% |
| E3-Hybrid-NoBCO | 271.448 | +2.56% | 33.701 | +53.47% |
| E3-Hybrid-NoPSO | 269.806 | +3.18% | 43.197 | +19.73% |
| E3-Hybrid-NoElite | 279.230 | -0.30% | 51.850 | -0.25% |
| E3-Hybrid-WithAdaptive | 278.392 | +0.00% | 51.721 | +0.00% |

