"""Interactive Folium map of the Taiwan Strait theater."""

import folium


# Fleet positions (lat, lng) and colors
FLEETS = [
    ("china_surface_ships", (25.0, 119.5), "#e74c3c", "PLAN Surface"),
    ("china_submarines", (24.5, 119.0), "#c0392b", "PLAN Submarines"),
    ("us_surface_ships", (22.0, 125.0), "#2980b9", "USN Surface"),
    ("us_submarines", (23.0, 126.0), "#1f6dad", "USN Submarines"),
    ("japan_surface_ships", (26.5, 128.0), "#3498db", "JMSDF Surface"),
    ("japan_submarines", (27.0, 127.0), "#2471a3", "JMSDF Submarines"),
    ("taiwan_surface_ships", (24.5, 120.5), "#27ae60", "ROC Navy"),
]

# Convoy route waypoints (lat, lng)
ROUTES = {
    "direct": [(24.5, 120.5), (24.0, 119.5), (24.0, 118.5)],
    "japan_transship": [(24.5, 120.5), (24.5, 123.0), (26.5, 128.0), (31.6, 130.7)],
    "southern": [(22.0, 120.5), (21.0, 121.5), (20.0, 123.0)],
}

# Blockade zone polygon (lat, lng)
BLOCKADE_ZONE = [(25.5, 119.0), (25.5, 121.0), (22.5, 121.0), (22.5, 119.0)]

# Base positions and status colors
BASES = [
    ("japan_base_okinawa", (26.5, 127.8), "Okinawa"),
    ("japan_base_kyushu", (31.6, 130.7), "Kyushu"),
]
BASE_STATUS_COLORS = {"closed": "red", "limited": "orange", "open": "green"}

# Strike counters
STRIKE_KEYS = [
    ("japan_okinawa_strikes", (26.5, 127.8), "Okinawa"),
    ("japan_kyushu_strikes", (31.6, 130.7), "Kyushu"),
]


def render_map(state: dict, all_actions: dict = None) -> folium.Map:
    """Render an interactive Folium map for the current game state."""
    m = folium.Map(
        location=[24.0, 122.0],
        zoom_start=5,
        tiles="CartoDB dark_matter",
    )

    _draw_blockade_zone(m, state)
    _draw_fleets(m, state)
    _draw_bases(m, state)
    _draw_strikes(m, state)

    if all_actions and "taiwan" in all_actions:
        tw = all_actions["taiwan"]
        route = tw.get("convoy_route", "direct")
        convoy_size = tw.get("convoy_size", 0)
        if convoy_size > 0:
            _draw_convoy_route(m, route, state.get("blockade_tightness", 0.5))

    return m


def _draw_fleets(m: folium.Map, state: dict):
    """Add fleet CircleMarkers to the map."""
    for key, pos, color, label in FLEETS:
        count = state.get(key, 0)
        if count <= 0:
            continue
        radius = max(5, min(count * 0.5, 25))
        folium.CircleMarker(
            location=pos,
            radius=radius,
            color=color,
            fill=True,
            fill_color=color,
            fill_opacity=0.7,
            popup=f"{label}: {count}",
            tooltip=f"{label}: {count}",
        ).add_to(m)


def _draw_convoy_route(m: folium.Map, route: str, blockade_tightness: float):
    """Draw the active convoy route as a dashed polyline."""
    waypoints = ROUTES.get(route, ROUTES["direct"])
    danger = max(0.0, min(blockade_tightness, 1.0))
    r = int(danger * 255)
    g = int((1 - danger) * 255)
    color = f"#{r:02x}{g:02x}33"

    folium.PolyLine(
        locations=waypoints,
        color=color,
        weight=3,
        dash_array="10",
        opacity=0.8,
        tooltip=f"Convoy route: {route}",
    ).add_to(m)


def _draw_blockade_zone(m: folium.Map, state: dict):
    """Draw a semi-transparent red polygon for the blockade zone."""
    tightness = state.get("blockade_tightness", 0.0)
    if tightness <= 0:
        return
    folium.Polygon(
        locations=BLOCKADE_ZONE,
        color="red",
        fill=True,
        fill_color="red",
        fill_opacity=tightness * 0.3,
        dash_array="10",
        tooltip=f"Blockade: {tightness:.0%}",
    ).add_to(m)


def _draw_bases(m: folium.Map, state: dict):
    """Draw base status markers for Okinawa and Kyushu."""
    for key, pos, label in BASES:
        status = state.get(key, "closed")
        color = BASE_STATUS_COLORS.get(status, "gray")
        folium.Marker(
            location=pos,
            icon=folium.Icon(icon="home", prefix="fa", color=color),
            popup=f"{label}: {status.upper()}",
            tooltip=f"{label}: {status.upper()}",
        ).add_to(m)


def _draw_strikes(m: folium.Map, state: dict):
    """Draw red X markers on struck bases."""
    for key, pos, label in STRIKE_KEYS:
        count = state.get(key, 0)
        if count <= 0:
            continue
        folium.Marker(
            location=(pos[0] + 0.15, pos[1] + 0.15),
            icon=folium.Icon(icon="times", prefix="fa", color="red"),
            popup=f"{label} struck x{count}",
            tooltip=f"{label} struck x{count}",
        ).add_to(m)
