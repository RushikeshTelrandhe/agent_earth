"""
Collapse Explainability Engine
================================
Computes structured, human-readable explanations for why each region
collapsed or survived at every timestep. Attaches multi-factor weighted
reasoning to simulation data without modifying simulation logic.

Factors (weighted):
  - Sustainability health (primary, ~40%)
  - Resource starvation per type (secondary, ~25%)
  - Strategy behavior impact (tertiary, ~15%)
  - Trade support / isolation (contextual, ~10%)
  - Climate shock exposure (contextual, ~10%)
"""

from __future__ import annotations
from typing import Any, Dict, List, Optional


# ── Constants ──────────────────────────────────────────

SUSTAINABILITY_COLLAPSE_THRESHOLD = 0.10
RESOURCE_CRITICAL_THRESHOLD = 10.0
TOTAL_RESOURCES_CRITICAL = 5.0

GREEDY_ACTIONS = {"hoard", "expand_pop"}
COOPERATIVE_ACTIONS = {"trade", "conserve"}

FACTOR_ICONS = {
    "sustainability": "🔴",
    "water_depletion": "💧",
    "food_depletion": "🍽️",
    "energy_depletion": "⚡",
    "land_depletion": "🏔️",
    "resource_starvation": "📉",
    "greedy_behavior": "🧠",
    "trade_isolation": "🤝",
    "climate_shock": "🌪️",
    "population_pressure": "👥",
}


def _compute_factors(region: Dict[str, Any], events: List[str]) -> List[Dict[str, Any]]:
    """Compute raw severity scores for all collapse/survival factors."""
    factors = []

    # ── 1. Sustainability (primary, weight ~40%) ──
    sust = region.get("sustainability", 0.5)
    if sust < 0.3:
        severity = 1.0 - (sust / 0.3)  # 1.0 at sust=0, 0.0 at sust=0.3
        factors.append({
            "name": "Low sustainability",
            "key": "sustainability",
            "severity": round(min(1.0, severity), 3),
            "weight": 0.40,
            "detail": f"Sustainability at {sust:.1%} (collapse threshold: {SUSTAINABILITY_COLLAPSE_THRESHOLD:.0%})"
        })

    # ── 2. Individual resource depletion (secondary, weight ~25% total) ──
    resource_weight = 0.07  # per resource
    for res in ["water", "food", "energy", "land"]:
        val = region.get(res, 50)
        if val < RESOURCE_CRITICAL_THRESHOLD:
            severity = 1.0 - (val / RESOURCE_CRITICAL_THRESHOLD)
            factors.append({
                "name": f"{res.capitalize()} depletion",
                "key": f"{res}_depletion",
                "severity": round(min(1.0, severity), 3),
                "weight": resource_weight,
                "detail": f"{res.capitalize()} at {val:.1f} (critical < {RESOURCE_CRITICAL_THRESHOLD})"
            })

    # Total resource starvation
    total = sum(region.get(r, 50) for r in ["water", "food", "energy", "land"])
    if total < 20:
        severity = 1.0 - (total / 20)
        factors.append({
            "name": "Total resource starvation",
            "key": "resource_starvation",
            "severity": round(min(1.0, severity), 3),
            "weight": 0.10,
            "detail": f"Combined resources at {total:.1f} (critical < {TOTAL_RESOURCES_CRITICAL})"
        })

    # ── 3. Strategy / behavior (tertiary, weight ~15%) ──
    action = region.get("last_action", "none")
    if action in GREEDY_ACTIONS:
        factors.append({
            "name": "Greedy behavior",
            "key": "greedy_behavior",
            "severity": 0.6,
            "weight": 0.15,
            "detail": f"Region chose '{action}' — reduces cooperative recovery"
        })

    # ── 4. Trade isolation (contextual, weight ~10%) ──
    partners = region.get("trade_partners", [])
    trade_balance = region.get("trade_balance", 0)
    if len(partners) == 0:
        factors.append({
            "name": "No trade partners",
            "key": "trade_isolation",
            "severity": 0.7,
            "weight": 0.10,
            "detail": "Region has no active trade partners — isolated from aid"
        })
    elif trade_balance < -5:
        factors.append({
            "name": "Negative trade balance",
            "key": "trade_isolation",
            "severity": 0.4,
            "weight": 0.05,
            "detail": f"Trade balance: {trade_balance:.1f} — giving more than receiving"
        })

    # ── 5. Climate shock (contextual, weight ~10%) ──
    climate_events = [e for e in events if e in ("drought", "flood", "energy_crisis", "soil_degradation")]
    if climate_events:
        severity = min(1.0, len(climate_events) * 0.5)
        factors.append({
            "name": "Climate shock",
            "key": "climate_shock",
            "severity": round(severity, 3),
            "weight": 0.10,
            "detail": f"Active climate events: {', '.join(climate_events)}"
        })

    # ── 6. Population pressure ──
    population = region.get("population", 100)
    if population > 400:
        severity = min(1.0, (population - 400) / 200)
        factors.append({
            "name": "Population pressure",
            "key": "population_pressure",
            "severity": round(severity, 3),
            "weight": 0.08,
            "detail": f"Population at {population:.0f} — straining resources"
        })

    return factors


def _normalize_contributions(factors: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Normalize factor contributions to sum to 1.0."""
    if not factors:
        return []

    total_weighted = sum(f["severity"] * f["weight"] for f in factors)
    if total_weighted == 0:
        return []

    result = []
    for f in factors:
        contribution = (f["severity"] * f["weight"]) / total_weighted
        if contribution > 0.02:  # Skip negligible factors
            result.append({
                "name": f["name"],
                "key": f["key"],
                "icon": FACTOR_ICONS.get(f["key"], "📊"),
                "contribution": round(contribution, 3),
                "severity": f["severity"],
                "detail": f["detail"],
            })

    result.sort(key=lambda x: x["contribution"], reverse=True)
    return result[:5]  # Top 5 factors max


def _compute_collapse_risk(region: Dict[str, Any], events: List[str]) -> float:
    """Compute a 0–1 collapse risk score for a region."""
    if region.get("collapsed"):
        return 1.0

    sust = region.get("sustainability", 0.5)
    total_res = sum(region.get(r, 50) for r in ["water", "food", "energy", "land"])
    partners = len(region.get("trade_partners", []))
    action = region.get("last_action", "none")

    risk = 0.0
    # Sustainability risk (biggest factor)
    if sust < 0.3:
        risk += 0.5 * (1.0 - sust / 0.3)
    # Resource risk
    if total_res < 40:
        risk += 0.25 * (1.0 - total_res / 40)
    # Isolation risk
    if partners == 0:
        risk += 0.1
    # Greedy behavior risk
    if action in GREEDY_ACTIONS:
        risk += 0.08
    # Climate risk
    if events:
        risk += 0.07 * min(1.0, len(events) * 0.5)

    return round(min(1.0, risk), 3)


def _survival_reason(region: Dict[str, Any]) -> Optional[str]:
    """Generate a human-readable explanation for why a region survives despite stress."""
    sust = region.get("sustainability", 0.5)
    resources = {r: region.get(r, 50) for r in ["water", "food", "energy", "land"]}
    action = region.get("last_action", "none")
    partners = region.get("trade_partners", [])
    low_resources = [r for r, v in resources.items() if v < RESOURCE_CRITICAL_THRESHOLD]

    if not low_resources and sust > 0.3:
        return None  # Not stressed — no explanation needed

    reasons = []
    if sust > SUSTAINABILITY_COLLAPSE_THRESHOLD:
        reasons.append(f"Sustainability at {sust:.1%} — above collapse threshold ({SUSTAINABILITY_COLLAPSE_THRESHOLD:.0%})")
    if len(partners) > 0:
        reasons.append(f"Active trade with {len(partners)} partner(s) supports recovery")
    if action in COOPERATIVE_ACTIONS:
        reasons.append(f"'{action}' strategy reduces resource consumption")

    total_res = sum(resources.values())
    if total_res >= TOTAL_RESOURCES_CRITICAL and low_resources:
        reasons.append(f"Other resources compensate: total at {total_res:.0f}")

    if reasons:
        return " · ".join(reasons)
    return None


def explain_region(region: Dict[str, Any], events: List[str]) -> Dict[str, Any]:
    """Generate a full collapse explanation for a single region.

    Parameters
    ----------
    region : dict
        Region data from a simulation step (id, water, food, energy, etc.)
    events : list[str]
        Climate events active at this step

    Returns
    -------
    dict with keys: status, collapse_risk, factors, primary_reason,
                    survival_reason, risk_level, risk_tooltip
    """
    is_collapsed = region.get("collapsed", False)
    factors = _compute_factors(region, events)
    normalized = _normalize_contributions(factors)

    collapse_risk = _compute_collapse_risk(region, events)

    # Risk level
    if collapse_risk >= 0.7:
        risk_level = "critical"
    elif collapse_risk >= 0.4:
        risk_level = "warning"
    else:
        risk_level = "safe"

    # Primary reason
    primary_reason = None
    if is_collapsed:
        cause = region.get("collapse_cause", "unknown")
        if "resource_depletion" in str(cause):
            res = str(cause).split(":")[-1] if ":" in str(cause) else "resources"
            primary_reason = f"{res.capitalize()} depletion triggered collapse"
        elif "sustainability" in str(cause):
            primary_reason = "Sustainability dropped below safe threshold"
        else:
            primary_reason = "Multiple factors caused collapse"
    elif normalized:
        primary_reason = normalized[0]["name"]

    # Survival reason
    survival_reason = None if is_collapsed else _survival_reason(region)

    # Risk tooltip
    risk_tooltip = _build_risk_tooltip(region, collapse_risk, risk_level, normalized)

    return {
        "status": "collapsed" if is_collapsed else "alive",
        "collapse_risk": collapse_risk,
        "risk_level": risk_level,
        "primary_reason": primary_reason,
        "factors": normalized,
        "survival_reason": survival_reason,
        "risk_tooltip": risk_tooltip,
    }


def _build_risk_tooltip(
    region: Dict[str, Any], risk: float, level: str, factors: List[Dict]
) -> str:
    """Build a human-readable tooltip for the collapse risk meter."""
    if region.get("collapsed"):
        return "This region has collapsed"

    if level == "safe":
        return f"Collapse risk: {risk:.0%} — region is stable"

    parts = [f"Collapse risk: {risk:.0%}"]
    for f in factors[:2]:
        parts.append(f"• {f['name']} ({f['contribution']:.0%})")

    if level == "critical":
        parts.append("⚠ Collapse imminent")

    return " | ".join(parts)


def explain_step(step_data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Add collapse explanations to all regions in a simulation step.

    Parameters
    ----------
    step_data : dict
        A single step from sim.logger.steps, must have 'regions' and optionally 'events'

    Returns
    -------
    list of collapse explanation dicts, one per region
    """
    regions = step_data.get("regions", [])
    events = step_data.get("events", [])
    return [explain_region(r, events) for r in regions]


def enrich_steps(steps: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Enrich all simulation steps with collapse explanations.

    Modifies each step in-place by adding 'collapse_explanations' key
    and 'collapse_explanation' to each region dict.

    Parameters
    ----------
    steps : list[dict]
        All steps from sim.logger.steps

    Returns
    -------
    The same list, mutated with explanations attached.
    """
    for step in steps:
        explanations = explain_step(step)
        step["collapse_explanations"] = explanations

        # Also attach per-region for convenience
        regions = step.get("regions", [])
        for i, region in enumerate(regions):
            if i < len(explanations):
                region["collapse_explanation"] = explanations[i]

    return steps
