import { useState } from 'react'

interface Props {
  onReset: () => void
}

export function ResultPage({ onReset }: Props) {
  const [downloading, setDownloading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function handleDownload() {
    setDownloading(true)
    setError(null)
    try {
      const res = await fetch('/api/reports/download/latest')
      if (!res.ok) throw new Error(`Download failed (${res.status})`)
      const blob = await res.blob()
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = 'scenario_delta_report.xlsx'
      document.body.appendChild(a)
      a.click()
      a.remove()
      URL.revokeObjectURL(url)
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Download failed.')
    } finally {
      setDownloading(false)
    }
  }

  return (
    <div className="page-container">
      <div className="page-header">
        <h1 className="page-title">Report Ready</h1>
        <p className="page-subtitle">
          Your scenario delta report has been generated. Download the Excel file below.
        </p>
      </div>

      <div className="card" style={{ textAlign: 'center', padding: 'var(--sp-16) var(--sp-8)' }}>
        {/* Success icon */}
        <svg
          width="64"
          height="64"
          viewBox="0 0 64 64"
          fill="none"
          xmlns="http://www.w3.org/2000/svg"
          style={{ margin: '0 auto var(--sp-5)' }}
          aria-hidden="true"
        >
          <circle cx="32" cy="32" r="30" fill="var(--clr-success-light)" />
          <path
            d="M20 32l9 9 15-15"
            stroke="var(--clr-success)"
            strokeWidth="3"
            strokeLinecap="round"
            strokeLinejoin="round"
          />
        </svg>

        <h2 style={{ fontSize: 'var(--text-xl)', fontWeight: 'var(--weight-semibold)', marginBottom: 'var(--sp-2)' }}>
          Generation complete
        </h2>
        <p style={{ color: 'var(--clr-text-secondary)', fontSize: 'var(--text-sm)', marginBottom: 'var(--sp-8)' }}>
          The report contains monthly pivot tables and delta comparison sheets.
        </p>

        <div style={{ display: 'flex', gap: 'var(--sp-4)', justifyContent: 'center', flexWrap: 'wrap' }}>
          <button
            className="btn btn--primary btn--lg"
            onClick={handleDownload}
            disabled={downloading}
          >
            {downloading ? (
              <><span className="spinner spinner--sm" aria-hidden="true" />Downloading…</>
            ) : (
              <>
                <svg width="18" height="18" viewBox="0 0 18 18" fill="none" aria-hidden="true">
                  <path d="M9 2v10M5 8l4 4 4-4M3 14h12" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" />
                </svg>
                Download Excel Report
              </>
            )}
          </button>
          <button className="btn btn--ghost btn--lg" onClick={onReset}>
            ← New Report
          </button>
        </div>

        {error && (
          <div className="alert alert--error" style={{ marginTop: 'var(--sp-5)', textAlign: 'left' }} role="alert">
            {error}
          </div>
        )}
      </div>

      {/* Output sheet summary */}
      <div className="card card--flat">
        <p className="section-label" style={{ marginBottom: 'var(--sp-4)' }}>Generated sheets</p>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))', gap: 'var(--sp-3)' }}>
          {[
            { name: 'EV_month',          desc: 'Monthly EV pivot (base + final)' },
            { name: 'Power_pos_month',    desc: 'Monthly POWER_POS pivot (IV)' },
            { name: 'IV_month',           desc: 'Monthly INTRINSIC_VALUE pivot' },
            { name: 'IV_sheet_general',   desc: '3 stacked IV delta tables' },
            { name: 'EV_sheet',           desc: '3 side-by-side EV delta tables' },
          ].map(sheet => (
            <div
              key={sheet.name}
              style={{
                padding: 'var(--sp-3) var(--sp-4)',
                background: 'var(--clr-bg)',
                borderRadius: 'var(--radius-md)',
                border: '1px solid var(--clr-border)',
              }}
            >
              <p style={{ fontWeight: 'var(--weight-medium)', fontSize: 'var(--text-sm)', marginBottom: 2 }}>
                {sheet.name}
              </p>
              <p style={{ fontSize: 'var(--text-xs)', color: 'var(--clr-text-muted)' }}>
                {sheet.desc}
              </p>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
