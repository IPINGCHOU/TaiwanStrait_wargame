"""All game constants — initial forces, combat rates, energy parameters, scoring weights."""

# --- Initial Forces ---
CHINA_INITIAL = {
    "surface_ships": 60, "submarines": 20, "aircraft": 400,
    "missiles": 1200, "coast_guard": 40, "morale": 0.9,
}
US_INITIAL = {
    "surface_ships": 24, "submarines": 12, "aircraft": 200, "missiles": 800,
}
TAIWAN_INITIAL = {
    "surface_ships": 26, "aircraft": 150, "missiles": 400,
    "reserves": 50000, "morale": 0.8,
    "energy_gas": 10.0,   # days
    "energy_coal": 7.0,   # weeks
    "energy_oil": 20.0,   # weeks
    "electricity_pct": 100.0,
    "economy_pct": 100.0,
}
JAPAN_INITIAL = {
    "surface_ships": 20, "submarines": 6, "aircraft": 100,
    "base_okinawa": "closed", "base_kyushu": "closed",
}

# --- Combat Coefficients ---
TECH_MULTIPLIERS = {
    "us_surface": 1.3, "us_submarine": 2.5,
    "japan_surface": 1.1, "japan_submarine": 1.8,
    "taiwan_surface": 0.9,
    "china_surface": 0.8, "china_submarine": 1.5,
}
LANCHESTER_RATE = 0.02
NOISE_RANGE = (0.8, 1.2)
MIN_EFFECTIVE_FORCE = 1.0

# --- Engagement Posture Modifiers ---
JAPAN_POSTURE_MODIFIER = {
    "self_defense_only": 0.5,
    "defensive": 0.8,
    "proactive": 1.1,
}

# --- Convoy ---
CARGO_PER_SHIP = 1.0  # normalized cargo units
ROUTE_THREAT_MODIFIER = {"direct": 1.0, "japan_transship": 0.6, "southern": 0.8}
CONVOY_SIGMOID_STEEPNESS = 3.0

# --- Energy (Taiwan) ---
GAS_CONSUMPTION_DAYS_PER_WEEK = 7.0  # days of gas consumed per week
COAL_CONSUMPTION_PER_WEEK = 1.0
OIL_CONSUMPTION_PER_WEEK = 1.0
ENERGY_MIX = {"gas": 0.38, "coal": 0.36, "oil": 0.12, "renewable": 0.14}
GAS_FRACTION_OF_CARGO = 0.3
COAL_FRACTION_OF_CARGO = 0.4
OIL_FRACTION_OF_CARGO = 0.3
ECONOMY_LAG_FACTOR = 0.3
MORALE_DECAY_THRESHOLD = 50.0  # economy_pct below this triggers morale decay
MORALE_DECAY_RATE = 0.10       # per week when economy < threshold
MORALE_SIEGE_FATIGUE = 0.01    # unconditional morale decay per week from blockade duration
RATIONING_MODIFIER = {"none": 1.0, "moderate": 0.7, "severe": 0.4}

# --- Escalation ---
ESCALATION_DEPLOY_WEIGHT = 2.0
ESCALATION_MISSILE_WEIGHT = 1.5
ESCALATION_CIVILIAN_WEIGHT = 2.0
ESCALATION_PORT_STRIKE_SCORE = 1.0
ESCALATION_AIRBASE_STRIKE_SCORE = 0.8
ESCALATION_HOMELAND_STRIKE_SCORE = 2.0
MAX_ESCALATION_CHANGE_PER_TURN = 1

# --- Scoring Weights (v2: smooth gradients, centered so baseline ≈ 0) ---
#
# Design: range ≈ -1000 to +1000, baseline strategy ≈ 0
# All categories use continuous functions, no binary jumps.

# Category A — Strategic Outcome (-500 to +200)
# Win: +50 base + up to +150 scaled by Taiwan final health
# Lose: -200 base - 15 per remaining week
SCORE_WIN_BASE = 50
SCORE_WIN_HEALTH_MAX = 150           # scaled by (electricity% × morale)
SCORE_SURRENDER_BASE = -200
SCORE_SURRENDER_PER_REMAINING_WEEK = -15

# Category B — Taiwan Survival Quality (0 to +200)
SCORE_ELECTRICITY_MAX = 80
SCORE_ECONOMY_MAX = 60
SCORE_MORALE_MAX = 60

# Category C — JMSDF Preservation (0 to +150)
SCORE_JMSDF_SURFACE_MAX = 60
SCORE_JMSDF_SUBS_MAX = 50
SCORE_JMSDF_AIR_MAX = 40

# Category D — Homeland Security (-200 to +100)
# Continuous: 100 × exp(-total_strikes × 0.7) instead of binary safe/not-safe
# Plus per-base penalties and missile defense
SCORE_HOMELAND_MAX = 100
SCORE_HOMELAND_DECAY_RATE = 0.7      # exponential decay per strike
SCORE_OKINAWA_STRIKE_PENALTY = -30
SCORE_KYUSHU_STRIKE_PENALTY = -60
SCORE_MAINLAND_STRIKE_PENALTY = -100
SCORE_US_MISSILE_DEFENSE_BONUS = 50

# Category E — Economic Impact (-100 to 0)
SCORE_SEA_LANE_DISRUPTION_PER_WEEK = -5

# Category F — Operational Success (0 to +200)
SCORE_CONVOY_JAPAN_MAX = 40
SCORE_CORRIDOR_RECOVERY_MAX = 30
SCORE_ASW_EFFECTIVENESS_MAX = 30
SCORE_BLOCKADE_CONTRIBUTION_MAX = 30
SCORE_DELIVERY_CONSISTENCY_MAX = 40  # new: reward steady cargo across turns
SCORE_CHINA_ATTRITION_MAX = 30       # new: reward degrading China forces

# Category G — Alliance Credibility (-100 to +100)
# Pure linear: score = 200 × deploy - 100 (so deploy=0 → -100, deploy=0.5 → 0, deploy=1.0 → +100)
SCORE_ALLIANCE_SLOPE = 200
SCORE_ALLIANCE_INTERCEPT = -100

# Category H — Escalation Management (-200 to +100)
# Continuous: 100 - 75 × avg_escalation_across_all_turns
# avg_esc=0 → +100, avg_esc=1.33 → 0, avg_esc=4 → -200
SCORE_ESCALATION_BASE = 100
SCORE_ESCALATION_SLOPE = -75         # per unit of average escalation
SCORE_DEESCALATION_BONUS = 30

# Category I — Legal & Humanitarian (-100 to 0)
SCORE_ARTICLE9_PENALTY_PER_TURN = -5  # reduced from -10 (was too punishing)
SCORE_FIRST_STRIKE_PENALTY = -30
SCORE_CIVILIAN_CASUALTY_MAX_PENALTY = -50
SCORE_CIVILIAN_CASUALTY_DIVISOR = 1000

# Centering offset — subtracted from total so baseline ≈ 0
# (calibrated after computing baseline score under new system)
SCORE_CENTERING_OFFSET = 470  # calibrated so baseline strategy ≈ 0

# --- Game ---
MAX_WEEKS = 20
# Surrender: morale < 0.15 OR (morale < 0.2 AND economy < 15)
SURRENDER_MORALE_HARD = 0.15     # auto-surrender below this
SURRENDER_MORALE_SOFT = 0.2      # surrender if also economy < soft threshold
SURRENDER_ECONOMY_THRESHOLD = 15.0

# Blockade
BASE_BLOCKADE_LEVEL = 0.3  # China's geographic advantage in Taiwan Strait

# --- Fitness Aggregation ---
FITNESS_AVG_WEIGHT = 0.5
FITNESS_MIN_WEIGHT = 0.3
FITNESS_WINRATE_MULTIPLIER = 200
