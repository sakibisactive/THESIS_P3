import os
from enum import StrEnum

import yaml
from pydantic import BaseModel, Field, model_validator

from src.utils.exceptions import ConfigValidationError


class SimulationConfig(BaseModel):
    """Configuration for simulation execution settings."""

    dt: float = Field(default=1.0, description="Simulation step duration in seconds")
    max_steps: int = Field(default=3600, description="Maximum simulation steps")
    mode: str = Field(
        default="standalone",
        description="Simulation engine mode ('standalone' or 'sumo')",
    )
    network_file_path: str = Field(
        ..., description="Path to network configuration file"
    )

    @model_validator(mode="after")
    def validate_mode(self) -> "SimulationConfig":
        if self.mode not in ("standalone", "sumo"):
            raise ValueError("Simulation mode must be either 'standalone' or 'sumo'")
        if self.dt <= 0:
            raise ValueError("dt must be greater than zero")
        if self.max_steps <= 0:
            raise ValueError("max_steps must be greater than zero")
        return self


class BatteryConfig(BaseModel):
    """Parameters for physical electric vehicle energy consumption modeling."""

    capacity_kwh: float = Field(
        ..., description="Total battery capacity in kilowatt-hours"
    )
    mass_kg: float = Field(..., description="Vehicle mass in kilograms")
    efficiency: float = Field(
        default=0.9,
        description="Powertrain efficiency coefficient (0.0 to 1.0)",
    )
    drag_coeff: float = Field(default=0.25, description="Aerodynamic drag coefficient")
    frontal_area: float = Field(
        default=2.2, description="Vehicle frontal area in square meters"
    )
    rolling_res_coeff: float = Field(
        default=0.01, description="Rolling resistance coefficient"
    )
    regen_efficiency: float = Field(
        default=0.7,
        description="Regenerative braking efficiency (0.0 to 1.0)",
    )

    @model_validator(mode="after")
    def validate_coefficients(self) -> "BatteryConfig":
        if not (0.0 <= self.efficiency <= 1.0):
            raise ValueError("Efficiency must be between 0.0 and 1.0")
        if not (0.0 <= self.regen_efficiency <= 1.0):
            raise ValueError("Regen efficiency must be between 0.0 and 1.0")
        if self.capacity_kwh <= 0:
            raise ValueError("Battery capacity must be greater than zero")
        if self.mass_kg <= 0:
            raise ValueError("Vehicle mass must be greater than zero")
        return self


class ChargingStationConfig(BaseModel):
    """Configuration for individual electric vehicle charging stations."""

    id: str = Field(..., description="Unique charging station identifier")
    node_id: str = Field(
        ..., description="Network node ID where the station is located"
    )
    capacity: int = Field(..., description="Number of concurrent chargers/slots")
    power_kw: float = Field(..., description="Charger output rate in kilowatts")
    base_price_per_kwh: float = Field(
        default=0.35, description="Base charging fee per kWh"
    )

    @model_validator(mode="after")
    def validate_station(self) -> "ChargingStationConfig":
        if self.capacity <= 0:
            raise ValueError("Station capacity must be greater than zero")
        if self.power_kw <= 0:
            raise ValueError("Station charging power must be greater than zero")
        return self


class BoundingBox(BaseModel):
    """2D bounding box representing spatial area in the network coordinate system."""

    min_x: float
    min_y: float
    max_x: float
    max_y: float

    @model_validator(mode="after")
    def validate_bounds(self) -> "BoundingBox":
        if self.min_x > self.max_x:
            raise ValueError("min_x cannot be greater than max_x")
        if self.min_y > self.max_y:
            raise ValueError("min_y cannot be greater than max_y")
        return self


class CommunicationConfig(BaseModel):
    """Configuration for V2X communications and failure parameters."""

    v2v_range_m: float = Field(
        default=300.0, description="V2V transmission range in meters"
    )
    v2i_range_m: float = Field(
        default=500.0, description="V2I transmission range in meters"
    )
    base_packet_loss_rate: float = Field(
        default=0.05,
        description="Baseline random packet loss probability (0.0 to 1.0)",
    )
    base_latency_s: float = Field(
        default=0.002, description="Base communication latency in seconds"
    )
    latency_jitter_s: float = Field(
        default=0.001, description="Latency jitter variation in seconds"
    )
    propagation_speed_m_s: float = Field(
        default=3.0e8, description="Signal propagation speed in meters/second"
    )
    blackout_start_time: float | None = Field(
        default=None, description="Start time of communication blackout (seconds)"
    )
    blackout_end_time: float | None = Field(
        default=None, description="End time of communication blackout (seconds)"
    )
    blackout_area: BoundingBox | None = Field(
        default=None, description="Spatial boundaries of the blackout zone"
    )

    @model_validator(mode="after")
    def validate_loss_rate(self) -> "CommunicationConfig":
        if not (0.0 <= self.base_packet_loss_rate <= 1.0):
            raise ValueError("Base packet loss rate must be between 0.0 and 1.0")
        if self.v2v_range_m <= 0:
            raise ValueError("v2v_range_m must be positive")
        if self.v2i_range_m <= 0:
            raise ValueError("v2i_range_m must be positive")
        if self.base_latency_s < 0:
            raise ValueError("base_latency_s must be non-negative")
        if self.latency_jitter_s < 0:
            raise ValueError("latency_jitter_s must be non-negative")
        if self.propagation_speed_m_s <= 0:
            raise ValueError("propagation_speed_m_s must be positive")
        return self


class EmergencyEventConfig(BaseModel):
    """Configuration for a dynamic spatiotemporal emergency event."""

    id: str = Field(..., description="Unique event identifier")
    epicenter_node_id: str = Field(
        ..., description="Node ID serving as the center of the incident"
    )
    start_time: float = Field(
        ..., description="Simulation time when the incident begins (seconds)"
    )
    duration: float = Field(
        ..., description="How long the emergency remains active in seconds"
    )
    initial_radius_m: float = Field(
        default=10.0, description="Initial radius of the hazard in meters"
    )
    propagation_rate: float = Field(
        default=1.0,
        description="Speed at which the hazard expands in meters/second",
    )
    intensity: float = Field(
        default=1.0, description="Peak hazard severity/disruption level"
    )

    @model_validator(mode="after")
    def validate_event(self) -> "EmergencyEventConfig":
        if self.start_time < 0:
            raise ValueError("Event start_time cannot be negative")
        if self.duration <= 0:
            raise ValueError("Event duration must be positive")
        if self.initial_radius_m < 0:
            raise ValueError("Event initial_radius_m cannot be negative")
        if self.propagation_rate < 0:
            raise ValueError("Event propagation_rate cannot be negative")
        return self


class InfrastructureFailureType(StrEnum):
    """Enumeration of possible infrastructure failure types."""

    COMMUNICATION = "COMMUNICATION"
    CHARGING_STATION = "CHARGING_STATION"
    ROAD_FAILURE = "ROAD_FAILURE"


class InfrastructureFailureConfig(BaseModel):
    """Configuration for a dynamic infrastructure failure."""

    id: str = Field(..., description="Unique failure identifier")
    failure_type: InfrastructureFailureType = Field(..., description="Type of failure")
    start_time: float = Field(..., description="Start time in seconds")
    duration: float = Field(..., description="Duration in seconds")
    target_id: str = Field(..., description="Target node/edge/station ID")
    blackout_area: BoundingBox | None = Field(
        default=None, description="Spatial boundaries of the blackout zone"
    )

    @model_validator(mode="after")
    def validate_failure(self) -> "InfrastructureFailureConfig":
        if self.start_time < 0:
            raise ValueError("Failure start_time cannot be negative")
        if self.duration <= 0:
            raise ValueError("Failure duration must be positive")
        if (
            self.failure_type == InfrastructureFailureType.COMMUNICATION
            and self.blackout_area is None
        ):
            raise ValueError("COMMUNICATION failure requires blackout_area")
        return self


class AmbulanceDispatchConfig(BaseModel):
    """Configuration for dynamic ambulance vehicle dispatches."""

    id: str = Field(..., description="Unique vehicle/dispatch identifier")
    start_time: float = Field(..., description="Start time in seconds")
    origin_node_id: str = Field(..., description="Origin node ID")
    destination_node_id: str = Field(..., description="Destination node ID")
    battery_capacity_kwh: float = Field(
        default=80.0, description="Battery capacity in kWh"
    )
    initial_soc: float = Field(
        default=1.0, description="Initial State of Charge (0.0 to 1.0)"
    )
    v2v_range_m: float = Field(
        default=300.0, description="V2V transmission range in meters"
    )
    v2i_range_m: float = Field(
        default=500.0, description="V2I transmission range in meters"
    )
    speed_m_s: float = Field(
        default=25.0, description="Cruising speed limit of the ambulance in m/s"
    )
    route: list[str] = Field(
        default_factory=list, description="List of edge IDs for the ambulance route"
    )

    @model_validator(mode="after")
    def validate_dispatch(self) -> "AmbulanceDispatchConfig":
        if self.start_time < 0:
            raise ValueError("Dispatch start_time cannot be negative")
        if not (0.0 <= self.initial_soc <= 1.0):
            raise ValueError("Initial SoC must be in [0.0, 1.0]")
        if self.battery_capacity_kwh <= 0:
            raise ValueError("battery_capacity_kwh must be positive")
        if self.v2v_range_m <= 0:
            raise ValueError("v2v_range_m must be positive")
        if self.v2i_range_m <= 0:
            raise ValueError("v2i_range_m must be positive")
        if self.speed_m_s <= 0:
            raise ValueError("speed_m_s must be positive")
        return self


class RoadClosureConfig(BaseModel):
    """Configuration for dynamic road closures."""

    id: str = Field(..., description="Unique closure identifier")
    start_time: float = Field(..., description="Start time in seconds")
    duration: float = Field(..., description="Duration in seconds")
    edge_id: str = Field(..., description="Target edge ID to close")

    @model_validator(mode="after")
    def validate_closure(self) -> "RoadClosureConfig":
        if self.start_time < 0:
            raise ValueError("Closure start_time cannot be negative")
        if self.duration <= 0:
            raise ValueError("Closure duration must be positive")
        return self


class RoutingObjectivesConfig(BaseModel):
    """Weight coefficients for the multi-objective edge scoring function.

    Controls the relative influence of each objective on the edge heuristic
    desirability used by swarm algorithms (ACO, BCO, PSO, E3-Hybrid).
    All weights are applied as a convex combination.
    """

    w_time: float = Field(
        default=0.4,
        description="Weight for travel time objective (seconds).",
    )
    w_distance: float = Field(
        default=0.1,
        description="Weight for physical distance objective (meters).",
    )
    w_energy: float = Field(
        default=0.3,
        description="Weight for EV energy consumption objective (kWh).",
    )
    w_congestion: float = Field(
        default=0.1,
        description="Weight for congestion penalty objective.",
    )
    w_emergency: float = Field(
        default=0.1,
        description="Weight for emergency proximity hazard potential objective.",
    )

    @model_validator(mode="after")
    def validate_weights(self) -> "RoutingObjectivesConfig":
        total = (
            self.w_time
            + self.w_distance
            + self.w_energy
            + self.w_congestion
            + self.w_emergency
        )
        if total <= 0.0:
            raise ValueError(
                "At least one routing objective weight must be positive."
            )
        return self


class ACOConfig(BaseModel):
    """Hyperparameters for the Ant Colony System (ACS) routing algorithm.

    Reference: Dorigo, M. & Gambardella, L.M. (1997). Ant Colony System:
    A Cooperative Learning Approach to the Travelling Salesman Problem.
    IEEE Transactions on Evolutionary Computation, 1(1), 53-66.
    """

    num_ants: int = Field(
        default=10, description="Number of ants per search iteration."
    )
    max_iterations: int = Field(
        default=50,
        description="Maximum number of search iterations per routing query.",
    )
    alpha: float = Field(
        default=1.0,
        description="Pheromone trail influence exponent (tau^alpha).",
    )
    beta: float = Field(
        default=2.0,
        description="Heuristic desirability influence exponent (eta^beta).",
    )
    q_zero: float = Field(
        default=0.9,
        description=(
            "ACS exploitation threshold q0 in [0, 1]. Higher values favour "
            "exploitation of best known paths over probabilistic exploration."
        ),
    )
    evaporation_rate: float = Field(
        default=0.1,
        description="Global pheromone evaporation rate rho in (0, 1).",
    )
    local_evaporation_rate: float = Field(
        default=0.1,
        description=(
            "Local pheromone update decay rate xi in (0, 1). Applied "
            "immediately when an ant traverses an edge."
        ),
    )
    q: float = Field(
        default=1.0,
        description="Pheromone deposit constant Q for global update.",
    )
    initial_pheromone: float = Field(
        default=0.1,
        description="Initial pheromone concentration tau_0 on all edges.",
    )
    min_pheromone: float = Field(
        default=1e-6,
        description="Minimum allowed pheromone concentration (tau_min).",
    )
    max_pheromone: float = Field(
        default=10.0,
        description="Maximum allowed pheromone concentration (tau_max).",
    )
    evaporation_dt: float = Field(
        default=1.0,
        description=(
            "Minimum elapsed simulation time (seconds) between global "
            "evaporation steps. Used by lazy temporal evaporation."
        ),
    )
    collect_metrics: bool = Field(
        default=False,
        description=(
            "Whether to collect per-iteration ACO research metrics "
            "(convergence, pheromone stats, exploration ratios)."
        ),
    )

    @model_validator(mode="after")
    def validate_aco(self) -> "ACOConfig":
        if not 0.0 <= self.q_zero <= 1.0:
            raise ValueError("q_zero must be in [0.0, 1.0]")
        if not 0.0 < self.evaporation_rate < 1.0:
            raise ValueError("evaporation_rate must be in (0.0, 1.0)")
        if not 0.0 < self.local_evaporation_rate < 1.0:
            raise ValueError("local_evaporation_rate must be in (0.0, 1.0)")
        if self.num_ants < 1:
            raise ValueError("num_ants must be >= 1")
        if self.max_iterations < 1:
            raise ValueError("max_iterations must be >= 1")
        if self.min_pheromone >= self.max_pheromone:
            raise ValueError(
                "min_pheromone must be strictly less than max_pheromone"
            )
        if self.initial_pheromone < self.min_pheromone:
            raise ValueError(
                "initial_pheromone must be >= min_pheromone"
            )
        return self


class BCOConfig(BaseModel):
    """Hyperparameters for Bee Colony Optimization path exploration."""

    scout_ratio: float = Field(
        default=0.2, description="Ratio of total vehicles designated as scouts"
    )
    max_alternative_routes: int = Field(
        default=3, description="Maximum number of alternative detour paths managed"
    )
    recruitment_factor: float = Field(
        default=0.5,
        description="Probability parameter for path advertising/waggle dance",
    )


class PSOConfig(BaseModel):
    """Hyperparameters for Particle Swarm Optimization parameter tuning."""

    cognitive_weight: float = Field(
        default=1.5, description="Acceleration constant c1 for personal best"
    )
    social_weight: float = Field(
        default=1.5, description="Acceleration constant c2 for global best"
    )
    inertia_weight: float = Field(
        default=0.8, description="Inertia weight w for velocity update"
    )
    swarm_size: int = Field(
        default=30, description="Number of particles evaluated in swarm"
    )


class AlgorithmConfig(BaseModel):
    """Global parameters for all comparison and hybrid routing algorithms."""

    objectives: RoutingObjectivesConfig = Field(
        default_factory=RoutingObjectivesConfig
    )
    aco: ACOConfig = Field(default_factory=ACOConfig)
    bco: BCOConfig = Field(default_factory=BCOConfig)
    pso: PSOConfig = Field(default_factory=PSOConfig)


class ScenarioConfig(BaseModel):
    """The root configuration object containing all simulation parameters."""

    name: str = Field(..., description="Name of the scenario")
    simulation: SimulationConfig
    battery: BatteryConfig
    charging_stations: list[ChargingStationConfig] = Field(default_factory=list)
    communication: CommunicationConfig = Field(default_factory=CommunicationConfig)
    emergencies: list[EmergencyEventConfig] = Field(default_factory=list)
    infrastructure_failures: list[InfrastructureFailureConfig] = Field(
        default_factory=list
    )
    ambulance_dispatches: list[AmbulanceDispatchConfig] = Field(default_factory=list)
    road_closures: list[RoadClosureConfig] = Field(default_factory=list)
    algorithms: AlgorithmConfig = Field(default_factory=AlgorithmConfig)


def load_scenario_config(filepath: str) -> ScenarioConfig:
    """Loads, parses, and validates a YAML scenario config file.

    Args:
        filepath: Absolute path to the YAML file.

    Returns:
        ScenarioConfig: The parsed and validated configuration model.

    Raises:
        ConfigValidationError: If file is missing, invalid YAML, or fails validation.
    """
    if not os.path.exists(filepath):
        msg = f"Scenario configuration file not found: {filepath}"
        raise ConfigValidationError(msg)

    try:
        with open(filepath, encoding="utf-8") as f:
            data = yaml.safe_load(f)
    except yaml.YAMLError as e:
        msg = f"Invalid YAML syntax in configuration file: {e}"
        raise ConfigValidationError(msg) from e
    except Exception as e:
        msg = f"Failed to read configuration file: {e}"
        raise ConfigValidationError(msg) from e

    if data is None:
        raise ConfigValidationError(f"Configuration file is empty: {filepath}")

    try:
        return ScenarioConfig.model_validate(data)
    except Exception as e:
        raise ConfigValidationError(f"Configuration validation failed:\n{e}") from e
