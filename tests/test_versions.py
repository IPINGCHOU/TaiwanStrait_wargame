"""Tests for dashboard.versions — version discovery and strategy loading."""

import sys
import os
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from dashboard.versions import discover_versions, load_strategy


def test_discover_versions_finds_baseline():
    project_root = os.path.join(os.path.dirname(__file__), "..")
    versions = discover_versions(project_root)
    names = [v["name"] for v in versions]
    assert names[0] == "baseline (initial.py)"
    assert versions[0]["type"] == "baseline"


def test_discover_versions_finds_best():
    project_root = os.path.join(os.path.dirname(__file__), "..")
    versions = discover_versions(project_root)
    names = [v["name"] for v in versions]
    assert names[-1] == "best"
    assert versions[-1]["type"] == "best"


def test_discover_versions_includes_generations():
    project_root = os.path.join(os.path.dirname(__file__), "..")
    versions = discover_versions(project_root)
    gen_versions = [v for v in versions if v["type"] == "generation"]
    assert len(gen_versions) > 0
    gen_names = [v["name"] for v in gen_versions]
    assert "gen_0" in gen_names


def test_discover_versions_sampled_includes_milestones():
    project_root = os.path.join(os.path.dirname(__file__), "..")
    versions = discover_versions(project_root, show_all=False)
    gen_names = [v["name"] for v in versions if v["type"] == "generation"]
    for name in ["gen_0", "gen_50", "gen_100"]:
        if os.path.isdir(os.path.join(project_root, "results", name)):
            assert name in gen_names, f"{name} should be in sampled list"


def test_discover_versions_show_all():
    project_root = os.path.join(os.path.dirname(__file__), "..")
    sampled = discover_versions(project_root, show_all=False)
    full = discover_versions(project_root, show_all=True)
    assert len(full) >= len(sampled)


def test_load_strategy_baseline():
    project_root = os.path.join(os.path.dirname(__file__), "..")
    path = os.path.join(project_root, "shinka_task", "initial.py")
    fn = load_strategy(path)
    assert fn is not None
    assert callable(fn)


def test_load_strategy_returns_none_on_bad_file():
    with tempfile.NamedTemporaryFile(suffix=".py", mode="w", delete=False) as f:
        f.write("this is not valid python {{{{")
        f.flush()
        fn = load_strategy(f.name)
    os.unlink(f.name)
    assert fn is None


def test_load_strategy_returns_none_on_missing_function():
    with tempfile.NamedTemporaryFile(suffix=".py", mode="w", delete=False) as f:
        f.write("def other_function(): pass\n")
        f.flush()
        fn = load_strategy(f.name)
    os.unlink(f.name)
    assert fn is None
