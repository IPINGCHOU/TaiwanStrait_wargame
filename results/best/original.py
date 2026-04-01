"""Baseline Japan strategy for ShinkaEvolve evolution."""

import sys
import os

# Add project root to path so wargame imports work
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# EVOLVE-BLOCK-START
#
# === GAME CONTEXT (unchanged — environment will provide state fields below) ===
#
# You are optimizing Japan's strategy in a 20-week Taiwan Strait naval blockade.
# China blockades Taiwan; US, Japan, Taiwan form a coalition to break it.
# Japan's decisions are the ONLY thing you control. The other 3 nations use fixed AI.
#
# === STATE FIELDS YOU CAN READ ===
# week, china_surface_ships, china_submarines, china_aircraft, china_missiles,
# us_surface_ships, us_submarines, taiwan_surface_ships, taiwan_morale,
# taiwan_energy_gas, taiwan_energy_coal, taiwan_energy_oil,
# taiwan_electricity_pct, taiwan_economy_pct, japan_surface_ships,
# japan_submarines, japan_aircraft, blockade_tightness (0-1),
# escalation_level (0-4), world_opinion (-1 to +1), total_cargo_delivered,
# merchant_ships_lost, japan_homeland_strikes, japan_base_okinawa, japan_base_kyushu
#

from typing import Dict, Any

# -----------------------
# Utilities
# -----------------------
def _clamp01(x: float) -> float:
    """Clamp numeric to [0,1] robustly and handle NaN/invalid."""
    try:
        xf = float(x)
    except Exception:
        return 0.0
    if xf != xf:  # NaN
        return 0.0
    if xf <= 0.0:
        return 0.0
    if xf >= 1.0:
        return 1.0
    return xf

def _safe_get(state: dict, key: str, default=0.0):
    return state.get(key, default)

# -----------------------
# Runtime state (persistent)
# -----------------------
_runtime_state = {
    "prev_bias": 0.5,
    "prev_cargo_urgency": 0.5,
    "prev_threat": 0.5,
    "prev_submarine": None,
}

# -----------------------
# Parameters (centralized)
# -----------------------
class Params:
    MAX_CHINA_SUBS = 40.0
    MAX_CHINA_SURFACE = 120.0
    MAX_CARGO = 500.0
    MAX_MERCHANT_LOST = 10.0
    US_SURFACE_REF = 50.0

    W_SUBS = 0.97
    W_SURFACE = 0.10
    W_BLOCKADE = 0.93

    # Slightly raise baseline ASW bias so Japan preserves anti-submarine coverage
    BASE_SUB = 0.83
    BASE_SURFACE = 0.10
    BASE_AIR = 0.12

    # Allow lower floor for subs so planner can reallocate aggressively when needed
    SUB_MIN = 0.18
    SURFACE_MIN = 0.06
    AIR_MIN = 0.07

    MOMENTUM_ALPHA_MIN = 0.06
    # Increase max alpha so the controller can respond faster to divergent signals
    MOMENTUM_ALPHA_MAX = 0.34

    # Reduce base inertia so threat/urgency react quicker to changes
    BASE_THREAT_INERTIA = 0.018
    BASE_URGENCY_INERTIA = 0.014

    ALLIED_ASW_DISCOUNT = 0.16
    ALLIED_SUB_DISCOUNT = 0.13

    ESCORT_BASE = 0.40
    ESCORT_MIN_CAP = 0.52
    ESCORT_MAX_CAP = 0.995
    ESCORT_BASE_BIAS = 0.86
    ESCORT_PRESERVE_THRESHOLD = 0.60

    PORT_BASE = 0.63
    PORT_EARLY_BONUS = 0.22
    PORT_BLOCKADE_SCALE = 0.38

    # Slightly reduce air priority boost to avoid over-allocating air at expense of ASW
    AIR_PRIORITY_BOOST = 0.28

# -----------------------
# Momentum / smoothing controller
# -----------------------
class MomentumController:
    """Encapsulate adaptive alpha/inertia and smoothing to keep behavior consistent."""
    @staticmethod
    def adaptive_alpha(cargo_urgency: float, threat: float, prev_bias: float) -> float:
        c = _clamp01(cargo_urgency)
        t = _clamp01(threat)
        pb = _clamp01(prev_bias)
        divergence = abs(c - 0.5) + abs(t - 0.5) + abs(pb - 0.5)
        scaled = _clamp01(divergence / 1.5)
        return Params.MOMENTUM_ALPHA_MIN + scaled * (Params.MOMENTUM_ALPHA_MAX - Params.MOMENTUM_ALPHA_MIN)

    @staticmethod
    def adaptive_inertia(val: float, base: float) -> float:
        v = _clamp01(val)
        prev = _clamp01(_runtime_state.get("prev_threat", 0.5))
        distance = abs(v - 0.5)
        trend = abs(v - prev)
        urgency = min(1.0, 0.85 * distance + 0.95 * trend)
        scale = 1.0 - 0.92 * urgency
        inertia = max(0.005, base * max(0.007, scale))
        return inertia

    @staticmethod
    def smooth(val: float, inertia: float) -> float:
        v = _clamp01(val)
        return _clamp01((1.0 - inertia) * v + inertia * 0.5)

    @staticmethod
    def update_momentum(cargo_urgency: float, bias: float, threat: float = None) -> None:
        prev_bias = _runtime_state.get("prev_bias", 0.5)
        prev_threat = _runtime_state.get("prev_threat", 0.5)
        a = MomentumController.adaptive_alpha(cargo_urgency, threat if threat is not None else prev_threat, prev_bias)
        _runtime_state["prev_cargo_urgency"] = (1.0 - a) * _runtime_state.get("prev_cargo_urgency", cargo_urgency) + a * cargo_urgency
        _runtime_state["prev_bias"] = (1.0 - a) * prev_bias + a * bias
        if threat is not None:
            _runtime_state["prev_threat"] = (1.0 - a) * prev_threat + a * threat

# -----------------------
# Signal extraction / normalization
# -----------------------
class SignalExtractor:
    """Extract normalized signals from raw state and update momentum seeds."""
    def __init__(self, raw: Dict[str, Any]):
        self.raw = raw
        _runtime_state.setdefault("prev_bias", 0.5)
        _runtime_state.setdefault("prev_cargo_urgency", 0.5)
        _runtime_state.setdefault("prev_threat", 0.5)
        self.ctx = self._extract()

    def _extract(self) -> Dict[str, Any]:
        week = int(_safe_get(self.raw, "week", 0))
        blockade = float(_safe_get(self.raw, "blockade_tightness", 0.5))
        escalation = int(_safe_get(self.raw, "escalation_level", 1))
        china_subs = int(_safe_get(self.raw, "china_submarines", 20))
        china_surface = int(_safe_get(self.raw, "china_surface_ships", 60))
        china_aircraft = int(_safe_get(self.raw, "china_aircraft", 40))
        china_missiles = int(_safe_get(self.raw, "china_missiles", 8))
        merchant_lost = int(_safe_get(self.raw, "merchant_ships_lost", 0))
        homeland_strikes = int(_safe_get(self.raw, "japan_homeland_strikes", 0))
        world_op = float(_safe_get(self.raw, "world_opinion", 0.0))
        us_surface = int(_safe_get(self.raw, "us_surface_ships", 20))
        us_subs = int(_safe_get(self.raw, "us_submarines", 0))
        japan_subs = int(_safe_get(self.raw, "japan_submarines", 8))
        total_cargo = float(_safe_get(self.raw, "total_cargo_delivered", 0.0))

        tw_economy = float(_safe_get(self.raw, "taiwan_economy_pct", 100.0))
        tw_electric = float(_safe_get(self.raw, "taiwan_electricity_pct", 100.0))
        tw_morale = float(_safe_get(self.raw, "taiwan_morale", 0.9))

        subs_comp = min(1.0, china_subs / Params.MAX_CHINA_SUBS)
        surf_comp = min(1.0, china_surface / Params.MAX_CHINA_SURFACE)
        cargo_frac = min(1.0, total_cargo / Params.MAX_CARGO)
        merchant_frac = _clamp01(merchant_lost / Params.MAX_MERCHANT_LOST)

        is_early = week <= 8
        is_mid = 9 <= week <= 14
        is_late = week > 14

        air_threat = min(1.0, china_aircraft / 120.0)
        missile_threat = min(1.0, china_missiles / 80.0)

        raw_threat = (
            Params.W_SUBS * (subs_comp ** 0.88)
            + Params.W_SURFACE * (surf_comp ** 0.98)
            + Params.W_BLOCKADE * (blockade ** 1.06)
            + 0.10 * (air_threat ** 1.02)
            + 0.08 * (missile_threat ** 1.02)
        )

        persistence = 0.26 * merchant_frac + 0.10 * (1.0 - cargo_frac)
        threat_unclamped = _clamp01(raw_threat + persistence)
        threat_inertia = MomentumController.adaptive_inertia(threat_unclamped, Params.BASE_THREAT_INERTIA)
        threat_index = MomentumController.smooth(threat_unclamped, threat_inertia)

        late_mult = 1.45 if is_late else 1.0
        cargo_raw = _clamp01((1.0 - cargo_frac) * 1.38 * late_mult + 1.9 * merchant_frac)
        cargo_inertia = MomentumController.adaptive_inertia(cargo_raw, Params.BASE_URGENCY_INERTIA)
        cargo_urgency = MomentumController.smooth(cargo_raw, cargo_inertia)

        coalition_support = _clamp01(us_surface / Params.US_SURFACE_REF)
        allied_asw = _clamp01((us_subs + japan_subs + max(0, us_surface - 8) * 0.44) / max(1.0, china_subs + 6.0))

        # seed momentum memory with neutral bias update
        MomentumController.update_momentum(cargo_urgency, _runtime_state.get("prev_bias", 0.5), threat_index)

        return {
            "week": week,
            "blockade": blockade,
            "escalation": escalation,
            "china_subs": china_subs,
            "china_surface": china_surface,
            "china_aircraft": china_aircraft,
            "china_missiles": china_missiles,
            "merchant_lost": merchant_lost,
            "homeland_strikes": homeland_strikes,
            "world_op": world_op,
            "us_surface": us_surface,
            "us_subs": us_subs,
            "japan_subs": japan_subs,
            "total_cargo": total_cargo,
            "threat_index": threat_index,
            "cargo_urgency": cargo_urgency,
            "coalition_support": coalition_support,
            "allied_asw": allied_asw,
            "tw_economy": tw_economy,
            "tw_electric": tw_electric,
            "tw_morale": tw_morale,
            "air_threat": air_threat,
            "missile_threat": missile_threat,
            "is_early": is_early,
            "is_mid": is_mid,
            "is_late": is_late,
        }

# -----------------------
# Military planner
# -----------------------
class MilitaryPlanner:
    @staticmethod
    def plan(ctx: Dict[str, Any]) -> Dict[str, float]:
        w = ctx["week"]
        threat = ctx["threat_index"]
        china_subs = ctx["china_subs"]
        merchant_lost = ctx["merchant_lost"]
        cargo_urgency = ctx["cargo_urgency"]
        coalition = ctx["coalition_support"]
        us_subs = ctx["us_subs"]
        japan_subs = ctx["japan_subs"]
        escalation = ctx["escalation"]
        hs = ctx["homeland_strikes"]
        allied_asw = ctx["allied_asw"]

        coalition_reliability = 0.5 * coalition + 0.5 * _clamp01(us_subs / 4.0)

        if w <= 8:
            sub_ramp = 0.15 * w
        elif w <= 14:
            sub_ramp = 0.15 * 8 + 0.035 * (w - 8)
        else:
            sub_ramp = 0.15 * 8 + 0.035 * 6 + 0.012 * max(0, w - 14)

        sub_from_subs = 0.10 * max(0, china_subs - 2)
        merchant_sub_bonus = 0.34 * min(1.0, merchant_lost / 6.0)
        hs_penalty_sub = 0.10 * min(1.0, hs)

        dynamic_allied_sub_discount = Params.ALLIED_SUB_DISCOUNT * max(0.16, coalition_reliability)
        if escalation >= 3 or hs > 0:
            dynamic_allied_sub_discount *= 0.5

        missile_threat = ctx.get("missile_threat", 0.0)
        missile_factor = max(0.24, 0.78 * (1.0 - min(0.9, missile_threat * 1.2)))

        submarine_raw = (
            Params.BASE_SUB
            + sub_ramp
            + sub_from_subs
            + missile_factor * (threat ** 1.03)
            + merchant_sub_bonus
            - hs_penalty_sub
            + 0.01 * japan_subs
        )

        if merchant_lost > 2:
            submarine_raw += 0.08 * min(1.0, (merchant_lost - 2) / 4.0)

        submarine_candidate = _clamp01(max(Params.SUB_MIN, submarine_raw * (1.0 - dynamic_allied_sub_discount * allied_asw)))

        prev_sub = _runtime_state.get("prev_submarine", None)
        prev_threat = _runtime_state.get("prev_threat", threat)
        prev_bias = _runtime_state.get("prev_bias", 0.5)
        a = MomentumController.adaptive_alpha(cargo_urgency, threat, prev_bias)

        if prev_sub is None:
            submarine = submarine_candidate
        else:
            trend = abs(prev_threat - threat)
            max_step = 0.14 + 0.28 * trend
            delta = submarine_candidate - prev_sub
            if delta > max_step:
                delta = max_step
            elif delta < -max_step:
                delta = -max_step
            target = prev_sub + delta
            submarine = _clamp01((1.0 - a) * prev_sub + a * target)
            submarine = max(submarine, Params.SUB_MIN)

        _runtime_state["prev_submarine"] = submarine

        surface_growth = 0.018 * w
        merchant_surface = 0.24 * min(1.0, merchant_lost / 6.0)
        surface_from_urgency = 0.56 * cargo_urgency
        coalition_surface_bonus = 0.095 * (1.0 - coalition) + 0.18 * allied_asw
        hs_penalty_surface = 0.09 * min(1.0, hs)
        surface_raw = Params.BASE_SURFACE + surface_growth + merchant_surface + surface_from_urgency + 0.095 * (threat ** 1.02) + coalition_surface_bonus - hs_penalty_surface
        surface = _clamp01(max(Params.SURFACE_MIN, surface_raw))

        air_ramp = 0.032 * w
        air_from_merchant = 0.16 * min(1.0, merchant_lost / 6.0)
        air_from_coalition = 0.24 * (1.0 - coalition)
        air_threat = ctx["air_threat"]
        air_missile = missile_threat
        air_from_domain = 0.38 * air_threat + 0.48 * air_missile
        air_priority_boost = Params.AIR_PRIORITY_BOOST * (air_threat + 1.6 * air_missile) * (1.0 - coalition)
        air_raw = Params.BASE_AIR + air_ramp + 0.30 * (threat ** 1.02) + air_from_merchant + air_from_coalition + air_from_domain + air_priority_boost - 0.042 * hs
        air = _clamp01(max(Params.AIR_MIN, air_raw))

        escalation_penalty = -0.12 if escalation >= 3 else (-0.05 if escalation == 2 else 0.0)
        asw_raw = 0.78 + 0.10 * china_subs + 0.92 * (threat ** 1.06) + 0.22 * ctx["blockade"] + 0.30 * min(1.0, merchant_lost / 6.0) + escalation_penalty
        dynamic_allied_asw_discount = Params.ALLIED_ASW_DISCOUNT * (0.94 * coalition_reliability + 0.06)
        if coalition_reliability < 0.45:
            dynamic_allied_asw_discount *= 0.55
        asw_pressure_scale = 1.0 - 0.30 * allied_asw - 0.18 * missile_threat
        asw_priority = _clamp01(max(0.36, asw_raw * max(0.40, asw_pressure_scale)))

        return {
            "submarine_deploy": submarine,
            "surface_deploy": surface,
            "air_sortie_rate": air,
            "asw_priority": asw_priority,
        }

# -----------------------
# Logistics planner
# -----------------------
class LogisticsPlanner:
    @staticmethod
    def plan(ctx: Dict[str, Any], military: Dict[str, float]) -> Dict[str, Any]:
        blockade = ctx["blockade"]
        china_surface = ctx["china_surface"]
        hs = ctx["homeland_strikes"]
        world_op = ctx["world_op"]
        merchant_lost = ctx["merchant_lost"]
        cargo_urgency = ctx["cargo_urgency"]
        escalation = ctx["escalation"]
        week = ctx["week"]
        coalition = ctx["coalition_support"]
        missile_threat = float(ctx.get("missile_threat", 0.0))
        asw_priority = float(military.get("asw_priority", 0.0))
        allied_asw = float(ctx.get("allied_asw", 0.0))

        desired_escort = _clamp01(
            Params.ESCORT_BASE
            + 0.70 * blockade
            + 0.74 * cargo_urgency
            + 0.5 * min(1.0, merchant_lost / 5.0)
            + max(0.0, (china_surface - 28) / 92.0)
            + 0.06 * max(0.0, -world_op)
        )

        dynamic_cap = 0.95 - 0.22 * coalition - 0.20 * missile_threat + 0.05 * (1.0 - allied_asw)
        if missile_threat > 0.65:
            dynamic_cap -= 0.06 * (missile_threat - 0.65)
        dynamic_cap = max(Params.ESCORT_MIN_CAP, min(Params.ESCORT_MAX_CAP, dynamic_cap))

        if asw_priority > 0.52:
            growth = min(0.30, 0.24 * (asw_priority - 0.50))
            dynamic_cap = min(1.0, dynamic_cap + max(0.0, growth * (1.0 - 0.78 * missile_threat)))

        if merchant_lost >= 3 or cargo_urgency > 0.94 or escalation >= 3:
            dynamic_cap = max(dynamic_cap, 0.995 - 0.02 * missile_threat)

        escort = min(dynamic_cap, desired_escort)
        surface = military.get("surface_deploy", 0.0)

        coalition_reliability = 0.5 * coalition + 0.5 * _clamp01(ctx.get("us_subs", 0) / 4.0)
        raw_bias = _clamp01(
            Params.ESCORT_BASE_BIAS * cargo_urgency
            + 0.44 * asw_priority
            + 0.36 * min(1.0, merchant_lost / 6.0)
            + 0.05 * max(0.0, -world_op)
            + 0.06 * (1.0 - coalition_reliability)
            - 0.18 * missile_threat
        )
        prev_bias = _runtime_state.get("prev_bias", 0.5)
        a = MomentumController.adaptive_alpha(cargo_urgency, ctx.get("threat_index", 0.5), prev_bias)
        bias = (1.0 - a) * prev_bias + a * raw_bias
        MomentumController.update_momentum(cargo_urgency, bias, ctx.get("threat_index", 0.5))

        total = surface + escort
        if total > 1.0:
            excess = total - 1.0
            keep_escort_factor = 1.12 if cargo_urgency > 0.62 else 1.0
            reduce_surface = excess * (1.0 - bias) * 0.92
            reduce_escort = excess * bias / keep_escort_factor
            surface = _clamp01(surface - reduce_surface)
            escort = _clamp01(escort - reduce_escort)
            if surface + escort > 1.0:
                if bias > 0.66 or cargo_urgency > Params.ESCORT_PRESERVE_THRESHOLD or merchant_lost > 1:
                    surface = _clamp01(1.0 - escort)
                else:
                    tot2 = surface + escort
                    if tot2 > 0:
                        surface = _clamp01(surface / tot2)
                        escort = _clamp01(escort / tot2)
                    else:
                        surface, escort = 0.5, 0.5

        if escort >= 0.995:
            surface = max(surface, Params.SURFACE_MIN)
            if surface + escort > 1.0:
                escort = _clamp01(1.0 - surface)

        transshipment_allow = True
        if hs > 0 and blockade < 0.72:
            transshipment_allow = False
        elif (hs > 0 or escalation >= 3) and cargo_urgency < 0.78:
            transshipment_allow = False
        if coalition > 0.70 and cargo_urgency > 0.56:
            transshipment_allow = True

        tw_econ = max(0.0, min(1.0, (100.0 - ctx.get("tw_economy", 100.0)) / 100.0))
        tw_elec = max(0.0, min(1.0, (100.0 - ctx.get("tw_electric", 100.0)) / 100.0))
        tw_morale = max(0.0, min(1.0, (0.9 - ctx.get("tw_morale", 0.9)) / 0.9))
        port_boost = 0.33 * tw_econ + 0.12 * tw_elec + 0.06 * tw_morale

        early_bonus = Params.PORT_EARLY_BONUS * (1.0 if ctx["is_early"] else 0.88)
        coalition_cargo_bonus = 0.22 * coalition * cargo_urgency
        missile_penalty = 0.10 * missile_threat if missile_threat <= 0.5 else (0.10 * 0.5 + 0.22 * (missile_threat - 0.5))

        port_capacity = _clamp01(
            Params.PORT_BASE
            + early_bonus
            + Params.PORT_BLOCKADE_SCALE * ctx["blockade"]
            - 0.08 * min(1.0, hs)
            + 0.36 * coalition
            + 0.38 * cargo_urgency
            + port_boost
            + coalition_cargo_bonus
            - missile_penalty
        )

        if coalition > 0.72 and cargo_urgency > 0.60:
            port_capacity = max(port_capacity, 0.66)

        return {
            "convoy_escort_commit": escort,
            "surface_deploy": surface,
            "transshipment_allow": transshipment_allow,
            "port_capacity_share": port_capacity,
        }

# -----------------------
# Political planner
# -----------------------
class PoliticalPlanner:
    @staticmethod
    def posture_and_bases(ctx: Dict[str, Any]) -> Dict[str, str]:
        blockade = ctx["blockade"]
        escalation = ctx["escalation"]
        hs = ctx["homeland_strikes"]
        week = ctx["week"]
        world_op = ctx["world_op"]
        coalition = ctx["coalition_support"]
        cargo_urgency = ctx["cargo_urgency"]

        if escalation >= 3 or hs > 0:
            posture = "self_defense_only"
        elif blockade >= 0.86 and cargo_urgency > 0.44 and week <= 14 and coalition > 0.20:
            posture = "proactive"
        elif blockade >= 0.74 and cargo_urgency > 0.58 and week <= 12:
            posture = "proactive"
        else:
            posture = "defensive"

        def decide_access():
            if hs > 0 or escalation >= 3:
                return "closed"
            if blockade >= 0.80 and coalition > 0.46 and cargo_urgency > 0.50 and week <= 12:
                return "open" if (coalition > 0.78 and world_op > -0.02) else "limited"
            return "limited"

        okinawa = decide_access()
        kyushu = decide_access()

        if world_op < -0.72 and cargo_urgency < 0.68:
            okinawa = "limited"
            kyushu = "limited"

        return {"engagement_posture": posture, "okinawa_access": okinawa, "kyushu_access": kyushu}

    @staticmethod
    def diplomacy_and_aid(ctx: Dict[str, Any]) -> Dict[str, Any]:
        week = ctx["week"]
        world_op = ctx["world_op"]
        blockade = ctx["blockade"]
        cargo_urgency = ctx["cargo_urgency"]
        escalation = ctx["escalation"]
        hs = ctx["homeland_strikes"]
        merchant_lost = ctx["merchant_lost"]

        if week <= 8:
            base = 0.995
        elif week <= 14:
            base = 0.92
        else:
            base = 0.78
        persistence = 0.30 * (blockade ** 2) if (week > 8 and blockade > 0.5) else 0.0
        merchant_bonus = 0.26 * min(1.0, merchant_lost / 6.0)
        diplo = _clamp01(base + persistence + merchant_bonus + 0.44 * max(0.0, -world_op) - 0.06 * escalation - 0.07 * min(1.0, hs))

        world_aid_boost = 0.20 * max(0.0, -world_op)
        human_aid = _clamp01(0.36 + 0.68 * cargo_urgency + 0.34 * blockade + world_aid_boost - 0.15 * min(1.0, hs))

        sanctions_advocacy = True if escalation <= 2 and world_op > -0.66 else False

        return {"diplomatic_pressure": diplo, "humanitarian_aid": human_aid, "sanctions_advocacy": sanctions_advocacy}

# -----------------------
# Orchestration pipeline
# -----------------------
class PlannerPipeline:
    @staticmethod
    def synthesize(state: dict) -> dict:
        extractor = SignalExtractor(state)
        ctx = extractor.ctx

        mil = MilitaryPlanner.plan(ctx)
        logi = LogisticsPlanner.plan(ctx, mil)
        post = PoliticalPlanner.posture_and_bases(ctx)
        dip = PoliticalPlanner.diplomacy_and_aid(ctx)

        final_sub = _clamp01(mil["submarine_deploy"])
        final_air = _clamp01(mil["air_sortie_rate"])
        final_surface = _clamp01(logi["surface_deploy"])
        final_escort = _clamp01(logi["convoy_escort_commit"])

        cargo_urgency = float(ctx.get("cargo_urgency", 0.0))
        asw_priority = float(mil.get("asw_priority", 0.0))
        missile_threat = float(ctx.get("missile_threat", 0.0))
        coalition_reliability = 0.5 * ctx.get("coalition_support", 0.0) + 0.5 * _clamp01(ctx.get("us_subs", 0) / 4.0)

        total = final_surface + final_escort
        if total > 1.0:
            bias_raw = 0.66 * cargo_urgency + 0.30 * asw_priority + 0.06 * (1.0 - coalition_reliability) - 0.18 * missile_threat
            prev_bias = _runtime_state.get("prev_bias", 0.5)
            a = MomentumController.adaptive_alpha(cargo_urgency, ctx.get("threat_index", 0.5), prev_bias)
            bias = (1.0 - a) * prev_bias + a * _clamp01(bias_raw)
            MomentumController.update_momentum(cargo_urgency, bias, ctx.get("threat_index", 0.5))
            if ctx["merchant_lost"] > 2:
                bias = max(bias, 0.96)

            excess = total - 1.0
            preserve_factor = 1.12 if cargo_urgency > Params.ESCORT_PRESERVE_THRESHOLD else 1.0
            final_surface = _clamp01(final_surface - excess * (1.0 - bias) * 0.94)
            final_escort = _clamp01(final_escort - (excess * bias) / preserve_factor)

            if final_surface + final_escort > 1.0:
                if bias > 0.66 or cargo_urgency > Params.ESCORT_PRESERVE_THRESHOLD or ctx["merchant_lost"] > 1:
                    final_surface = _clamp01(1.0 - final_escort)
                else:
                    tot2 = final_surface + final_escort
                    if tot2 > 0:
                        final_surface = _clamp01(final_surface / tot2)
                        final_escort = _clamp01(final_escort / tot2)
                    else:
                        final_surface, final_escort = 0.5, 0.5

            if final_escort > 0.995:
                final_surface = max(final_surface, Params.SURFACE_MIN)
                if final_surface + final_escort > 1.0:
                    final_escort = _clamp01(1.0 - final_surface)

        # Reallocate to air in missile scenarios, prefer surface pulls then escort
        if missile_threat > 0.30:
            desired_air_floor = _clamp01(0.16 + 0.52 * missile_threat)
            if final_air < desired_air_floor:
                shortfall = desired_air_floor - final_air
                s_share = final_surface + 0.6 * final_escort
                if s_share > 0:
                    pull_surface = min(final_surface, shortfall * (final_surface / s_share) * 1.35)
                    pull_escort = min(final_escort, shortfall * (0.6 * final_escort / s_share) * 0.95)
                    safe_escort_floor = max(0.08, Params.SURFACE_MIN * 0.85)
                    if final_escort - pull_escort < safe_escort_floor:
                        pull_escort = max(0.0, final_escort - safe_escort_floor)
                else:
                    pull_surface = pull_escort = 0.0
                final_surface = _clamp01(final_surface - pull_surface)
                final_escort = _clamp01(final_escort - pull_escort)
                final_air = _clamp01(final_air + pull_surface + pull_escort)
                if final_surface + final_escort > 1.0:
                    tot2 = final_surface + final_escort
                    final_surface = _clamp01(final_surface / tot2)
                    final_escort = _clamp01(final_escort / tot2)

        actions = {
            "surface_deploy": final_surface,
            "submarine_deploy": final_sub,
            "air_sortie_rate": final_air,
            "okinawa_access": post["okinawa_access"],
            "kyushu_access": post["kyushu_access"],
            "transshipment_allow": logi["transshipment_allow"],
            "convoy_escort_commit": final_escort,
            "port_capacity_share": logi["port_capacity_share"],
            "engagement_posture": post["engagement_posture"],
            "asw_priority": mil["asw_priority"],
            "diplomatic_pressure": dip["diplomatic_pressure"],
            "sanctions_advocacy": dip["sanctions_advocacy"],
            "humanitarian_aid": dip["humanitarian_aid"],
        }
        return actions

# Public entrypoint
def synthesize_actions(state: dict) -> dict:
    return PlannerPipeline.synthesize(state)

def japan_strategy(state: dict) -> dict:
    """Japan's turn-by-turn strategy. Returns actions dict."""
    return synthesize_actions(state)

# EVOLVE-BLOCK-END