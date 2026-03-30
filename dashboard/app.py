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
from dashboard.versions import discover_versions, load_strategy
from dashboard.map_view import render_map
from streamlit_folium import st_folium

st.set_page_config(page_title="Taiwan Strait Wargame", layout="wide")
st.title("Taiwan Strait Blockade — Wargame Dashboard")

# ─── Sidebar: API Keys ───────────────────────────────────────────────────
st.sidebar.markdown("### API Configuration")
_env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")

_ds_key = os.getenv("DEEPSEEK_API_KEY", "")
_ds_input = st.sidebar.text_input("DeepSeek API Key (LLM)", value=_ds_key, type="password")

_oai_key = os.getenv("OPENAI_API_KEY", "")
_oai_input = st.sidebar.text_input("OpenAI API Key (embeddings)", value=_oai_key, type="password")

if st.sidebar.button("Save API Keys"):
    set_key(_env_path, "DEEPSEEK_API_KEY", _ds_input)
    set_key(_env_path, "OPENAI_API_KEY", _oai_input)
    os.environ["DEEPSEEK_API_KEY"] = _ds_input
    os.environ["OPENAI_API_KEY"] = _oai_input
    st.sidebar.success("Saved to .env")
st.sidebar.markdown("---")

scenario_names = [s["name"] for s in EVALUATION_SCENARIOS]

tab1, tab2, tab3, tab4 = st.tabs(
    ["Game Replay", "Strategy Analysis", "Scenario Explorer", "Compare"]
)


# ─── Tab 1: Game Replay ───────────────────────────────────────────────────

with tab1:
    st.markdown("### Game Replay")

    col_scenario, col_seed = st.columns(2)
    with col_scenario:
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


# ─── Tab 4: Compare ──────────────────────────────────────────────────────

with tab4:
    st.markdown("### Compare Strategies")

    _project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    _show_all = st.checkbox("Show all generations", value=False, key="compare_show_all")
    versions = discover_versions(_project_root, show_all=_show_all)
    version_names = [v["name"] for v in versions]

    if not version_names:
        st.warning("No strategy versions found in results/")
    else:
        # Version pickers
        col_left, col_vs, col_right = st.columns([5, 1, 5])
        with col_left:
            left_idx = st.selectbox("Left version", range(len(version_names)),
                                     format_func=lambda i: version_names[i],
                                     key="compare_left")
        with col_vs:
            st.markdown("<div style='text-align:center; padding-top:28px; font-size:18px; color:#888'>vs</div>",
                        unsafe_allow_html=True)
        with col_right:
            right_default = min(len(version_names) - 1, 1)
            right_idx = st.selectbox("Right version", range(len(version_names)),
                                      format_func=lambda i: version_names[i],
                                      index=right_default,
                                      key="compare_right")

        # Scenario + Seed + Run
        col_sc, col_seed, col_run = st.columns([4, 2, 2])
        with col_sc:
            cmp_scenario_idx = st.selectbox(
                "Scenario", range(len(scenario_names)),
                format_func=lambda i: scenario_names[i],
                key="compare_scenario",
            )
        with col_seed:
            cmp_seed = st.number_input("Seed", 0, 100, 0, key="compare_seed")
        with col_run:
            st.markdown("<div style='padding-top:28px'></div>", unsafe_allow_html=True)
            run_clicked = st.button("Run Both", key="run_compare")

        # Load strategies and run
        if run_clicked:
            left_fn = load_strategy(versions[left_idx]["path"])
            right_fn = load_strategy(versions[right_idx]["path"])

            if left_fn is None:
                st.error(f"Failed to load: {versions[left_idx]['name']}")
            elif right_fn is None:
                st.error(f"Failed to load: {versions[right_idx]['name']}")
            else:
                cmp_scenario = EVALUATION_SCENARIOS[cmp_scenario_idx]
                with st.spinner("Running left strategy..."):
                    lh, lr = run_game_and_record(cmp_scenario, left_fn, cmp_seed)
                with st.spinner("Running right strategy..."):
                    rh, rr = run_game_and_record(cmp_scenario, right_fn, cmp_seed)
                st.session_state["compare_left_history"] = lh
                st.session_state["compare_left_result"] = lr
                st.session_state["compare_right_history"] = rh
                st.session_state["compare_right_result"] = rr
                st.session_state["compare_left_name"] = versions[left_idx]["name"]
                st.session_state["compare_right_name"] = versions[right_idx]["name"]

        # Display results
        if "compare_left_history" in st.session_state:
            lh = st.session_state["compare_left_history"]
            rh = st.session_state["compare_right_history"]
            lr = st.session_state["compare_left_result"]
            rr = st.session_state["compare_right_result"]
            l_name = st.session_state["compare_left_name"]
            r_name = st.session_state["compare_right_name"]

            cmp_max = min(len(lh), len(rh)) - 1
            if "compare_week_val" not in st.session_state:
                st.session_state["compare_week_val"] = 0
            cmp_week = min(st.session_state["compare_week_val"], cmp_max)

            # Side-by-side maps
            col_ml, col_mr = st.columns(2)
            with col_ml:
                st.markdown(f"**{l_name}** — Score: {lr['score']['total']:.0f}")
                l_state = lh[cmp_week]["state"]
                l_actions = lh[cmp_week].get("all_actions")
                m_left = render_map(l_state, l_actions)
                st_folium(m_left, width=None, height=400,
                          key=f"compare_left_map_{cmp_week}")

            with col_mr:
                st.markdown(f"**{r_name}** — Score: {rr['score']['total']:.0f}")
                r_state = rh[cmp_week]["state"]
                r_actions = rh[cmp_week].get("all_actions")
                m_right = render_map(r_state, r_actions)
                st_folium(m_right, width=None, height=400,
                          key=f"compare_right_map_{cmp_week}")

            # Synced slider
            st.slider(
                "Week", 0, cmp_max, cmp_week,
                key="compare_week",
                on_change=lambda: st.session_state.update(
                    {"compare_week_val": st.session_state["compare_week"]}
                ),
            )

            # Score breakdown
            st.markdown("---")
            st.markdown("### Score Breakdown")
            strategy_comparison([lr, rr], [l_name, r_name])
