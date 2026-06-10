import { useRef, useState } from 'react'
import type { UploadContext } from '../App'

interface Props {
  onSuccess: (ctx: UploadContext) => void
}

// Accepted MIME types for file picker
const ACCEPT = '.xlsx,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'

export function UploadPage({ onSuccess }: Props) {
  const inputRef = useRef<HTMLInputElement>(null)
  const [dragOver, setDragOver] = useState(false)
  const [file, setFile] = useState<File | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // ── helpers ────────────────────────────────────────────
  function validate(f: File): string | null {
    if (!f.name.endsWith('.xlsx')) return 'Only .xlsx files are supported.'
    if (f.size > 150 * 1024 * 1024) return 'File is too large (max 150 MB).'
    return null
  }

  function pickFile(f: File) {
    const err = validate(f)
    if (err) { setError(err); return }
    setError(null)
    setFile(f)
  }

  // ── drag & drop ─────────────────────────────────────────
  function onDragOver(e: React.DragEvent) {
    e.preventDefault()
    setDragOver(true)
  }
  function onDragLeave() { setDragOver(false) }
  function onDrop(e: React.DragEvent) {
    e.preventDefault()
    setDragOver(false)
    const f = e.dataTransfer.files[0]
    if (f) pickFile(f)
  }
  function onInputChange(e: React.ChangeEvent<HTMLInputElement>) {
    const f = e.target.files?.[0]
    if (f) pickFile(f)
  }

  // ── upload ──────────────────────────────────────────────
  async function handleUpload() {
    if (!file) return
    setLoading(true)
    setError(null)

    try {
      const form = new FormData()
      form.append('file', file)

      const res = await fetch('/api/upload', { method: 'POST', body: form })
      if (!res.ok) {
        const body = await res.json().catch(() => ({}))
        throw new Error(body?.detail ?? `Upload failed (${res.status})`)
      }
      const data = await res.json()
      onSuccess({
        uploadId: data.upload_id,
        fileName: data.file_name,
        scenarios: data.scenarios.map((s: {
          index: number
          scenario_name: string
          scenario_id: number
          market_area: string
          scenario_type: string
          status: string
          role: string | null
        }) => ({
          index: s.index,
          scenarioName: s.scenario_name,
          scenarioId: s.scenario_id,
          marketArea: s.market_area,
          scenarioType: s.scenario_type,
          status: s.status,
          role: s.role,
        })),
        machines: data.machines,
      })
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Upload failed.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="page-container">
      {/* Page header */}
      <div className="page-header">
        <h1 className="page-title">Upload Excel Workbook</h1>
        <p className="page-subtitle">
          Upload the scenario export file that contains an <strong>Info</strong> sheet and a{' '}
          <strong>Data</strong> sheet. The tool will extract available scenarios and machine names.
        </p>
      </div>

      {/* Upload card */}
      <div className="card">
        {/* Drop zone */}
        <div
          className={['upload-zone', dragOver ? 'upload-zone--drag-over' : ''].join(' ')}
          onDragOver={onDragOver}
          onDragLeave={onDragLeave}
          onDrop={onDrop}
          onClick={() => inputRef.current?.click()}
          role="button"
          tabIndex={0}
          onKeyDown={(e) => e.key === 'Enter' && inputRef.current?.click()}
          aria-label="Click or drag and drop to select an Excel file"
        >
          {/* Cloud-upload icon */}
          <svg
            className="upload-zone__icon"
            viewBox="0 0 52 52"
            fill="none"
            xmlns="http://www.w3.org/2000/svg"
            aria-hidden="true"
          >
            <path
              d="M36 34l-10-10-10 10M26 24v20"
              stroke="currentColor"
              strokeWidth="2.5"
              strokeLinecap="round"
              strokeLinejoin="round"
            />
            <path
              d="M44.2 40a9 9 0 000-18h-1.26A16 16 0 108 36.8"
              stroke="currentColor"
              strokeWidth="2.5"
              strokeLinecap="round"
              strokeLinejoin="round"
            />
          </svg>

          {file ? (
            <>
              <p className="upload-zone__title" style={{ color: 'var(--clr-success)' }}>
                {file.name}
              </p>
              <p className="upload-zone__hint">
                {(file.size / 1024 / 1024).toFixed(1)} MB · Click to replace
              </p>
            </>
          ) : (
            <>
              <p className="upload-zone__title">Drop your Excel file here</p>
              <p className="upload-zone__hint">or click to browse</p>
              <div className="upload-zone__types">
                <span className="badge badge--navy">.xlsx</span>
                <span className="badge badge--navy">max 150 MB</span>
              </div>
            </>
          )}
        </div>

        <input
          ref={inputRef}
          type="file"
          accept={ACCEPT}
          style={{ display: 'none' }}
          onChange={onInputChange}
        />

        {/* Error */}
        {error && (
          <div
            className="alert alert--error"
            style={{ marginTop: 'var(--sp-4)' }}
            role="alert"
          >
            <svg width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden="true">
              <circle cx="8" cy="8" r="7" stroke="currentColor" strokeWidth="1.5" />
              <path d="M8 5v3.5M8 10.5v.5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
            </svg>
            {error}
          </div>
        )}

        {/* Action */}
        <div style={{ marginTop: 'var(--sp-5)', display: 'flex', justifyContent: 'flex-end' }}>
          <button
            className="btn btn--primary btn--lg"
            onClick={handleUpload}
            disabled={!file || loading}
          >
            {loading ? (
              <>
                <span className="spinner spinner--sm" aria-hidden="true" />
                Uploading…
              </>
            ) : (
              <>
                Upload &amp; Extract Scenarios
                <svg width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden="true">
                  <path d="M3 8h10M9 4l4 4-4 4" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" />
                </svg>
              </>
            )}
          </button>
        </div>
      </div>

      {/* Info note */}
      <div className="alert alert--info" role="note">
        <svg width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden="true">
          <circle cx="8" cy="8" r="7" stroke="currentColor" strokeWidth="1.5" />
          <path d="M8 7v5M8 5v.5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
        </svg>
        <span>
          Expected sheets: <strong>Info</strong> (scenario metadata) and <strong>Data</strong>{' '}
          (scenario results with columns SCENARIO_ID, SCENARIO_NAME, OUTPUT_TYPE, YEAR, MONTH,
          TARIFF, MACHINE_NAME, and metric columns).
          {' '}For automatic chain ordering, name scenarios with numeric prefixes:
          {' '}<strong>0_Base_IV</strong>, <strong>1_Intermediate_IV</strong>,
          {' '}<strong>2_Final_IV</strong> and the same pattern for EV.
        </span>
      </div>

      {/* Info note */}
      <div className="alert alert--info" role="note">
        <svg width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden="true">
          <circle cx="8" cy="8" r="7" stroke="currentColor" strokeWidth="1.5" />
          <path d="M8 7v5M8 5v.5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
        </svg>
        <span>
          Expected naming convention:
          {' '}For automatic chain ordering, name scenarios with numeric prefixes:
          {' '}<strong>0_Base_IV</strong>, <strong>1_Intermediate_IV</strong>,
          {' '}<strong>2_Final_IV</strong> and the same pattern for EV.
        </span>
      </div>
    </div>
  )
}
