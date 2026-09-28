/**
 * Reusable UI components for SupplyChainAI Dashboard.
 * No emojis anywhere. All icons from lucide-react.
 */
import { Loader2, AlertTriangle, Info, CheckCircle, XCircle } from 'lucide-react'

// ── Risk Badge ────────────────────────────────────────────────────────────────
export function RiskBadge({ level }) {
  const map = {
    Critical: 'badge-critical',
    High: 'badge-high',
    Medium: 'badge-medium',
    Low: 'badge-low',
  }
  return <span className={`badge ${map[level] || 'badge-neutral'}`}>{level || 'Unknown'}</span>
}

// ── Status Badge ──────────────────────────────────────────────────────────────
export function StatusBadge({ status }) {
  const map = {
    'Delivered': 'badge-low',
    'In Transit': 'badge-info',
    'Pending': 'badge-neutral',
    'Delayed': 'badge-high',
    'Ready': 'badge-low',
    'Processing': 'badge-info',
    'Failed': 'badge-critical',
  }
  return <span className={`badge ${map[status] || 'badge-neutral'}`}>{status}</span>
}

// ── Loading State ─────────────────────────────────────────────────────────────
export function LoadingState({ message = 'Loading...' }) {
  return (
    <div className="loading-spinner">
      <Loader2 size={18} className="spinner" style={{ animation: 'spin 0.7s linear infinite' }} />
      <span>{message}</span>
    </div>
  )
}

// ── Error State ───────────────────────────────────────────────────────────────
export function ErrorState({ message, onRetry }) {
  return (
    <div className="alert alert-error">
      <XCircle size={16} style={{ flexShrink: 0, marginTop: 1 }} />
      <div>
        <div style={{ fontWeight: 600 }}>Error</div>
        <div style={{ marginTop: 2 }}>{message}</div>
        {onRetry && (
          <button className="btn btn-sm btn-secondary" style={{ marginTop: 8 }} onClick={onRetry}>
            Retry
          </button>
        )}
      </div>
    </div>
  )
}

// ── Empty State ───────────────────────────────────────────────────────────────
export function EmptyState({ title = 'No data', description = '' }) {
  return (
    <div className="empty-state">
      <Info size={32} color="var(--color-text-muted)" style={{ margin: '0 auto 12px' }} />
      <div className="empty-state-title">{title}</div>
      {description && <div className="empty-state-desc">{description}</div>}
    </div>
  )
}

// ── KPI Card ──────────────────────────────────────────────────────────────────
export function KpiCard({ label, value, icon: Icon, color = '#1e40af', bgColor = '#eff6ff', change, changePositive }) {
  return (
    <div className="kpi-card">
      <div className="kpi-icon-wrap" style={{ background: bgColor }}>
        <Icon size={18} color={color} />
      </div>
      <div className="kpi-label">{label}</div>
      <div className="kpi-value">{value}</div>
      {change && (
        <div className="kpi-change" style={{ color: changePositive ? 'var(--color-low)' : 'var(--color-critical)' }}>
          <span>{change}</span>
        </div>
      )}
    </div>
  )
}

// ── Metric Row ────────────────────────────────────────────────────────────────
export function MetricRow({ label, value, valueStyle }) {
  return (
    <div className="metric-row">
      <span className="metric-label">{label}</span>
      <span className="metric-value" style={valueStyle}>{value}</span>
    </div>
  )
}

// ── Progress Bar ──────────────────────────────────────────────────────────────
export function ProgressBar({ value, max = 100, color = 'var(--color-primary)' }) {
  const pct = Math.min(100, Math.max(0, (value / max) * 100))
  return (
    <div className="progress-bar-wrap">
      <div className="progress-bar-fill" style={{ width: `${pct}%`, background: color }} />
    </div>
  )
}

// ── Section Header ────────────────────────────────────────────────────────────
export function SectionHeader({ title, subtitle, actions }) {
  return (
    <div className="card-header">
      <div>
        <div className="card-title">{title}</div>
        {subtitle && <div className="card-subtitle">{subtitle}</div>}
      </div>
      {actions && <div className="flex gap-2">{actions}</div>}
    </div>
  )
}

// ── Tooltip-like helper: format currency ──────────────────────────────────────
export function formatCurrency(val, currency = 'INR') {
  if (val == null) return '--'
  return new Intl.NumberFormat('en-IN', {
    style: 'currency', currency, maximumFractionDigits: 0
  }).format(val)
}

export function formatNumber(val, decimals = 0) {
  if (val == null) return '--'
  return Number(val).toLocaleString('en-IN', { maximumFractionDigits: decimals })
}

export function riskColor(level) {
  return {
    Critical: 'var(--color-critical)',
    High: 'var(--color-high)',
    Medium: 'var(--color-medium)',
    Low: 'var(--color-low)',
  }[level] || 'var(--color-text-muted)'
}
