"""Strategy analysis — score breakdowns, action heatmaps, comparison."""

import streamlit as st
import numpy as np
import plotly.graph_objects as go
import plotly.express as px


def score_breakdown_table(result):
    """Render the 9 scoring categories as a colored table."""
    score = result["score"]
    categories = [
        ("A. Strategic Outcome", "A_outcome", -580, 500),
        ("B. Taiwan Survival", "B_taiwan_survival", 0, 200),
        ("C. JMSDF Preservation", "C_jmsdf_preservation", 0, 150),
        ("D. Homeland Security", "D_homeland_security", -410, 200),
        ("E. Economic Impact", "E_economic_impact", -150, 0),
        ("F. Operational Success", "F_operational_success", 0, 150),
        ("G. Alliance Credibility", "G_alliance_credibility", -50, 100),
        ("H. Escalation Mgmt", "H_escalation_mgmt", -250, 80),
        ("I. Legal/Humanitarian", "I_legal_humanitarian", -100, 0),
    ]

    st.markdown(f"### Total Score: **{score['total']:.0f}**")

    for label, key, min_val, max_val in categories:
        val = score.get(key, 0)
        range_size = max_val - min_val
        if range_size > 0:
            normalized = (val - min_val) / range_size
        else:
            normalized = 0.5
        normalized = max(0.0, min(1.0, normalized))

        # Color: red for negative, green for positive
        if val >= 0:
            color = f"rgb({int(100 - normalized * 100)}, {int(normalized * 200)}, 50)"
        else:
            color = f"rgb({int((1 - normalized) * 200)}, {int(normalized * 100)}, 50)"

        col1, col2 = st.columns([3, 1])
        with col1:
            st.progress(normalized, text=f"{label}: {val:+.0f}")
        with col2:
            st.text(f"[{min_val}, {max_val}]")


def action_heatmap(history):
    """Heatmap of Japan's actions across 20 weeks."""
    if not history:
        st.warning("No history to display")
        return

    # Extract numeric actions only
    numeric_keys = []
    first_actions = (history[0].get("all_actions") or {}).get("japan", {})
    if first_actions:
        numeric_keys = [k for k, v in first_actions.items() if isinstance(v, (int, float))]

    if not numeric_keys:
        st.warning("No numeric actions to display")
        return

    weeks = []
    data = {k: [] for k in numeric_keys}
    for i, entry in enumerate(history):
        actions = (entry.get("all_actions") or {}).get("japan")
        if actions is None:
            continue
        weeks.append(i + 1)
        for k in numeric_keys:
            data[k].append(float(actions.get(k, 0)))

    z = [data[k] for k in numeric_keys]

    fig = go.Figure(data=go.Heatmap(
        z=z,
        x=[f"W{w}" for w in weeks],
        y=numeric_keys,
        colorscale="RdYlGn",
        zmin=0, zmax=1,
    ))
    fig.update_layout(
        title="Japan Actions Over Time",
        xaxis_title="Week",
        yaxis_title="Action",
        height=400,
    )
    st.plotly_chart(fig, width="stretch")


def strategy_comparison(results_list, labels):
    """Compare 2-3 strategies' score breakdowns side by side."""
    if not results_list:
        return

    categories = [
        "A_outcome", "B_taiwan_survival", "C_jmsdf_preservation",
        "D_homeland_security", "E_economic_impact", "F_operational_success",
        "G_alliance_credibility", "H_escalation_mgmt", "I_legal_humanitarian",
    ]
    cat_labels = [
        "Outcome", "TW Survival", "JMSDF", "Homeland",
        "Economy", "Ops Success", "Alliance", "Escalation", "Legal",
    ]

    fig = go.Figure()
    for result, label in zip(results_list, labels):
        values = [result["score"].get(c, 0) for c in categories]
        fig.add_trace(go.Bar(name=label, x=cat_labels, y=values))

    fig.update_layout(
        barmode="group",
        title="Strategy Comparison — Score by Category",
        yaxis_title="Score",
        height=400,
    )
    st.plotly_chart(fig, width="stretch")

    # Total scores
    cols = st.columns(len(results_list))
    for i, (result, label) in enumerate(zip(results_list, labels)):
        with cols[i]:
            st.metric(label, f"{result['score']['total']:.0f}")


def scenario_explorer_sidebar():
    """Render preset selector and parameter sliders in sidebar.

    Returns a scenario config dict.
    """
    from wargame.scenarios import UI_PRESETS

    preset_names = [p["name"] for p in UI_PRESETS]
    preset_idx = st.sidebar.selectbox("Preset", range(len(preset_names)),
                                       format_func=lambda i: preset_names[i])
    preset = UI_PRESETS[preset_idx]

    st.sidebar.markdown("---")
    st.sidebar.markdown("### China")
    china_profile = st.sidebar.selectbox("China Profile",
                                          ["aggressive", "adaptive", "cautious"],
                                          index=["aggressive", "adaptive", "cautious"].index(
                                              preset.get("china_profile", "adaptive")))
    china_surface = st.sidebar.slider("China Surface Ships", 20, 120,
                                       preset.get("china_surface_ships", 60))
    china_subs = st.sidebar.slider("China Submarines", 5, 50,
                                    preset.get("china_submarines", 20))
    china_aircraft = st.sidebar.slider("China Aircraft", 100, 600,
                                        preset.get("china_aircraft", 400))

    st.sidebar.markdown("### US")
    us_profile = st.sidebar.selectbox("US Profile",
                                       ["interventionist", "restrained"],
                                       index=["interventionist", "restrained"].index(
                                           preset.get("us_profile", "interventionist")))
    us_surface = st.sidebar.slider("US Surface Ships", 5, 40,
                                    preset.get("us_surface_ships", 24))
    us_subs = st.sidebar.slider("US Submarines", 2, 20,
                                 preset.get("us_submarines", 12))

    st.sidebar.markdown("### Taiwan")
    taiwan_profile = st.sidebar.selectbox("Taiwan Profile",
                                           ["resilient", "defeatist"],
                                           index=["resilient", "defeatist"].index(
                                               preset.get("taiwan_profile", "resilient")))
    taiwan_energy_mult = st.sidebar.slider("Taiwan Energy Multiplier", 0.1, 2.0,
                                            preset.get("taiwan_energy_multiplier", 1.0),
                                            step=0.1)

    st.sidebar.markdown("### Japan")
    japan_surface = st.sidebar.slider("Japan Surface Ships", 5, 30,
                                       preset.get("japan_surface_ships", 20))
    japan_subs = st.sidebar.slider("Japan Submarines", 2, 12,
                                    preset.get("japan_submarines", 6))

    return {
        "name": "custom",
        "china_profile": china_profile,
        "us_profile": us_profile,
        "taiwan_profile": taiwan_profile,
        "china_surface_ships": china_surface,
        "china_submarines": china_subs,
        "china_aircraft": china_aircraft,
        "us_surface_ships": us_surface,
        "us_submarines": us_subs,
        "taiwan_energy_multiplier": taiwan_energy_mult,
        "japan_surface_ships": japan_surface,
        "japan_submarines": japan_subs,
    }
