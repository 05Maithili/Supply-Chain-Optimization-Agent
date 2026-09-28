import { useState, useEffect } from 'react'
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts'
import { getRoutes, getWarehouses, getShipments, optimizeLogistics, getProducts } from '../services/api'
import { StatusBadge, LoadingState, ErrorState, formatNumber } from '../components/UI'
import { Truck, ArrowRight } from 'lucide-react'

export default function Logistics() {
  const [routes, setRoutes] = useState([])
  const [warehouses, setWarehouses] = useState([])
  const [shipments, setShipments] = useState([])
  const [products, setProducts] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  // Optimization form
  const [optProduct, setOptProduct] = useState('')
  const [optDest, setOptDest] = useState('')
  const [optQty, setOptQty] = useState(100)
  const [optResult, setOptResult] = useState(null)
  const [optLoading, setOptLoading] = useState(false)

  useEffect(() => {
    Promise.all([getRoutes(), getWarehouses(), getShipments(), getProducts()])
      .then(([r, w, s, p]) => {
        setRoutes(r.all_routes || [])
        setWarehouses(w)
        setShipments(s)
        setProducts(p)
        if (p.length) setOptProduct(p[0].product_id)
      })
      .catch(e => setError(e.message))
      .finally(() => setLoading(false))
  }, [])

  const runOptimization = () => {
    if (!optProduct || !optDest) return
    setOptLoading(true)
    optimizeLogistics({ product_id: optProduct, destination: optDest, quantity: optQty })
      .then(setOptResult)
      .catch(e => setError(e.message))
      .finally(() => setOptLoading(false))
  }

  if (loading) return <LoadingState message="Loading logistics data..." />
  if (error) return <ErrorState message={error} />

  const routeCostData = routes.slice(0, 8).map(r => ({
    route: `${r.origin_warehouse_id}->${r.destination?.split(',')[0]}`,
    cost: r.estimated_cost_100_units,
    distance: r.distance_km,
    time: r.transit_time_days,
  }))

  const destinations = [...new Set(routes.map(r => r.destination))]

  return (
    <div>
      <div className="page-header">
        <h1 className="page-title">Logistics & Transportation</h1>
        <p className="page-description">
          Route optimization powered by Google OR-Tools. Transportation costs calculated from distance and unit weight.
        </p>
      </div>

      {/* Warehouse summary */}
      <div className="kpi-grid mb-6">
        {warehouses.map(w => (
          <div key={w.warehouse_id} className="kpi-card">
            <div className="kpi-label">{w.warehouse_name}</div>
            <div style={{ fontSize: 12, color: 'var(--color-text-secondary)', margin: '4px 0' }}>{w.location}</div>
            <div style={{ fontWeight: 700, fontSize: 18 }}>{formatNumber(w.capacity)} capacity</div>
            <div style={{ marginTop: 8 }}>
              <div style={{ fontSize: 11.5, color: 'var(--color-text-muted)', marginBottom: 4 }}>
                Utilization: {formatNumber(w.current_utilization, 1)}%
              </div>
              <div className="progress-bar-wrap">
                <div className="progress-bar-fill" style={{
                  width: `${w.current_utilization}%`,
                  background: w.current_utilization > 80 ? 'var(--color-critical)' : 'var(--color-primary)'
                }} />
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Transport Cost Chart */}
      <div className="card mb-6">
        <div className="card-header">
          <div className="card-title">Transportation Cost by Route (100 units)</div>
          <div className="card-subtitle">Base cost + distance surcharge + fuel + handling</div>
        </div>
        <div className="chart-container">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={routeCostData} margin={{ top: 4, right: 12, left: 0, bottom: 40 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
              <XAxis dataKey="route" tick={{ fontSize: 10, fill: '#94a3b8' }} angle={-25} textAnchor="end" />
              <YAxis tick={{ fontSize: 11, fill: '#94a3b8' }} />
              <Tooltip formatter={(v) => [`INR ${formatNumber(v, 0)}`, 'Cost']} />
              <Bar dataKey="cost" fill="#1e40af" radius={[3, 3, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Warehouse Allocation Optimizer */}
      <div className="card mb-6">
        <div className="card-header">
          <div>
            <div className="card-title">Warehouse Allocation Optimizer</div>
            <div className="card-subtitle">OR-Tools minimizes total transportation cost across warehouses</div>
          </div>
        </div>
        <div className="filter-bar" style={{ marginBottom: 16 }}>
          <div>
            <label>Product</label>
            <select value={optProduct} onChange={e => setOptProduct(e.target.value)} style={{ minWidth: 180 }}>
              {products.map(p => <option key={p.product_id} value={p.product_id}>{p.product_id} — {p.product_name}</option>)}
            </select>
          </div>
          <div>
            <label>Destination</label>
            <select value={optDest} onChange={e => setOptDest(e.target.value)} style={{ minWidth: 180 }}>
              <option value="">Select destination</option>
              {destinations.map(d => <option key={d} value={d}>{d}</option>)}
            </select>
          </div>
          <div>
            <label>Quantity</label>
            <input type="number" value={optQty} onChange={e => setOptQty(Number(e.target.value))} min={1} style={{ width: 100 }} />
          </div>
          <button className="btn btn-primary" onClick={runOptimization} disabled={optLoading || !optDest} style={{ alignSelf: 'flex-end' }}>
            <Truck size={14} />
            {optLoading ? 'Optimizing...' : 'Optimize Allocation'}
          </button>
        </div>

        {optResult && (
          <div>
            <div style={{ marginBottom: 12, padding: '10px 14px', background: 'var(--color-info-bg)', border: '1px solid #bae6fd', borderRadius: 8 }}>
              <div style={{ fontWeight: 600, color: 'var(--color-info)', fontSize: 13 }}>
                Optimization Complete — Total Transport Cost: INR {formatNumber(optResult.total_transportation_cost, 0)}
              </div>
              <div style={{ fontSize: 12, color: 'var(--color-text-secondary)', marginTop: 2 }}>
                {optResult.quantity_requested} units to {optResult.destination}
              </div>
            </div>
            <div className="table-container">
              <table>
                <thead>
                  <tr>
                    <th>Warehouse</th>
                    <th>Allocated Qty</th>
                    <th>Available Stock</th>
                    <th>Distance</th>
                    <th>Transit Time</th>
                    <th>Cost/Unit</th>
                    <th>Total Cost</th>
                  </tr>
                </thead>
                <tbody>
                  {(optResult.allocations || []).map(a => (
                    <tr key={a.warehouse_id}>
                      <td style={{ fontWeight: 600 }}>{a.warehouse_name}</td>
                      <td style={{ fontWeight: 700, color: 'var(--color-primary)' }}>{formatNumber(a.allocated_quantity)}</td>
                      <td>{formatNumber(a.available_stock)}</td>
                      <td>{a.distance_km ? `${formatNumber(a.distance_km, 0)} km` : '--'}</td>
                      <td>{a.transit_time_days ? `${a.transit_time_days} days` : '--'}</td>
                      <td>{a.cost_per_unit ? `INR ${formatNumber(a.cost_per_unit, 1)}` : '--'}</td>
                      <td>{a.total_cost ? `INR ${formatNumber(a.total_cost, 0)}` : '--'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </div>

      {/* Shipments */}
      <div className="card" style={{ padding: 0 }}>
        <div style={{ padding: '16px 20px 0' }}>
          <div className="card-title">Recent Shipments</div>
          <div className="card-subtitle" style={{ marginBottom: 12 }}>Last 50 shipments from database</div>
        </div>
        <div className="table-container" style={{ border: 'none' }}>
          <table>
            <thead>
              <tr>
                <th>Shipment ID</th>
                <th>Product</th>
                <th>From</th>
                <th>To</th>
                <th>Qty</th>
                <th>Status</th>
                <th>Ship Date</th>
                <th>Est. Delivery</th>
                <th>Cost</th>
              </tr>
            </thead>
            <tbody>
              {shipments.map(s => (
                <tr key={s.shipment_id}>
                  <td style={{ fontFamily: 'monospace', fontSize: 12 }}>{s.shipment_id}</td>
                  <td>{s.product_id}</td>
                  <td>{s.warehouse_id}</td>
                  <td style={{ maxWidth: 140 }} className="truncate">{s.destination}</td>
                  <td>{formatNumber(s.quantity)}</td>
                  <td><StatusBadge status={s.status} /></td>
                  <td style={{ fontSize: 12 }}>{s.ship_date || '--'}</td>
                  <td style={{ fontSize: 12 }}>{s.estimated_delivery || '--'}</td>
                  <td>INR {formatNumber(s.transportation_cost, 0)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}
