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

# --- Scoring Weights (spec section 9) ---
SCORE_WIN_BONUS = 500
SCORE_SURRENDER_PENALTY = -500
SCORE_EARLY_SURRENDER_PER_WEEK = -10

SCORE_ELECTRICITY_MAX = 80
SCORE_ECONOMY_MAX = 60
SCORE_MORALE_MAX = 60

SCORE_JMSDF_SURFACE_MAX = 60
SCORE_JMSDF_SUBS_MAX = 50
SCORE_JMSDF_AIR_MAX = 40

SCORE_HOMELAND_SAFE_BONUS = 100
SCORE_OKINAWA_STRIKE_PENALTY = -30
SCORE_KYUSHU_STRIKE_PENALTY = -60
SCORE_MAINLAND_STRIKE_PENALTY = -100
SCORE_US_MISSILE_DEFENSE_BONUS = 50
SCORE_INTERCEPT_BONUS = 10
SCORE_INTERCEPT_MAX = 50

SCORE_SEA_LANE_DISRUPTION_PER_WEEK = -5
SCORE_ENERGY_IMPORT_DISRUPTION_MAX = -30
SCORE_PORT_CONGESTION_MAX = -20

SCORE_CONVOY_JAPAN_MAX = 50
SCORE_CORRIDOR_RECOVERY_MAX = 40
SCORE_ASW_EFFECTIVENESS_MAX = 30
SCORE_BLOCKADE_CONTRIBUTION_MAX = 30

SCORE_US_SATISFACTION_MAX = 50
SCORE_FREE_RIDING_PENALTY = -50
SCORE_FREE_RIDING_THRESHOLD = 0.2
SCORE_REGIONAL_TRUST_MAX = 30
SCORE_COORDINATION_MAX = 20

SCORE_ESCALATION_LOW_BONUS = 50
SCORE_ESCALATION_LEVEL3_PENALTY = -50
SCORE_ESCALATION_LEVEL4_PENALTY = -100
SCORE_HOMELAND_ESCALATION_PENALTY = -150
SCORE_DEESCALATION_BONUS = 30

SCORE_ARTICLE9_PENALTY_PER_TURN = -10
SCORE_FIRST_STRIKE_PENALTY = -30
SCORE_CIVILIAN_CASUALTY_MAX_PENALTY = -50
SCORE_CIVILIAN_CASUALTY_DIVISOR = 1000

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
