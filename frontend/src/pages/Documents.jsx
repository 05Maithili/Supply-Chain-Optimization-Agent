import { useState, useEffect, useRef } from 'react'
import { getDocuments, uploadDocument, ragQuery } from '../services/api'
import { LoadingState, ErrorState, StatusBadge, formatNumber } from '../components/UI'
import { Upload, Send, FileText } from 'lucide-react'

export default function Documents() {
  const [documents, setDocuments] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [uploading, setUploading] = useState(false)
  const [uploadMsg, setUploadMsg] = useState(null)
  const [dragOver, setDragOver] = useState(false)
  const [query, setQuery] = useState('')
  const [queryLoading, setQueryLoading] = useState(false)
  const [queryResult, setQueryResult] = useState(null)
  const fileInput = useRef(null)

  const loadDocs = () => {
    getDocuments()
      .then(setDocuments)
      .catch(e => setError(e.message))
      .finally(() => setLoading(false))
  }

  useEffect(() => { loadDocs() }, [])

  const handleUpload = async (file) => {
    if (!file) return
    const ext = file.name.rsplit?.('.', 1)?.[1]?.toLowerCase() || file.name.split('.').pop().toLowerCase()
    if (!['pdf', 'txt', 'docx'].includes(ext)) {
      setUploadMsg({ type: 'error', text: 'Only PDF, TXT, and DOCX files are allowed.' })
      return
    }
    setUploading(true)
    setUploadMsg(null)
    const form = new FormData()
    form.append('file', file)
    form.append('description', '')
    try {
      const result = await uploadDocument(form)
      setUploadMsg({ type: 'success', text: `Uploaded "${result.filename}" — ${result.num_chunks} chunks indexed.` })
      loadDocs()
    } catch (e) {
      setUploadMsg({ type: 'error', text: e.message })
    } finally {
      setUploading(false)
    }
  }

  const handleDrop = (e) => {
    e.preventDefault()
    setDragOver(false)
    const file = e.dataTransfer.files[0]
    if (file) handleUpload(file)
  }

  const runQuery = async () => {
    if (!query.trim()) return
    setQueryLoading(true)
    setQueryResult(null)
    try {
      const result = await ragQuery(query)
      setQueryResult(result)
    } catch (e) {
      setQueryResult({ answer: `Error: ${e.message}`, sources: [] })
    } finally {
      setQueryLoading(false)
    }
  }

  return (
    <div>
      <div className="page-header">
        <h1 className="page-title">Document Management</h1>
        <p className="page-description">
          Upload supply chain policy documents. The RAG pipeline indexes them for AI-powered question answering.
        </p>
      </div>

      <div className="grid-2 mb-6">
        {/* Upload Zone */}
        <div className="card">
          <div className="card-header">
            <div className="card-title">Upload Document</div>
            <div className="card-subtitle">PDF, TXT, DOCX — max 50 MB</div>
          </div>

          <div
            className={`upload-zone ${dragOver ? 'drag-over' : ''}`}
            onDragOver={e => { e.preventDefault(); setDragOver(true) }}
            onDragLeave={() => setDragOver(false)}
            onDrop={handleDrop}
            onClick={() => fileInput.current?.click()}
          >
            <Upload size={28} color="var(--color-text-muted)" style={{ margin: '0 auto' }} />
            <div className="upload-zone-title">Drop file here or click to browse</div>
            <div className="upload-zone-sub">Supported formats: PDF, TXT, DOCX</div>
          </div>

          <input
            ref={fileInput}
            type="file"
            accept=".pdf,.txt,.docx"
            style={{ display: 'none' }}
            onChange={e => handleUpload(e.target.files[0])}
          />

          {uploading && <LoadingState message="Uploading and indexing document..." />}

          {uploadMsg && (
            <div className={`alert ${uploadMsg.type === 'error' ? 'alert-error' : 'alert-success'}`} style={{ marginTop: 12 }}>
              {uploadMsg.text}
            </div>
          )}
        </div>

        {/* RAG Query */}
        <div className="card">
          <div className="card-header">
            <div className="card-title">Query Documents</div>
            <div className="card-subtitle">Ask questions about uploaded policy documents</div>
          </div>

          <div style={{ display: 'flex', gap: 8, marginBottom: 16 }}>
            <input
              type="text"
              placeholder="e.g. What is the safety stock policy?"
              value={query}
              onChange={e => setQuery(e.target.value)}
              onKeyDown={e => e.key === 'Enter' && runQuery()}
              style={{ flex: 1 }}
            />
            <button className="btn btn-primary" onClick={runQuery} disabled={queryLoading || !query.trim()}>
              <Send size={14} />
              {queryLoading ? 'Searching...' : 'Ask'}
            </button>
          </div>

          {queryLoading && <LoadingState message="Searching documents..." />}

          {queryResult && (
            <div>
              <div style={{
                background: 'var(--color-surface-alt)',
                border: '1px solid var(--color-border)',
                borderRadius: 8,
                padding: 14,
                fontSize: 13.5,
                lineHeight: 1.7,
                marginBottom: 12,
              }}>
                {queryResult.answer}
              </div>

              {queryResult.sources?.length > 0 && (
                <div>
                  <div style={{ fontSize: 11.5, fontWeight: 600, color: 'var(--color-text-secondary)', marginBottom: 6 }}>
                    Sources ({queryResult.num_chunks_retrieved} chunks retrieved):
                  </div>
                  {queryResult.sources.map((s, i) => (
                    <div key={i} style={{
                      fontSize: 11.5, padding: '4px 0',
                      borderBottom: i < queryResult.sources.length - 1 ? '1px solid var(--color-border-light)' : 'none',
                    }}>
                      <span style={{ fontWeight: 600 }}>{s.source}</span>
                      <span style={{ color: 'var(--color-text-muted)', marginLeft: 8 }}>
                        Chunk {s.chunk_id} — Relevance: {s.relevance_score}
                      </span>
                      <div style={{ color: 'var(--color-text-secondary)', marginTop: 2, fontStyle: 'italic' }}>
                        "{s.excerpt}"
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {queryResult === null && !queryLoading && (
            <div className="empty-state" style={{ padding: '20px 0' }}>
              <div className="empty-state-desc">
                Upload documents and ask questions to get policy-grounded answers with source citations.
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Document List */}
      <div className="card" style={{ padding: 0 }}>
        <div style={{ padding: '16px 20px 0' }}>
          <div className="card-title">Indexed Documents</div>
          <div className="card-subtitle" style={{ marginBottom: 12 }}>{documents.length} document(s) in vector store</div>
        </div>

        {loading ? <LoadingState /> : (
          documents.length === 0 ? (
            <div className="empty-state">
              <FileText size={28} color="var(--color-text-muted)" style={{ margin: '0 auto 8px' }} />
              <div className="empty-state-title">No documents uploaded</div>
              <div className="empty-state-desc">Upload PDF, TXT, or DOCX files to enable RAG-based policy Q&A.</div>
            </div>
          ) : (
            <div className="table-container" style={{ border: 'none' }}>
              <table>
                <thead>
                  <tr>
                    <th>Filename</th>
                    <th>Type</th>
                    <th>Size</th>
                    <th>Upload Date</th>
                    <th>Chunks</th>
                    <th>Status</th>
                  </tr>
                </thead>
                <tbody>
                  {documents.map(doc => (
                    <tr key={doc.id}>
                      <td style={{ fontWeight: 500 }}>{doc.filename}</td>
                      <td><span className="badge badge-neutral">{doc.file_type.toUpperCase()}</span></td>
                      <td>{formatNumber(Math.round(doc.file_size_bytes / 1024))} KB</td>
                      <td style={{ fontSize: 12 }}>{new Date(doc.upload_date).toLocaleDateString()}</td>
                      <td>{formatNumber(doc.num_chunks)}</td>
                      <td><StatusBadge status={doc.status} /></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )
        )}
      </div>
    </div>
  )
}
