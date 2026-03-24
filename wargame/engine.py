"""WarGame engine — orchestrates the full turn sequence."""

import copy
import numpy as np

from profiles import PROFILES
from wargame.constants import (
    MAX_WEEKS, BASE_BLOCKADE_LEVEL, SURRENDER_MORALE_HARD,
    SURRENDER_MORALE_SOFT, SURRENDER_ECONOMY_THRESHOLD,
    JAPAN_POSTURE_MODIFIER,
)
from wargame.combat import (
    resolve_naval, resolve_convoy, update_blockade_tightness,
    resolve_missiles, check_homeland_strikes,
)
from wargame.economy import update_taiwan_economy, update_japan_economy
from wargame.escalation import compute_escalation, update_world_opinion
from wargame.scoring import compute_score
from wargame.scenarios import build_initial_state


class WarGame:
    """Turn-based Taiwan Strait blockade simulation."""

    def __init__(self, scenario: dict, seed: int = 0):
        self.state = build_initial_state(scenario)
        self.rng = np.random.RandomState(seed)
        self.state_history = []
        self._done = False
        self._taiwan_survived = True
        self.turn_actions = []

        # Load country profiles from registry
        china_name = self.state.pop("china_profile")
        us_name = self.state.pop("us_profile")
        taiwan_name = self.state.pop("taiwan_profile")
        self._china_profile = PROFILES["china"][china_name]
        self._us_profile = PROFILES["us"][us_name]
        self._taiwan_profile = PROFILES["taiwan"][taiwan_name]
        self._china_profile_name = china_name

    def get_state(self) -> dict:
        """Return a deep copy of the current state."""
        return copy.deepcopy(self.state)

    def is_done(self) -> bool:
        return self._done

    def step(self, japan_actions: dict):
        """Execute one turn (1 week)."""
        if self._done:
            return

        s = self.state

        # --- Step 1: All players decide (simultaneous — use frozen snapshot) ---
        snapshot = copy.deepcopy(s)
        china_actions = self._china_profile(snapshot)
        us_actions = self._us_profile(snapshot)
        taiwan_actions = self._taiwan_profile(snapshot)

        # --- Step 2: Clamp & validate ---
        # Missile budget clamping
        china_actions["missile_budget"] = min(
            china_actions["missile_budget"], s["china_missiles"]
        )
        us_actions["missile_budget"] = min(
            us_actions["missile_budget"], s["us_missiles"]
        )
        taiwan_actions["missile_budget"] = min(
            taiwan_actions["missile_budget"], s["taiwan_missiles"]
        )

        # Force conservation: surface_deploy + convoy_escort_commit <= 1.0
        for actions in [us_actions, japan_actions]:
            deploy = actions.get("surface_deploy", 0)
            escort = actions.get("convoy_escort_commit", 0)
            total = deploy + escort
            if total > 1.0:
                scale = 1.0 / total
                actions["surface_deploy"] = deploy * scale
                actions["convoy_escort_commit"] = escort * scale

        # --- Step 3: Naval combat ---
        coalition_actions = {
            "us": us_actions,
            "japan": japan_actions,
            "taiwan": taiwan_actions,
        }
        prev_civilians = s["civilian_casualties"]

        naval_result = resolve_naval(s, coalition_actions, china_actions, self.rng)

        # Apply naval losses
        s["us_surface_ships"] = max(0, s["us_surface_ships"] - naval_result["us_losses"])
        s["japan_surface_ships"] = max(0, s["japan_surface_ships"] - naval_result["japan_losses"])
        s["taiwan_surface_ships"] = max(0, s["taiwan_surface_ships"] - naval_result["taiwan_losses"])
        s["china_surface_ships"] = max(0, s["china_surface_ships"] - naval_result["china_surface_losses"])
        s["china_submarines"] = max(0, s["china_submarines"] - naval_result["china_sub_losses"])

        # Track Japan-specific losses and kill attribution
        s["japan_ships_lost"] += naval_result["japan_losses"]
        s["china_subs_neutralized_by_jmsdf"] += naval_result.get("china_subs_by_jmsdf", 0)
        s["china_ships_neutralized_by_jmsdf"] += naval_result.get("china_ships_by_jmsdf", 0)

        combat_occurred = (
            naval_result["us_losses"] + naval_result["japan_losses"] +
            naval_result["taiwan_losses"] + naval_result["china_surface_losses"] +
            naval_result["china_sub_losses"]
        ) > 0

        # --- Step 4: Missile exchanges ---
        missile_result = resolve_missiles(
            s, china_actions, us_actions, taiwan_actions, s["escalation_level"]
        )
        if missile_result["total_missiles_fired"] > 0:
            combat_occurred = True

        # --- Step 5: Convoy resolution ---
        convoy_size = taiwan_actions.get("convoy_size", 5)
        convoy_route = taiwan_actions.get("convoy_route", "direct")

        # Compute escort and threat for convoy
        us_escort = s["us_surface_ships"] * us_actions.get("convoy_escort_commit", 0)
        japan_escort = s["japan_surface_ships"] * japan_actions.get("convoy_escort_commit", 0)
        sub_screen = (
            s["us_submarines"] * us_actions.get("submarine_deploy", 0) * 0.3 +
            s["japan_submarines"] * japan_actions.get("submarine_deploy", 0) *
            japan_actions.get("asw_priority", 0.5) * 0.3
        )
        escort_strength = us_escort + japan_escort + sub_screen

        threat = s["blockade_tightness"] * (
            s["china_submarines"] * 0.4 +
            s["china_surface_ships"] * 0.1 +
            s["china_aircraft"] * 0.005
        )

        convoy_result = resolve_convoy(
            escort_strength, threat, convoy_size, convoy_route, self.rng
        )

        s["total_cargo_delivered"] += convoy_result["cargo_delivered"]
        s["merchant_ships_lost"] += convoy_result["ships_lost"]
        s["cargo_per_turn"].append(convoy_result["cargo_delivered"])

        # Track cargo via Japan
        cargo_via_japan = (
            convoy_result["cargo_delivered"] if convoy_route == "japan_transship" else 0
        )

        # --- Step 6: Escalation (after combat, using actual outcomes) ---
        all_actions = {
            "china": china_actions,
            "us": us_actions,
            "japan": japan_actions,
            "taiwan": taiwan_actions,
        }
        self.turn_actions.append(copy.deepcopy(all_actions))
        new_escalation = compute_escalation(
            s, all_actions, prev_civilians, combat_occurred
        )
        if new_escalation < s["escalation_level"]:
            s["escalation_decreased"] = True
        s["escalation_level"] = new_escalation
        s["escalation_sum"] += new_escalation

        # --- Step 7: Homeland strike check ---
        check_homeland_strikes(s, self._china_profile_name)

        # --- Step 8: Taiwan economy update ---
        rationing = taiwan_actions.get("rationing_level", "none")
        update_taiwan_economy(s, convoy_result["cargo_delivered"], rationing)

        # --- Step 9: Japan economy update ---
        update_japan_economy(s, japan_actions, cargo_via_japan)

        # Update world opinion
        update_world_opinion(s, all_actions, s["escalation_level"])

        # --- Track derived fields ---
        # Blockade tightness
        china_forces = {
            "surface_ships": s["china_surface_ships"],
            "submarines": s["china_submarines"],
            "coast_guard": s.get("china_coast_guard", 40),
        }
        coalition_deployed = {
            "us_surface": s["us_surface_ships"] * us_actions.get("surface_deploy", 0),
            "us_subs": s["us_submarines"] * us_actions.get("submarine_deploy", 0),
            "japan_surface": s["japan_surface_ships"] * japan_actions.get("surface_deploy", 0),
            "japan_subs": s["japan_submarines"] * japan_actions.get("submarine_deploy", 0),
        }
        s["blockade_tightness"] = update_blockade_tightness(
            china_actions, china_forces, coalition_deployed
        )
        s["peak_blockade_tightness"] = max(
            s["peak_blockade_tightness"], s["blockade_tightness"]
        )

        # Japan average deployment
        japan_deploy = (
            japan_actions.get("surface_deploy", 0) +
            japan_actions.get("submarine_deploy", 0) +
            japan_actions.get("air_sortie_rate", 0)
        ) / 3.0
        week = s["week"]
        s["japan_avg_deploy"] = (
            (s["japan_avg_deploy"] * (week - 1) + japan_deploy) / week
        )

        # Article 9 violations
        if japan_actions.get("engagement_posture") == "proactive":
            s["japan_article9_violations"] += 1

        # US missile defense
        s["us_japan_missile_defense"] = us_actions.get("japan_missile_defense", False)

        # Japan blockade reduction share
        if s["peak_blockade_tightness"] > 0:
            japan_counter = (
                s["japan_surface_ships"] * japan_actions.get("surface_deploy", 0) * 0.15 +
                s["japan_submarines"] * japan_actions.get("submarine_deploy", 0) * 0.2
            )
            total_counter = (
                coalition_deployed["us_surface"] * 0.2 +
                coalition_deployed["us_subs"] * 0.3 +
                japan_counter
            )
            if total_counter > 0:
                s["japan_blockade_reduction_share"] = japan_counter / total_counter

        # Save state snapshot
        self.state_history.append(copy.deepcopy(s))

        # --- Step 10: End-condition check ---
        morale = s["taiwan_morale"]
        economy = s["taiwan_economy_pct"]
        if morale < SURRENDER_MORALE_HARD or (
            morale < SURRENDER_MORALE_SOFT and economy < SURRENDER_ECONOMY_THRESHOLD
        ):
            self._done = True
            self._taiwan_survived = False

        if s["week"] >= MAX_WEEKS:
            self._done = True

        s["week"] += 1

    def get_result(self) -> dict:
        """Return game result with score breakdown."""
        weeks_played = self.state["week"] - 1  # week was incremented after last step
        score = compute_score(
            self.state, self._taiwan_survived, weeks_played
        )
        return {
            "score": score,
            "weeks": weeks_played,
            "taiwan_survived": self._taiwan_survived,
            "state_history": self.state_history,
            "turn_actions": self.turn_actions,
        }
