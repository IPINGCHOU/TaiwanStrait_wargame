"""Event detection from game history for the timeline widget."""

_FLEET_KEYS = [
    ("china_surface_ships", "PLAN Surface"),
    ("china_submarines", "PLAN Submarines"),
    ("us_surface_ships", "USN Surface"),
    ("us_submarines", "USN Submarines"),
    ("japan_surface_ships", "JMSDF Surface"),
    ("japan_submarines", "JMSDF Submarines"),
    ("taiwan_surface_ships", "ROC Navy"),
]

_BLOCKADE_THRESHOLDS = [
    (0.25, "Blockade initiated"),
    (0.50, "Blockade tightening"),
    (0.75, "Blockade severe"),
]

_MORALE_THRESHOLDS = [0.5, 0.3]

_FORCE_LOSS_THRESHOLD = 3


def detect_events(history, result=None):
    """Scan game history and return a list of significant event dicts.

    Args:
        history: list of {"state": dict, "all_actions": dict} entries
        result: game result dict (from WarGame.get_result()) — used for
                taiwan_survived which is NOT stored in state dicts.
    """
    if not history:
        return []

    events = []

    for i, entry in enumerate(history):
        state = entry["state"]
        week = state.get("week", i + 1)

        if i == 0:
            prev_state = None
        else:
            prev_state = history[i - 1]["state"]

        if prev_state is not None:
            _check_escalation(events, state, prev_state, week)
            _check_strikes(events, state, prev_state, week)
            _check_blockade(events, state, prev_state, week)
            _check_forces(events, state, prev_state, week)
            _check_base(events, state, prev_state, week)
            _check_morale(events, state, prev_state, week)

        if i == len(history) - 1:
            if result is not None:
                survived = result.get("taiwan_survived", True)
                # Use result["weeks"] for accurate week (state["week"] is
                # incremented past the last played week after game ends)
                outcome_week = result.get("weeks", week)
            else:
                survived = state.get("taiwan_survived", True)
                outcome_week = week
            label = "Taiwan survived" if survived else "Taiwan surrendered"
            events.append({
                "week": outcome_week,
                "category": "OUTCOME",
                "label": label,
                "color": "#9b59b6",
            })

    return events


def _check_escalation(events, state, prev_state, week):
    cur = state.get("escalation_level", 0)
    prev = prev_state.get("escalation_level", 0)
    if cur > prev:
        events.append({
            "week": week,
            "category": "ESCALATION",
            "label": f"Escalation → Level {cur}",
            "color": "#f39c12",
        })
    elif cur < prev:
        events.append({
            "week": week,
            "category": "ESCALATION",
            "label": f"De-escalation → Level {cur}",
            "color": "#f39c12",
        })


def _check_strikes(events, state, prev_state, week):
    for key, base_name in [("japan_okinawa_strikes", "Okinawa"),
                            ("japan_kyushu_strikes", "Kyushu")]:
        cur = state.get(key, 0)
        prev = prev_state.get(key, 0)
        if cur > prev:
            events.append({
                "week": week,
                "category": "STRIKE",
                "label": f"{base_name} struck (x{cur})",
                "color": "#e74c3c",
            })


def _check_blockade(events, state, prev_state, week):
    cur = state.get("blockade_tightness", 0.0)
    prev = prev_state.get("blockade_tightness", 0.0)
    for threshold, label in _BLOCKADE_THRESHOLDS:
        if prev < threshold <= cur:
            events.append({
                "week": week,
                "category": "BLOCKADE",
                "label": label,
                "color": "#e74c3c",
            })


def _check_forces(events, state, prev_state, week):
    for key, label in _FLEET_KEYS:
        cur = state.get(key, 0)
        prev = prev_state.get(key, 0)
        loss = prev - cur
        if loss > _FORCE_LOSS_THRESHOLD:
            events.append({
                "week": week,
                "category": "FORCES",
                "label": f"{label} lost {loss} ships",
                "color": "#e74c3c",
            })


def _check_base(events, state, prev_state, week):
    for key, base_name in [("japan_base_okinawa", "Okinawa"),
                            ("japan_base_kyushu", "Kyushu")]:
        cur = state.get(key, "closed")
        prev = prev_state.get(key, "closed")
        if cur != prev:
            events.append({
                "week": week,
                "category": "BASE",
                "label": f"{base_name} → {cur}",
                "color": "#27ae60",
            })


def _check_morale(events, state, prev_state, week):
    cur = state.get("taiwan_morale", 0.8)
    prev = prev_state.get("taiwan_morale", 0.8)
    for threshold in _MORALE_THRESHOLDS:
        if prev >= threshold > cur:
            events.append({
                "week": week,
                "category": "MORALE",
                "label": f"TW morale below {threshold}",
                "color": "#f39c12",
            })
