# Module Dependency Graph

The following Mermaid diagram visualizes the dependency structure across the simulator's modules.

```mermaid
graph TD
    subgraph src [src]
        src[src]
    end
    subgraph src_utils [src.utils]
        src_utils_config[config]
        src_utils_exceptions[exceptions]
        src_utils_logger[logger]
        src_utils[utils]
    subgraph src_evaluation [src.evaluation]
        src_evaluation_scenario_executor[scenario_executor]
        src_evaluation_experiment_runner[experiment_runner]
        src_evaluation_statistics[statistics]
        src_evaluation_result_exporter[result_exporter]
        src_evaluation_metrics_collector[metrics_collector]
        src_evaluation_plot_generator[plot_generator]
        src_evaluation_benchmark_suite[benchmark_suite]
    subgraph src_routing [src.routing]
        src_routing_routing_result[routing_result]
        src_routing_heuristic[heuristic]
        src_routing_benchmark[benchmark]
        src_routing_scorer[scorer]
        src_routing_astar[astar]
        src_routing_pso[pso]
        src_routing_e3_hybrid[e3_hybrid]
        src_routing_bco[bco]
        src_routing_routing_metrics[routing_metrics]
        src_routing_routing_context[routing_context]
        src_routing_cache[cache]
        src_routing_exceptions[exceptions]
        src_routing_dijkstra[dijkstra]
        src_routing_base_swarm[base_swarm]
        src_routing_router[router]
        src_routing_graph_utils[graph_utils]
        src_routing_aco[aco]
        src_routing[routing]
    subgraph src_emergency [src.emergency]
        src_emergency_incident[incident]
        src_emergency_scenario_loader[scenario_loader]
        src_emergency_scenario_manager[scenario_manager]
        src_emergency_ambulance[ambulance]
        src_emergency_corridor[corridor]
        src_emergency_scheduler[scheduler]
        src_emergency_failure[failure]
        src_emergency[emergency]
    subgraph src_core [src.core]
        src_core_vehicle[vehicle]
        src_core_battery[battery]
        src_core_network[network]
        src_core[core]
    subgraph src_communication [src.communication]
        src_communication_channel[channel]
        src_communication_transceiver[transceiver]
        src_communication_packet[packet]
        src_communication[communication]
    subgraph src_sumo_adapter [src.sumo_adapter]
        src_sumo_adapter_adapter[adapter]
        src_sumo_adapter[sumo_adapter]
    src_utils_config --> src_utils_exceptions
    src_evaluation_scenario_executor --> src_communication_channel
    src_evaluation_scenario_executor --> src_communication_packet
    src_evaluation_scenario_executor --> src_communication_transceiver
    src_evaluation_scenario_executor --> src_core_battery
    src_evaluation_scenario_executor --> src_core_network
    src_evaluation_scenario_executor --> src_core_vehicle
    src_evaluation_scenario_executor --> src_emergency_scenario_loader
    src_evaluation_scenario_executor --> src_evaluation_metrics_collector
    src_evaluation_scenario_executor --> src_routing_router
    src_evaluation_scenario_executor --> src_routing_routing_context
    src_evaluation_scenario_executor --> src_utils_config
    src_evaluation_experiment_runner --> src_evaluation_metrics_collector
    src_evaluation_experiment_runner --> src_evaluation_scenario_executor
    src_evaluation_experiment_runner --> src_routing_router
    src_evaluation_experiment_runner --> src_utils_config
    src_evaluation_result_exporter --> src_evaluation_metrics_collector
    src_evaluation_benchmark_suite --> src_evaluation_experiment_runner
    src_evaluation_benchmark_suite --> src_evaluation_metrics_collector
    src_evaluation_benchmark_suite --> src_routing_router
    src_evaluation_benchmark_suite --> src_utils_config
    src_routing_heuristic --> src_core_network
    src_routing_benchmark --> src_routing_router
    src_routing_benchmark --> src_routing_routing_context
    src_routing_benchmark --> src_routing_routing_metrics
    src_routing_scorer --> src_core_network
    src_routing_scorer --> src_core_vehicle
    src_routing_scorer --> src_utils_config
    src_routing_astar --> src_routing_exceptions
    src_routing_astar --> src_routing_graph_utils
    src_routing_astar --> src_routing_heuristic
    src_routing_astar --> src_routing_router
    src_routing_astar --> src_routing_routing_context
    src_routing_astar --> src_routing_routing_result
    src_routing_pso --> src_routing_base_swarm
    src_routing_pso --> src_routing_exceptions
    src_routing_pso --> src_routing_router
    src_routing_pso --> src_routing_routing_context
    src_routing_pso --> src_routing_routing_result
    src_routing_pso --> src_routing_scorer
    src_routing_pso --> src_utils_config
    src_routing_e3_hybrid --> src_routing_aco
    src_routing_e3_hybrid --> src_routing_base_swarm
    src_routing_e3_hybrid --> src_routing_bco
    src_routing_e3_hybrid --> src_routing_exceptions
    src_routing_e3_hybrid --> src_routing_pso
    src_routing_e3_hybrid --> src_routing_router
    src_routing_e3_hybrid --> src_routing_routing_context
    src_routing_e3_hybrid --> src_routing_routing_result
    src_routing_e3_hybrid --> src_routing_scorer
    src_routing_e3_hybrid --> src_utils_config
    src_routing_bco --> src_routing_base_swarm
    src_routing_bco --> src_routing_exceptions
    src_routing_bco --> src_routing_router
    src_routing_bco --> src_routing_routing_context
    src_routing_bco --> src_routing_routing_result
    src_routing_bco --> src_routing_scorer
    src_routing_bco --> src_utils_config
    src_routing_routing_metrics --> src_core_network
    src_routing_routing_metrics --> src_core_vehicle
    src_routing_routing_context --> src_core_network
    src_routing_routing_context --> src_core_vehicle
    src_routing_cache --> src_routing_router
    src_routing_cache --> src_routing_routing_context
    src_routing_cache --> src_routing_routing_result
    src_routing_dijkstra --> src_routing_exceptions
    src_routing_dijkstra --> src_routing_graph_utils
    src_routing_dijkstra --> src_routing_router
    src_routing_dijkstra --> src_routing_routing_context
    src_routing_dijkstra --> src_routing_routing_result
    src_routing_base_swarm --> src_routing_routing_context
    src_routing_router --> src_routing_routing_context
    src_routing_router --> src_routing_routing_result
    src_routing_aco --> src_routing_base_swarm
    src_routing_aco --> src_routing_exceptions
    src_routing_aco --> src_routing_graph_utils
    src_routing_aco --> src_routing_router
    src_routing_aco --> src_routing_routing_context
    src_routing_aco --> src_routing_routing_result
    src_routing_aco --> src_routing_scorer
    src_routing_aco --> src_utils_config
    src_routing --> src_routing_aco
    src_routing --> src_routing_astar
    src_routing --> src_routing_bco
    src_routing --> src_routing_benchmark
    src_routing --> src_routing_cache
    src_routing --> src_routing_dijkstra
    src_routing --> src_routing_e3_hybrid
    src_routing --> src_routing_exceptions
    src_routing --> src_routing_graph_utils
    src_routing --> src_routing_heuristic
    src_routing --> src_routing_pso
    src_routing --> src_routing_router
    src_routing --> src_routing_routing_context
    src_routing --> src_routing_routing_metrics
    src_routing --> src_routing_routing_result
    src_routing --> src_routing_scorer
    src_emergency_incident --> src_core_network
    src_emergency_incident --> src_utils_config
    src_emergency_scenario_loader --> src_core_battery
    src_emergency_scenario_loader --> src_emergency_failure
    src_emergency_scenario_loader --> src_emergency_incident
    src_emergency_scenario_loader --> src_emergency_scenario_manager
    src_emergency_scenario_loader --> src_utils_config
    src_emergency_scenario_manager --> src_communication_channel
    src_emergency_scenario_manager --> src_core_battery
    src_emergency_scenario_manager --> src_core_network
    src_emergency_scenario_manager --> src_core_vehicle
    src_emergency_scenario_manager --> src_emergency_ambulance
    src_emergency_scenario_manager --> src_emergency_corridor
    src_emergency_scenario_manager --> src_emergency_failure
    src_emergency_scenario_manager --> src_emergency_incident
    src_emergency_scenario_manager --> src_emergency_scheduler
    src_emergency_ambulance --> src_communication_channel
    src_emergency_ambulance --> src_communication_packet
    src_emergency_ambulance --> src_communication_transceiver
    src_emergency_ambulance --> src_core_battery
    src_emergency_ambulance --> src_core_network
    src_emergency_ambulance --> src_core_vehicle
    src_emergency_corridor --> src_core_vehicle
    src_emergency_corridor --> src_emergency_ambulance
    src_emergency_failure --> src_communication_channel
    src_emergency_failure --> src_core_network
    src_emergency_failure --> src_utils_config
    src_emergency --> src_emergency_ambulance
    src_emergency --> src_emergency_corridor
    src_emergency --> src_emergency_failure
    src_emergency --> src_emergency_incident
    src_emergency --> src_emergency_scenario_loader
    src_emergency --> src_emergency_scenario_manager
    src_emergency --> src_emergency_scheduler
    src_core_vehicle --> src_core_battery
    src_core_vehicle --> src_core_network
    src_core_battery --> src_utils_config
    src_core_network --> src_utils_exceptions
    src_communication_channel --> src_communication_packet
    src_communication_channel --> src_communication_transceiver
    src_communication_channel --> src_utils_config
    src_communication_transceiver --> src_communication_channel
    src_communication_transceiver --> src_communication_packet
    src_communication --> src_communication_channel
    src_communication --> src_communication_packet
    src_communication --> src_communication_transceiver
    src_sumo_adapter_adapter --> src_core_battery
    src_sumo_adapter_adapter --> src_core_network
    src_sumo_adapter_adapter --> src_core_vehicle
    src_sumo_adapter_adapter --> src_utils_config
    src_sumo_adapter --> src_sumo_adapter_adapter
```
