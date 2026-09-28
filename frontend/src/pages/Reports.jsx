import { useState, useEffect } from 'react'
import { getInventoryRiskReport, getSupplierPerformanceReport, getDemandForecastReport, getLogisticsCostReport, getSupplyChainSummaryReport } from '../services/api'
import { RiskBadge, LoadingState, ErrorState, formatNumber, formatCurrency } from '../components/UI'
import { Download, FileText, RefreshCw } from 'lucide-react'

const REPORT_TYPES = [
  { id: 'summary', label: 'Supply Chain Summary', fn: getSupplyChainSummaryReport },
  { id: 'inventory', label: 'Inventory Risk Report', fn: getInventoryRiskReport },
  { id: 'supplier', label: 'Supplier Performance', fn: getSupplierPerformanceReport },
  { id: 'demand', label: 'Demand Forecast Report', fn: getDemandForecastReport },
  { id: 'logistics', label: 'Logistics Cost Report', fn: getLogisticsCostReport },
]

export default function Reports() {
  const [activeReport, setActiveReport] = useState('summary')
  const [reportData, setReportData] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  const loadReport = (type = activeReport) => {
    const report = REPORT_TYPES.find(r => r.id === type)
    if (!report) return
    setLoading(true)
    setError(null)
    setReportData(null)
    report.fn()
      .then(setReportData)
      .catch(e => setError(e.message))
      .finally(() => setLoading(false))
  }

  useEffect(() => { loadReport() }, [activeReport])

  const downloadCSV = () => {
    window.open('/api/reports/inventory-risk/csv', '_blank')
  }

  return (
    <div>
      <div className="page-header">
        <h1 className="page-title">Reports</h1>
        <p className="page-description">
          Generate and download supply chain analytics reports. All data sourced from live database calculations.
        </p>
      </div>

      {/* Report Type Selector */}
      <div className="filter-bar mb-6">
        {REPORT_TYPES.map(r => (
          <button
            key={r.id}
            className={`btn ${activeReport === r.id ? 'btn-primary' : 'btn-secondary'} btn-sm`}
            onClick={() => setActiveReport(r.id)}
          >
            {r.label}
          </button>
        ))}
        <button className="btn btn-secondary btn-sm" onClick={() => loadReport()} style={{ marginLeft: 'auto' }}>
          <RefreshCw size={13} /> Refresh
        </button>
        {activeReport === 'inventory' && (
          <button className="btn btn-secondary btn-sm" onClick={downloadCSV}>
            <Download size={13} /> Download CSV
          </button>
        )}
      </div>

      {loading && <LoadingState message="Generating report..." />}
      {error && <ErrorState message={error} onRetry={() => loadReport()} />}

      {reportData && !loading && (
        <>
          {/* Header */}
          <div className="card mb-6">
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
              <div>
                <div className="card-title" style={{ fontSize: 16 }}>{reportData.report_type}</div>
                <div className="card-subtitle">
                  Generated: {reportData.generated_at}
                  {reportData.period && ` — Period: ${reportData.period}`}
                  {reportData.horizon_days && ` — Horizon: ${reportData.horizon_days} days`}
                </div>
              </div>
              <span className="badge badge-info">Live Data</span>
            </div>
          </div>

          {/* SUMMARY REPORT */}
          {activeReport === 'summary' && reportData.risk_overview && (
            <div className="grid-3 mb-6">
              <div className="card">
                <div className="card-title mb-4">Risk Overview</div>
                {Object.entries(reportData.risk_overview).map(([k, v]) => (
                  <div key={k} className="metric-row">
                    <span className="metric-label">{k.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())}</span>
                    <RiskBadge level={v} />
                  </div>
                ))}
              </div>
              <div className="card">
                <div className="card-title mb-4">Inventory Summary</div>
                {Object.entries(reportData.inventory_summary || {}).map(([k, v]) => (
                  <div key={k} className="metric-row">
                    <span className="metric-label">{k.replace(/_/g, ' ')}</span>
                    <span className="metric-value">{typeof v === 'number' ? v.toLocaleString() : v}</span>
                  </div>
                ))}
              </div>
              <div className="card">
                <div className="card-title mb-4">Supplier Summary</div>
                {Object.entries(reportData.supplier_summary || {}).map(([k, v]) => (
                  <div key={k} className="metric-row">
                    <span className="metric-label">{k.replace(/_/g, ' ')}</span>
                    <span className="metric-value">{v}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* INVENTORY RISK REPORT */}
          {activeReport === 'inventory' && reportData.summary && (
            <>
              <div className="kpi-grid mb-6">
                {Object.entries(reportData.summary).map(([k, v]) => (
                  <div key={k} className="kpi-card">
                    <div className="kpi-label">{k.replace(/_/g, ' ')}</div>
                    <div className="kpi-value" style={{ fontSize: 22 }}>{v}</div>
                  </div>
                ))}
              </div>
              <div className="card" style={{ padding: 0 }}>
                <div className="table-container">
                  <table>
                    <thead>
                      <tr>
                        <th>Product</th>
                        <th>Stock</th>
                        <th>Safety Stock</th>
                        <th>Reorder Point</th>
                        <th>30d Forecast</th>
                        <th>Shortage</th>
                        <th>Order Qty</th>
                        <th>Risk</th>
                      </tr>
                    </thead>
                    <tbody>
                      {(reportData.products || []).map(p => (
                        <tr key={p.product_id}>
                          <td>
                            <div style={{ fontWeight: 600 }}>{p.product_id}</div>
                            <div style={{ fontSize: 11, color: 'var(--color-text-muted)' }}>{p.product_name}</div>
                          </td>
                          <td>{formatNumber(p.total_stock)}</td>
                          <td>{formatNumber(p.safety_stock)}</td>
                          <td>{formatNumber(p.reorder_point)}</td>
                          <td>{formatNumber(p.forecast_30_day, 0)}</td>
                          <td style={{ color: p.shortage > 0 ? 'var(--color-critical)' : 'inherit', fontWeight: p.shortage > 0 ? 700 : 400 }}>
                            {p.shortage > 0 ? `-${formatNumber(p.shortage, 0)}` : '--'}
                          </td>
                          <td>{p.recommended_order_quantity > 0 ? formatNumber(p.recommended_order_quantity) : '--'}</td>
                          <td><RiskBadge level={p.risk_level} /></td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            </>
          )}

          {/* SUPPLIER REPORT */}
          {activeReport === 'supplier' && (
            <div className="card" style={{ padding: 0 }}>
              <div className="table-container">
                <table>
                  <thead>
                    <tr>
                      <th>Supplier</th>
                      <th>Country</th>
                      <th>Reliability</th>
                      <th>Quality</th>
                      <th>Lead Time</th>
                      <th>Fulfillment</th>
                      <th>Delays</th>
                      <th>Score</th>
                      <th>Risk</th>
                    </tr>
                  </thead>
                  <tbody>
                    {(reportData.suppliers || []).map(s => (
                      <tr key={s.supplier_id}>
                        <td><div style={{ fontWeight: 600 }}>{s.supplier_name}</div></td>
                        <td>{s.country}</td>
                        <td>{s.reliability}%</td>
                        <td>{s.quality_score}</td>
                        <td>{s.lead_time_days}d</td>
                        <td>{s.order_fulfillment_rate}%</td>
                        <td>{s.historical_delays}</td>
                        <td style={{ fontWeight: 700 }}>{s.composite_score || '--'}</td>
                        <td><RiskBadge level={s.risk_level} /></td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* DEMAND REPORT */}
          {activeReport === 'demand' && (
            <div className="card" style={{ padding: 0 }}>
              <div className="table-container">
                <table>
                  <thead>
                    <tr>
                      <th>Product</th>
                      <th>Total Forecast</th>
                      <th>Avg Daily</th>
                      <th>MAE</th>
                      <th>RMSE</th>
                      <th>MAPE (%)</th>
                    </tr>
                  </thead>
                  <tbody>
                    {(reportData.products || []).map(p => (
                      <tr key={p.product_id}>
                        <td>
                          <div style={{ fontWeight: 600 }}>{p.product_id}</div>
                          <div style={{ fontSize: 11, color: 'var(--color-text-muted)' }}>{p.product_name}</div>
                        </td>
                        <td>{formatNumber(p.total_forecast, 0)}</td>
                        <td>{formatNumber(p.avg_daily_forecast, 1)}</td>
                        <td>{p.metrics?.MAE != null ? formatNumber(p.metrics.MAE, 2) : '--'}</td>
                        <td>{p.metrics?.RMSE != null ? formatNumber(p.metrics.RMSE, 2) : '--'}</td>
                        <td>{p.metrics?.MAPE != null ? `${formatNumber(p.metrics.MAPE, 1)}%` : '--'}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* LOGISTICS REPORT */}
          {activeReport === 'logistics' && (
            <div className="card" style={{ padding: 0 }}>
              <div className="table-container">
                <table>
                  <thead>
                    <tr>
                      <th>Warehouse</th>
                      <th>Destination</th>
                      <th>Total Cost</th>
                      <th>Shipments</th>
                      <th>Units</th>
                      <th>Avg Cost/Unit</th>
                    </tr>
                  </thead>
                  <tbody>
                    {(reportData.routes || []).map((r, i) => (
                      <tr key={i}>
                        <td style={{ fontWeight: 600 }}>{r.warehouse_id}</td>
                        <td>{r.destination}</td>
                        <td style={{ fontWeight: 700 }}>{formatCurrency(r.total_cost)}</td>
                        <td>{r.num_shipments}</td>
                        <td>{formatNumber(r.total_units)}</td>
                        <td>{formatCurrency(r.avg_cost_per_unit)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </>
      )}
    </div>
  )
}
