"""Tests for wargame.scoring — Japan-centric 9-category scoring system."""

from wargame.scoring import compute_score, compute_fitness_aggregate
from wargame.constants import JAPAN_INITIAL


def test_winning_game_positive_score():
    state = _winning_state()
    result = compute_score(state, taiwan_survived=True, weeks_played=20)
    assert result["total"] > 500


def test_losing_game_negative_score():
    state = _losing_state()
    result = compute_score(state, taiwan_survived=False, weeks_played=12)
    assert result["total"] < 0


def test_score_categories_breakdown():
    state = _winning_state()
    result = compute_score(state, taiwan_survived=True, weeks_played=20)
    assert isinstance(result, dict)
    assert "total" in result
    for cat in ["A_outcome", "B_taiwan_survival", "C_jmsdf_preservation",
                "D_homeland_security", "E_economic_impact", "F_operational_success",
                "G_alliance_credibility", "H_escalation_mgmt", "I_legal_humanitarian"]:
        assert cat in result, f"Missing category: {cat}"


def test_homeland_strikes_reduce_score():
    clean = _winning_state()
    struck = _winning_state()
    struck["japan_okinawa_strikes"] = 2
    struck["japan_kyushu_strikes"] = 1
    struck["japan_homeland_strikes"] = 3
    clean_score = compute_score(clean, True, 20)["total"]
    struck_score = compute_score(struck, True, 20)["total"]
    assert struck_score < clean_score - 100


def test_deescalation_bonus():
    state_no = _winning_state()
    state_no["escalation_decreased"] = False
    state_yes = _winning_state()
    state_yes["escalation_decreased"] = True
    score_no = compute_score(state_no, True, 20)["H_escalation_mgmt"]
    score_yes = compute_score(state_yes, True, 20)["H_escalation_mgmt"]
    assert score_yes > score_no


def test_fitness_aggregate():
    scenario_results = [
        {"score": 700, "taiwan_survived": True},
        {"score": 400, "taiwan_survived": True},
        {"score": 200, "taiwan_survived": False},
    ]
    combined = compute_fitness_aggregate(scenario_results)
    expected = 433.3 * 0.5 + 200 * 0.3 + (2 / 3) * 200
    assert abs(combined - expected) < 1.0


def _winning_state():
    return {
        "taiwan_electricity_pct": 70.0, "taiwan_economy_pct": 65.0, "taiwan_morale": 0.6,
        "japan_surface_ships": 16, "japan_submarines": 5, "japan_aircraft": 80,
        "japan_okinawa_strikes": 0, "japan_kyushu_strikes": 0,
        "japan_mainland_strikes": 0, "japan_homeland_strikes": 0,
        "escalation_level": 2, "escalation_decreased": False,
        "sea_lanes_disrupted_weeks": 5,
        "cargo_via_japan": 30.0, "total_cargo_delivered": 50.0,
        "china_subs_neutralized_by_jmsdf": 4,
        "china_submarines": 12,
        "japan_blockade_reduction_share": 0.3,
        "blockade_tightness": 0.4, "peak_blockade_tightness": 0.8,
        "us_japan_missile_defense": True,
        "japan_avg_deploy": 0.4,
        "japan_article9_violations": 0,
        "japan_first_strike": False,
        "japan_civilian_casualties": 0,
        "civilian_casualties": 500,
    }


def _losing_state():
    s = _winning_state()
    s["taiwan_morale"] = 0.05
    s["taiwan_economy_pct"] = 15.0
    s["taiwan_electricity_pct"] = 10.0
    return s
