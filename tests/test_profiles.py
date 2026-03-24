from profiles import PROFILES
from wargame.scenarios import EVALUATION_SCENARIOS, build_initial_state

CHINA_KEYS = {"blockade_enforcement", "submarine_patrol", "surface_deploy",
              "air_sortie_rate", "missile_budget", "target_priority", "coast_guard_boarding"}
US_KEYS = {"submarine_deploy", "surface_deploy", "air_sortie_rate",
           "missile_budget", "engagement_posture", "convoy_escort_commit", "japan_missile_defense"}
TAIWAN_KEYS = {"surface_deploy", "rationing_level", "reserve_mobilization",
               "coastal_defense_posture", "missile_budget", "morale_policy",
               "convoy_size", "convoy_route"}


def test_all_profiles_return_valid_keys():
    state = build_initial_state(EVALUATION_SCENARIOS[0])
    for name, fn in PROFILES["china"].items():
        actions = fn(state)
        assert CHINA_KEYS.issubset(actions.keys()), f"China/{name} missing keys: {CHINA_KEYS - actions.keys()}"
    for name, fn in PROFILES["us"].items():
        actions = fn(state)
        assert US_KEYS.issubset(actions.keys()), f"US/{name} missing keys: {US_KEYS - actions.keys()}"
    for name, fn in PROFILES["taiwan"].items():
        actions = fn(state)
        assert TAIWAN_KEYS.issubset(actions.keys()), f"Taiwan/{name} missing keys: {TAIWAN_KEYS - actions.keys()}"


def test_profiles_respect_bounds():
    state = build_initial_state(EVALUATION_SCENARIOS[0])
    for country, profiles in PROFILES.items():
        for name, fn in profiles.items():
            actions = fn(state)
            for k, v in actions.items():
                if isinstance(v, float):
                    assert 0.0 <= v <= 1.0, f"{country}/{name}.{k} = {v} out of [0,1]"
                if k == "missile_budget":
                    assert v >= 0, f"{country}/{name}.missile_budget negative"
                if k == "convoy_size":
                    assert 0 <= v <= 20, f"{country}/{name}.convoy_size = {v} out of [0,20]"


def test_profiles_work_across_all_scenarios():
    for scenario in EVALUATION_SCENARIOS:
        state = build_initial_state(scenario)
        for country, profiles in PROFILES.items():
            for name, fn in profiles.items():
                actions = fn(state)
                assert isinstance(actions, dict), f"{country}/{name} didn't return dict for {scenario['name']}"
