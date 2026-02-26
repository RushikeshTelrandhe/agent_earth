"""
AgentEarth RL Advisor
======================
Embedded simulation intelligence interpreter.
Analyzes multi-agent RL outputs and generates structured,
research-grade explanations.

This is NOT a real-world monitoring system.
All analysis is strictly simulation-based.
"""

from __future__ import annotations
from typing import Any, Dict, List, Optional
import re


# ── Strategy semantics ────────────────────────────────────
STRATEGY_INFO = {
    "hoard": {
        "label": "Hoard",
        "type": "greedy",
        "risk": "high",
        "desc": "Short-term survival through resource accumulation, increases long-term collapse risk",
    },
    "trade": {
        "label": "Trade",
        "type": "cooperative",
        "risk": "low",
        "desc": "Resource exchange with partners, stabilizes multi-agent ecosystem",
    },
    "conserve": {
        "label": "Conserve",
        "type": "sustainability",
        "risk": "low",
        "desc": "Reduces consumption, builds sustainability buffer",
    },
    "invest_growth": {
        "label": "Invest Growth",
        "type": "adaptive",
        "risk": "medium",
        "desc": "Growth-oriented with moderate risk, depends on resource availability",
    },
    "expand_pop": {
        "label": "Expand Population",
        "type": "greedy",
        "risk": "high",
        "desc": "Aggressive population expansion, dramatically increases resource pressure",
    },
}


def _extract_context(steps: List[Dict], analysis: Dict) -> Dict[str, Any]:
    """Extract structured simulation context from raw step data and analysis."""
    if not steps:
        return {"valid": False, "reason": "No simulation data available"}

    last_step = steps[-1]
    regions = last_step.get("regions", [])
    num_steps = len(steps)

    # Per-region context
    region_contexts = []
    for r in regions:
        sust = r.get("sustainability", 0.5)
        expl = r.get("collapse_explanation", {})

        # Determine convergence from reward trend
        reward_trend = "stable"
        if num_steps > 20:
            early_avg = sum(
                s.get("regions", [{}])[r["id"]].get("sustainability", 0.5)
                for s in steps[:20] if r["id"] < len(s.get("regions", []))
            ) / 20
            late_avg = sum(
                s.get("regions", [{}])[r["id"]].get("sustainability", 0.5)
                for s in steps[-20:] if r["id"] < len(s.get("regions", []))
            ) / 20
            if late_avg > early_avg + 0.05:
                reward_trend = "improving"
            elif late_avg < early_avg - 0.05:
                reward_trend = "declining"

        # Resource efficiency
        total_res = sum(r.get(res, 0) for res in ["water", "food", "energy", "land"])
        max_possible = 400  # 4 resources * 100 max
        res_efficiency = min(1.0, total_res / max_possible)

        # Population pressure
        pop = r.get("population", 100)
        pop_pressure = "low" if pop < 200 else "medium" if pop < 400 else "high"

        # Climate stress from events
        events = last_step.get("events", [])
        climate_stress = "low" if len(events) == 0 else "medium" if len(events) <= 2 else "high"

        # Collapse risk
        risk = expl.get("collapse_risk", 0) if expl else 0
        collapse_risk = "low" if risk < 0.3 else "medium" if risk < 0.6 else "high"

        # Cooperation index from trade partners
        partners = r.get("trade_partners", [])
        coop_index = min(1.0, len(partners) / max(1, len(regions) - 1))

        # Convergence
        if reward_trend == "improving":
            convergence = "learning"
        elif reward_trend == "stable" and sust > 0.3:
            convergence = "converged"
        else:
            convergence = "unstable"

        # Confidence
        confidence = "high" if num_steps > 200 else "medium" if num_steps > 50 else "low"

        ctx = {
            "region_id": r["id"],
            "region_name": f"Region {r['id']}",
            "collapsed": r.get("collapsed", False),
            "sustainability_score": round(sust, 3),
            "resource_efficiency": round(res_efficiency, 3),
            "dominant_strategy": r.get("last_action", "none"),
            "collapse_risk": collapse_risk,
            "population_pressure": pop_pressure,
            "climate_stress": climate_stress,
            "reward_trend": reward_trend,
            "convergence_status": convergence,
            "cooperation_index": round(coop_index, 3),
            "collapse_reason": expl.get("primary_reason") if expl else None,
            "confidence_level": confidence,
            "collapse_explanation": expl,
            "water": r.get("water", 0),
            "food": r.get("food", 0),
            "energy": r.get("energy", 0),
            "land": r.get("land", 0),
            "population": pop,
            "trade_partners": partners,
        }
        region_contexts.append(ctx)

    # System-level metrics
    coop = analysis.get("cooperation_vs_greed", {})
    system_ctx = {
        "valid": True,
        "total_steps": num_steps,
        "regions": region_contexts,
        "cooperation_ratio": coop.get("cooperation_ratio", 0),
        "greed_ratio": coop.get("greed_ratio", 0),
        "inequality_mean": analysis.get("inequality_mean", 0),
        "total_collapses": len(analysis.get("collapses", [])),
        "survival_rates": analysis.get("survival_rates", {}),
    }
    return system_ctx


def _match_intent(question: str) -> str:
    """Classify the user question into an intent category."""
    q = question.lower().strip()

    if any(w in q for w in ["collapse", "die", "dead", "fell", "fail", "💀"]):
        if any(w in q for w in ["why", "reason", "cause", "explain"]):
            return "collapse_reason"
        return "collapse_overview"

    if any(w in q for w in ["surviv", "alive", "stable", "strong", "best", "safest"]):
        return "survival_analysis"

    if any(w in q for w in ["converg", "learn", "train", "reward", "policy"]):
        return "training_insight"

    if any(w in q for w in ["cooperat", "trade", "partner", "alliance", "trust"]):
        return "cooperation_analysis"

    if any(w in q for w in ["crowd", "sens", "signal", "detect", "webcam", "yolo", "camera"]):
        return "crowdsense_overview"

    if any(w in q for w in ["strateg", "hoard", "conserve", "invest", "expand", "action"]):
        return "strategy_analysis"

    if any(w in q for w in ["risk", "danger", "threat", "warning"]):
        return "risk_outlook"

    if any(w in q for w in ["compar", "versus", "vs", "differ", "rank"]):
        return "comparison"

    if any(w in q for w in ["region"]):
        # Extract region ID
        nums = re.findall(r"\d+", q)
        if nums:
            return f"region_detail:{nums[0]}"

    if any(w in q for w in ["overview", "summary", "status", "system", "overall"]):
        return "system_overview"

    return "system_overview"


def _assess_region(ctx: Dict) -> str:
    """Generate a single-region assessment."""
    lines = []
    name = ctx["region_name"]
    strat = ctx["dominant_strategy"]
    strat_info = STRATEGY_INFO.get(strat, {})

    if ctx["collapsed"]:
        lines.append(f"**{name}** has collapsed during the simulation.")
        if ctx.get("collapse_reason"):
            lines.append(f"Primary cause: {ctx['collapse_reason']}.")
        expl = ctx.get("collapse_explanation", {})
        factors = expl.get("factors", [])
        if factors:
            lines.append("Contributing factors:")
            for f in factors[:3]:
                pct = f"{f['contribution']*100:.0f}%"
                lines.append(f"- {f['name']}: {pct} contribution")
    else:
        sust = ctx["sustainability_score"]
        risk_label = ctx["collapse_risk"]
        lines.append(
            f"**{name}** is currently active with a sustainability score of {sust:.1%} "
            f"and {risk_label} collapse risk."
        )
        lines.append(
            f"Dominant strategy: **{strat_info.get('label', strat)}** — {strat_info.get('desc', 'unknown behavior')}."
        )
        if ctx["cooperation_index"] > 0.5:
            lines.append(f"This region shows strong cooperative behavior (cooperation index: {ctx['cooperation_index']:.2f}).")
        elif ctx["cooperation_index"] == 0:
            lines.append("This region has no active trade partners, indicating isolation risk.")

        survival = ctx.get("collapse_explanation", {}).get("survival_reason")
        if survival:
            lines.append(f"Survival factors: {survival}")

    return "\n".join(lines)


def _format_section(title: str, content: str) -> str:
    """Format a response section."""
    return f"### {title}\n\n{content}"


def generate_response(question: str, steps: List[Dict], analysis: Dict) -> Dict[str, Any]:
    """Generate a structured RL Advisor response.

    Parameters
    ----------
    question : str
        User's natural language question
    steps : list
        Simulation step data
    analysis : dict
        Analysis report from SimulationAnalyzer

    Returns
    -------
    dict with keys: response (str), sections (list), intent (str), confidence (str)
    """
    ctx = _extract_context(steps, analysis)

    if not ctx.get("valid"):
        return {
            "response": "No simulation data is currently available. Please run a simulation first to generate outputs for analysis.",
            "sections": [],
            "intent": "no_data",
            "confidence": "n/a",
        }

    intent = _match_intent(question)
    regions = ctx["regions"]
    active = [r for r in regions if not r["collapsed"]]
    collapsed = [r for r in regions if r["collapsed"]]
    confidence = "high" if ctx["total_steps"] > 200 else "medium" if ctx["total_steps"] > 50 else "low"

    sections = []

    # ── System Overview ──
    if intent == "system_overview":
        status = (
            f"The simulation completed **{ctx['total_steps']} timesteps** across **{len(regions)} regions**. "
            f"**{len(active)}** regions remain active and **{len(collapsed)}** have collapsed."
        )
        if ctx["cooperation_ratio"] > 0.5:
            status += f"\n\nThe system exhibits predominantly cooperative dynamics (cooperation ratio: {ctx['cooperation_ratio']:.0%})."
        elif ctx["greed_ratio"] > 0.5:
            status += f"\n\nThe system shows predominantly competitive behavior (greed ratio: {ctx['greed_ratio']:.0%}), indicating agents have not learned stable cooperative policies."
        sections.append(("Simulation Assessment", status))

        # Key drivers
        drivers = []
        strat_counts = {}
        for r in regions:
            s = r["dominant_strategy"]
            strat_counts[s] = strat_counts.get(s, 0) + 1
        dominant = max(strat_counts, key=strat_counts.get) if strat_counts else "none"
        drivers.append(f"Dominant system strategy: **{STRATEGY_INFO.get(dominant, {}).get('label', dominant)}** ({strat_counts.get(dominant, 0)}/{len(regions)} regions)")
        if collapsed:
            drivers.append(f"Collapsed regions: {', '.join(r['region_name'] for r in collapsed)}")
        if ctx["inequality_mean"]:
            drivers.append(f"Resource inequality (Gini): {ctx['inequality_mean']}")
        sections.append(("Key Drivers", "\n".join(f"- {d}" for d in drivers)))

        # Training insight
        convergence_states = [r["convergence_status"] for r in regions]
        conv_summary = "mixed"
        if all(c == "converged" for c in convergence_states):
            conv_summary = "All agents have converged to stable policies."
        elif all(c == "unstable" for c in convergence_states):
            conv_summary = "All agents show unstable learning dynamics. Consider longer training or adjusted hyperparameters."
        else:
            learning = sum(1 for c in convergence_states if c == "learning")
            stable = sum(1 for c in convergence_states if c == "converged")
            conv_summary = f"{stable}/{len(regions)} agents converged, {learning}/{len(regions)} still learning."
        sections.append(("RL Training Insight", conv_summary))

        # Risk
        high_risk = [r for r in active if r["collapse_risk"] == "high"]
        if high_risk:
            risk_text = f"**{len(high_risk)} region(s)** face elevated collapse risk: {', '.join(r['region_name'] for r in high_risk)}."
        elif collapsed:
            risk_text = f"System has experienced {len(collapsed)} collapse(s). Remaining regions show manageable risk levels."
        else:
            risk_text = "No immediate systemic risk detected. All regions maintain viable sustainability buffers."
        sections.append(("Risk Outlook", risk_text))

    # ── Collapse Analysis ──
    elif intent in ("collapse_reason", "collapse_overview"):
        if not collapsed:
            sections.append(("Simulation Assessment", "No regions have collapsed in this simulation run. All agents maintained viable sustainability levels."))
        else:
            for r in collapsed:
                assessment = _assess_region(r)
                sections.append((r["region_name"], assessment))

            if active:
                survivors = "\n".join(f"- **{r['region_name']}**: sustainability {r['sustainability_score']:.1%}, strategy: {STRATEGY_INFO.get(r['dominant_strategy'], {}).get('label', r['dominant_strategy'])}" for r in active)
                sections.append(("Surviving Regions", survivors))

    # ── Survival Analysis ──
    elif intent == "survival_analysis":
        if not active:
            sections.append(("Simulation Assessment", "All regions have collapsed. No surviving agents remain."))
        else:
            # Rank by sustainability
            ranked = sorted(active, key=lambda r: r["sustainability_score"], reverse=True)
            best = ranked[0]
            sections.append(("Strongest Region", _assess_region(best)))

            if len(ranked) > 1:
                weakest = ranked[-1]
                sections.append(("Most Vulnerable", _assess_region(weakest)))

    # ── Training Insight ──
    elif intent == "training_insight":
        lines = []
        for r in regions:
            status = r["convergence_status"]
            trend = r["reward_trend"]
            icon = "✓" if status == "converged" else "⟳" if status == "learning" else "✗"
            lines.append(f"- {icon} **{r['region_name']}**: {status} (reward trend: {trend})")
        sections.append(("Convergence Status", "\n".join(lines)))

        # Interpret
        interp = []
        if any(r["convergence_status"] == "unstable" for r in regions):
            interp.append("Some agents exhibit unstable training dynamics, suggesting reward signal noise or environmental volatility.")
        if any(r["reward_trend"] == "declining" for r in regions):
            interp.append("Declining reward trends indicate agents may be trapped in suboptimal policy loops or facing worsening environmental conditions.")
        if any(r["convergence_status"] == "converged" and r["reward_trend"] == "stable" for r in regions):
            interp.append("Converged agents with stable rewards demonstrate successful policy learning — these represent the simulation's equilibrium strategies.")
        if interp:
            sections.append(("Interpretation", "\n\n".join(interp)))

    # ── Cooperation Analysis ──
    elif intent == "cooperation_analysis":
        coop_ratio = ctx["cooperation_ratio"]
        assessment = f"System cooperation ratio: **{coop_ratio:.0%}**. "
        if coop_ratio > 0.6:
            assessment += "Agents have developed predominantly cooperative strategies, suggesting emergent multi-agent coordination."
        elif coop_ratio > 0.3:
            assessment += "Mixed cooperative-competitive dynamics observed. Some agents cooperate while others exploit."
        else:
            assessment += "Low cooperation levels indicate agents have not learned the benefits of resource sharing. This often correlates with higher collapse rates."
        sections.append(("Cooperation Assessment", assessment))

        # Most cooperative
        ranked_coop = sorted(regions, key=lambda r: r["cooperation_index"], reverse=True)
        if ranked_coop:
            top = ranked_coop[0]
            sections.append(("Most Cooperative Agent", f"**{top['region_name']}** (cooperation index: {top['cooperation_index']:.2f}, {len(top['trade_partners'])} trade partners)"))
        isolated = [r for r in regions if r["cooperation_index"] == 0 and not r["collapsed"]]
        if isolated:
            sections.append(("Isolated Agents", f"{', '.join(r['region_name'] for r in isolated)} — no active trade relationships, elevated collapse risk"))

    # ── Strategy Analysis ──
    elif intent == "strategy_analysis":
        strat_groups = {}
        for r in regions:
            s = r["dominant_strategy"]
            strat_groups.setdefault(s, []).append(r)

        lines = []
        for s, rs in sorted(strat_groups.items(), key=lambda x: -len(x[1])):
            info = STRATEGY_INFO.get(s, {})
            active_in_group = [r for r in rs if not r["collapsed"]]
            collapsed_in_group = [r for r in rs if r["collapsed"]]
            line = f"**{info.get('label', s)}** ({len(rs)} region{'s' if len(rs) != 1 else ''}): {info.get('desc', 'unknown')}"
            if collapsed_in_group:
                line += f" — {len(collapsed_in_group)} collapsed"
            lines.append(f"- {line}")
        sections.append(("Strategy Distribution", "\n".join(lines)))

        # Effectiveness
        effective = []
        for s, rs in strat_groups.items():
            survival_rate = sum(1 for r in rs if not r["collapsed"]) / len(rs) if rs else 0
            avg_sust = sum(r["sustainability_score"] for r in rs) / len(rs) if rs else 0
            effective.append((s, survival_rate, avg_sust))
        effective.sort(key=lambda x: (x[1], x[2]), reverse=True)

        if effective:
            best_s = effective[0]
            info = STRATEGY_INFO.get(best_s[0], {})
            sections.append(("Most Effective Strategy", f"**{info.get('label', best_s[0])}** — {best_s[1]:.0%} survival rate, {best_s[2]:.1%} avg sustainability"))

    # ── Risk Outlook ──
    elif intent == "risk_outlook":
        high_risk = [r for r in active if r["collapse_risk"] == "high"]
        med_risk = [r for r in active if r["collapse_risk"] == "medium"]

        if high_risk:
            lines = [f"**{len(high_risk)} region(s)** face imminent collapse risk:"]
            for r in high_risk:
                expl = r.get("collapse_explanation", {})
                tooltip = expl.get("risk_tooltip", "")
                risk_val = expl.get("collapse_risk", 0)
                detail = tooltip if tooltip else f"collapse risk {risk_val:.0%}"
                lines.append(f"- **{r['region_name']}**: {detail}")
            sections.append(("Critical Risks", "\n".join(lines)))
        elif med_risk:
            sections.append(("Moderate Risks", f"{len(med_risk)} region(s) show moderate risk levels that warrant monitoring."))
        else:
            sections.append(("Risk Assessment", "All active regions maintain acceptable risk levels. No immediate systemic threats detected."))

    # ── Comparison ──
    elif intent == "comparison":
        if len(regions) < 2:
            sections.append(("Comparison", "Insufficient regions for comparison."))
        else:
            ranked = sorted(regions, key=lambda r: (not r["collapsed"], r["sustainability_score"]), reverse=True)
            strongest = ranked[0]
            weakest = ranked[-1]
            sections.append(("Strongest Region", _assess_region(strongest)))
            sections.append(("Weakest Region", _assess_region(weakest)))

            # Most cooperative
            most_coop = max(regions, key=lambda r: r["cooperation_index"])
            sections.append(("Most Cooperative", f"**{most_coop['region_name']}** — cooperation index: {most_coop['cooperation_index']:.2f}"))

    # ── Region Detail ──
    elif intent.startswith("region_detail:"):
        rid = int(intent.split(":")[1])
        target = next((r for r in regions if r["region_id"] == rid), None)
        if target:
            sections.append(("Region Analysis", _assess_region(target)))
            # Add resource breakdown
            res_text = (
                f"| Resource | Level |\n|----------|-------|\n"
                f"| Water | {target['water']} |\n"
                f"| Food | {target['food']} |\n"
                f"| Energy | {target['energy']} |\n"
                f"| Land | {target['land']} |\n"
                f"| Population | {target['population']} |"
            )
            sections.append(("Resource Breakdown", res_text))
        else:
            sections.append(("Error", f"Region {rid} not found in simulation data."))

    # ── Crowdsense Overview ──
    elif intent == "crowdsense_overview":
        try:
            from crowdsense.adapter import get_all_modifiers
            mods = get_all_modifiers()
            has_any = any(m["has_data"] for m in mods)
            if has_any:
                lines = ["Based on simulation dynamics influenced by regional sensing inputs:"]
                for m in mods:
                    if m["has_data"]:
                        sig = m.get("signals", {})
                        lines.append(
                            f"- **Region {m['region_id']}**: {m['label']} "
                            f"(population: {sig.get('population_pressure', 0):.0%}, "
                            f"energy: {sig.get('energy_activity', 0):.0%}, "
                            f"land: {sig.get('land_utilization', 0):.0%}, "
                            f"food demand: {sig.get('food_demand_index', 0):.0%}, "
                            f"{sig.get('sample_count', 0)} samples)"
                        )
                lines.append("")
                lines.append("Crowdsense signals map to simulation resource dimensions: "
                           "Food · Energy · Land · Population. "
                           "All conclusions remain grounded in RL dynamics.")
                sections.append(("Crowdsense Signal Analysis", "\n".join(lines)))
            else:
                sections.append(("Crowdsense Status", "No crowdsense data is currently available. "
                               "Start the detection module in the Crowdsense tab to begin contributing signals."))
        except ImportError:
            sections.append(("Crowdsense Status", "Crowdsense module is not active in this deployment."))

    # Confidence footer
    sections.append(("Confidence", f"**{confidence.capitalize()}** — based on {ctx['total_steps']} simulation timesteps. All insights are derived from simulation outputs and do not represent real-world measurements."))

    # Build full response
    full_response = "\n\n".join(_format_section(t, c) for t, c in sections)

    return {
        "response": full_response,
        "sections": [{"title": t, "content": c} for t, c in sections],
        "intent": intent,
        "confidence": confidence,
    }
