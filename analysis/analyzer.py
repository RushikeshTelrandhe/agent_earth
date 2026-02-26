"""
Agent Earth - Post-Simulation Analysis
=========================================
Extended analysis: survival, collapse root-cause, strategy evolution,
climate resilience, trade dependency, KMeans clustering, and
automatic textual insights.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from typing import Any, Dict, List, Optional

import numpy as np

from utils.config import ACTION_NAMES, NUM_REGIONS, RESOURCE_NAMES


def _safe_gini(values: List[float]) -> float:
    """Compute the Gini coefficient for a list of non-negative values."""
    arr = np.array(values, dtype=np.float64)
    if arr.sum() == 0:
        return 0.0
    arr = np.sort(arr)
    n = len(arr)
    index = np.arange(1, n + 1)
    return float((2 * np.sum(index * arr) - (n + 1) * np.sum(arr)) / (n * np.sum(arr)))


class SimulationAnalyzer:
    """Analyses a completed simulation run.

    Parameters
    ----------
    steps : list[dict]
        The ``steps`` list from a ``SimulationLogger``.
    num_regions : int
        Number of regions in the world.
    """

    def __init__(self, steps: List[Dict[str, Any]], num_regions: int = NUM_REGIONS) -> None:
        self.steps = steps
        self.num_regions = num_regions

    # ──────────────────────────────────────────
    # Core metrics (preserved from v1)
    # ──────────────────────────────────────────
    def survival_rates(self) -> Dict[int, float]:
        total = len(self.steps)
        if total == 0:
            return {}
        alive: Dict[int, int] = {i: 0 for i in range(self.num_regions)}
        for record in self.steps:
            for r in record.get("regions", []):
                if not r.get("collapsed", False):
                    alive[r["id"]] = alive.get(r["id"], 0) + 1
        return {rid: round(cnt / total, 3) for rid, cnt in alive.items()}

    def collapse_events(self) -> List[Dict[str, Any]]:
        collapsed_at: Dict[int, Optional[Dict[str, Any]]] = {i: None for i in range(self.num_regions)}
        for record in self.steps:
            step = record.get("step", 0)
            for r in record.get("regions", []):
                if r.get("collapsed") and collapsed_at.get(r["id"]) is None:
                    collapsed_at[r["id"]] = {
                        "region": r["id"],
                        "collapsed_at_step": step,
                        "cause": r.get("collapse_cause", "unknown"),
                    }
        return [v for v in collapsed_at.values() if v is not None]

    def inequality_index(self) -> List[float]:
        ginis: List[float] = []
        for record in self.steps:
            regions = record.get("regions", [])
            totals = [sum(r.get(res, 0) for res in RESOURCE_NAMES) for r in regions]
            ginis.append(round(_safe_gini(totals), 4))
        return ginis

    def cooperation_vs_greed(self) -> Dict[str, float]:
        coop_actions = {"trade", "conserve"}
        greed_actions = {"hoard", "expand_pop"}
        coop_count = greed_count = total = 0
        for record in self.steps:
            for r in record.get("regions", []):
                act = r.get("last_action", "none")
                total += 1
                if act in coop_actions:
                    coop_count += 1
                elif act in greed_actions:
                    greed_count += 1
        if total == 0:
            return {"cooperation_ratio": 0.0, "greed_ratio": 0.0}
        return {
            "cooperation_ratio": round(coop_count / total, 3),
            "greed_ratio": round(greed_count / total, 3),
        }

    def dominant_strategies(self) -> Dict[int, str]:
        counters: Dict[int, Counter] = {i: Counter() for i in range(self.num_regions)}
        for record in self.steps:
            for r in record.get("regions", []):
                counters[r["id"]][r.get("last_action", "none")] += 1
        return {rid: c.most_common(1)[0][0] if c else "none" for rid, c in counters.items()}

    # ──────────────────────────────────────────
    # NEW: Strategy evolution timeline
    # ──────────────────────────────────────────
    def strategy_evolution(self, window: int = 10) -> Dict[int, List[Dict[str, float]]]:
        """Action distribution over time for each region (sliding window).

        Returns: {region_id: [{action_name: fraction, ...}, ...]}
        """
        # Collect actions per region per step
        region_actions: Dict[int, List[str]] = {i: [] for i in range(self.num_regions)}
        for record in self.steps:
            for r in record.get("regions", []):
                region_actions[r["id"]].append(r.get("last_action", "none"))

        result: Dict[int, List[Dict[str, float]]] = {}
        for rid in range(self.num_regions):
            actions = region_actions[rid]
            timeline: List[Dict[str, float]] = []
            for start in range(0, len(actions), window):
                chunk = actions[start:start + window]
                if not chunk:
                    continue
                counts = Counter(chunk)
                total = len(chunk)
                dist = {name: round(counts.get(name, 0) / total, 3) for name in ACTION_NAMES}
                dist["step"] = start
                timeline.append(dist)
            result[rid] = timeline
        return result

    # ──────────────────────────────────────────
    # NEW: Collapse root-cause analysis
    # ──────────────────────────────────────────
    def collapse_root_causes(self) -> List[Dict[str, Any]]:
        """For each collapsed region, identify which resource crashed first."""
        collapses = self.collapse_events()
        causes: List[Dict[str, Any]] = []
        for collapse in collapses:
            rid = collapse["region"]
            step = collapse["collapsed_at_step"]
            # Look at resource levels leading up to collapse
            pre_collapse: Dict[str, List[float]] = {res: [] for res in RESOURCE_NAMES}
            for record in self.steps:
                if record.get("step", 0) >= step:
                    break
                for r in record.get("regions", []):
                    if r["id"] == rid:
                        for res in RESOURCE_NAMES:
                            pre_collapse[res].append(r.get(res, 0))
            # Find fastest-declining resource
            decline_rates = {}
            for res, vals in pre_collapse.items():
                if len(vals) >= 5:
                    last5 = vals[-5:]
                    decline_rates[res] = round(float(last5[0] - last5[-1]), 2)
                else:
                    decline_rates[res] = 0.0
            causes.append({
                "region": rid,
                "step": step,
                "cause": collapse.get("cause", "unknown"),
                "resource_decline_rates": decline_rates,
                "critical_resource": max(decline_rates, key=decline_rates.get) if decline_rates else "unknown",
            })
        return causes

    # ──────────────────────────────────────────
    # NEW: Climate resilience ranking
    # ──────────────────────────────────────────
    def climate_resilience_ranking(self) -> List[Dict[str, Any]]:
        """Rank regions by resilience: survival * avg sustainability / climate exposure."""
        survival = self.survival_rates()
        rankings: List[Dict[str, Any]] = []
        for rid in range(self.num_regions):
            susts = []
            exposure = 0.5  # default
            for record in self.steps:
                for r in record.get("regions", []):
                    if r["id"] == rid:
                        susts.append(r.get("sustainability", 0))
            avg_sust = float(np.mean(susts)) if susts else 0.0
            surv = survival.get(rid, 0.0)
            score = round(surv * avg_sust, 4)
            rankings.append({
                "region": rid,
                "survival": surv,
                "avg_sustainability": round(avg_sust, 3),
                "resilience_score": score,
            })
        rankings.sort(key=lambda x: x["resilience_score"], reverse=True)
        return rankings

    # ──────────────────────────────────────────
    # NEW: Trade dependency index
    # ──────────────────────────────────────────
    def trade_dependency_index(self) -> Dict[int, Dict[str, Any]]:
        """How reliant each region is on incoming trade."""
        received: Dict[int, float] = {i: 0.0 for i in range(self.num_regions)}
        sent: Dict[int, float] = {i: 0.0 for i in range(self.num_regions)}
        trade_count: Dict[int, int] = {i: 0 for i in range(self.num_regions)}

        for record in self.steps:
            for trade in record.get("trades", []):
                if not trade.get("accepted", True):
                    continue
                sender = trade.get("from", -1)
                receiver = trade.get("to", -1)
                amount = trade.get("amount", 0)
                if sender >= 0:
                    sent[sender] = sent.get(sender, 0) + amount
                    trade_count[sender] = trade_count.get(sender, 0) + 1
                if receiver >= 0:
                    received[receiver] = received.get(receiver, 0) + amount

        result = {}
        for rid in range(self.num_regions):
            total = received.get(rid, 0) + sent.get(rid, 0)
            dependency = round(received.get(rid, 0) / max(total, 1), 3)
            result[rid] = {
                "received": round(received.get(rid, 0), 2),
                "sent": round(sent.get(rid, 0), 2),
                "trade_count": trade_count.get(rid, 0),
                "dependency_ratio": dependency,
            }
        return result

    # ──────────────────────────────────────────
    # NEW: Alliance history
    # ──────────────────────────────────────────
    def alliance_history(self) -> List[Dict[str, Any]]:
        """Track alliance formation and dissolution over time."""
        events: List[Dict[str, Any]] = []
        for record in self.steps:
            for alliance in record.get("alliances", []):
                events.append({
                    "step": record.get("step", 0),
                    "pair": alliance.get("pair", []),
                    "since": alliance.get("since", 0),
                })
        return events

    # ──────────────────────────────────────────
    # Clustering (preserved)
    # ──────────────────────────────────────────
    def cluster_behaviours(self, n_clusters: int = 3) -> Dict[str, Any]:
        try:
            from sklearn.cluster import KMeans
        except ImportError:
            return {"error": "scikit-learn not installed"}

        survival = self.survival_rates()
        features: List[List[float]] = []
        for rid in range(self.num_regions):
            waters, foods, energies, pops, susts = [], [], [], [], []
            coop, greed = 0, 0
            for record in self.steps:
                for r in record.get("regions", []):
                    if r["id"] != rid:
                        continue
                    waters.append(r.get("water", 0))
                    foods.append(r.get("food", 0))
                    energies.append(r.get("energy", 0))
                    pops.append(r.get("population", 0))
                    susts.append(r.get("sustainability", 0))
                    act = r.get("last_action", "none")
                    if act in ("trade", "conserve"):
                        coop += 1
                    elif act in ("hoard", "expand_pop"):
                        greed += 1
            features.append([
                float(np.mean(waters)) if waters else 0,
                float(np.mean(foods)) if foods else 0,
                float(np.mean(energies)) if energies else 0,
                float(np.mean(pops)) if pops else 0,
                float(np.mean(susts)) if susts else 0,
                survival.get(rid, 0),
                coop, greed,
            ])

        X = np.array(features)
        n_clusters = min(n_clusters, len(X))
        km = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
        labels = km.fit_predict(X)
        return {
            "labels": {i: int(labels[i]) for i in range(len(labels))},
            "centers": km.cluster_centers_.tolist(),
        }

    def correlation_sustainability_survival(self) -> float:
        survival = self.survival_rates()
        avg_sust: Dict[int, float] = {}
        for rid in range(self.num_regions):
            susts = []
            for record in self.steps:
                for r in record.get("regions", []):
                    if r["id"] == rid:
                        susts.append(r.get("sustainability", 0))
            avg_sust[rid] = float(np.mean(susts)) if susts else 0.0
        x = np.array([avg_sust[i] for i in range(self.num_regions)])
        y = np.array([survival[i] for i in range(self.num_regions)])
        if np.std(x) == 0 or np.std(y) == 0:
            return 0.0
        return float(round(np.corrcoef(x, y)[0, 1], 4))

    # ──────────────────────────────────────────
    # NEW: Automatic insights
    # ──────────────────────────────────────────
    def generate_insights(self) -> str:
        """Generate a human-readable paragraph of insights."""
        survival = self.survival_rates()
        coop = self.cooperation_vs_greed()
        collapses = self.collapse_events()
        resilience = self.climate_resilience_ranking()
        trade_dep = self.trade_dependency_index()

        insights = []

        # Survivor analysis
        survivors = [rid for rid, rate in survival.items() if rate >= 1.0]
        collapsed_regions = [c["region"] for c in collapses]
        if survivors:
            insights.append(f"Regions {survivors} survived the entire simulation.")
        if collapsed_regions:
            for c in collapses:
                insights.append(f"Region {c['region']} collapsed at step {c['collapsed_at_step']} ({c.get('cause', 'unknown')}).")

        # Cooperation analysis
        if coop["cooperation_ratio"] > coop["greed_ratio"]:
            insights.append(f"Cooperation dominated ({coop['cooperation_ratio']:.0%} vs {coop['greed_ratio']:.0%} greed).")
        else:
            insights.append(f"Greed dominated ({coop['greed_ratio']:.0%} vs {coop['cooperation_ratio']:.0%} cooperation).")

        # Check if cooperative regions survived longer
        dom = self.dominant_strategies()
        coop_survivors = [rid for rid in survivors if dom.get(rid) in ("trade", "conserve")]
        greed_survivors = [rid for rid in survivors if dom.get(rid) in ("hoard", "expand_pop")]
        if coop_survivors and not greed_survivors:
            insights.append("Cooperative strategies correlated with better survival outcomes.")
        elif greed_survivors and not coop_survivors:
            insights.append("Greedy strategies surprisingly dominated among survivors.")

        # Resilience
        if resilience:
            top = resilience[0]
            insights.append(f"Most resilient: Region {top['region']} (score {top['resilience_score']}).")

        # Trade
        heavy_traders = [rid for rid, info in trade_dep.items() if info["trade_count"] > 5]
        if heavy_traders:
            insights.append(f"Regions {heavy_traders} were the most active traders.")

        return " ".join(insights)

    # ──────────────────────────────────────────
    # Full report (expanded)
    # ──────────────────────────────────────────
    def full_report(self) -> Dict[str, Any]:
        ginis = self.inequality_index()
        return {
            "survival_rates": self.survival_rates(),
            "collapses": self.collapse_events(),
            "collapse_root_causes": self.collapse_root_causes(),
            "inequality_mean": round(float(np.mean(ginis)), 4) if ginis else 0,
            "inequality_final": ginis[-1] if ginis else 0,
            "cooperation_vs_greed": self.cooperation_vs_greed(),
            "dominant_strategies": self.dominant_strategies(),
            "sustainability_survival_corr": self.correlation_sustainability_survival(),
            "clusters": self.cluster_behaviours(),
            "climate_resilience": self.climate_resilience_ranking(),
            "trade_dependency": self.trade_dependency_index(),
            "strategy_evolution": self.strategy_evolution(),
            "insights": self.generate_insights(),
        }
