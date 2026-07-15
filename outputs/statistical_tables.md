# Thesis Evaluation: Statistical Significance Analysis

## Scenario: Normal Traffic

### Statistical Summary: Average Travel Time (s)

| Algorithm | Sample Size (N) | Mean | Median | Std Dev | 95% Confidence Interval |
| :--- | :---: | :---: | :---: | :---: | :---: |
| Dijkstra | 12 | 286.132 | 282.532 | 15.109 | [276.533, 295.732] |
| AStar | 12 | 286.132 | 282.532 | 15.109 | [276.533, 295.732] |
| ACO | 12 | 292.725 | 290.582 | 27.634 | [275.168, 310.283] |
| BCO | 12 | 300.602 | 298.062 | 23.646 | [285.577, 315.626] |
| PSO | 12 | 303.984 | 298.121 | 30.128 | [284.842, 323.127] |
| E3-Hybrid | 12 | 289.087 | 288.074 | 20.929 | [275.790, 302.385] |

### Hypothesis Testing: Pairwise Reroute Significance

| Comparison (A vs B) | Welch t-stat | t-p-value | Sig (t) | Mann-Whitney U | U-p-value | Sig (U) | Cohen's d | Effect Size |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| AStar vs Dijkstra | 0.000 | 1.000e+00 | No | 72.0 | 1.000e+00 | No | 0.000 | negligible |
| ACO vs Dijkstra | 0.725 | 4.782e-01 | No | 79.0 | 7.075e-01 | No | 0.296 | small |
| BCO vs Dijkstra | 1.786 | 9.029e-02 | No | 100.0 | 1.124e-01 | No | 0.729 | medium |
| PSO vs Dijkstra | 1.835 | 8.496e-02 | No | 93.0 | 2.366e-01 | No | 0.749 | medium |
| E3-Hybrid vs Dijkstra | 0.397 | 6.959e-01 | No | 70.0 | 9.310e-01 | No | 0.162 | negligible |

### Hypothesis Testing: E3-Hybrid Pairwise Significance

| Comparison (A vs B) | Welch t-stat | t-p-value | Sig (t) | Mann-Whitney U | U-p-value | Sig (U) | Cohen's d | Effect Size |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| E3-Hybrid vs ACO | -0.364 | 7.199e-01 | No | 70.0 | 9.310e-01 | No | -0.148 | negligible |
| E3-Hybrid vs Dijkstra | 0.397 | 6.959e-01 | No | 70.0 | 9.310e-01 | No | 0.162 | negligible |
| E3-Hybrid vs PSO | -1.407 | 1.752e-01 | No | 51.0 | 2.366e-01 | No | -0.574 | medium |

---

## Scenario: Road Closure

### Statistical Summary: Average Travel Time (s)

| Algorithm | Sample Size (N) | Mean | Median | Std Dev | 95% Confidence Interval |
| :--- | :---: | :---: | :---: | :---: | :---: |
| Dijkstra | 12 | 288.491 | 284.904 | 16.642 | [277.917, 299.065] |
| AStar | 12 | 288.491 | 284.904 | 16.642 | [277.917, 299.065] |
| ACO | 12 | 296.068 | 292.330 | 27.331 | [278.702, 313.433] |
| BCO | 12 | 303.554 | 298.094 | 24.251 | [288.145, 318.962] |
| PSO | 12 | 307.716 | 300.708 | 31.798 | [287.512, 327.919] |
| E3-Hybrid | 12 | 289.087 | 288.074 | 20.929 | [275.790, 302.385] |

### Hypothesis Testing: Pairwise Reroute Significance

| Comparison (A vs B) | Welch t-stat | t-p-value | Sig (t) | Mann-Whitney U | U-p-value | Sig (U) | Cohen's d | Effect Size |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| AStar vs Dijkstra | 0.000 | 1.000e+00 | No | 72.0 | 1.000e+00 | No | 0.000 | negligible |
| ACO vs Dijkstra | 0.820 | 4.227e-01 | No | 79.0 | 7.075e-01 | No | 0.335 | small |
| BCO vs Dijkstra | 1.774 | 9.169e-02 | No | 100.0 | 1.124e-01 | No | 0.724 | medium |
| PSO vs Dijkstra | 1.856 | 8.136e-02 | No | 94.0 | 2.145e-01 | No | 0.758 | medium |
| E3-Hybrid vs Dijkstra | 0.077 | 9.392e-01 | No | 69.0 | 8.852e-01 | No | 0.032 | negligible |

### Hypothesis Testing: E3-Hybrid Pairwise Significance

| Comparison (A vs B) | Welch t-stat | t-p-value | Sig (t) | Mann-Whitney U | U-p-value | Sig (U) | Cohen's d | Effect Size |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| E3-Hybrid vs ACO | -0.702 | 4.903e-01 | No | 62.0 | 5.834e-01 | No | -0.287 | small |
| E3-Hybrid vs Dijkstra | 0.077 | 9.392e-01 | No | 69.0 | 8.852e-01 | No | 0.032 | negligible |
| E3-Hybrid vs PSO | -1.695 | 1.064e-01 | No | 49.0 | 1.939e-01 | No | -0.692 | medium |

---

## Scenario: Progressive Closures

### Statistical Summary: Average Travel Time (s)

| Algorithm | Sample Size (N) | Mean | Median | Std Dev | 95% Confidence Interval |
| :--- | :---: | :---: | :---: | :---: | :---: |
| Dijkstra | 12 | 287.262 | 284.136 | 16.870 | [276.543, 297.981] |
| AStar | 12 | 287.262 | 284.136 | 16.870 | [276.543, 297.981] |
| ACO | 12 | 293.435 | 292.017 | 24.549 | [277.837, 309.032] |
| BCO | 12 | 303.082 | 298.094 | 25.674 | [286.769, 319.394] |
| PSO | 12 | 307.514 | 300.731 | 32.204 | [287.053, 327.976] |
| E3-Hybrid | 12 | 288.502 | 288.074 | 21.148 | [275.065, 301.939] |

### Hypothesis Testing: Pairwise Reroute Significance

| Comparison (A vs B) | Welch t-stat | t-p-value | Sig (t) | Mann-Whitney U | U-p-value | Sig (U) | Cohen's d | Effect Size |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| AStar vs Dijkstra | 0.000 | 1.000e+00 | No | 72.0 | 1.000e+00 | No | 0.000 | negligible |
| ACO vs Dijkstra | 0.718 | 4.814e-01 | No | 81.0 | 6.236e-01 | No | 0.293 | small |
| BCO vs Dijkstra | 1.784 | 9.042e-02 | No | 100.0 | 1.124e-01 | No | 0.728 | medium |
| PSO vs Dijkstra | 1.930 | 7.090e-02 | No | 93.0 | 2.366e-01 | No | 0.788 | medium |
| E3-Hybrid vs Dijkstra | 0.159 | 8.754e-01 | No | 71.0 | 9.770e-01 | No | 0.065 | negligible |

### Hypothesis Testing: E3-Hybrid Pairwise Significance

| Comparison (A vs B) | Welch t-stat | t-p-value | Sig (t) | Mann-Whitney U | U-p-value | Sig (U) | Cohen's d | Effect Size |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| E3-Hybrid vs ACO | -0.527 | 6.033e-01 | No | 63.0 | 6.236e-01 | No | -0.215 | small |
| E3-Hybrid vs Dijkstra | 0.159 | 8.754e-01 | No | 71.0 | 9.770e-01 | No | 0.065 | negligible |
| E3-Hybrid vs PSO | -1.709 | 1.037e-01 | No | 45.0 | 1.260e-01 | No | -0.698 | medium |

---

## Scenario: Emergency Incident

### Statistical Summary: Average Travel Time (s)

| Algorithm | Sample Size (N) | Mean | Median | Std Dev | 95% Confidence Interval |
| :--- | :---: | :---: | :---: | :---: | :---: |
| Dijkstra | 12 | 286.132 | 282.532 | 15.109 | [276.533, 295.732] |
| AStar | 12 | 286.132 | 282.532 | 15.109 | [276.533, 295.732] |
| ACO | 12 | 292.725 | 290.582 | 27.634 | [275.168, 310.283] |
| BCO | 12 | 300.602 | 298.062 | 23.646 | [285.577, 315.626] |
| PSO | 12 | 303.984 | 298.121 | 30.128 | [284.842, 323.127] |
| E3-Hybrid | 12 | 289.087 | 288.074 | 20.929 | [275.790, 302.385] |

### Hypothesis Testing: Pairwise Reroute Significance

| Comparison (A vs B) | Welch t-stat | t-p-value | Sig (t) | Mann-Whitney U | U-p-value | Sig (U) | Cohen's d | Effect Size |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| AStar vs Dijkstra | 0.000 | 1.000e+00 | No | 72.0 | 1.000e+00 | No | 0.000 | negligible |
| ACO vs Dijkstra | 0.725 | 4.782e-01 | No | 79.0 | 7.075e-01 | No | 0.296 | small |
| BCO vs Dijkstra | 1.786 | 9.029e-02 | No | 100.0 | 1.124e-01 | No | 0.729 | medium |
| PSO vs Dijkstra | 1.835 | 8.496e-02 | No | 93.0 | 2.366e-01 | No | 0.749 | medium |
| E3-Hybrid vs Dijkstra | 0.397 | 6.959e-01 | No | 70.0 | 9.310e-01 | No | 0.162 | negligible |

### Hypothesis Testing: E3-Hybrid Pairwise Significance

| Comparison (A vs B) | Welch t-stat | t-p-value | Sig (t) | Mann-Whitney U | U-p-value | Sig (U) | Cohen's d | Effect Size |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| E3-Hybrid vs ACO | -0.364 | 7.199e-01 | No | 70.0 | 9.310e-01 | No | -0.148 | negligible |
| E3-Hybrid vs Dijkstra | 0.397 | 6.959e-01 | No | 70.0 | 9.310e-01 | No | 0.162 | negligible |
| E3-Hybrid vs PSO | -1.407 | 1.752e-01 | No | 51.0 | 2.366e-01 | No | -0.574 | medium |

---

## Scenario: Infrastructure Failure

### Statistical Summary: Average Travel Time (s)

| Algorithm | Sample Size (N) | Mean | Median | Std Dev | 95% Confidence Interval |
| :--- | :---: | :---: | :---: | :---: | :---: |
| Dijkstra | 12 | 286.132 | 282.532 | 15.109 | [276.533, 295.732] |
| AStar | 12 | 286.132 | 282.532 | 15.109 | [276.533, 295.732] |
| ACO | 12 | 292.725 | 290.582 | 27.634 | [275.168, 310.283] |
| BCO | 12 | 300.602 | 298.062 | 23.646 | [285.577, 315.626] |
| PSO | 12 | 303.984 | 298.121 | 30.128 | [284.842, 323.127] |
| E3-Hybrid | 12 | 289.087 | 288.074 | 20.929 | [275.790, 302.385] |

### Hypothesis Testing: Pairwise Reroute Significance

| Comparison (A vs B) | Welch t-stat | t-p-value | Sig (t) | Mann-Whitney U | U-p-value | Sig (U) | Cohen's d | Effect Size |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| AStar vs Dijkstra | 0.000 | 1.000e+00 | No | 72.0 | 1.000e+00 | No | 0.000 | negligible |
| ACO vs Dijkstra | 0.725 | 4.782e-01 | No | 79.0 | 7.075e-01 | No | 0.296 | small |
| BCO vs Dijkstra | 1.786 | 9.029e-02 | No | 100.0 | 1.124e-01 | No | 0.729 | medium |
| PSO vs Dijkstra | 1.835 | 8.496e-02 | No | 93.0 | 2.366e-01 | No | 0.749 | medium |
| E3-Hybrid vs Dijkstra | 0.397 | 6.959e-01 | No | 70.0 | 9.310e-01 | No | 0.162 | negligible |

### Hypothesis Testing: E3-Hybrid Pairwise Significance

| Comparison (A vs B) | Welch t-stat | t-p-value | Sig (t) | Mann-Whitney U | U-p-value | Sig (U) | Cohen's d | Effect Size |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| E3-Hybrid vs ACO | -0.364 | 7.199e-01 | No | 70.0 | 9.310e-01 | No | -0.148 | negligible |
| E3-Hybrid vs Dijkstra | 0.397 | 6.959e-01 | No | 70.0 | 9.310e-01 | No | 0.162 | negligible |
| E3-Hybrid vs PSO | -1.407 | 1.752e-01 | No | 51.0 | 2.366e-01 | No | -0.574 | medium |

---

## Scenario: Communication Blackout

### Statistical Summary: Average Travel Time (s)

| Algorithm | Sample Size (N) | Mean | Median | Std Dev | 95% Confidence Interval |
| :--- | :---: | :---: | :---: | :---: | :---: |
| Dijkstra | 12 | 286.132 | 282.532 | 15.109 | [276.533, 295.732] |
| AStar | 12 | 286.132 | 282.532 | 15.109 | [276.533, 295.732] |
| ACO | 12 | 292.725 | 290.582 | 27.634 | [275.168, 310.283] |
| BCO | 12 | 300.602 | 298.062 | 23.646 | [285.577, 315.626] |
| PSO | 12 | 303.984 | 298.121 | 30.128 | [284.842, 323.127] |
| E3-Hybrid | 12 | 289.087 | 288.074 | 20.929 | [275.790, 302.385] |

### Hypothesis Testing: Pairwise Reroute Significance

| Comparison (A vs B) | Welch t-stat | t-p-value | Sig (t) | Mann-Whitney U | U-p-value | Sig (U) | Cohen's d | Effect Size |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| AStar vs Dijkstra | 0.000 | 1.000e+00 | No | 72.0 | 1.000e+00 | No | 0.000 | negligible |
| ACO vs Dijkstra | 0.725 | 4.782e-01 | No | 79.0 | 7.075e-01 | No | 0.296 | small |
| BCO vs Dijkstra | 1.786 | 9.029e-02 | No | 100.0 | 1.124e-01 | No | 0.729 | medium |
| PSO vs Dijkstra | 1.835 | 8.496e-02 | No | 93.0 | 2.366e-01 | No | 0.749 | medium |
| E3-Hybrid vs Dijkstra | 0.397 | 6.959e-01 | No | 70.0 | 9.310e-01 | No | 0.162 | negligible |

### Hypothesis Testing: E3-Hybrid Pairwise Significance

| Comparison (A vs B) | Welch t-stat | t-p-value | Sig (t) | Mann-Whitney U | U-p-value | Sig (U) | Cohen's d | Effect Size |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| E3-Hybrid vs ACO | -0.364 | 7.199e-01 | No | 70.0 | 9.310e-01 | No | -0.148 | negligible |
| E3-Hybrid vs Dijkstra | 0.397 | 6.959e-01 | No | 70.0 | 9.310e-01 | No | 0.162 | negligible |
| E3-Hybrid vs PSO | -1.407 | 1.752e-01 | No | 51.0 | 2.366e-01 | No | -0.574 | medium |

---


# Advanced Multi-Objective & Resilience Evaluation

This section presents the advanced multi-objective optimization metrics, emergency priorities, robustness diagnostics, and recovery resilience under failure models.

## Multi-Objective Optimization Indicators

The table below reports the Hypervolume (HV) Indicator (computed using a dynamic reference point set at 1.10x the worst observed objectives) and the Weighted Utility Score (using the thesis weights: Travel Time = 0.7, Energy = 0.2, Safety/Stranded = 0.1). Higher values are superior for both metrics.

| Algorithm | Hypervolume (HV) | Weighted Utility Score | Scenario Win Count | Non-Dominated Run % |
| :--- | :---: | :---: | :---: | :---: |
| AStar | 4.6584e+03 | 0.7122 | 19 | 54.2% |
| Dijkstra | 4.6584e+03 | 0.7122 | 0 | 54.2% |
| ACO | 4.1469e+03 | 0.5760 | 19 | 34.7% |
| PSO | 5.8869e+03 | 0.5595 | 10 | 100.0% |
| **E3-Hybrid** | 1.9194e+03 | 0.5555 | 12 | 18.1% |
| BCO | 3.1313e+03 | 0.4417 | 12 | 19.4% |

## Pairwise Pareto Dominance Ratios

The value at row A, column B represents the fraction of evaluation runs in which Algorithm A Pareto-dominates Algorithm B (i.e. is better or equal in all objectives, and strictly better in at least one).

| Dominates ↓ / Dominated → | ACO | AStar | BCO | Dijkstra | E3-Hybrid | PSO |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| ACO | 0.0% | 25.0% | 33.3% | 25.0% | 41.7% | 0.0% |
| AStar | 51.4% | 0.0% | 66.7% | 0.0% | 50.0% | 0.0% |
| BCO | 41.7% | 12.5% | 0.0% | 12.5% | 30.6% | 0.0% |
| Dijkstra | 51.4% | 0.0% | 66.7% | 0.0% | 50.0% | 0.0% |
| **E3-Hybrid** | 16.7% | 0.0% | 16.7% | 0.0% | 0.0% | 0.0% |
| PSO | 31.9% | 33.3% | 47.2% | 33.3% | 31.9% | 0.0% |

## Dynamic Network Resilience Analysis

For scenarios featuring physical bottlenecks and outages, we report the Performance Loss Area (cumulative speed reduction below limit over time) and Recovery Time (steps to restore average speed above 0.95 of free-flow). Lower is superior.

### Scenario: Single Road Closure Scenario

| Algorithm | Performance Loss Area | Recovery Time (steps) |
| :--- | :---: | :---: |
| Dijkstra | 0.000 | 1.0 |
| AStar | 0.000 | 1.0 |
| ACO | 0.000 | 1.0 |
| BCO | 0.000 | 1.0 |
| PSO | 0.000 | 1.0 |
| **E3-Hybrid** | 0.000 | 1.0 |

### Scenario: Progressive Closures Scenario

| Algorithm | Performance Loss Area | Recovery Time (steps) |
| :--- | :---: | :---: |
| Dijkstra | 0.000 | 1.0 |
| AStar | 0.000 | 1.0 |
| ACO | 0.000 | 1.0 |
| BCO | 0.000 | 1.0 |
| PSO | 0.000 | 1.0 |
| **E3-Hybrid** | 0.000 | 1.0 |

### Scenario: Infrastructure Failure Scenario

| Algorithm | Performance Loss Area | Recovery Time (steps) |
| :--- | :---: | :---: |
| Dijkstra | 0.000 | 1.0 |
| AStar | 0.000 | 1.0 |
| ACO | 0.000 | 1.0 |
| BCO | 0.000 | 1.0 |
| PSO | 0.000 | 1.0 |
| **E3-Hybrid** | 0.000 | 1.0 |

### Scenario: Communication Blackout Scenario

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

### Scenario: Emergency Incident Scenario

| Algorithm | Ambulance Response Time (s) | Dispatch Success Rate | Yielding Corridor Duration (s) |
| :--- | :---: | :---: | :---: |
| Dijkstra | nan | 100.0% | 0.00 |
| AStar | nan | 100.0% | 0.00 |
| ACO | nan | 100.0% | 0.00 |
| BCO | nan | 100.0% | 0.00 |
| PSO | nan | 100.0% | 0.00 |
| **E3-Hybrid** | nan | 100.0% | 0.00 |

## Robustness and Consistency Analysis

We evaluate the stability of travel times across seeds via the Coefficient of Variation (CV = standard deviation / mean). Lower CV indicates higher routing predictability and robustness.

### Scenario: Normal Traffic Scenario

| Algorithm | Mean Travel Time (s) | Std Dev (s) | Coefficient of Variation (CV) |
| :--- | :---: | :---: | :---: |
| Dijkstra | 286.13 | 14.47 | 0.0506 |
| AStar | 286.13 | 14.47 | 0.0506 |
| **E3-Hybrid** | 289.09 | 20.04 | 0.0693 |
| BCO | 300.60 | 22.64 | 0.0753 |
| ACO | 292.73 | 26.46 | 0.0904 |
| PSO | 303.98 | 28.85 | 0.0949 |

### Scenario: Single Road Closure Scenario

| Algorithm | Mean Travel Time (s) | Std Dev (s) | Coefficient of Variation (CV) |
| :--- | :---: | :---: | :---: |
| Dijkstra | 288.49 | 15.93 | 0.0552 |
| AStar | 288.49 | 15.93 | 0.0552 |
| **E3-Hybrid** | 289.09 | 20.04 | 0.0693 |
| BCO | 303.55 | 23.22 | 0.0765 |
| ACO | 296.07 | 26.17 | 0.0884 |
| PSO | 307.72 | 30.44 | 0.0989 |

### Scenario: Progressive Closures Scenario

| Algorithm | Mean Travel Time (s) | Std Dev (s) | Coefficient of Variation (CV) |
| :--- | :---: | :---: | :---: |
| Dijkstra | 287.26 | 16.15 | 0.0562 |
| AStar | 287.26 | 16.15 | 0.0562 |
| **E3-Hybrid** | 288.50 | 20.25 | 0.0702 |
| ACO | 293.43 | 23.50 | 0.0801 |
| BCO | 303.08 | 24.58 | 0.0811 |
| PSO | 307.51 | 30.83 | 0.1003 |

### Scenario: Emergency Incident Scenario

| Algorithm | Mean Travel Time (s) | Std Dev (s) | Coefficient of Variation (CV) |
| :--- | :---: | :---: | :---: |
| Dijkstra | 286.13 | 14.47 | 0.0506 |
| AStar | 286.13 | 14.47 | 0.0506 |
| **E3-Hybrid** | 289.09 | 20.04 | 0.0693 |
| BCO | 300.60 | 22.64 | 0.0753 |
| ACO | 292.73 | 26.46 | 0.0904 |
| PSO | 303.98 | 28.85 | 0.0949 |

### Scenario: Infrastructure Failure Scenario

| Algorithm | Mean Travel Time (s) | Std Dev (s) | Coefficient of Variation (CV) |
| :--- | :---: | :---: | :---: |
| Dijkstra | 286.13 | 14.47 | 0.0506 |
| AStar | 286.13 | 14.47 | 0.0506 |
| **E3-Hybrid** | 289.09 | 20.04 | 0.0693 |
| BCO | 300.60 | 22.64 | 0.0753 |
| ACO | 292.73 | 26.46 | 0.0904 |
| PSO | 303.98 | 28.85 | 0.0949 |

### Scenario: Communication Blackout Scenario

| Algorithm | Mean Travel Time (s) | Std Dev (s) | Coefficient of Variation (CV) |
| :--- | :---: | :---: | :---: |
| Dijkstra | 286.13 | 14.47 | 0.0506 |
| AStar | 286.13 | 14.47 | 0.0506 |
| **E3-Hybrid** | 289.09 | 20.04 | 0.0693 |
| BCO | 300.60 | 22.64 | 0.0753 |
| ACO | 292.73 | 26.46 | 0.0904 |
| PSO | 303.98 | 28.85 | 0.0949 |

