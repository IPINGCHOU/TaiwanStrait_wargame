"""Japan-centric scoring system v2 — smooth gradients, centered baseline.

All categories use continuous functions (no binary jumps) so that small
strategy improvements always produce measurable score changes.

Target: range ≈ -1000 to +1000, baseline strategy ≈ 0.
"""

from __future__ import annotations

import math

from wargame.constants import (
    CARGO_PER_SHIP,
    CHINA_INITIAL,
    JAPAN_INITIAL,
    MAX_WEEKS,
    # Category A
    SCORE_WIN_BASE,
    SCORE_WIN_HEALTH_MAX,
    SCORE_SURRENDER_BASE,
    SCORE_SURRENDER_PER_REMAINING_WEEK,
    # Category B
    SCORE_ELECTRICITY_MAX,
    SCORE_ECONOMY_MAX,
    SCORE_MORALE_MAX,
    # Category C
    SCORE_JMSDF_SURFACE_MAX,
    SCORE_JMSDF_SUBS_MAX,
    SCORE_JMSDF_AIR_MAX,
    # Category D
    SCORE_HOMELAND_MAX,
    SCORE_HOMELAND_DECAY_RATE,
    SCORE_OKINAWA_STRIKE_PENALTY,
    SCORE_KYUSHU_STRIKE_PENALTY,
    SCORE_MAINLAND_STRIKE_PENALTY,
    SCORE_US_MISSILE_DEFENSE_BONUS,
    # Category E
    SCORE_SEA_LANE_DISRUPTION_PER_WEEK,
    # Category F
    SCORE_CONVOY_JAPAN_MAX,
    SCORE_CORRIDOR_RECOVERY_MAX,
    SCORE_ASW_EFFECTIVENESS_MAX,
    SCORE_BLOCKADE_CONTRIBUTION_MAX,
    SCORE_DELIVERY_CONSISTENCY_MAX,
    SCORE_CHINA_ATTRITION_MAX,
    # Category G
    SCORE_ALLIANCE_SLOPE,
    SCORE_ALLIANCE_INTERCEPT,
    # Category H
    SCORE_ESCALATION_BASE,
    SCORE_ESCALATION_SLOPE,
    SCORE_DEESCALATION_BONUS,
    # Category I
    SCORE_ARTICLE9_PENALTY_PER_TURN,
    SCORE_FIRST_STRIKE_PENALTY,
    SCORE_CIVILIAN_CASUALTY_MAX_PENALTY,
    SCORE_CIVILIAN_CASUALTY_DIVISOR,
    # Centering
    SCORE_CENTERING_OFFSET,
    # Fitness
    FITNESS_AVG_WEIGHT,
    FITNESS_MIN_WEIGHT,
    FITNESS_WINRATE_MULTIPLIER,
)


def compute_score(
    state: dict,
    taiwan_survived: bool,
    weeks_played: int,
) -> dict:
    """Return a dict with ``"total"`` and 9 category keys (A through I)."""

    a = _category_a_outcome(state, taiwan_survived, weeks_played)
    b = _category_b_taiwan_survival(state)
    c = _category_c_jmsdf_preservation(state)
    d = _category_d_homeland_security(state)
    e = _category_e_economic_impact(state)
    f = _category_f_operational_success(state)
    g = _category_g_alliance_credibility(state)
    h = _category_h_escalation_mgmt(state, weeks_played)
    i = _category_i_legal_humanitarian(state)

    total = a + b + c + d + e + f + g + h + i - SCORE_CENTERING_OFFSET

    return {
        "total": total,
        "A_outcome": a,
        "B_taiwan_survival": b,
        "C_jmsdf_preservation": c,
        "D_homeland_security": d,
        "E_economic_impact": e,
        "F_operational_success": f,
        "G_alliance_credibility": g,
        "H_escalation_mgmt": h,
        "I_legal_humanitarian": i,
    }


def compute_fitness_aggregate(scenario_results: list[dict]) -> float:
    """Combine multiple scenario results into a single fitness scalar."""
    scores = [r["score"] for r in scenario_results]
    avg_score = sum(scores) / len(scores)
    min_score = min(scores)
    win_rate = sum(1 for r in scenario_results if r["taiwan_survived"]) / len(
        scenario_results
    )
    return (
        avg_score * FITNESS_AVG_WEIGHT
        + min_score * FITNESS_MIN_WEIGHT
        + win_rate * FITNESS_WINRATE_MULTIPLIER
    )


# ---------------------------------------------------------------------------
# Category helpers
# ---------------------------------------------------------------------------

def _category_a_outcome(state: dict, taiwan_survived: bool, weeks_played: int) -> float:
    """A — Strategic Outcome: continuous health-weighted win score.

    Win: +50 base + up to +150 × (electricity% × morale). Ranges 50–200.
    Lose: -200 base - 15 × remaining weeks. Ranges -200 to -500.
    """
    if taiwan_survived:
        elec_frac = min(state["taiwan_electricity_pct"] / 100.0, 1.0)
        morale = state["taiwan_morale"]
        health = elec_frac * morale  # 0.0 to 1.0
        return SCORE_WIN_BASE + SCORE_WIN_HEALTH_MAX * health
    # Taiwan surrendered
    remaining = MAX_WEEKS - weeks_played
    return SCORE_SURRENDER_BASE + SCORE_SURRENDER_PER_REMAINING_WEEK * remaining


def _category_b_taiwan_survival(state: dict) -> float:
    """B — Taiwan Survival Quality: electricity, economy, morale. (0 to 200)"""
    elec = min(state["taiwan_electricity_pct"] / 100.0, 1.0) * SCORE_ELECTRICITY_MAX
    econ = min(state["taiwan_economy_pct"] / 100.0, 1.0) * SCORE_ECONOMY_MAX
    morale = state["taiwan_morale"] * SCORE_MORALE_MAX
    return elec + econ + morale


def _category_c_jmsdf_preservation(state: dict) -> float:
    """C — JMSDF Preservation: fraction remaining. (0 to 150)"""
    surface = (
        state["japan_surface_ships"] / JAPAN_INITIAL["surface_ships"]
        * SCORE_JMSDF_SURFACE_MAX
    )
    subs = (
        state["japan_submarines"] / JAPAN_INITIAL["submarines"]
        * SCORE_JMSDF_SUBS_MAX
    )
    air = (
        state["japan_aircraft"] / JAPAN_INITIAL["aircraft"]
        * SCORE_JMSDF_AIR_MAX
    )
    return surface + subs + air


def _category_d_homeland_security(state: dict) -> float:
    """D — Homeland Security: exponential decay with strikes. (-200 to +100)

    Safe bonus decays smoothly: 100 × exp(-0.7 × total_strikes).
    0 strikes → 100, 1 → 50, 2 → 25, 3 → 12, etc.
    """
    total_strikes = state["japan_homeland_strikes"]

    # Smooth safe bonus (exponential decay)
    safe_score = SCORE_HOMELAND_MAX * math.exp(-SCORE_HOMELAND_DECAY_RATE * total_strikes)

    # Per-base penalties (still discrete per strike but accumulate smoothly)
    base_penalty = (
        SCORE_OKINAWA_STRIKE_PENALTY * min(state["japan_okinawa_strikes"], 3)
        + SCORE_KYUSHU_STRIKE_PENALTY * min(state["japan_kyushu_strikes"], 2)
        + SCORE_MAINLAND_STRIKE_PENALTY * min(state["japan_mainland_strikes"], 2)
    )

    # Missile defense bonus
    missile_def = SCORE_US_MISSILE_DEFENSE_BONUS if state.get("us_japan_missile_defense", False) else 0.0

    return safe_score + base_penalty + missile_def


def _category_e_economic_impact(state: dict) -> float:
    """E — Economic Impact: sea-lane disruption. (-100 to 0)"""
    return SCORE_SEA_LANE_DISRUPTION_PER_WEEK * state["sea_lanes_disrupted_weeks"]


def _category_f_operational_success(state: dict) -> float:
    """F — Operational Success: convoy, corridor, ASW, blockade, consistency, attrition. (0 to 200)"""
    # Convoy cargo routed through Japan
    target_cargo = CARGO_PER_SHIP * MAX_WEEKS * 10
    convoy = min(state["cargo_via_japan"] / target_cargo, 1.0) * SCORE_CONVOY_JAPAN_MAX

    # Corridor recovery
    peak = max(state.get("peak_blockade_tightness", 0.01), 0.01)
    current = state.get("blockade_tightness", peak)
    corridor = (peak - current) / peak * SCORE_CORRIDOR_RECOVERY_MAX

    # ASW effectiveness
    asw = (
        state["china_subs_neutralized_by_jmsdf"]
        / CHINA_INITIAL["submarines"]
        * SCORE_ASW_EFFECTIVENESS_MAX
    )

    # Blockade contribution
    blockade_contrib = state["japan_blockade_reduction_share"] * SCORE_BLOCKADE_CONTRIBUTION_MAX

    # Delivery consistency: reward low variance in per-turn cargo
    cargo_per_turn = state.get("cargo_per_turn", [])
    if len(cargo_per_turn) >= 2:
        import numpy as np
        mean_cargo = np.mean(cargo_per_turn)
        if mean_cargo > 0:
            cv = np.std(cargo_per_turn) / mean_cargo  # coefficient of variation
            consistency = max(0, 1.0 - cv) * SCORE_DELIVERY_CONSISTENCY_MAX
        else:
            consistency = 0.0
    else:
        consistency = 0.0

    # China force attrition: reward degrading China's navy
    china_surface_frac = 1.0 - state["china_surface_ships"] / CHINA_INITIAL["surface_ships"]
    china_sub_frac = 1.0 - state["china_submarines"] / CHINA_INITIAL["submarines"]
    attrition = (china_surface_frac * 0.5 + china_sub_frac * 0.5) * SCORE_CHINA_ATTRITION_MAX

    return convoy + corridor + asw + blockade_contrib + consistency + attrition


def _category_g_alliance_credibility(state: dict) -> float:
    """G — Alliance Credibility: pure linear scaling. (-100 to +100)

    score = 200 × avg_deploy - 100
    deploy=0 → -100, deploy=0.5 → 0, deploy=1.0 → +100
    """
    deploy = state["japan_avg_deploy"]
    return SCORE_ALLIANCE_SLOPE * min(deploy, 1.0) + SCORE_ALLIANCE_INTERCEPT


def _category_h_escalation_mgmt(state: dict, weeks_played: int) -> float:
    """H — Escalation Management: continuous, based on avg escalation. (-200 to +100)

    score = 100 - 75 × avg_escalation
    avg_esc=0 → +100, avg_esc=1.33 → 0, avg_esc=4 → -200
    """
    if weeks_played > 0:
        avg_esc = state["escalation_sum"] / weeks_played
    else:
        avg_esc = state["escalation_level"]

    score = SCORE_ESCALATION_BASE + SCORE_ESCALATION_SLOPE * avg_esc

    # De-escalation bonus (still binary but small)
    if state.get("escalation_decreased", False):
        score += SCORE_DEESCALATION_BONUS

    return max(-200, min(130, score))  # clamp to reasonable range


def _category_i_legal_humanitarian(state: dict) -> float:
    """I — Legal & Humanitarian: article 9, first strike, civilian casualties. (-100 to 0)"""
    score = 0.0
    score += SCORE_ARTICLE9_PENALTY_PER_TURN * state["japan_article9_violations"]

    if state.get("japan_first_strike", False):
        score += SCORE_FIRST_STRIKE_PENALTY

    casualty_frac = min(
        state["japan_civilian_casualties"] / SCORE_CIVILIAN_CASUALTY_DIVISOR, 1.0
    )
    score += casualty_frac * SCORE_CIVILIAN_CASUALTY_MAX_PENALTY

    return score
