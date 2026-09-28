import { NavLink } from 'react-router-dom'
import {
  LayoutDashboard, TrendingUp, Package, Truck, Users,
  AlertTriangle, FileText, Bot, BarChart2, Settings, Zap
} from 'lucide-react'

const navItems = [
  { path: '/', label: 'Dashboard', icon: LayoutDashboard },
  { path: '/demand', label: 'Demand Forecasting', icon: TrendingUp },
  { path: '/inventory', label: 'Inventory', icon: Package },
  { path: '/suppliers', label: 'Suppliers', icon: Users },
  { path: '/logistics', label: 'Logistics', icon: Truck },
  { path: '/risk', label: 'Risk Analysis', icon: AlertTriangle },
  { path: '/documents', label: 'Documents', icon: FileText },
  { path: '/agent', label: 'AI Agent', icon: Bot },
  { path: '/reports', label: 'Reports', icon: BarChart2 },
  { path: '/settings', label: 'Settings', icon: Settings },
]

export default function Sidebar() {
  return (
    <aside className="sidebar">
      <div className="sidebar-brand">
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 6 }}>
          <div style={{
            width: 28, height: 28, background: 'var(--color-primary)',
            borderRadius: 6, display: 'flex', alignItems: 'center', justifyContent: 'center'
          }}>
            <Zap size={14} color="#fff" />
          </div>
          <div className="sidebar-brand-name">SupplyChainAI</div>
        </div>
        <div className="sidebar-brand-sub">Decision Support System</div>
      </div>

      <div className="sidebar-section-label">Navigation</div>

      <nav className="sidebar-nav">
        {navItems.map(({ path, label, icon: Icon }) => (
          <NavLink
            key={path}
            to={path}
            className={({ isActive }) => `sidebar-item ${isActive ? 'active' : ''}`}
            end={path === '/'}
          >
            <Icon size={16} className="icon" />
            {label}
          </NavLink>
        ))}
      </nav>

      <div className="sidebar-footer">
        <div style={{ fontWeight: 500, color: '#64748b', fontSize: 11 }}>Academic Project</div>
        <div style={{ marginTop: 2, color: '#475569', fontSize: 11 }}>Agentic AI &amp; LLMs</div>
        <div style={{ marginTop: 6, color: '#334155', fontSize: 11, fontWeight: 500 }}>
          LLM: Ollama / llama3.2
        </div>
      </div>
    </aside>
  )
}
