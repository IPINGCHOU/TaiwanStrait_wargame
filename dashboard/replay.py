"""Turn-by-turn game replay with Folium map and action log."""

import streamlit as st
from streamlit_folium import st_folium
import plotly.graph_objects as go

from wargame.engine import WarGame
from dashboard.map_view import render_map
from dashboard.events import detect_events


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


# Nation config: (label, flag, key, border_color)
_NATIONS = [
    ("China", "cn", "china", "#e74c3c"),
    ("Taiwan", "tw", "taiwan", "#27ae60"),
    ("US", "us", "us", "#2980b9"),
    ("Japan", "jp", "japan", "#3498db"),
]


def replay_widget(history, result, key_prefix="replay"):
    """Streamlit widget: action cards + map/status + timeline."""
    max_week = len(history) - 1

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

    # Row 1: Horizontal action cards
    _render_action_cards(all_actions, state.get("week", 1))

    # Row 2: Map + Status sidebar
    col_map, col_status = st.columns([2, 1])

    with col_map:
        m = render_map(state, all_actions)
        st_folium(m, width=None, height=500, key=f"{key_prefix}_map_{week_idx}")

    with col_status:
        _render_status_sidebar(state)

    # Row 3: Timeline with event markers + event log
    events = detect_events(history, result=result)

    # Plotly scatter strip for event markers
    if events:
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=[e["week"] for e in events],
            y=[0] * len(events),
            mode="markers",
            marker=dict(
                size=10,
                color=[e["color"] for e in events],
            ),
            text=[f"{e['category']}: {e['label']}" for e in events],
            hoverinfo="text",
            showlegend=False,
        ))
        fig.update_layout(
            height=50,
            margin=dict(l=0, r=0, t=0, b=0),
            xaxis=dict(range=[0, max_week], showticklabels=False, showgrid=False),
            yaxis=dict(visible=False, range=[-0.5, 0.5]),
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
        )
        st.plotly_chart(fig, width="stretch", key=f"{key_prefix}_events")

    # Week slider
    st.slider(
        "Week", 0, max_week, week_idx,
        key=f"{key_prefix}_week",
        on_change=lambda: st.session_state.update(
            {f"{key_prefix}_week_val": st.session_state[f"{key_prefix}_week"]}
        ),
    )

    # Event log
    if events:
        with st.container(height=150):
            for e in events:
                if e["week"] < week_idx + 1:
                    opacity = "1.0"
                    weight = "normal"
                elif e["week"] == week_idx + 1:
                    opacity = "1.0"
                    weight = "bold"
                else:
                    opacity = "0.4"
                    weight = "normal"
                bg = "background:rgba(41,128,185,0.15);" if e["week"] == week_idx + 1 else ""
                st.markdown(
                    f'<div style="opacity:{opacity}; font-weight:{weight}; font-size:13px; margin-bottom:2px; {bg} padding:2px 4px; border-radius:4px">'
                    f'<span style="color:{e["color"]}; font-weight:bold; min-width:30px; display:inline-block">W{e["week"]}</span> '
                    f'<span style="background:{e["color"]}33; color:{e["color"]}; padding:1px 6px; border-radius:4px; font-size:11px">{e["category"]}</span> '
                    f'{e["label"]}'
                    f'</div>',
                    unsafe_allow_html=True,
                )

    # Row 4: Game result on final week
    if week_idx == max_week:
        survived = result["taiwan_survived"]
        score = result["score"]["total"]
        if survived:
            st.success(f"Taiwan Survived — Score: {score:.0f}")
        else:
            st.error(f"Taiwan Surrendered at Week {result['weeks']} — Score: {score:.0f}")


def _render_action_cards(all_actions, week):
    """Render 4 horizontal action cards in st.columns(4)."""
    cols = st.columns(4)
    for col, (label, flag, key, color) in zip(cols, _NATIONS):
        with col:
            st.markdown(
                f'<div style="border-left:3px solid {color}; padding-left:8px">'
                f'<strong>:flag-{flag}: {label}</strong></div>',
                unsafe_allow_html=True,
            )
            if all_actions is None:
                st.caption("No actions")
                continue
            actions = all_actions.get(key, {})
            for k, v in sorted(actions.items()):
                if isinstance(v, float):
                    st.text(f"{k}: {v:.2f}")
                else:
                    st.text(f"{k}: {v}")


def _render_status_sidebar(state):
    """Render Energy / Forces / Status panels stacked vertically."""
    # Energy
    st.markdown("**Energy**")
    gas = state.get("taiwan_energy_gas", 0)
    coal = state.get("taiwan_energy_coal", 0)
    oil = state.get("taiwan_energy_oil", 0)
    st.progress(min(gas / 10.0, 1.0), text=f"Gas: {gas:.1f} days")
    st.progress(min(coal / 7.0, 1.0), text=f"Coal: {coal:.1f} weeks")
    st.progress(min(oil / 20.0, 1.0), text=f"Oil: {oil:.1f} weeks")
    st.text(f"Electricity: {state.get('taiwan_electricity_pct', 100):.0f}%")
    st.text(f"Economy: {state.get('taiwan_economy_pct', 100):.0f}%")

    # Forces
    st.markdown("---")
    st.markdown("**Forces**")
    forces = [
        ("PLAN Surface", "china_surface_ships", "#e74c3c"),
        ("PLAN Subs", "china_submarines", "#e74c3c"),
        ("USN Surface", "us_surface_ships", "#2980b9"),
        ("USN Subs", "us_submarines", "#2980b9"),
        ("JMSDF Surface", "japan_surface_ships", "#3498db"),
        ("JMSDF Subs", "japan_submarines", "#3498db"),
        ("ROC Navy", "taiwan_surface_ships", "#27ae60"),
    ]
    for name, key, _color in forces:
        st.text(f"{name}: {state.get(key, 0)}")

    # Status
    st.markdown("---")
    st.markdown("**Status**")
    st.text(f"Escalation: {state.get('escalation_level', 0)}")
    st.text(f"Blockade: {state.get('blockade_tightness', 0):.0%}")
    st.text(f"TW Morale: {state.get('taiwan_morale', 0.8):.2f}")
    st.text(f"World Opinion: {state.get('world_opinion', 0):.2f}")
    okinawa = state.get("japan_base_okinawa", "closed")
    kyushu = state.get("japan_base_kyushu", "closed")
    st.text(f"Okinawa: {okinawa.upper()}")
    st.text(f"Kyushu: {kyushu.upper()}")
