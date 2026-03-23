"""Taiwan and Japan economy models — energy depletion, electricity, morale, resupply."""

from wargame.constants import (
    GAS_CONSUMPTION_DAYS_PER_WEEK,
    COAL_CONSUMPTION_PER_WEEK,
    OIL_CONSUMPTION_PER_WEEK,
    GAS_FRACTION_OF_CARGO,
    COAL_FRACTION_OF_CARGO,
    OIL_FRACTION_OF_CARGO,
    ECONOMY_LAG_FACTOR,
    MORALE_DECAY_THRESHOLD,
    MORALE_DECAY_RATE,
    MORALE_SIEGE_FATIGUE,
    RATIONING_MODIFIER,
)


def update_taiwan_economy(state: dict, cargo_delivered: float, rationing: str = "none") -> None:
    """Update Taiwan's energy, electricity, economy, and morale for one week.

    Mutates *state* in-place.

    Args:
        state: Game state dict with taiwan_energy_*, taiwan_electricity_pct,
               taiwan_economy_pct, taiwan_morale keys.
        cargo_delivered: Normalised cargo units that arrived this week.
        rationing: One of "none", "moderate", "severe".  Reduces consumption.
    """
    rat_mod = RATIONING_MODIFIER[rationing]

    # --- 1. Fuel consumption & resupply ---
    # Consume first (can't burn fuel you don't have → clamp to 0),
    # then add resupply that arrives at end of week.

    # Gas (stored in *days*)
    state["taiwan_energy_gas"] = max(0.0, state["taiwan_energy_gas"] - GAS_CONSUMPTION_DAYS_PER_WEEK * rat_mod)
    state["taiwan_energy_gas"] += cargo_delivered * GAS_FRACTION_OF_CARGO

    # Coal (stored in *weeks*)
    state["taiwan_energy_coal"] = max(0.0, state["taiwan_energy_coal"] - COAL_CONSUMPTION_PER_WEEK * rat_mod)
    state["taiwan_energy_coal"] += cargo_delivered * COAL_FRACTION_OF_CARGO

    # Oil (stored in *weeks*)
    state["taiwan_energy_oil"] = max(0.0, state["taiwan_energy_oil"] - OIL_CONSUMPTION_PER_WEEK * rat_mod)
    state["taiwan_energy_oil"] += cargo_delivered * OIL_FRACTION_OF_CARGO

    # --- 2. Electricity ---
    gas_contrib = min(1.0, state["taiwan_energy_gas"] / 2.0) * 0.38
    coal_contrib = min(1.0, state["taiwan_energy_coal"] / 3.0) * 0.36
    oil_contrib = min(1.0, state["taiwan_energy_oil"] / 5.0) * 0.12
    renewable_contrib = 0.14
    electricity = (gas_contrib + coal_contrib + oil_contrib + renewable_contrib) * 100.0
    state["taiwan_electricity_pct"] = electricity

    # --- 3. Economy (tracks electricity with lag) ---
    economy = state["taiwan_economy_pct"]
    target = electricity * 0.9
    state["taiwan_economy_pct"] = economy + ECONOMY_LAG_FACTOR * (target - economy)

    # --- 4. Morale ---
    morale = state["taiwan_morale"]
    # Unconditional siege fatigue
    morale -= MORALE_SIEGE_FATIGUE
    # Extra decay when economy is below threshold
    econ = state["taiwan_economy_pct"]
    if econ < MORALE_DECAY_THRESHOLD:
        morale -= MORALE_DECAY_RATE * (MORALE_DECAY_THRESHOLD - econ) / MORALE_DECAY_THRESHOLD
    state["taiwan_morale"] = max(0.0, min(1.0, morale))


def update_japan_economy(state: dict, japan_actions: dict, cargo_via_japan_this_turn: float) -> None:
    """Update Japan-side economic state for one week.

    Mutates *state* in-place.

    Args:
        state: Game state dict with sea_lanes_disrupted_weeks,
               blockade_tightness, cargo_via_japan keys.
        japan_actions: Dict of Japan's policy choices this turn (currently
                       used for future extensions, e.g. port_capacity_share).
        cargo_via_japan_this_turn: Cargo routed through Japan this turn.
    """
    # Sea-lane disruption counter
    if state["blockade_tightness"] > 0.5:
        state["sea_lanes_disrupted_weeks"] += 1

    # Accumulate cargo routed via Japan
    state["cargo_via_japan"] += cargo_via_japan_this_turn
