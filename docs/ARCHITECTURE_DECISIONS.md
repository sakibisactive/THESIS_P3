# Architecture Decision Records (ADR) - E³-Hybrid Routing Simulator

This document logs the major engineering and design decisions guiding the simulator's development.

---

## AD-001: Decoupled Emergency System Architecture

*   **Context**: The emergency system must model realistic urban emergencies (incidents, ambulance corridors, and infrastructure outages) without coupling directly to SUMO, TraCI, or specific routing algorithms.
*   **Decision**: Design the emergency system as an independent, simulator-agnostic publisher of information. Edge limits, closures, and vehicle yielding states are modified on the core python domain models via clean public interfaces (`Edge.is_closed`, `Vehicle.yield_for_emergency`). Routing algorithms and adapters will consume this state through network queries.
*   **Rationale**: Ensures the simulator remains clean, unit-testable, and swappable between the pure Python simulator and the SUMO coupling layer.
*   **Consequences**: The emergency system does not directly modify routes; it only creates information (e.g. broadcasting beacons, closing edges) that vehicles must query and act upon.

---

## AD-002: Polymorphic Event Scheduler

*   **Context**: The simulation requires complex, scheduled, recurring, and randomized events. Implementing these through chains of conditional `if/else` statements is fragile and hard to extend.
*   **Decision**: Implement a priority-sorted, polymorphic event scheduler. Define a `SimulationEvent` abstract base class with an `execute(manager, context)` hook. Specific event behaviors (e.g., spawning incidents, closures, ambulance dispatches) are encapsulated in dedicated subclasses. Wrappers like `RecurringEvent` and `RandomEvent` manage temporal repetitions and window-based randomized executions.
*   **Rationale**: Satisfies the constraint against branching conditional logic chains, simplifies adding new event types, and enables modular, testable event triggers.
*   **Consequences**: All dynamic scenario events are fully represented as objects, facilitating deterministic execution ordering based on timestamps and priorities.

---

## AD-003: Ambulance as a Core Vehicle Subclass

*   **Context**: Ambulances need to move through the network, consume battery energy, use V2X transceivers to broadcast coordinates, and force other vehicles to yield.
*   **Decision**: Define `Ambulance` as a subclass of `Vehicle`. It overrides `step_movement` to bypass edge congestion (using the free-flow edge speed limit or its target cruising limit) and implements a periodic transceiver beacon broadcast. It maps its dynamic coordinate provider using a lambda callback referencing the underlying network interpolation method.
*   **Rationale**: Bypasses code duplication by inheriting vehicle movement physics, battery drainage, and route-tracking, while allowing custom speed override limits and communication beacon protocols.
*   **Consequences**: Ambulances are treated as normal vehicles by network monitoring but can be specifically queried for lane-clearing yielding calculations.

---

## AD-004: Dynamic, Reversible Infrastructure Failures

*   **Context**: Progressive urban disasters can cause temporary outages in charging stations, communication grids, and road segments, which must be reversible.
*   **Decision**: Implement `InfrastructureFailure` and `RoadClosure` as objects with `apply(network, channel, stations)` and `reverse(...)` hooks. State mutations (such as setting `Edge.is_closed = True`, `ChargingStation.is_operational = False`, or adding area coordinates to `CommunicationChannel.active_blackout_zones`) are modified temporarily and restored to default values when the failure duration expires.
*   **Rationale**: Keeps network and channel classes decoupled from scenario timelines, ensuring state mutations are managed cleanly by the scenario clock.
*   **Consequences**: The system can dynamically recover from failures, modeling dynamic disaster recovery protocols accurately.

---

## AD-005: Johnson's Potential Reweighting for EV Energy Routing

*   **Context**: EV energy consumption modeling includes regenerative braking, which yields negative cost weights. Negative cost weights violate the non-negativity constraints of Dijkstra and A*, leading to infinite negative-cost loops or loss of path optimality guarantees.
*   **Decision**: Apply **Johnson's potential reweighting technique** to transform edge energy costs to non-negative values. We compute a potential $h(u) = (m \cdot g \cdot \text{elevation}(u)) / 3.6\times 10^6$ in kWh for each node $u$ using the network's cumulative edge gradients. The reweighted edge cost $E'(u, v) = E(u, v) + h(u) - h(v)$ is mathematically guaranteed to be non-negative and preserve optimal path selection.
*   **Rationale**: Avoids the sub-optimality of arbitrary clamping and ensures Dijkstra and A* can solve energy-optimal paths correctly.
*   **Consequences**: All optimal routes found are mathematically equivalent to the optimal routes in the original negative-weight graph, with strictly positive edge costs during graph search.

---

## AD-006: Strategy-based Pluggable Cost and Heuristic Interfaces

*   **Context**: Different routing algorithms (and future swarm routing variants) must support multiple optimization goals (distance, time, energy) and different A* heuristics.
*   **Decision**: Implement pluggable strategies for edge cost evaluation and A* heuristics. Edge cost functions are callables matching `EdgeCostFunction = Callable[[Edge, Vehicle | None, Network, Any], float]`. Heuristics are represented as strategy classes (`ZeroHeuristic`, `EuclideanHeuristic`, `ManhattanHeuristic`).
*   **Rationale**: Decouples search logic from specific metrics, allowing the router implementation (e.g. Dijkstra, A*, or future ACO/BCO/PSO) to remain clean and unmodified.
*   **Consequences**: Adding new optimization criteria or custom heuristics requires zero changes to the underlying router implementations.

---

## AD-007: Edge-Specific Cache Invalidation

*   **Context**: Routing is computationally expensive. Caching routing paths speeds up simulation. However, when incidents, road closures, or failures occur, cache entries must be invalidated to prevent vehicles from using stale, blocked paths.
*   **Decision**: Implement a route cache (`RouteCache`) that tracks the specific edges traversed by each cached path. When a network update (road closure, speed reduction) occurs, the cache selectively invalidates only the paths containing the affected edge IDs.
*   **Rationale**: Avoids clearing the entire cache when only one edge changes, maximizing cache hits while guaranteeing that stale paths are never returned.
*   **Consequences**: High-performance, dynamically correct path caching during simulation runs.

---

## AD-008: ACS Variant Selected for ACO Routing

*   **Context**: Multiple Ant Colony Optimization variants exist (AS, ACS, MMAS, ACS-TSP). The thesis requires a routing algorithm suitable for dynamic, directed graphs with EV-aware multi-objective costs.
*   **Decision**: Implement the **Ant Colony System (ACS)** variant (Dorigo & Gambardella, 1997, IEEE Transactions on Evolutionary Computation, 1(1), 53–66). ACS is selected over the simpler Ant System (AS) for three specific advantages:
    1.  **Pseudo-random proportional rule**: The exploitation threshold `q0` allows direct control of the exploration/exploitation trade-off, which is important in a dynamic environment where both rapid adaptation (exploration) and route stability (exploitation) are desirable.
    2.  **Local pheromone update**: Immediately reduces pheromone on traversed edges within an iteration, discouraging all ants from converging on the same path and maintaining solution diversity.
    3.  **Global pheromone update restricted to best path**: Only the best-found ant reinforces its path at the end of each iteration, accelerating convergence versus the AS approach where all ants deposit pheromones.
*   **Deviations from the original paper**:
    1.  The original targets the static Traveling Salesman Problem; this implementation targets dynamic directed routing graphs.
    2.  Pheromones persist across multiple routing queries, representing accumulated learned knowledge rather than resetting per query.
    3.  Global evaporation is applied lazily, triggered by simulation time advancement rather than by ACS iteration count.
    4.  Pheromone bounds `[tau_min, tau_max]` are borrowed from MMAS (Stützle & Hoos, 2000) to prevent premature stagnation.
*   **Rationale**: Scientific correctness requires minimal deviation from the published algorithm. All deviations are explicitly documented and are direct necessities of the dynamic simulation context.
*   **Consequences**: The ACS implementation is directly citable in thesis experiments, and deviations are documented for reproducibility.

---

## AD-009: Multi-Objective Edge Scorer Separated from ACO Core

*   **Context**: ACO traditionally uses a single-objective heuristic (1/distance). The thesis requires EV-aware routing combining travel time, distance, energy, congestion, and emergency proximity.
*   **Decision**: Implement a dedicated `MultiObjectiveEdgeScorer` class (`src/routing/scorer.py`) that computes a composite weighted score from five normalised objective components. The scorer is injected into the `ACORouter` at construction time and can be shared with future BCO, PSO, and E3-Hybrid algorithm implementations.
*   **Rationale**: Separation of responsibilities. The ACO algorithm is not responsible for deciding what constitutes "desirable" edges; it only consumes the heuristic value `eta(e) = 1/score(e)`. This allows the scoring weights to be changed or extended without modifying the ACO algorithm.
*   **Consequences**: BCO, PSO, and E3-Hybrid can reuse `MultiObjectiveEdgeScorer` without modification, ensuring consistent edge evaluation across all algorithm comparisons.

---

## AD-010: Persistent Pheromones Across Routing Queries

*   **Context**: In a static TSP, pheromone matrices are typically reset between problem instances. In a continuous simulation, each routing query is not independent; the network conditions evolve over time and the algorithm should learn from past routing decisions.
*   **Decision**: The `ACORouter` maintains a persistent pheromone matrix across all calls to `find_route()`. The matrix is never reset unless `reset()` is explicitly called (e.g., when starting a new independent experiment). Road closures and emergency events decay pheromone naturally through evaporation rather than forcing reinitialization.
*   **Rationale**: Persistent learning allows the algorithm to capitalize on prior routing knowledge and adapt smoothly to network changes. A complete reset would discard valuable information and cause erratic route instability after dynamic events.
*   **Consequences**: The `reset()` method provides an explicit, controlled mechanism for independent experiment boundaries. Lazy temporal evaporation ensures pheromones on obsolete paths decay at realistic simulation rates.

