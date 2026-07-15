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
        self.colors = {
            "E3-Hybrid": "#2ecc71",     # Vibrant Green
            "Dijkstra": "#7f8c8d",      # Gray
            "AStar": "#95a5a6",         # Light Gray
            "ACO": "#3498db",           # Blue
            "PSO": "#e74c3c",           # Red
            "BCO": "#f1c40f",           # Yellow
            "E3Hybrid": "#2ecc71",
            "A*": "#95a5a6",
        }
        self.fallback_colors = ["#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd", "#8c564b"]

    def _get_color(self, label: str, idx: int = 0) -> str:
        """Returns standard color for known algorithms, otherwise a fallback color."""
        clean_label = label.replace("Router", "").strip()
        if clean_label in self.colors:
            return self.colors[clean_label]
        return self.fallback_colors[idx % len(self.fallback_colors)]

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
        """Generates an iteration-by-iteration convergence cost plot."""
        fig, ax = plt.subplots(figsize=(6, 4))
        ax.plot(
            range(1, len(iteration_costs) + 1),
            iteration_costs,
            marker="o",
            color="#2ea02c",
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
        """Generates a boxplot comparing travel times of different algorithms."""
        fig, ax = plt.subplots(figsize=(7, 5))

        labels = list(alg_travel_times.keys())
        data = [alg_travel_times[label] for label in labels]

        bp = ax.boxplot(
            data, patch_artist=True, medianprops={"color": "black", "linewidth": 1.5}
        )
        clean_labels = [l.replace("Router", "").replace("E3Hybrid", "E3-Hybrid") for l in labels]
        ax.set_xticklabels(clean_labels)

        # Color coding boxes
        for idx, (patch, label) in enumerate(zip(bp["boxes"], labels)):
            color = self._get_color(label, idx)
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
        """Generates a Cumulative Distribution Function (CDF) plot of travel times."""
        fig, ax = plt.subplots(figsize=(7, 5))

        for idx, (label, times) in enumerate(alg_travel_times.items()):
            if not times:
                continue
            sorted_times = np.sort(times)
            cdf = np.arange(1, len(sorted_times) + 1) / len(sorted_times)
            color = self._get_color(label, idx)
            clean_label = label.replace("Router", "").replace("E3Hybrid", "E3-Hybrid")
            ax.plot(
                sorted_times,
                cdf,
                label=clean_label,
                color=color,
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
        """Generates a bar plot comparing average emergency response times."""
        fig, ax = plt.subplots(figsize=(6, 4))

        labels: list[str] = []
        means: list[float] = []
        stds: list[float] = []
        colors_list: list[str] = []

        for idx, (label, times) in enumerate(alg_response_times.items()):
            clean_label = label.replace("Router", "").replace("E3Hybrid", "E3-Hybrid")
            labels.append(clean_label)
            colors_list.append(self._get_color(label, idx))
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
            alpha=0.8,
            color=colors_list,
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
        """Generates a line plot tracking dynamic network congestion levels over time."""
        fig, ax = plt.subplots(figsize=(7, 4))
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

    def generate_pareto_fronts(
        self,
        alg_means: dict[str, tuple[float, float, float, float]],  # alg -> (mean_t, std_t, mean_e, std_e)
        name: str = "pareto_front",
        formats: list[str] | None = None
    ) -> list[str]:
        """Generates a Pareto front scatter plot comparing Travel Time and Energy Consumption."""
        fig, ax = plt.subplots(figsize=(7, 5))

        for idx, (label, (mean_t, std_t, mean_e, std_e)) in enumerate(alg_means.items()):
            color = self._get_color(label, idx)
            clean_label = label.replace("Router", "").replace("E3Hybrid", "E3-Hybrid")
            ax.errorbar(
                mean_t,
                mean_e,
                xerr=std_t,
                yerr=std_e,
                fmt="o",
                color=color,
                ecolor=color,
                capsize=5,
                markersize=8,
                label=clean_label,
                alpha=0.8,
                markeredgecolor="black"
            )

        ax.set_xlabel("Average Travel Time (seconds)")
        ax.set_ylabel("Average Energy Consumption (kWh)")
        ax.set_title("Multi-Objective Pareto Trade-Off Space")
        ax.legend(loc="upper right")
        ax.grid(True)

        return self._save_figure(fig, name, formats)

    def generate_scalability_curves(
        self,
        scalability_data: dict[str, dict[int, float]],  # alg -> {vehicles: mean_time}
        name: str = "scalability_curves",
        formats: list[str] | None = None
    ) -> list[str]:
        """Generates travel time scalability curves as vehicle density scales up."""
        fig, ax = plt.subplots(figsize=(7, 5))

        for idx, (label, points) in enumerate(scalability_data.items()):
            vehs = sorted(list(points.keys()))
            times = [points[v] for v in vehs]
            color = self._get_color(label, idx)
            clean_label = label.replace("Router", "").replace("E3Hybrid", "E3-Hybrid")
            ax.plot(
                vehs,
                times,
                marker="s",
                color=color,
                linewidth=2,
                label=clean_label
            )

        ax.set_xlabel("Vehicle Fleet Scale")
        ax.set_ylabel("Average Travel Time (seconds)")
        ax.set_title("Scalability Profile under Heavy Congestion")
        ax.set_xticks(sorted(list(next(iter(scalability_data.values())).keys())) if scalability_data else [25, 50, 100, 200])
        ax.legend(loc="upper left")
        ax.grid(True)

        return self._save_figure(fig, name, formats)

    def generate_resilience_profiles(
        self,
        steps: list[float],
        alg_congestion_profiles: dict[str, list[float]],  # alg -> list of speed ratios
        name: str = "resilience_profiles",
        formats: list[str] | None = None
    ) -> list[str]:
        """Generates dynamic performance resilience recovery profiles."""
        fig, ax = plt.subplots(figsize=(8, 4.5))

        for idx, (label, profile) in enumerate(alg_congestion_profiles.items()):
            color = self._get_color(label, idx)
            clean_label = label.replace("Router", "").replace("E3Hybrid", "E3-Hybrid")
            # If profile is longer than steps, truncate
            profile_len = min(len(steps), len(profile))
            ax.plot(
                steps[:profile_len],
                profile[:profile_len],
                color=color,
                linewidth=1.8,
                label=clean_label
            )

        ax.set_xlabel("Simulation Steps (seconds)")
        ax.set_ylabel("Average Speed Ratio (Actual / Limit)")
        ax.set_title("Network Resilience Profile under Disruption")
        ax.set_ylim(0.0, 1.05)
        ax.axvline(x=100.0, color="gray", linestyle=":", label="Disruption Inception")
        ax.legend(loc="lower left")
        ax.grid(True)

        return self._save_figure(fig, name, formats)

    def generate_rank_heatmap(
        self,
        heatmap_data: np.ndarray,
        row_labels: list[str],
        col_labels: list[str],
        name: str = "rank_heatmap",
        formats: list[str] | None = None
    ) -> list[str]:
        """Generates a rank heatmap showing relative algorithm performance (ranks)."""
        fig, ax = plt.subplots(figsize=(8, 5))
        
        # Lower ranks (closer to 1) are better, use a sequential color map
        im = ax.imshow(heatmap_data, cmap="YlGn_r", aspect="auto")
        
        # Show all ticks and label them
        ax.set_xticks(np.arange(len(col_labels)))
        ax.set_yticks(np.arange(len(row_labels)))
        
        clean_cols = [c.replace("Router", "").replace("E3Hybrid", "E3-Hybrid") for c in col_labels]
        ax.set_xticklabels(clean_cols)
        ax.set_yticklabels(row_labels)
        
        # Rotate the tick labels and set their alignment
        plt.setp(ax.get_xticklabels(), rotation=45, ha="right", rotation_mode="anchor")
        
        # Loop over data dimensions and create text annotations
        for i in range(len(row_labels)):
            for j in range(len(col_labels)):
                ax.text(j, i, f"{heatmap_data[i, j]:.1f}",
                        ha="center", va="center", color="black", weight="bold")
                        
        ax.set_title("Routing Policy Rank Heatmap (Lower is Better)")
        fig.tight_layout()
        plt.colorbar(im, label="Average Policy Rank")
        
        return self._save_figure(fig, name, formats)

    def generate_rank_comparison(
        self,
        alg_ranks: dict[str, float],
        name: str = "rank_comparison",
        formats: list[str] | None = None
    ) -> list[str]:
        """Generates a bar chart comparing the overall average rank of algorithms."""
        fig, ax = plt.subplots(figsize=(6, 4))
        
        sorted_algs = sorted(alg_ranks.keys(), key=lambda x: alg_ranks[x])
        ranks = [alg_ranks[a] for a in sorted_algs]
        colors_list = [self._get_color(a) for a in sorted_algs]
        
        x = np.arange(len(sorted_algs))
        bars = ax.bar(x, ranks, color=colors_list, edgecolor="black", alpha=0.8)
        
        ax.set_xticks(x)
        clean_labels = [a.replace("Router", "").replace("E3Hybrid", "E3-Hybrid") for a in sorted_algs]
        ax.set_xticklabels(clean_labels)
        ax.set_ylabel("Overall Average Rank")
        ax.set_title("Critical Performance Rank Summary")
        ax.grid(True, axis="y")
        
        # Add labels on top of the bars
        for bar in bars:
            height = bar.get_height()
            ax.annotate(f"{height:.2f}",
                        xy=(bar.get_x() + bar.get_width() / 2, height),
                        xytext=(0, 3),  # 3 points vertical offset
                        textcoords="offset points",
                        ha='center', va='bottom', fontweight='bold')
                        
        return self._save_figure(fig, name, formats)

    def generate_radar_chart(
        self,
        categories: list[str],
        alg_metrics: dict[str, list[float]],  # alg -> list of normalized values [0, 1]
        name: str = "radar_chart",
        formats: list[str] | None = None
    ) -> list[str]:
        """Generates a spider (radar) chart comparing multi-dimensional attributes."""
        # Number of variables
        N = len(categories)
        
        # What will be the angle of each axis in the plot? (we do divide by N)
        angles = [n / float(N) * 2 * np.pi for n in range(N)]
        angles += angles[:1]
        
        fig, ax = plt.subplots(figsize=(7, 7), subplot_kw=dict(polar=True))
        
        # Draw one axe per variable + add labels
        plt.xticks(angles[:-1], categories, size=10)
        
        # Draw ylabels
        ax.set_rlabel_position(0)
        plt.yticks([0.2, 0.4, 0.6, 0.8, 1.0], ["0.2", "0.4", "0.6", "0.8", "1.0"], color="grey", size=8)
        plt.ylim(0, 1.1)
        
        # Plot each algorithm
        for idx, (label, values) in enumerate(alg_metrics.items()):
            # repeat the first value to close the circular graph
            val_closed = list(values)
            val_closed += val_closed[:1]
            
            color = self._get_color(label, idx)
            clean_label = label.replace("Router", "").replace("E3Hybrid", "E3-Hybrid")
            
            ax.plot(angles, val_closed, linewidth=2, linestyle='solid', label=clean_label, color=color)
            ax.fill(angles, val_closed, color=color, alpha=0.1)
            
        plt.legend(loc='upper right', bbox_to_anchor=(0.1, 0.1))
        ax.set_title("Multi-Objective Performance Envelope (Normalized)")
        
        return self._save_figure(fig, name, formats)
