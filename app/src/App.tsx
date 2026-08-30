import { useMemo, useState } from 'react'
import './App.css'
import dataset from './data/tenth-data.json'

type TabKey = 'Overview' | 'Performance' | 'Research' | 'System Status'

const tabs: TabKey[] = ['Overview', 'Performance', 'Research', 'System Status']

const currency = new Intl.NumberFormat('en-GB', {
  style: 'currency',
  currency: 'GBP',
  maximumFractionDigits: 2,
})

const percent = (value: number, digits = 2) => `${(value * 100).toFixed(digits)}%`

function App() {
  const [activeTab, setActiveTab] = useState<TabKey>('Overview')

  const overview = (dataset as any).overview
  const annualReturns = (dataset as any).annualReturns as Array<any>
  const signals = (dataset as any).signals as Array<any>
  const research = (dataset as any).research
  const systemStatus = (dataset as any).systemStatus
  const equityCurve = (dataset as any).equityCurve as Array<any>

  const chart = useMemo(() => {
    const values = equityCurve.map((point) => Number(point.tenthValue))
    const spyValues = equityCurve.map((point) => Number(point.spyValue))
    const minValue = Math.min(...values, ...spyValues)
    const maxValue = Math.max(...values, ...spyValues)

    const toPath = (series: number[]) =>
      series
        .map((value, index) => {
          const x = (index / Math.max(series.length - 1, 1)) * 760
          const y = 200 - ((value - minValue) / Math.max(maxValue - minValue, 1e-9)) * 160
          return `${index === 0 ? 'M' : 'L'} ${x} ${y}`
        })
        .join(' ')

    return {
      tenthPath: toPath(values),
      spyPath: toPath(spyValues),
    }
  }, [equityCurve])

  const cards = [
    { label: 'Portfolio value', value: currency.format(overview.endingPortfolioValue) },
    { label: 'Total return', value: percent(overview.totalReturn) },
    { label: 'Annualised return', value: percent(overview.annualisedReturn) },
    { label: 'Sharpe ratio', value: overview.sharpe.toFixed(2) },
    { label: 'Max drawdown', value: percent(overview.maxDrawdown) },
    { label: 'Avg market exposure', value: percent(overview.averageMarketExposure / 100) },
    { label: 'Avg cash allocation', value: percent(overview.averageCashAllocation / 100) },
    { label: 'Transaction costs', value: currency.format(overview.transactionCosts) },
    { label: 'Rebalance count', value: overview.rebalanceCount.toLocaleString() },
  ]

  return (
    <div className="app-shell">
      <header className="topbar">
        <div>
          <p className="eyebrow">TENTH — SIMULATION VIEW</p>
          <h1>TENTH</h1>
        </div>
        <div className="status-badge">{systemStatus.currentMode}</div>
      </header>

      <nav className="tabbar" aria-label="Sections">
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
          <section className="kpi-grid">{cards.map((card) => (
            <article className="kpi-card" key={card.label}>
              <span>{card.label}</span>
              <strong>{card.value}</strong>
            </article>
          ))}</section>

          <section className="panel chart-panel">
            <div className="panel-header">
              <div>
                <p className="section-tag">Equity curve</p>
                <h2>Portfolio vs SPY benchmark</h2>
              </div>
              <div className="legend">
                <span><i className="swatch tenth" /> TENTH</span>
                <span><i className="swatch spy" /> SPY</span>
              </div>
            </div>
            <svg viewBox="0 0 780 220" className="chart" role="img" aria-label="Tenth equity curve and SPY benchmark">
              <path d={chart.tenthPath} className="line tenth-line" />
              <path d={chart.spyPath} className="line spy-line" />
            </svg>
          </section>

          <section className="panel">
            <div className="panel-header">
              <div>
                <p className="section-tag">Current signals</p>
                <h2>B009 states</h2>
              </div>
            </div>
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
        </>
      )}

      {activeTab === 'Performance' && (
        <section className="panel">
          <div className="panel-header">
            <div>
              <p className="section-tag">Historical results</p>
              <h2>Annual return table</h2>
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
                  <th>Avg exposure</th>
                  <th>End value</th>
                </tr>
              </thead>
              <tbody>
                {annualReturns.map((row) => (
                  <tr key={row.year}>
                    <td>{row.year}</td>
                    <td>{percent(row.tenthReturn)}</td>
                    <td>{percent(row.spyReturn)}</td>
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
              <h2>Frozen logic and evidence</h2>
            </div>
          </div>
          <div className="research-body">
            <p>{research.status}</p>
            <ul>
              {research.frozenComponents.map((item: string) => (
                <li key={item}>{item}</li>
              ))}
            </ul>
            <p className="note">This dashboard uses the accepted V1 portfolio output and does not alter the frozen research logic.</p>
          </div>
        </section>
      )}

      {activeTab === 'System Status' && (
        <section className="status-panel-wrap">
          <div className="status-box active">
            <span>SIMULATION</span>
            <strong>{systemStatus.simulation}</strong>
          </div>
          <div className="status-box inactive">
            <span>PAPER</span>
            <strong>{systemStatus.paper}</strong>
          </div>
          <div className="status-box inactive">
            <span>LIVE</span>
            <strong>{systemStatus.live}</strong>
          </div>
          <div className="panel status-message">
            <p>Only one mode is active: simulation. No live trading, brokerage connection, or order routing is enabled.</p>
            {overview.warnings.map((warning: string) => (
              <li key={warning}>{warning}</li>
            ))}
          </div>
        </section>
      )}
    </div>
  )
}

export default App
