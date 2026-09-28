import { useState, useEffect } from 'react'
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, Legend, ReferenceLine
} from 'recharts'
import { getProducts, getDemandForecast, getWarehouses } from '../services/api'
import { LoadingState, ErrorState, MetricRow, formatNumber } from '../components/UI'
import { RefreshCw } from 'lucide-react'

export default function DemandForecast() {
  const [products, setProducts] = useState([])
  const [warehouses, setWarehouses] = useState([])
  const [selectedProduct, setSelectedProduct] = useState('')
  const [selectedWarehouse, setSelectedWarehouse] = useState('')
  const [horizon, setHorizon] = useState(30)
  const [forecastData, setForecastData] = useState(null)
  const [loading, setLoading] = useState(false)
  const [loadingInit, setLoadingInit] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    Promise.all([getProducts(), getWarehouses()])
      .then(([prods, whs]) => {
        setProducts(prods)
        setWarehouses(whs)
        if (prods.length) setSelectedProduct(prods[0].product_id)
      })
      .catch(e => setError(e.message))
      .finally(() => setLoadingInit(false))
  }, [])

  const runForecast = () => {
    if (!selectedProduct) return
    setLoading(true)
    setError(null)
    getDemandForecast(selectedProduct, horizon, selectedWarehouse || null)
      .then(setForecastData)
      .catch(e => setError(e.message))
      .finally(() => setLoading(false))
  }

  useEffect(() => {
    if (selectedProduct) runForecast()
  }, [selectedProduct])

  if (loadingInit) return <LoadingState message="Loading products..." />

  // Merge historical + forecast for chart
  let chartData = []
  if (forecastData) {
    const hist = (forecastData.historical || []).slice(-60).map(d => ({
      date: d.date, actual: d.actual, type: 'Historical'
    }))
    const fcast = (forecastData.forecast || []).map(d => ({
      date: d.date, predicted: d.predicted, lower: d.lower, upper: d.upper, type: 'Forecast'
    }))
    chartData = [...hist, ...fcast]
  }

  const metrics = forecastData?.metrics || {}

  return (
    <div>
      <div className="page-header">
        <h1 className="page-title">Demand Forecasting</h1>
        <p className="page-description">
          XGBoost-powered demand forecast with feature engineering and time-series cross-validation.
        </p>
      </div>

      {/* Filter Bar */}
      <div className="filter-bar">
        <div className="form-group" style={{ margin: 0 }}>
          <label style={{ marginBottom: 4 }}>Product</label>
          <select
            value={selectedProduct}
            onChange={e => setSelectedProduct(e.target.value)}
            style={{ minWidth: 200 }}
          >
            {products.map(p => (
              <option key={p.product_id} value={p.product_id}>
                {p.product_id} — {p.product_name}
              </option>
            ))}
          </select>
        </div>
        <div className="form-group" style={{ margin: 0 }}>
          <label style={{ marginBottom: 4 }}>Warehouse</label>
          <select
            value={selectedWarehouse}
            onChange={e => setSelectedWarehouse(e.target.value)}
            style={{ minWidth: 180 }}
          >
            <option value="">All Warehouses</option>
            {warehouses.map(w => (
              <option key={w.warehouse_id} value={w.warehouse_id}>{w.warehouse_name}</option>
            ))}
          </select>
        </div>
        <div className="form-group" style={{ margin: 0 }}>
          <label style={{ marginBottom: 4 }}>Horizon (days)</label>
          <select value={horizon} onChange={e => setHorizon(Number(e.target.value))} style={{ width: 120 }}>
            {[7, 14, 30, 60, 90].map(h => (
              <option key={h} value={h}>{h} days</option>
            ))}
          </select>
        </div>
        <button className="btn btn-primary" onClick={runForecast} disabled={loading} style={{ alignSelf: 'flex-end' }}>
          <RefreshCw size={14} />
          {loading ? 'Forecasting...' : 'Run Forecast'}
        </button>
      </div>

      {error && <ErrorState message={error} onRetry={runForecast} />}

      {loading && <LoadingState message="Running XGBoost forecast..." />}

      {forecastData && !loading && (
        <>
          {/* Model Metrics */}
          <div className="grid-4 mb-6" style={{ gridTemplateColumns: 'repeat(4, 1fr)' }}>
            {[
              { label: 'Total Forecast', value: `${formatNumber(forecastData.total_forecast)} units` },
              { label: 'Avg Daily Demand', value: `${formatNumber(forecastData.avg_daily_forecast, 1)} units/day` },
              { label: 'MAE', value: metrics.MAE != null ? formatNumber(metrics.MAE, 2) : 'N/A' },
              { label: 'MAPE', value: metrics.MAPE != null ? `${formatNumber(metrics.MAPE, 1)}%` : 'N/A' },
            ].map(({ label, value }) => (
              <div key={label} className="card" style={{ padding: 16, textAlign: 'center' }}>
                <div className="kpi-label">{label}</div>
                <div className="kpi-value" style={{ fontSize: 20 }}>{value}</div>
              </div>
            ))}
          </div>

          {/* Chart */}
          <div className="card mb-6">
            <div className="card-header">
              <div>
                <div className="card-title">Demand Forecast — {selectedProduct}</div>
                <div className="card-subtitle">
                  Historical demand (blue) and {horizon}-day forecast (orange) with 95% confidence band.
                  Model: {forecastData.model}
                </div>
              </div>
            </div>
            <div className="chart-container-lg">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={chartData} margin={{ top: 8, right: 24, left: 0, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
                  <XAxis dataKey="date" tick={{ fontSize: 10, fill: '#94a3b8' }}
                    interval={Math.floor(chartData.length / 8)} />
                  <YAxis tick={{ fontSize: 11, fill: '#94a3b8' }} />
                  <Tooltip
                    formatter={(v, n) => [v != null ? formatNumber(v, 1) : '--', n]}
                    labelStyle={{ fontSize: 11 }}
                  />
                  <Legend />
                  <Line type="monotone" dataKey="actual" stroke="#1e40af" strokeWidth={2}
                    dot={false} name="Historical Demand" />
                  <Line type="monotone" dataKey="predicted" stroke="#ea580c" strokeWidth={2}
                    strokeDasharray="4 2" dot={false} name="Forecast" />
                  <Line type="monotone" dataKey="upper" stroke="#ea580c" strokeWidth={1}
                    strokeDasharray="2 4" dot={false} name="Upper Bound" opacity={0.4} />
                  <Line type="monotone" dataKey="lower" stroke="#ea580c" strokeWidth={1}
                    strokeDasharray="2 4" dot={false} name="Lower Bound" opacity={0.4} />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </div>

          {/* Evaluation Metrics */}
          <div className="card">
            <div className="card-header">
              <div className="card-title">Model Evaluation Metrics</div>
              <div className="card-subtitle">Time-series cross-validation results</div>
            </div>
            <div style={{ maxWidth: 400 }}>
              <MetricRow label="Model Used" value={forecastData.model} />
              <MetricRow label="Mean Absolute Error (MAE)" value={metrics.MAE != null ? formatNumber(metrics.MAE, 2) : 'Insufficient data'} />
              <MetricRow label="Root Mean Square Error (RMSE)" value={metrics.RMSE != null ? formatNumber(metrics.RMSE, 2) : 'Insufficient data'} />
              <MetricRow label="Mean Absolute Percentage Error (MAPE)" value={metrics.MAPE != null ? `${formatNumber(metrics.MAPE, 1)}%` : 'Insufficient data'} />
              <MetricRow label="Forecast Horizon" value={`${forecastData.horizon_days} days`} />
            </div>
          </div>
        </>
      )}
    </div>
  )
}
