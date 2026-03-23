import numpy as np
from wargame.combat import (
    resolve_naval, resolve_convoy, update_blockade_tightness,
    resolve_missiles, check_homeland_strikes,
)
from wargame.constants import *

def test_resolve_naval_returns_losses_per_country():
    """Naval combat returns a dict of losses keyed by country."""
    state = {
        "us_surface_ships": 24, "us_submarines": 12,
        "japan_surface_ships": 20, "japan_submarines": 6,
        "taiwan_surface_ships": 26,
        "china_surface_ships": 60, "china_submarines": 20,
    }
    coalition_actions = {
        "us": {"surface_deploy": 0.5, "submarine_deploy": 0.8, "convoy_escort_commit": 0.2},
        "japan": {"surface_deploy": 0.5, "submarine_deploy": 0.5,
                  "engagement_posture": "defensive", "asw_priority": 0.5,
                  "convoy_escort_commit": 0.3},
        "taiwan": {"surface_deploy": 0.3},
    }
    china_actions = {"surface_deploy": 0.8, "submarine_patrol": 0.6}
    rng = np.random.RandomState(42)

    result = resolve_naval(state, coalition_actions, china_actions, rng)

    assert "us_losses" in result
    assert "japan_losses" in result
    assert "taiwan_losses" in result
    assert "china_surface_losses" in result
    assert "china_sub_losses" in result
    assert "china_subs_by_jmsdf" in result
    assert all(v >= 0 for v in result.values())


def test_resolve_naval_zero_forces():
    """No crash when one side has zero forces."""
    state = {
        "us_surface_ships": 0, "us_submarines": 0,
        "japan_surface_ships": 0, "japan_submarines": 0,
        "taiwan_surface_ships": 0,
        "china_surface_ships": 60, "china_submarines": 20,
    }
    coalition_actions = {
        "us": {"surface_deploy": 0, "submarine_deploy": 0, "convoy_escort_commit": 0},
        "japan": {"surface_deploy": 0, "submarine_deploy": 0,
                  "engagement_posture": "self_defense_only", "asw_priority": 0,
                  "convoy_escort_commit": 0},
        "taiwan": {"surface_deploy": 0},
    }
    china_actions = {"surface_deploy": 0.8, "submarine_patrol": 0.6}
    rng = np.random.RandomState(42)

    result = resolve_naval(state, coalition_actions, china_actions, rng)
    assert result["china_surface_losses"] == 0


def test_convoy_survival_high_escort():
    """High escort ratio -> high survival rate."""
    survival = resolve_convoy(
        escort_strength=20.0, threat=5.0, convoy_size=10, route="japan_transship",
        rng=np.random.RandomState(42),
    )
    assert survival["ships_surviving"] >= 8
    assert survival["cargo_delivered"] > 0


def test_convoy_survival_no_escort():
    """Zero escort -> low survival."""
    survival = resolve_convoy(
        escort_strength=0.0, threat=20.0, convoy_size=10, route="direct",
        rng=np.random.RandomState(42),
    )
    assert survival["ships_surviving"] <= 3


def test_blockade_tightness_bounded():
    """Blockade tightness stays in [0, 1]."""
    tightness = update_blockade_tightness(
        china_actions={"blockade_enforcement": 1.0},
        china_forces={"surface_ships": 90, "submarines": 30, "coast_guard": 50},
        coalition_deployed={"us_surface": 0, "us_subs": 0, "japan_surface": 0, "japan_subs": 0},
    )
    assert 0.0 <= tightness <= 1.0


def test_resolve_missiles_depletes_stockpile():
    """Firing missiles reduces stockpile."""
    state = {"china_missiles": 1200, "us_missiles": 800, "taiwan_missiles": 400}
    result = resolve_missiles(
        state,
        china_actions={"missile_budget": 50, "target_priority": "military"},
        us_actions={"missile_budget": 30},
        taiwan_actions={"missile_budget": 20},
        escalation_level=2,
    )
    assert state["china_missiles"] == 1150
    assert state["us_missiles"] == 770
    assert state["taiwan_missiles"] == 380
    assert result["total_missiles_fired"] == 100


def test_homeland_strikes_at_escalation_3_aggressive():
    """Aggressive China strikes Japanese bases at escalation level 3."""
    state = {"escalation_level": 3, "japan_base_okinawa": "open",
             "japan_base_kyushu": "closed", "japan_homeland_strikes": 0,
             "japan_okinawa_strikes": 0, "japan_kyushu_strikes": 0,
             "japan_mainland_strikes": 0}
    result = check_homeland_strikes(state, china_profile="aggressive")
    assert state["japan_homeland_strikes"] > 0
    assert state["japan_base_okinawa"] == "limited"


def test_homeland_strikes_cautious_never():
    """Cautious China never strikes Japan."""
    state = {"escalation_level": 4, "japan_base_okinawa": "open",
             "japan_base_kyushu": "open", "japan_homeland_strikes": 0,
             "japan_okinawa_strikes": 0, "japan_kyushu_strikes": 0,
             "japan_mainland_strikes": 0}
    result = check_homeland_strikes(state, china_profile="cautious")
    assert state["japan_homeland_strikes"] == 0


def test_missile_budget_clamped_to_stockpile():
    """Cannot fire more missiles than remaining stockpile."""
    state = {"china_missiles": 10, "us_missiles": 5, "taiwan_missiles": 0}
    result = resolve_missiles(
        state,
        china_actions={"missile_budget": 50, "target_priority": "military"},
        us_actions={"missile_budget": 30},
        taiwan_actions={"missile_budget": 0},
        escalation_level=2,
    )
    assert state["china_missiles"] == 0
    assert state["us_missiles"] == 0
    assert result["total_missiles_fired"] == 15


def test_japan_posture_modifier_applied():
    """Self-defense-only posture reduces Japan's effective force."""
    state = {
        "us_surface_ships": 0, "us_submarines": 0,
        "japan_surface_ships": 20, "japan_submarines": 6,
        "taiwan_surface_ships": 0,
        "china_surface_ships": 60, "china_submarines": 20,
    }
    defensive_actions = _make_coalition_actions(japan_posture="defensive")
    sdo_actions = _make_coalition_actions(japan_posture="self_defense_only")
    china_actions = {"surface_deploy": 0.8, "submarine_patrol": 0.6}
    rng1 = np.random.RandomState(42)
    rng2 = np.random.RandomState(42)

    r_def = resolve_naval(state, defensive_actions, china_actions, rng1)
    r_sdo = resolve_naval(state, sdo_actions, china_actions, rng2)
    assert r_sdo["japan_losses"] >= r_def["japan_losses"]


def _make_coalition_actions(japan_posture="defensive"):
    return {
        "us": {"surface_deploy": 0, "submarine_deploy": 0, "convoy_escort_commit": 0},
        "japan": {"surface_deploy": 0.5, "submarine_deploy": 0.5,
                  "engagement_posture": japan_posture, "asw_priority": 0.5,
                  "convoy_escort_commit": 0.3},
        "taiwan": {"surface_deploy": 0},
    }
