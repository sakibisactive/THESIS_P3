import os
from enum import StrEnum

from typing import Any
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
        default="", description="Path to network configuration file"
    )
    
    # Path configuration fields for file loading/compilation
    osm_file: str | None = Field(
        default=None, description="Path to raw OpenStreetMap (.osm) file"
    )
    network_file: str | None = Field(
        default=None, description="Path to compiled SUMO (.net.xml) file"
    )
    route_file: str | None = Field(
        default=None, description="Path to SUMO route or trip file"
    )
    scenario_file: str | None = Field(
        default=None, description="Path to scenario definition file"
    )
    output_dir: str | None = Field(
        default=None, description="Path to output directory"
    )
    
    # SUMO integration configuration parameters
    sumo_binary: str = Field(
        default="sumo", description="Executable name or path for SUMO"
    )
    use_gui: bool = Field(
        default=False, description="Whether to run SUMO with GUI interface"
    )
    step_length: float = Field(
        default=1.0, description="Step length in seconds for SUMO"
    )
    seed: int = Field(
        default=42, description="Random seed for SUMO and traffic generation"
    )
    traci_port: int = Field(
        default=8813, description="Port for TraCI connection"
    )
    output_directory: str = Field(
        default="outputs", description="Directory to save simulation outputs"
    )
    enable_subscriptions: bool = Field(
        default=True, description="Whether to use TraCI subscription queries"
    )
    real_time_factor: float = Field(
        default=-1.0,
        description="Target real-time speed factor for SUMO, -1 for unlimited",
    )

    @model_validator(mode="after")
    def validate_mode(self) -> "SimulationConfig":
        if self.mode not in ("standalone", "sumo"):
            raise ValueError("Simulation mode must be either 'standalone' or 'sumo'")
        if self.dt <= 0:
            raise ValueError("dt must be greater than zero")
        if self.max_steps <= 0:
            raise ValueError("max_steps must be greater than zero")
        if self.step_length <= 0:
            raise ValueError("step_length must be greater than zero")
            
        # Update output_directory if output_dir is specified
        if self.output_dir:
            self.output_directory = self.output_dir
            
        # Sync network_file_path if missing but network_file is provided
        if not self.network_file_path and self.network_file:
            self.network_file_path = self.network_file
            
        # If neither is specified but osm_file is, we will generate network_file later, 
        # so we don't fail validation immediately if osm_file is present.
        if not self.network_file_path and not self.network_file and not self.osm_file:
            raise ValueError(
                "At least one of network_file_path, network_file, or "
                "osm_file must be specified."
            )
            
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

    @model_validator(mode="before")
    @classmethod
    def map_aliases_and_defaults(cls, data: Any) -> Any:
        if isinstance(data, dict):
            mappings = {
                "weight_travel_time": "w_time",
                "weight_distance": "w_distance",
                "weight_energy_consumption": "w_energy",
                "weight_congestion": "w_congestion",
                "weight_safety": "w_emergency",
            }
            mapped_data = {}
            has_custom = any(k in data for k in mappings)
            for legacy_key, internal_key in mappings.items():
                if legacy_key in data:
                    mapped_data[internal_key] = data[legacy_key]
                elif internal_key in data:
                    mapped_data[internal_key] = data[internal_key]
                elif has_custom:
                    mapped_data[internal_key] = 0.0
            for k, v in mapped_data.items():
                data[k] = v
        return data

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
            raise ValueError("At least one routing objective weight must be positive.")
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
            raise ValueError("min_pheromone must be strictly less than max_pheromone")
        if self.initial_pheromone < self.min_pheromone:
            raise ValueError("initial_pheromone must be >= min_pheromone")
        return self


class BCOConfig(BaseModel):
    """Hyperparameters for Bee Colony Optimization (BCO) routing.

    Reference: Lučić, P. & Teodorović, D. (2001). Bee System: Solving routing
    problems by artificial bees. Journal of Heuristics, 7, 507-526.
    """

    colony_size: int = Field(
        default=20, description="Total number of bees in the colony (B)."
    )
    max_iterations: int = Field(
        default=50, description="Maximum number of search iterations per query (I)."
    )
    scout_ratio: float = Field(
        default=0.2, description="Ratio of colony acting as scout bees."
    )
    recruitment_factor: float = Field(
        default=0.5,
        description="Base probability scalar for recruiter waggle dance loyalty.",
    )
    abandonment_threshold: float = Field(
        default=0.2,
        description="Probability below which a bee abandons its route.",
    )
    elite_route_seeding: bool = Field(
        default=False,
        description=(
            "If True, seeds the first iteration of a new query with the "
            "best route from the previous query to accelerate convergence "
            "in dynamic networks. Must be False for independent benchmarks."
        ),
    )
    collect_metrics: bool = Field(
        default=False,
        description="Collect per-iteration research metrics for BCO evaluation.",
    )

    @model_validator(mode="after")
    def validate_bco(self) -> "BCOConfig":
        if self.colony_size < 1:
            raise ValueError("colony_size must be >= 1")
        if self.max_iterations < 1:
            raise ValueError("max_iterations must be >= 1")
        if not 0.0 < self.scout_ratio <= 1.0:
            raise ValueError("scout_ratio must be in (0, 1]")
        if not 0.0 < self.recruitment_factor <= 1.0:
            raise ValueError("recruitment_factor must be in (0, 1]")
        if not 0.0 <= self.abandonment_threshold <= 1.0:
            raise ValueError("abandonment_threshold must be in [0, 1]")
        return self


class PSOConfig(BaseModel):
    """Hyperparameters for Particle Swarm Optimization (PSO) routing.

    Uses Edge Priority-Based Encoding mapping continuous positions
    to combinatorial paths via DFS.
    """

    swarm_size: int = Field(
        default=20, description="Number of particles in the swarm (S)."
    )
    max_iterations: int = Field(
        default=50, description="Maximum number of search iterations per query (I)."
    )
    inertia_weight: float = Field(
        default=0.7, description="Inertia weight factor (omega) for velocity update."
    )
    cognitive_weight: float = Field(
        default=1.5, description="Acceleration constant c1 for personal best."
    )
    social_weight: float = Field(
        default=1.5, description="Acceleration constant c2 for global best."
    )
    v_max: float = Field(
        default=5.0, description="Maximum absolute velocity for priority clamping."
    )
    collect_metrics: bool = Field(
        default=False,
        description="Collect per-iteration research metrics for PSO evaluation.",
    )

    @model_validator(mode="after")
    def validate_pso(self) -> "PSOConfig":
        if self.swarm_size < 1:
            raise ValueError("swarm_size must be >= 1")
        if self.max_iterations < 1:
            raise ValueError("max_iterations must be >= 1")
        if self.v_max <= 0.0:
            raise ValueError("v_max must be positive")
        return self


class E3HybridConfig(BaseModel):
    """Configuration and ablation toggles for the E3-Hybrid Swarm Routing system."""

    max_iterations: int = Field(
        default=50, description="Maximum number of search iterations per query (I)."
    )
    collect_metrics: bool = Field(
        default=True,
        description="Collect per-iteration research metrics for hybrid evaluation.",
    )

    # Information Sharing Ablation Toggles
    share_aco_to_pso: bool = Field(
        default=True,
        description="If True, ACO pheromones bias PSO particle initialization.",
    )
    share_gbest_to_pso: bool = Field(
        default=True,
        description="If True, Hybrid G_best acts as the global attractor for PSO.",
    )
    share_gbest_to_bco: bool = Field(
        default=True,
        description="If True, Hybrid G_best seeds BCO recruiters.",
    )
    share_bco_pso_to_aco: bool = Field(
        default=True,
        description="If True, Hybrid G_best triggers ACO global pheromone update.",
    )

    @model_validator(mode="after")
    def validate_hybrid(self) -> "E3HybridConfig":
        if self.max_iterations < 1:
            raise ValueError("max_iterations must be >= 1")
        return self


class AlgorithmConfig(BaseModel):
    """Global parameters for all comparison and hybrid routing algorithms."""

    objectives: RoutingObjectivesConfig = Field(default_factory=RoutingObjectivesConfig)
    aco: ACOConfig = Field(default_factory=ACOConfig)
    bco: BCOConfig = Field(default_factory=BCOConfig)
    pso: PSOConfig = Field(default_factory=PSOConfig)
    e3_hybrid: E3HybridConfig = Field(default_factory=E3HybridConfig)


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
