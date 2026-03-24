"""China behavior profiles — deterministic strategy functions."""


def aggressive(state: dict) -> dict:
    """High pressure, willing to escalate, heavy missile use."""
    week = state["week"]
    china_missiles = state.get("china_missiles", 1200)

    # Ramp up pressure over time
    base_deploy = min(0.8 + week * 0.01, 1.0)

    # Target infrastructure after week 8
    target = "military" if week <= 8 else "infrastructure"

    # Heavy missile use, scaling with escalation
    missile_base = 80 if week <= 5 else 100
    missile_budget = min(missile_base, china_missiles)

    return {
        "blockade_enforcement": 0.9,
        "submarine_patrol": base_deploy,
        "surface_deploy": base_deploy,
        "air_sortie_rate": min(0.7 + week * 0.02, 1.0),
        "missile_budget": missile_budget,
        "target_priority": target,
        "coast_guard_boarding": 0.8,
    }


def adaptive(state: dict) -> dict:
    """Reacts to game state — adjusts based on success/failure."""
    week = state["week"]
    china_missiles = state.get("china_missiles", 1200)
    china_surface = state.get("china_surface_ships", 60)
    taiwan_economy = state.get("taiwan_economy_pct", 100.0)
    cargo_delivered = state.get("total_cargo_delivered", 0.0)

    # Base posture
    enforcement = 0.6
    surface_deploy = 0.6
    sub_patrol = 0.7

    # If blockade is working (Taiwan economy dropping), maintain
    if taiwan_economy < 50:
        enforcement = 0.5  # ease off to preserve forces
        surface_deploy = 0.4

    # If losing ships fast, pull back surface and rely on subs
    initial_surface = 60
    if china_surface < initial_surface * 0.5:
        surface_deploy = 0.3
        sub_patrol = 0.9  # shift to submarine warfare

    # If convoys getting through, tighten
    if week > 3 and cargo_delivered / max(week, 1) > 5:
        enforcement = 0.8
        sub_patrol = 0.8

    missile_budget = min(40, china_missiles)
    target = "convoys" if taiwan_economy > 40 else "military"

    return {
        "blockade_enforcement": enforcement,
        "submarine_patrol": sub_patrol,
        "surface_deploy": surface_deploy,
        "air_sortie_rate": 0.5,
        "missile_budget": missile_budget,
        "target_priority": target,
        "coast_guard_boarding": 0.6,
    }


def cautious(state: dict) -> dict:
    """Low deployment, avoids escalation, preserves forces."""
    china_missiles = state.get("china_missiles", 1200)

    return {
        "blockade_enforcement": 0.5,
        "submarine_patrol": 0.4,
        "surface_deploy": 0.3,
        "air_sortie_rate": 0.3,
        "missile_budget": min(15, china_missiles),
        "target_priority": "convoys",
        "coast_guard_boarding": 0.7,
    }
