import { useState, useEffect } from 'react'
import { RadarChart, Radar, PolarGrid, PolarAngleAxis, ResponsiveContainer, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip } from 'recharts'
import { getSuppliers, getProducts, compareSuppliers } from '../services/api'
import { RiskBadge, LoadingState, ErrorState, formatNumber } from '../components/UI'

export default function Suppliers() {
  const [suppliers, setSuppliers] = useState([])
  const [products, setProducts] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [compareProduct, setCompareProduct] = useState('')
  const [comparison, setComparison] = useState(null)
  const [compareLoading, setCompareLoading] = useState(false)

  useEffect(() => {
    Promise.all([getSuppliers(), getProducts()])
      .then(([sups, prods]) => {
        setSuppliers(sups)
        setProducts(prods)
        if (prods.length) setCompareProduct(prods[0].product_id)
      })
      .catch(e => setError(e.message))
      .finally(() => setLoading(false))
  }, [])

  const runComparison = () => {
    if (!compareProduct) return
    setCompareLoading(true)
    compareSuppliers(compareProduct)
      .then(setComparison)
      .catch(e => setError(e.message))
      .finally(() => setCompareLoading(false))
  }

  if (loading) return <LoadingState message="Loading suppliers..." />
  if (error) return <ErrorState message={error} />

  const chartData = suppliers.map(s => ({
    supplier: s.supplier_name?.split(' ')[0] || s.supplier_id,
    reliability: s.reliability,
    quality: s.quality_score,
    fulfillment: s.order_fulfillment_rate,
  }))

  return (
    <div>
      <div className="page-header">
        <h1 className="page-title">Supplier Management</h1>
        <p className="page-description">
          Supplier scoring uses a composite model: reliability, quality, lead time, cost, and fulfillment rate.
        </p>
      </div>

      {/* Bar chart: supplier performance */}
      <div className="card mb-6">
        <div className="card-header">
          <div className="card-title">Supplier Performance Comparison</div>
          <div className="card-subtitle">Reliability, quality, and fulfillment rate (%)</div>
        </div>
        <div className="chart-container">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={chartData} margin={{ top: 4, right: 12, left: 0, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
              <XAxis dataKey="supplier" tick={{ fontSize: 11, fill: '#94a3b8' }} />
              <YAxis domain={[0, 100]} tick={{ fontSize: 11, fill: '#94a3b8' }} />
              <Tooltip />
              <Bar dataKey="reliability" name="Reliability" fill="#1e40af" radius={[3, 3, 0, 0]} />
              <Bar dataKey="quality" name="Quality Score" fill="#0891b2" radius={[3, 3, 0, 0]} />
              <Bar dataKey="fulfillment" name="Fulfillment Rate" fill="#16a34a" radius={[3, 3, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Supplier table */}
      <div className="card mb-6" style={{ padding: 0 }}>
        <div style={{ padding: '16px 20px 0' }}>
          <div className="card-title">All Suppliers</div>
        </div>
        <div className="table-container" style={{ border: 'none' }}>
          <table>
            <thead>
              <tr>
                <th>Supplier</th>
                <th>Country</th>
                <th>Reliability</th>
                <th>Quality Score</th>
                <th>Lead Time</th>
                <th>Capacity</th>
                <th>Fulfillment Rate</th>
                <th>Delays</th>
                <th>Risk Level</th>
              </tr>
            </thead>
            <tbody>
              {suppliers.map(s => (
                <tr key={s.supplier_id}>
                  <td>
                    <div style={{ fontWeight: 600 }}>{s.supplier_name}</div>
                    <div style={{ fontSize: 11.5, color: 'var(--color-text-muted)' }}>{s.supplier_id}</div>
                  </td>
                  <td>{s.country}</td>
                  <td>
                    <div>{s.reliability}%</div>
                    <div className="progress-bar-wrap" style={{ marginTop: 4, width: 64 }}>
                      <div className="progress-bar-fill" style={{ width: `${s.reliability}%`, background: s.reliability >= 85 ? '#16a34a' : '#ea580c' }} />
                    </div>
                  </td>
                  <td>{s.quality_score}/100</td>
                  <td>{s.lead_time_days} days</td>
                  <td>{formatNumber(s.capacity)}</td>
                  <td>{s.order_fulfillment_rate}%</td>
                  <td style={{ color: s.historical_delays > 5 ? 'var(--color-critical)' : 'inherit' }}>
                    {s.historical_delays}
                  </td>
                  <td><RiskBadge level={s.risk_level} /></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Supplier Comparison Tool */}
      <div className="card">
        <div className="card-header">
          <div>
            <div className="card-title">Supplier Comparison Tool</div>
            <div className="card-subtitle">Compare suppliers for a specific product using composite scoring</div>
          </div>
        </div>
        <div className="filter-bar" style={{ marginBottom: 16 }}>
          <select value={compareProduct} onChange={e => setCompareProduct(e.target.value)} style={{ minWidth: 200 }}>
            {products.map(p => (
              <option key={p.product_id} value={p.product_id}>{p.product_id} — {p.product_name}</option>
            ))}
          </select>
          <button className="btn btn-primary" onClick={runComparison} disabled={compareLoading}>
            {compareLoading ? 'Analyzing...' : 'Compare Suppliers'}
          </button>
        </div>

        {comparison && (
          <div>
            <div style={{ marginBottom: 12, padding: '10px 14px', background: 'var(--color-low-bg)', border: '1px solid var(--color-low-border)', borderRadius: 8 }}>
              <div style={{ fontWeight: 600, color: 'var(--color-low)', fontSize: 13 }}>
                Recommended Supplier: {comparison.recommended_supplier?.supplier_name}
              </div>
              <div style={{ fontSize: 12, color: 'var(--color-text-secondary)', marginTop: 2 }}>
                Composite Score: {comparison.recommended_supplier?.composite_score}/100 |
                Lead Time: {comparison.recommended_supplier?.lead_time_days} days |
                Risk: {comparison.recommended_supplier?.risk_level}
              </div>
            </div>

            <div className="table-container">
              <table>
                <thead>
                  <tr>
                    <th>Rank</th>
                    <th>Supplier</th>
                    <th>Score</th>
                    <th>Unit Cost</th>
                    <th>Lead Time</th>
                    <th>Reliability</th>
                    <th>Quality</th>
                    <th>Fulfillment</th>
                    <th>Risk</th>
                  </tr>
                </thead>
                <tbody>
                  {comparison.suppliers.map((s, i) => (
                    <tr key={s.supplier_id} style={{ background: i === 0 ? 'var(--color-low-bg)' : 'inherit' }}>
                      <td style={{ fontWeight: 700, color: i === 0 ? 'var(--color-low)' : 'var(--color-text-muted)' }}>
                        #{i + 1}
                      </td>
                      <td>
                        <div style={{ fontWeight: 600 }}>{s.supplier_name}</div>
                        <div style={{ fontSize: 11, color: 'var(--color-text-muted)' }}>{s.country}</div>
                      </td>
                      <td style={{ fontWeight: 700 }}>{s.composite_score}</td>
                      <td>{s.unit_cost != null ? `INR ${s.unit_cost}` : '--'}</td>
                      <td>{s.lead_time_days}d</td>
                      <td>{s.reliability}%</td>
                      <td>{s.quality_score}</td>
                      <td>{s.order_fulfillment_rate}%</td>
                      <td><RiskBadge level={s.risk_level} /></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
