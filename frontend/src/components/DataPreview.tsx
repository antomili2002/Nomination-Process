import { useState, useEffect } from 'react'
import { PivotTable } from './PivotTable'
import type { PivotTableData } from './PivotTable'

interface DataPreviewPayload {
  available_machines: string[]
  ev_monthly: PivotTableData[]
  ev_deltas:  PivotTableData[]
  iv_monthly: PivotTableData[]
  iv_deltas:  PivotTableData[]
  pp_monthly: PivotTableData[]
  pp_deltas:  PivotTableData[]
  iv_heat_monthly: PivotTableData[]
  iv_heat_deltas:  PivotTableData[]
  heat_prod_monthly: PivotTableData[]
  heat_prod_deltas:  PivotTableData[]
}

interface Props {
  uploadId: string
  ivChain: number[]
  evChain: number[]
}

type Tab = 'ev' | 'iv' | 'pp' | 'ivHeat' | 'heatProd'

export function DataPreview({ uploadId, ivChain, evChain }: Props) {
  const [data, setData] = useState<DataPreviewPayload | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [machine, setMachine] = useState<string>('__all__')
  const [activeTab, setActiveTab] = useState<Tab>('ev')
  const [showDeltas, setShowDeltas] = useState(true)

  async function fetchPreview(selectedMachine: string) {
    setLoading(true)
    setError(null)
    try {
      const body = {
        upload_id: uploadId,
        iv_chain: ivChain,
        ev_chain: evChain,
        selected_machines: selectedMachine === '__all__' ? null : [selectedMachine],
      }
      const res = await fetch('/api/reports/data-preview', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      })
      if (!res.ok) {
        const d = await res.json().catch(() => ({}))
        throw new Error((d as { detail?: string })?.detail ?? `Preview failed (${res.status})`)
      }
      const payload: DataPreviewPayload = await res.json()
      setData(payload)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Preview failed.')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchPreview(machine)
  }, [machine])

  const tabTables: Record<Tab, { monthly: PivotTableData[]; deltas: PivotTableData[] }> = data
    ? {
        ev: { monthly: data.ev_monthly, deltas: data.ev_deltas },
        iv: { monthly: data.iv_monthly, deltas: data.iv_deltas },
        pp: { monthly: data.pp_monthly, deltas: data.pp_deltas },
        ivHeat: { monthly: data.iv_heat_monthly, deltas: data.iv_heat_deltas },
        heatProd: { monthly: data.heat_prod_monthly, deltas: data.heat_prod_deltas },
      }
    : {
        ev: { monthly: [], deltas: [] },
        iv: { monthly: [], deltas: [] },
        pp: { monthly: [], deltas: [] },
        ivHeat: { monthly: [], deltas: [] },
        heatProd: { monthly: [], deltas: [] },
      }

  return (
    <div className="card" style={{ marginTop: 'var(--sp-6)' }}>
      {/* Header row */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: 'var(--sp-3)', marginBottom: 'var(--sp-4)' }}>
        <p className="section-label" style={{ margin: 0 }}>Data Preview</p>

        {/* Machine selector */}
        {data && (
          <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--sp-2)' }}>
            <label style={{ fontSize: 'var(--text-xs)', color: 'var(--clr-text-muted)', whiteSpace: 'nowrap' }}>
              MACHINE_NAME:
            </label>
            <select
              className="select"
              style={{ fontSize: 'var(--text-xs)', padding: '4px 8px' }}
              value={machine}
              onChange={e => setMachine(e.target.value)}
            >
              <option value="__all__">(All)</option>
              {data.available_machines.map(m => (
                <option key={m} value={m}>{m}</option>
              ))}
            </select>
          </div>
        )}
      </div>

      {loading && (
        <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--sp-2)', color: 'var(--clr-text-muted)', fontSize: 'var(--text-sm)', padding: 'var(--sp-4) 0' }}>
          <span className="spinner spinner--sm" aria-hidden="true" />
          Loading preview…
        </div>
      )}

      {error && (
        <div className="alert alert--error" role="alert">{error}</div>
      )}

      {data && !loading && (
        <>
          {/* Tabs */}
          <div style={{ display: 'flex', gap: 'var(--sp-1)', marginBottom: 'var(--sp-4)', borderBottom: '1px solid var(--clr-border)', paddingBottom: 0 }}>
            {([
              ['ev', 'EV'],
              ['iv', 'IV'],
              ['pp', 'Power Position'],
              ['ivHeat', 'IV incl. Heat'],
              ['heatProd', 'Heat Production'],
            ] as const).map(([tab, label]) => (
              <button
                key={tab}
                onClick={() => setActiveTab(tab)}
                style={{
                  background: 'none', border: 'none', cursor: 'pointer',
                  padding: 'var(--sp-2) var(--sp-3)',
                  fontSize: 'var(--text-sm)', fontWeight: activeTab === tab ? 'var(--weight-medium)' : 'normal',
                  color: activeTab === tab ? 'var(--clr-blue)' : 'var(--clr-text-muted)',
                  borderBottom: activeTab === tab ? '2px solid var(--clr-blue)' : '2px solid transparent',
                  marginBottom: -1,
                }}
              >
                {label}
              </button>
            ))}
          </div>

          {/* Monthly tables */}
          <div style={{ marginBottom: 'var(--sp-2)' }}>
            <p style={{ fontSize: 'var(--text-xs)', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.06em', color: 'var(--clr-text-muted)', marginBottom: 'var(--sp-3)' }}>
              Base &amp; Final
            </p>
            {tabTables[activeTab].monthly.map((t, i) => (
              <PivotTable key={i} table={t} isDelta={false} />
            ))}
          </div>

          {/* Delta tables */}
          {tabTables[activeTab].deltas.length > 0 && (
            <div>
              <button
                onClick={() => setShowDeltas(v => !v)}
                style={{ background: 'none', border: 'none', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 'var(--sp-2)', padding: 0, marginBottom: 'var(--sp-3)' }}
              >
                <span style={{ fontSize: 'var(--text-xs)', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.06em', color: 'var(--clr-text-muted)' }}>
                  Delta Tables
                </span>
                <span style={{ fontSize: 10, color: 'var(--clr-text-muted)' }}>{showDeltas ? '▲' : '▼'}</span>
              </button>
              {showDeltas && tabTables[activeTab].deltas.map((t, i) => (
                <PivotTable key={i} table={t} isDelta={true} />
              ))}
            </div>
          )}
        </>
      )}
    </div>
  )
}
