"""Version discovery and strategy loading for the Compare tab."""

import os
import re
import importlib.util


_EARLY_GENS = {0, 1, 5, 10}
_SAMPLE_INTERVAL = 50


def discover_versions(project_root, show_all=False):
    """Discover available strategy versions.

    Returns list of {"name": str, "path": str, "type": str} sorted:
    baseline first, generations in numeric order, best last.
    """
    versions = []

    # 1. Baseline
    baseline_path = os.path.join(project_root, "shinka_task", "initial.py")
    if os.path.isfile(baseline_path):
        versions.append({
            "name": "baseline (initial.py)",
            "path": baseline_path,
            "type": "baseline",
        })

    # 2. Generation snapshots
    results_dir = os.path.join(project_root, "results")
    if os.path.isdir(results_dir):
        gen_dirs = []
        for entry in os.listdir(results_dir):
            m = re.match(r"^gen_(\d+)$", entry)
            if m:
                gen_num = int(m.group(1))
                main_path = os.path.join(results_dir, entry, "main.py")
                if os.path.isfile(main_path):
                    gen_dirs.append((gen_num, entry, main_path))
        gen_dirs.sort(key=lambda x: x[0])

        for gen_num, name, path in gen_dirs:
            if show_all or gen_num in _EARLY_GENS or gen_num % _SAMPLE_INTERVAL == 0:
                versions.append({
                    "name": name,
                    "path": path,
                    "type": "generation",
                })

    # 3. Best
    best_path = os.path.join(results_dir, "best", "main.py")
    if os.path.isfile(best_path):
        versions.append({
            "name": "best",
            "path": best_path,
            "type": "best",
        })

    return versions


def load_strategy(path):
    """Dynamically import japan_strategy from a .py file.

    Returns callable japan_strategy function, or None if loading fails.
    """
    try:
        spec = importlib.util.spec_from_file_location("_strategy_module", path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        fn = getattr(module, "japan_strategy")
        if not callable(fn):
            return None
        return fn
    except Exception:
        return None
