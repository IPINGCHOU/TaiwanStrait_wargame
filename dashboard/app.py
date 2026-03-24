"""Streamlit dashboard for the Taiwan Strait blockade wargame."""

import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st

from dotenv import load_dotenv, set_key

load_dotenv()

from wargame.scenarios import EVALUATION_SCENARIOS
from shinka_task.initial import japan_strategy as baseline_strategy
from dashboard.replay import run_game_and_record, replay_widget
from dashboard.analysis import (
    score_breakdown_table, action_heatmap, strategy_comparison,
    scenario_explorer_sidebar,
)

st.set_page_config(page_title="Taiwan Strait Wargame", layout="wide")
st.title("Taiwan Strait Blockade — Wargame Dashboard")

# ─── Sidebar: API Key ────────────────────────────────────────────────────
st.sidebar.markdown("### API Configuration")
_current_key = os.getenv("DEEPSEEK_API_KEY", "")
_api_key = st.sidebar.text_input("DeepSeek API Key", value=_current_key, type="password")
if st.sidebar.button("Save API Key"):
    _env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")
    set_key(_env_path, "DEEPSEEK_API_KEY", _api_key)
    os.environ["DEEPSEEK_API_KEY"] = _api_key
    st.sidebar.success("Saved to .env")
st.sidebar.markdown("---")

tab1, tab2, tab3 = st.tabs(["Game Replay", "Strategy Analysis", "Scenario Explorer"])


# ─── Tab 1: Game Replay ───────────────────────────────────────────────────

with tab1:
    st.markdown("### Game Replay")

    col_scenario, col_seed = st.columns(2)
    with col_scenario:
        scenario_names = [s["name"] for s in EVALUATION_SCENARIOS]
        scenario_idx = st.selectbox("Scenario", range(len(scenario_names)),
                                     format_func=lambda i: scenario_names[i],
                                     key="replay_scenario")
    with col_seed:
        seed = st.number_input("Seed", 0, 100, 0, key="replay_seed")

    scenario = EVALUATION_SCENARIOS[scenario_idx]

    if st.button("Run Game", key="run_replay"):
        with st.spinner("Running simulation..."):
            history, result = run_game_and_record(scenario, baseline_strategy, seed)
            st.session_state["replay_history"] = history
            st.session_state["replay_result"] = result

    if "replay_history" in st.session_state:
        replay_widget(st.session_state["replay_history"],
                      st.session_state["replay_result"])


# ─── Tab 2: Strategy Analysis ─────────────────────────────────────────────

with tab2:
    st.markdown("### Strategy Analysis")

    if "replay_result" in st.session_state:
        result = st.session_state["replay_result"]
        score_breakdown_table(result)
        st.markdown("---")
        action_heatmap(st.session_state.get("replay_history", []))
    else:
        st.info("Run a game in the Replay tab first to see analysis.")


# ─── Tab 3: Scenario Explorer ─────────────────────────────────────────────

with tab3:
    st.markdown("### Scenario Explorer")

    custom_scenario = scenario_explorer_sidebar()
    explorer_seed = st.number_input("Seed", 0, 100, 0, key="explorer_seed")

    if st.button("Run Custom Scenario", key="run_explorer"):
        with st.spinner("Running simulation..."):
            history, result = run_game_and_record(
                custom_scenario, baseline_strategy, explorer_seed
            )
            st.session_state["explorer_history"] = history
            st.session_state["explorer_result"] = result

    if "explorer_history" in st.session_state:
        replay_widget(st.session_state["explorer_history"],
                      st.session_state["explorer_result"],
                      key_prefix="explorer")
        st.markdown("---")
        score_breakdown_table(st.session_state["explorer_result"])
