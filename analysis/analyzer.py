"""
Agent Earth — Post-Simulation Analysis
=========================================
Computes survival metrics, detects collapses, measures inequality
and cooperation, runs KMeans clustering on region behaviours, and
produces an automatic insights summary.
"""

from __future__ import annotations

from collections import Counter
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
    # Core metrics
    # ──────────────────────────────────────────
    def survival_rates(self) -> Dict[int, float]:
        """Fraction of timesteps each region was alive."""
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
        """Detect the first timestep each region collapsed."""
        collapsed_at: Dict[int, Optional[int]] = {i: None for i in range(self.num_regions)}
        for record in self.steps:
            step = record.get("step", 0)
            for r in record.get("regions", []):
                if r.get("collapsed") and collapsed_at.get(r["id"]) is None:
                    collapsed_at[r["id"]] = step
        return [
            {"region": rid, "collapsed_at_step": s}
            for rid, s in collapsed_at.items()
            if s is not None
        ]

    def inequality_index(self) -> List[float]:
        """Gini coefficient of total resources across regions at each step."""
        ginis: List[float] = []
        for record in self.steps:
            regions = record.get("regions", [])
            totals = [sum(r.get(res, 0) for res in RESOURCE_NAMES) for r in regions]
            ginis.append(round(_safe_gini(totals), 4))
        return ginis

    def cooperation_vs_greed(self) -> Dict[str, float]:
        """Fraction of actions that were cooperative (trade/conserve) vs greedy (hoard/expand)."""
        coop_actions = {"trade", "conserve"}
        greed_actions = {"hoard", "expand_pop"}
        coop_count = 0
        greed_count = 0
        total = 0
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
        """Most frequent action for each region."""
        counters: Dict[int, Counter] = {i: Counter() for i in range(self.num_regions)}
        for record in self.steps:
            for r in record.get("regions", []):
                act = r.get("last_action", "none")
                counters[r["id"]][act] += 1
        return {rid: c.most_common(1)[0][0] if c else "none" for rid, c in counters.items()}

    # ──────────────────────────────────────────
    # Clustering
    # ──────────────────────────────────────────
    def cluster_behaviours(self, n_clusters: int = 3) -> Dict[str, Any]:
        """KMeans clustering on region behaviour vectors.

        Each region is represented by:
          [avg_water, avg_food, avg_energy, avg_pop, avg_sustainability,
           survival_rate, coop_action_count, greed_action_count]
        """
        try:
            from sklearn.cluster import KMeans
        except ImportError:
            return {"error": "scikit-learn not installed"}

        survival = self.survival_rates()

        # Build feature matrix
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
                np.mean(waters) if waters else 0,
                np.mean(foods) if foods else 0,
                np.mean(energies) if energies else 0,
                np.mean(pops) if pops else 0,
                np.mean(susts) if susts else 0,
                survival.get(rid, 0),
                coop,
                greed,
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
        """Pearson correlation between average sustainability and survival rate."""
        survival = self.survival_rates()
        avg_sust: Dict[int, float] = {}
        for rid in range(self.num_regions):
            susts = []
            for record in self.steps:
                for r in record.get("regions", []):
                    if r["id"] == rid:
                        susts.append(r.get("sustainability", 0))
            avg_sust[rid] = np.mean(susts) if susts else 0.0

        x = np.array([avg_sust[i] for i in range(self.num_regions)])
        y = np.array([survival[i] for i in range(self.num_regions)])
        if np.std(x) == 0 or np.std(y) == 0:
            return 0.0
        return float(round(np.corrcoef(x, y)[0, 1], 4))

    # ──────────────────────────────────────────
    # Full report
    # ──────────────────────────────────────────
    def full_report(self) -> Dict[str, Any]:
        """Generate a complete analysis report."""
        ginis = self.inequality_index()
        return {
            "survival_rates": self.survival_rates(),
            "collapses": self.collapse_events(),
            "inequality_mean": round(float(np.mean(ginis)), 4) if ginis else 0,
            "inequality_final": ginis[-1] if ginis else 0,
            "cooperation_vs_greed": self.cooperation_vs_greed(),
            "dominant_strategies": self.dominant_strategies(),
            "sustainability_survival_corr": self.correlation_sustainability_survival(),
            "clusters": self.cluster_behaviours(),
        }
