"""US behavior profiles — deterministic strategy functions."""


def interventionist(state: dict) -> dict:
    """Heavy deployment, aggressive, provides Japan missile defense."""
    us_missiles = state.get("us_missiles", 800)
    taiwan_economy = state.get("taiwan_economy_pct", 100.0)
    escalation = state.get("escalation_level", 0)

    # Increase commitment if Taiwan struggling
    sub_deploy = 0.7 if taiwan_economy > 50 else 0.9
    surface_deploy = 0.5 if taiwan_economy > 50 else 0.7

    # More aggressive at higher escalation
    posture = "balanced" if escalation < 3 else "aggressive"
    missile_base = 50 if escalation < 3 else 80
    missile_budget = min(missile_base, us_missiles)

    return {
        "submarine_deploy": sub_deploy,
        "surface_deploy": surface_deploy,
        "air_sortie_rate": 0.6,
        "missile_budget": missile_budget,
        "engagement_posture": posture,
        "convoy_escort_commit": 0.3,
        "japan_missile_defense": True,
    }


def restrained(state: dict) -> dict:
    """Minimal deployment, defensive, prioritizes convoy escort."""
    us_missiles = state.get("us_missiles", 800)
    escalation = state.get("escalation_level", 0)

    # Only provide missile defense at high escalation
    missile_defense = escalation >= 3

    return {
        "submarine_deploy": 0.4,
        "surface_deploy": 0.3,
        "air_sortie_rate": 0.2,
        "missile_budget": min(15, us_missiles),
        "engagement_posture": "defensive",
        "convoy_escort_commit": 0.5,  # prioritize escort over combat
        "japan_missile_defense": missile_defense,
    }
