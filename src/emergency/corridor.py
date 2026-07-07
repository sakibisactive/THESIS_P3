from src.core.vehicle import Vehicle, VehicleState
from src.emergency.ambulance import Ambulance


class EmergencyCorridor:
    """Manages the yielding logic and state for standard vehicles
    on an ambulance route.
    """

    @staticmethod
    def update_yield_states(
        vehicles: dict[str, Vehicle],
        ambulances: dict[str, Ambulance],
        yield_speed_m_s: float = 2.0,
    ) -> None:
        """Evaluates routing overlaps, marking standard vehicles as yielding
        if they block an ambulance.

        Args:
            vehicles: Dictionary containing all simulation vehicle instances.
            ambulances: Dictionary containing active ambulance instances.
            yield_speed_m_s: Speed cap forced upon yielding standard vehicles.
        """
        # Reset all standard vehicles first
        for vehicle in vehicles.values():
            if not isinstance(vehicle, Ambulance):
                vehicle.reset_yield()

        for ambulance in ambulances.values():
            if not ambulance.current_route or ambulance.state != VehicleState.EN_ROUTE:
                continue

            amb_edge_idx = ambulance.current_edge_idx
            amb_edge_id = ambulance.current_route[amb_edge_idx]

            # Emergency corridor spans the current edge and the next 2 upcoming edges
            corridor_edges = set(
                ambulance.current_route[amb_edge_idx : amb_edge_idx + 3]
            )

            for vehicle in vehicles.values():
                if (
                    isinstance(vehicle, Ambulance)
                    or vehicle.state != VehicleState.EN_ROUTE
                ):
                    continue

                if not vehicle.current_route:
                    continue

                veh_edge_id = vehicle.current_route[vehicle.current_edge_idx]

                if veh_edge_id in corridor_edges:
                    # On the exact same edge, standard vehicle must be
                    # in front of the ambulance
                    if veh_edge_id == amb_edge_id:
                        if (
                            vehicle.distance_on_current_edge
                            >= ambulance.distance_on_current_edge
                        ):
                            vehicle.yield_for_emergency(yield_speed_m_s)
                    else:
                        # On upcoming edges, yield immediately
                        vehicle.yield_for_emergency(yield_speed_m_s)
