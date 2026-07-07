class E3SimulatorError(Exception):
    """Base exception for all errors in the E3-Hybrid Swarm Routing Simulator."""

    pass


class ConfigValidationError(E3SimulatorError):
    """Raised when there is an error validating or loading configuration files."""

    pass


class NetworkError(E3SimulatorError):
    """Raised when there is a topological or structural error in the road network."""

    pass


class BatteryDepletionError(E3SimulatorError):
    """Raised when a vehicle runs out of charge and becomes stranded."""

    pass


class CommunicationError(E3SimulatorError):
    """Raised when a vehicle fails to send or receive a required packet."""

    pass


class IncidentError(E3SimulatorError):
    """Raised when there is an error in managing or propagating emergency incidents."""

    pass
