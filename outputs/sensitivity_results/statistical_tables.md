# Thesis Evaluation: Statistical Significance Analysis

## Scenario: Normal Traffic

### Statistical Summary: Average Travel Time (s)

| Algorithm | Sample Size (N) | Mean | Median | Std Dev | 95% Confidence Interval |
| :--- | :---: | :---: | :---: | :---: | :---: |
| E3-Hybrid-WTime | 6 | 279.564 | 276.341 | 14.541 | [264.304, 294.824] |
| E3-Hybrid-WEnergy | 6 | 279.089 | 277.879 | 11.650 | [266.863, 291.315] |
| E3-Hybrid-WSafety | 6 | 290.338 | 289.034 | 11.633 | [278.130, 302.547] |
| E3-Hybrid-Balanced | 6 | 279.389 | 275.882 | 14.452 | [264.222, 294.556] |
| E3-Hybrid-Thesis | 6 | 278.392 | 274.139 | 15.413 | [262.217, 294.567] |

## Scenario: Road Closure

### Statistical Summary: Average Travel Time (s)

| Algorithm | Sample Size (N) | Mean | Median | Std Dev | 95% Confidence Interval |
| :--- | :---: | :---: | :---: | :---: | :---: |
| E3-Hybrid-WTime | 6 | 279.564 | 276.341 | 14.541 | [264.304, 294.824] |
| E3-Hybrid-WEnergy | 6 | 280.472 | 278.284 | 12.571 | [267.279, 293.665] |
| E3-Hybrid-WSafety | 6 | 288.913 | 285.613 | 11.459 | [276.888, 300.939] |
| E3-Hybrid-Balanced | 6 | 279.389 | 275.882 | 14.452 | [264.222, 294.556] |
| E3-Hybrid-Thesis | 6 | 278.392 | 274.139 | 15.413 | [262.217, 294.567] |

## Scenario: Progressive Closures

### Statistical Summary: Average Travel Time (s)

| Algorithm | Sample Size (N) | Mean | Median | Std Dev | 95% Confidence Interval |
| :--- | :---: | :---: | :---: | :---: | :---: |
| E3-Hybrid-WTime | 6 | 277.828 | 273.734 | 14.510 | [262.601, 293.055] |
| E3-Hybrid-WEnergy | 6 | 279.047 | 278.093 | 12.997 | [265.408, 292.686] |
| E3-Hybrid-WSafety | 6 | 288.157 | 285.009 | 14.048 | [273.414, 302.900] |
| E3-Hybrid-Balanced | 6 | 277.344 | 273.700 | 14.861 | [261.748, 292.939] |
| E3-Hybrid-Thesis | 6 | 277.222 | 273.498 | 15.065 | [261.412, 293.031] |

## Scenario: Emergency Incident

### Statistical Summary: Average Travel Time (s)

| Algorithm | Sample Size (N) | Mean | Median | Std Dev | 95% Confidence Interval |
| :--- | :---: | :---: | :---: | :---: | :---: |
| E3-Hybrid-WTime | 6 | 279.564 | 276.341 | 14.541 | [264.304, 294.824] |
| E3-Hybrid-WEnergy | 6 | 279.089 | 277.879 | 11.650 | [266.863, 291.315] |
| E3-Hybrid-WSafety | 6 | 290.338 | 289.034 | 11.633 | [278.130, 302.547] |
| E3-Hybrid-Balanced | 6 | 279.389 | 275.882 | 14.452 | [264.222, 294.556] |
| E3-Hybrid-Thesis | 6 | 278.392 | 274.139 | 15.413 | [262.217, 294.567] |

## Scenario: Infrastructure Failure

### Statistical Summary: Average Travel Time (s)

| Algorithm | Sample Size (N) | Mean | Median | Std Dev | 95% Confidence Interval |
| :--- | :---: | :---: | :---: | :---: | :---: |
| E3-Hybrid-WTime | 6 | 279.564 | 276.341 | 14.541 | [264.304, 294.824] |
| E3-Hybrid-WEnergy | 6 | 279.089 | 277.879 | 11.650 | [266.863, 291.315] |
| E3-Hybrid-WSafety | 6 | 290.338 | 289.034 | 11.633 | [278.130, 302.547] |
| E3-Hybrid-Balanced | 6 | 279.389 | 275.882 | 14.452 | [264.222, 294.556] |
| E3-Hybrid-Thesis | 6 | 278.392 | 274.139 | 15.413 | [262.217, 294.567] |

## Scenario: Communication Blackout

### Statistical Summary: Average Travel Time (s)

| Algorithm | Sample Size (N) | Mean | Median | Std Dev | 95% Confidence Interval |
| :--- | :---: | :---: | :---: | :---: | :---: |
| E3-Hybrid-WTime | 6 | 279.564 | 276.341 | 14.541 | [264.304, 294.824] |
| E3-Hybrid-WEnergy | 6 | 279.089 | 277.879 | 11.650 | [266.863, 291.315] |
| E3-Hybrid-WSafety | 6 | 290.338 | 289.034 | 11.633 | [278.130, 302.547] |
| E3-Hybrid-Balanced | 6 | 279.389 | 275.882 | 14.452 | [264.222, 294.556] |
| E3-Hybrid-Thesis | 6 | 278.392 | 274.139 | 15.413 | [262.217, 294.567] |


# Advanced Multi-Objective & Resilience Evaluation

This section presents the advanced multi-objective optimization metrics, emergency priorities, robustness diagnostics, and recovery resilience under failure models.

## Multi-Objective Optimization Indicators

The table below reports the Hypervolume (HV) Indicator (computed using a dynamic reference point set at 1.10x the worst observed objectives) and the Weighted Utility Score (using the thesis weights: Travel Time = 0.7, Energy = 0.2, Safety/Stranded = 0.1). Higher values are superior for both metrics.

| Algorithm | Hypervolume (HV) | Weighted Utility Score | Scenario Win Count | Non-Dominated Run % |
| :--- | :---: | :---: | :---: | :---: |
| **E3-Hybrid-WEnergy** | 3.9015e+03 | 0.7579 | 14 | 100.0% |
| **E3-Hybrid-Thesis** | 2.2247e+03 | 0.6933 | 9 | 66.7% |
| **E3-Hybrid-Balanced** | 2.0983e+03 | 0.6453 | 13 | 38.9% |
| **E3-Hybrid-WTime** | 2.0781e+03 | 0.6333 | 0 | 36.1% |
| **E3-Hybrid-WSafety** | 3.7472e+03 | 0.3047 | 0 | 100.0% |

## Pairwise Pareto Dominance Ratios

The value at row A, column B represents the fraction of evaluation runs in which Algorithm A Pareto-dominates Algorithm B (i.e. is better or equal in all objectives, and strictly better in at least one).

| Dominates ↓ / Dominated → | E3-Hybrid-Balanced | E3-Hybrid-Thesis | E3-Hybrid-WEnergy | E3-Hybrid-WSafety | E3-Hybrid-WTime |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **E3-Hybrid-Balanced** | 0.0% | 33.3% | 0.0% | 0.0% | 36.1% |
| **E3-Hybrid-Thesis** | 44.4% | 0.0% | 0.0% | 0.0% | 47.2% |
| **E3-Hybrid-WEnergy** | 27.8% | 16.7% | 0.0% | 0.0% | 33.3% |
| **E3-Hybrid-WSafety** | 13.9% | 13.9% | 0.0% | 0.0% | 13.9% |
| **E3-Hybrid-WTime** | 27.8% | 0.0% | 0.0% | 0.0% | 0.0% |

## Dynamic Network Resilience Analysis

For scenarios featuring physical bottlenecks and outages, we report the Performance Loss Area (cumulative speed reduction below limit over time) and Recovery Time (steps to restore average speed above 0.95 of free-flow). Lower is superior.

### Scenario: Single Road Closure Scenario

| Algorithm | Performance Loss Area | Recovery Time (steps) |
| :--- | :---: | :---: |
| **E3-Hybrid-WTime** | 0.000 | 1.0 |
| **E3-Hybrid-WEnergy** | 0.000 | 1.0 |
| **E3-Hybrid-WSafety** | 0.000 | 1.0 |
| **E3-Hybrid-Balanced** | 0.000 | 1.0 |
| **E3-Hybrid-Thesis** | 0.000 | 1.0 |

### Scenario: Progressive Closures Scenario

| Algorithm | Performance Loss Area | Recovery Time (steps) |
| :--- | :---: | :---: |
| **E3-Hybrid-WTime** | 0.000 | 1.0 |
| **E3-Hybrid-WEnergy** | 0.000 | 1.0 |
| **E3-Hybrid-WSafety** | 0.000 | 1.0 |
| **E3-Hybrid-Balanced** | 0.000 | 1.0 |
| **E3-Hybrid-Thesis** | 0.000 | 1.0 |

### Scenario: Infrastructure Failure Scenario

| Algorithm | Performance Loss Area | Recovery Time (steps) |
| :--- | :---: | :---: |
| **E3-Hybrid-WTime** | 0.000 | 1.0 |
| **E3-Hybrid-WEnergy** | 0.000 | 1.0 |
| **E3-Hybrid-WSafety** | 0.000 | 1.0 |
| **E3-Hybrid-Balanced** | 0.000 | 1.0 |
| **E3-Hybrid-Thesis** | 0.000 | 1.0 |

### Scenario: Communication Blackout Scenario

| Algorithm | Performance Loss Area | Recovery Time (steps) |
| :--- | :---: | :---: |
| **E3-Hybrid-WTime** | 0.000 | 1.0 |
| **E3-Hybrid-WEnergy** | 0.000 | 1.0 |
| **E3-Hybrid-WSafety** | 0.000 | 1.0 |
| **E3-Hybrid-Balanced** | 0.000 | 1.0 |
| **E3-Hybrid-Thesis** | 0.000 | 1.0 |

## Emergency Prioritization and Corridor Response

Under scenarios with ambulance dispatches, we evaluate the average ambulance response time, dispatch success rate, and emergency corridor yielding duration.

### Scenario: Emergency Incident Scenario

| Algorithm | Ambulance Response Time (s) | Dispatch Success Rate | Yielding Corridor Duration (s) |
| :--- | :---: | :---: | :---: |
| **E3-Hybrid-WTime** | nan | 100.0% | 0.00 |
| **E3-Hybrid-WEnergy** | nan | 100.0% | 0.00 |
| **E3-Hybrid-WSafety** | nan | 100.0% | 0.00 |
| **E3-Hybrid-Balanced** | nan | 100.0% | 0.00 |
| **E3-Hybrid-Thesis** | nan | 100.0% | 0.00 |

## Robustness and Consistency Analysis

We evaluate the stability of travel times across seeds via the Coefficient of Variation (CV = standard deviation / mean). Lower CV indicates higher routing predictability and robustness.

### Scenario: Normal Traffic Scenario

| Algorithm | Mean Travel Time (s) | Std Dev (s) | Coefficient of Variation (CV) |
| :--- | :---: | :---: | :---: |
| **E3-Hybrid-WSafety** | 290.34 | 10.62 | 0.0366 |
| **E3-Hybrid-WEnergy** | 279.09 | 10.64 | 0.0381 |
| **E3-Hybrid-Balanced** | 279.39 | 13.19 | 0.0472 |
| **E3-Hybrid-WTime** | 279.56 | 13.27 | 0.0475 |
| **E3-Hybrid-Thesis** | 278.39 | 14.07 | 0.0505 |

### Scenario: Single Road Closure Scenario

| Algorithm | Mean Travel Time (s) | Std Dev (s) | Coefficient of Variation (CV) |
| :--- | :---: | :---: | :---: |
| **E3-Hybrid-WSafety** | 288.91 | 10.46 | 0.0362 |
| **E3-Hybrid-WEnergy** | 280.47 | 11.48 | 0.0409 |
| **E3-Hybrid-Balanced** | 279.39 | 13.19 | 0.0472 |
| **E3-Hybrid-WTime** | 279.56 | 13.27 | 0.0475 |
| **E3-Hybrid-Thesis** | 278.39 | 14.07 | 0.0505 |

### Scenario: Progressive Closures Scenario

| Algorithm | Mean Travel Time (s) | Std Dev (s) | Coefficient of Variation (CV) |
| :--- | :---: | :---: | :---: |
| **E3-Hybrid-WEnergy** | 279.05 | 11.86 | 0.0425 |
| **E3-Hybrid-WSafety** | 288.16 | 12.82 | 0.0445 |
| **E3-Hybrid-WTime** | 277.83 | 13.25 | 0.0477 |
| **E3-Hybrid-Balanced** | 277.34 | 13.57 | 0.0489 |
| **E3-Hybrid-Thesis** | 277.22 | 13.75 | 0.0496 |

### Scenario: Emergency Incident Scenario

| Algorithm | Mean Travel Time (s) | Std Dev (s) | Coefficient of Variation (CV) |
| :--- | :---: | :---: | :---: |
| **E3-Hybrid-WSafety** | 290.34 | 10.62 | 0.0366 |
| **E3-Hybrid-WEnergy** | 279.09 | 10.64 | 0.0381 |
| **E3-Hybrid-Balanced** | 279.39 | 13.19 | 0.0472 |
| **E3-Hybrid-WTime** | 279.56 | 13.27 | 0.0475 |
| **E3-Hybrid-Thesis** | 278.39 | 14.07 | 0.0505 |

### Scenario: Infrastructure Failure Scenario

| Algorithm | Mean Travel Time (s) | Std Dev (s) | Coefficient of Variation (CV) |
| :--- | :---: | :---: | :---: |
| **E3-Hybrid-WSafety** | 290.34 | 10.62 | 0.0366 |
| **E3-Hybrid-WEnergy** | 279.09 | 10.64 | 0.0381 |
| **E3-Hybrid-Balanced** | 279.39 | 13.19 | 0.0472 |
| **E3-Hybrid-WTime** | 279.56 | 13.27 | 0.0475 |
| **E3-Hybrid-Thesis** | 278.39 | 14.07 | 0.0505 |

### Scenario: Communication Blackout Scenario

| Algorithm | Mean Travel Time (s) | Std Dev (s) | Coefficient of Variation (CV) |
| :--- | :---: | :---: | :---: |
| **E3-Hybrid-WSafety** | 290.34 | 10.62 | 0.0366 |
| **E3-Hybrid-WEnergy** | 279.09 | 10.64 | 0.0381 |
| **E3-Hybrid-Balanced** | 279.39 | 13.19 | 0.0472 |
| **E3-Hybrid-WTime** | 279.56 | 13.27 | 0.0475 |
| **E3-Hybrid-Thesis** | 278.39 | 14.07 | 0.0505 |

