from wargame.scenarios import EVALUATION_SCENARIOS, UI_PRESETS, build_initial_state


def test_build_initial_state_has_all_fields():
    state = build_initial_state(EVALUATION_SCENARIOS[0])
    required_fields = [
        "week", "china_surface_ships", "china_submarines", "china_aircraft",
        "china_missiles", "china_coast_guard", "china_morale",
        "us_surface_ships", "us_submarines", "us_aircraft", "us_missiles",
        "taiwan_surface_ships", "taiwan_aircraft", "taiwan_missiles",
        "taiwan_reserves", "taiwan_morale", "taiwan_energy_gas",
        "taiwan_energy_coal", "taiwan_energy_oil", "taiwan_electricity_pct",
        "taiwan_economy_pct",
        "japan_surface_ships", "japan_submarines", "japan_aircraft",
        "japan_base_okinawa", "japan_base_kyushu",
        "japan_okinawa_strikes", "japan_kyushu_strikes",
        "japan_mainland_strikes", "japan_homeland_strikes",
        "japan_ships_lost", "japan_subs_lost", "japan_aircraft_lost",
        "china_subs_neutralized_by_jmsdf", "china_ships_neutralized_by_jmsdf",
        "japan_blockade_reduction_share",
        "blockade_tightness", "escalation_level", "world_opinion",
        "merchant_ships_lost", "total_cargo_delivered", "cargo_via_japan",
        "civilian_casualties", "japan_civilian_casualties",
        "sea_lanes_disrupted_weeks",
        "peak_blockade_tightness", "escalation_decreased",
        "japan_avg_deploy", "japan_article9_violations",
        "japan_first_strike", "us_japan_missile_defense",
    ]
    for field in required_fields:
        assert field in state, f"Missing state field: {field}"


def test_scenario_energy_multiplier():
    degraded = [s for s in EVALUATION_SCENARIOS if s["name"] == "degraded"][0]
    state = build_initial_state(degraded)
    assert state["taiwan_energy_gas"] == 5.0
    assert state["taiwan_energy_coal"] == 3.5


def test_three_evaluation_scenarios():
    assert len(EVALUATION_SCENARIOS) == 3


def test_three_ui_presets():
    assert len(UI_PRESETS) == 3
