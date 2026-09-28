import { BrowserRouter, Routes, Route } from 'react-router-dom'
import Sidebar from './components/Sidebar'
import Dashboard from './pages/Dashboard'
import DemandForecast from './pages/DemandForecast'
import Inventory from './pages/Inventory'
import Suppliers from './pages/Suppliers'
import Logistics from './pages/Logistics'
import RiskAnalysis from './pages/RiskAnalysis'
import Documents from './pages/Documents'
import AIAgent from './pages/AIAgent'
import Reports from './pages/Reports'
import Settings from './pages/Settings'
import './index.css'

function TopBar({ title, subtitle }) {
  return (
    <div className="topbar">
      <div>
        <div className="topbar-title">{title}</div>
        {subtitle && <div className="topbar-subtitle">{subtitle}</div>}
      </div>
      <div className="topbar-actions">
        <span style={{
          fontSize: 12, color: 'var(--color-text-muted)',
          background: 'var(--color-surface-alt)',
          border: '1px solid var(--color-border)',
          borderRadius: 6, padding: '4px 10px',
          fontFamily: 'monospace',
        }}>
          llama3.2 via Ollama
        </span>
      </div>
    </div>
  )
}

const PAGE_META = {
  '/':          { title: 'Dashboard', subtitle: 'Supply Chain Overview' },
  '/demand':    { title: 'Demand Forecasting', subtitle: 'XGBoost ML Forecasting' },
  '/inventory': { title: 'Inventory Management', subtitle: 'Stock Levels and Reorder Analysis' },
  '/suppliers': { title: 'Supplier Management', subtitle: 'Supplier Scoring and Comparison' },
  '/logistics': { title: 'Logistics & Transportation', subtitle: 'Route Optimization via OR-Tools' },
  '/risk':      { title: 'Risk Analysis', subtitle: 'Comprehensive Supply Chain Risk Assessment' },
  '/documents': { title: 'Document Management', subtitle: 'RAG Pipeline — Policy Q&A' },
  '/agent':     { title: 'AI Agent', subtitle: 'LangGraph Multi-Agent System' },
  '/reports':   { title: 'Reports', subtitle: 'Analytics Reports' },
  '/settings':  { title: 'Settings', subtitle: 'System Configuration' },
}

function PageWrapper({ path, children }) {
  const meta = PAGE_META[path] || { title: 'SupplyChainAI' }
  return (
    <div className="main-content">
      <TopBar title={meta.title} subtitle={meta.subtitle} />
      <div className="page-content">{children}</div>
    </div>
  )
}

export default function App() {
  return (
    <BrowserRouter>
      <div className="app-layout">
        <Sidebar />
        <Routes>
          <Route path="/" element={<PageWrapper path="/"><Dashboard /></PageWrapper>} />
          <Route path="/demand" element={<PageWrapper path="/demand"><DemandForecast /></PageWrapper>} />
          <Route path="/inventory" element={<PageWrapper path="/inventory"><Inventory /></PageWrapper>} />
          <Route path="/suppliers" element={<PageWrapper path="/suppliers"><Suppliers /></PageWrapper>} />
          <Route path="/logistics" element={<PageWrapper path="/logistics"><Logistics /></PageWrapper>} />
          <Route path="/risk" element={<PageWrapper path="/risk"><RiskAnalysis /></PageWrapper>} />
          <Route path="/documents" element={<PageWrapper path="/documents"><Documents /></PageWrapper>} />
          <Route path="/agent" element={<PageWrapper path="/agent"><AIAgent /></PageWrapper>} />
          <Route path="/reports" element={<PageWrapper path="/reports"><Reports /></PageWrapper>} />
          <Route path="/settings" element={<PageWrapper path="/settings"><Settings /></PageWrapper>} />
        </Routes>
      </div>
    </BrowserRouter>
  )
}
