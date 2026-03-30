"""Emergent escalation model — computes escalation level and world opinion."""

from __future__ import annotations

from wargame.constants import (
    ESCALATION_DEPLOY_WEIGHT,
    ESCALATION_MISSILE_WEIGHT,
    ESCALATION_PORT_STRIKE_SCORE,
    ESCALATION_AIRBASE_STRIKE_SCORE,
    MAX_ESCALATION_CHANGE_PER_TURN,
)

# ---------------------------------------------------------------------------
# Deployment keys for each country (floats in [0, 1])
# ---------------------------------------------------------------------------
_DEPLOY_KEYS: dict[str, list[str]] = {
    "china": ["surface_deploy", "submarine_patrol", "air_sortie_rate"],
    "us": ["surface_deploy", "submarine_deploy", "air_sortie_rate"],
    "japan": ["surface_deploy", "submarine_deploy", "air_sortie_rate"],
    "taiwan": ["reserve_mobilization"],
}


def _sum_deployments(all_actions: dict) -> float:
    """Sum all deployment floats across every country."""
    total = 0.0
    for country, keys in _DEPLOY_KEYS.items():
        actions = all_actions.get(country, {})
        for k in keys:
            total += float(actions.get(k, 0.0))
    return total


def _sum_missiles(all_actions: dict) -> float:
    """Sum missile_budget values across all countries."""
    total = 0.0
    for actions in all_actions.values():
        total += float(actions.get("missile_budget", 0.0))
    return total


def compute_escalation(
    state: dict,
    all_actions: dict,
    combat_occurred: bool,
    *,
    airbase_strike: bool = False,
) -> int:
    """Return new escalation level (int 0-4).

    Parameters
    ----------
    state : dict
        Must contain ``escalation_level`` (int).
    all_actions : dict
        Keyed by country name; each value is a dict of action parameters.
    combat_occurred : bool
        Whether any combat resolution happened this turn.
    airbase_strike : bool, optional
        Whether strikes on airbases occurred this turn (default ``False``).
    """
    current: int = state["escalation_level"]

    # --- intensity score ---------------------------------------------------
    score = 0.0

    # deployment intensity
    total_deploy = _sum_deployments(all_actions)
    score += (total_deploy / 10.0) * ESCALATION_DEPLOY_WEIGHT

    # missile fire intensity
    missiles_fired = _sum_missiles(all_actions)
    score += (missiles_fired / 100.0) * ESCALATION_MISSILE_WEIGHT

    # infrastructure targeting
    china_actions = all_actions.get("china", {})
    if china_actions.get("target_priority") == "infrastructure":
        score += ESCALATION_PORT_STRIKE_SCORE

    # airbase strikes
    if airbase_strike:
        score += ESCALATION_AIRBASE_STRIKE_SCORE

    # --- target level ------------------------------------------------------
    target = min(4, int(score))

    # --- apply constraints -------------------------------------------------
    if target > current:
        return min(current + MAX_ESCALATION_CHANGE_PER_TURN, target)
    if target < current and not combat_occurred:
        return max(current - MAX_ESCALATION_CHANGE_PER_TURN, target)
    return current


# ---------------------------------------------------------------------------
# World opinion
# ---------------------------------------------------------------------------

def update_world_opinion(
    state: dict,
    all_actions: dict,
    escalation_level: int,
) -> float:
    """Adjust and return world opinion on a scale of -1.0 (pro-China) to +1.0 (pro-coalition).

    Higher escalation (visible China aggression) pushes opinion toward
    pro-coalition.

    Parameters
    ----------
    state : dict
        Must contain ``world_opinion`` (float, current value).
    all_actions : dict
        Action dicts keyed by country.
    escalation_level : int
        Current escalation level (0-4).

    Returns
    -------
    float
        Updated world opinion clamped to [-1.0, 1.0].
    """
    opinion: float = state.get("world_opinion", 0.0)

    # Escalation pushes opinion toward pro-coalition (+)
    # Rationale: high-profile military escalation makes China look aggressive.
    escalation_shift = escalation_level * 0.05  # +0.00 to +0.20 per turn

    # Infrastructure targeting by China is a big optics hit for China
    china_actions = all_actions.get("china", {})
    targeting_shift = 0.0
    if china_actions.get("target_priority") == "infrastructure":
        targeting_shift = 0.10  # pro-coalition
    elif china_actions.get("target_priority") == "military":
        targeting_shift = 0.02  # mild

    # High coalition missile use can erode support
    coalition_missiles = sum(
        float(all_actions.get(c, {}).get("missile_budget", 0.0))
        for c in ("us", "japan", "taiwan")
    )
    coalition_shift = -(coalition_missiles / 500.0) * 0.05

    # Apply shifts
    opinion += escalation_shift + targeting_shift + coalition_shift

    # Clamp
    opinion = max(-1.0, min(1.0, opinion))
    return opinion
