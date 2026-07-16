# Thesis Evaluation: Statistical Significance Analysis

## Scenario: Normal Traffic

### Statistical Summary: Average Travel Time (s)

| Algorithm | Sample Size (N) | Mean | Median | Std Dev | 95% Confidence Interval |
| :--- | :---: | :---: | :---: | :---: | :---: |
| Dijkstra | 40 | 294.827 | 289.298 | 28.034 | [285.861, 303.792] |
| AStar | 40 | 294.827 | 289.298 | 28.034 | [285.861, 303.792] |
| ACO | 40 | 289.103 | 282.061 | 27.461 | [280.320, 297.885] |
| BCO | 40 | 293.579 | 291.287 | 24.814 | [285.643, 301.515] |
| PSO | 40 | 303.726 | 303.465 | 33.820 | [292.910, 314.542] |
| E3-Hybrid | 40 | 292.226 | 286.405 | 30.582 | [282.445, 302.007] |

### Hypothesis Testing: Pairwise Reroute Significance

| Comparison (A vs B) | Welch t-stat | t-p-value | Sig (t) | Mann-Whitney U | U-p-value | Sig (U) | Cohen's d | Effect Size |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| AStar vs Dijkstra | 0.000 | 1.000e+00 | No | 800.0 | 1.000e+00 | No | 0.000 | negligible |
| ACO vs Dijkstra | -0.922 | 3.591e-01 | No | 680.0 | 2.502e-01 | No | -0.206 | small |
| BCO vs Dijkstra | -0.211 | 8.336e-01 | No | 810.0 | 9.272e-01 | No | -0.047 | negligible |
| PSO vs Dijkstra | 1.281 | 2.040e-01 | No | 932.0 | 2.057e-01 | No | 0.287 | small |
| E3-Hybrid vs Dijkstra | -0.396 | 6.929e-01 | No | 712.0 | 3.998e-01 | No | -0.089 | negligible |

### Hypothesis Testing: E3-Hybrid Pairwise Significance

| Comparison (A vs B) | Welch t-stat | t-p-value | Sig (t) | Mann-Whitney U | U-p-value | Sig (U) | Cohen's d | Effect Size |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| E3-Hybrid vs ACO | 0.481 | 6.322e-01 | No | 841.0 | 6.967e-01 | No | 0.107 | negligible |
| E3-Hybrid vs Dijkstra | -0.396 | 6.929e-01 | No | 712.0 | 3.998e-01 | No | -0.089 | negligible |
| E3-Hybrid vs PSO | -1.595 | 1.148e-01 | No | 621.0 | 8.587e-02 | No | -0.357 | small |

---

## Scenario: Road Closure

### Statistical Summary: Average Travel Time (s)

| Algorithm | Sample Size (N) | Mean | Median | Std Dev | 95% Confidence Interval |
| :--- | :---: | :---: | :---: | :---: | :---: |
| Dijkstra | 40 | 296.914 | 292.077 | 28.492 | [287.802, 306.026] |
| AStar | 40 | 296.914 | 292.077 | 28.492 | [287.802, 306.026] |
| ACO | 40 | 291.554 | 284.300 | 27.066 | [282.898, 300.210] |
| BCO | 40 | 294.740 | 292.648 | 25.397 | [286.618, 302.863] |
| PSO | 40 | 305.412 | 304.504 | 34.038 | [294.526, 316.298] |
| E3-Hybrid | 40 | 293.465 | 289.476 | 30.845 | [283.600, 303.329] |

### Hypothesis Testing: Pairwise Reroute Significance

| Comparison (A vs B) | Welch t-stat | t-p-value | Sig (t) | Mann-Whitney U | U-p-value | Sig (U) | Cohen's d | Effect Size |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| AStar vs Dijkstra | 0.000 | 1.000e+00 | No | 800.0 | 1.000e+00 | No | 0.000 | negligible |
| ACO vs Dijkstra | -0.863 | 3.910e-01 | No | 699.0 | 3.335e-01 | No | -0.193 | negligible |
| BCO vs Dijkstra | -0.360 | 7.197e-01 | No | 791.0 | 9.348e-01 | No | -0.081 | negligible |
| PSO vs Dijkstra | 1.211 | 2.297e-01 | No | 921.0 | 2.462e-01 | No | 0.271 | small |
| E3-Hybrid vs Dijkstra | -0.520 | 6.049e-01 | No | 719.0 | 4.386e-01 | No | -0.116 | negligible |

### Hypothesis Testing: E3-Hybrid Pairwise Significance

| Comparison (A vs B) | Welch t-stat | t-p-value | Sig (t) | Mann-Whitney U | U-p-value | Sig (U) | Cohen's d | Effect Size |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| E3-Hybrid vs ACO | 0.295 | 7.692e-01 | No | 816.0 | 8.814e-01 | No | 0.066 | negligible |
| E3-Hybrid vs Dijkstra | -0.520 | 6.049e-01 | No | 719.0 | 4.386e-01 | No | -0.116 | negligible |
| E3-Hybrid vs PSO | -1.645 | 1.040e-01 | No | 617.0 | 7.907e-02 | No | -0.368 | small |

---

## Scenario: Progressive Closures

### Statistical Summary: Average Travel Time (s)

| Algorithm | Sample Size (N) | Mean | Median | Std Dev | 95% Confidence Interval |
| :--- | :---: | :---: | :---: | :---: | :---: |
| Dijkstra | 40 | 296.046 | 290.221 | 28.850 | [286.819, 305.273] |
| AStar | 40 | 296.046 | 290.221 | 28.850 | [286.819, 305.273] |
| ACO | 40 | 290.513 | 284.300 | 27.115 | [281.841, 299.185] |
| BCO | 40 | 293.422 | 291.216 | 25.749 | [285.187, 301.657] |
| PSO | 40 | 304.680 | 303.264 | 34.305 | [293.709, 315.651] |
| E3-Hybrid | 40 | 292.781 | 287.621 | 30.637 | [282.982, 302.579] |

### Hypothesis Testing: Pairwise Reroute Significance

| Comparison (A vs B) | Welch t-stat | t-p-value | Sig (t) | Mann-Whitney U | U-p-value | Sig (U) | Cohen's d | Effect Size |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| AStar vs Dijkstra | 0.000 | 1.000e+00 | No | 800.0 | 1.000e+00 | No | 0.000 | negligible |
| ACO vs Dijkstra | -0.884 | 3.795e-01 | No | 702.0 | 3.481e-01 | No | -0.198 | negligible |
| BCO vs Dijkstra | -0.429 | 6.690e-01 | No | 791.0 | 9.348e-01 | No | -0.096 | negligible |
| PSO vs Dijkstra | 1.218 | 2.269e-01 | No | 932.0 | 2.057e-01 | No | 0.272 | small |
| E3-Hybrid vs Dijkstra | -0.491 | 6.250e-01 | No | 723.0 | 4.617e-01 | No | -0.110 | negligible |

### Hypothesis Testing: E3-Hybrid Pairwise Significance

| Comparison (A vs B) | Welch t-stat | t-p-value | Sig (t) | Mann-Whitney U | U-p-value | Sig (U) | Cohen's d | Effect Size |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| E3-Hybrid vs ACO | 0.351 | 7.269e-01 | No | 818.0 | 8.663e-01 | No | 0.078 | negligible |
| E3-Hybrid vs Dijkstra | -0.491 | 6.250e-01 | No | 723.0 | 4.617e-01 | No | -0.110 | negligible |
| E3-Hybrid vs PSO | -1.636 | 1.059e-01 | No | 619.0 | 8.241e-02 | No | -0.366 | small |

---

## Scenario: Emergency Incident

### Statistical Summary: Average Travel Time (s)

| Algorithm | Sample Size (N) | Mean | Median | Std Dev | 95% Confidence Interval |
| :--- | :---: | :---: | :---: | :---: | :---: |
| Dijkstra | 40 | 294.827 | 289.298 | 28.034 | [285.861, 303.792] |
| AStar | 40 | 294.827 | 289.298 | 28.034 | [285.861, 303.792] |
| ACO | 40 | 289.103 | 282.061 | 27.461 | [280.320, 297.885] |
| BCO | 40 | 293.579 | 291.287 | 24.814 | [285.643, 301.515] |
| PSO | 40 | 303.726 | 303.465 | 33.820 | [292.910, 314.542] |
| E3-Hybrid | 40 | 292.226 | 286.405 | 30.582 | [282.445, 302.007] |

### Hypothesis Testing: Pairwise Reroute Significance

| Comparison (A vs B) | Welch t-stat | t-p-value | Sig (t) | Mann-Whitney U | U-p-value | Sig (U) | Cohen's d | Effect Size |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| AStar vs Dijkstra | 0.000 | 1.000e+00 | No | 800.0 | 1.000e+00 | No | 0.000 | negligible |
| ACO vs Dijkstra | -0.922 | 3.591e-01 | No | 680.0 | 2.502e-01 | No | -0.206 | small |
| BCO vs Dijkstra | -0.211 | 8.336e-01 | No | 810.0 | 9.272e-01 | No | -0.047 | negligible |
| PSO vs Dijkstra | 1.281 | 2.040e-01 | No | 932.0 | 2.057e-01 | No | 0.287 | small |
| E3-Hybrid vs Dijkstra | -0.396 | 6.929e-01 | No | 712.0 | 3.998e-01 | No | -0.089 | negligible |

### Hypothesis Testing: E3-Hybrid Pairwise Significance

| Comparison (A vs B) | Welch t-stat | t-p-value | Sig (t) | Mann-Whitney U | U-p-value | Sig (U) | Cohen's d | Effect Size |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| E3-Hybrid vs ACO | 0.481 | 6.322e-01 | No | 841.0 | 6.967e-01 | No | 0.107 | negligible |
| E3-Hybrid vs Dijkstra | -0.396 | 6.929e-01 | No | 712.0 | 3.998e-01 | No | -0.089 | negligible |
| E3-Hybrid vs PSO | -1.595 | 1.148e-01 | No | 621.0 | 8.587e-02 | No | -0.357 | small |

---

## Scenario: Infrastructure Failure

### Statistical Summary: Average Travel Time (s)

| Algorithm | Sample Size (N) | Mean | Median | Std Dev | 95% Confidence Interval |
| :--- | :---: | :---: | :---: | :---: | :---: |
| Dijkstra | 40 | 294.827 | 289.298 | 28.034 | [285.861, 303.792] |
| AStar | 40 | 294.827 | 289.298 | 28.034 | [285.861, 303.792] |
| ACO | 40 | 289.103 | 282.061 | 27.461 | [280.320, 297.885] |
| BCO | 40 | 293.579 | 291.287 | 24.814 | [285.643, 301.515] |
| PSO | 40 | 303.726 | 303.465 | 33.820 | [292.910, 314.542] |
| E3-Hybrid | 40 | 292.226 | 286.405 | 30.582 | [282.445, 302.007] |

### Hypothesis Testing: Pairwise Reroute Significance

| Comparison (A vs B) | Welch t-stat | t-p-value | Sig (t) | Mann-Whitney U | U-p-value | Sig (U) | Cohen's d | Effect Size |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| AStar vs Dijkstra | 0.000 | 1.000e+00 | No | 800.0 | 1.000e+00 | No | 0.000 | negligible |
| ACO vs Dijkstra | -0.922 | 3.591e-01 | No | 680.0 | 2.502e-01 | No | -0.206 | small |
| BCO vs Dijkstra | -0.211 | 8.336e-01 | No | 810.0 | 9.272e-01 | No | -0.047 | negligible |
| PSO vs Dijkstra | 1.281 | 2.040e-01 | No | 932.0 | 2.057e-01 | No | 0.287 | small |
| E3-Hybrid vs Dijkstra | -0.396 | 6.929e-01 | No | 712.0 | 3.998e-01 | No | -0.089 | negligible |

### Hypothesis Testing: E3-Hybrid Pairwise Significance

| Comparison (A vs B) | Welch t-stat | t-p-value | Sig (t) | Mann-Whitney U | U-p-value | Sig (U) | Cohen's d | Effect Size |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| E3-Hybrid vs ACO | 0.481 | 6.322e-01 | No | 841.0 | 6.967e-01 | No | 0.107 | negligible |
| E3-Hybrid vs Dijkstra | -0.396 | 6.929e-01 | No | 712.0 | 3.998e-01 | No | -0.089 | negligible |
| E3-Hybrid vs PSO | -1.595 | 1.148e-01 | No | 621.0 | 8.587e-02 | No | -0.357 | small |

---

## Scenario: Communication Blackout

### Statistical Summary: Average Travel Time (s)

| Algorithm | Sample Size (N) | Mean | Median | Std Dev | 95% Confidence Interval |
| :--- | :---: | :---: | :---: | :---: | :---: |
| Dijkstra | 40 | 294.827 | 289.298 | 28.034 | [285.861, 303.792] |
| AStar | 40 | 294.827 | 289.298 | 28.034 | [285.861, 303.792] |
| ACO | 40 | 289.103 | 282.061 | 27.461 | [280.320, 297.885] |
| BCO | 40 | 293.579 | 291.287 | 24.814 | [285.643, 301.515] |
| PSO | 40 | 303.726 | 303.465 | 33.820 | [292.910, 314.542] |
| E3-Hybrid | 40 | 292.226 | 286.405 | 30.582 | [282.445, 302.007] |

### Hypothesis Testing: Pairwise Reroute Significance

| Comparison (A vs B) | Welch t-stat | t-p-value | Sig (t) | Mann-Whitney U | U-p-value | Sig (U) | Cohen's d | Effect Size |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| AStar vs Dijkstra | 0.000 | 1.000e+00 | No | 800.0 | 1.000e+00 | No | 0.000 | negligible |
| ACO vs Dijkstra | -0.922 | 3.591e-01 | No | 680.0 | 2.502e-01 | No | -0.206 | small |
| BCO vs Dijkstra | -0.211 | 8.336e-01 | No | 810.0 | 9.272e-01 | No | -0.047 | negligible |
| PSO vs Dijkstra | 1.281 | 2.040e-01 | No | 932.0 | 2.057e-01 | No | 0.287 | small |
| E3-Hybrid vs Dijkstra | -0.396 | 6.929e-01 | No | 712.0 | 3.998e-01 | No | -0.089 | negligible |

### Hypothesis Testing: E3-Hybrid Pairwise Significance

| Comparison (A vs B) | Welch t-stat | t-p-value | Sig (t) | Mann-Whitney U | U-p-value | Sig (U) | Cohen's d | Effect Size |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| E3-Hybrid vs ACO | 0.481 | 6.322e-01 | No | 841.0 | 6.967e-01 | No | 0.107 | negligible |
| E3-Hybrid vs Dijkstra | -0.396 | 6.929e-01 | No | 712.0 | 3.998e-01 | No | -0.089 | negligible |
| E3-Hybrid vs PSO | -1.595 | 1.148e-01 | No | 621.0 | 8.587e-02 | No | -0.357 | small |

---

