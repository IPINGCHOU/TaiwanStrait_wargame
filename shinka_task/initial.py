"""Baseline Japan strategy for ShinkaEvolve evolution."""

import sys
import os

# Add project root to path so wargame imports work
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# EVOLVE-BLOCK-START
#
# === GAME CONTEXT (for the LLM) ===
#
# You are optimizing Japan's strategy in a 20-week Taiwan Strait naval blockade.
# China blockades Taiwan; US, Japan, Taiwan form a coalition to break it.
# Japan's decisions are the ONLY thing you control. The other 3 nations use fixed AI.
#
# === HOW ACTIONS AFFECT OUTCOMES ===
#
# MILITARY DEPLOYMENT (higher = more combat power but more risk/losses):
#   surface_deploy (0-1): JMSDF ships in combat. Higher → more damage to China, but more losses.
#   submarine_deploy (0-1): JMSDF subs. Subs have 1.8x tech multiplier — very effective.
#   air_sortie_rate (0-1): JASDF aircraft. Contributes to general combat.
#   NOTE: surface_deploy + convoy_escort_commit cannot exceed 1.0 (ships do one or the other).
#
# CONVOY/LOGISTICS (keeping Taiwan alive):
#   convoy_escort_commit (0-1): JMSDF ships escorting convoys (reduces combat availability).
#   transshipment_allow (bool): Let convoys route through Japan (0.6x threat reduction!).
#   port_capacity_share (0-1): Port capacity shared with Taiwan transshipment.
#
# ENGAGEMENT RULES:
#   engagement_posture: "self_defense_only" (0.5x), "defensive" (0.8x), "proactive" (1.1x combat).
#     WARNING: "proactive" triggers Article 9 violations (-5 points/turn penalty).
#   asw_priority (0-1): Focus on anti-submarine warfare. Higher → more Chinese sub kills.
#
# BASE ACCESS:
#   okinawa_access / kyushu_access: "closed", "limited", "open" for US forces.
#     Opening bases helps US but risks Chinese strikes on Japan homeland.
#     Strikes cause exponential score decay (0→100pts, 1→50pts, 2→25pts safe bonus).
#
# DIPLOMACY:
#   diplomatic_pressure (0-1): Resources on diplomacy (affects world opinion).
#   sanctions_advocacy (bool): Push for UN sanctions on China.
#   humanitarian_aid (0-1): Aid to Taiwan (improves morale).
#
# === SCORING (what you're optimizing) ===
#
# Score = A + B + C + D + E + F + G + H + I - 470 (centering offset)
#
# A. Strategic Outcome (-500 to +200): Win base +50, plus up to +150 × (electricity% × morale)
# B. Taiwan Survival (0 to +200): Final electricity + economy + morale
# C. JMSDF Preservation (0 to +150): Fraction of ships/subs/aircraft remaining
# D. Homeland Security (-200 to +100): Exponential decay with strikes + missile defense
# E. Economic Impact (-100 to 0): -5 per week of sea lane disruption
# F. Operational Success (0 to +200): Convoy throughput, ASW kills, delivery consistency
# G. Alliance Credibility (-100 to +100): Linear with avg deployment (0.5 → score 0)
# H. Escalation Management (-200 to +100): 100 - 75 × avg_escalation_across_all_turns
# I. Legal/Humanitarian (-100 to 0): Article 9 violations, civilian casualties
#
# Each scenario score is NORMALIZED to 0-100 (equal weight regardless of difficulty).
# Fitness = avg_normalized × 0.6 + min_scenario_normalized × 0.25 + win_rate × 15
# Max fitness ≈ 100. Baseline ≈ 48. Evaluated across 3 scenarios × 5 seeds = 15 games.
#
# === KEY INSIGHTS ===
# - Submarines are your best asset (1.8x multiplier). Deploy them early and always.
# - Transshipment through Japan reduces convoy threat by 40% — almost always worth it.
# - "defensive" posture is usually optimal (0.8x combat, no Article 9 penalty).
# - The surge scenario (China 90 ships, 30 subs) is hardest — strategies must handle it.
# - Escalation is scored by AVERAGE across all turns, not just final level.
# - Opening bases to US helps combat but risks homeland strikes (exponential penalty).
# - You can read ANY state field to make reactive decisions (see state dict below).
#
# === STATE FIELDS YOU CAN READ ===
# week, china_surface_ships, china_submarines, china_aircraft, china_missiles,
# us_surface_ships, us_submarines, taiwan_surface_ships, taiwan_morale,
# taiwan_energy_gas, taiwan_energy_coal, taiwan_energy_oil,
# taiwan_electricity_pct, taiwan_economy_pct, japan_surface_ships,
# japan_submarines, japan_aircraft, blockade_tightness (0-1),
# escalation_level (0-4), world_opinion (-1 to +1), total_cargo_delivered,
# merchant_ships_lost, japan_homeland_strikes, japan_base_okinawa, japan_base_kyushu

def japan_strategy(state: dict) -> dict:
    """Japan's turn-by-turn strategy. Returns actions dict."""
    week = state["week"]

    # Helper: clamp float to [0, 1]
    def clamp(x):
        return max(0.0, min(1.0, x))

    # Read key state variables for reactive decisions
    blockade = state.get("blockade_tightness", 0.5)
    escalation = state.get("escalation_level", 1)
    tw_economy = state.get("taiwan_economy_pct", 100)
    tw_morale = state.get("taiwan_morale", 0.8)
    china_subs = state.get("china_submarines", 20)
    china_surface = state.get("china_surface_ships", 60)
    homeland_strikes = state.get("japan_homeland_strikes", 0)

    # Base deployment — ramp up over time
    sub_deploy = clamp(0.4 + week * 0.03)
    surface_deploy = clamp(0.3 + week * 0.015)
    air_rate = clamp(0.2 + week * 0.015)

    # ASW priority — higher when China has more subs
    asw = clamp(0.3 + china_subs * 0.02)

    # Convoy escort — balance with surface combat
    escort = clamp(0.4 - surface_deploy * 0.2)

    # Posture — stay defensive to avoid Article 9 penalties
    posture = "defensive"

    # Base access — limited early, open if no strikes
    okinawa = "limited" if homeland_strikes == 0 else "closed"
    kyushu = "closed" if week <= 8 else ("limited" if homeland_strikes == 0 else "closed")

    # Diplomacy — front-load
    diplo = clamp(0.8 - week * 0.02)

    return {
        "surface_deploy": surface_deploy,
        "submarine_deploy": sub_deploy,
        "air_sortie_rate": air_rate,
        "okinawa_access": okinawa,
        "kyushu_access": kyushu,
        "transshipment_allow": True,
        "convoy_escort_commit": escort,
        "port_capacity_share": 0.4,
        "engagement_posture": posture,
        "asw_priority": asw,
        "diplomatic_pressure": diplo,
        "sanctions_advocacy": True,
        "humanitarian_aid": 0.4,
    }
# EVOLVE-BLOCK-END
