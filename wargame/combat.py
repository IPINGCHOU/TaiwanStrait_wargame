"""Combat resolution functions for the Taiwan Strait blockade wargame.

Functions:
    resolve_naval      -- Lanchester's Square Law naval combat
    resolve_convoy     -- Sigmoid survival model for convoy escort
    update_blockade_tightness -- Compute blockade effectiveness [0, 1]
    resolve_missiles   -- Clamp budgets, deduct stockpiles, compute damage
    check_homeland_strikes -- Check/apply Chinese strikes on Japanese bases
"""

from __future__ import annotations

import numpy as np

from wargame.constants import (
    TECH_MULTIPLIERS,
    JAPAN_POSTURE_MODIFIER,
    LANCHESTER_RATE,
    NOISE_RANGE,
    MIN_EFFECTIVE_FORCE,
    CARGO_PER_SHIP,
    ROUTE_THREAT_MODIFIER,
    CONVOY_SIGMOID_STEEPNESS,
    BASE_BLOCKADE_LEVEL,
    CHINA_INITIAL,
    US_INITIAL,
    JAPAN_INITIAL,
)


# ---------------------------------------------------------------------------
# Naval Combat (Lanchester's Square Law)
# ---------------------------------------------------------------------------

def resolve_naval(
    state: dict,
    coalition_actions: dict,
    china_actions: dict,
    rng: np.random.RandomState,
) -> dict:
    """Resolve one round of naval combat using Lanchester's Square Law.

    Parameters
    ----------
    state : dict
        Current force counts (us_surface_ships, us_submarines, japan_surface_ships,
        japan_submarines, taiwan_surface_ships, china_surface_ships, china_submarines).
    coalition_actions : dict
        Keyed by "us", "japan", "taiwan". Each contains deploy fractions and
        posture settings.
    china_actions : dict
        Contains "surface_deploy" and "submarine_patrol" fractions.

    Returns
    -------
    dict with keys: us_losses, japan_losses, taiwan_losses,
                    china_surface_losses, china_sub_losses, china_subs_by_jmsdf
    """
    us = coalition_actions["us"]
    jp = coalition_actions["japan"]
    tw = coalition_actions["taiwan"]

    posture = jp.get("engagement_posture", "defensive")
    posture_mod = JAPAN_POSTURE_MODIFIER.get(posture, 0.8)
    asw_priority = jp.get("asw_priority", 0.0)

    # --- Effective forces (per-component) ---
    us_surface_eff = (
        state["us_surface_ships"]
        * us.get("surface_deploy", 0.0)
        * TECH_MULTIPLIERS["us_surface"]
    )
    us_sub_eff = (
        state["us_submarines"]
        * us.get("submarine_deploy", 0.0)
        * TECH_MULTIPLIERS["us_submarine"]
    )
    jp_surface_eff = (
        state["japan_surface_ships"]
        * jp.get("surface_deploy", 0.0)
        * TECH_MULTIPLIERS["japan_surface"]
        * posture_mod
    )
    jp_sub_eff = (
        state["japan_submarines"]
        * jp.get("submarine_deploy", 0.0)
        * TECH_MULTIPLIERS["japan_submarine"]
        * posture_mod
    )
    tw_surface_eff = (
        state["taiwan_surface_ships"]
        * tw.get("surface_deploy", 0.0)
        * TECH_MULTIPLIERS["taiwan_surface"]
    )

    coalition_eff = us_surface_eff + us_sub_eff + jp_surface_eff + jp_sub_eff + tw_surface_eff

    china_surface_eff = (
        state["china_surface_ships"]
        * china_actions.get("surface_deploy", 0.0)
        * TECH_MULTIPLIERS["china_surface"]
    )
    china_sub_eff = (
        state["china_submarines"]
        * china_actions.get("submarine_patrol", 0.0)
        * TECH_MULTIPLIERS["china_submarine"]
    )
    china_eff = china_surface_eff + china_sub_eff

    # Clamp to minimum
    coalition_eff = max(coalition_eff, MIN_EFFECTIVE_FORCE)
    china_eff = max(china_eff, MIN_EFFECTIVE_FORCE)

    # --- Loss rates (Lanchester's Square Law) ---
    coalition_loss_rate = LANCHESTER_RATE * (china_eff ** 2) / coalition_eff
    china_loss_rate = LANCHESTER_RATE * (coalition_eff ** 2) / china_eff

    # Stochastic noise
    coalition_loss_raw = coalition_loss_rate * rng.uniform(*NOISE_RANGE)
    china_loss_raw = china_loss_rate * rng.uniform(*NOISE_RANGE)

    total_coalition_losses = max(0, int(coalition_loss_raw))
    total_china_losses = max(0, int(china_loss_raw))

    # --- Distribute coalition losses proportionally ---
    component_effs = {
        "us": us_surface_eff + us_sub_eff,
        "japan": jp_surface_eff + jp_sub_eff,
        "taiwan": tw_surface_eff,
    }
    total_comp_eff = sum(component_effs.values())

    if total_comp_eff > 0:
        us_losses = int(total_coalition_losses * component_effs["us"] / total_comp_eff)
        jp_losses = int(total_coalition_losses * component_effs["japan"] / total_comp_eff)
        tw_losses = total_coalition_losses - us_losses - jp_losses  # remainder to taiwan
    else:
        us_losses = 0
        jp_losses = 0
        tw_losses = 0

    us_losses = max(0, us_losses)
    jp_losses = max(0, jp_losses)
    tw_losses = max(0, tw_losses)

    # --- Distribute China losses into surface vs sub ---
    china_total_eff = china_surface_eff + china_sub_eff
    if china_total_eff > 0:
        china_surface_losses = int(
            total_china_losses * china_surface_eff / china_total_eff
        )
        china_sub_losses = total_china_losses - china_surface_losses
    else:
        china_surface_losses = 0
        china_sub_losses = 0

    china_surface_losses = max(0, china_surface_losses)
    china_sub_losses = max(0, china_sub_losses)

    # --- Kill attribution: JMSDF ASW ---
    # Coalition sub contribution weighted by ASW priority
    if total_comp_eff > 0 and china_sub_losses > 0:
        china_subs_by_jmsdf = int(
            china_sub_losses * jp_sub_eff * asw_priority / total_comp_eff
        )
        china_subs_by_jmsdf = max(0, min(china_subs_by_jmsdf, china_sub_losses))
    else:
        china_subs_by_jmsdf = 0

    return {
        "us_losses": us_losses,
        "japan_losses": jp_losses,
        "taiwan_losses": tw_losses,
        "china_surface_losses": china_surface_losses,
        "china_sub_losses": china_sub_losses,
        "china_subs_by_jmsdf": china_subs_by_jmsdf,
    }


# ---------------------------------------------------------------------------
# Convoy Escort (Sigmoid Survival Model)
# ---------------------------------------------------------------------------

def resolve_convoy(
    escort_strength: float,
    threat: float,
    convoy_size: int,
    route: str,
    rng: np.random.RandomState,
) -> dict:
    """Compute convoy survival using a sigmoid model.

    Parameters
    ----------
    escort_strength : float
        Combined escort force strength.
    threat : float
        Threat level (enemy interdiction capability).
    convoy_size : int
        Number of ships in the convoy.
    route : str
        One of "direct", "japan_transship", "southern".
    rng : np.random.RandomState
        Random state (reserved for future stochastic extensions).

    Returns
    -------
    dict with keys: ships_surviving, ships_lost, cargo_delivered
    """
    threat *= ROUTE_THREAT_MODIFIER.get(route, 1.0)

    ratio = escort_strength / (threat + 1e-6)
    survival_rate = 1.0 / (1.0 + np.exp(-CONVOY_SIGMOID_STEEPNESS * (ratio - 1.0)))

    ships_surviving = int(convoy_size * survival_rate)
    ships_surviving = max(0, min(ships_surviving, convoy_size))
    ships_lost = convoy_size - ships_surviving
    cargo_delivered = ships_surviving * CARGO_PER_SHIP

    return {
        "ships_surviving": ships_surviving,
        "ships_lost": ships_lost,
        "cargo_delivered": cargo_delivered,
    }


# ---------------------------------------------------------------------------
# Blockade Tightness
# ---------------------------------------------------------------------------

def update_blockade_tightness(
    china_actions: dict,
    china_forces: dict,
    coalition_deployed: dict,
) -> float:
    """Compute the current blockade tightness as a float in [0, 1].

    Parameters
    ----------
    china_actions : dict
        Must contain "blockade_enforcement" in [0, 1].
    china_forces : dict
        Current Chinese forces: surface_ships, submarines, coast_guard.
    coalition_deployed : dict
        Currently deployed coalition forces: us_surface, us_subs,
        japan_surface, japan_subs.

    Returns
    -------
    float in [0, 1]
    """
    # Weighted initial totals (for normalization)
    initial_china_total = (
        CHINA_INITIAL["surface_ships"] * 0.3
        + CHINA_INITIAL["submarines"] * 0.5
        + CHINA_INITIAL["coast_guard"] * 0.2
    )
    initial_coalition_total = (
        US_INITIAL["surface_ships"] * 0.2
        + JAPAN_INITIAL["surface_ships"] * 0.15
        + US_INITIAL["submarines"] * 0.3
        + JAPAN_INITIAL["submarines"] * 0.2
    )

    china_pressure = china_actions["blockade_enforcement"] * (
        china_forces.get("surface_ships", 0) * 0.3
        + china_forces.get("submarines", 0) * 0.5
        + china_forces.get("coast_guard", 0) * 0.2
    ) / max(initial_china_total, 1e-6)

    coalition_counter = (
        coalition_deployed.get("us_surface", 0) * 0.2
        + coalition_deployed.get("japan_surface", 0) * 0.15
        + coalition_deployed.get("us_subs", 0) * 0.3
        + coalition_deployed.get("japan_subs", 0) * 0.2
    ) / max(initial_coalition_total, 1e-6)

    tightness = BASE_BLOCKADE_LEVEL + china_pressure - coalition_counter
    return max(0.0, min(1.0, tightness))


# ---------------------------------------------------------------------------
# Missile Resolution
# ---------------------------------------------------------------------------

def resolve_missiles(
    state: dict,
    china_actions: dict,
    us_actions: dict,
    taiwan_actions: dict,
    escalation_level: int,
) -> dict:
    """Resolve missile exchanges for one turn. Mutates state stockpiles.

    Parameters
    ----------
    state : dict
        Must contain china_missiles, us_missiles, taiwan_missiles.
    china_actions : dict
        "missile_budget": int, "target_priority": str
    us_actions : dict
        "missile_budget": int
    taiwan_actions : dict
        "missile_budget": int
    escalation_level : int
        Current escalation level (reserved for future damage scaling).

    Returns
    -------
    dict with keys: total_missiles_fired, damage_events
    """
    damage_events = []
    total_fired = 0

    # --- China ---
    china_budget = min(china_actions.get("missile_budget", 0), state["china_missiles"])
    state["china_missiles"] -= china_budget
    total_fired += china_budget
    if china_budget > 0:
        damage_events.append({
            "side": "china",
            "missiles_fired": china_budget,
            "target_priority": china_actions.get("target_priority", "military"),
            "damage": china_budget * 0.1,
        })

    # --- US ---
    us_budget = min(us_actions.get("missile_budget", 0), state["us_missiles"])
    state["us_missiles"] -= us_budget
    total_fired += us_budget
    if us_budget > 0:
        damage_events.append({
            "side": "us",
            "missiles_fired": us_budget,
            "damage": us_budget * 0.1,
        })

    # --- Taiwan ---
    tw_budget = min(taiwan_actions.get("missile_budget", 0), state["taiwan_missiles"])
    state["taiwan_missiles"] -= tw_budget
    total_fired += tw_budget
    if tw_budget > 0:
        damage_events.append({
            "side": "taiwan",
            "missiles_fired": tw_budget,
            "damage": tw_budget * 0.1,
        })

    return {
        "total_missiles_fired": total_fired,
        "damage_events": damage_events,
    }


# ---------------------------------------------------------------------------
# Homeland Strikes (China -> Japan)
# ---------------------------------------------------------------------------

_BASE_DEGRADATION = {"open": "limited", "limited": "closed", "closed": "closed"}


def check_homeland_strikes(
    state: dict,
    china_profile: str,
) -> list[dict]:
    """Check if China strikes Japanese bases. Mutates state.

    Parameters
    ----------
    state : dict
        Must contain escalation_level, japan_base_okinawa, japan_base_kyushu,
        japan_homeland_strikes, japan_okinawa_strikes, japan_kyushu_strikes,
        japan_mainland_strikes.
    china_profile : str
        One of "cautious", "adaptive", "aggressive".

    Returns
    -------
    list of strike event dicts
    """
    events: list[dict] = []
    escalation = state.get("escalation_level", 0)

    # Cautious profile never strikes Japan
    if china_profile == "cautious":
        return events

    # Determine if strikes happen based on profile + escalation
    strikes_triggered = False
    if china_profile == "aggressive" and escalation >= 3:
        strikes_triggered = True
    elif china_profile == "adaptive" and escalation >= 4:
        strikes_triggered = True

    if not strikes_triggered:
        return events

    # Strike Okinawa if not already closed
    okinawa_status = state.get("japan_base_okinawa", "closed")
    if okinawa_status != "closed":
        new_status = _BASE_DEGRADATION[okinawa_status]
        state["japan_base_okinawa"] = new_status
        state["japan_okinawa_strikes"] = state.get("japan_okinawa_strikes", 0) + 1
        state["japan_homeland_strikes"] = state.get("japan_homeland_strikes", 0) + 1
        events.append({
            "target": "okinawa",
            "previous_status": okinawa_status,
            "new_status": new_status,
        })

    # Strike Kyushu if not already closed
    kyushu_status = state.get("japan_base_kyushu", "closed")
    if kyushu_status != "closed":
        new_status = _BASE_DEGRADATION[kyushu_status]
        state["japan_base_kyushu"] = new_status
        state["japan_kyushu_strikes"] = state.get("japan_kyushu_strikes", 0) + 1
        state["japan_homeland_strikes"] = state.get("japan_homeland_strikes", 0) + 1
        events.append({
            "target": "kyushu",
            "previous_status": kyushu_status,
            "new_status": new_status,
        })

    return events
