from wargame.escalation import compute_escalation

def test_escalation_increases_with_high_deployment():
    state = {"escalation_level": 0, "civilian_casualties": 0}
    all_actions = {
        "china": {"surface_deploy": 1.0, "submarine_patrol": 1.0, "air_sortie_rate": 1.0, "missile_budget": 80, "target_priority": "military"},
        "us": {"surface_deploy": 1.0, "submarine_deploy": 1.0, "air_sortie_rate": 1.0, "missile_budget": 60},
        "japan": {"surface_deploy": 1.0, "submarine_deploy": 1.0, "air_sortie_rate": 1.0},
        "taiwan": {"reserve_mobilization": 1.0, "missile_budget": 40},
    }
    new_level = compute_escalation(state, all_actions, prev_civilians=0, combat_occurred=True)
    assert new_level == 1

def test_escalation_max_increase_one_per_turn():
    state = {"escalation_level": 1, "civilian_casualties": 5000}
    new_level = compute_escalation(state, _max_actions(), prev_civilians=0, combat_occurred=True)
    assert new_level == 2

def test_deescalation_possible_without_combat():
    state = {"escalation_level": 3, "civilian_casualties": 100}
    all_actions = {
        "china": {"surface_deploy": 0.0, "submarine_patrol": 0.0, "air_sortie_rate": 0.0, "missile_budget": 0, "target_priority": "convoys"},
        "us": {"surface_deploy": 0.0, "submarine_deploy": 0.0, "air_sortie_rate": 0.0, "missile_budget": 0},
        "japan": {"surface_deploy": 0.0, "submarine_deploy": 0.0, "air_sortie_rate": 0.0},
        "taiwan": {"reserve_mobilization": 0.0, "missile_budget": 0},
    }
    new_level = compute_escalation(state, all_actions, prev_civilians=100, combat_occurred=False)
    assert new_level == 2

def _max_actions():
    return {
        "china": {"surface_deploy": 1.0, "submarine_patrol": 1.0, "air_sortie_rate": 1.0, "missile_budget": 200, "target_priority": "infrastructure"},
        "us": {"surface_deploy": 1.0, "submarine_deploy": 1.0, "air_sortie_rate": 1.0, "missile_budget": 100},
        "japan": {"surface_deploy": 1.0, "submarine_deploy": 1.0, "air_sortie_rate": 1.0},
        "taiwan": {"reserve_mobilization": 1.0, "missile_budget": 100},
    }
