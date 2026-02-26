# Agent Earth: Adaptive Multi-Agent Resource Scarcity Simulator

A true **multi-agent reinforcement learning** simulation where independent AI agents govern regions with finite resources in a dynamic world. Watch emergent cooperation, trade alliances, strategic divergence, and climate-driven collapse unfold.

## Architecture

```
agent_earth/
├── main.py                            # CLI: train, simulate, analyse, dashboard
├── requirements.txt
├── env/
│   ├── world_env.py                   # Multi-agent world with trust & learned trade
│   └── multi_agent_env.py             # Per-agent Gymnasium wrappers
├── agents/
│   ├── shared_agent.py                # Legacy shared PPO (backward compat)
│   └── independent_agents.py          # N independent PPO models (one per region)
├── simulation/
│   └── simulator.py                   # Simulation runner (independent/shared modes)
├── events/
│   └── disasters.py                   # Per-region climate vulnerability & events
├── analysis/
│   └── analyzer.py                    # Strategy evolution, resilience, trade deps
├── dashboard/
│   ├── app.py                         # Flask API backend
│   └── frontend/                      # React + Plotly interactive dashboard
└── utils/
    ├── config.py                      # Regional profiles, trust, interdependence
    └── logger.py                      # JSON/CSV logging, save/load
```

## Multi-Agent Design

Each region has its **own independent PPO policy** trained via Stable-Baselines3:

```
Region 0 → models/region_0.zip   (Water-rich, low drought risk)
Region 1 → models/region_1.zip   (Agricultural, high food prod)
Region 2 → models/region_2.zip   (Energy hub, crisis-prone)
Region 3 → models/region_3.zip   (Balanced)
Region 4 → models/region_4.zip   (Land-rich, drought-prone)
Region 5 → models/region_5.zip   (Coastal, flood-prone)
```

**Per-agent action space**: `[strategy, trade_target, trade_resource, trade_amount]`

| Action | Effect |
|--------|--------|
| Hoard | Slight resource boost, sustainability penalty |
| Trade | Initiate learned trade with chosen target |
| Invest | Boost food/energy with productivity multipliers |
| Conserve | Reduce consumption, increase sustainability |
| Expand | Grow population faster |

**Trade is learned, not hardcoded**: agents choose whom to trade with, which resource, and how much. Trades are accepted/rejected based on trust + utility.

## Trust & Alliance System

- **Trust matrix**: pairwise trust between all regions (0-1)
- **Trust grows** with successful trades, **decays** naturally each step
- **Alliances form** when mutual trust exceeds threshold
- **Alliances break** when trust drops (betrayal/conflict)
- Trust influences trade acceptance probability

## Climate System

Per-region vulnerability profiles — some regions are drought-prone, others flood-prone:
- **Drought** (water collapse)
- **Flood** (food destruction)
- **Energy crisis**
- **Soil degradation** (land loss)

Resource interdependence: food production depends on energy + land availability.

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt
cd dashboard/frontend && npm install && cd ../..

# Train independent agents (demo: fast, ~1 min)
python main.py train --demo --mode independent

# Train (research: longer, better strategies)
python main.py train --train-steps 50000 --mode independent

# Simulate with trained models
python main.py simulate --model models --mode independent --timesteps 300

# Simulate with random actions
python main.py simulate --timesteps 300

# Analyse saved run
python main.py analyse --input results/<file>.json

# Dashboard
python main.py dashboard              # Flask API on :5000
cd dashboard/frontend && npm run dev   # React on :3000
```

## Analysis & Insights

The analyzer generates:
- **Strategy evolution timeline**: action distribution per region over time
- **Collapse root-cause analysis**: which resource crashed first
- **Climate resilience ranking**: survival * sustainability / exposure
- **Trade dependency index**: how reliant each region is on trade
- **Cooperative vs greedy survival curve**
- **Automatic textual insights** summarizing emergent behaviors

Example output:
```
Regions [0, 2, 3, 4] survived the entire simulation.
Region 1 collapsed at step 36 (sustainability_collapse).
Cooperation dominated (56% vs 21% greed).
Cooperative strategies correlated with better survival outcomes.
Most resilient: Region 0 (score 0.5496).
```

## Dashboard Visualizations

| Visualization | Description |
|---|---|
| Agent Behavior Cards | Per-region: strategy badge, resource meters, collapse risk, trade partners |
| Trade Network Graph | Animated arrows between regions, thickness=volume, color=resource |
| Strategy Evolution | Stacked area chart of action distributions with climate event markers |
| Trust Heatmap | Inter-region trust matrix evolving over time |
| Collapse Replay | Step-by-step world state with slider navigation |
| Climate Resilience | Ranked table of survival * sustainability scores |
| Trade Dependency | Bar chart of sent vs received resources per region |
| Behavioral Clusters | KMeans clustering on region behavior vectors |

## Presets

| Preset | Description |
|---|---|
| default | Balanced resources, moderate climate |
| scarcity | Low resources, high population, severe climate |
| abundance | Plentiful resources, mild climate |

## License

MIT
