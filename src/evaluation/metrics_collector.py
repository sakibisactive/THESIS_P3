"""Metrics collector for tracking simulation run results and diagnostics."""

from typing import Any

from pydantic import BaseModel, Field


class SubsystemContribution(BaseModel):
    """Tracks E3-Hybrid subsystem contributions for a query."""

    aco_contrib: float = 0.0
    bco_contrib: float = 0.0
    pso_contrib: float = 0.0


class SimulationRunMetrics(BaseModel):
    """Encapsulates all collected metrics for a single simulation run."""

    # Metadata
    algorithm_name: str
    scenario_name: str
    seed: int
    config_details: dict[str, Any] = Field(default_factory=dict)
    timestamp: str = ""
    ablation_settings: dict[str, bool] = Field(default_factory=dict)
    
    # Telemetry Metrics
    cpu_utilization_percent: float = 0.0
    memory_usage_mb: float = 0.0

    # Traffic Metrics
    vehicle_travel_times: dict[str, float] = Field(
        default_factory=dict
    )  # veh_id -> time (s)
    vehicle_free_flow_times: dict[str, float] = Field(
        default_factory=dict
    )  # veh_id -> time (s)
    vehicle_delays: dict[str, float] = Field(
        default_factory=dict
    )  # veh_id -> delay (s)
    total_rerouting_events: int = 0
    vehicle_reroutes: dict[str, int] = Field(default_factory=dict)  # veh_id -> count
    congestion_levels_over_time: list[float] = Field(
        default_factory=list
    )  # speed ratio per step
    throughput_over_time: list[int] = Field(default_factory=list)  # arrivals per step

    # Emergency Metrics
    ambulance_travel_times: dict[str, float] = Field(
        default_factory=dict
    )  # amb_id -> time (s)
    ambulance_response_times: dict[str, float] = Field(
        default_factory=dict
    )  # amb_id -> response time (s)
    ambulance_success_rate: float = 0.0
    emergency_corridor_activation_time: float = 0.0  # total cumulative yielding time
    emergency_corridor_activation_count: int = (
        0  # number of times corridor yielding triggered
    )

    # Communication Metrics
    packets_sent: int = 0
    packets_delivered: int = 0
    packet_delivery_ratio: float = 0.0
    message_latencies: list[float] = Field(default_factory=list)
    packet_loss_count: int = 0
    communication_overhead_per_vehicle: dict[str, int] = Field(
        default_factory=dict
    )  # veh_id -> packets sent

    # EV Metrics
    vehicle_energy_consumed: dict[str, float] = Field(
        default_factory=dict
    )  # veh_id -> energy (kWh)
    vehicle_travelled_distance: dict[str, float] = Field(
        default_factory=dict
    )  # veh_id -> distance (m)
    charging_queue_lengths_over_time: list[float] = Field(
        default_factory=list
    )  # average queue length per step
    stranded_vehicle_count: int = 0
    total_charging_events: int = 0
    vehicle_charging_events: dict[str, int] = Field(
        default_factory=dict
    )  # veh_id -> count

    # Algorithm Metrics
    router_execution_times: list[float] = Field(
        default_factory=list
    )  # find_route call durations (s)
    router_convergence_speeds: list[int] = Field(
        default_factory=list
    )  # iterations to best path
    adaptation_times_after_disruptions: list[float] = Field(
        default_factory=list
    )  # steps/time to stabilize routes
    route_stability_metrics: list[float] = Field(
        default_factory=list
    )  # path similarity scores
    subsystem_contributions: list[SubsystemContribution] = Field(default_factory=list)
    exploration_ratios: list[float] = Field(default_factory=list)


class MetricsCollector:
    """Collects and aggregates metrics during a simulation run."""

    def __init__(
        self,
        algorithm_name: str,
        scenario_name: str,
        seed: int,
        config_details: dict[str, Any],
        ablation_settings: dict[str, bool] | None = None,
    ) -> None:
        import datetime

        self.metrics = SimulationRunMetrics(
            algorithm_name=algorithm_name,
            scenario_name=scenario_name,
            seed=seed,
            config_details=config_details,
            timestamp=datetime.datetime.now().isoformat(),
            ablation_settings=ablation_settings or {},
        )
        self._temp_vehicle_start_times: dict[str, float] = {}
        self._temp_ambulance_dispatch_times: dict[str, float] = {}
        self._temp_yielding_vehicles: set[str] = set()

    def record_vehicle_spawn(self, vehicle_id: str, current_time: float) -> None:
        """Records when a vehicle is spawned/started its journey."""
        self._temp_vehicle_start_times[vehicle_id] = current_time

    def record_vehicle_arrival(
        self,
        vehicle_id: str,
        travel_time: float,
        energy_consumed: float,
        distance_m: float,
        free_flow_time: float,
    ) -> None:
        """Records metrics for a vehicle arriving at its destination."""
        self.metrics.vehicle_travel_times[vehicle_id] = travel_time
        self.metrics.vehicle_free_flow_times[vehicle_id] = free_flow_time
        self.metrics.vehicle_delays[vehicle_id] = max(0.0, travel_time - free_flow_time)
        self.metrics.vehicle_energy_consumed[vehicle_id] = energy_consumed
        self.metrics.vehicle_travelled_distance[vehicle_id] = distance_m

    def record_stranded_vehicle(self) -> None:
        """Increments stranded vehicle count."""
        self.metrics.stranded_vehicle_count += 1

    def record_reroute(self, vehicle_id: str) -> None:
        """Records a rerouting event for a vehicle."""
        self.metrics.total_rerouting_events += 1
        self.metrics.vehicle_reroutes[vehicle_id] = (
            self.metrics.vehicle_reroutes.get(vehicle_id, 0) + 1
        )

    def record_charging_event(self, vehicle_id: str) -> None:
        """Records a battery charging event."""
        self.metrics.total_charging_events += 1
        self.metrics.vehicle_charging_events[vehicle_id] = (
            self.metrics.vehicle_charging_events.get(vehicle_id, 0) + 1
        )

    def record_packet_transmit(self, sender_id: str) -> None:
        """Records a V2X packet transmission."""
        self.metrics.packets_sent += 1
        self.metrics.communication_overhead_per_vehicle[sender_id] = (
            self.metrics.communication_overhead_per_vehicle.get(sender_id, 0) + 1
        )

    def record_packet_deliver(self, latency: float) -> None:
        """Records a V2X packet delivery."""
        self.metrics.packets_delivered += 1
        self.metrics.message_latencies.append(latency)

    def record_packet_loss(self) -> None:
        """Records a dropped packet."""
        self.metrics.packet_loss_count += 1

    def record_router_invocation(
        self,
        execution_time: float,
        convergence_iter: int | None = None,
        exploration_ratio: float | None = None,
    ) -> None:
        """Logs engine execution metrics."""
        self.metrics.router_execution_times.append(execution_time)
        if convergence_iter is not None:
            self.metrics.router_convergence_speeds.append(convergence_iter)
        if exploration_ratio is not None:
            self.metrics.exploration_ratios.append(exploration_ratio)

    def record_subsystem_contribution(self, aco: float, bco: float, pso: float) -> None:
        """Logs E3-Hybrid subsystem contributions for the iteration."""
        self.metrics.subsystem_contributions.append(
            SubsystemContribution(aco_contrib=aco, bco_contrib=bco, pso_contrib=pso)
        )

    def record_adaptation_time(self, duration: float) -> None:
        """Logs route adaptation time after network disruptions."""
        self.metrics.adaptation_times_after_disruptions.append(duration)

    def record_route_stability(self, similarity: float) -> None:
        """Logs path similarity metric."""
        self.metrics.route_stability_metrics.append(similarity)

    def record_ambulance_dispatch(self, ambulance_id: str, current_time: float) -> None:
        """Records dispatch time of an ambulance."""
        self._temp_ambulance_dispatch_times[ambulance_id] = current_time

    def record_ambulance_arrival(
        self, ambulance_id: str, travel_time: float, response_time: float
    ) -> None:
        """Records ambulance completion metrics."""
        self.metrics.ambulance_travel_times[ambulance_id] = travel_time
        self.metrics.ambulance_response_times[ambulance_id] = response_time

    def update_step_metrics(
        self,
        active_yielding_vehicles: set[str],
        dt: float,
        average_queue_len: float,
        throughput: int,
        average_speed_ratio: float,
    ) -> None:
        """Updates metrics computed at each simulation step."""
        # Update emergency yielding corridor metrics
        current_yielding = len(active_yielding_vehicles)
        if current_yielding > 0:
            self.metrics.emergency_corridor_activation_time += dt * current_yielding
            # If new vehicles started yielding
            newly_yielding = active_yielding_vehicles - self._temp_yielding_vehicles
            self.metrics.emergency_corridor_activation_count += len(newly_yielding)
        self._temp_yielding_vehicles = active_yielding_vehicles

        # Queue lengths over time
        self.metrics.charging_queue_lengths_over_time.append(average_queue_len)
        self.metrics.throughput_over_time.append(throughput)
        self.metrics.congestion_levels_over_time.append(average_speed_ratio)

    def finalize(self, total_ambulances: int) -> SimulationRunMetrics:
        """Finalizes summary metric calculations at the end of the simulation run."""
        # Calculate packet delivery ratio
        if self.metrics.packets_sent > 0:
            self.metrics.packet_delivery_ratio = (
                self.metrics.packets_delivered / self.metrics.packets_sent
            )
        else:
            self.metrics.packet_delivery_ratio = 1.0

        # Calculate ambulance success rate
        arrived_ambulances = len(self.metrics.ambulance_travel_times)
        if total_ambulances > 0:
            self.metrics.ambulance_success_rate = arrived_ambulances / total_ambulances
        else:
            self.metrics.ambulance_success_rate = 1.0

        # Collect CPU and Memory utilization
        try:
            import psutil
            process = psutil.Process()
            self.metrics.memory_usage_mb = float(process.memory_info().rss / (1024.0 * 1024.0))
            # System-wide or process-specific CPU percentage
            self.metrics.cpu_utilization_percent = float(psutil.cpu_percent())
        except Exception:
            pass

        return self.metrics
