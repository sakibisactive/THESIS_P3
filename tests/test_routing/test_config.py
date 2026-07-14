from src.utils.config import RoutingObjectivesConfig

def test_routing_objectives_legacy_mapping() -> None:
    # 1. Test legacy scenario key mappings
    legacy_data = {
        "weight_travel_time": 0.7,
        "weight_energy_consumption": 0.2,
        "weight_safety": 0.1
    }
    config = RoutingObjectivesConfig.model_validate(legacy_data)
    assert config.w_time == 0.7
    assert config.w_energy == 0.2
    assert config.w_emergency == 0.1
    assert config.w_distance == 0.0
    assert config.w_congestion == 0.0

def test_routing_objectives_internal_mapping() -> None:
    # 2. Test internal key mappings
    internal_data = {
        "w_time": 0.7,
        "w_energy": 0.2,
        "w_emergency": 0.1,
        "w_distance": 0.0,
        "w_congestion": 0.0
    }
    config = RoutingObjectivesConfig.model_validate(internal_data)
    assert config.w_time == 0.7
    assert config.w_energy == 0.2
    assert config.w_emergency == 0.1
    assert config.w_distance == 0.0
    assert config.w_congestion == 0.0

def test_routing_objectives_mixed_mapping() -> None:
    # 3. Test mixed mappings to verify preference or combination
    mixed_data = {
        "weight_travel_time": 0.6,
        "w_energy": 0.3,
        "w_emergency": 0.1
    }
    config = RoutingObjectivesConfig.model_validate(mixed_data)
    assert config.w_time == 0.6
    assert config.w_energy == 0.3
    assert config.w_emergency == 0.1
    assert config.w_distance == 0.0
    assert config.w_congestion == 0.0
