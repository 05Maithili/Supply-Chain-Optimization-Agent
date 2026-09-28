import { useState, useEffect } from 'react'
import { Settings2, Server, Database, Cpu } from 'lucide-react'

export default function Settings() {
  const [ollamaStatus, setOllamaStatus] = useState('Checking...')
  const [backendStatus, setBackendStatus] = useState('Checking...')

  useEffect(() => {
    const checkBackend = async () => {
      try {
        const res = await fetch('/api/health')
        if (res.ok) {
          const d = await res.json()
          if (d.status === 'ok') {
            setBackendStatus('Connected')
            return
          }
        }
      } catch (_) {}

      try {
        const res = await fetch('/health')
        if (res.ok) {
          const d = await res.json()
          if (d.status === 'ok') {
            setBackendStatus('Connected')
            return
          }
        }
      } catch (_) {}

      setBackendStatus('Unavailable')
    }

    checkBackend()

    fetch('http://localhost:11434/api/tags')
      .then(r => r.json())
      .then(d => {
        const models = d.models?.map(m => m.name) || []
        setOllamaStatus(models.includes('llama3.2') || models.some(m => m.includes('llama3.2'))
          ? 'Connected — llama3.2 available'
          : `Connected — Models: ${models.slice(0, 3).join(', ')}`)
      })
      .catch(() => setOllamaStatus('Unavailable — Start Ollama: ollama serve'))
  }, [])

  return (
    <div>
      <div className="page-header">
        <h1 className="page-title">Settings</h1>
        <p className="page-description">System configuration and connection status.</p>
      </div>

      <div className="grid-2">
        <div className="card">
          <div className="card-header">
            <div className="card-title">System Status</div>
          </div>
          <div className="metric-row">
            <span className="metric-label"><Server size={13} style={{ display: 'inline', marginRight: 6 }} />Backend API</span>
            <span className={`badge ${backendStatus === 'Connected' ? 'badge-low' : 'badge-critical'}`}>
              {backendStatus}
            </span>
          </div>
          <div className="metric-row">
            <span className="metric-label"><Cpu size={13} style={{ display: 'inline', marginRight: 6 }} />Ollama LLM</span>
            <span className={`badge ${ollamaStatus.startsWith('Connected') ? 'badge-low' : 'badge-critical'}`}>
              {ollamaStatus}
            </span>
          </div>
          <div className="metric-row">
            <span className="metric-label"><Database size={13} style={{ display: 'inline', marginRight: 6 }} />Database</span>
            <span className="badge badge-low">SQLite — Active</span>
          </div>
        </div>

        <div className="card">
          <div className="card-header">
            <div className="card-title">Configuration</div>
          </div>
          {[
            ['LLM Provider', 'Ollama (local)'],
            ['LLM Model', 'llama3.2'],
            ['Embedding Model', 'all-MiniLM-L6-v2'],
            ['Agent Framework', 'LangGraph'],
            ['Forecasting Model', 'XGBoost'],
            ['Optimization', 'Google OR-Tools'],
            ['Vector Store', 'FAISS (NumPy-based)'],
            ['Database', 'SQLite (async)'],
          ].map(([k, v]) => (
            <div key={k} className="metric-row">
              <span className="metric-label">{k}</span>
              <span className="metric-value" style={{ fontSize: 12.5 }}>{v}</span>
            </div>
          ))}
        </div>

        <div className="card col-span-2">
          <div className="card-header">
            <div className="card-title">Quick Start Commands</div>
          </div>
          <div style={{ fontFamily: 'monospace', fontSize: 12.5, lineHeight: 2 }}>
            <div style={{ marginBottom: 12 }}>
              <div style={{ color: 'var(--color-text-secondary)', marginBottom: 4, fontFamily: 'inherit', fontWeight: 600 }}>
                1. Start Ollama &amp; pull model:
              </div>
              <code style={{ background: '#0f172a', color: '#e2e8f0', padding: '8px 14px', borderRadius: 6, display: 'block' }}>
                ollama serve<br />
                ollama pull llama3.2
              </code>
            </div>
            <div style={{ marginBottom: 12 }}>
              <div style={{ color: 'var(--color-text-secondary)', marginBottom: 4, fontFamily: 'inherit', fontWeight: 600 }}>
                2. Start backend:
              </div>
              <code style={{ background: '#0f172a', color: '#e2e8f0', padding: '8px 14px', borderRadius: 6, display: 'block' }}>
                cd backend<br />
                pip install -r requirements.txt<br />
                uvicorn main:app --reload
              </code>
            </div>
            <div>
              <div style={{ color: 'var(--color-text-secondary)', marginBottom: 4, fontFamily: 'inherit', fontWeight: 600 }}>
                3. Start frontend:
              </div>
              <code style={{ background: '#0f172a', color: '#e2e8f0', padding: '8px 14px', borderRadius: 6, display: 'block' }}>
                cd frontend<br />
                npm install<br />
                npm run dev
              </code>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
