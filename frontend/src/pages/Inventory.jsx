import { useState, useEffect } from 'react'
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts'
import { getInventory } from '../services/api'
import { RiskBadge, LoadingState, ErrorState, formatNumber, formatCurrency } from '../components/UI'
import { Search } from 'lucide-react'

export default function Inventory() {
  const [inventory, setInventory] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [search, setSearch] = useState('')
  const [riskFilter, setRiskFilter] = useState('All')

  const load = () => {
    setLoading(true)
    setError(null)
    getInventory()
      .then(setInventory)
      .catch(e => setError(e.message))
      .finally(() => setLoading(false))
  }

  useEffect(() => { load() }, [])

  const filtered = inventory.filter(item => {
    const matchSearch = !search || 
      item.product_id.toLowerCase().includes(search.toLowerCase()) ||
      item.product_name.toLowerCase().includes(search.toLowerCase())
    const matchRisk = riskFilter === 'All' || item.risk_level === riskFilter
    return matchSearch && matchRisk
  })

  const chartData = filtered.slice(0, 10).map(item => ({
    product: item.product_id,
    stock: item.total_stock,
    safety: item.safety_stock,
    reorder: item.reorder_point,
  }))

  if (loading) return <LoadingState message="Loading inventory..." />
  if (error) return <ErrorState message={error} onRetry={load} />

  return (
    <div>
      <div className="page-header">
        <h1 className="page-title">Inventory Management</h1>
        <p className="page-description">
          Stock levels, safety stock and reorder points calculated from historical demand data.
        </p>
      </div>

      {/* Summary cards */}
      <div className="kpi-grid mb-6">
        {['Critical', 'High', 'Medium', 'Low'].map(level => {
          const count = inventory.filter(i => i.risk_level === level).length
          const colors = { Critical: '#dc2626', High: '#ea580c', Medium: '#ca8a04', Low: '#16a34a' }
          return (
            <div key={level} className="kpi-card">
              <div className="kpi-label" style={{ color: colors[level] }}>{level} Risk</div>
              <div className="kpi-value" style={{ color: colors[level] }}>{count}</div>
              <div style={{ fontSize: 11, color: 'var(--color-text-muted)' }}>products</div>
            </div>
          )
        })}
      </div>

      {/* Chart */}
      <div className="card mb-6">
        <div className="card-header">
          <div className="card-title">Stock vs Reorder Points (Top 10 Products)</div>
        </div>
        <div className="chart-container">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={chartData} margin={{ top: 4, right: 12, left: 0, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
              <XAxis dataKey="product" tick={{ fontSize: 11, fill: '#94a3b8' }} />
              <YAxis tick={{ fontSize: 11, fill: '#94a3b8' }} />
              <Tooltip />
              <Bar dataKey="stock" name="Current Stock" fill="#1e40af" radius={[3, 3, 0, 0]} />
              <Bar dataKey="safety" name="Safety Stock" fill="#94a3b8" radius={[3, 3, 0, 0]} />
              <Bar dataKey="reorder" name="Reorder Point" fill="#ea580c" radius={[3, 3, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Filters */}
      <div className="filter-bar">
        <div style={{ position: 'relative' }}>
          <Search size={14} style={{ position: 'absolute', left: 10, top: '50%', transform: 'translateY(-50%)', color: 'var(--color-text-muted)' }} />
          <input
            type="text"
            placeholder="Search products..."
            value={search}
            onChange={e => setSearch(e.target.value)}
            style={{ paddingLeft: 32, width: 220 }}
          />
        </div>
        <select value={riskFilter} onChange={e => setRiskFilter(e.target.value)} style={{ width: 160 }}>
          <option value="All">All Risk Levels</option>
          <option value="Critical">Critical</option>
          <option value="High">High</option>
          <option value="Medium">Medium</option>
          <option value="Low">Low</option>
        </select>
        <span style={{ marginLeft: 'auto', fontSize: 12, color: 'var(--color-text-muted)' }}>
          {filtered.length} products
        </span>
      </div>

      {/* Table */}
      <div className="card" style={{ padding: 0 }}>
        <div className="table-container">
          <table>
            <thead>
              <tr>
                <th>Product</th>
                <th>Current Stock</th>
                <th>Safety Stock</th>
                <th>Reorder Point</th>
                <th>30-Day Forecast</th>
                <th>Shortage</th>
                <th>Rec. Order Qty</th>
                <th>Risk Level</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map(item => (
                <tr key={item.product_id}>
                  <td>
                    <div style={{ fontWeight: 600 }}>{item.product_id}</div>
                    <div style={{ fontSize: 11.5, color: 'var(--color-text-muted)' }}>{item.product_name}</div>
                  </td>
                  <td>
                    <span style={{
                      fontWeight: 600,
                      color: item.current_stock <= item.safety_stock ? 'var(--color-critical)' : 'var(--color-text)'
                    }}>
                      {formatNumber(item.total_stock)}
                    </span>
                  </td>
                  <td>{formatNumber(item.safety_stock)}</td>
                  <td>{formatNumber(item.reorder_point)}</td>
                  <td>{formatNumber(item.forecast_30_day, 0)}</td>
                  <td>
                    {item.shortage > 0 ? (
                      <span style={{ color: 'var(--color-critical)', fontWeight: 600 }}>
                        -{formatNumber(item.shortage, 0)}
                      </span>
                    ) : (
                      <span style={{ color: 'var(--color-low)' }}>Sufficient</span>
                    )}
                  </td>
                  <td>
                    {item.recommended_order_quantity > 0 ? (
                      <span style={{ fontWeight: 600, color: 'var(--color-primary)' }}>
                        {formatNumber(item.recommended_order_quantity)}
                      </span>
                    ) : '--'}
                  </td>
                  <td><RiskBadge level={item.risk_level} /></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}
