"""Exception definitions for the routing package."""


class RoutingError(Exception):
    """Base exception class for all routing-related errors."""

    pass


class NoPathFoundError(RoutingError):
    """Raised when no valid path exists between origin and destination nodes."""

    pass


class InvalidNodeError(RoutingError):
    """Raised when the specified origin or destination node ID does not exist."""

    pass
