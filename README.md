# shinka-wargame

Evolving Japan's coalition strategy for a Taiwan Strait naval blockade using [ShinkaEvolve](https://pypi.org/project/shinka-evolve/).

## Overview

A turn-based simulation of a 20-week Chinese naval blockade of Taiwan with four players — China, US, Taiwan, and Japan. China, US, and Taiwan are controlled by LLM-generated deterministic strategy profiles. **Japan's strategy is evolved by ShinkaEvolve** — an LLM-driven evolutionary code synthesis framework that discovers optimal decision-making logic through program evolution.

The core insight: instead of using LLMs to role-play as countries (like WarAgent), we let ShinkaEvolve evolve the decision algorithm itself. The resulting strategy is a pure Python function — deterministic, fast, and fully inspectable.

### Why This Matters

The Taiwan Strait is arguably the most consequential theater for Japan's national security. Japan's decisions in a blockade scenario — JMSDF deployment, base access for US forces, convoy transshipment through Japanese waters, escalation management — are under-explored in wargaming literature. This project uses evolutionary optimization to discover robust strategies across multiple scenarios.

## Installation

```bash
pip install -r requirements.txt
# ShinkaEvolve installed separately:
pip install shinka-evolve
```

## Usage

### Run a single game

```python
from wargame.engine import WarGame
from wargame.scenarios import EVALUATION_SCENARIOS
from shinka_task.initial import japan_strategy

game = WarGame(scenario=EVALUATION_SCENARIOS[0], seed=42)
while not game.is_done():
    game.step(japan_strategy(game.get_state()))
result = game.get_result()
print(f"Score: {result['score']['total']}, Survived: {result['taiwan_survived']}")
```

### Run ShinkaEvolve evolution

```bash
export DEEPSEEK_API_KEY="your-key"
shinka run --config shinka_task/shinka_config.yaml
```

### Launch dashboard

```bash
streamlit run dashboard/app.py
```

## Project Structure

```
shinka-wargame/
├── wargame/              # Core simulation engine
│   ├── engine.py         # WarGame class (step, get_state, get_result)
│   ├── combat.py         # Naval combat, convoy survival, missile resolution
│   ├── economy.py        # Taiwan energy/economy, Japan economy
│   ├── escalation.py     # Emergent escalation computation
│   ├── scoring.py        # Japan-centric scoring (9 categories)
│   ├── scenarios.py      # Scenario definitions + UI presets
│   └── constants.py      # All game constants
├── profiles/             # LLM-generated country behavior profiles
│   ├── china.py          # Aggressive, adaptive, cautious
│   ├── us.py             # Interventionist, restrained
│   └── taiwan.py         # Resilient, defeatist
├── shinka_task/           # ShinkaEvolve task directory
│   ├── initial.py        # japan_strategy() in EVOLVE-BLOCK
│   ├── evaluate.py       # Multi-scenario evaluation
│   └── shinka_config.yaml
├── dashboard/            # Streamlit wargame visualization
│   ├── app.py            # Main app (3 tabs)
│   ├── map_view.py       # Regional schematic map
│   ├── replay.py         # Turn-by-turn game replay
│   └── analysis.py       # Strategy comparison
└── tests/                # Unit and integration tests
```

## Game Design

### Players & Forces

| Player | Forces | Control |
|--------|--------|---------|
| China | 60 surface ships, 20 submarines, 400 aircraft, 1200 missiles | LLM-generated profile |
| US | 24 surface ships, 12 SSN, 200 aircraft, 800 missiles | LLM-generated profile |
| Taiwan | 26 surface ships, 150 aircraft, 400 missiles | LLM-generated profile |
| Japan | 20 JMSDF ships, 6 submarines, 100 JASDF aircraft | **Evolved by ShinkaEvolve** |

### Japan's Decision Space

- JMSDF/JASDF deployment levels
- Base access for US forces (Okinawa, Kyushu: closed/limited/open)
- Convoy transshipment through Japanese waters
- Engagement posture (self-defense only / defensive / proactive)
- ASW vs surface combat priority
- Diplomatic pressure and sanctions advocacy
- Humanitarian aid to Taiwan

### Scoring (Japan-centric, -1540 to +1380)

- Taiwan outcome: ±500 (win/surrender)
- Taiwan survival quality: 0–200
- JMSDF force preservation: 0–150
- Homeland security: -410 to +200
- Japan economic impact: -150 to 0
- Operational success: 0–150
- Alliance credibility: -50 to +100
- Escalation management: -250 to +80
- Legal & humanitarian: -100 to 0

## References

- CSIS "The First Battle of the Next War" (2023) — amphibious invasion wargame
- CSIS "Lights Out" (2024) — naval blockade wargame, Taiwan energy vulnerability
- CSIS "Confronting Armageddon" (2024) — nuclear dynamics
- Stanley & Miikkulainen, "Evolving Neural Networks through Augmenting Topologies" (2002)
- ShinkaEvolve — LLM-driven evolutionary program synthesis
