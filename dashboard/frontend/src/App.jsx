import { useState, useCallback } from 'react'
import Plot from 'react-plotly.js'
import './App.css'

const API = '/api'

function App() {
  const [config, setConfig] = useState({
    preset: 'default',
    timesteps: 300,
    climate_severity: 1.0,
  })
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(false)
  const [replayStep, setReplayStep] = useState(0)
  const [savedRuns, setSavedRuns] = useState([])

  /* ── Run simulation ──────────────────────── */
  const runSimulation = useCallback(async () => {
    setLoading(true)
    try {
      const res = await fetch(`${API}/run`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(config),
      })
      const json = await res.json()
      setData(json)
      setReplayStep(0)
    } catch (e) {
      console.error(e)
    }
    setLoading(false)
  }, [config])

  /* ── Load saved runs list ────────────────── */
  const loadSavedRuns = useCallback(async () => {
    const res = await fetch(`${API}/results`)
    const json = await res.json()
    setSavedRuns(json.files || [])
  }, [])

  const loadRun = useCallback(async (filename) => {
    setLoading(true)
    const res = await fetch(`${API}/results/${filename}`)
    const json = await res.json()
    setData(json)
    setReplayStep(0)
    setLoading(false)
  }, [])

  /* ── Helpers ─────────────────────────────── */
  const resources = ['water', 'food', 'energy', 'land']
  const colors = {
    water: '#3b82f6', food: '#22c55e', energy: '#f59e0b', land: '#a78bfa',
    population: '#ec4899', sustainability: '#06b6d4',
  }

  const getRegionTimeSeries = (steps, regionId, field) =>
    steps.map(s => {
      const r = s.regions?.find(r => r.id === regionId)
      return r ? r[field] : 0
    })

  const numRegions = data?.steps?.[0]?.regions?.length || 6

  return (
    <div className="app">
      {/* ── Header ──────────────────────────── */}
      <header className="header">
        <div className="header-glow"></div>
        <h1>🌍 Agent Earth</h1>
        <p className="subtitle">Adaptive Multi-Agent Resource Scarcity Simulator</p>
      </header>

      {/* ── Controls ────────────────────────── */}
      <section className="controls-section">
        <div className="controls-grid">
          <div className="control-group">
            <label>Preset</label>
            <select value={config.preset} onChange={e => setConfig(c => ({ ...c, preset: e.target.value }))}>
              <option value="default">Default</option>
              <option value="scarcity">Scarcity</option>
              <option value="abundance">Abundance</option>
            </select>
          </div>
          <div className="control-group">
            <label>Simulation Length: <span className="val">{config.timesteps}</span></label>
            <input type="range" min={50} max={1000} step={50}
              value={config.timesteps} onChange={e => setConfig(c => ({ ...c, timesteps: +e.target.value }))} />
          </div>
          <div className="control-group">
            <label>Climate Severity: <span className="val">{config.climate_severity.toFixed(1)}</span></label>
            <input type="range" min={0} max={3} step={0.1}
              value={config.climate_severity} onChange={e => setConfig(c => ({ ...c, climate_severity: +e.target.value }))} />
          </div>
          <button className="run-btn" onClick={runSimulation} disabled={loading}>
            {loading ? '⏳ Running…' : '▶ Run Simulation'}
          </button>
        </div>

        <div className="saved-runs">
          <button className="secondary-btn" onClick={loadSavedRuns}>📂 Load Saved Runs</button>
          {savedRuns.map(f => (
            <button key={f} className="run-chip" onClick={() => loadRun(f)}>{f}</button>
          ))}
        </div>
      </section>

      {/* ── Dashboard ───────────────────────── */}
      {data && (
        <>
          {/* ── Summary Cards ───────────────── */}
          <section className="summary-section">
            <div className="cards">
              <div className="card">
                <div className="card-icon">📊</div>
                <div className="card-value">{data.summary?.total_reward ?? '—'}</div>
                <div className="card-label">Total Reward</div>
              </div>
              <div className="card">
                <div className="card-icon">⏱</div>
                <div className="card-value">{data.summary?.steps_completed ?? data.steps?.length ?? '—'}</div>
                <div className="card-label">Steps</div>
              </div>
              <div className="card">
                <div className="card-icon">💀</div>
                <div className="card-value">{data.analysis?.collapses?.length ?? 0}</div>
                <div className="card-label">Collapses</div>
              </div>
              <div className="card">
                <div className="card-icon">🤝</div>
                <div className="card-value">
                  {data.analysis?.cooperation_vs_greed
                    ? (data.analysis.cooperation_vs_greed.cooperation_ratio * 100).toFixed(1) + '%'
                    : '—'}
                </div>
                <div className="card-label">Cooperation</div>
              </div>
              <div className="card">
                <div className="card-icon">📈</div>
                <div className="card-value">{data.analysis?.inequality_final ?? '—'}</div>
                <div className="card-label">Final Gini</div>
              </div>
              <div className="card">
                <div className="card-icon">🔗</div>
                <div className="card-value">
                  {data.analysis?.sustainability_survival_corr ?? '—'}
                </div>
                <div className="card-label">Sust↔Surv Corr</div>
              </div>
            </div>
          </section>

          {/* ── Resource Heatmap ────────────── */}
          <section className="chart-section">
            <h2>🗺 Resource Heatmap (Final State)</h2>
            <Plot
              data={[{
                z: resources.map(res =>
                  Array.from({ length: numRegions }, (_, i) => {
                    const last = data.steps[data.steps.length - 1]
                    return last?.regions?.[i]?.[res] ?? 0
                  })
                ),
                x: Array.from({ length: numRegions }, (_, i) => `Region ${i}`),
                y: resources.map(r => r.charAt(0).toUpperCase() + r.slice(1)),
                type: 'heatmap',
                colorscale: 'YlGnBu',
                colorbar: { title: 'Level' },
              }]}
              layout={{
                paper_bgcolor: 'rgba(0,0,0,0)', plot_bgcolor: 'rgba(0,0,0,0)',
                font: { color: '#e2e8f0' }, margin: { t: 30, b: 50, l: 80, r: 30 },
                height: 280,
              }}
              config={{ responsive: true }}
              style={{ width: '100%' }}
            />
          </section>

          {/* ── Time-Series Graphs ──────────── */}
          <section className="chart-section">
            <h2>📈 Resource Time Series</h2>
            <div className="chart-grid">
              {resources.map(res => (
                <Plot key={res}
                  data={Array.from({ length: numRegions }, (_, i) => ({
                    x: data.steps.map(s => s.step),
                    y: getRegionTimeSeries(data.steps, i, res),
                    type: 'scatter', mode: 'lines',
                    name: `R${i}`,
                    line: { width: 1.5 },
                  }))}
                  layout={{
                    title: { text: res.charAt(0).toUpperCase() + res.slice(1), font: { size: 14 } },
                    paper_bgcolor: 'rgba(0,0,0,0)', plot_bgcolor: 'rgba(0,0,0,0)',
                    font: { color: '#e2e8f0', size: 10 },
                    margin: { t: 40, b: 30, l: 40, r: 10 },
                    height: 250, showlegend: false,
                    xaxis: { gridcolor: '#334155' }, yaxis: { gridcolor: '#334155' },
                  }}
                  config={{ responsive: true }}
                  style={{ width: '100%' }}
                />
              ))}
            </div>
          </section>

          {/* ── Population & Sustainability ─── */}
          <section className="chart-section">
            <h2>👥 Population & 🌱 Sustainability</h2>
            <div className="chart-grid two-col">
              <Plot
                data={Array.from({ length: numRegions }, (_, i) => ({
                  x: data.steps.map(s => s.step),
                  y: getRegionTimeSeries(data.steps, i, 'population'),
                  type: 'scatter', mode: 'lines',
                  name: `R${i}`, line: { width: 1.5 },
                }))}
                layout={{
                  title: { text: 'Population', font: { size: 14 } },
                  paper_bgcolor: 'rgba(0,0,0,0)', plot_bgcolor: 'rgba(0,0,0,0)',
                  font: { color: '#e2e8f0', size: 10 }, margin: { t: 40, b: 30, l: 50, r: 10 },
                  height: 280, showlegend: true, legend: { orientation: 'h', y: -0.2 },
                  xaxis: { gridcolor: '#334155' }, yaxis: { gridcolor: '#334155' },
                }}
                config={{ responsive: true }} style={{ width: '100%' }}
              />
              <Plot
                data={Array.from({ length: numRegions }, (_, i) => ({
                  x: data.steps.map(s => s.step),
                  y: getRegionTimeSeries(data.steps, i, 'sustainability'),
                  type: 'scatter', mode: 'lines',
                  name: `R${i}`, line: { width: 1.5 },
                }))}
                layout={{
                  title: { text: 'Sustainability', font: { size: 14 } },
                  paper_bgcolor: 'rgba(0,0,0,0)', plot_bgcolor: 'rgba(0,0,0,0)',
                  font: { color: '#e2e8f0', size: 10 }, margin: { t: 40, b: 30, l: 50, r: 10 },
                  height: 280, showlegend: true, legend: { orientation: 'h', y: -0.2 },
                  xaxis: { gridcolor: '#334155' }, yaxis: { gridcolor: '#334155', range: [0, 1] },
                }}
                config={{ responsive: true }} style={{ width: '100%' }}
              />
            </div>
          </section>

          {/* ── Survival Timeline ──────────── */}
          <section className="chart-section">
            <h2>⏳ Survival Timeline</h2>
            <Plot
              data={Array.from({ length: numRegions }, (_, i) => ({
                x: data.steps.map(s => s.step),
                y: data.steps.map(s => {
                  const r = s.regions?.find(r => r.id === i)
                  return r ? (r.collapsed ? 0 : 1) : 1
                }),
                type: 'scatter', mode: 'lines',
                name: `Region ${i}`,
                fill: 'tozeroy', opacity: 0.5,
                line: { width: 1 },
              }))}
              layout={{
                paper_bgcolor: 'rgba(0,0,0,0)', plot_bgcolor: 'rgba(0,0,0,0)',
                font: { color: '#e2e8f0' }, margin: { t: 20, b: 40, l: 40, r: 10 },
                height: 250,
                yaxis: { title: 'Alive', range: [-0.1, 1.1], gridcolor: '#334155' },
                xaxis: { title: 'Step', gridcolor: '#334155' },
                showlegend: true, legend: { orientation: 'h', y: -0.3 },
              }}
              config={{ responsive: true }} style={{ width: '100%' }}
            />
          </section>

          {/* ── Collapse Replay ─────────────── */}
          <section className="chart-section">
            <h2>🔄 Collapse Replay</h2>
            <div className="replay-controls">
              <input type="range" min={0} max={(data.steps?.length || 1) - 1}
                value={replayStep}
                onChange={e => setReplayStep(+e.target.value)} />
              <span className="val">Step {data.steps?.[replayStep]?.step ?? replayStep}</span>
            </div>
            <div className="replay-grid">
              {data.steps?.[replayStep]?.regions?.map(r => (
                <div key={r.id} className={`replay-card ${r.collapsed ? 'collapsed' : 'alive'}`}>
                  <div className="replay-id">R{r.id}</div>
                  <div className="replay-status">{r.collapsed ? '💀' : '✅'}</div>
                  <div className="replay-stats">
                    <span>W: {r.water}</span><span>F: {r.food}</span>
                    <span>E: {r.energy}</span><span>Pop: {Math.round(r.population)}</span>
                    <span>Sust: {r.sustainability}</span>
                    <span>Act: {r.last_action}</span>
                  </div>
                </div>
              ))}
            </div>
          </section>

          {/* ── Trade Network ──────────────── */}
          {data.analysis?.dominant_strategies && (
            <section className="chart-section">
              <h2>🔀 Strategy Comparison</h2>
              <Plot
                data={[{
                  x: Object.keys(data.analysis.dominant_strategies).map(k => `Region ${k}`),
                  y: Object.keys(data.analysis.dominant_strategies).map(() => 1),
                  text: Object.values(data.analysis.dominant_strategies),
                  type: 'bar',
                  marker: {
                    color: Object.values(data.analysis.dominant_strategies).map(s => {
                      const map = { hoard: '#ef4444', trade: '#22c55e', invest_growth: '#3b82f6', conserve: '#06b6d4', expand_pop: '#f59e0b', none: '#6b7280' }
                      return map[s] || '#6b7280'
                    }),
                  },
                  textposition: 'auto',
                }]}
                layout={{
                  paper_bgcolor: 'rgba(0,0,0,0)', plot_bgcolor: 'rgba(0,0,0,0)',
                  font: { color: '#e2e8f0' }, margin: { t: 20, b: 60, l: 40, r: 10 },
                  height: 250,
                  yaxis: { visible: false }, xaxis: { gridcolor: '#334155' },
                }}
                config={{ responsive: true }} style={{ width: '100%' }}
              />
            </section>
          )}

          {/* ── Cluster Visualization ──────── */}
          {data.analysis?.clusters?.labels && (
            <section className="chart-section">
              <h2>🧬 Behaviour Clusters (KMeans)</h2>
              <div className="cluster-grid">
                {Object.entries(data.analysis.clusters.labels).map(([rid, cluster]) => (
                  <div key={rid} className={`cluster-badge cluster-${cluster}`}>
                    Region {rid}: Cluster {cluster}
                  </div>
                ))}
              </div>
            </section>
          )}

          {/* ── Survival Rates ─────────────── */}
          {data.analysis?.survival_rates && (
            <section className="chart-section">
              <h2>🏆 Survival Rates</h2>
              <Plot
                data={[{
                  x: Object.keys(data.analysis.survival_rates).map(k => `Region ${k}`),
                  y: Object.values(data.analysis.survival_rates).map(v => v * 100),
                  type: 'bar',
                  marker: {
                    color: Object.values(data.analysis.survival_rates).map(v =>
                      v > 0.8 ? '#22c55e' : v > 0.5 ? '#f59e0b' : '#ef4444'
                    ),
                  },
                  text: Object.values(data.analysis.survival_rates).map(v => `${(v * 100).toFixed(1)}%`),
                  textposition: 'auto',
                }]}
                layout={{
                  paper_bgcolor: 'rgba(0,0,0,0)', plot_bgcolor: 'rgba(0,0,0,0)',
                  font: { color: '#e2e8f0' }, margin: { t: 20, b: 60, l: 50, r: 10 },
                  height: 250,
                  yaxis: { title: '%', range: [0, 105], gridcolor: '#334155' },
                  xaxis: { gridcolor: '#334155' },
                }}
                config={{ responsive: true }} style={{ width: '100%' }}
              />
            </section>
          )}
        </>
      )}

      {/* ── Footer ──────────────────────────── */}
      <footer className="footer">
        <p>Agent Earth · Adaptive Multi-Agent Resource Scarcity Simulator</p>
      </footer>
    </div>
  )
}

export default App
