# Thesis Evaluation: Statistical Significance Analysis

## Scenario: Stress Normal

### Statistical Summary: Average Travel Time (s)

| Algorithm | Sample Size (N) | Mean | Median | Std Dev | 95% Confidence Interval |
| :--- | :---: | :---: | :---: | :---: | :---: |
| Dijkstra | 3 | 166.897 | 165.007 | 4.040 | [156.860, 176.934] |
| AStar | 3 | 166.897 | 165.007 | 4.040 | [156.860, 176.934] |
| ACO | 3 | 154.855 | 155.601 | 1.676 | [150.690, 159.020] |
| BCO | 3 | 167.912 | 168.066 | 0.742 | [166.069, 169.756] |
| PSO | 3 | 144.288 | 143.686 | 2.850 | [137.208, 151.369] |
| E3-Hybrid | 3 | 154.938 | 154.791 | 3.436 | [146.402, 163.473] |

### Hypothesis Testing: Pairwise Reroute Significance

| Comparison (A vs B) | Welch t-stat | t-p-value | Sig (t) | Mann-Whitney U | U-p-value | Sig (U) | Cohen's d | Effect Size |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| AStar vs Dijkstra | 0.000 | 1.000e+00 | No | 4.5 | 1.000e+00 | No | 0.000 | negligible |
| ACO vs Dijkstra | -4.768 | 2.274e-02 | Yes* | 0.0 | 1.000e-01 | No | -3.893 | large |
| BCO vs Dijkstra | 0.428 | 7.079e-01 | No | 6.0 | 7.000e-01 | No | 0.350 | small |
| PSO vs Dijkstra | -7.920 | 2.120e-03 | Yes* | 0.0 | 1.000e-01 | No | -6.466 | large |
| E3-Hybrid vs Dijkstra | -3.905 | 1.833e-02 | Yes* | 0.0 | 1.000e-01 | No | -3.189 | large |

### Hypothesis Testing: E3-Hybrid Pairwise Significance

| Comparison (A vs B) | Welch t-stat | t-p-value | Sig (t) | Mann-Whitney U | U-p-value | Sig (U) | Cohen's d | Effect Size |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| E3-Hybrid vs ACO | 0.037 | 9.726e-01 | No | 4.0 | 1.000e+00 | No | 0.031 | negligible |
| E3-Hybrid vs Dijkstra | -3.905 | 1.833e-02 | Yes* | 0.0 | 1.000e-01 | No | -3.189 | large |
| E3-Hybrid vs PSO | 4.132 | 1.551e-02 | Yes* | 9.0 | 1.000e-01 | No | 3.373 | large |

---

## Scenario: Stress Closures

### Statistical Summary: Average Travel Time (s)

| Algorithm | Sample Size (N) | Mean | Median | Std Dev | 95% Confidence Interval |
| :--- | :---: | :---: | :---: | :---: | :---: |
| Dijkstra | 3 | 165.883 | 164.332 | 2.853 | [158.796, 172.970] |
| AStar | 3 | 165.883 | 164.332 | 2.853 | [158.796, 172.970] |
| ACO | 3 | 153.015 | 154.334 | 2.468 | [146.883, 159.147] |
| BCO | 3 | 165.805 | 165.663 | 1.014 | [163.286, 168.324] |
| PSO | 3 | 143.547 | 142.989 | 2.242 | [137.976, 149.117] |
| E3-Hybrid | 3 | 154.938 | 154.791 | 3.436 | [146.402, 163.473] |

### Hypothesis Testing: Pairwise Reroute Significance

| Comparison (A vs B) | Welch t-stat | t-p-value | Sig (t) | Mann-Whitney U | U-p-value | Sig (U) | Cohen's d | Effect Size |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| AStar vs Dijkstra | 0.000 | 1.000e+00 | No | 4.5 | 1.000e+00 | No | 0.000 | negligible |
| ACO vs Dijkstra | -5.908 | 4.381e-03 | Yes* | 0.0 | 1.000e-01 | No | -4.824 | large |
| BCO vs Dijkstra | -0.045 | 9.676e-01 | No | 6.0 | 7.000e-01 | No | -0.037 | negligible |
| PSO vs Dijkstra | -10.661 | 5.806e-04 | Yes* | 0.0 | 1.000e-01 | No | -8.705 | large |
| E3-Hybrid vs Dijkstra | -4.245 | 1.418e-02 | Yes* | 0.0 | 1.000e-01 | No | -3.466 | large |

### Hypothesis Testing: E3-Hybrid Pairwise Significance

| Comparison (A vs B) | Welch t-stat | t-p-value | Sig (t) | Mann-Whitney U | U-p-value | Sig (U) | Cohen's d | Effect Size |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| E3-Hybrid vs ACO | 0.787 | 4.795e-01 | No | 7.0 | 4.000e-01 | No | 0.643 | medium |
| E3-Hybrid vs Dijkstra | -4.245 | 1.418e-02 | Yes* | 0.0 | 1.000e-01 | No | -3.466 | large |
| E3-Hybrid vs PSO | 4.808 | 1.241e-02 | Yes* | 9.0 | 1.000e-01 | No | 3.926 | large |

---

## Scenario: Stress Blackout

### Statistical Summary: Average Travel Time (s)

| Algorithm | Sample Size (N) | Mean | Median | Std Dev | 95% Confidence Interval |
| :--- | :---: | :---: | :---: | :---: | :---: |
| Dijkstra | 3 | 166.897 | 165.007 | 4.040 | [156.860, 176.934] |
| AStar | 3 | 166.897 | 165.007 | 4.040 | [156.860, 176.934] |
| ACO | 3 | 154.855 | 155.601 | 1.676 | [150.690, 159.020] |
| BCO | 3 | 167.912 | 168.066 | 0.742 | [166.069, 169.756] |
| PSO | 3 | 144.288 | 143.686 | 2.850 | [137.208, 151.369] |
| E3-Hybrid | 3 | 154.938 | 154.791 | 3.436 | [146.402, 163.473] |

### Hypothesis Testing: Pairwise Reroute Significance

| Comparison (A vs B) | Welch t-stat | t-p-value | Sig (t) | Mann-Whitney U | U-p-value | Sig (U) | Cohen's d | Effect Size |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| AStar vs Dijkstra | 0.000 | 1.000e+00 | No | 4.5 | 1.000e+00 | No | 0.000 | negligible |
| ACO vs Dijkstra | -4.768 | 2.274e-02 | Yes* | 0.0 | 1.000e-01 | No | -3.893 | large |
| BCO vs Dijkstra | 0.428 | 7.079e-01 | No | 6.0 | 7.000e-01 | No | 0.350 | small |
| PSO vs Dijkstra | -7.920 | 2.120e-03 | Yes* | 0.0 | 1.000e-01 | No | -6.466 | large |
| E3-Hybrid vs Dijkstra | -3.905 | 1.833e-02 | Yes* | 0.0 | 1.000e-01 | No | -3.189 | large |

### Hypothesis Testing: E3-Hybrid Pairwise Significance

| Comparison (A vs B) | Welch t-stat | t-p-value | Sig (t) | Mann-Whitney U | U-p-value | Sig (U) | Cohen's d | Effect Size |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| E3-Hybrid vs ACO | 0.037 | 9.726e-01 | No | 4.0 | 1.000e+00 | No | 0.031 | negligible |
| E3-Hybrid vs Dijkstra | -3.905 | 1.833e-02 | Yes* | 0.0 | 1.000e-01 | No | -3.189 | large |
| E3-Hybrid vs PSO | 4.132 | 1.551e-02 | Yes* | 9.0 | 1.000e-01 | No | 3.373 | large |

---

## Scenario: Stress Failures

### Statistical Summary: Average Travel Time (s)

| Algorithm | Sample Size (N) | Mean | Median | Std Dev | 95% Confidence Interval |
| :--- | :---: | :---: | :---: | :---: | :---: |
| Dijkstra | 3 | 154.153 | 151.309 | 6.579 | [137.809, 170.497] |
| AStar | 3 | 154.153 | 151.309 | 6.579 | [137.809, 170.497] |
| ACO | 3 | 145.582 | 145.913 | 4.280 | [134.949, 156.215] |
| BCO | 3 | 161.541 | 160.772 | 2.281 | [155.875, 167.208] |
| PSO | 3 | 135.252 | 133.202 | 4.119 | [125.020, 145.484] |
| E3-Hybrid | 3 | 139.236 | 140.564 | 4.054 | [129.166, 149.306] |

### Hypothesis Testing: Pairwise Reroute Significance

| Comparison (A vs B) | Welch t-stat | t-p-value | Sig (t) | Mann-Whitney U | U-p-value | Sig (U) | Cohen's d | Effect Size |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| AStar vs Dijkstra | 0.000 | 1.000e+00 | No | 4.5 | 1.000e+00 | No | 0.000 | negligible |
| ACO vs Dijkstra | -1.891 | 1.432e-01 | No | 1.0 | 2.000e-01 | No | -1.544 | large |
| BCO vs Dijkstra | 1.838 | 1.826e-01 | No | 7.0 | 4.000e-01 | No | 1.501 | large |
| PSO vs Dijkstra | -4.218 | 1.941e-02 | Yes* | 0.0 | 1.000e-01 | No | -3.444 | large |
| E3-Hybrid vs Dijkstra | -3.343 | 3.795e-02 | Yes* | 0.0 | 1.000e-01 | No | -2.730 | large |

### Hypothesis Testing: E3-Hybrid Pairwise Significance

| Comparison (A vs B) | Welch t-stat | t-p-value | Sig (t) | Mann-Whitney U | U-p-value | Sig (U) | Cohen's d | Effect Size |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| E3-Hybrid vs ACO | -1.864 | 1.359e-01 | No | 1.0 | 2.000e-01 | No | -1.522 | large |
| E3-Hybrid vs Dijkstra | -3.343 | 3.795e-02 | Yes* | 0.0 | 1.000e-01 | No | -2.730 | large |
| E3-Hybrid vs PSO | 1.194 | 2.984e-01 | No | 8.0 | 2.000e-01 | No | 0.975 | large |

---

## Scenario: Stress Ambulance

### Statistical Summary: Average Travel Time (s)

| Algorithm | Sample Size (N) | Mean | Median | Std Dev | 95% Confidence Interval |
| :--- | :---: | :---: | :---: | :---: | :---: |
| Dijkstra | 3 | 166.897 | 165.007 | 4.040 | [156.860, 176.934] |
| AStar | 3 | 166.897 | 165.007 | 4.040 | [156.860, 176.934] |
| ACO | 3 | 154.855 | 155.601 | 1.676 | [150.690, 159.020] |
| BCO | 3 | 167.912 | 168.066 | 0.742 | [166.069, 169.756] |
| PSO | 3 | 144.288 | 143.686 | 2.850 | [137.208, 151.369] |
| E3-Hybrid | 3 | 154.938 | 154.791 | 3.436 | [146.402, 163.473] |

### Hypothesis Testing: Pairwise Reroute Significance

| Comparison (A vs B) | Welch t-stat | t-p-value | Sig (t) | Mann-Whitney U | U-p-value | Sig (U) | Cohen's d | Effect Size |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| AStar vs Dijkstra | 0.000 | 1.000e+00 | No | 4.5 | 1.000e+00 | No | 0.000 | negligible |
| ACO vs Dijkstra | -4.768 | 2.274e-02 | Yes* | 0.0 | 1.000e-01 | No | -3.893 | large |
| BCO vs Dijkstra | 0.428 | 7.079e-01 | No | 6.0 | 7.000e-01 | No | 0.350 | small |
| PSO vs Dijkstra | -7.920 | 2.120e-03 | Yes* | 0.0 | 1.000e-01 | No | -6.466 | large |
| E3-Hybrid vs Dijkstra | -3.905 | 1.833e-02 | Yes* | 0.0 | 1.000e-01 | No | -3.189 | large |

### Hypothesis Testing: E3-Hybrid Pairwise Significance

| Comparison (A vs B) | Welch t-stat | t-p-value | Sig (t) | Mann-Whitney U | U-p-value | Sig (U) | Cohen's d | Effect Size |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| E3-Hybrid vs ACO | 0.037 | 9.726e-01 | No | 4.0 | 1.000e+00 | No | 0.031 | negligible |
| E3-Hybrid vs Dijkstra | -3.905 | 1.833e-02 | Yes* | 0.0 | 1.000e-01 | No | -3.189 | large |
| E3-Hybrid vs PSO | 4.132 | 1.551e-02 | Yes* | 9.0 | 1.000e-01 | No | 3.373 | large |

---


# Advanced Multi-Objective & Resilience Evaluation

This section presents the advanced multi-objective optimization metrics, emergency priorities, robustness diagnostics, and recovery resilience under failure models.

## Multi-Objective Optimization Indicators

The table below reports the Hypervolume (HV) Indicator (computed using a dynamic reference point set at 1.10x the worst observed objectives) and the Weighted Utility Score (using the thesis weights: Travel Time = 0.7, Energy = 0.2, Safety/Stranded = 0.1). Higher values are superior for both metrics.

| Algorithm | Hypervolume (HV) | Weighted Utility Score | Scenario Win Count | Non-Dominated Run % |
| :--- | :---: | :---: | :---: | :---: |
| PSO | 2.6981e+04 | 1.0000 | 15 | 100.0% |
| ACO | 1.0386e+04 | 0.5783 | 0 | 0.0% |
| **E3-Hybrid** | 6.2660e+03 | 0.5391 | 0 | 0.0% |
| AStar | 6.1421e+03 | 0.2411 | 0 | 0.0% |
| Dijkstra | 6.1421e+03 | 0.2411 | 0 | 0.0% |
| BCO | 4.4728e+03 | 0.1510 | 0 | 0.0% |

## Pairwise Pareto Dominance Ratios

The value at row A, column B represents the fraction of evaluation runs in which Algorithm A Pareto-dominates Algorithm B (i.e. is better or equal in all objectives, and strictly better in at least one).

| Dominates ↓ / Dominated → | ACO | AStar | BCO | Dijkstra | E3-Hybrid | PSO |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| ACO | 0.0% | 60.0% | 100.0% | 60.0% | 40.0% | 0.0% |
| AStar | 0.0% | 0.0% | 73.3% | 0.0% | 0.0% | 0.0% |
| BCO | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% |
| Dijkstra | 0.0% | 0.0% | 73.3% | 0.0% | 0.0% | 0.0% |
| **E3-Hybrid** | 6.7% | 6.7% | 20.0% | 6.7% | 0.0% | 0.0% |
| PSO | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% | 0.0% |

## Dynamic Network Resilience Analysis

For scenarios featuring physical bottlenecks and outages, we report the Performance Loss Area (cumulative speed reduction below limit over time) and Recovery Time (steps to restore average speed above 0.95 of free-flow). Lower is superior.

### Scenario: Stress Closures Scenario

| Algorithm | Performance Loss Area | Recovery Time (steps) |
| :--- | :---: | :---: |
| Dijkstra | 0.000 | 1.0 |
| AStar | 0.000 | 1.0 |
| ACO | 0.000 | 1.0 |
| BCO | 0.000 | 1.0 |
| PSO | 0.000 | 1.0 |
| **E3-Hybrid** | 0.000 | 1.0 |

### Scenario: Stress Blackout Scenario

| Algorithm | Performance Loss Area | Recovery Time (steps) |
| :--- | :---: | :---: |
| Dijkstra | 0.000 | 1.0 |
| AStar | 0.000 | 1.0 |
| ACO | 0.000 | 1.0 |
| BCO | 0.000 | 1.0 |
| PSO | 0.000 | 1.0 |
| **E3-Hybrid** | 0.000 | 1.0 |

### Scenario: Stress Failures Scenario

| Algorithm | Performance Loss Area | Recovery Time (steps) |
| :--- | :---: | :---: |
| Dijkstra | 0.000 | 1.0 |
| AStar | 0.000 | 1.0 |
| ACO | 0.000 | 1.0 |
| BCO | 0.000 | 1.0 |
| PSO | 0.000 | 1.0 |
| **E3-Hybrid** | 0.000 | 1.0 |

## Emergency Prioritization and Corridor Response

Under scenarios with ambulance dispatches, we evaluate the average ambulance response time, dispatch success rate, and emergency corridor yielding duration.

*No ambulance dispatch scenarios found in results.*

## Robustness and Consistency Analysis

We evaluate the stability of travel times across seeds via the Coefficient of Variation (CV = standard deviation / mean). Lower CV indicates higher routing predictability and robustness.

### Scenario: Stress Normal Scenario

| Algorithm | Mean Travel Time (s) | Std Dev (s) | Coefficient of Variation (CV) |
| :--- | :---: | :---: | :---: |
| BCO | 167.91 | 0.61 | 0.0036 |
| ACO | 154.86 | 1.37 | 0.0088 |
| PSO | 144.29 | 2.33 | 0.0161 |
| **E3-Hybrid** | 154.94 | 2.81 | 0.0181 |
| Dijkstra | 166.90 | 3.30 | 0.0198 |
| AStar | 166.90 | 3.30 | 0.0198 |

### Scenario: Stress Closures Scenario

| Algorithm | Mean Travel Time (s) | Std Dev (s) | Coefficient of Variation (CV) |
| :--- | :---: | :---: | :---: |
| BCO | 165.81 | 0.83 | 0.0050 |
| PSO | 143.55 | 1.83 | 0.0128 |
| ACO | 153.02 | 2.02 | 0.0132 |
| Dijkstra | 165.88 | 2.33 | 0.0140 |
| AStar | 165.88 | 2.33 | 0.0140 |
| **E3-Hybrid** | 154.94 | 2.81 | 0.0181 |

### Scenario: Stress Blackout Scenario

| Algorithm | Mean Travel Time (s) | Std Dev (s) | Coefficient of Variation (CV) |
| :--- | :---: | :---: | :---: |
| BCO | 167.91 | 0.61 | 0.0036 |
| ACO | 154.86 | 1.37 | 0.0088 |
| PSO | 144.29 | 2.33 | 0.0161 |
| **E3-Hybrid** | 154.94 | 2.81 | 0.0181 |
| Dijkstra | 166.90 | 3.30 | 0.0198 |
| AStar | 166.90 | 3.30 | 0.0198 |

### Scenario: Stress Failures Scenario

| Algorithm | Mean Travel Time (s) | Std Dev (s) | Coefficient of Variation (CV) |
| :--- | :---: | :---: | :---: |
| BCO | 161.54 | 1.86 | 0.0115 |
| **E3-Hybrid** | 139.24 | 3.31 | 0.0238 |
| ACO | 145.58 | 3.49 | 0.0240 |
| PSO | 135.25 | 3.36 | 0.0249 |
| Dijkstra | 154.15 | 5.37 | 0.0348 |
| AStar | 154.15 | 5.37 | 0.0348 |

### Scenario: Stress Ambulance Scenario

| Algorithm | Mean Travel Time (s) | Std Dev (s) | Coefficient of Variation (CV) |
| :--- | :---: | :---: | :---: |
| BCO | 167.91 | 0.61 | 0.0036 |
| ACO | 154.86 | 1.37 | 0.0088 |
| PSO | 144.29 | 2.33 | 0.0161 |
| **E3-Hybrid** | 154.94 | 2.81 | 0.0181 |
| Dijkstra | 166.90 | 3.30 | 0.0198 |
| AStar | 166.90 | 3.30 | 0.0198 |

