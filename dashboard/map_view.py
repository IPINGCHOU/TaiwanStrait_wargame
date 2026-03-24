"""Regional schematic map of the Taiwan Strait theater."""

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np


# Region positions (schematic, not geographic)
REGIONS = {
    "china": {"center": (0.15, 0.5), "color": "#e74c3c", "label": "China\n(East Coast)"},
    "taiwan": {"center": (0.5, 0.4), "color": "#2ecc71", "label": "Taiwan"},
    "okinawa": {"center": (0.7, 0.75), "color": "#3498db", "label": "Okinawa"},
    "kyushu": {"center": (0.65, 0.9), "color": "#3498db", "label": "Kyushu"},
}

# Convoy routes as bezier-ish waypoints
ROUTES = {
    "direct": [(0.5, 0.4), (0.35, 0.35), (0.15, 0.3)],
    "japan_transship": [(0.5, 0.4), (0.6, 0.6), (0.7, 0.75), (0.65, 0.9)],
    "southern": [(0.5, 0.4), (0.5, 0.15), (0.3, 0.1), (0.15, 0.2)],
}

BASE_STATUS_COLORS = {"closed": "#e74c3c", "limited": "#f39c12", "open": "#2ecc71"}


def render_map(state: dict, all_actions: dict = None, fig=None, ax=None):
    """Render the regional schematic map for a given game state.

    Returns (fig, ax) matplotlib objects.
    """
    if fig is None or ax is None:
        fig, ax = plt.subplots(1, 1, figsize=(10, 8))
    ax.clear()
    ax.set_xlim(-0.05, 1.05)
    ax.set_ylim(-0.05, 1.05)
    ax.set_aspect("equal")
    ax.set_facecolor("#1a1a2e")
    fig.patch.set_facecolor("#16213e")

    # Draw water
    water = mpatches.FancyBboxPatch(
        (-0.05, -0.05), 1.1, 1.1, boxstyle="round,pad=0.02",
        facecolor="#0f3460", edgecolor="none"
    )
    ax.add_patch(water)

    # Draw regions
    for name, info in REGIONS.items():
        cx, cy = info["center"]
        size = 0.12 if name == "china" else 0.08
        region = mpatches.FancyBboxPatch(
            (cx - size/2, cy - size/2), size, size,
            boxstyle="round,pad=0.01",
            facecolor=info["color"], alpha=0.3, edgecolor=info["color"], linewidth=2
        )
        ax.add_patch(region)
        ax.text(cx, cy, info["label"], ha="center", va="center",
                fontsize=9, fontweight="bold", color="white")

    # Draw Taiwan Strait label
    ax.text(0.32, 0.45, "Taiwan\nStrait", ha="center", va="center",
            fontsize=7, color="#aaaaaa", style="italic")

    # Draw fleet icons
    _draw_fleets(ax, state)

    # Draw convoy route if actions provided
    if all_actions and "taiwan" in all_actions:
        route = all_actions["taiwan"].get("convoy_route", "direct")
        convoy_size = all_actions["taiwan"].get("convoy_size", 0)
        if convoy_size > 0:
            _draw_convoy_route(ax, route, state.get("blockade_tightness", 0.5))

    # Draw base status indicators
    _draw_base_status(ax, state)

    # Draw strike markers
    _draw_strikes(ax, state)

    # Info box
    _draw_info_box(ax, state)

    ax.set_xticks([])
    ax.set_yticks([])
    ax.set_title(f"Week {state.get('week', 1)} — Escalation Level {state.get('escalation_level', 0)}",
                 color="white", fontsize=14, fontweight="bold", pad=10)

    return fig, ax


def _draw_fleets(ax, state):
    """Draw fleet icons as sized circles near their region."""
    fleets = [
        ("china_surface_ships", (0.25, 0.55), "#e74c3c", "PLAN"),
        ("china_submarines", (0.25, 0.45), "#c0392b", "PLAN Sub"),
        ("us_surface_ships", (0.55, 0.55), "#2980b9", "USN"),
        ("us_submarines", (0.55, 0.65), "#1f6dad", "USN Sub"),
        ("japan_surface_ships", (0.75, 0.7), "#3498db", "JMSDF"),
        ("japan_submarines", (0.78, 0.65), "#2471a3", "JMSDF Sub"),
        ("taiwan_surface_ships", (0.45, 0.3), "#27ae60", "ROC Navy"),
    ]
    for key, pos, color, label in fleets:
        count = state.get(key, 0)
        if count > 0:
            size = max(80, min(count * 8, 500))
            ax.scatter(*pos, s=size, c=color, alpha=0.7, edgecolors="white", linewidth=0.5, zorder=5)
            ax.text(pos[0], pos[1] - 0.04, f"{label}\n{count}",
                    ha="center", va="top", fontsize=6, color="white")


def _draw_convoy_route(ax, route, blockade_tightness):
    """Draw convoy route arrow with color based on danger level."""
    waypoints = ROUTES.get(route, ROUTES["direct"])
    # Color: green (safe) to red (dangerous)
    danger = min(blockade_tightness, 1.0)
    color = (danger, 1 - danger, 0.2)

    xs = [p[0] for p in waypoints]
    ys = [p[1] for p in waypoints]
    ax.plot(xs, ys, color=color, linewidth=2, linestyle="--", alpha=0.8, zorder=4)
    # Arrow at midpoint
    mid = len(xs) // 2
    if mid > 0:
        dx = xs[mid] - xs[mid-1]
        dy = ys[mid] - ys[mid-1]
        ax.annotate("", xy=(xs[mid], ys[mid]),
                     xytext=(xs[mid] - dx*0.3, ys[mid] - dy*0.3),
                     arrowprops=dict(arrowstyle="->", color=color, lw=2))


def _draw_base_status(ax, state):
    """Draw base status indicators for Okinawa and Kyushu."""
    bases = [
        ("japan_base_okinawa", (0.82, 0.75), "Okinawa Base"),
        ("japan_base_kyushu", (0.77, 0.9), "Kyushu Base"),
    ]
    for key, pos, label in bases:
        status = state.get(key, "closed")
        color = BASE_STATUS_COLORS.get(status, "#999999")
        ax.scatter(*pos, s=120, c=color, marker="s", edgecolors="white",
                   linewidth=1, zorder=6)
        ax.text(pos[0] + 0.04, pos[1], f"{status.upper()}",
                fontsize=6, color=color, va="center")


def _draw_strikes(ax, state):
    """Draw red X markers for homeland strikes."""
    total_strikes = state.get("japan_homeland_strikes", 0)
    if total_strikes > 0:
        okinawa_strikes = state.get("japan_okinawa_strikes", 0)
        kyushu_strikes = state.get("japan_kyushu_strikes", 0)
        if okinawa_strikes > 0:
            ax.scatter(0.72, 0.73, s=200, c="red", marker="x", linewidths=3, zorder=7)
            ax.text(0.72, 0.69, f"x{okinawa_strikes}", color="red", fontsize=8, ha="center")
        if kyushu_strikes > 0:
            ax.scatter(0.67, 0.88, s=200, c="red", marker="x", linewidths=3, zorder=7)
            ax.text(0.67, 0.84, f"x{kyushu_strikes}", color="red", fontsize=8, ha="center")


def _draw_info_box(ax, state):
    """Draw info panel with key metrics."""
    info_lines = [
        f"Blockade: {state.get('blockade_tightness', 0):.0%}",
        f"Electricity: {state.get('taiwan_electricity_pct', 100):.0f}%",
        f"Economy: {state.get('taiwan_economy_pct', 100):.0f}%",
        f"TW Morale: {state.get('taiwan_morale', 0.8):.2f}",
        f"Cargo: {state.get('total_cargo_delivered', 0):.0f}",
    ]
    info_text = "\n".join(info_lines)
    ax.text(0.02, 0.98, info_text, transform=ax.transAxes,
            fontsize=8, color="white", va="top", ha="left",
            bbox=dict(boxstyle="round,pad=0.3", facecolor="#16213e", alpha=0.9, edgecolor="#444"))
