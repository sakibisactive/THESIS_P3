"""Plot generator for creating publication-quality charts from simulation runs."""

import os

import matplotlib

matplotlib.use("Agg")  # Headless backend to prevent display errors
import matplotlib.pyplot as plt
import numpy as np


class PlotGenerator:
    """Generates charts and saves them to a destination directory."""

    def __init__(self, output_dir: str) -> None:
        """Initializes the plot generator.

        Args:
            output_dir: Directory where plot image files will be saved.
        """
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)

        # Apply publication style defaults
        plt.rcParams.update(
            {
                "font.family": "serif",
                "font.size": 11,
                "axes.labelsize": 12,
                "axes.titlesize": 13,
                "xtick.labelsize": 10,
                "ytick.labelsize": 10,
                "figure.titlesize": 14,
                "legend.fontsize": 10,
                "grid.alpha": 0.3,
                "grid.linestyle": "--",
            }
        )

    def _save_figure(
        self, fig: plt.Figure, name: str, formats: list[str] | None = None
    ) -> list[str]:
        """Saves a figure to all specified formats (e.g. png, pdf, svg)."""
        if formats is None:
            formats = ["png", "pdf", "svg"]

        saved_paths = []
        for fmt in formats:
            path = os.path.join(self.output_dir, f"{name}.{fmt}")
            fig.savefig(path, format=fmt, bbox_inches="tight", dpi=300)
            saved_paths.append(path)
        plt.close(fig)
        return saved_paths

    def generate_convergence_plot(
        self,
        iteration_costs: list[float],
        name: str = "convergence_plot",
        formats: list[str] | None = None,
    ) -> list[str]:
        """Generates an iteration-by-iteration convergence cost plot.

        Args:
            iteration_costs: Costs indexed by search iteration.
            name: Output base name.
            formats: List of formats to export.

        Returns:
            list[str]: Saved file paths.
        """
        fig, ax = plt.subplots(figsize=(6, 4))
        ax.plot(
            range(1, len(iteration_costs) + 1),
            iteration_costs,
            marker="o",
            color="#1f77b4",
            linewidth=1.5,
            markersize=4,
        )
        ax.set_xlabel("Search Iterations")
        ax.set_ylabel("Calculated Route Cost")
        ax.set_title("Swarm Routing Algorithm Convergence")
        ax.grid(True)
        return self._save_figure(fig, name, formats)

    def generate_travel_time_comparison(
        self,
        alg_travel_times: dict[str, list[float]],
        name: str = "travel_time_comparison",
        formats: list[str] | None = None,
    ) -> list[str]:
        """Generates a boxplot comparing travel times of different algorithms.

        Args:
            alg_travel_times: Dictionary mapping algorithm name -> list of vehicle travel times.
            name: Output base name.
            formats: List of formats to export.

        Returns:
            list[str]: Saved file paths.
        """
        fig, ax = plt.subplots(figsize=(7, 5))

        labels = list(alg_travel_times.keys())
        data = [alg_travel_times[label] for label in labels]

        bp = ax.boxplot(
            data, patch_artist=True, medianprops={"color": "black", "linewidth": 1.5}
        )
        ax.set_xticklabels(labels)

        # Color coding boxes
        colors = ["#3498db", "#e74c3c", "#2ecc71", "#f1c40f", "#9b59b6"]
        for patch, color in zip(bp["boxes"], colors * 10):
            patch.set_facecolor(color)
            patch.set_alpha(0.7)

        ax.set_ylabel("Travel Time (seconds)")
        ax.set_xlabel("Routing Algorithm")
        ax.set_title("Vehicle Travel Time Distribution Comparison")
        ax.grid(True, axis="y")

        return self._save_figure(fig, name, formats)

    def generate_travel_time_cdf(
        self,
        alg_travel_times: dict[str, list[float]],
        name: str = "travel_time_cdf",
        formats: list[str] | None = None,
    ) -> list[str]:
        """Generates a Cumulative Distribution Function (CDF) plot of travel times.

        Args:
            alg_travel_times: Dictionary mapping algorithm name -> list of vehicle travel times.
            name: Output base name.
            formats: List of formats to export.

        Returns:
            list[str]: Saved file paths.
        """
        fig, ax = plt.subplots(figsize=(7, 5))

        colors = ["#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd"]
        for idx, (label, times) in enumerate(alg_travel_times.items()):
            if not times:
                continue
            sorted_times = np.sort(times)
            cdf = np.arange(1, len(sorted_times) + 1) / len(sorted_times)
            ax.plot(
                sorted_times,
                cdf,
                label=label,
                color=colors[idx % len(colors)],
                linewidth=2,
            )

        ax.set_xlabel("Travel Time (seconds)")
        ax.set_ylabel("Cumulative Probability P(T <= t)")
        ax.set_title("Travel Time Cumulative Distribution Function (CDF)")
        ax.legend(loc="lower right")
        ax.grid(True)

        return self._save_figure(fig, name, formats)

    def generate_emergency_response_plot(
        self,
        alg_response_times: dict[str, list[float]],
        name: str = "emergency_response",
        formats: list[str] | None = None,
    ) -> list[str]:
        """Generates a bar plot comparing average emergency response times.

        Args:
            alg_response_times: Dictionary mapping algorithm name -> list of response times.
            name: Output base name.
            formats: List of formats to export.

        Returns:
            list[str]: Saved file paths.
        """
        fig, ax = plt.subplots(figsize=(6, 4))

        labels: list[str] = []
        means: list[float] = []
        stds: list[float] = []

        for label, times in alg_response_times.items():
            labels.append(label)
            if times:
                means.append(float(np.mean(times)))
                stds.append(float(np.std(times)) if len(times) > 1 else 0.0)
            else:
                means.append(0.0)
                stds.append(0.0)

        x = np.arange(len(labels))
        ax.bar(
            x,
            means,
            yerr=stds,
            align="center",
            alpha=0.7,
            color="#d62728",
            edgecolor="black",
            capsize=5,
        )
        ax.set_xticks(x)
        ax.set_xticklabels(labels)
        ax.set_ylabel("Average Response Time (seconds)")
        ax.set_title("Emergency Incident Response Times")
        ax.grid(True, axis="y")

        return self._save_figure(fig, name, formats)

    def generate_congestion_level_plot(
        self,
        steps_time: list[float],
        congestion_ratios: list[float],
        name: str = "congestion_ratio",
        formats: list[str] | None = None,
    ) -> list[str]:
        """Generates a line plot tracking dynamic network congestion levels over time.

        Args:
            steps_time: Timestamps of ticks.
            congestion_ratios: Speed reduction ratio of the network (average speed / speed limit).
            name: Output base name.
            formats: List of formats to export.

        Returns:
            list[str]: Saved file paths.
        """
        fig, ax = plt.subplots(figsize=(7, 4))
        # Plot congestion as speed reduction: 1.0 is free flow, <1.0 is congested
        ax.plot(
            steps_time,
            congestion_ratios,
            color="#d62728",
            label="Network Congestion Index",
            linewidth=1.5,
        )
        ax.set_xlabel("Time (seconds)")
        ax.set_ylabel("Average Speed Ratio (Actual/Limit)")
        ax.set_title("Dynamic Network Performance Index")
        ax.set_ylim(0.0, 1.05)
        ax.grid(True)

        return self._save_figure(fig, name, formats)
