import { useState, useEffect } from 'react'
import { RadialBarChart, RadialBar, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts'
import { getRiskAnalysis, getProducts } from '../services/api'
import { RiskBadge, LoadingState, ErrorState, formatNumber } from '../components/UI'
import { RefreshCw } from 'lucide-react'

const RISK_COLORS = { Critical: '#dc2626', High: '#ea580c', Medium: '#ca8a04', Low: '#16a34a' }

function RiskGauge({ label, score, level }) {
  const color = RISK_COLORS[level] || '#94a3b8'
  const pct = Math.min(100, (score / 10) * 100)
  return (
    <div className="card" style={{ textAlign: 'center', padding: 20 }}>
      <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 12, color: 'var(--color-text-secondary)' }}>{label}</div>
      <div style={{
        width: 72, height: 72, borderRadius: '50%',
        border: `5px solid ${color}`,
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        margin: '0 auto 12px',
        background: `${color}18`,
      }}>
        <span style={{ fontWeight: 800, fontSize: 22, color }}>{score}</span>
      </div>
      <RiskBadge level={level} />
      <div style={{ marginTop: 8 }}>
        <div className="progress-bar-wrap">
          <div className="progress-bar-fill" style={{ width: `${pct}%`, background: color }} />
        </div>
      </div>
    </div>
  )
}

export default function RiskAnalysis() {
  const [riskData, setRiskData] = useState(null)
  const [products, setProducts] = useState([])
  const [selectedProduct, setSelectedProduct] = useState('')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  const load = (pid = null) => {
    setLoading(true)
    setError(null)
    getRiskAnalysis(pid)
      .then(setRiskData)
      .catch(e => setError(e.message))
      .finally(() => setLoading(false))
  }

  useEffect(() => {
    getProducts().then(setProducts).catch(() => {})
    load()
  }, [])

  if (loading) return <LoadingState message="Analyzing supply chain risks..." />
  if (error) return <ErrorState message={error} onRetry={() => load(selectedProduct || null)} />
  if (!riskData) return null

  const atRiskProducts = riskData.at_risk_products || []
  const demandVolatility = riskData.demand_volatility || []
  const supplierRisks = riskData.supplier_risks || []

  const riskScoreData = [
    { category: 'Inventory', score: riskData.inventory_risk_score },
    { category: 'Supplier', score: riskData.supplier_risk_score },
    { category: 'Demand', score: riskData.demand_risk_score },
    { category: 'Logistics', score: riskData.logistics_risk_score },
  ]

  return (
    <div>
      <div className="page-header">
        <h1 className="page-title">Risk Analysis</h1>
        <p className="page-description">
          Comprehensive supply chain risk assessment — inventory shortages, supplier reliability, demand volatility, and logistics disruptions.
        </p>
      </div>

      {/* Filters */}
      <div className="filter-bar">
        <select
          value={selectedProduct}
          onChange={e => {
            setSelectedProduct(e.target.value)
            load(e.target.value || null)
          }}
          style={{ minWidth: 200 }}
        >
          <option value="">All Products (System-wide)</option>
          {products.map(p => (
            <option key={p.product_id} value={p.product_id}>{p.product_id} — {p.product_name}</option>
          ))}
        </select>
        <button className="btn btn-secondary btn-sm" onClick={() => load(selectedProduct || null)}>
          <RefreshCw size={13} /> Refresh
        </button>
        <div style={{ marginLeft: 'auto', display: 'flex', alignItems: 'center', gap: 8 }}>
          <span style={{ fontSize: 12, color: 'var(--color-text-muted)' }}>Overall Risk:</span>
          <span style={{
            fontWeight: 700, fontSize: 15,
            color: RISK_COLORS[riskData.overall_risk] || 'var(--color-text)'
          }}>
            {riskData.overall_risk}
          </span>
          <span style={{ fontSize: 12, color: 'var(--color-text-muted)' }}>
            (score: {riskData.overall_risk_score}/10)
          </span>
        </div>
      </div>

      {/* Risk Gauges */}
      <div className="grid-4 mb-6">
        <RiskGauge label="Inventory Risk" score={riskData.inventory_risk_score} level={riskData.inventory_risk} />
        <RiskGauge label="Supplier Risk" score={riskData.supplier_risk_score} level={riskData.supplier_risk} />
        <RiskGauge label="Demand Risk" score={riskData.demand_risk_score} level={riskData.demand_risk} />
        <RiskGauge label="Logistics Risk" score={riskData.logistics_risk_score} level={riskData.logistics_risk} />
      </div>

      {/* Risk score bar chart */}
      <div className="card mb-6">
        <div className="card-header">
          <div className="card-title">Risk Score by Category (0 = No Risk, 10 = Critical)</div>
        </div>
        <div style={{ height: 200 }}>
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={riskScoreData} margin={{ top: 4, right: 12, left: 0, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
              <XAxis dataKey="category" tick={{ fontSize: 12, fill: '#475569' }} />
              <YAxis domain={[0, 10]} tick={{ fontSize: 11, fill: '#94a3b8' }} />
              <Tooltip formatter={(v) => [v.toFixed(1), 'Risk Score']} />
              <Bar dataKey="score" radius={[4, 4, 0, 0]}
                fill="#1e40af"
                label={{ position: 'top', fontSize: 11, fill: '#475569' }}
              />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      <div className="grid-2 mb-6">
        {/* At-Risk Products */}
        <div className="card">
          <div className="card-header">
            <div className="card-title">At-Risk Products</div>
            <div className="card-subtitle">{atRiskProducts.length} inventory issues detected</div>
          </div>
          {atRiskProducts.length === 0 ? (
            <div style={{ color: 'var(--color-low)', fontSize: 13, fontWeight: 500 }}>
              No inventory risk issues detected.
            </div>
          ) : (
            <div className="table-container">
              <table>
                <thead>
                  <tr>
                    <th>Product</th>
                    <th>Warehouse</th>
                    <th>Issue</th>
                    <th>Stock</th>
                    <th>Severity</th>
                  </tr>
                </thead>
                <tbody>
                  {atRiskProducts.map((p, i) => (
                    <tr key={i}>
                      <td style={{ fontWeight: 600 }}>{p.product_id}</td>
                      <td>{p.warehouse_id}</td>
                      <td style={{ fontSize: 12 }}>{p.issue}</td>
                      <td>{formatNumber(p.current_stock)}</td>
                      <td><RiskBadge level={p.severity} /></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>

        {/* Demand Volatility */}
        <div className="card">
          <div className="card-header">
            <div className="card-title">Demand Volatility</div>
            <div className="card-subtitle">Products with &gt;30% demand change (last 30d vs previous 30d)</div>
          </div>
          {demandVolatility.length === 0 ? (
            <div style={{ color: 'var(--color-low)', fontSize: 13, fontWeight: 500 }}>
              Demand volatility is within normal range.
            </div>
          ) : (
            <div className="table-container">
              <table>
                <thead>
                  <tr>
                    <th>Product</th>
                    <th>Recent</th>
                    <th>Previous</th>
                    <th>Change</th>
                    <th>Direction</th>
                  </tr>
                </thead>
                <tbody>
                  {demandVolatility.map((d, i) => (
                    <tr key={i}>
                      <td style={{ fontWeight: 600 }}>{d.product_id}</td>
                      <td>{formatNumber(d.recent_qty)}</td>
                      <td>{formatNumber(d.prev_qty)}</td>
                      <td style={{ fontWeight: 700, color: 'var(--color-high)' }}>
                        {formatNumber(d.change_percent, 1)}%
                      </td>
                      <td>
                        <span className={`badge ${d.direction === 'Increasing' ? 'badge-info' : 'badge-high'}`}>
                          {d.direction}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>

      {/* Supplier Risks */}
      {supplierRisks.length > 0 && (
        <div className="card">
          <div className="card-header">
            <div className="card-title">Supplier Risk Alerts</div>
            <div className="card-subtitle">{supplierRisks.length} supplier issues detected</div>
          </div>
          {supplierRisks.map((s, i) => (
            <div key={i} style={{
              padding: '10px 0', borderBottom: i < supplierRisks.length - 1 ? '1px solid var(--color-border-light)' : 'none',
              display: 'flex', justifyContent: 'space-between', alignItems: 'center'
            }}>
              <div>
                <span style={{ fontWeight: 600 }}>{s.supplier_name}</span>
                <span style={{ color: 'var(--color-text-muted)', fontSize: 12, marginLeft: 8 }}>{s.supplier_id}</span>
                <div style={{ fontSize: 12, color: 'var(--color-text-secondary)', marginTop: 2 }}>{s.issue}</div>
              </div>
              <RiskBadge level={s.severity} />
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
