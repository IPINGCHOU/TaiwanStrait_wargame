"""Baseline Japan strategy for ShinkaEvolve evolution."""

import sys
import os

# Add project root to path so wargame imports work
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# EVOLVE-BLOCK-START
def japan_strategy(state: dict) -> dict:
    """Japan's turn-by-turn strategy for the Taiwan Strait blockade.

    Receives game state, returns Japan's actions dict.
    This function is evolved by ShinkaEvolve.

    Actions:
        surface_deploy (float 0-1): JMSDF surface ship deployment
        submarine_deploy (float 0-1): JMSDF submarine deployment
        air_sortie_rate (float 0-1): JASDF sortie rate
        okinawa_access (str): "closed", "limited", "open"
        kyushu_access (str): "closed", "limited", "open"
        transshipment_allow (bool): allow Taiwan convoys through Japan
        convoy_escort_commit (float 0-1): JMSDF ships for convoy escort
        port_capacity_share (float 0-1): port capacity for Taiwan transshipment
        engagement_posture (str): "self_defense_only", "defensive", "proactive"
        asw_priority (float 0-1): ASW vs surface combat priority
        diplomatic_pressure (float 0-1): diplomatic effort
        sanctions_advocacy (bool): push for UN sanctions
        humanitarian_aid (float 0-1): aid to Taiwan
    """
    week = state["week"]

    # Phase-based baseline: cautious early, increase commitment mid-game
    if week <= 5:
        return {
            "surface_deploy": 0.3,
            "submarine_deploy": 0.4,
            "air_sortie_rate": 0.2,
            "okinawa_access": "limited",
            "kyushu_access": "closed",
            "transshipment_allow": True,
            "convoy_escort_commit": 0.4,
            "port_capacity_share": 0.3,
            "engagement_posture": "self_defense_only",
            "asw_priority": 0.6,
            "diplomatic_pressure": 0.8,
            "sanctions_advocacy": True,
            "humanitarian_aid": 0.4,
        }
    elif week <= 12:
        return {
            "surface_deploy": 0.5,
            "submarine_deploy": 0.6,
            "air_sortie_rate": 0.3,
            "okinawa_access": "limited",
            "kyushu_access": "limited",
            "transshipment_allow": True,
            "convoy_escort_commit": 0.4,
            "port_capacity_share": 0.5,
            "engagement_posture": "defensive",
            "asw_priority": 0.5,
            "diplomatic_pressure": 0.6,
            "sanctions_advocacy": True,
            "humanitarian_aid": 0.5,
        }
    else:
        return {
            "surface_deploy": 0.6,
            "submarine_deploy": 0.8,
            "air_sortie_rate": 0.5,
            "okinawa_access": "open",
            "kyushu_access": "limited",
            "transshipment_allow": True,
            "convoy_escort_commit": 0.3,
            "port_capacity_share": 0.6,
            "engagement_posture": "defensive",
            "asw_priority": 0.4,
            "diplomatic_pressure": 0.4,
            "sanctions_advocacy": True,
            "humanitarian_aid": 0.6,
        }
# EVOLVE-BLOCK-END
