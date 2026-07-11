"""Multi-Objective Edge Scorer for EV-aware swarm routing.

Provides a unified, configurable scoring function that evaluates the
heuristic desirability of a network edge using a weighted combination
of travel time, physical distance, energy consumption, congestion, and
emergency proximity objectives.

This scorer is designed to be shared across all swarm algorithms
(ACO, BCO, PSO, and E3-Hybrid) without modification.

References:
    Dorigo, M. & Gambardella, L.M. (1997). Ant Colony System.
    IEEE Transactions on Evolutionary Computation, 1(1), 53-66.

    Liu, W. et al. (2016). Multi-Objective Electric Vehicle Routing.
    Transportation Research Part C, 67, 427-441.
"""

from typing import Protocol, runtime_checkable

from src.core.network import Edge, Network
from src.core.vehicle import Vehicle
from src.utils.config import RoutingObjectivesConfig


@runtime_checkable
class IncidentProtocol(Protocol):
    """Structural protocol for incident objects used by the emergency scorer.

    Any object exposing ``distance_to_edge`` and ``intensity`` satisfies
    this protocol without requiring an explicit subclass relationship.
    This keeps the scorer decoupled from the emergency module.
    """

    intensity: float

    def distance_to_edge(self, edge: Edge, network: Network) -> float:
        """Returns shortest distance in metres from epicentre to edge."""
        ...


class MultiObjectiveEdgeScorer:
    """Computes a composite heuristic desirability score for a road edge.

    The score reflects multiple routing objectives simultaneously:
    travel time, physical distance, EV energy consumption, congestion
    severity, and emergency proximity. Each objective is individually
    normalised and weighted by the RoutingObjectivesConfig coefficients.

    The composite score S(e) is intended to be converted to a heuristic
    visibility value:
        eta(e) = 1.0 / S(e)
    so that edges with lower composite cost have higher desirability.

    Design principle:
        This class is stateless; every call to ``score_edge`` is pure and
        side-effect-free.  Swarm algorithm implementations should hold one
        shared scorer instance and inject it at construction time.
    """

    # Normalisation reference values – converted from physical units to
    # dimensionless fractions before applying weights.  These constants are
    # chosen to keep the per-objective contribution in roughly the same
    # magnitude range for typical urban networks.
    _TIME_REF_S: float = 60.0  # 60 s reference traversal time
    _DIST_REF_M: float = 500.0  # 500 m reference edge length
    _ENERGY_REF_KWH: float = 0.05  # 0.05 kWh reference energy per edge
    _CONGESTION_REF: float = 1.0  # Maximum possible congestion score

    def __init__(self, config: RoutingObjectivesConfig) -> None:
        """Initialises the scorer with objective weight configuration.

        Args:
            config: RoutingObjectivesConfig specifying the weight of each
                routing objective component.
        """
        self.config = config

    def score_edge(
        self,
        edge: Edge,
        vehicle: Vehicle | None,
        network: Network,
        active_incidents: list[object],
    ) -> float:
        """Computes the composite weighted cost score for a single edge.

        A score of 0.0 is theoretically perfect; in practice the score
        is always strictly positive because each component is clamped to
        a minimum positive value to avoid division-by-zero in the
        heuristic conversion.

        Args:
            edge: The directed road segment to score.
            vehicle: Optional EV instance providing battery parameters for
                the energy sub-score. If None, the energy component falls
                back to travel-time cost.
            network: The full road network graph.
            active_incidents: List of currently active Incident objects.
                Each must expose ``distance_to_edge(edge, network) -> float``
                and ``intensity: float``.

        Returns:
            float: Composite cost score >= 1e-9.
        """
        cfg = self.config

        # --- 1. Travel Time Component ---
        speed = edge.current_speed_limit
        if speed <= 0.0:
            # Edge is effectively impassable; return maximum cost
            return float("inf")

        time_s = edge.length / speed
        s_time = time_s / self._TIME_REF_S

        # --- 2. Distance Component ---
        s_dist = edge.length / self._DIST_REF_M

        # --- 3. Energy Component ---
        s_energy = self._compute_energy_score(edge, vehicle, speed)

        # --- 4. Congestion Component ---
        # Penalty = degradation from free-flow speed; 0.0 = free-flow,
        # 1.0 = fully stopped.  Multiplied by length to keep units
        # consistent with distance normalisation.
        congestion_penalty = (1.0 - edge.speed_reduction_factor) * edge.length
        s_congestion = congestion_penalty / self._DIST_REF_M

        # --- 5. Emergency Proximity Component ---
        s_emergency = self._compute_emergency_score(edge, network, active_incidents)

        # --- Weighted Combination ---
        score = (
            cfg.w_time * s_time
            + cfg.w_distance * s_dist
            + cfg.w_energy * s_energy
            + cfg.w_congestion * s_congestion
            + cfg.w_emergency * s_emergency
        )

        # Ensure strictly positive to avoid division-by-zero in eta(e) = 1/S
        return max(1e-9, score)

    def heuristic(
        self,
        edge: Edge,
        vehicle: Vehicle | None,
        network: Network,
        active_incidents: list[object],
    ) -> float:
        """Returns eta(e) = 1 / score(e), the heuristic desirability.

        Higher values indicate more desirable edges.  This is the form
        consumed directly in the ACS transition probability formula.

        Args:
            edge: The road segment.
            vehicle: Optional EV vehicle instance.
            network: Full road network graph.
            active_incidents: Currently active incident objects.

        Returns:
            float: Heuristic desirability value > 0.
        """
        s = self.score_edge(edge, vehicle, network, active_incidents)
        if s >= float("inf"):
            return 0.0
        return 1.0 / s

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _compute_energy_score(
        self,
        edge: Edge,
        vehicle: Vehicle | None,
        speed: float,
    ) -> float:
        """Returns the normalised energy cost sub-score for the edge."""
        if vehicle is None or vehicle.battery is None:
            # No EV model: use travel-time proxy normalised to energy ref
            time_s = edge.length / speed
            return time_s / self._TIME_REF_S

        raw_kwh = vehicle.battery.calculate_consumption(
            distance_m=edge.length,
            speed_m_s=speed,
            acceleration_m_s2=0.0,
            gradient_rad=edge.gradient_rad,
        )
        # Regenerative braking can make raw_kwh negative.  Clamp to 0.0
        # before normalisation; we score based on forward cost, not regen
        # benefit (which is handled implicitly via energy routing objective).
        energy_kwh = max(0.0, raw_kwh)
        return energy_kwh / self._ENERGY_REF_KWH

    def _compute_emergency_score(
        self,
        edge: Edge,
        network: Network,
        active_incidents: list[object],
    ) -> float:
        """Computes the emergency proximity hazard potential for the edge.

        Uses a gravity-potential field:
            S_emg = sum_i ( intensity_i / (dist_i + 1) )

        where dist_i is the distance in metres from incident i's epicentre
        to the closest point on the edge segment.

        Args:
            edge: The road segment to evaluate.
            network: The full network graph.
            active_incidents: List of active incident objects satisfying
                IncidentProtocol.

        Returns:
            float: Non-negative emergency hazard score.
        """
        if not active_incidents:
            return 0.0

        total = 0.0
        for incident in active_incidents:
            if not isinstance(incident, IncidentProtocol):
                continue
            try:
                dist = float(incident.distance_to_edge(edge, network))
                intensity = float(incident.intensity)
                total += intensity / (dist + 1.0)
            except (AttributeError, TypeError, ValueError):
                pass

        return total

    @staticmethod
    def edge_travel_time(edge: Edge) -> float:
        """Returns traversal time in seconds (convenience helper).

        Returns:
            float: Travel time in seconds, or inf if edge is impassable.
        """
        speed = edge.current_speed_limit
        if speed <= 0.0:
            return float("inf")
        return edge.length / speed

    @staticmethod
    def pheromone_heuristic(
        tau: float,
        eta: float,
        alpha: float,
        beta: float,
    ) -> float:
        """Computes the combined attractiveness: tau^alpha * eta^beta.

        This is the core ACS transition weight used in both the
        probabilistic selection and the exploitation selection rules.

        Args:
            tau: Pheromone concentration on the edge.
            eta: Heuristic desirability of the edge.
            alpha: Pheromone influence exponent.
            beta: Heuristic influence exponent.

        Returns:
            float: Attractiveness value >= 0.
        """
        if tau <= 0.0 or eta <= 0.0:
            return 0.0
        return float((tau**alpha) * (eta**beta))


def build_scorer(config: RoutingObjectivesConfig) -> MultiObjectiveEdgeScorer:
    """Factory function to construct a MultiObjectiveEdgeScorer.

    Args:
        config: RoutingObjectivesConfig specifying objective weights.

    Returns:
        MultiObjectiveEdgeScorer: Configured scorer instance.
    """
    return MultiObjectiveEdgeScorer(config)
