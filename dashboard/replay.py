"""Turn-by-turn game replay with state history recording."""

import copy
import streamlit as st
import matplotlib.pyplot as plt

from wargame.engine import WarGame
from dashboard.map_view import render_map


def run_game_and_record(scenario, japan_strategy_fn, seed=0):
    """Run a full game and record per-turn state + actions.

    Returns:
        state_history: list of (state_dict, actions_dict) per turn
        result: game result dict
    """
    game = WarGame(scenario=scenario, seed=seed)
    history = []

    while not game.is_done():
        state = game.get_state()
        actions = japan_strategy_fn(state)
        history.append({"state": state, "japan_actions": actions})
        game.step(actions)

    # Append final state
    final_state = game.get_state()
    history.append({"state": final_state, "japan_actions": None})

    return history, game.get_result()


def replay_widget(history, result):
    """Streamlit widget: week slider + map + side panels."""
    max_week = len(history) - 1

    week_idx = st.slider("Week", 0, max_week, 0, key="replay_week")

    entry = history[week_idx]
    state = entry["state"]
    japan_actions = entry["japan_actions"]

    # Map
    fig, ax = render_map(state)
    st.pyplot(fig)
    plt.close(fig)

    # Side panels in columns
    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown("### Energy")
        gas = state.get("taiwan_energy_gas", 0)
        coal = state.get("taiwan_energy_coal", 0)
        oil = state.get("taiwan_energy_oil", 0)
        st.progress(min(gas / 10.0, 1.0), text=f"Gas: {gas:.1f} days")
        st.progress(min(coal / 7.0, 1.0), text=f"Coal: {coal:.1f} weeks")
        st.progress(min(oil / 20.0, 1.0), text=f"Oil: {oil:.1f} weeks")
        st.metric("Electricity", f"{state.get('taiwan_electricity_pct', 100):.0f}%")
        st.metric("Economy", f"{state.get('taiwan_economy_pct', 100):.0f}%")

    with col2:
        st.markdown("### Forces")
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
        st.markdown("### Status")
        st.metric("Escalation", state.get("escalation_level", 0))
        st.metric("Blockade", f"{state.get('blockade_tightness', 0):.0%}")
        st.metric("TW Morale", f"{state.get('taiwan_morale', 0.8):.2f}")
        st.metric("World Opinion", f"{state.get('world_opinion', 0):.2f}")

        okinawa = state.get("japan_base_okinawa", "closed")
        kyushu = state.get("japan_base_kyushu", "closed")
        st.text(f"Okinawa: {okinawa.upper()}")
        st.text(f"Kyushu: {kyushu.upper()}")

    # Japan actions for this turn
    if japan_actions:
        with st.expander("Japan's Actions This Turn", expanded=False):
            for k, v in sorted(japan_actions.items()):
                st.text(f"  {k}: {v}")

    # Game result summary
    if week_idx == max_week:
        survived = result["taiwan_survived"]
        score = result["score"]["total"]
        if survived:
            st.success(f"Taiwan Survived — Score: {score:.0f}")
        else:
            st.error(f"Taiwan Surrendered at Week {result['weeks']} — Score: {score:.0f}")
