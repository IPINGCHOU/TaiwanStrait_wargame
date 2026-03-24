"""ShinkaEvolve evaluation harness — runs evolved japan_strategy across scenarios."""

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


def run_evaluation(strategy_fn, results_dir: str = None) -> dict:
    """Run the strategy across all scenarios and seeds, return aggregated fitness."""
    all_results = []

    for scenario in EVALUATION_SCENARIOS:
        scenario_scores = []
        for seed in range(SEEDS_PER_SCENARIO):
            game = WarGame(scenario=scenario, seed=seed)

            while not game.is_done():
                state = game.get_state()
                actions = strategy_fn(state)
                game.step(actions)

            result = game.get_result()
            scenario_scores.append({
                "score": result["score"]["total"],
                "taiwan_survived": result["taiwan_survived"],
                "weeks": result["weeks"],
                "final_electricity": result["score"].get("B_taiwan_survival", 0),
                "final_escalation": result["state_history"][-1]["escalation_level"] if result["state_history"] else 0,
            })

        avg_score = np.mean([r["score"] for r in scenario_scores])
        win_rate = np.mean([r["taiwan_survived"] for r in scenario_scores])

        all_results.append({
            "scenario": scenario["name"],
            "avg_score": float(avg_score),
            "win_rate": float(win_rate),
            "runs": scenario_scores,
        })

    # Flatten for fitness aggregation
    flat_results = []
    for sr in all_results:
        for run in sr["runs"]:
            flat_results.append(run)

    combined_fitness = compute_fitness_aggregate(flat_results)

    output = {
        "combined_score": float(combined_fitness),
        "public": {
            "combined_fitness": round(float(combined_fitness), 2),
            "avg_score": round(float(np.mean([r["score"] for r in flat_results])), 2),
            "win_rate": round(float(np.mean([r["taiwan_survived"] for r in flat_results])), 3),
            "min_scenario_avg": round(float(min(r["avg_score"] for r in all_results)), 2),
        },
        "private": {
            "per_scenario": all_results,
        },
    }

    # Save results if directory provided
    if results_dir:
        os.makedirs(results_dir, exist_ok=True)
        with open(os.path.join(results_dir, "results.json"), "w") as f:
            json.dump(output, f, indent=2, default=str)

    return output


def main():
    parser = argparse.ArgumentParser(description="Evaluate evolved Japan strategy")
    parser.add_argument("--program_path", required=True, help="Path to evolved initial.py")
    parser.add_argument("--results_dir", required=True, help="Directory to save results")
    args = parser.parse_args()

    strategy_fn = load_strategy(args.program_path)
    result = run_evaluation(strategy_fn, args.results_dir)

    # Print for ShinkaEvolve to capture
    print(json.dumps(result["public"], indent=2))


if __name__ == "__main__":
    main()
