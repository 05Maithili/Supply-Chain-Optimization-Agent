import { useState, useEffect } from 'react'
import {
  LineChart, Line, BarChart, Bar, PieChart, Pie, Cell,
  XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend
} from 'recharts'
import {
  Package, AlertTriangle, Users, Truck, TrendingUp, DollarSign
} from 'lucide-react'
import { getDashboardSummary } from '../services/api'
import { KpiCard, RiskBadge, LoadingState, ErrorState, formatCurrency, formatNumber } from '../components/UI'

const RISK_COLORS = {
  Critical: '#dc2626',
  High: '#ea580c',
  Medium: '#ca8a04',
  Low: '#16a34a',
}

export default function Dashboard() {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  const load = () => {
    setLoading(true)
    setError(null)
    getDashboardSummary()
      .then(setData)
      .catch(e => setError(e.message))
      .finally(() => setLoading(false))
  }

  useEffect(() => { load() }, [])

  if (loading) return <LoadingState message="Loading dashboard..." />
  if (error) return <ErrorState message={error} onRetry={load} />
  if (!data) return null

  const { kpis, monthly_sales_trend, top_products, inventory_risk_distribution, recent_alerts } = data

  return (
    <div>
      <div className="page-header">
        <h1 className="page-title">Supply Chain Overview</h1>
        <p className="page-description">
          Real-time supply chain analytics — all metrics sourced from live database calculations.
        </p>
      </div>

      {/* KPIs */}
      <div className="kpi-grid">
        <KpiCard label="Total Products" value={formatNumber(kpis.total_products)}
          icon={Package} color="#1e40af" bgColor="#eff6ff" />
        <KpiCard label="Inventory Value" value={formatCurrency(kpis.total_inventory_value)}
          icon={DollarSign} color="#16a34a" bgColor="#f0fdf4" />
        <KpiCard label="Products at Risk" value={formatNumber(kpis.products_at_risk)}
          icon={AlertTriangle} color="#dc2626" bgColor="#fef2f2" />
        <KpiCard label="Active Suppliers" value={formatNumber(kpis.active_suppliers)}
          icon={Users} color="#7c3aed" bgColor="#faf5ff" />
        <KpiCard label="Pending Shipments" value={formatNumber(kpis.pending_shipments)}
          icon={Truck} color="#0284c7" bgColor="#f0f9ff" />
        <KpiCard label="Revenue (30d)" value={formatCurrency(kpis.revenue_30d)}
          icon={TrendingUp} color="#0891b2" bgColor="#ecfeff" />
      </div>

      {/* Charts Row 1 */}
      <div className="grid-2 mb-6">
        {/* Revenue trend */}
        <div className="card">
          <div className="card-header">
            <div>
              <div className="card-title">Monthly Revenue Trend</div>
              <div className="card-subtitle">Last 6 months — aggregated from sales database</div>
            </div>
          </div>
          <div className="chart-container">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={monthly_sales_trend} margin={{ top: 4, right: 12, left: 0, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
                <XAxis dataKey="month" tick={{ fontSize: 11, fill: '#94a3b8' }} />
                <YAxis tickFormatter={v => `${(v/100000).toFixed(1)}L`} tick={{ fontSize: 11, fill: '#94a3b8' }} />
                <Tooltip formatter={(v) => [formatCurrency(v), 'Revenue']} />
                <Line type="monotone" dataKey="revenue" stroke="#1e40af" strokeWidth={2}
                  dot={{ r: 3, fill: '#1e40af' }} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Inventory Risk Distribution */}
        <div className="card">
          <div className="card-header">
            <div>
              <div className="card-title">Inventory Risk Distribution</div>
              <div className="card-subtitle">Products classified by stock risk level</div>
            </div>
          </div>
          <div className="chart-container" style={{ display: 'flex', alignItems: 'center' }}>
            <ResponsiveContainer width="60%" height="100%">
              <PieChart>
                <Pie
                  data={inventory_risk_distribution}
                  dataKey="count"
                  nameKey="risk_level"
                  cx="50%"
                  cy="50%"
                  outerRadius={80}
                  innerRadius={40}
                >
                  {inventory_risk_distribution.map((entry) => (
                    <Cell key={entry.risk_level} fill={RISK_COLORS[entry.risk_level] || '#94a3b8'} />
                  ))}
                </Pie>
                <Tooltip formatter={(v, n) => [v, n]} />
              </PieChart>
            </ResponsiveContainer>
            <div style={{ flex: 1, paddingLeft: 8 }}>
              {inventory_risk_distribution.map(d => (
                <div key={d.risk_level} style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8 }}>
                  <div style={{ width: 10, height: 10, borderRadius: 2, background: RISK_COLORS[d.risk_level], flexShrink: 0 }} />
                  <span style={{ fontSize: 12, color: 'var(--color-text-secondary)' }}>{d.risk_level}</span>
                  <span style={{ fontSize: 12, fontWeight: 600, marginLeft: 'auto' }}>{d.count}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* Charts Row 2 */}
      <div className="grid-2 mb-6">
        {/* Top Products */}
        <div className="card">
          <div className="card-header">
            <div className="card-title">Top Products by Revenue (30 days)</div>
          </div>
          <div className="chart-container">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={top_products} layout="vertical" margin={{ top: 4, right: 20, left: 70, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" horizontal={false} />
                <XAxis type="number" tickFormatter={v => `${(v/1000).toFixed(0)}K`} tick={{ fontSize: 11, fill: '#94a3b8' }} />
                <YAxis type="category" dataKey="product_id" tick={{ fontSize: 11, fill: '#475569' }} width={64} />
                <Tooltip formatter={v => [formatCurrency(v), 'Revenue']} />
                <Bar dataKey="revenue" fill="#1e40af" radius={[0, 4, 4, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Recent Alerts */}
        <div className="card" style={{ overflow: 'hidden' }}>
          <div className="card-header">
            <div>
              <div className="card-title">Recent Alerts</div>
              <div className="card-subtitle">Products requiring immediate attention</div>
            </div>
          </div>
          <div style={{ overflowY: 'auto', maxHeight: 240 }}>
            {recent_alerts.length === 0 ? (
              <div className="text-muted text-sm" style={{ padding: '16px 0' }}>No alerts at this time.</div>
            ) : (
              recent_alerts.map((alert, i) => (
                <div key={i} style={{
                  padding: '10px 0', borderBottom: i < recent_alerts.length - 1 ? '1px solid var(--color-border-light)' : 'none'
                }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <div>
                      <span style={{ fontWeight: 600, fontSize: 13 }}>{alert.product_id}</span>
                      <span style={{ color: 'var(--color-text-secondary)', fontSize: 12, marginLeft: 8 }}>
                        {alert.warehouse_id}
                      </span>
                    </div>
                    <RiskBadge level={alert.risk_level} />
                  </div>
                  <div style={{ fontSize: 12, color: 'var(--color-text-secondary)', marginTop: 3 }}>
                    {alert.issue} — Stock: {formatNumber(alert.current_stock)} / Reorder: {formatNumber(alert.reorder_point)}
                  </div>
                  <div style={{ fontSize: 11.5, color: 'var(--color-text-muted)', marginTop: 2 }}>
                    Action: {alert.recommended_action}
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
