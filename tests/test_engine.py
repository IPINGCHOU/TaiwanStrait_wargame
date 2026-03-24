from wargame.engine import WarGame
from wargame.scenarios import EVALUATION_SCENARIOS


def test_game_runs_to_completion():
    """Game runs 20 weeks with dummy strategies."""
    scenario = EVALUATION_SCENARIOS[0]
    game = WarGame(scenario=scenario, seed=42)

    while not game.is_done():
        game.step(_dummy_japan_actions())

    result = game.get_result()
    assert "score" in result
    assert "weeks" in result
    assert "taiwan_survived" in result
    assert 1 <= result["weeks"] <= 20


def test_game_state_has_all_fields():
    """Game state contains all fields from the spec."""
    game = WarGame(scenario=EVALUATION_SCENARIOS[0], seed=0)
    state = game.get_state()
    required = ["week", "china_surface_ships", "us_submarines",
                "taiwan_morale", "japan_surface_ships", "blockade_tightness",
                "escalation_level", "cargo_via_japan",
                "peak_blockade_tightness", "escalation_decreased",
                "japan_avg_deploy", "japan_article9_violations"]
    for key in required:
        assert key in state, f"Missing state key: {key}"


def test_game_deterministic_with_same_seed():
    """Same seed + same strategy = same result."""
    scenario = EVALUATION_SCENARIOS[0]
    results = []
    for _ in range(2):
        game = WarGame(scenario=scenario, seed=42)
        while not game.is_done():
            game.step(_dummy_japan_actions())
        results.append(game.get_result())
    assert results[0]["score"]["total"] == results[1]["score"]["total"]


def test_passive_japan_scores_worse_than_active():
    """Passive Japan should score significantly worse than active Japan."""
    scenario = EVALUATION_SCENARIOS[0]  # baseline

    # Active Japan
    game_active = WarGame(scenario=scenario, seed=42)
    while not game_active.is_done():
        game_active.step(_dummy_japan_actions())
    active_score = game_active.get_result()["score"]["total"]

    # Passive Japan
    passive = {
        "surface_deploy": 0.0, "submarine_deploy": 0.0,
        "air_sortie_rate": 0.0,
        "okinawa_access": "closed", "kyushu_access": "closed",
        "transshipment_allow": False, "convoy_escort_commit": 0.0,
        "port_capacity_share": 0.0,
        "engagement_posture": "self_defense_only", "asw_priority": 0.0,
        "diplomatic_pressure": 0.0, "sanctions_advocacy": False,
        "humanitarian_aid": 0.0,
    }
    game_passive = WarGame(scenario=scenario, seed=42)
    while not game_passive.is_done():
        game_passive.step(passive)
    passive_score = game_passive.get_result()["score"]["total"]

    # Active Japan should score much better (alliance credibility, operational success)
    assert active_score > passive_score + 50


def test_turn_actions_recorded():
    """Engine records all 4 players' actions each turn."""
    scenario = EVALUATION_SCENARIOS[0]
    game = WarGame(scenario=scenario, seed=42)

    while not game.is_done():
        game.step(_dummy_japan_actions())

    result = game.get_result()

    # turn_actions should be in result
    assert "turn_actions" in result
    # One entry per week played
    assert len(result["turn_actions"]) == result["weeks"]
    # Each entry has all 4 countries
    first = result["turn_actions"][0]
    assert set(first.keys()) == {"china", "us", "japan", "taiwan"}
    # Japan actions match input (no clamping: 0.5 + 0.3 < 1.0)
    assert first["japan"]["engagement_posture"] == "defensive"


def _dummy_japan_actions():
    return {
        "surface_deploy": 0.5, "submarine_deploy": 0.5,
        "air_sortie_rate": 0.3,
        "okinawa_access": "limited", "kyushu_access": "closed",
        "transshipment_allow": True, "convoy_escort_commit": 0.3,
        "port_capacity_share": 0.3,
        "engagement_posture": "defensive", "asw_priority": 0.5,
        "diplomatic_pressure": 0.5, "sanctions_advocacy": True,
        "humanitarian_aid": 0.3,
    }
