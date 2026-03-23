"""Scenario definitions and initial-state builder for the Taiwan Strait wargame."""

from wargame.constants import (
    BASE_BLOCKADE_LEVEL,
    CHINA_INITIAL,
    JAPAN_INITIAL,
    TAIWAN_INITIAL,
    US_INITIAL,
)

# ---------------------------------------------------------------------------
# Evaluation scenarios (spec section 10) — used by ShinkaEvolve fitness runs
# ---------------------------------------------------------------------------
EVALUATION_SCENARIOS = [
    {
        "name": "baseline",
        "china_profile": "adaptive",
        "us_profile": "interventionist",
        "taiwan_profile": "resilient",
        "china_surface_ships": 60,
        "china_submarines": 20,
        "china_aircraft": 400,
        "us_surface_ships": 24,
        "us_submarines": 12,
        "taiwan_energy_multiplier": 1.0,
    },
    {
        "name": "surge",
        "china_profile": "aggressive",
        "us_profile": "interventionist",
        "taiwan_profile": "resilient",
        "china_surface_ships": 90,
        "china_submarines": 30,
        "china_aircraft": 500,
        "us_surface_ships": 24,
        "us_submarines": 12,
        "taiwan_energy_multiplier": 1.0,
    },
    {
        "name": "degraded",
        "china_profile": "cautious",
        "us_profile": "restrained",
        "taiwan_profile": "defeatist",
        "china_surface_ships": 60,
        "china_submarines": 20,
        "china_aircraft": 400,
        "us_surface_ships": 16,
        "us_submarines": 8,
        "taiwan_energy_multiplier": 0.5,
    },
]

# ---------------------------------------------------------------------------
# Dashboard UI presets (spec section 11)
# ---------------------------------------------------------------------------
UI_PRESETS = [
    {
        "name": "Coalition Advantage",
        "china_profile": "cautious",
        "us_profile": "interventionist",
        "taiwan_profile": "resilient",
        "china_surface_ships": 45,
        "china_submarines": 15,
        "china_aircraft": 300,
        "china_missiles": 800,
        "china_coast_guard": 30,
        "us_surface_ships": 30,
        "us_submarines": 16,
        "us_aircraft": 250,
        "us_missiles": 1000,
        "taiwan_surface_ships": 30,
        "taiwan_aircraft": 180,
        "taiwan_missiles": 500,
        "taiwan_energy_multiplier": 1.5,
        "taiwan_morale": 0.9,
        "japan_surface_ships": 24,
        "japan_submarines": 8,
        "japan_aircraft": 120,
    },
    {
        "name": "Neutral",
        # Use defaults from constants (no overrides needed except profile names)
        "china_profile": "adaptive",
        "us_profile": "interventionist",
        "taiwan_profile": "resilient",
        "taiwan_energy_multiplier": 1.0,
    },
    {
        "name": "China Advantage",
        "china_profile": "aggressive",
        "us_profile": "restrained",
        "taiwan_profile": "defeatist",
        "china_surface_ships": 90,
        "china_submarines": 30,
        "china_aircraft": 500,
        "china_missiles": 1600,
        "china_coast_guard": 50,
        "us_surface_ships": 16,
        "us_submarines": 8,
        "us_aircraft": 120,
        "us_missiles": 500,
        "taiwan_surface_ships": 20,
        "taiwan_aircraft": 100,
        "taiwan_missiles": 250,
        "taiwan_energy_multiplier": 0.5,
        "taiwan_morale": 0.6,
        "japan_surface_ships": 16,
        "japan_submarines": 4,
        "japan_aircraft": 80,
    },
]


# ---------------------------------------------------------------------------
# Mapping from scenario key prefixes to the default-constant dicts
# ---------------------------------------------------------------------------
_PREFIX_DEFAULTS = {
    "china_": CHINA_INITIAL,
    "us_": US_INITIAL,
    "taiwan_": TAIWAN_INITIAL,
    "japan_": JAPAN_INITIAL,
}


def build_initial_state(scenario: dict) -> dict:
    """Build a complete game-state dict from a scenario definition.

    1. Populate force fields from the default constants (CHINA_INITIAL, etc.).
    2. Override any value explicitly set in *scenario*.
    3. Apply ``taiwan_energy_multiplier`` to gas / coal / oil reserves.
    4. Initialise all tracking / accumulator fields to zero / False.
    5. Store behaviour-profile names in the state.
    """

    # -- 1. Start with defaults from constants ---------------------------------
    state: dict = {
        # China
        "china_surface_ships": CHINA_INITIAL["surface_ships"],
        "china_submarines": CHINA_INITIAL["submarines"],
        "china_aircraft": CHINA_INITIAL["aircraft"],
        "china_missiles": CHINA_INITIAL["missiles"],
        "china_coast_guard": CHINA_INITIAL["coast_guard"],
        "china_morale": CHINA_INITIAL["morale"],
        # US
        "us_surface_ships": US_INITIAL["surface_ships"],
        "us_submarines": US_INITIAL["submarines"],
        "us_aircraft": US_INITIAL["aircraft"],
        "us_missiles": US_INITIAL["missiles"],
        # Taiwan
        "taiwan_surface_ships": TAIWAN_INITIAL["surface_ships"],
        "taiwan_aircraft": TAIWAN_INITIAL["aircraft"],
        "taiwan_missiles": TAIWAN_INITIAL["missiles"],
        "taiwan_reserves": TAIWAN_INITIAL["reserves"],
        "taiwan_morale": TAIWAN_INITIAL["morale"],
        "taiwan_energy_gas": TAIWAN_INITIAL["energy_gas"],
        "taiwan_energy_coal": TAIWAN_INITIAL["energy_coal"],
        "taiwan_energy_oil": TAIWAN_INITIAL["energy_oil"],
        "taiwan_electricity_pct": TAIWAN_INITIAL["electricity_pct"],
        "taiwan_economy_pct": TAIWAN_INITIAL["economy_pct"],
        # Japan
        "japan_surface_ships": JAPAN_INITIAL["surface_ships"],
        "japan_submarines": JAPAN_INITIAL["submarines"],
        "japan_aircraft": JAPAN_INITIAL["aircraft"],
        "japan_base_okinawa": JAPAN_INITIAL["base_okinawa"],
        "japan_base_kyushu": JAPAN_INITIAL["base_kyushu"],
    }

    # -- 2. Override with scenario-specific values -----------------------------
    for key, value in scenario.items():
        if key in ("name", "china_profile", "us_profile", "taiwan_profile",
                    "taiwan_energy_multiplier"):
            continue  # handled separately
        if key in state:
            state[key] = value

    # -- 3. Apply energy multiplier --------------------------------------------
    multiplier = scenario.get("taiwan_energy_multiplier", 1.0)
    state["taiwan_energy_gas"] *= multiplier
    state["taiwan_energy_coal"] *= multiplier
    state["taiwan_energy_oil"] *= multiplier

    # -- 4. Tracking / accumulator fields (all start at zero / False) ----------
    state["week"] = 1
    state["blockade_tightness"] = BASE_BLOCKADE_LEVEL
    state["escalation_level"] = 1  # starts at gray zone

    # Japan strike counters
    state["japan_okinawa_strikes"] = 0
    state["japan_kyushu_strikes"] = 0
    state["japan_mainland_strikes"] = 0
    state["japan_homeland_strikes"] = 0

    # Japan loss counters
    state["japan_ships_lost"] = 0
    state["japan_subs_lost"] = 0
    state["japan_aircraft_lost"] = 0

    # Kill attribution
    state["china_subs_neutralized_by_jmsdf"] = 0
    state["china_ships_neutralized_by_jmsdf"] = 0
    state["japan_blockade_reduction_share"] = 0

    # Global accumulators
    state["world_opinion"] = 0.0
    state["merchant_ships_lost"] = 0
    state["total_cargo_delivered"] = 0
    state["cargo_via_japan"] = 0
    state["civilian_casualties"] = 0
    state["japan_civilian_casualties"] = 0
    state["sea_lanes_disrupted_weeks"] = 0

    # End-of-game summary helpers
    state["peak_blockade_tightness"] = BASE_BLOCKADE_LEVEL
    state["escalation_decreased"] = False
    state["japan_avg_deploy"] = 0.0
    state["japan_article9_violations"] = 0
    state["japan_first_strike"] = False
    state["us_japan_missile_defense"] = False

    # -- 5. Behaviour profiles -------------------------------------------------
    state["china_profile"] = scenario.get("china_profile", "adaptive")
    state["us_profile"] = scenario.get("us_profile", "interventionist")
    state["taiwan_profile"] = scenario.get("taiwan_profile", "resilient")

    return state
