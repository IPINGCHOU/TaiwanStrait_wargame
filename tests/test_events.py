"""Tests for dashboard.events — event detection from game history."""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from dashboard.events import detect_events


def _make_state(**overrides):
    """Create a minimal game state dict with defaults."""
    base = {
        "week": 1,
        "escalation_level": 0,
        "blockade_tightness": 0.0,
        "japan_okinawa_strikes": 0,
        "japan_kyushu_strikes": 0,
        "japan_base_okinawa": "closed",
        "japan_base_kyushu": "closed",
        "taiwan_morale": 0.8,
        "taiwan_survived": True,
        "china_surface_ships": 60,
        "china_submarines": 20,
        "us_surface_ships": 24,
        "us_submarines": 12,
        "japan_surface_ships": 20,
        "japan_submarines": 6,
        "taiwan_surface_ships": 26,
    }
    base.update(overrides)
    return base


def _make_history(states):
    """Wrap a list of state dicts into history format."""
    return [{"state": s, "all_actions": {}} for s in states]


def test_escalation_event():
    history = _make_history([
        _make_state(week=1, escalation_level=0),
        _make_state(week=2, escalation_level=1),
    ])
    events = detect_events(history)
    esc = [e for e in events if e["category"] == "ESCALATION"]
    assert len(esc) == 1
    assert esc[0]["week"] == 2
    assert "Level 1" in esc[0]["label"]


def test_blockade_thresholds():
    history = _make_history([
        _make_state(week=1, blockade_tightness=0.0),
        _make_state(week=2, blockade_tightness=0.30),
        _make_state(week=3, blockade_tightness=0.55),
        _make_state(week=4, blockade_tightness=0.80),
    ])
    events = detect_events(history)
    blockade = [e for e in events if e["category"] == "BLOCKADE"]
    assert len(blockade) == 3
    assert blockade[0]["week"] == 2
    assert blockade[1]["week"] == 3
    assert blockade[2]["week"] == 4


def test_strike_event():
    history = _make_history([
        _make_state(week=1, japan_okinawa_strikes=0),
        _make_state(week=2, japan_okinawa_strikes=2),
    ])
    events = detect_events(history)
    strikes = [e for e in events if e["category"] == "STRIKE"]
    assert len(strikes) == 1
    assert "Okinawa" in strikes[0]["label"]


def test_forces_loss_event():
    history = _make_history([
        _make_state(week=1, china_surface_ships=60),
        _make_state(week=2, china_surface_ships=55),
    ])
    events = detect_events(history)
    forces = [e for e in events if e["category"] == "FORCES"]
    assert len(forces) == 1
    assert "PLAN Surface" in forces[0]["label"]


def test_forces_no_event_small_loss():
    history = _make_history([
        _make_state(week=1, china_surface_ships=60),
        _make_state(week=2, china_surface_ships=58),
    ])
    events = detect_events(history)
    forces = [e for e in events if e["category"] == "FORCES"]
    assert len(forces) == 0


def test_forces_boundary_exactly_3_no_event():
    """Loss of exactly 3 should NOT trigger (threshold is >3)."""
    history = _make_history([
        _make_state(week=1, china_surface_ships=60),
        _make_state(week=2, china_surface_ships=57),
    ])
    events = detect_events(history)
    forces = [e for e in events if e["category"] == "FORCES"]
    assert len(forces) == 0


def test_forces_boundary_exactly_4_triggers():
    """Loss of exactly 4 should trigger (>3)."""
    history = _make_history([
        _make_state(week=1, china_surface_ships=60),
        _make_state(week=2, china_surface_ships=56),
    ])
    events = detect_events(history)
    forces = [e for e in events if e["category"] == "FORCES"]
    assert len(forces) == 1


def test_base_change_event():
    history = _make_history([
        _make_state(week=1, japan_base_okinawa="closed"),
        _make_state(week=2, japan_base_okinawa="open"),
    ])
    events = detect_events(history)
    base = [e for e in events if e["category"] == "BASE"]
    assert len(base) == 1
    assert "Okinawa" in base[0]["label"]


def test_morale_drop_event():
    history = _make_history([
        _make_state(week=1, taiwan_morale=0.6),
        _make_state(week=2, taiwan_morale=0.45),
    ])
    events = detect_events(history)
    morale = [e for e in events if e["category"] == "MORALE"]
    assert len(morale) == 1
    assert "0.5" in morale[0]["label"] or "50%" in morale[0]["label"]


def test_outcome_event():
    history = _make_history([
        _make_state(week=1),
    ])
    history[-1]["state"]["taiwan_survived"] = True
    events = detect_events(history)
    outcome = [e for e in events if e["category"] == "OUTCOME"]
    assert len(outcome) == 1
    assert "survived" in outcome[0]["label"].lower()


def test_single_entry_history():
    history = _make_history([_make_state(week=1)])
    events = detect_events(history)
    assert all(e["category"] == "OUTCOME" for e in events)


def test_empty_history():
    events = detect_events([])
    assert events == []
