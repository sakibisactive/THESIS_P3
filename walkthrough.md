# Walkthrough: E3-Hybrid Routing Framework Complete Evaluation Suite

All evaluation simulation matrices for the E3-Hybrid framework have been successfully completed, consolidated, and analyzed.

---

## 1. Code Modifications & Consolidation Bug Fix

### A. E3-Hybrid Variant Classification Fix
* **Issue:** The `SumoScenarioExecutor` logs the router's class name (`self.router.__class__.__name__`) inside the raw metrics under `algorithm_name`. Since all ablation and sensitivity variants instantiate the base `E3HybridRouter` class (configured with different parameter overrides), every variant was serialized into checkpoints as `"E3HybridRouter"`. During results consolidation, this caused all variants to group under the base `E3-Hybrid` name, leaving the ablation and sensitivity tables and summaries blank or marked as `N/A`.
* **Solution:** Modified the checkpoint loader in [scripts/run_benchmarks.py](file:///home/shiku/THESIS/scripts/run_benchmarks.py) to explicitly override `data["algorithm_name"] = algorithm` (the task-specific configuration name) when loading each JSON file.
* **Result:** Successfully enabled correct categorization, data aggregation, and report generation for all E3-Hybrid variants (ablation and sensitivity configs).

---

## 2. Complete Evaluation Suite Execution

The complete evaluation suite comprising **918 simulation runs** has been executed successfully:
1. **Baseline Matrix (`heavy`, 432 runs):** Investigates standard routing under 6 traffic scenarios, 4 scale factors, and 3 random seeds.
2. **Stress Matrix (`stress`, 90 runs):** Subjects the routers to heavy congestion (1,000 vehicles) and random vehicle breakdowns/incidents.
3. **Ablation Study (`ablation`, 216 runs):** Systematically disables core components of the E3-Hybrid model (ACO, BCO, PSO, Elite Pheromone/Position Sharing) to isolate their individual contributions.
4. **Sensitivity Analysis (`sensitivity`, 180 runs):** Tests the framework's behavior across different objective weight combinations.

The run completed cleanly in **5 hours, 6 minutes, and 15 seconds**.

---

## 3. Generated Artifacts & Reports

All final outputs, datasets, statistical significance tables, and plots have been successfully generated and updated under their respective output directories:

* **Preset: heavy (Baseline)**:
  * Consolidated Datasets: [outputs/benchmark_results.json](file:///home/shiku/THESIS/outputs/benchmark_results.json) & [outputs/benchmark_results.csv](file:///home/shiku/THESIS/outputs/benchmark_results.csv)
  * Significance Analysis: [outputs/statistical_tables.md](file:///home/shiku/THESIS/outputs/statistical_tables.md)
  
* **Preset: stress (Stress Tests)**:
  * Consolidated Datasets: [outputs/stress_results/benchmark_results.json](file:///home/shiku/THESIS/outputs/stress_results/benchmark_results.json)
  * Significance Analysis: [outputs/stress_results/statistical_tables.md](file:///home/shiku/THESIS/outputs/stress_results/statistical_tables.md)
  * Executive Summary: [outputs/stress_results/benchmark_summary.md](file:///home/shiku/THESIS/outputs/stress_results/benchmark_summary.md)
  
* **Preset: ablation (Ablation Study)**:
  * Consolidated Datasets: [outputs/ablation_results/benchmark_results.json](file:///home/shiku/THESIS/outputs/ablation_results/benchmark_results.json)
  * Significance Analysis: [outputs/ablation_results/statistical_tables.md](file:///home/shiku/THESIS/outputs/ablation_results/statistical_tables.md)
  * Executive Summary: [outputs/ablation_results/benchmark_summary.md](file:///home/shiku/THESIS/outputs/ablation_results/benchmark_summary.md)
  
* **Preset: sensitivity (Sensitivity Analysis)**:
  * Consolidated Datasets: [outputs/sensitivity_results/benchmark_results.json](file:///home/shiku/THESIS/outputs/sensitivity_results/benchmark_results.json)
  * Significance Analysis: [outputs/sensitivity_results/statistical_tables.md](file:///home/shiku/THESIS/outputs/sensitivity_results/statistical_tables.md)
  * Executive Summary: [outputs/sensitivity_results/benchmark_summary.md](file:///home/shiku/THESIS/outputs/sensitivity_results/benchmark_summary.md)

---

## 4. Comprehensive Analysis & Findings

A detailed scientific evaluation, comparison, and analysis of all completed simulation matrices has been compiled into the following project artifact:
* [thesis_results_analysis.md](file:///home/shiku/.gemini/antigravity/brain/eb812645-a0b7-4ca2-8196-16b52593cc72/thesis_results_analysis.md)
