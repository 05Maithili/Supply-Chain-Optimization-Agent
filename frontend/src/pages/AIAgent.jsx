import { useState, useEffect, useRef } from 'react'
import { agentQuery, getDemoQueries } from '../services/api'
import { RiskBadge, LoadingState } from '../components/UI'
import ReactMarkdown from 'react-markdown'
import { Send, Bot, User, Cpu } from 'lucide-react'

function AgentBadge({ name }) {
  const shortNames = {
    'Demand Forecasting Agent': 'Demand',
    'Inventory Optimization Agent': 'Inventory',
    'Supplier Analysis Agent': 'Supplier',
    'Logistics Optimization Agent': 'Logistics',
    'Risk Analysis Agent': 'Risk',
    'RAG Document Agent': 'RAG',
    'Decision Agent': 'Decision',
  }
  return (
    <span className="badge badge-info" style={{ fontSize: 10.5 }}>
      {shortNames[name] || name}
    </span>
  )
}

function ToolResultCard({ label, data }) {
  if (!data) return null
  return (
    <div style={{
      background: 'var(--color-surface)',
      border: '1px solid var(--color-border)',
      borderRadius: 8,
      padding: 12,
      marginTop: 8,
      fontSize: 12.5,
    }}>
      <div style={{ fontWeight: 600, color: 'var(--color-primary)', marginBottom: 8, fontSize: 12 }}>
        {label}
      </div>
      {Object.entries(data).map(([k, v]) => {
        if (typeof v === 'object' || v === null) return null
        return (
          <div key={k} className="metric-row" style={{ padding: '4px 0' }}>
            <span className="metric-label" style={{ fontSize: 12 }}>
              {k.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())}
            </span>
            <span className="metric-value" style={{ fontSize: 12 }}>
              {typeof v === 'number' ? v.toLocaleString() : String(v)}
            </span>
          </div>
        )
      })}
    </div>
  )
}

function Message({ msg }) {
  const isUser = msg.role === 'user'
  return (
    <div className={`chat-message ${isUser ? 'user' : 'assistant'}`}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 4 }}>
        {isUser
          ? <User size={13} color="var(--color-text-muted)" />
          : <Bot size={13} color="var(--color-primary)" />
        }
        <span style={{ fontSize: 11, color: 'var(--color-text-muted)' }}>
          {isUser ? 'You' : 'SupplyChainAI Agent'}
        </span>
        <span style={{ fontSize: 10, color: 'var(--color-text-muted)', marginLeft: 4 }}>
          {msg.time}
        </span>
      </div>

      <div className="chat-bubble">
        {isUser ? (
          <span>{msg.content}</span>
        ) : (
          <div className="markdown-content">
            <ReactMarkdown>{msg.content}</ReactMarkdown>
          </div>
        )}
      </div>

      {/* Agent metadata for assistant messages */}
      {!isUser && msg.agents_used?.length > 0 && (
        <div style={{ marginTop: 6 }}>
          <div style={{ fontSize: 10.5, color: 'var(--color-text-muted)', marginBottom: 4 }}>
            Agents used:
          </div>
          <div className="chat-agents-used">
            {msg.agents_used.map(a => <AgentBadge key={a} name={a} />)}
          </div>
        </div>
      )}

      {/* Tool results */}
      {!isUser && msg.tool_results && (
        <div style={{ marginTop: 8 }}>
          {msg.tool_results.inventory && (
            <ToolResultCard label="Inventory Status" data={msg.tool_results.inventory} />
          )}
          {msg.tool_results.demand_forecast && (
            <ToolResultCard label="Demand Forecast" data={msg.tool_results.demand_forecast} />
          )}
          {msg.tool_results.supplier_recommendation && (
            <ToolResultCard label="Supplier Recommendation" data={msg.tool_results.supplier_recommendation} />
          )}
          {msg.tool_results.risk_summary && (
            <ToolResultCard label="Risk Summary" data={msg.tool_results.risk_summary} />
          )}
          {msg.tool_results.inventory_summary && (
            <div style={{
              background: 'var(--color-surface)',
              border: '1px solid var(--color-border)',
              borderRadius: 8,
              padding: 12,
              marginTop: 8,
            }}>
              <div style={{ fontWeight: 600, color: 'var(--color-primary)', marginBottom: 8, fontSize: 12 }}>
                Inventory Summary — All Products
              </div>
              <div style={{ fontSize: 12.5, marginBottom: 6 }}>
                <strong>{msg.tool_results.inventory_summary.at_risk_count}</strong> of{' '}
                <strong>{msg.tool_results.inventory_summary.total_products}</strong> products at risk
              </div>
              {(msg.tool_results.inventory_summary.at_risk_products || []).map(p => (
                <div key={p.product_id} style={{
                  padding: '6px 0', borderBottom: '1px solid var(--color-border-light)',
                  display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: 12
                }}>
                  <span>
                    <strong>{p.product_id}</strong> — {p.product_name}
                    <br />
                    <span style={{ color: 'var(--color-text-muted)' }}>
                      Stock: {p.total_stock?.toLocaleString()} | Shortage: {p.shortage?.toLocaleString()} | Order: {p.recommended_order_quantity?.toLocaleString()}
                    </span>
                  </span>
                  <RiskBadge level={p.risk_level} />
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* RAG sources */}
      {!isUser && msg.sources?.length > 0 && (
        <div style={{ marginTop: 8, fontSize: 11 }}>
          <span style={{ color: 'var(--color-text-muted)', fontWeight: 500 }}>
            Policy sources: {msg.sources.map(s => s.source).join(', ')}
          </span>
        </div>
      )}

      {/* Errors */}
      {!isUser && msg.errors?.length > 0 && (
        <div className="alert alert-warning" style={{ marginTop: 8, fontSize: 12 }}>
          {msg.errors.join(' | ')}
        </div>
      )}
    </div>
  )
}

export default function AIAgent() {
  const [messages, setMessages] = useState([
    {
      role: 'assistant',
      content: 'Welcome to SupplyChainAI. I am an agentic AI system powered by a multi-agent LangGraph workflow with tool calling.\n\nI can analyze demand, inventory, suppliers, logistics, and risks using actual data — not guesses. Ask me anything about your supply chain.',
      agents_used: [],
      tool_results: null,
      sources: [],
      errors: [],
      time: new Date().toLocaleTimeString(),
    }
  ])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [demoQueries, setDemoQueries] = useState([])
  const messagesEnd = useRef(null)
  const sessionId = useRef(`session-${Date.now()}`)

  useEffect(() => {
    getDemoQueries().then(setDemoQueries).catch(() => {})
  }, [])

  useEffect(() => {
    messagesEnd.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const send = async (text) => {
    const q = (text || input).trim()
    if (!q || loading) return
    setInput('')

    const userMsg = { role: 'user', content: q, time: new Date().toLocaleTimeString() }
    setMessages(prev => [...prev, userMsg])
    setLoading(true)

    try {
      const result = await agentQuery(q, sessionId.current)
      const assistantMsg = {
        role: 'assistant',
        content: result.answer || 'No response generated.',
        agents_used: result.agents_used || [],
        tool_results: result.tool_results || null,
        sources: result.sources || [],
        errors: result.errors || [],
        intent: result.intent,
        time: new Date().toLocaleTimeString(),
      }
      setMessages(prev => [...prev, assistantMsg])
    } catch (e) {
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: `Error: ${e.message}. Ensure the backend is running and Ollama is available.`,
        agents_used: [],
        tool_results: null,
        sources: [],
        errors: [e.message],
        time: new Date().toLocaleTimeString(),
      }])
    } finally {
      setLoading(false)
    }
  }

  return (
    <div>
      <div className="page-header">
        <h1 className="page-title">AI Agent</h1>
        <p className="page-description">
          Multi-agent LangGraph system — the LLM orchestrates specialized agents and calls tools to provide evidence-based recommendations.
        </p>
      </div>

      {/* Demo queries */}
      <div className="demo-queries mb-4">
        {demoQueries.map(q => (
          <button
            key={q.id}
            className="demo-query-chip"
            onClick={() => send(q.query)}
            disabled={loading}
          >
            {q.query}
          </button>
        ))}
      </div>

      {/* Chat Container */}
      <div className="chat-container">
        <div style={{
          padding: '10px 20px',
          borderBottom: '1px solid var(--color-border)',
          background: 'var(--color-surface-alt)',
          display: 'flex', alignItems: 'center', gap: 8
        }}>
          <Cpu size={14} color="var(--color-primary)" />
          <span style={{ fontSize: 12.5, fontWeight: 500, color: 'var(--color-text-secondary)' }}>
            LangGraph Workflow — 8 Agents — Ollama llama3.2 — Tool Calling Active
          </span>
        </div>

        <div className="chat-messages">
          {messages.map((msg, i) => <Message key={i} msg={msg} />)}
          {loading && (
            <div className="chat-message assistant">
              <div className="chat-bubble" style={{ padding: '10px 14px' }}>
                <LoadingState message="Running multi-agent workflow..." />
              </div>
            </div>
          )}
          <div ref={messagesEnd} />
        </div>

        <div className="chat-input-area">
          <textarea
            className="chat-input"
            placeholder="Ask about demand forecasts, inventory, suppliers, risks, or upload policy documents..."
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={e => {
              if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault()
                send()
              }
            }}
            rows={1}
          />
          <button
            className="btn btn-primary"
            onClick={() => send()}
            disabled={loading || !input.trim()}
          >
            <Send size={14} />
            Send
          </button>
        </div>
      </div>
    </div>
  )
}
