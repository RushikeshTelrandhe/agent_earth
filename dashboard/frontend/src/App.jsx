/*
 * Agent Earth v2 - Interactive Multi-Agent Dashboard
 * ====================================================
 * Trade network, agent cards, trust heatmap, strategy timeline,
 * alliance graph, climate response, and cluster visualizations.
 */
import { useState, useEffect, useCallback, useMemo, lazy, Suspense } from "react";
import Plot from "react-plotly.js";
import "./App.css";

// Lazy-load the 3D globe
const GlobeScene = lazy(() => import("./components/earth/GlobeScene"));
import WebGLErrorBoundary from "./components/earth/WebGLErrorBoundary";

const API = "/api";

function hasWebGL() {
  try {
    const c = document.createElement('canvas');
    return !!(c.getContext('webgl2') || c.getContext('webgl'));
  } catch { return false; }
}

/* ── Helpers ──────────────────────────── */
const COLORS = ["#6366f1", "#06b6d4", "#22c55e", "#f59e0b", "#f43f5e", "#a855f7"];
const RES_COLORS = { water: "#3b82f6", food: "#22c55e", energy: "#f59e0b", land: "#a78bfa" };
const plotLayout = (title, extra = {}) => ({
  title: { text: title, font: { color: "#e2e8f0", size: 14 } },
  paper_bgcolor: "transparent", plot_bgcolor: "transparent",
  font: { color: "#94a3b8", size: 11 },
  margin: { l: 50, r: 20, t: 40, b: 40 },
  xaxis: { gridcolor: "rgba(148,163,184,0.08)" },
  yaxis: { gridcolor: "rgba(148,163,184,0.08)" },
  legend: { font: { size: 10 }, bgcolor: "transparent" },
  ...extra,
});

function getStrategyType(action) {
  if (action === "trade" || action === "conserve") return "cooperative";
  if (action === "hoard" || action === "expand_pop") return "greedy";
  if (action === "invest_growth") return "adaptive";
  return "balanced";
}

export default function App() {
  const [preset, setPreset] = useState("default");
  const [mode, setMode] = useState("independent");
  const [severity, setSeverity] = useState(1.0);
  const [steps, setSteps] = useState(300);
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [savedRuns, setSavedRuns] = useState([]);
  const [replayStep, setReplayStep] = useState(0);
  const [activeTab, setActiveTab] = useState("analytics");
  const [safeMode, setSafeMode] = useState(false);
  const [globeLoaded, setGlobeLoaded] = useState(false);

  const fetchRuns = useCallback(() => {
    fetch(`${API}/results`).then(r => r.json()).then(d => setSavedRuns(d.files || [])).catch(() => { });
  }, []);
  useEffect(fetchRuns, [fetchRuns]);

  const runSim = async () => {
    setLoading(true);
    try {
      const resp = await fetch(`${API}/run`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ preset, timesteps: steps, climate_severity: severity, mode }),
      });
      const json = await resp.json();
      setData(json);
      setReplayStep(0);
      fetchRuns();
    } catch (e) { console.error(e); }
    setLoading(false);
  };

  const loadRun = async (file) => {
    setLoading(true);
    try {
      const resp = await fetch(`${API}/results/${file}`);
      const json = await resp.json();
      setData(json);
      setReplayStep(0);
    } catch (e) { console.error(e); }
    setLoading(false);
  };

  // Derived data
  const allSteps = data?.steps || [];
  const analysis = data?.analysis || {};
  const summary = data?.summary || {};
  const maxStep = allSteps.length > 0 ? allSteps[allSteps.length - 1]?.step || 0 : 0;
  const replayData = allSteps[Math.min(replayStep, allSteps.length - 1)] || {};
  const numRegions = replayData?.regions?.length || 6;

  return (
    <div className="app">
      {/* ── Header ─── */}
      <header className="header">
        <div className="header-glow" />
        <h1>Agent Earth</h1>
        <p className="subtitle">Adaptive Multi-Agent Resource Scarcity Simulator</p>
      </header>

      {/* ── Tab Navigation ─── */}
      <nav className="tab-nav">
        <button className={`tab-btn ${activeTab === 'analytics' ? 'active' : ''}`} onClick={() => setActiveTab('analytics')}>
          📊 Analytics
        </button>
        <button className={`tab-btn ${activeTab === 'globe' ? 'active' : ''}`} onClick={() => { setActiveTab('globe'); setGlobeLoaded(true); }} disabled={!hasWebGL()}>
          🌍 Holographic Earth
        </button>
      </nav>

      {/* ── Controls ─── */}
      <section className="controls-section">
        <div className="controls-grid">
          <div className="control-group">
            <label>Preset</label>
            <select value={preset} onChange={e => setPreset(e.target.value)}>
              <option value="default">Default</option>
              <option value="scarcity">Scarcity</option>
              <option value="abundance">Abundance</option>
            </select>
          </div>
          <div className="control-group">
            <label>Mode</label>
            <select value={mode} onChange={e => setMode(e.target.value)}>
              <option value="independent">Independent Agents</option>
              <option value="shared">Shared Policy</option>
            </select>
          </div>
          <div className="control-group">
            <label>Climate Severity <span className="val">{severity.toFixed(1)}</span></label>
            <input type="range" min="0" max="3" step="0.1" value={severity} onChange={e => setSeverity(+e.target.value)} />
          </div>
          <div className="control-group">
            <label>Timesteps <span className="val">{steps}</span></label>
            <input type="range" min="50" max="1000" step="50" value={steps} onChange={e => setSteps(+e.target.value)} />
          </div>
          <button className="run-btn" onClick={runSim} disabled={loading}>
            {loading ? "Running..." : "Simulate"}
          </button>
        </div>
        <div className="saved-runs">
          <button className="secondary-btn" onClick={fetchRuns}>Saved Runs</button>
          {savedRuns.slice(-8).map(f => (
            <button key={f} className="run-chip" onClick={() => loadRun(f)}>{f.replace("run_", "").replace(".json", "")}</button>
          ))}
        </div>
      </section>

      {data && (
        <>
          {/* ── Summary Cards ─── */}
          <SummaryCards summary={summary} analysis={analysis} />

          {/* ── Insights ─── */}
          {analysis.insights && (
            <div className="insights-banner">
              <strong>AI Insights: </strong>{analysis.insights}
            </div>
          )}

          {/* ── Globe Tab (persistent mount — hidden via CSS, never unmounted) ─── */}
          {globeLoaded && (
            <div style={{ display: activeTab === 'globe' ? 'block' : 'none' }}>
              <section className="chart-section">
                <h2>
                  <span className="icon">🌍</span> Holographic Earth
                  <span style={{ fontSize: '0.7rem', color: '#64748b', fontWeight: 400, marginLeft: 8 }}>node size=pop, color=strategy, arcs=trade</span>
                  <button
                    onClick={() => setSafeMode(m => !m)}
                    style={{
                      marginLeft: 12, padding: '2px 10px', fontSize: '0.65rem',
                      borderRadius: 6, border: '1px solid rgba(148,163,184,0.2)',
                      background: safeMode ? 'rgba(34,197,94,0.15)' : 'transparent',
                      color: safeMode ? '#22c55e' : '#64748b', cursor: 'pointer',
                      fontFamily: 'Inter,sans-serif', verticalAlign: 'middle',
                    }}
                  >
                    {safeMode ? '🛡️ Safe Mode ON' : '🛡️ Safe Mode'}
                  </button>
                </h2>
                <WebGLErrorBoundary height={600} onFallback={() => setActiveTab('analytics')}>
                  <Suspense fallback={<div style={{ height: 600, display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#64748b' }}>Loading 3D Engine...</div>}>
                    <GlobeScene stepData={replayData} allSteps={allSteps} replayStep={replayStep} safeMode={safeMode} />
                  </Suspense>
                </WebGLErrorBoundary>
              </section>
              <CollapseReplay allSteps={allSteps} replayStep={replayStep} setReplayStep={setReplayStep} maxStep={maxStep} replayData={replayData} />
            </div>
          )}

          {/* ── Analytics Tab ─── */}
          {activeTab === 'analytics' && (
            <>
              {/* ── Agent Behavior Cards ─── */}
              <AgentCards replayData={replayData} analysis={analysis} />

              {/* ── Trade Network ─── */}
              <TradeNetwork allSteps={allSteps} numRegions={numRegions} replayStep={replayStep} />

              {/* ── Strategy Evolution Timeline ─── */}
              <StrategyTimeline analysis={analysis} allSteps={allSteps} numRegions={numRegions} />

              {/* ── Resource Time Series + Trust Heatmap ─── */}
              <div className="chart-grid" style={{ marginBottom: 22 }}>
                <ResourceTimeSeries allSteps={allSteps} numRegions={numRegions} />
                <TrustHeatmap allSteps={allSteps} replayStep={replayStep} numRegions={numRegions} />
              </div>

              {/* ── Collapse Replay ─── */}
              <CollapseReplay allSteps={allSteps} replayStep={replayStep} setReplayStep={setReplayStep} maxStep={maxStep} replayData={replayData} />

              {/* ── Climate Resilience + Trade Dependency ─── */}
              <div className="chart-grid" style={{ marginBottom: 22 }}>
                <ResilienceTable analysis={analysis} />
                <TradeDependency analysis={analysis} numRegions={numRegions} />
              </div>

              {/* ── Clusters ─── */}
              <Clusters analysis={analysis} />
            </>
          )}
        </>
      )}

      <footer className="footer">Agent Earth v2 - Multi-Agent RL Simulator</footer>
    </div>
  );
}

/* ══════════ Summary Cards ══════════ */
function SummaryCards({ summary, analysis }) {
  const coop = analysis.cooperation_vs_greed || {};
  const collapses = analysis.collapses || [];
  const survival = analysis.survival_rates || {};
  const survived = Object.values(survival).filter(v => v >= 1.0).length;
  const total = Object.keys(survival).length;
  return (
    <section className="summary-section">
      <div className="cards">
        <div className="card"><div className="card-icon">⚡</div><div className="card-value">{summary.steps_completed || 0}</div><div className="card-label">Steps</div></div>
        <div className="card"><div className="card-icon">🏆</div><div className="card-value">{summary.total_reward || 0}</div><div className="card-label">Total Reward</div></div>
        <div className="card"><div className="card-icon">🌍</div><div className="card-value">{survived}/{total}</div><div className="card-label">Survived</div></div>
        <div className="card"><div className="card-icon">💀</div><div className="card-value" style={{ color: collapses.length ? "#ef4444" : "#22c55e" }}>{collapses.length}</div><div className="card-label">Collapses</div></div>
        <div className="card"><div className="card-icon">🤝</div><div className="card-value">{((coop.cooperation_ratio || 0) * 100).toFixed(0)}%</div><div className="card-label">Cooperation</div></div>
        <div className="card"><div className="card-icon">📊</div><div className="card-value">{analysis.inequality_mean || 0}</div><div className="card-label">Gini Index</div></div>
      </div>
    </section>
  );
}

/* ══════════ Agent Behavior Cards ══════════ */
function AgentCards({ replayData, analysis }) {
  const regions = replayData?.regions || [];
  const dominant = analysis?.dominant_strategies || {};
  const tradeDep = analysis?.trade_dependency || {};

  return (
    <section className="chart-section">
      <h2><span className="icon">🤖</span> Agent Behavior</h2>
      <div className="agent-cards-grid">
        {regions.map(r => {
          const strat = getStrategyType(dominant[r.id] || r.last_action);
          const collapseRisk = r.collapsed ? 100 : Math.max(0, 100 - (r.sustainability || 0) * 100 - ((r.water + r.food + r.energy) / 3));
          const dep = tradeDep[r.id] || {};
          return (
            <div key={r.id} className={`agent-card ${r.collapsed ? "collapsed-card" : ""}`}>
              <div className="agent-card-header">
                <span className="agent-id">{r.collapsed ? "💀" : "🌐"} Region {r.id}</span>
                <span className={`agent-strategy-badge strategy-${strat}`}>{strat}</span>
              </div>
              <div className="agent-meters">
                <MeterBar label="Water" value={r.water} max={100} cls="water" />
                <MeterBar label="Food" value={r.food} max={100} cls="food" />
                <MeterBar label="Energy" value={r.energy} max={100} cls="energy" />
                <MeterBar label="Sustain." value={(r.sustainability || 0) * 100} max={100} cls="sustainability" />
                <MeterBar label="Risk" value={Math.min(100, Math.max(0, collapseRisk))} max={100} cls="collapse-risk" />
              </div>
              <div className="agent-partners">
                Pop: <span>{r.population}</span> | Partners: <span>{(r.trade_partners || []).join(", ") || "none"}</span>
                {dep.trade_count > 0 && <> | Trades: <span>{dep.trade_count}</span></>}
              </div>
            </div>
          );
        })}
      </div>
    </section>
  );
}

function MeterBar({ label, value, max, cls }) {
  const pct = Math.min(100, Math.max(0, (value / max) * 100));
  return (
    <div className="meter-row">
      <span className="meter-label">{label}</span>
      <div className="meter-bar"><div className={`meter-fill ${cls}`} style={{ width: `${pct}%` }} /></div>
      <span className="meter-val">{Math.round(value)}</span>
    </div>
  );
}

/* ══════════ Trade Network ══════════ */
function TradeNetwork({ allSteps, numRegions, replayStep }) {
  // Aggregate trades from last N steps around replay position
  const windowSize = Math.min(20, allSteps.length);
  const start = Math.max(0, replayStep - windowSize);
  const end = Math.min(allSteps.length, replayStep + 1);

  const tradeVolume = {};
  const tradesByResource = {};
  for (let s = start; s < end; s++) {
    const trades = allSteps[s]?.trades || [];
    for (const t of trades) {
      if (!t.accepted && t.accepted !== undefined) continue;
      const key = `${t.from}-${t.to}`;
      tradeVolume[key] = (tradeVolume[key] || 0) + (t.amount || 0);
      tradesByResource[key] = t.resource;
    }
  }

  // Circular layout for regions
  const nodeX = [], nodeY = [], nodeText = [];
  for (let i = 0; i < numRegions; i++) {
    const angle = (2 * Math.PI * i) / numRegions - Math.PI / 2;
    nodeX.push(Math.cos(angle));
    nodeY.push(Math.sin(angle));
    nodeText.push(`R${i}`);
  }

  const traces = [];
  // Trade arrows
  for (const [key, vol] of Object.entries(tradeVolume)) {
    const [from, to] = key.split("-").map(Number);
    const res = tradesByResource[key] || "water";
    traces.push({
      x: [nodeX[from], nodeX[to], null],
      y: [nodeY[from], nodeY[to], null],
      mode: "lines",
      line: { width: Math.min(8, 1 + vol / 5), color: RES_COLORS[res] || "#6366f1" },
      opacity: 0.7,
      hoverinfo: "text",
      text: `R${from} -> R${to}: ${vol.toFixed(1)} (${res})`,
      showlegend: false,
    });
  }

  // Region nodes
  traces.push({
    x: nodeX, y: nodeY,
    mode: "markers+text",
    marker: { size: 28, color: COLORS.slice(0, numRegions), line: { width: 2, color: "#1a2035" } },
    text: nodeText,
    textfont: { color: "#f1f5f9", size: 12, weight: 700 },
    textposition: "middle center",
    hoverinfo: "text",
    showlegend: false,
  });

  return (
    <section className="chart-section">
      <h2><span className="icon">🔗</span> Trade Network <span style={{ fontSize: "0.7rem", color: "#64748b", fontWeight: 400 }}>(arrow thickness = volume, color = resource)</span></h2>
      <Plot
        data={traces}
        layout={plotLayout("", {
          xaxis: { visible: false, range: [-1.5, 1.5] },
          yaxis: { visible: false, range: [-1.5, 1.5], scaleanchor: "x" },
          margin: { l: 10, r: 10, t: 10, b: 10 },
          height: 380,
        })}
        config={{ displayModeBar: false }}
        style={{ width: "100%" }}
      />
    </section>
  );
}

/* ══════════ Strategy Evolution Timeline ══════════ */
function StrategyTimeline({ analysis, allSteps, numRegions }) {
  const evolution = analysis?.strategy_evolution || {};
  const events = useMemo(() => {
    const evts = [];
    for (const s of allSteps) {
      for (const e of (s.events || [])) {
        evts.push({ step: s.step, event: e });
      }
    }
    return evts;
  }, [allSteps]);

  // Build per-region stacked area
  const traces = [];
  const actionNames = ["hoard", "trade", "invest_growth", "conserve", "expand_pop"];
  const actionColors = ["#ef4444", "#06b6d4", "#22c55e", "#6366f1", "#f59e0b"];

  const selectedRegion = 0; // show first region by default, others available via dropdown

  for (let rid = 0; rid < Math.min(numRegions, 3); rid++) {
    const timeline = evolution[rid] || [];
    if (!timeline.length) continue;
    const xVals = timeline.map(t => t.step);
    for (let ai = 0; ai < actionNames.length; ai++) {
      traces.push({
        x: xVals,
        y: timeline.map(t => (t[actionNames[ai]] || 0) * 100),
        name: rid === 0 ? actionNames[ai] : undefined,
        type: "scatter",
        mode: "lines",
        stackgroup: `r${rid}`,
        line: { width: 0, color: actionColors[ai] },
        fillcolor: actionColors[ai] + "60",
        showlegend: rid === 0,
        xaxis: rid === 0 ? "x" : rid === 1 ? "x2" : "x3",
        yaxis: rid === 0 ? "y" : rid === 1 ? "y2" : "y3",
      });
    }
  }

  // Climate event markers
  const eventShapes = events.slice(0, 50).map(e => ({
    type: "line", x0: e.step, x1: e.step, y0: 0, y1: 100,
    line: { color: "#ef444455", width: 1, dash: "dot" },
  }));

  return (
    <section className="chart-section">
      <h2><span className="icon">📈</span> Strategy Evolution <span style={{ fontSize: "0.7rem", color: "#64748b", fontWeight: 400 }}>(action % over time | R0, R1, R2)</span></h2>
      <Plot
        data={traces}
        layout={{
          ...plotLayout(""),
          grid: { rows: 1, columns: Math.min(numRegions, 3), pattern: "independent" },
          height: 280,
          margin: { l: 40, r: 20, t: 10, b: 40 },
          shapes: eventShapes,
          xaxis: { title: "R0", gridcolor: "rgba(148,163,184,0.08)" },
          xaxis2: { title: "R1", gridcolor: "rgba(148,163,184,0.08)" },
          xaxis3: { title: "R2", gridcolor: "rgba(148,163,184,0.08)" },
          yaxis: { title: "%", gridcolor: "rgba(148,163,184,0.08)", range: [0, 100] },
          yaxis2: { gridcolor: "rgba(148,163,184,0.08)", range: [0, 100] },
          yaxis3: { gridcolor: "rgba(148,163,184,0.08)", range: [0, 100] },
        }}
        config={{ displayModeBar: false }}
        style={{ width: "100%" }}
      />
    </section>
  );
}

/* ══════════ Resource Time Series ══════════ */
function ResourceTimeSeries({ allSteps, numRegions }) {
  const resources = ["water", "food", "energy", "land"];
  const traces = [];
  for (let rid = 0; rid < numRegions; rid++) {
    const xVals = allSteps.map(s => s.step);
    for (const res of resources) {
      traces.push({
        x: xVals, y: allSteps.map(s => (s.regions?.[rid]?.[res] || 0)),
        name: `R${rid} ${res}`, mode: "lines",
        line: { width: 1.5, color: RES_COLORS[res] },
        opacity: 0.6,
        legendgroup: res,
        showlegend: rid === 0,
        visible: res === "water" || res === "food" ? true : "legendonly",
      });
    }
  }
  return (
    <section className="chart-section">
      <h2><span className="icon">📊</span> Resources Over Time</h2>
      <Plot data={traces} layout={plotLayout("", { height: 320, margin: { l: 50, r: 20, t: 10, b: 40 } })} config={{ displayModeBar: false }} style={{ width: "100%" }} />
    </section>
  );
}

/* ══════════ Trust Heatmap ══════════ */
function TrustHeatmap({ allSteps, replayStep, numRegions }) {
  const stepData = allSteps[Math.min(replayStep, allSteps.length - 1)] || {};
  const trustMatrix = stepData?.trust_matrix;

  if (!trustMatrix || !trustMatrix.length) {
    return (
      <section className="chart-section">
        <h2><span className="icon">🤝</span> Trust Matrix</h2>
        <p style={{ color: "#64748b", fontSize: "0.85rem" }}>Trust data not available for this run.</p>
      </section>
    );
  }

  const labels = Array.from({ length: numRegions }, (_, i) => `R${i}`);
  return (
    <section className="chart-section">
      <h2><span className="icon">🤝</span> Trust Matrix <span style={{ fontSize: "0.7rem", color: "#64748b", fontWeight: 400 }}>(step {stepData.step || replayStep})</span></h2>
      <div className="trust-matrix-container">
        <Plot
          data={[{
            z: trustMatrix, x: labels, y: labels,
            type: "heatmap",
            colorscale: [[0, "#0f172a"], [0.5, "#6366f1"], [1, "#22c55e"]],
            showscale: true,
            colorbar: { tickfont: { color: "#94a3b8" }, len: 0.8 },
          }]}
          layout={plotLayout("", {
            height: 300, width: 340,
            margin: { l: 40, r: 20, t: 10, b: 40 },
            xaxis: { side: "bottom" }, yaxis: { autorange: "reversed" },
          })}
          config={{ displayModeBar: false }}
        />
      </div>
    </section>
  );
}

/* ══════════ Collapse Replay ══════════ */
function CollapseReplay({ allSteps, replayStep, setReplayStep, maxStep, replayData }) {
  const regions = replayData?.regions || [];
  return (
    <section className="chart-section">
      <h2><span className="icon">🔄</span> World Replay</h2>
      <div className="replay-controls">
        <span style={{ fontSize: "0.8rem", color: "#94a3b8" }}>Step {replayStep}</span>
        <input type="range" min={0} max={Math.max(0, allSteps.length - 1)} value={replayStep} onChange={e => setReplayStep(+e.target.value)} />
        <span style={{ fontSize: "0.8rem", color: "#64748b" }}>{maxStep}</span>
      </div>
      <div className="replay-grid">
        {regions.map(r => (
          <div key={r.id} className={`replay-card ${r.collapsed ? "collapsed" : "alive"}`}>
            <div className="replay-id">Region {r.id}</div>
            <div className="replay-status">{r.collapsed ? "💀" : "🌍"}</div>
            <div className="replay-stats">
              <span>W:{r.water}</span><span>F:{r.food}</span>
              <span>E:{r.energy}</span><span>L:{r.land}</span>
              <span>Pop:{r.population}</span><span>S:{r.sustainability}</span>
              <span>Act:{r.last_action}</span>
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}

/* ══════════ Resilience Table ══════════ */
function ResilienceTable({ analysis }) {
  const resilience = analysis?.climate_resilience || [];
  const medals = ["🥇", "🥈", "🥉"];
  return (
    <section className="chart-section">
      <h2><span className="icon">🛡️</span> Climate Resilience Ranking</h2>
      <table className="resilience-table">
        <thead><tr><th>#</th><th>Region</th><th>Survival</th><th>Avg Sustain.</th><th>Score</th></tr></thead>
        <tbody>
          {resilience.map((r, i) => (
            <tr key={r.region}>
              <td><span className="rank-medal">{medals[i] || i + 1}</span></td>
              <td style={{ fontWeight: 600 }}>Region {r.region}</td>
              <td>{(r.survival * 100).toFixed(0)}%</td>
              <td>{r.avg_sustainability}</td>
              <td style={{ color: "#6366f1", fontWeight: 600 }}>{r.resilience_score}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  );
}

/* ══════════ Trade Dependency ══════════ */
function TradeDependency({ analysis, numRegions }) {
  const dep = analysis?.trade_dependency || {};
  const labels = Object.keys(dep).map(k => `R${k}`);
  return (
    <section className="chart-section">
      <h2><span className="icon">📦</span> Trade Dependency</h2>
      <Plot
        data={[
          { x: labels, y: labels.map((_, i) => dep[i]?.sent || 0), name: "Sent", type: "bar", marker: { color: "#6366f1" } },
          { x: labels, y: labels.map((_, i) => dep[i]?.received || 0), name: "Received", type: "bar", marker: { color: "#06b6d4" } },
        ]}
        layout={plotLayout("", { barmode: "group", height: 260, margin: { l: 40, r: 20, t: 10, b: 40 } })}
        config={{ displayModeBar: false }}
        style={{ width: "100%" }}
      />
    </section>
  );
}

/* ══════════ Clusters ══════════ */
function Clusters({ analysis }) {
  const clusters = analysis?.clusters || {};
  const labels = clusters.labels || {};
  return (
    <section className="chart-section">
      <h2><span className="icon">🧬</span> Behavioral Clusters</h2>
      <div className="cluster-grid">
        {Object.entries(labels).map(([rid, cid]) => (
          <div key={rid} className={`cluster-badge cluster-${cid % 3}`}>
            Region {rid}: Cluster {cid}
          </div>
        ))}
      </div>
    </section>
  );
}
