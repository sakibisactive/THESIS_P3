from src.communication.channel import CommunicationChannel
from src.core.network import ChargingStation, Network
from src.utils.config import InfrastructureFailureConfig, InfrastructureFailureType


class InfrastructureFailure:
    """Models a configurable, dynamic, and reversible infrastructure failure."""

    def __init__(self, config: InfrastructureFailureConfig) -> None:
        """Initializes the failure based on config parameters.

        Args:
            config: InfrastructureFailureConfig instance.
        """
        self.id = config.id
        self.failure_type = config.failure_type
        self.start_time = config.start_time
        self.duration = config.duration
        self.target_id = config.target_id
        self.blackout_area = config.blackout_area

        # Active state flag
        self.active = False

    def is_within_timeframe(self, current_time: float) -> bool:
        """Checks if the current simulation time lies within the failure lifespan.

        Args:
            current_time: The current simulation time in seconds.

        Returns:
            bool: True if it should be active, False otherwise.
        """
        return self.start_time <= current_time <= (self.start_time + self.duration)

    def apply(
        self,
        network: Network,
        channel: CommunicationChannel,
        charging_stations: dict[str, ChargingStation],
    ) -> None:
        """Applies the failure condition to the target simulation components.

        Args:
            network: The road network.
            channel: The V2X communication channel.
            charging_stations: Dict of charging stations.
        """
        if self.active:
            return

        if self.failure_type == InfrastructureFailureType.ROAD_FAILURE:
            edge = network.edges.get(self.target_id)
            if edge:
                edge.is_closed = True
                self.active = True

        elif self.failure_type == InfrastructureFailureType.CHARGING_STATION:
            station = charging_stations.get(self.target_id)
            if station:
                station.is_operational = False
                self.active = True

        elif self.failure_type == InfrastructureFailureType.COMMUNICATION:
            if (
                self.blackout_area
                and self.blackout_area not in channel.active_blackout_zones
            ):
                channel.active_blackout_zones.append(self.blackout_area)
                self.active = True

    def reverse(
        self,
        network: Network,
        channel: CommunicationChannel,
        charging_stations: dict[str, ChargingStation],
    ) -> None:
        """Reverses the failure condition, restoring components to normal operation.

        Args:
            network: The road network.
            channel: The V2X communication channel.
            charging_stations: Dict of charging stations.
        """
        if not self.active:
            return

        if self.failure_type == InfrastructureFailureType.ROAD_FAILURE:
            edge = network.edges.get(self.target_id)
            if edge:
                edge.is_closed = False
                self.active = False

        elif self.failure_type == InfrastructureFailureType.CHARGING_STATION:
            station = charging_stations.get(self.target_id)
            if station:
                station.is_operational = True
                self.active = False

        elif self.failure_type == InfrastructureFailureType.COMMUNICATION:
            if (
                self.blackout_area
                and self.blackout_area in channel.active_blackout_zones
            ):
                channel.active_blackout_zones.remove(self.blackout_area)
                self.active = False

    def update(
        self,
        current_time: float,
        network: Network,
        channel: CommunicationChannel,
        charging_stations: dict[str, ChargingStation],
    ) -> None:
        """Updates the failure state based on simulation time.

        Args:
            current_time: Current simulation timestamp.
            network: The road network.
            channel: The communication channel.
            charging_stations: Dict of charging stations.
        """
        if self.is_within_timeframe(current_time):
            self.apply(network, channel, charging_stations)
        else:
            self.reverse(network, channel, charging_stations)
