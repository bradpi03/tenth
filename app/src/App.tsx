import { useMemo, useState } from 'react'
import './App.css'
import dataset from './data/tenth-data.json'

type TabKey = 'Overview' | 'Signals' | 'Performance' | 'Research' | 'System Status'

const tabs: TabKey[] = ['Overview', 'Signals', 'Performance', 'Research', 'System Status']

const currency = new Intl.NumberFormat('en-GB', {
  style: 'currency',
  currency: 'GBP',
  maximumFractionDigits: 2,
})

const percent = (value: number, digits = 2) => `${(value * 100).toFixed(digits)}%`
const signedPercent = (value: number, digits = 2) => `${value >= 0 ? '+' : ''}${(value * 100).toFixed(digits)}%`

function App() {
  const [activeTab, setActiveTab] = useState<TabKey>('Overview')
  const [chartHover, setChartHover] = useState({
    visible: false,
    x: 0,
    y: 0,
    date: '',
    tenth: '',
    spy: '',
  })

  const overview = (dataset as any).overview
  const annualReturns = (dataset as any).annualReturns as Array<any>
  const signals = (dataset as any).signals as Array<any>
  const research = (dataset as any).research
  const systemStatus = (dataset as any).systemStatus
  const equityCurve = (dataset as any).equityCurve as Array<any>

  const signalSummary = useMemo(() => {
    const totals = { FULL: 0, PARTIAL: 0, CASH: 0 }
    signals.forEach((signal) => {
      totals[signal.state as keyof typeof totals] += 1
    })
    const representative = signals.slice(0, 6).map((signal) => ({
      ticker: signal.ticker,
      state: signal.state,
    }))

    return { totals, representative }
  }, [signals])

  const chart = useMemo(() => {
    const values = equityCurve.map((point) => Number(point.tenthValue))
    const spyValues = equityCurve.map((point) => Number(point.spyValue))
    const minValue = Math.min(...values, ...spyValues)
    const maxValue = Math.max(...values, ...spyValues)
    const width = 760
    const height = 220
    const left = 28
    const right = 20
    const top = 16
    const bottom = 26

    const toPoints = (series: number[]) =>
      series.map((value, index) => {
        const x = left + (index / Math.max(series.length - 1, 1)) * (width - left - right)
        const y = height - bottom - ((value - minValue) / Math.max(maxValue - minValue, 1e-9)) * (height - top - bottom)
        return { x, y }
      })

    const tenthPoints = toPoints(values)
    const spyPoints = toPoints(spyValues)

    const toPath = (points: { x: number; y: number }[]) =>
      points
        .map((point, index) => `${index === 0 ? 'M' : 'L'} ${point.x} ${point.y}`)
        .join(' ')

    return {
      tenthPath: toPath(tenthPoints),
      spyPath: toPath(spyPoints),
      width,
      height,
      left,
      right,
      top,
      bottom,
      series: equityCurve.map((point, index) => ({
        date: point.date,
        x: left + (index / Math.max(equityCurve.length - 1, 1)) * (width - left - right),
        tenth: Number(point.tenthValue),
        spy: Number(point.spyValue),
      })),
    }
  }, [equityCurve])

  const primaryMetrics = [
    { label: 'Portfolio Value', value: currency.format(overview.endingPortfolioValue) },
    { label: 'Annualised Return', value: signedPercent(overview.annualisedReturn) },
    { label: 'Max Drawdown', value: percent(overview.maxDrawdown) },
    { label: 'Sharpe', value: overview.sharpe.toFixed(2) },
  ]

  const secondaryMetrics = [
    { label: 'Total Return', value: signedPercent(overview.totalReturn) },
    { label: 'Avg Market Exposure', value: percent(overview.averageMarketExposure / 100) },
    { label: 'Avg Cash Allocation', value: percent(overview.averageCashAllocation / 100) },
    { label: 'Transaction Costs', value: currency.format(overview.transactionCosts) },
  ]

  const tertiaryMetrics = [
    { label: 'Rebalance Count', value: overview.rebalanceCount.toLocaleString() },
    { label: 'Benchmark', value: 'SPY' },
  ]

  const lastSimulationDate = equityCurve[equityCurve.length - 1]?.date ?? 'N/A'

  const handleChartMove = (event: React.MouseEvent<SVGSVGElement>) => {
    const bounds = event.currentTarget.getBoundingClientRect()
    const relativeX = Math.min(Math.max((event.clientX - bounds.left) / bounds.width, 0), 1)
    const index = Math.min(
      Math.max(Math.round(relativeX * (equityCurve.length - 1)), 0),
      equityCurve.length - 1,
    )

    const point = equityCurve[index]
    const x = 28 + (index / Math.max(equityCurve.length - 1, 1)) * (chart.width - 48)
    const y = chart.height - 26 - ((Number(point.tenthValue) - Math.min(...equityCurve.map((item) => Number(item.tenthValue)), ...equityCurve.map((item) => Number(item.spyValue)))) / Math.max(Math.max(...equityCurve.map((item) => Number(item.tenthValue)), ...equityCurve.map((item) => Number(item.spyValue))) - Math.min(...equityCurve.map((item) => Number(item.tenthValue)), ...equityCurve.map((item) => Number(item.spyValue))), 1e-9)) * 170

    setChartHover({
      visible: true,
      x: x,
      y: y,
      date: point.date,
      tenth: currency.format(Number(point.tenthValue)),
      spy: currency.format(Number(point.spyValue)),
    })
  }

  return (
    <div className="app-shell">
      <header className="topbar">
        <div className="brand-block">
          <p className="eyebrow">HISTORICAL SIMULATION</p>
          <h1>TENTH</h1>
        </div>
        <div className="header-meta">
          <div className="status-badge" aria-live="polite">
            <span className="status-dot" aria-hidden="true" />
            {systemStatus.currentMode}
          </div>
          <p className="header-subtitle">B009 frozen strategy • V1 baseline • Not live</p>
        </div>
      </header>

      <nav className="tabbar" aria-label="Tenth sections">
        {tabs.map((tab) => (
          <button
            key={tab}
            type="button"
            className={tab === activeTab ? 'tab active' : 'tab'}
            onClick={() => setActiveTab(tab)}
          >
            {tab}
          </button>
        ))}
      </nav>

      {activeTab === 'Overview' && (
        <>
          <section className="kpi-section" aria-label="Portfolio performance summary">
            <div className="kpi-grid primary-grid">
              {primaryMetrics.map((card) => (
                <article className="kpi-card primary" key={card.label}>
                  <span>{card.label}</span>
                  <strong>{card.value}</strong>
                </article>
              ))}
            </div>

            <div className="kpi-grid secondary-grid">
              {secondaryMetrics.map((card) => (
                <article className="kpi-card secondary" key={card.label}>
                  <span>{card.label}</span>
                  <strong>{card.value}</strong>
                </article>
              ))}
            </div>

            <div className="kpi-grid tertiary-grid">
              {tertiaryMetrics.map((card) => (
                <article className="kpi-card tertiary" key={card.label}>
                  <span>{card.label}</span>
                  <strong>{card.value}</strong>
                </article>
              ))}
            </div>
          </section>

          <section className="panel chart-panel">
            <div className="panel-header">
              <div>
                <p className="section-tag">Equity curve</p>
                <h2>TENTH vs SPY benchmark</h2>
              </div>
              <div className="legend" aria-label="Chart legend">
                <span><i className="swatch tenth" /> TENTH</span>
                <span><i className="swatch spy" /> SPY</span>
              </div>
            </div>

            <div className="chart-container">
              <svg
                viewBox={`0 0 ${chart.width} ${chart.height}`}
                className="chart"
                role="img"
                aria-label="Tenth equity curve and SPY benchmark over the historical simulation period"
                onMouseMove={handleChartMove}
                onMouseLeave={() => setChartHover((current) => ({ ...current, visible: false }))}
              >
                <g>
                  {[0, 0.25, 0.5, 0.75, 1].map((step) => {
                    const x = chart.left + step * (chart.width - chart.left - chart.right)
                    return (
                      <line
                        key={`grid-${step}`}
                        x1={x}
                        y1={chart.top}
                        x2={x}
                        y2={chart.height - chart.bottom}
                        className="grid-line"
                        opacity={step === 0 || step === 1 ? 0.3 : 0.15}
                      />
                    )
                  })}
                </g>
                <path d={chart.tenthPath} className="line tenth-line" />
                <path d={chart.spyPath} className="line spy-line" />
                {chartHover.visible && (
                  <g>
                    <line x1={chartHover.x} y1={chart.top} x2={chartHover.x} y2={chart.height - chart.bottom} className="hover-line" />
                    <circle cx={chartHover.x} cy={chartHover.y} r={4} className="hover-dot" />
                  </g>
                )}
                <line x1={chart.left} y1={chart.height - chart.bottom} x2={chart.width - chart.right} y2={chart.height - chart.bottom} className="axis-line" />
                <line x1={chart.left} y1={chart.top} x2={chart.left} y2={chart.height - chart.bottom} className="axis-line" />
              </svg>

              {chartHover.visible && (
                <div
                  className="chart-tooltip"
                  style={{ left: `${Math.min(chartHover.x + 12, 640)}px`, top: `${Math.max(chartHover.y - 28, 18)}px` }}
                >
                  <strong>{chartHover.date}</strong>
                  <span>TENTH: {chartHover.tenth}</span>
                  <span>SPY: {chartHover.spy}</span>
                </div>
              )}
            </div>
          </section>

          <section className="panel signal-summary-panel">
            <div className="panel-header">
              <div>
                <p className="section-tag">Current signals</p>
                <h2>HISTORICAL SIMULATION SIGNALS</h2>
              </div>
            </div>
            <div className="signal-summary-grid">
              <article className="summary-stat full">
                <span>FULL</span>
                <strong>{signalSummary.totals.FULL}</strong>
              </article>
              <article className="summary-stat partial">
                <span>PARTIAL</span>
                <strong>{signalSummary.totals.PARTIAL}</strong>
              </article>
              <article className="summary-stat cash">
                <span>CASH</span>
                <strong>{signalSummary.totals.CASH}</strong>
              </article>
            </div>
            <p className="callout-block">NOT LIVE TRADING SIGNALS</p>
            <ul className="signal-mini-list">
              {signalSummary.representative.map((signal) => (
                <li key={signal.ticker}>
                  <span>{signal.ticker}</span>
                  <span className={`state-pill ${signal.state.toLowerCase()}`}>{signal.state}</span>
                </li>
              ))}
            </ul>
          </section>
        </>
      )}

      {activeTab === 'Signals' && (
        <section className="panel">
          <div className="panel-header">
            <div>
              <p className="section-tag">Signals</p>
              <h2>HISTORICAL SIMULATION SIGNALS</h2>
            </div>
          </div>
          <p className="callout-block muted">NOT LIVE TRADING SIGNALS</p>
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Ticker</th>
                  <th>B009 state</th>
                  <th>Target weight</th>
                  <th>Approx. allocation</th>
                </tr>
              </thead>
              <tbody>
                {signals.map((signal) => (
                  <tr key={signal.ticker}>
                    <td>{signal.ticker}</td>
                    <td><span className={`state-pill ${signal.state.toLowerCase()}`}>{signal.state}</span></td>
                    <td>{(signal.targetWeight * 100).toFixed(2)}%</td>
                    <td>{currency.format(signal.approximateAllocation)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      )}

      {activeTab === 'Performance' && (
        <section className="panel performance-panel">
          <div className="panel-header">
            <div>
              <p className="section-tag">Historical performance</p>
              <h2>TENTH vs SPY comparison</h2>
            </div>
          </div>

          <div className="kpi-grid metric-grid">
            <article className="kpi-card tertiary">
              <span>Annualised Return</span>
              <strong>{signedPercent(overview.annualisedReturn)}</strong>
            </article>
            <article className="kpi-card tertiary">
              <span>Sharpe</span>
              <strong>{overview.sharpe.toFixed(2)}</strong>
            </article>
            <article className="kpi-card tertiary">
              <span>Max Drawdown</span>
              <strong>{percent(overview.maxDrawdown)}</strong>
            </article>
            <article className="kpi-card tertiary">
              <span>Transaction Costs</span>
              <strong>{currency.format(overview.transactionCosts)}</strong>
            </article>
          </div>

          <div className="chart-wrap">
            <div className="chart-container">
              <svg
                viewBox={`0 0 ${chart.width} ${chart.height}`}
                className="chart performance-chart"
                role="img"
                aria-label="Historical Tenth and SPY equity curves"
              >
                <path d={chart.tenthPath} className="line tenth-line" />
                <path d={chart.spyPath} className="line spy-line" />
              </svg>
            </div>
          </div>

          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Year</th>
                  <th>TENTH</th>
                  <th>SPY</th>
                  <th>Max drawdown</th>
                  <th>Exposure</th>
                  <th>End value</th>
                </tr>
              </thead>
              <tbody>
                {annualReturns.map((row) => (
                  <tr key={row.year}>
                    <td>{row.year}</td>
                    <td>{signedPercent(row.tenthReturn)}</td>
                    <td>{signedPercent(row.spyReturn)}</td>
                    <td>{percent(row.tenthMaxDrawdown)}</td>
                    <td>{percent(row.avgExposure / 100)}</td>
                    <td>{currency.format(row.endValue)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      )}

      {activeTab === 'Research' && (
        <section className="panel research-panel">
          <div className="panel-header">
            <div>
              <p className="section-tag">Research</p>
              <h2>Frozen logic, accepted baseline, and failed experiment</h2>
            </div>
          </div>

          <div className="research-body">
            <div className="research-card">
              <h3>Frozen strategy</h3>
              <p>{research.strategy}</p>
            </div>

            <div className="research-card">
              <h3>Accepted baseline</h3>
              <p>Portfolio Engine V1 remains the accepted baseline for the historical simulation product.</p>
            </div>

            <div className="research-card warning-card">
              <h3>Experimental work</h3>
              <p>Portfolio Engine V2 remains an experimental variant and <strong>EXPERIMENT RESULT: FAILURE</strong>.</p>
            </div>

            <ul className="research-list">
              <li>Survivorship bias remains in the fixed 28-asset research universe.</li>
              <li>Selection bias is present because the universe is not a broad, live market representation.</li>
              <li>FX is ignored in the accepted V1 engine.</li>
              <li>Historical simulation only. This is not a live or paper trading implementation.</li>
              <li>No demonstrated alpha is claimed; this is not a claim of future performance.</li>
              <li>All outputs are evidence-based historical results only.</li>
            </ul>
          </div>
        </section>
      )}

      {activeTab === 'System Status' && (
        <section className="status-panel-wrap">
          <div className="status-box active">
            <span>Simulation</span>
            <strong>{systemStatus.simulation}</strong>
          </div>
          <div className="status-box inactive">
            <span>Paper</span>
            <strong>{systemStatus.paper}</strong>
          </div>
          <div className="status-box inactive">
            <span>Live</span>
            <strong>{systemStatus.live}</strong>
          </div>

          <div className="panel status-message">
            <div className="status-list-wrap">
              <div className="status-item"><span>Strategy</span><strong>B009</strong></div>
              <div className="status-item"><span>Portfolio Engine</span><strong>V1</strong></div>
              <div className="status-item"><span>Transaction Cost</span><strong>0.10%</strong></div>
              <div className="status-item"><span>FX</span><strong>IGNORED</strong></div>
              <div className="status-item"><span>Leverage</span><strong>OFF</strong></div>
              <div className="status-item"><span>Shorting</span><strong>OFF</strong></div>
              <div className="status-item"><span>Asset Universe</span><strong>28</strong></div>
              <div className="status-item"><span>Execution</span><strong>HISTORICAL SIMULATION</strong></div>
              <div className="status-item"><span>Last Simulation Date</span><strong>{lastSimulationDate}</strong></div>
            </div>

            <ul className="status-message-list">
              <li>Historical simulation only.</li>
              <li>No broker integration.</li>
              <li>No order routing.</li>
              <li>No paper-trading mode active.</li>
            </ul>
          </div>
        </section>
      )}
    </div>
  )
}

export default App
