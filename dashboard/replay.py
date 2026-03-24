"""Turn-by-turn game replay with Folium map and action log."""

import streamlit as st
from streamlit_folium import st_folium

from wargame.engine import WarGame
from dashboard.map_view import render_map


def run_game_and_record(scenario, japan_strategy_fn, seed=0):
    """Run a full game and record per-turn state + all players' actions.

    Returns:
        history: list of dicts with "state" and "all_actions" keys
        result: game result dict
    """
    game = WarGame(scenario=scenario, seed=seed)
    history = []

    while not game.is_done():
        state = game.get_state()
        actions = japan_strategy_fn(state)
        game.step(actions)
        # Grab the full action set recorded by the engine
        history.append({
            "state": state,
            "all_actions": game.turn_actions[-1],
        })

    # Append final state (no actions)
    final_state = game.get_state()
    history.append({"state": final_state, "all_actions": None})

    return history, game.get_result()


def replay_widget(history, result, key_prefix="replay"):
    """Streamlit widget: Folium map + action log + side panels + week slider."""
    max_week = len(history) - 1

    # Slider state — use session_state so we can place the slider widget below
    if f"{key_prefix}_week_val" not in st.session_state:
        st.session_state[f"{key_prefix}_week_val"] = 0
    week_idx = st.session_state[f"{key_prefix}_week_val"]
    week_idx = min(week_idx, max_week)

    entry = history[week_idx]
    state = entry["state"]
    all_actions = entry.get("all_actions")

    # Row 0: Header
    st.markdown(
        f"### Week {state.get('week', 1)} — "
        f"Escalation Level {state.get('escalation_level', 0)}"
    )

    # Row 1: Map + Action Log
    col_map, col_actions = st.columns([2, 1])

    with col_map:
        m = render_map(state, all_actions)
        st_folium(m, width=None, height=500, key=f"{key_prefix}_map_{week_idx}")

    with col_actions:
        _render_action_log(all_actions, state.get("week", 1))

    # Row 2: Energy / Forces / Status panels
    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown("**Energy**")
        gas = state.get("taiwan_energy_gas", 0)
        coal = state.get("taiwan_energy_coal", 0)
        oil = state.get("taiwan_energy_oil", 0)
        st.progress(min(gas / 10.0, 1.0), text=f"Gas: {gas:.1f} days")
        st.progress(min(coal / 7.0, 1.0), text=f"Coal: {coal:.1f} weeks")
        st.progress(min(oil / 20.0, 1.0), text=f"Oil: {oil:.1f} weeks")
        st.metric("Electricity", f"{state.get('taiwan_electricity_pct', 100):.0f}%")
        st.metric("Economy", f"{state.get('taiwan_economy_pct', 100):.0f}%")

    with col2:
        st.markdown("**Forces**")
        forces = {
            "PLAN Surface": state.get("china_surface_ships", 0),
            "PLAN Subs": state.get("china_submarines", 0),
            "USN Surface": state.get("us_surface_ships", 0),
            "USN Subs": state.get("us_submarines", 0),
            "JMSDF Surface": state.get("japan_surface_ships", 0),
            "JMSDF Subs": state.get("japan_submarines", 0),
            "ROC Navy": state.get("taiwan_surface_ships", 0),
        }
        for name, count in forces.items():
            st.text(f"{name}: {count}")

    with col3:
        st.markdown("**Status**")
        st.metric("Escalation", state.get("escalation_level", 0))
        st.metric("Blockade", f"{state.get('blockade_tightness', 0):.0%}")
        st.metric("TW Morale", f"{state.get('taiwan_morale', 0.8):.2f}")
        st.metric("World Opinion", f"{state.get('world_opinion', 0):.2f}")

        okinawa = state.get("japan_base_okinawa", "closed")
        kyushu = state.get("japan_base_kyushu", "closed")
        st.text(f"Okinawa: {okinawa.upper()}")
        st.text(f"Kyushu: {kyushu.upper()}")

    # Row 3: Week slider (below panels per spec layout)
    st.slider(
        "Week", 0, max_week, week_idx,
        key=f"{key_prefix}_week",
        on_change=lambda: st.session_state.update(
            {f"{key_prefix}_week_val": st.session_state[f"{key_prefix}_week"]}
        ),
    )

    # Row 4: Game result summary on final week
    if week_idx == max_week:
        survived = result["taiwan_survived"]
        score = result["score"]["total"]
        if survived:
            st.success(f"Taiwan Survived — Score: {score:.0f}")
        else:
            st.error(f"Taiwan Surrendered at Week {result['weeks']} — Score: {score:.0f}")


def _render_action_log(all_actions, week):
    """Render the 4-nation action log in a chat-like column."""
    st.markdown(f"**Week {week} Actions**")

    if all_actions is None:
        st.caption("No actions this turn")
        return

    nations = [
        ("China", "cn", "china"),
        ("US", "us", "us"),
        ("Japan", "jp", "japan"),
        ("Taiwan", "tw", "taiwan"),
    ]
    for label, flag, key in nations:
        actions = all_actions.get(key, {})
        with st.expander(f":flag-{flag}: {label}", expanded=True):
            for k, v in sorted(actions.items()):
                if isinstance(v, float):
                    st.text(f"{k}: {v:.2f}")
                else:
                    st.text(f"{k}: {v}")
