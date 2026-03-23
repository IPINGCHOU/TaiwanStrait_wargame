from wargame.economy import update_taiwan_economy, update_japan_economy


def test_gas_depletes_without_resupply():
    state = {"taiwan_energy_gas": 10.0, "taiwan_energy_coal": 7.0,
             "taiwan_energy_oil": 20.0, "taiwan_electricity_pct": 100.0,
             "taiwan_economy_pct": 100.0, "taiwan_morale": 0.8}
    update_taiwan_economy(state, cargo_delivered=0.0)
    assert state["taiwan_energy_gas"] == 3.0  # 10 - 7 days consumed
    update_taiwan_economy(state, cargo_delivered=0.0)
    assert state["taiwan_energy_gas"] == 0.0


def test_electricity_drops_with_fuel_depletion():
    state = {"taiwan_energy_gas": 0.0, "taiwan_energy_coal": 0.0,
             "taiwan_energy_oil": 0.0, "taiwan_electricity_pct": 100.0,
             "taiwan_economy_pct": 100.0, "taiwan_morale": 0.8}
    update_taiwan_economy(state, cargo_delivered=0.0)
    assert state["taiwan_electricity_pct"] < 20.0  # only renewables (14%)


def test_morale_decays_below_threshold():
    state = {"taiwan_energy_gas": 0.0, "taiwan_energy_coal": 0.0,
             "taiwan_energy_oil": 0.0, "taiwan_electricity_pct": 14.0,
             "taiwan_economy_pct": 30.0, "taiwan_morale": 0.8}
    update_taiwan_economy(state, cargo_delivered=0.0)
    assert state["taiwan_morale"] < 0.8


def test_cargo_resupply_replenishes_fuel():
    state = {"taiwan_energy_gas": 3.0, "taiwan_energy_coal": 3.0,
             "taiwan_energy_oil": 15.0, "taiwan_electricity_pct": 50.0,
             "taiwan_economy_pct": 50.0, "taiwan_morale": 0.7}
    update_taiwan_economy(state, cargo_delivered=5.0)
    assert state["taiwan_energy_gas"] > 0
    assert state["taiwan_energy_coal"] > 2.0


def test_rationing_slows_depletion():
    state_no = {"taiwan_energy_gas": 10.0, "taiwan_energy_coal": 7.0,
                "taiwan_energy_oil": 20.0, "taiwan_electricity_pct": 100.0,
                "taiwan_economy_pct": 100.0, "taiwan_morale": 0.8}
    state_severe = dict(state_no)
    update_taiwan_economy(state_no, cargo_delivered=0.0, rationing="none")
    update_taiwan_economy(state_severe, cargo_delivered=0.0, rationing="severe")
    assert state_severe["taiwan_energy_gas"] > state_no["taiwan_energy_gas"]


def test_japan_sea_lane_disruption():
    state = {"sea_lanes_disrupted_weeks": 0, "blockade_tightness": 0.8, "cargo_via_japan": 0.0}
    japan_actions = {"port_capacity_share": 0.5, "transshipment_allow": True}
    update_japan_economy(state, japan_actions, cargo_via_japan_this_turn=3.0)
    assert state["sea_lanes_disrupted_weeks"] == 1
