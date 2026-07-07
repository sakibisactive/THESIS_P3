from src.core.battery import BatteryModel
from src.emergency.failure import InfrastructureFailure
from src.emergency.incident import Incident
from src.emergency.scenario_manager import (
    ApplyFailureEvent,
    ApplyRoadClosureEvent,
    DispatchAmbulanceEvent,
    RoadClosure,
    ScenarioManager,
    SpawnIncidentEvent,
)
from src.utils.config import BatteryConfig, ScenarioConfig


class ScenarioLoader:
    """Populates ScenarioManager events from a validated ScenarioConfig."""

    @staticmethod
    def load_scenario(scenario_config: ScenarioConfig) -> ScenarioManager:
        """Translates scenario configuration parameters into scheduler events.

        Args:
            scenario_config: The ScenarioConfig root object.

        Returns:
            ScenarioManager: Manager loaded with all configured simulation events.
        """
        manager = ScenarioManager()

        # 1. Schedule dynamic hazards (incidents)
        for inc_cfg in scenario_config.emergencies:
            incident = Incident(inc_cfg)
            manager.scheduler.schedule(SpawnIncidentEvent(incident))

        # 2. Schedule infrastructure failures (road blocks, charging outages, blackouts)
        for fail_cfg in scenario_config.infrastructure_failures:
            failure = InfrastructureFailure(fail_cfg)
            manager.scheduler.schedule(ApplyFailureEvent(failure))

        # 3. Schedule dedicated road closures
        for closure_cfg in scenario_config.road_closures:
            closure = RoadClosure(
                closure_id=closure_cfg.id,
                edge_id=closure_cfg.edge_id,
                start_time=closure_cfg.start_time,
                duration=closure_cfg.duration,
            )
            manager.scheduler.schedule(ApplyRoadClosureEvent(closure))

        # 4. Schedule ambulance vehicle dispatches
        for amb_cfg in scenario_config.ambulance_dispatches:
            # Overwrite default battery capacity with specific dispatch parameters
            amb_battery_config = BatteryConfig(
                capacity_kwh=amb_cfg.battery_capacity_kwh,
                mass_kg=scenario_config.battery.mass_kg,
                efficiency=scenario_config.battery.efficiency,
                drag_coeff=scenario_config.battery.drag_coeff,
                frontal_area=scenario_config.battery.frontal_area,
                rolling_res_coeff=scenario_config.battery.rolling_res_coeff,
                regen_efficiency=scenario_config.battery.regen_efficiency,
            )
            battery_model = BatteryModel(amb_battery_config)

            dispatch_event = DispatchAmbulanceEvent(
                ambulance_id=amb_cfg.id,
                execution_time=amb_cfg.start_time,
                origin_node_id=amb_cfg.origin_node_id,
                destination_node_id=amb_cfg.destination_node_id,
                battery_model=battery_model,
                route=amb_cfg.route,
                speed_m_s=amb_cfg.speed_m_s,
                v2v_range_m=amb_cfg.v2v_range_m,
                v2i_range_m=amb_cfg.v2i_range_m,
                initial_soc=amb_cfg.initial_soc,
            )
            manager.scheduler.schedule(dispatch_event)

        return manager
