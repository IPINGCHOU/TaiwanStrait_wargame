"""Generate country behavior profiles using DeepSeek API.

Usage:
    export DEEPSEEK_API_KEY="your-key"
    python profiles/generate_profiles.py

Saves generated profiles to profiles/generated/ for review before
curating into china.py, us.py, taiwan.py.
"""

import os
import json
from openai import OpenAI

client = OpenAI(
    api_key=os.environ.get("DEEPSEEK_API_KEY"),
    base_url="https://api.deepseek.com",
)

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "generated")
os.makedirs(OUTPUT_DIR, exist_ok=True)


PROMPTS = {
    "china_aggressive": """Write a Python function `aggressive(state: dict) -> dict` for China's strategy in a Taiwan Strait blockade wargame.

Profile: "aggressive" — China maximizes blockade pressure, deploys forces at 0.8-1.0 intensity, uses 80-100 missiles per turn, targets military early then infrastructure later, willing to escalate.

The state dict contains: week (1-20), china_surface_ships, china_submarines, china_aircraft, china_missiles, china_coast_guard, china_morale, taiwan_economy_pct, total_cargo_delivered, blockade_tightness, escalation_level.

Return dict must have these exact keys:
- blockade_enforcement: float 0-1
- submarine_patrol: float 0-1
- surface_deploy: float 0-1
- air_sortie_rate: float 0-1
- missile_budget: int (don't exceed china_missiles)
- target_priority: "convoys" | "military" | "infrastructure"
- coast_guard_boarding: float 0-1

Write a deterministic function with no randomness. Use if/elif on state values for reactive behavior. Keep it under 40 lines.""",

    "china_adaptive": """Write a Python function `adaptive(state: dict) -> dict` for China in a Taiwan Strait blockade wargame.

Profile: "adaptive" — China adjusts to game state. If Taiwan economy is dropping, maintain posture. If losing ships fast, pull back surface and rely on subs. If convoys getting through, tighten blockade. Moderate missile use (30-50/turn).

[Same state dict and return dict as above]

Write a deterministic function, no randomness, under 40 lines.""",

    "china_cautious": """Write a Python function `cautious(state: dict) -> dict` for China in a Taiwan Strait blockade wargame.

Profile: "cautious" — Low deployment (0.3-0.5), moderate blockade (0.5), minimal missiles (10-20/turn), targets only convoys, coast guard focus. Avoids escalation. Preserves forces.

[Same state dict and return dict as above]

Write a deterministic function, no randomness, under 20 lines.""",

    "us_interventionist": """Write a Python function `interventionist(state: dict) -> dict` for the US in a Taiwan Strait blockade wargame.

Profile: "interventionist" — Heavy deployment (0.7-0.9 subs, 0.5-0.7 surface), aggressive posture, high missile use (50-80/turn), provides missile defense to Japan. Increases commitment if Taiwan economy drops below 50%.

State dict contains: week, us_surface_ships, us_submarines, us_aircraft, us_missiles, taiwan_economy_pct, escalation_level, blockade_tightness.

Return dict keys:
- submarine_deploy: float 0-1
- surface_deploy: float 0-1
- air_sortie_rate: float 0-1
- missile_budget: int
- engagement_posture: "defensive" | "balanced" | "aggressive"
- convoy_escort_commit: float 0-1
- japan_missile_defense: bool

Deterministic, no randomness, under 30 lines.""",

    "us_restrained": """Write a Python function `restrained(state: dict) -> dict` for the US.

Profile: "restrained" — Low deployment (0.3-0.4), defensive posture, minimal missiles (10-20/turn), no missile defense for Japan unless escalation >= 3. Prioritizes convoy escort.

[Same return dict as interventionist]

Deterministic, no randomness, under 20 lines.""",

    "taiwan_resilient": """Write a Python function `resilient(state: dict) -> dict` for Taiwan.

Profile: "resilient" — Strict rationing early, high reserve mobilization (0.6-0.8), active coastal defense, defensive missiles (20-40/turn), propaganda for morale. Convoys size 8-12 via japan_transship.

State contains: week, taiwan_surface_ships, taiwan_aircraft, taiwan_missiles, taiwan_reserves, taiwan_morale, taiwan_energy_gas, taiwan_energy_coal, taiwan_energy_oil, taiwan_economy_pct.

Return dict keys:
- surface_deploy: float 0-1
- rationing_level: "none" | "moderate" | "severe"
- reserve_mobilization: float 0-1
- coastal_defense_posture: "passive" | "active" | "aggressive"
- missile_budget: int
- morale_policy: "normal" | "propaganda" | "martial_law"
- convoy_size: int 0-20
- convoy_route: "direct" | "japan_transship" | "southern"

Deterministic, no randomness, under 30 lines.""",

    "taiwan_defeatist": """Write a Python function `defeatist(state: dict) -> dict` for Taiwan.

Profile: "defeatist" — Late/no rationing, low mobilization (0.2-0.3), passive defense, minimal missiles (5-10), normal morale policy. Small convoys (3-5) via direct route.

[Same return dict as resilient]

Deterministic, no randomness, under 20 lines.""",
}


def generate_profile(name, prompt):
    """Call DeepSeek to generate a profile function."""
    print(f"Generating {name}...")
    response = client.chat.completions.create(
        model="deepseek-chat",
        messages=[
            {"role": "system", "content": "You are a Python programmer. Output only the function, no markdown fences."},
            {"role": "user", "content": prompt},
        ],
        temperature=0.3,
        max_tokens=1000,
    )
    code = response.choices[0].message.content.strip()

    # Save to file
    out_path = os.path.join(OUTPUT_DIR, f"{name}.py")
    with open(out_path, "w") as f:
        f.write(code)
    print(f"  Saved to {out_path}")
    return code


if __name__ == "__main__":
    if not os.environ.get("DEEPSEEK_API_KEY"):
        print("Set DEEPSEEK_API_KEY environment variable first.")
        exit(1)

    for name, prompt in PROMPTS.items():
        generate_profile(name, prompt)

    print(f"\nDone! Generated profiles saved to {OUTPUT_DIR}/")
    print("Review and curate into profiles/china.py, profiles/us.py, profiles/taiwan.py")
