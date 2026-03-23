"""Japan-centric scoring system with 9 weighted categories (A-I).

Each category returns a sub-score; ``compute_score`` aggregates them into a
single *total*.  ``compute_fitness_aggregate`` combines results across multiple
scenario runs into a single fitness value suitable for evolutionary search.
"""

from __future__ import annotations

from wargame.constants import (
    # Game constants
    CARGO_PER_SHIP,
    CHINA_INITIAL,
    JAPAN_INITIAL,
    MAX_WEEKS,
    # Category A — Strategic Outcome
    SCORE_WIN_BONUS,
    SCORE_SURRENDER_PENALTY,
    SCORE_EARLY_SURRENDER_PER_WEEK,
    # Category B — Taiwan Survival Quality
    SCORE_ELECTRICITY_MAX,
    SCORE_ECONOMY_MAX,
    SCORE_MORALE_MAX,
    # Category C — JMSDF Preservation
    SCORE_JMSDF_SURFACE_MAX,
    SCORE_JMSDF_SUBS_MAX,
    SCORE_JMSDF_AIR_MAX,
    # Category D — Homeland Security
    SCORE_HOMELAND_SAFE_BONUS,
    SCORE_OKINAWA_STRIKE_PENALTY,
    SCORE_KYUSHU_STRIKE_PENALTY,
    SCORE_MAINLAND_STRIKE_PENALTY,
    SCORE_US_MISSILE_DEFENSE_BONUS,
    # Category E — Economic Impact
    SCORE_SEA_LANE_DISRUPTION_PER_WEEK,
    # Category F — Operational Success
    SCORE_CONVOY_JAPAN_MAX,
    SCORE_CORRIDOR_RECOVERY_MAX,
    SCORE_ASW_EFFECTIVENESS_MAX,
    SCORE_BLOCKADE_CONTRIBUTION_MAX,
    # Category G — Alliance Credibility
    SCORE_US_SATISFACTION_MAX,
    SCORE_FREE_RIDING_PENALTY,
    SCORE_FREE_RIDING_THRESHOLD,
    SCORE_REGIONAL_TRUST_MAX,
    # Category H — Escalation Management
    SCORE_ESCALATION_LOW_BONUS,
    SCORE_ESCALATION_LEVEL3_PENALTY,
    SCORE_ESCALATION_LEVEL4_PENALTY,
    SCORE_HOMELAND_ESCALATION_PENALTY,
    SCORE_DEESCALATION_BONUS,
    # Category I — Legal & Humanitarian
    SCORE_ARTICLE9_PENALTY_PER_TURN,
    SCORE_FIRST_STRIKE_PENALTY,
    SCORE_CIVILIAN_CASUALTY_MAX_PENALTY,
    SCORE_CIVILIAN_CASUALTY_DIVISOR,
    # Fitness aggregation
    FITNESS_AVG_WEIGHT,
    FITNESS_MIN_WEIGHT,
    FITNESS_WINRATE_MULTIPLIER,
)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def compute_score(
    state: dict,
    taiwan_survived: bool,
    weeks_played: int,
) -> dict:
    """Return a dict with ``"total"`` and 9 category keys (A through I).

    Parameters
    ----------
    state:
        End-of-game state dictionary produced by the simulation engine.
    taiwan_survived:
        ``True`` if Taiwan did not surrender before the game ended.
    weeks_played:
        How many weekly turns elapsed before the game concluded.
    """

    a = _category_a_outcome(taiwan_survived, weeks_played)
    b = _category_b_taiwan_survival(state)
    c = _category_c_jmsdf_preservation(state)
    d = _category_d_homeland_security(state)
    e = _category_e_economic_impact(state)
    f = _category_f_operational_success(state)
    g = _category_g_alliance_credibility(state)
    h = _category_h_escalation_mgmt(state)
    i = _category_i_legal_humanitarian(state)

    total = a + b + c + d + e + f + g + h + i

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
    """Combine multiple scenario results into a single fitness scalar.

    Parameters
    ----------
    scenario_results:
        List of dicts, each with ``"score"`` (float) and
        ``"taiwan_survived"`` (bool).

    Returns
    -------
    float
        Weighted combination:
        ``avg_score * FITNESS_AVG_WEIGHT
         + min_score * FITNESS_MIN_WEIGHT
         + win_rate  * FITNESS_WINRATE_MULTIPLIER``
    """

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
# Category helpers (private)
# ---------------------------------------------------------------------------

def _category_a_outcome(taiwan_survived: bool, weeks_played: int) -> float:
    """A — Strategic Outcome: win/loss bonus + early-surrender penalty."""
    if taiwan_survived:
        return SCORE_WIN_BONUS
    # Taiwan surrendered
    score = SCORE_SURRENDER_PENALTY
    remaining_weeks = MAX_WEEKS - weeks_played
    score += SCORE_EARLY_SURRENDER_PER_WEEK * remaining_weeks
    return score


def _category_b_taiwan_survival(state: dict) -> float:
    """B — Taiwan Survival Quality: electricity, economy, morale."""
    elec = state["taiwan_electricity_pct"] / 100.0 * SCORE_ELECTRICITY_MAX
    econ = state["taiwan_economy_pct"] / 100.0 * SCORE_ECONOMY_MAX
    morale = state["taiwan_morale"] * SCORE_MORALE_MAX
    return elec + econ + morale


def _category_c_jmsdf_preservation(state: dict) -> float:
    """C — JMSDF Preservation: fraction of ships/subs/aircraft remaining."""
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
    """D — Homeland Security: bonuses for safety, penalties for strikes."""
    score = 0.0

    # Safe homeland bonus
    if state["japan_homeland_strikes"] == 0:
        score += SCORE_HOMELAND_SAFE_BONUS

    # Strike penalties (capped)
    score += SCORE_OKINAWA_STRIKE_PENALTY * min(state["japan_okinawa_strikes"], 3)
    score += SCORE_KYUSHU_STRIKE_PENALTY * min(state["japan_kyushu_strikes"], 2)
    score += SCORE_MAINLAND_STRIKE_PENALTY * min(state["japan_mainland_strikes"], 2)

    # US–Japan missile defense cooperation bonus
    if state.get("us_japan_missile_defense", False):
        score += SCORE_US_MISSILE_DEFENSE_BONUS

    # Interception bonus — skip for now (set to 0)

    return score


def _category_e_economic_impact(state: dict) -> float:
    """E — Economic Impact: sea-lane disruption penalty."""
    return SCORE_SEA_LANE_DISRUPTION_PER_WEEK * state["sea_lanes_disrupted_weeks"]


def _category_f_operational_success(state: dict) -> float:
    """F — Operational Success: convoy throughput, corridor recovery, ASW, blockade."""
    # Convoy cargo routed through Japan (target ~200 cargo units)
    target_cargo = CARGO_PER_SHIP * MAX_WEEKS * 10
    convoy = (
        state["cargo_via_japan"] / target_cargo * SCORE_CONVOY_JAPAN_MAX
    )

    # Corridor recovery: how much blockade tightness was reduced from peak
    peak = max(state.get("peak_blockade_tightness", 0.01), 0.01)
    current = state.get("blockade_tightness", peak)
    corridor = (peak - current) / peak * SCORE_CORRIDOR_RECOVERY_MAX

    # ASW effectiveness
    china_subs_initial = CHINA_INITIAL["submarines"]
    asw = (
        state["china_subs_neutralized_by_jmsdf"]
        / china_subs_initial
        * SCORE_ASW_EFFECTIVENESS_MAX
    )

    # Japan's share of blockade reduction
    blockade_contrib = (
        state["japan_blockade_reduction_share"] * SCORE_BLOCKADE_CONTRIBUTION_MAX
    )

    return convoy + corridor + asw + blockade_contrib


def _category_g_alliance_credibility(state: dict) -> float:
    """G — Alliance Credibility: US satisfaction, free-riding penalty, regional trust."""
    deploy = state["japan_avg_deploy"]

    # US satisfaction (deploy >= 50% = full marks)
    us_sat = min(deploy / 0.5, 1.0) * SCORE_US_SATISFACTION_MAX

    # Free-riding penalty
    free_ride = SCORE_FREE_RIDING_PENALTY if deploy < SCORE_FREE_RIDING_THRESHOLD else 0.0

    # Regional trust (deploy >= 30% = full marks)
    regional = min(deploy / 0.3, 1.0) * SCORE_REGIONAL_TRUST_MAX

    return us_sat + free_ride + regional


def _category_h_escalation_mgmt(state: dict) -> float:
    """H — Escalation Management: level-based bonus/penalty, de-escalation bonus."""
    level = state["escalation_level"]

    if level <= 1:
        score = SCORE_ESCALATION_LOW_BONUS
    elif level == 2:
        score = 0.0
    elif level == 3:
        score = SCORE_ESCALATION_LEVEL3_PENALTY
    else:  # level >= 4
        score = SCORE_ESCALATION_LEVEL4_PENALTY

    # Homeland escalation penalty
    if state["japan_homeland_strikes"] > 0:
        score += SCORE_HOMELAND_ESCALATION_PENALTY

    # De-escalation bonus
    if state.get("escalation_decreased", False):
        score += SCORE_DEESCALATION_BONUS

    return score


def _category_i_legal_humanitarian(state: dict) -> float:
    """I — Legal & Humanitarian: Article 9, first strike, civilian casualties."""
    score = 0.0

    # Article 9 violations
    score += SCORE_ARTICLE9_PENALTY_PER_TURN * state["japan_article9_violations"]

    # First strike penalty
    if state.get("japan_first_strike", False):
        score += SCORE_FIRST_STRIKE_PENALTY

    # Civilian casualties (scaled, capped at divisor)
    casualty_frac = min(
        state["japan_civilian_casualties"] / SCORE_CIVILIAN_CASUALTY_DIVISOR, 1.0
    )
    score += casualty_frac * SCORE_CIVILIAN_CASUALTY_MAX_PENALTY

    return score
