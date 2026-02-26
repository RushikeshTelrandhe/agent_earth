# 🌍 Agent Earth: Adaptive Multi-Agent Resource Scarcity Simulator

A modular simulation where **AI agents** (reinforcement learning) govern regions with finite resources in a dynamic world. Watch emergent behaviours like cooperation, collapse, trade, and resource conflicts unfold.

## Architecture

```
agent_earth/
├── main.py                    # CLI entry point
├── requirements.txt
├── env/
│   └── world_env.py           # Gymnasium custom environment
├── agents/
│   └── shared_agent.py        # PPO RL wrapper (Stable-Baselines3)
├── simulation/
│   └── simulator.py           # Simulation runner
├── events/
│   └── disasters.py           # Stochastic climate events
├── analysis/
│   └── analyzer.py            # Metrics, KMeans clustering, insights
├── dashboard/
│   ├── app.py                 # Flask API backend
│   └── frontend/              # React + Vite + Plotly dashboard
└── utils/
    ├── config.py              # Constants, presets, parameters
    └── logger.py              # JSON/CSV logging, save/load
```

## Key Components

| Component | Description |
|---|---|
| **World Environment** | 6 regions, each with water/food/energy/land/population/sustainability. Logistic food growth, linear decay for water/energy, consumption proportional to population. |
| **Climate Events** | Probabilistic disasters (drought, flood, energy crisis) with configurable severity. |
| **Trade System** | Surplus/deficit detection among neighbours, automatic resource transfers, alliance tracking. |
| **RL Agent** | Parameter-shared PPO policy (one model, all regions). Behaviour diverges based on per-region state. |
| **Reward Function** | Multi-objective: survival + sustainability + population stability + cooperation − collapse − overconsumption. |
| **Analysis** | Survival rates, Gini inequality, cooperation ratio, KMeans clustering, Pearson correlation. |
| **Dashboard** | React + Plotly: heatmaps, time-series, survival timeline, collapse replay, strategy comparison, cluster badges. |

## Quick Start

### 1. Install Dependencies

```bash
# Python (in a venv)
pip install -r requirements.txt

# React dashboard
cd dashboard/frontend
npm install
```

### 2. Train the RL Agent

```bash
python main.py train --train-steps 50000 --preset default
```

This saves the model to `models/agent_earth_ppo.zip`.

### 3. Run a Simulation

```bash
# With trained model
python main.py simulate --timesteps 300 --model models/agent_earth_ppo --output results

# With random actions (no model)
python main.py simulate --timesteps 300 --output results
```

Results are saved in `results/` as JSON and CSV.

### 4. Analyse Results

```bash
python main.py analyse --input results/<run_file>.json
```

### 5. Launch Dashboard

**Terminal 1 — Flask API:**
```bash
python main.py dashboard --port 5000
```

**Terminal 2 — React dev server:**
```bash
cd dashboard/frontend
npm run dev
```

Open **http://localhost:3000** to see the interactive dashboard.

## Configuration Presets

| Preset | Description |
|---|---|
| `default` | Balanced resources, moderate climate |
| `scarcity` | Low resources, high population, severe climate |
| `abundance` | Plentiful resources, mild climate |

Use with: `--preset scarcity`

## Action Space

| Action | Effect |
|---|---|
| 0: Hoard | Slight resource boost, sustainability penalty |
| 1: Trade | Share surplus with deficit neighbours |
| 2: Invest in Growth | Boost food/energy, small sustainability gain |
| 3: Conserve | Reduce consumption, increase sustainability |
| 4: Expand Population | Grow population faster |

## Algorithms

- **PPO** (Proximal Policy Optimization) via Stable-Baselines3
- **KMeans** clustering on region behaviour vectors (avg resources, survival rate, action counts)
- **Gini coefficient** for resource inequality measurement
- **Pearson correlation** between sustainability and survival

## Example Output

```
  Simulation complete — 300 steps, reward=1247.32
  Results → results/run_20260226_120000.json

  Analysis Report:
    survival_rates: {0: 1.0, 1: 0.87, 2: 1.0, 3: 0.65, 4: 1.0, 5: 0.92}
    collapses: [{'region': 3, 'collapsed_at_step': 195}]
    inequality_mean: 0.1234
    cooperation_vs_greed: {cooperation_ratio: 0.42, greed_ratio: 0.31}
    sustainability_survival_corr: 0.8721
```

## License

MIT
