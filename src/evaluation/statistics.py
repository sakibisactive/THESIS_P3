"""Statistical analysis module for simulation run comparisons."""

import numpy as np
from pydantic import BaseModel
from scipy import stats  # type: ignore[import-untyped]


class GroupStatistics(BaseModel):
    """Statistical summaries for a specific evaluation group."""

    name: str
    sample_size: int
    mean: float
    median: float
    std_dev: float
    ci_lower: float
    ci_upper: float


class HypothesisTestResult(BaseModel):
    """Results of hypothesis testing between two evaluation groups."""

    group_a_name: str
    group_b_name: str
    t_stat: float | None = None
    t_p_value: float | None = None
    u_stat: float | None = None
    u_p_value: float | None = None
    cohens_d: float
    effect_size_interpretation: str
    is_t_significant: bool = False
    is_u_significant: bool = False


def calculate_group_statistics(
    data: list[float] | np.ndarray, name: str, confidence: float = 0.95
) -> GroupStatistics:
    """Computes summary statistics and confidence intervals for a data array.

    Args:
        data: List or array of float values.
        name: Name of the evaluation group (e.g., algorithm name).
        confidence: Confidence level (default 0.95).

    Returns:
        GroupStatistics: Statistical summary values.
    """
    arr = np.array(data, dtype=float)
    n = len(arr)
    if n == 0:
        return GroupStatistics(
            name=name,
            sample_size=0,
            mean=0.0,
            median=0.0,
            std_dev=0.0,
            ci_lower=0.0,
            ci_upper=0.0,
        )

    mean_val = float(np.mean(arr))
    med_val = float(np.median(arr))
    std_val = float(np.std(arr, ddof=1)) if n > 1 else 0.0

    # Confidence Interval calculation
    if n > 1:
        sem = stats.sem(arr)
        ci_lower, ci_upper = stats.t.interval(
            confidence, df=n - 1, loc=mean_val, scale=sem
        )
    else:
        ci_lower, ci_upper = mean_val, mean_val

    # Replace nan or infinite CIs
    if np.isnan(ci_lower) or np.isinf(ci_lower):
        ci_lower = mean_val
    if np.isnan(ci_upper) or np.isinf(ci_upper):
        ci_upper = mean_val

    return GroupStatistics(
        name=name,
        sample_size=n,
        mean=mean_val,
        median=med_val,
        std_dev=std_val,
        ci_lower=float(ci_lower),
        ci_upper=float(ci_upper),
    )


def perform_hypothesis_tests(
    group_a: list[float], group_b: list[float], name_a: str, name_b: str
) -> HypothesisTestResult:
    """Performs Welch's t-test, Mann-Whitney U, and Cohen's d effect size between two groups.

    Args:
        group_a: Data points for group A.
        group_b: Data points for group B.
        name_a: Name of group A.
        name_b: Name of group B.

    Returns:
        HypothesisTestResult: Test statistics and interpretations.
    """
    arr_a = np.array(group_a, dtype=float)
    arr_b = np.array(group_b, dtype=float)

    n_a = len(arr_a)
    n_b = len(arr_b)

    # Welch's t-test (independent t-test with unequal variances)
    if n_a > 1 and n_b > 1:
        t_res = stats.ttest_ind(arr_a, arr_b, equal_var=False)
        t_stat = float(t_res.statistic)
        t_p = float(t_res.pvalue)
    else:
        t_stat, t_p = None, None

    # Mann-Whitney U test
    if n_a > 0 and n_b > 0:
        try:
            u_res = stats.mannwhitneyu(arr_a, arr_b, alternative="two-sided")
            u_stat = float(u_res.statistic)
            u_p = float(u_res.pvalue)
        except Exception:
            u_stat, u_p = None, None
    else:
        u_stat, u_p = None, None

    # Cohen's d calculation
    mean_a, mean_b = (
        np.mean(arr_a) if n_a > 0 else 0.0,
        np.mean(arr_b) if n_b > 0 else 0.0,
    )
    var_a = np.var(arr_a, ddof=1) if n_a > 1 else 0.0
    var_b = np.var(arr_b, ddof=1) if n_b > 1 else 0.0

    pooled_sd = 1.0
    if n_a > 1 or n_b > 1:
        denom = (n_a - 1) * var_a + (n_b - 1) * var_b
        degrees_of_freedom = n_a + n_b - 2
        if degrees_of_freedom > 0:
            pooled_sd = np.sqrt(denom / degrees_of_freedom)

    if pooled_sd == 0.0:
        pooled_sd = 1.0

    d = (mean_a - mean_b) / pooled_sd
    abs_d = abs(d)

    # Effect size interpretation
    if abs_d < 0.2:
        effect_size = "negligible"
    elif abs_d < 0.5:
        effect_size = "small"
    elif abs_d < 0.8:
        effect_size = "medium"
    else:
        effect_size = "large"

    is_t_sig = (t_p is not None) and (t_p < 0.05)
    is_u_sig = (u_p is not None) and (u_p < 0.05)

    return HypothesisTestResult(
        group_a_name=name_a,
        group_b_name=name_b,
        t_stat=t_stat,
        t_p_value=t_p,
        u_stat=u_stat,
        u_p_value=u_p,
        cohens_d=float(d),
        effect_size_interpretation=effect_size,
        is_t_significant=is_t_sig,
        is_u_significant=is_u_sig,
    )


def format_statistics_markdown_table(
    stats_list: list[GroupStatistics], metric_name: str
) -> str:
    """Generates a publication-quality markdown table for Group Statistics.

    Args:
        stats_list: List of calculated GroupStatistics.
        metric_name: Name of the evaluated metric (e.g. Travel Time).

    Returns:
        str: Markdown table string.
    """
    lines = [
        f"### Statistical Summary: {metric_name}",
        "",
        "| Algorithm | Sample Size (N) | Mean | Median | Std Dev | 95% Confidence Interval |",
        "| :--- | :---: | :---: | :---: | :---: | :---: |",
    ]
    for s in stats_list:
        lines.append(
            f"| {s.name} | {s.sample_size} | {s.mean:.3f} | {s.median:.3f} | "
            f"{s.std_dev:.3f} | [{s.ci_lower:.3f}, {s.ci_upper:.3f}] |"
        )
    return "\n".join(lines)


def format_hypothesis_markdown_table(
    test_results: list[HypothesisTestResult], metric_name: str
) -> str:
    """Generates a publication-quality markdown table for Hypothesis Test Results.

    Args:
        test_results: List of HypothesisTestResult objects.
        metric_name: Name of the evaluated metric.

    Returns:
        str: Markdown table string.
    """
    lines = [
        f"### Hypothesis Testing: {metric_name}",
        "",
        "| Comparison (A vs B) | Welch t-stat | t-p-value | Sig (t) | Mann-Whitney U | U-p-value | Sig (U) | Cohen's d | Effect Size |",
        "| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |",
    ]
    for r in test_results:
        t_s = f"{r.t_stat:.3f}" if r.t_stat is not None else "N/A"
        t_p = f"{r.t_p_value:.3e}" if r.t_p_value is not None else "N/A"
        u_s = f"{r.u_stat:.1f}" if r.u_stat is not None else "N/A"
        u_p = f"{r.u_p_value:.3e}" if r.u_p_value is not None else "N/A"
        sig_t = "Yes*" if r.is_t_significant else "No"
        sig_u = "Yes*" if r.is_u_significant else "No"

        lines.append(
            f"| {r.group_a_name} vs {r.group_b_name} | {t_s} | {t_p} | {sig_t} | "
            f"{u_s} | {u_p} | {sig_u} | {r.cohens_d:.3f} | {r.effect_size_interpretation} |"
        )
    return "\n".join(lines)
