import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
  timeout: 120000,
  headers: { 'Content-Type': 'application/json' },
})

api.interceptors.response.use(
  (response) => response,
  (error) => {
    const message = error.response?.data?.detail || error.message || 'An error occurred'
    return Promise.reject(new Error(message))
  }
)

export default api

// ── Products ─────────────────────────────────────────────────────────────────
export const getProducts = () => api.get('/products').then(r => r.data)
export const getProduct = (id) => api.get(`/products/${id}`).then(r => r.data)

// ── Inventory ─────────────────────────────────────────────────────────────────
export const getInventory = () => api.get('/inventory').then(r => r.data)
export const getProductInventory = (pid) => api.get(`/inventory/${pid}`).then(r => r.data)
export const getStockoutRisk = (pid, horizon = 7) => api.get(`/inventory/${pid}/stockout-risk?horizon=${horizon}`).then(r => r.data)

// ── Demand ───────────────────────────────────────────────────────────────────
export const getDemandForecast = (pid, horizon = 30, warehouseId = null) => {
  const params = new URLSearchParams({ horizon: String(horizon) })
  if (warehouseId) params.append('warehouse_id', warehouseId)
  return api.get(`/demand/forecast/${pid}?${params}`).then(r => r.data)
}

// ── Suppliers ─────────────────────────────────────────────────────────────────
export const getSuppliers = () => api.get('/suppliers').then(r => r.data)
export const getProductSuppliers = (pid) => api.get(`/suppliers/product/${pid}`).then(r => r.data)
export const compareSuppliers = (pid) => api.get(`/suppliers/compare/${pid}`).then(r => r.data)
export const getSupplierRisk = (sid) => api.get(`/suppliers/${sid}/risk`).then(r => r.data)

// ── Logistics ─────────────────────────────────────────────────────────────────
export const getRoutes = (dest = null) => api.get(dest ? `/logistics/routes?destination=${dest}` : '/logistics/routes').then(r => r.data)
export const getWarehouses = () => api.get('/logistics/warehouses').then(r => r.data)
export const getShipments = () => api.get('/logistics/shipments').then(r => r.data)
export const optimizeLogistics = (body) => api.post('/logistics/optimize', body).then(r => r.data)

// ── Risk ──────────────────────────────────────────────────────────────────────
export const getRiskAnalysis = (pid = null) => api.get(pid ? `/risk/product/${pid}` : '/risk').then(r => r.data)

// ── Documents ────────────────────────────────────────────────────────────────
export const getDocuments = () => api.get('/documents').then(r => r.data)
export const uploadDocument = (formData) =>
  api.post('/documents/upload', formData, { headers: { 'Content-Type': 'multipart/form-data' } }).then(r => r.data)
export const ragQuery = (query, top_k = 5) => api.post('/rag/query', { query, top_k }).then(r => r.data)

// ── Agent ─────────────────────────────────────────────────────────────────────
export const agentQuery = (query, session_id = '') => api.post('/agent/query', { query, session_id }).then(r => r.data)
export const getDemoQueries = () => api.get('/agent/demo-queries').then(r => r.data)

// ── Dashboard ─────────────────────────────────────────────────────────────────
export const getDashboardSummary = () => api.get('/dashboard/summary').then(r => r.data)

// ── Reports ───────────────────────────────────────────────────────────────────
export const getInventoryRiskReport = () => api.get('/reports/inventory-risk').then(r => r.data)
export const getSupplierPerformanceReport = () => api.get('/reports/supplier-performance').then(r => r.data)
export const getDemandForecastReport = (horizon = 30) => api.get(`/reports/demand-forecast?horizon=${horizon}`).then(r => r.data)
export const getLogisticsCostReport = () => api.get('/reports/logistics-cost').then(r => r.data)
export const getSupplyChainSummaryReport = () => api.get('/reports/supply-chain-summary').then(r => r.data)
