"""ShinkaEvolve evaluation harness — runs evolved japan_strategy across scenarios.

Contract: ShinkaEvolve calls this as:
    python evaluate.py --program_path <evolved_initial.py> --results_dir <dir>

Must write to results_dir:
    - metrics.json  (must contain "combined_score" float)
    - correct.json  ({"correct": bool, "error": str|null})
"""

import sys
import os
import argparse
import json
import importlib.util

import numpy as np

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from wargame.engine import WarGame
from wargame.scenarios import EVALUATION_SCENARIOS
from wargame.scoring import compute_fitness_aggregate


SEEDS_PER_SCENARIO = 5

# Per-scenario normalization ranges (floor=passive Japan, ceiling=estimated best)
# Each scenario's raw score is normalized to 0-100 so they contribute equally.
SCENARIO_RANGES = {
    "baseline": {"floor": -50, "ceiling": 400},
    "surge":    {"floor": -350, "ceiling": 100},
    "degraded": {"floor": -270, "ceiling": 300},
}


def _normalize(raw_score: float, scenario_name: str) -> float:
    """Normalize a raw scenario score to 0-100."""
    r = SCENARIO_RANGES.get(scenario_name, {"floor": -500, "ceiling": 500})
    span = r["ceiling"] - r["floor"]
    if span <= 0:
        return 50.0
    normalized = (raw_score - r["floor"]) / span * 100.0
    return max(0.0, min(100.0, normalized))


def load_strategy(program_path: str):
    """Load japan_strategy function from the evolved program file."""
    spec = importlib.util.spec_from_file_location("evolved_module", program_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.japan_strategy


def run_evaluation(strategy_fn) -> dict:
    """Run the strategy across all scenarios and seeds, return aggregated metrics."""
    scenario_summaries = []
    all_normalized = []
    all_wins = []

    for scenario in EVALUATION_SCENARIOS:
        scenario_raw = []
        scenario_norm = []
        scenario_wins = []
        for seed in range(SEEDS_PER_SCENARIO):
            game = WarGame(scenario=scenario, seed=seed)

            while not game.is_done():
                state = game.get_state()
                actions = strategy_fn(state)
                game.step(actions)

            result = game.get_result()
            raw = result["score"]["total"]
            norm = _normalize(raw, scenario["name"])

            scenario_raw.append(raw)
            scenario_norm.append(norm)
            scenario_wins.append(result["taiwan_survived"])

        avg_raw = float(np.mean(scenario_raw))
        avg_norm = float(np.mean(scenario_norm))
        win_rate = float(np.mean(scenario_wins))
        all_normalized.extend(scenario_norm)
        all_wins.extend(scenario_wins)

        scenario_summaries.append({
            "scenario": scenario["name"],
            "avg_raw_score": round(avg_raw, 1),
            "avg_normalized": round(avg_norm, 1),
            "win_rate": win_rate,
        })

    # Fitness: avg normalized score (0-100) + win_rate bonus
    avg_norm_all = float(np.mean(all_normalized))
    min_scenario_norm = float(min(s["avg_normalized"] for s in scenario_summaries))
    overall_win_rate = float(np.mean(all_wins))

    # combined_score: 0-1000 scale with win bonus
    # avg_norm × 6 + min_scenario × 2.5 + win_rate × 150
    combined = avg_norm_all * 6 + min_scenario_norm * 2.5 + overall_win_rate * 150

    return {
        "combined_score": combined,
        "public": {
            "combined_score": round(combined, 2),
            "avg_normalized": round(avg_norm_all, 1),
            "min_scenario_normalized": round(min_scenario_norm, 1),
            "win_rate": round(overall_win_rate, 3),
        },
        "private": {
            "per_scenario": scenario_summaries,
        },
    }


def main():
    parser = argparse.ArgumentParser(description="Evaluate evolved Japan strategy")
    parser.add_argument("--program_path", required=True, help="Path to evolved initial.py")
    parser.add_argument("--results_dir", required=True, help="Directory to save results")
    args = parser.parse_args()

    os.makedirs(args.results_dir, exist_ok=True)

    try:
        strategy_fn = load_strategy(args.program_path)
        metrics = run_evaluation(strategy_fn)
        correct = True
        error = None
    except Exception as e:
        metrics = {"combined_score": 0.0}
        correct = False
        error = str(e)

    # Write metrics.json (ShinkaEvolve reads combined_score from here)
    with open(os.path.join(args.results_dir, "metrics.json"), "w") as f:
        json.dump(metrics, f, indent=4)

    # Write correct.json (ShinkaEvolve reads correctness from here)
    with open(os.path.join(args.results_dir, "correct.json"), "w") as f:
        json.dump({"correct": correct, "error": error}, f, indent=4)

    print(json.dumps(metrics.get("public", metrics), indent=2))


if __name__ == "__main__":
    main()
