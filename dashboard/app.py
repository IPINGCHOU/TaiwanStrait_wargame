"""Streamlit dashboard for the Taiwan Strait blockade wargame."""

import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st
from streamlit_folium import st_folium
import plotly.graph_objects as go

from dotenv import load_dotenv, set_key

load_dotenv()

from wargame.scenarios import EVALUATION_SCENARIOS
from dashboard.replay import run_game_and_record
from dashboard.analysis import strategy_comparison, scenario_explorer_sidebar
from dashboard.versions import discover_versions, load_strategy
from dashboard.map_view import render_map
from dashboard.events import detect_events

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

# ─── Sidebar: Scenario Customization ─────────────────────────────────────
custom_scenario = scenario_explorer_sidebar()

# ─── Nation config ────────────────────────────────────────────────────────
_NATIONS = [
    ("China", "cn", "china", "#e74c3c"),
    ("Taiwan", "tw", "taiwan", "#27ae60"),
    ("US", "us", "us", "#2980b9"),
    ("Japan", "jp", "japan", "#3498db"),
]

# ─── Score footnotes ──────────────────────────────────────────────────────
_SCORE_FOOTNOTES = [
    ("A. Strategic Outcome", "[-500, +200]",
     "Win: +50 base + up to +150 scaled by electricity % × morale. Lose: -200 base - 15 × remaining weeks."),
    ("B. Taiwan Survival", "[0, 200]",
     "Electricity % × 70 + Economy % × 70 + Morale × 60. Measures Taiwan's end-state health."),
    ("C. JMSDF Preservation", "[0, 150]",
     "Fraction of JMSDF surface ships, submarines, and aircraft surviving × weights."),
    ("D. Homeland Security", "[-200, +100]",
     "Safe bonus: 100 × exp(-0.7 × total_strikes). Penalties per Okinawa/Kyushu/mainland strike."),
    ("E. Economic Impact", "[-100, 0]",
     "Penalty for weeks of sea-lane disruption to Japan's trade routes."),
    ("F. Operational Success", "[0, 200]",
     "Convoy throughput via Japan + corridor recovery + ASW effectiveness + blockade reduction + China attrition."),
    ("G. Alliance Credibility", "[-100, +100]",
     "200 × avg_deploy - 100. Full deployment = +100, zero deployment = -100."),
    ("H. Escalation Mgmt", "[-200, +130]",
     "100 - 75 × avg_escalation_level. Low escalation = positive, high = deeply negative."),
    ("I. Legal/Humanitarian", "[-100, 0]",
     "Penalties for Article 9 violations, first-strike actions, and civilian casualties."),
]

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
scenario_names = [s["name"] for s in EVALUATION_SCENARIOS]

# ─── Main: Compare & Explore ─────────────────────────────────────────────

st.markdown("### Compare & Explore")

# Strategy pickers
_show_all = st.checkbox("Show all generations", value=False, key="compare_show_all")
versions = discover_versions(_PROJECT_ROOT, show_all=_show_all)
version_names = [v["name"] for v in versions]

if not version_names:
    st.warning("No strategy versions found in results/")
    st.stop()

col_left, col_vs, col_right = st.columns([5, 1, 5])
with col_left:
    left_idx = st.selectbox("Left strategy", range(len(version_names)),
                             format_func=lambda i: version_names[i],
                             key="compare_left")
with col_vs:
    st.markdown(
        "<div style='text-align:center; padding-top:28px; font-size:18px; color:#888'>vs</div>",
        unsafe_allow_html=True,
    )
with col_right:
    right_default = min(len(version_names) - 1, 1)
    right_idx = st.selectbox("Right strategy", range(len(version_names)),
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

# Use custom scenario from sidebar, or preset from dropdown
use_custom = st.checkbox("Use sidebar custom scenario", value=False, key="use_custom_scenario")

if run_clicked:
    left_fn = load_strategy(versions[left_idx]["path"])
    right_fn = load_strategy(versions[right_idx]["path"])

    if left_fn is None:
        st.error(f"Failed to load: {versions[left_idx]['name']}")
    elif right_fn is None:
        st.error(f"Failed to load: {versions[right_idx]['name']}")
    else:
        scenario = custom_scenario if use_custom else EVALUATION_SCENARIOS[cmp_scenario_idx]
        with st.spinner("Running left strategy..."):
            lh, lr = run_game_and_record(scenario, left_fn, cmp_seed)
        with st.spinner("Running right strategy..."):
            rh, rr = run_game_and_record(scenario, right_fn, cmp_seed)
        st.session_state["compare_left_history"] = lh
        st.session_state["compare_left_result"] = lr
        st.session_state["compare_right_history"] = rh
        st.session_state["compare_right_result"] = rr
        st.session_state["compare_left_name"] = versions[left_idx]["name"]
        st.session_state["compare_right_name"] = versions[right_idx]["name"]

# ─── Display Results ──────────────────────────────────────────────────────
if "compare_left_history" not in st.session_state:
    st.info("Select two strategies and click **Run Both** to compare.")
    st.stop()

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

st.markdown("---")

# ─── Side-by-side action cards ────────────────────────────────────────────
col_al, col_ar = st.columns(2)

for col_side, history, name, result, color in [
    (col_al, lh, l_name, lr, "#3498db"),
    (col_ar, rh, r_name, rr, "#27ae60"),
]:
    with col_side:
        st.markdown(f"**{name}** — Score: {result['score']['total']:.0f}")
        all_actions = history[cmp_week].get("all_actions")
        sub_cols = st.columns(4)
        for sub_col, (label, flag, key, nation_color) in zip(sub_cols, _NATIONS):
            with sub_col:
                st.markdown(
                    f'<div style="border-left:3px solid {nation_color}; padding-left:6px">'
                    f'<strong style="font-size:12px">:flag-{flag}: {label}</strong></div>',
                    unsafe_allow_html=True,
                )
                if all_actions is None:
                    st.caption("—")
                    continue
                actions = all_actions.get(key, {})
                for k, v in sorted(actions.items()):
                    if isinstance(v, float):
                        st.text(f"{k}: {v:.2f}")
                    else:
                        st.text(f"{k}: {v}")

# ─── Side-by-side map + status ────────────────────────────────────────────
col_ml, col_mr = st.columns(2)

for col_side, history, name, key_prefix in [
    (col_ml, lh, l_name, "compare_left"),
    (col_mr, rh, r_name, "compare_right"),
]:
    with col_side:
        map_col, status_col = st.columns([2, 1])
        state = history[cmp_week]["state"]
        all_actions = history[cmp_week].get("all_actions")

        with map_col:
            m = render_map(state, all_actions)
            st_folium(m, width=None, height=400, key=f"{key_prefix}_map_{cmp_week}")

        with status_col:
            with st.container(height=400):
                # Energy
                st.markdown("**Energy**")
                gas = state.get("taiwan_energy_gas", 0)
                coal = state.get("taiwan_energy_coal", 0)
                oil = state.get("taiwan_energy_oil", 0)
                st.progress(min(gas / 10.0, 1.0), text=f"Gas: {gas:.1f}d")
                st.progress(min(coal / 7.0, 1.0), text=f"Coal: {coal:.1f}w")
                st.progress(min(oil / 20.0, 1.0), text=f"Oil: {oil:.1f}w")
                st.text(f"Elec: {state.get('taiwan_electricity_pct', 100):.0f}%")
                st.text(f"Econ: {state.get('taiwan_economy_pct', 100):.0f}%")
                # Forces
                st.markdown("---")
                st.markdown("**Forces**")
                st.text(f"PLAN: {state.get('china_surface_ships', 0)}/{state.get('china_submarines', 0)}")
                st.text(f"USN: {state.get('us_surface_ships', 0)}/{state.get('us_submarines', 0)}")
                st.text(f"JMSDF: {state.get('japan_surface_ships', 0)}/{state.get('japan_submarines', 0)}")
                st.text(f"ROC: {state.get('taiwan_surface_ships', 0)}")
                # Status
                st.markdown("---")
                st.markdown("**Status**")
                st.text(f"Esc: {state.get('escalation_level', 0)}")
                st.text(f"Blockade: {state.get('blockade_tightness', 0):.0%}")
                st.text(f"Morale: {state.get('taiwan_morale', 0.8):.2f}")
                okinawa = state.get("japan_base_okinawa", "closed")
                kyushu = state.get("japan_base_kyushu", "closed")
                st.text(f"Okinawa: {okinawa.upper()}")
                st.text(f"Kyushu: {kyushu.upper()}")

# ─── Mirrored Event Timeline (merged dots + labels) ─────────────────────
l_events = detect_events(lh, result=lr)
r_events = detect_events(rh, result=rr)

if l_events or r_events:
    fig = go.Figure()

    # Center line
    fig.add_shape(
        type="line", x0=0.5, x1=cmp_max + 1.5, y0=0, y1=0,
        line=dict(color="#555", width=2),
    )

    def _stagger_y(events, base_y, step):
        """Assign y-positions to labels, staggering when weeks are close.

        base_y: starting y offset from center (positive=above, negative=below)
        step: increment per stagger level (positive=further from center)
        Returns list of y values, one per event.
        """
        y_positions = []
        for i, e in enumerate(events):
            level = 0
            # Check how many prior events are within 1 week
            for j in range(i):
                if abs(events[j]["week"] - e["week"]) <= 1:
                    level += 1
            y_positions.append(base_y + step * level)
        return y_positions

    # Compute staggered y positions
    l_ys = _stagger_y(l_events, base_y=1.5, step=1.2) if l_events else []
    r_ys = _stagger_y(r_events, base_y=-1.5, step=-1.2) if r_events else []

    # Left strategy dots on the center line (above side)
    if l_events:
        fig.add_trace(go.Scatter(
            x=[e["week"] for e in l_events],
            y=[0.3] * len(l_events),
            mode="markers",
            marker=dict(size=12, color=[e["color"] for e in l_events]),
            hovertext=[f"{l_name} W{e['week']}: {e['label']}" for e in l_events],
            hoverinfo="text",
            showlegend=False,
        ))

    # Right strategy dots on the center line (below side)
    if r_events:
        fig.add_trace(go.Scatter(
            x=[e["week"] for e in r_events],
            y=[-0.3] * len(r_events),
            mode="markers",
            marker=dict(size=12, color=[e["color"] for e in r_events]),
            hovertext=[f"{r_name} W{e['week']}: {e['label']}" for e in r_events],
            hoverinfo="text",
            showlegend=False,
        ))

    # Left labels with guide lines (above)
    for e, label_y in zip(l_events, l_ys):
        is_outcome = e["category"] == "OUTCOME"
        fig.add_annotation(
            x=e["week"], y=label_y,
            text=f"<b>{e['label']}</b>" if is_outcome else e["label"],
            showarrow=True,
            arrowhead=0, arrowwidth=1, arrowcolor=e["color"] + "66",
            ax=0, ay=0,
            xanchor="center", yanchor="bottom",
            font=dict(size=12, color=e["color"]),
        )
        # Guide line from label to dot
        fig.add_shape(
            type="line", x0=e["week"], x1=e["week"],
            y0=0.3, y1=label_y - 0.1,
            line=dict(color=e["color"] + "44", width=1),
        )

    # Right labels with guide lines (below)
    for e, label_y in zip(r_events, r_ys):
        is_outcome = e["category"] == "OUTCOME"
        fig.add_annotation(
            x=e["week"], y=label_y,
            text=f"<b>{e['label']}</b>" if is_outcome else e["label"],
            showarrow=True,
            arrowhead=0, arrowwidth=1, arrowcolor=e["color"] + "66",
            ax=0, ay=0,
            xanchor="center", yanchor="top",
            font=dict(size=12, color=e["color"]),
        )
        fig.add_shape(
            type="line", x0=e["week"], x1=e["week"],
            y0=-0.3, y1=label_y + 0.1,
            line=dict(color=e["color"] + "44", width=1),
        )

    # Current week indicator
    max_y = max([abs(y) for y in l_ys + r_ys] + [2.0]) + 0.5
    fig.add_shape(
        type="line", x0=cmp_week + 1, x1=cmp_week + 1,
        y0=-max_y, y1=max_y,
        line=dict(color="#3498db", width=2, dash="dot"),
    )
    fig.add_annotation(
        x=cmp_week + 1, y=max_y + 0.3,
        text=f"W{cmp_week + 1} (current)",
        showarrow=False, font=dict(size=12, color="#3498db"),
    )

    # Compute dynamic y range based on stagger depth
    y_range = max_y + 1.0

    fig.update_layout(
        height=max(300, int(y_range * 45)),
        margin=dict(l=10, r=10, t=10, b=10),
        yaxis=dict(
            visible=True, range=[-y_range, y_range],
            tickvals=[0.3, -0.3],
            ticktext=[f"▲ {l_name}", f"▼ {r_name}"],
            tickfont=dict(size=13),
            showgrid=False, zeroline=False,
        ),
        xaxis=dict(
            range=[0.5, cmp_max + 1.5], showgrid=False,
            tickvals=list(range(1, cmp_max + 2)),
            ticktext=[f"W{i}" for i in range(1, cmp_max + 2)],
            tickfont=dict(size=12, color="#666"),
        ),
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
    )
    st.plotly_chart(fig, use_container_width=True, key="compare_timeline")

# ─── Synced week slider ──────────────────────────────────────────────────
st.slider(
    "Week", 0, cmp_max, cmp_week,
    key="compare_week",
    on_change=lambda: st.session_state.update(
        {"compare_week_val": st.session_state["compare_week"]}
    ),
)

# ─── Score Breakdown with Footnotes ───────────────────────────────────────
st.markdown("---")
st.markdown("### Score Breakdown")
strategy_comparison([lr, rr], [l_name, r_name])

# Footnotes
with st.expander("Score category descriptions", expanded=False):
    for label, score_range, desc in _SCORE_FOOTNOTES:
        st.markdown(f"**{label}** {score_range} — {desc}")
