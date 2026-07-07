import random
from abc import ABC, abstractmethod
from typing import Any


class SimulationEvent(ABC):
    """Abstract base class representing an emergency event scheduled
    in the simulation.
    """

    def __init__(
        self,
        event_id: str,
        execution_time: float,
        priority: int = 0,
        expiration_time: float | None = None,
    ) -> None:
        """Initializes a SimulationEvent.

        Args:
            event_id: Unique string identifier for the event.
            execution_time: Simulation timestamp when the event is triggered (seconds).
            priority: Event priority (higher values trigger first in case
                of timestamp ties).
            expiration_time: Optional timestamp after which the event is discarded.
        """
        self.id = event_id
        self.execution_time = execution_time
        self.priority = priority
        self.expiration_time = expiration_time
        self.cancelled = False

    @abstractmethod
    def execute(self, manager: Any, context: Any) -> None:
        """Executes the specific state modification on the simulation.

        Args:
            manager: The ScenarioManager instance coordinate.
            context: Context containing network, channel, vehicles, etc.
        """
        pass

    def cancel(self) -> None:
        """Flags the event as cancelled, preventing execution."""
        self.cancelled = True


class RecurringEvent(SimulationEvent):
    """Wraps an event to repeat periodically until an optional end timestamp."""

    def __init__(
        self,
        event_id: str,
        execution_time: float,
        period: float,
        inner_event: SimulationEvent,
        end_time: float | None = None,
    ) -> None:
        """Initializes a RecurringEvent.

        Args:
            event_id: Identifier.
            execution_time: Starting trigger time.
            period: Recurrence period in seconds.
            inner_event: The actual event command to run.
            end_time: Maximum timestamp to repeat until.
        """
        super().__init__(
            event_id=event_id,
            execution_time=execution_time,
            priority=inner_event.priority,
            expiration_time=inner_event.expiration_time,
        )
        self.period = period
        self.inner_event = inner_event
        self.end_time = end_time

    def execute(self, manager: Any, context: Any) -> None:
        if self.cancelled:
            return

        # Execute the underlying payload event
        self.inner_event.execute(manager, context)

        # Queue the next repetition
        next_time = self.execution_time + self.period
        if self.end_time is None or next_time <= self.end_time:
            next_event = RecurringEvent(
                event_id=self.id,
                execution_time=next_time,
                period=self.period,
                inner_event=self.inner_event,
                end_time=self.end_time,
            )
            manager.scheduler.schedule(next_event)


class RandomEvent(SimulationEvent):
    """An event scheduled dynamically inside a time window using a
    seeded random generator.
    """

    def __init__(
        self,
        event_id: str,
        earliest_time: float,
        latest_time: float,
        rng: random.Random,
        inner_event: SimulationEvent,
    ) -> None:
        """Initializes a RandomEvent.

        Args:
            event_id: Identifier.
            earliest_time: Start of random window.
            latest_time: End of random window.
            rng: Seeded Random instance.
            inner_event: Payload event to execute.
        """
        exec_time = rng.uniform(earliest_time, latest_time)
        super().__init__(
            event_id=event_id,
            execution_time=exec_time,
            priority=inner_event.priority,
            expiration_time=inner_event.expiration_time,
        )
        self.inner_event = inner_event

    def execute(self, manager: Any, context: Any) -> None:
        if self.cancelled:
            return
        self.inner_event.execute(manager, context)


class EventScheduler:
    """Manages scheduling, prioritization, cancellation, and execution
    of simulation events.
    """

    def __init__(self) -> None:
        self.events: list[SimulationEvent] = []

    def schedule(self, event: SimulationEvent) -> None:
        """Adds an event to the scheduler schedule queue.

        Args:
            event: SimulationEvent.
        """
        self.events.append(event)

    def cancel(self, event_id: str) -> None:
        """Cancels all active events with a matching event ID.

        Args:
            event_id: Unique string identifier.
        """
        for event in self.events:
            if event.id == event_id:
                event.cancel()

    def step(self, current_time: float, manager: Any, context: Any) -> None:
        """Executes all pending events whose schedule timestamps have been reached.

        Sorts by execution time and priority, checking expiration limits.

        Args:
            current_time: Current simulation timestamp.
            manager: ScenarioManager instance.
            context: Simulator Context object.
        """
        # Filter out expired events
        valid_events = []
        for event in self.events:
            if (
                event.expiration_time is not None
                and current_time > event.expiration_time
            ):
                # Expired event is discarded
                continue
            valid_events.append(event)
        self.events = valid_events

        # Identify events that should execute now
        to_execute = [e for e in self.events if e.execution_time <= current_time]

        # Sort: execution_time ascending, then priority descending, then event_id
        to_execute.sort(key=lambda e: (e.execution_time, -e.priority, e.id))

        # Execute and remove from schedule
        for event in to_execute:
            self.events.remove(event)
            if not event.cancelled:
                event.execute(manager, context)
