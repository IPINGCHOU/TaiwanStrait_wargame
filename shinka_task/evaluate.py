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


def load_strategy(program_path: str):
    """Load japan_strategy function from the evolved program file."""
    spec = importlib.util.spec_from_file_location("evolved_module", program_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.japan_strategy


def run_evaluation(strategy_fn) -> dict:
    """Run the strategy across all scenarios and seeds, return aggregated metrics."""
    flat_results = []

    scenario_summaries = []
    for scenario in EVALUATION_SCENARIOS:
        scenario_scores = []
        for seed in range(SEEDS_PER_SCENARIO):
            game = WarGame(scenario=scenario, seed=seed)

            while not game.is_done():
                state = game.get_state()
                actions = strategy_fn(state)
                game.step(actions)

            result = game.get_result()
            run = {
                "score": result["score"]["total"],
                "taiwan_survived": result["taiwan_survived"],
                "weeks": result["weeks"],
            }
            scenario_scores.append(run)
            flat_results.append(run)

        avg_score = float(np.mean([r["score"] for r in scenario_scores]))
        win_rate = float(np.mean([r["taiwan_survived"] for r in scenario_scores]))
        scenario_summaries.append({
            "scenario": scenario["name"],
            "avg_score": avg_score,
            "win_rate": win_rate,
        })

    combined_fitness = float(compute_fitness_aggregate(flat_results))

    return {
        "combined_score": combined_fitness,
        "public": {
            "combined_fitness": round(combined_fitness, 2),
            "avg_score": round(float(np.mean([r["score"] for r in flat_results])), 2),
            "win_rate": round(float(np.mean([r["taiwan_survived"] for r in flat_results])), 3),
            "min_scenario_avg": round(float(min(s["avg_score"] for s in scenario_summaries)), 2),
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
