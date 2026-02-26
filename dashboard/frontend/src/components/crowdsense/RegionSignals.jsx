/*
 * RegionSignals — Crowdsense per-region signal strength cards
 */
import { useState, useEffect, useCallback } from "react";

const API = "http://localhost:5000";

const REGION_NAMES = [
    "Region 0", "Region 1", "Region 2", "Region 3", "Region 4", "Region 5"
];

function SignalBar({ label, value, color }) {
    const pct = Math.min(100, Math.round(value * 100));
    return (
        <div className="cs-signal-row">
            <span className="cs-signal-label">{label}</span>
            <div className="cs-signal-track">
                <div className="cs-signal-fill" style={{ width: `${pct}%`, background: color }} />
            </div>
            <span className="cs-signal-pct">{pct}%</span>
        </div>
    );
}

export default function RegionSignals({ activeRegion }) {
    const [signals, setSignals] = useState([]);
    const [loading, setLoading] = useState(false);

    const refresh = useCallback(async () => {
        setLoading(true);
        try {
            const resp = await fetch(`${API}/api/crowdsense/all-signals`);
            const data = await resp.json();
            setSignals(data.regions || []);
        } catch { /* ignore */ }
        setLoading(false);
    }, []);

    useEffect(() => {
        refresh();
        const iv = setInterval(refresh, 10000);
        return () => clearInterval(iv);
    }, [refresh]);

    return (
        <div className="cs-signals">
            <div className="cs-signals-header">
                <h4>
                    <span className="cs-pulse" />
                    Regional Signal Strength
                </h4>
                <button className="cs-refresh-btn" onClick={refresh} disabled={loading}>
                    {loading ? "..." : "↻"}
                </button>
            </div>

            <div className="cs-signals-grid">
                {REGION_NAMES.map((name, i) => {
                    const s = signals.find(x => x.region_id === i) || {};
                    const isActive = activeRegion === i;
                    const hasSamples = (s.sample_count || 0) > 0;
                    return (
                        <div key={i} className={`cs-signal-card ${isActive ? "active" : ""} ${hasSamples ? "has-data" : ""}`}>
                            <div className="cs-signal-card-header">
                                <span className="cs-signal-region">R{i}</span>
                                <span className="cs-signal-name">{name}</span>
                                {hasSamples && <span className="cs-signal-live">LIVE</span>}
                            </div>
                            <SignalBar label="Population" value={s.population_pressure || 0} color="#7B5CFF" />
                            <SignalBar label="Energy" value={s.energy_activity || 0} color="#22c55e" />
                            <SignalBar label="Land" value={s.land_utilization || 0} color="#f59e0b" />
                            <SignalBar label="Food Demand" value={s.food_demand_index || 0} color="#3b82f6" />
                            <div className="cs-signal-samples">
                                {hasSamples ? `${s.sample_count} samples / ${s.window_seconds}s` : "No data yet"}
                            </div>
                        </div>
                    );
                })}
            </div>
        </div>
    );
}
