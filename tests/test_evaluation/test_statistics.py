"""Unit tests for the statistics evaluation module."""

import numpy as np
import pytest

from src.evaluation.statistics import (
    calculate_group_statistics,
    perform_hypothesis_tests,
    format_statistics_markdown_table,
    format_hypothesis_markdown_table,
)


def test_calculate_group_statistics() -> None:
    """Verifies correct calculation of statistical properties (mean, std dev, CI)."""
    # Sample data
    data = [10.0, 12.0, 11.0, 9.0, 13.0]
    stats = calculate_group_statistics(data, "GroupA")

    assert stats.name == "GroupA"
    assert stats.sample_size == 5
    assert stats.mean == 11.0
    assert stats.median == 11.0
    # Expected sample std dev: sqrt(((10-11)^2 + (12-11)^2 + (11-11)^2 + (9-11)^2 + (13-11)^2)/(5-1)) = sqrt((1 + 1 + 0 + 4 + 4)/4) = sqrt(2.5) ≈ 1.581
    assert pytest.approx(stats.std_dev, 0.01) == 1.5811
    # 95% Confidence Interval for df=4 t-distribution: t_crit ≈ 2.776
    # sem = 1.5811 / sqrt(5) ≈ 0.7071
    # CI margin = 2.776 * 0.7071 ≈ 1.963
    # CI = [11.0 - 1.963, 11.0 + 1.963] = [9.037, 12.963]
    assert pytest.approx(stats.ci_lower, 0.01) == 9.037
    assert pytest.approx(stats.ci_upper, 0.01) == 12.963


def test_hypothesis_tests() -> None:
    """Verifies Welch t-test, Mann-Whitney U, and Cohen's d effect size."""
    # Clearly distinct groups
    group_a = [10.0, 11.0, 12.0, 10.0, 11.0]
    group_b = [20.0, 21.0, 22.0, 20.0, 21.0]

    res = perform_hypothesis_tests(group_a, group_b, "GroupA", "GroupB")

    assert res.group_a_name == "GroupA"
    assert res.group_b_name == "GroupB"
    assert res.t_stat is not None
    assert res.t_stat < 0  # Group A mean is smaller
    assert res.t_p_value is not None
    assert res.t_p_value < 0.05  # Highly significant
    assert res.is_t_significant is True
    
    assert res.u_stat is not None
    assert res.u_p_value is not None
    assert res.u_p_value < 0.05
    assert res.is_u_significant is True

    # Cohen's d: (10.8 - 20.8) / Pooled SD. Since var A = 0.7, var B = 0.7, pooled SD = sqrt(0.7) ≈ 0.8366
    # Cohen's d = -10.0 / 0.8366 ≈ -11.95
    assert pytest.approx(res.cohens_d, 0.1) == -11.95
    assert res.effect_size_interpretation == "large"


def test_format_markdown_tables() -> None:
    """Verifies formatting of stats tables into markdown syntax."""
    # Mock data
    stats_a = calculate_group_statistics([1.0, 2.0, 3.0], "AlgA")
    stats_b = calculate_group_statistics([4.0, 5.0, 6.0], "AlgB")
    
    tbl_stats = format_statistics_markdown_table([stats_a, stats_b], "Travel Time")
    assert "| AlgA | 3 | 2.000 | 2.000 | 1.000 |" in tbl_stats
    assert "| AlgB | 3 | 5.000 | 5.000 | 1.000 |" in tbl_stats

    test_res = perform_hypothesis_tests([1.0, 2.0, 3.0], [4.0, 5.0, 6.0], "AlgA", "AlgB")
    tbl_hyp = format_hypothesis_markdown_table([test_res], "Travel Time")
    assert "AlgA vs AlgB" in tbl_hyp
    assert "large" in tbl_hyp
