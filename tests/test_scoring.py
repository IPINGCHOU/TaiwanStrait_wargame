"""Tests for wargame.scoring — Japan-centric 9-category scoring system v2."""

from wargame.scoring import compute_score, compute_fitness_aggregate
from wargame.constants import JAPAN_INITIAL


def test_winning_game_positive_score():
    state = _winning_state()
    result = compute_score(state, taiwan_survived=True, weeks_played=20)
    # A good winning game should score positive (above centering offset)
    assert result["total"] > -100


def test_losing_game_negative_score():
    state = _losing_state()
    result = compute_score(state, taiwan_survived=False, weeks_played=12)
    assert result["total"] < -200


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
    assert struck_score < clean_score - 50


def test_deescalation_bonus():
    state_no = _winning_state()
    state_no["escalation_decreased"] = False
    state_yes = _winning_state()
    state_yes["escalation_decreased"] = True
    score_no = compute_score(state_no, True, 20)["H_escalation_mgmt"]
    score_yes = compute_score(state_yes, True, 20)["H_escalation_mgmt"]
    assert score_yes > score_no


def test_continuous_escalation_gradient():
    """Average escalation creates smooth gradient, not step function."""
    scores = []
    for esc_sum in [0, 10, 20, 30, 40]:
        state = _winning_state()
        state["escalation_sum"] = esc_sum
        s = compute_score(state, True, 20)["H_escalation_mgmt"]
        scores.append(s)
    # Each step should decrease monotonically
    for i in range(len(scores) - 1):
        assert scores[i] > scores[i + 1], f"Not monotonic at {i}: {scores}"


def test_continuous_homeland_gradient():
    """Homeland score decays smoothly with strikes, not binary."""
    scores = []
    for strikes in [0, 1, 2, 3, 5]:
        state = _winning_state()
        state["japan_homeland_strikes"] = strikes
        s = compute_score(state, True, 20)["D_homeland_security"]
        scores.append(s)
    # Each step should decrease
    for i in range(len(scores) - 1):
        assert scores[i] > scores[i + 1], f"Not monotonic at {i}: {scores}"


def test_alliance_linear_gradient():
    """Alliance credibility is pure linear, no threshold caps."""
    scores = []
    for deploy in [0.0, 0.2, 0.4, 0.6, 0.8, 1.0]:
        state = _winning_state()
        state["japan_avg_deploy"] = deploy
        s = compute_score(state, True, 20)["G_alliance_credibility"]
        scores.append(s)
    # Monotonically increasing
    for i in range(len(scores) - 1):
        assert scores[i] < scores[i + 1], f"Not monotonic at {i}: {scores}"


def test_fitness_aggregate():
    scenario_results = [
        {"score": 700, "taiwan_survived": True},
        {"score": 400, "taiwan_survived": True},
        {"score": 200, "taiwan_survived": False},
    ]
    combined = compute_fitness_aggregate(scenario_results)
    avg = (700 + 400 + 200) / 3
    expected = avg * 0.6 + 200 * 0.15 + (2 / 3) * 200
    assert abs(combined - expected) < 1.0


def _winning_state():
    return {
        "taiwan_electricity_pct": 70.0, "taiwan_economy_pct": 65.0, "taiwan_morale": 0.6,
        "japan_surface_ships": 16, "japan_submarines": 5, "japan_aircraft": 80,
        "japan_okinawa_strikes": 0, "japan_kyushu_strikes": 0,
        "japan_mainland_strikes": 0, "japan_homeland_strikes": 0,
        "escalation_level": 2, "escalation_decreased": False,
        "escalation_sum": 30,  # avg escalation = 1.5 over 20 weeks
        "sea_lanes_disrupted_weeks": 5,
        "cargo_via_japan": 30.0, "total_cargo_delivered": 50.0,
        "cargo_per_turn": [2.5] * 20,  # steady delivery
        "china_surface_ships": 40, "china_submarines": 12,
        "china_subs_neutralized_by_jmsdf": 4,
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
