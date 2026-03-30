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
_ECONOMY_THRESHOLDS = [75, 50, 25]
_ELECTRICITY_THRESHOLDS = [75, 50, 25]
_MERCHANT_THRESHOLDS = [5, 10, 15]
_OPINION_THRESHOLDS = [0.3, 0.6, -0.3, -0.6]
_ASW_THRESHOLDS = [5, 10]

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
            _check_economy(events, state, prev_state, week)
            _check_electricity(events, state, prev_state, week)
            _check_energy(events, state, prev_state, week)
            _check_merchant(events, state, prev_state, week)
            _check_world_opinion(events, state, prev_state, week)
            _check_asw(events, state, prev_state, week)
            _check_article9(events, state, prev_state, week)
            _check_first_strike(events, state, prev_state, week)
            _check_blockade_broken(events, state, prev_state, week)
            _check_missile_defense(events, state, prev_state, week)
            _check_mainland_strikes(events, state, prev_state, week)

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


def _check_economy(events, state, prev_state, week):
    cur = state.get("taiwan_economy_pct", 100)
    prev = prev_state.get("taiwan_economy_pct", 100)
    for threshold in _ECONOMY_THRESHOLDS:
        if prev >= threshold > cur:
            events.append({
                "week": week,
                "category": "ECONOMY",
                "label": f"TW economy below {threshold}%",
                "color": "#f39c12",
            })


def _check_electricity(events, state, prev_state, week):
    cur = state.get("taiwan_electricity_pct", 100)
    prev = prev_state.get("taiwan_electricity_pct", 100)
    for threshold in _ELECTRICITY_THRESHOLDS:
        if prev >= threshold > cur:
            events.append({
                "week": week,
                "category": "ENERGY",
                "label": f"TW electricity below {threshold}%",
                "color": "#e67e22",
            })


def _check_energy(events, state, prev_state, week):
    # Gas critical (< 2 days)
    cur_gas = state.get("taiwan_energy_gas", 10)
    prev_gas = prev_state.get("taiwan_energy_gas", 10)
    if prev_gas >= 2 > cur_gas:
        events.append({
            "week": week,
            "category": "ENERGY",
            "label": f"Gas critical ({cur_gas:.1f} days)",
            "color": "#e67e22",
        })
    # Oil critical (< 5 weeks)
    cur_oil = state.get("taiwan_energy_oil", 20)
    prev_oil = prev_state.get("taiwan_energy_oil", 20)
    if prev_oil >= 5 > cur_oil:
        events.append({
            "week": week,
            "category": "ENERGY",
            "label": f"Oil critical ({cur_oil:.1f} weeks)",
            "color": "#e67e22",
        })


def _check_merchant(events, state, prev_state, week):
    cur = state.get("merchant_ships_lost", 0)
    prev = prev_state.get("merchant_ships_lost", 0)
    for threshold in _MERCHANT_THRESHOLDS:
        if prev < threshold <= cur:
            events.append({
                "week": week,
                "category": "CONVOY",
                "label": f"{cur} merchant ships lost",
                "color": "#f39c12",
            })


def _check_world_opinion(events, state, prev_state, week):
    cur = state.get("world_opinion", 0.0)
    prev = prev_state.get("world_opinion", 0.0)
    for threshold in _OPINION_THRESHOLDS:
        if threshold > 0 and prev < threshold <= cur:
            events.append({
                "week": week,
                "category": "OPINION",
                "label": f"World opinion pro-coalition ({cur:+.2f})",
                "color": "#2ecc71",
            })
        elif threshold < 0 and prev > threshold >= cur:
            events.append({
                "week": week,
                "category": "OPINION",
                "label": f"World opinion pro-China ({cur:+.2f})",
                "color": "#e74c3c",
            })


def _check_asw(events, state, prev_state, week):
    cur = state.get("china_subs_neutralized_by_jmsdf", 0)
    prev = prev_state.get("china_subs_neutralized_by_jmsdf", 0)
    for threshold in _ASW_THRESHOLDS:
        if prev < threshold <= cur:
            events.append({
                "week": week,
                "category": "ASW",
                "label": f"JMSDF neutralized {cur} CN subs",
                "color": "#3498db",
            })


def _check_article9(events, state, prev_state, week):
    cur = state.get("japan_article9_violations", 0)
    prev = prev_state.get("japan_article9_violations", 0)
    if cur > prev:
        events.append({
            "week": week,
            "category": "LEGAL",
            "label": f"Article 9 violation (#{cur})",
            "color": "#9b59b6",
        })


def _check_first_strike(events, state, prev_state, week):
    cur = state.get("japan_first_strike", False)
    prev = prev_state.get("japan_first_strike", False)
    if cur and not prev:
        events.append({
            "week": week,
            "category": "LEGAL",
            "label": "Japan first strike",
            "color": "#9b59b6",
        })


def _check_blockade_broken(events, state, prev_state, week):
    cur = state.get("blockade_tightness", 0.0)
    prev = prev_state.get("blockade_tightness", 0.0)
    for threshold, label in _BLOCKADE_THRESHOLDS:
        if prev >= threshold > cur:
            events.append({
                "week": week,
                "category": "BLOCKADE",
                "label": f"Blockade eased below {int(threshold*100)}%",
                "color": "#27ae60",
            })


def _check_missile_defense(events, state, prev_state, week):
    cur = state.get("us_japan_missile_defense", False)
    prev = prev_state.get("us_japan_missile_defense", False)
    if cur and not prev:
        events.append({
            "week": week,
            "category": "DEFENSE",
            "label": "US missile defense activated",
            "color": "#2980b9",
        })
    elif not cur and prev:
        events.append({
            "week": week,
            "category": "DEFENSE",
            "label": "US missile defense withdrawn",
            "color": "#e74c3c",
        })


def _check_mainland_strikes(events, state, prev_state, week):
    cur = state.get("japan_mainland_strikes", 0)
    prev = prev_state.get("japan_mainland_strikes", 0)
    if cur > prev:
        events.append({
            "week": week,
            "category": "STRIKE",
            "label": f"Mainland struck (x{cur})",
            "color": "#c0392b",
        })
