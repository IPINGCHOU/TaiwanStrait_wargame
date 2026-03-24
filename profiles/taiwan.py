"""Taiwan behavior profiles — deterministic strategy functions."""


def resilient(state: dict) -> dict:
    """Strict rationing early, high mobilization, active defense."""
    week = state["week"]
    taiwan_missiles = state.get("taiwan_missiles", 400)
    gas = state.get("taiwan_energy_gas", 10.0)
    coal = state.get("taiwan_energy_coal", 7.0)
    economy = state.get("taiwan_economy_pct", 100.0)

    # Aggressive early rationing
    if gas > 5 and coal > 4:
        rationing = "moderate"
    else:
        rationing = "severe"

    # Mobilize reserves progressively
    mobilization = min(0.5 + week * 0.02, 0.8)

    # Defensive missile use
    missile_budget = min(30, taiwan_missiles)
    if economy < 40:
        missile_budget = min(40, taiwan_missiles)  # fight harder when desperate

    # Convoys via Japan for safety
    convoy_size = 10 if week <= 10 else 8
    convoy_route = "japan_transship"

    return {
        "surface_deploy": 0.6,
        "rationing_level": rationing,
        "reserve_mobilization": mobilization,
        "coastal_defense_posture": "active",
        "missile_budget": missile_budget,
        "morale_policy": "propaganda",
        "convoy_size": convoy_size,
        "convoy_route": convoy_route,
    }


def defeatist(state: dict) -> dict:
    """Slow to ration, low mobilization, passive defense."""
    week = state["week"]
    taiwan_missiles = state.get("taiwan_missiles", 400)
    gas = state.get("taiwan_energy_gas", 10.0)

    # Late rationing — only when gas nearly gone
    rationing = "none" if gas > 2 else "moderate"

    # Smaller convoys, direct route (riskier but simpler)
    convoy_size = 5 if week <= 10 else 3

    return {
        "surface_deploy": 0.4,
        "rationing_level": rationing,
        "reserve_mobilization": 0.2,
        "coastal_defense_posture": "passive",
        "missile_budget": min(8, taiwan_missiles),
        "morale_policy": "normal",
        "convoy_size": convoy_size,
        "convoy_route": "direct",
    }
