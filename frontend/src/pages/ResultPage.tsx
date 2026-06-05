import React, { useEffect, useRef, useState } from 'react'
import type { ReportData, YearlyDeltaTable } from '../App'
import type { PivotTableData } from '../components/PivotTable'

interface Props {
  reportData: ReportData
  onReset: () => void
}

type SectionId = 'ev-monthly' | 'ev-deltas' | 'iv-monthly' | 'iv-deltas' | 'pp-monthly' | 'pp-deltas'

interface Section {
  id: SectionId
  label: string
  metric: string
  group: 'EV' | 'IV' | 'Power Position'
  isDeltas: boolean
}

const SECTIONS: Section[] = [
  { id: 'ev-monthly', label: 'Monthly',  metric: 'EXTRINSIC_VALUE',       group: 'EV',             isDeltas: false },
  { id: 'ev-deltas',  label: 'Deltas',   metric: 'EXTRINSIC_VALUE',       group: 'EV',             isDeltas: true  },
  { id: 'iv-monthly', label: 'Monthly',  metric: 'INTRINSIC_VALUE__CUR',  group: 'IV',             isDeltas: false },
  { id: 'iv-deltas',  label: 'Deltas',   metric: 'INTRINSIC_VALUE__CUR',  group: 'IV',             isDeltas: true  },
  { id: 'pp-monthly', label: 'Monthly',  metric: 'POWER_POS__GWH',        group: 'Power Position', isDeltas: false },
  { id: 'pp-deltas',  label: 'Deltas',   metric: 'POWER_POS__GWH',        group: 'Power Position', isDeltas: true  },
]

function getMonthlyTables(d: ReportData, id: SectionId): PivotTableData[] {
  switch (id) {
    case 'ev-monthly': return d.evMonthly
    case 'iv-monthly': return d.ivMonthly
    case 'pp-monthly': return d.ppMonthly
    default: return []
  }
}

function getYearlyDeltas(d: ReportData, id: SectionId): YearlyDeltaTable[] {
  switch (id) {
    case 'ev-deltas': return d.evDeltas
    case 'iv-deltas': return d.ivDeltas
    case 'pp-deltas': return d.ppDeltas
    default: return []
  }
}

function getSectionCount(d: ReportData, id: SectionId): number {
  const sec = SECTIONS.find(s => s.id === id)!
  return sec.isDeltas ? getYearlyDeltas(d, id).length : getMonthlyTables(d, id).length
}

const FMT3 = { minimumFractionDigits: 3, maximumFractionDigits: 3 } as const

function fmtN(v: number): string {
  if (Math.abs(v) < 0.005) return '\u2014'
  return Math.round(v).toLocaleString('en-GB')
}

// Used by ExcelPivotSection (monthly tables, rounded integers)
function fmtDelta(v: number): { text: string; color?: string } {
  if (Math.abs(v) < 0.005) return { text: '\u2014' }
  const abs = Math.round(Math.abs(v)).toLocaleString('en-GB')
  if (v < 0) return { text: `(${abs})`, color: '#c0392b' }
  return { text: abs, color: 'var(--clr-blue)' }
}

function fmtY(v: number): string {
  if (Math.abs(v) < 0.0005) return '\u2014'
  return v.toLocaleString('en-GB', FMT3)
}

function fmtDif(v: number): { text: string; color?: string } {
  if (Math.abs(v) < 0.0005) return { text: '' }
  const s = Math.abs(v).toLocaleString('en-GB', FMT3)
  if (v < 0) return { text: `-${s}`, color: '#c0392b' }
  return { text: s, color: 'var(--clr-blue)' }
}

// Yearly-aggregate delta table (matches Excel screenshot format) 

function YearlyDeltaSection({ tables, metric }: { tables: YearlyDeltaTable[]; metric: string }) {
  if (tables.length === 0)
    return <p style={{ color: 'var(--clr-text-muted)', fontStyle: 'italic' }}>No data available.</p>

  const TH: React.CSSProperties = {
    padding: '5px 10px', fontWeight: 700, fontSize: 'var(--text-xs)',
    background: '#d9e1f2', borderBottom: '2px solid #8ea9d8',
    whiteSpace: 'nowrap', borderRight: '1px solid #b8c9e0',
  }
  const TD: React.CSSProperties = {
    padding: '3px 10px', textAlign: 'right', fontVariantNumeric: 'tabular-nums',
    fontSize: 'var(--text-xs)', borderRight: '1px solid var(--clr-border)', whiteSpace: 'nowrap',
  }
  const TDL: React.CSSProperties = { ...TD, textAlign: 'left', fontVariantNumeric: 'normal' }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--sp-5)' }}>
      {tables.map((t, ti) => {
        return (
          <div key={ti}>
            {/* Pair type badge */}
            {t.pair_type && (
              <div style={{ marginBottom: 'var(--sp-2)', display: 'flex', alignItems: 'center', gap: 'var(--sp-2)' }}>
                <span style={{
                  fontSize: 9, padding: '2px 8px', borderRadius: 3,
                  background: t.pair_type === 'cumulative' ? 'var(--clr-blue)' : '#6c757d', color: '#fff',
                  fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.06em',
                }}>
                  {t.pair_type === 'cumulative' ? 'Cumulative' : `Step ${t.step_number}`}
                </span>
                <span style={{ fontSize: 'var(--text-xs)', color: 'var(--clr-text-muted)' }}>
                  {t.right_name} vs {t.left_name}
                </span>
              </div>
            )}

            <div className="table-wrapper" style={{ overflowX: 'auto', borderRadius: 'var(--radius-md)', border: '1px solid var(--clr-border)' }}>
              <table style={{ borderCollapse: 'collapse', minWidth: 'max-content', width: '100%' }}>
                <thead>
                  <tr>
                    <th style={{ ...TH, textAlign: 'left', minWidth: 260 }}>Row Labels</th>
                    <th style={{ ...TH, minWidth: 140 }}>{t.left_name}</th>
                    <th style={{ ...TH, minWidth: 140 }}>{t.right_name}</th>
                    <th style={{ ...TH, minWidth: 140 }}>Dif of {metric}</th>
                  </tr>
                </thead>
                <tbody>
                  {t.rows.map((row, ri) => {
                    const { text, color } = fmtDif(row.delta)
                    return (
                      <tr key={ri} style={{ background: ri % 2 === 0 ? '#fff' : '#fafafa' }}>
                        <td style={{ ...TDL, paddingLeft: 24 }}>{row.year}</td>
                        <td style={TD}>{fmtY(row.left_value)}</td>
                        <td style={TD}>{fmtY(row.right_value)}</td>
                        <td style={{ ...TD, color }}>{text}</td>
                      </tr>
                    )
                  })}

                  {/* Grand Total */}
                  <tr style={{ background: '#b8cce4', fontWeight: 700, borderTop: '2px solid #8ea9d8' }}>
                    <td style={{ ...TDL, paddingLeft: 10 }}>Grand Total</td>
                    <td style={{ ...TD, fontWeight: 700 }}>{fmtY(t.left_total)}</td>
                    <td style={{ ...TD, fontWeight: 700 }}>{fmtY(t.right_total)}</td>
                    <td style={{ ...TD, fontWeight: 700, color: t.delta_total < 0 ? '#c0392b' : 'var(--clr-blue)' }}>
                      {fmtDif(t.delta_total).text}
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>
        )
      })}
    </div>
  )
}

function ExcelPivotSection({ tables, isDelta }: { tables: PivotTableData[]; isDelta: boolean }) {
  if (tables.length === 0) return <p style={{ color: 'var(--clr-text-muted)', fontStyle: 'italic' }}>No data available.</p>

  const months = tables[0].months
  const colTotals = months.map((_, mi) =>
    tables.flatMap(t => t.rows).reduce((s, r) => s + (r.values[mi] ?? 0), 0)
  )
  const overallTotal = colTotals.reduce((s, v) => s + v, 0)

  const TH: React.CSSProperties = {
    padding: '5px 10px', textAlign: 'right', fontWeight: 700, fontSize: 'var(--text-xs)',
    background: '#d9e1f2', borderBottom: '2px solid #8ea9d8', whiteSpace: 'nowrap',
    borderRight: '1px solid #b8c9e0',
  }
  const TD: React.CSSProperties = {
    padding: '3px 10px', textAlign: 'right', fontVariantNumeric: 'tabular-nums',
    fontSize: 'var(--text-xs)', borderRight: '1px solid var(--clr-border)', whiteSpace: 'nowrap',
  }
  const TDL: React.CSSProperties = { ...TD, textAlign: 'left', minWidth: 60, fontVariantNumeric: 'normal' }

  function valTD(v: number, bold = false, bg?: string): React.ReactNode {
    if (isDelta) {
      const { text, color } = fmtDelta(v)
      return <td style={{ ...TD, color, fontWeight: bold ? 700 : undefined, background: bg }}>{text}</td>
    }
    return <td style={{ ...TD, fontWeight: bold ? 700 : undefined, background: bg }}>{fmtN(v)}</td>
  }

  return (
    <div className="table-wrapper" style={{ overflowX: 'auto', borderRadius: 'var(--radius-md)', border: '1px solid var(--clr-border)' }}>
      <table style={{ borderCollapse: 'collapse', minWidth: 'max-content', width: '100%' }}>
        <thead>
          <tr>
            <th style={{ ...TH, textAlign: 'left', minWidth: 56, borderRight: '1px solid #b8c9e0' }}>Year</th>
            <th style={{ ...TH, textAlign: 'left', minWidth: 72, borderRight: '1px solid #b8c9e0' }}>Tariff</th>
            {months.map(m => (
              <th key={m} style={{ ...TH, minWidth: 72 }}>{m}</th>
            ))}
            <th style={{ ...TH, minWidth: 90, borderLeft: '2px solid #8ea9d8' }}>Grand Total</th>
          </tr>
        </thead>
        <tbody>
          {tables.map((table, ti) => {
            const years = [...new Set(table.rows.map(r => r.year))].sort()
            const scMonthTotals = months.map((_, mi) =>
              table.rows.reduce((s, r) => s + (r.values[mi] ?? 0), 0)
            )
            const scGrandTotal = scMonthTotals.reduce((s, v) => s + v, 0)

            return (
              <React.Fragment key={ti}>
                <tr>
                  <td colSpan={months.length + 3} style={{
                    padding: '5px 10px', fontWeight: 700, fontSize: 'var(--text-xs)',
                    background: isDelta ? '#fdecea' : '#ebf3fb',
                    borderTop: ti > 0 ? '2px solid var(--clr-border)' : undefined,
                    color: isDelta ? '#c0392b' : 'var(--clr-blue)',
                  }}>
                    {table.pair_type && (
                      <span style={{
                        display: 'inline-block', fontSize: 9, padding: '1px 6px', borderRadius: 3, marginRight: 8,
                        background: table.pair_type === 'cumulative' ? 'var(--clr-blue)' : '#6c757d', color: '#fff',
                      }}>
                        {table.pair_type === 'cumulative' ? 'Cumulative' : `Step ${table.step_number}`}
                      </span>
                    )}
                    {table.title}
                  </td>
                </tr>

                {years.map(year => {
                  const yearRows = table.rows.filter(r => r.year === year)
                  const yearMTotals = months.map((_, mi) =>
                    yearRows.reduce((s, r) => s + (r.values[mi] ?? 0), 0)
                  )
                  const yearTotal = yearMTotals.reduce((s, v) => s + v, 0)

                  return (
                    <React.Fragment key={year}>
                      {yearRows.map((row, ri) => (
                        <tr key={ri} style={{ background: ri % 2 === 0 ? '#fff' : '#fafafa' }}>
                          <td style={{ ...TDL, paddingLeft: 16, borderRight: '1px solid var(--clr-border)' }}>
                            {ri === 0 ? <strong>{year}</strong> : ''}
                          </td>
                          <td style={{ ...TDL, paddingLeft: 24, textTransform: 'capitalize' }}>{row.tariff}</td>
                          {row.values.map((v, mi) => {
                            if (isDelta) {
                              const { text, color } = fmtDelta(v)
                              return <td key={mi} style={{ ...TD, color }}>{text}</td>
                            }
                            return <td key={mi} style={TD}>{fmtN(v)}</td>
                          })}
                          {valTD(row.values.reduce((s, v) => s + v, 0), false, '#edf2f7')}
                        </tr>
                      ))}

                      {yearRows.length > 1 && (
                        <tr style={{ background: '#edf2f7', fontWeight: 600 }}>
                          <td style={{ ...TDL, paddingLeft: 16, color: 'var(--clr-text-muted)', fontSize: 10 }}>{year} Total</td>
                          <td style={TDL} />
                          {yearMTotals.map((v, i) => {
                            if (isDelta) {
                              const { text, color } = fmtDelta(v)
                              return <td key={i} style={{ ...TD, color, fontWeight: 600 }}>{text}</td>
                            }
                            return <td key={i} style={{ ...TD, fontWeight: 600 }}>{fmtN(v)}</td>
                          })}
                          {valTD(yearTotal, true, '#dce3ed')}
                        </tr>
                      )}
                    </React.Fragment>
                  )
                })}

                <tr style={{ background: '#dce3ed', fontWeight: 700, borderBottom: '1px solid #b8c9e0' }}>
                  <td colSpan={2} style={{ ...TDL, paddingLeft: 10, color: isDelta ? '#c0392b' : 'var(--clr-blue)' }}>
                    {table.title} Total
                  </td>
                  {scMonthTotals.map((v, i) => {
                    if (isDelta) {
                      const { text, color } = fmtDelta(v)
                      return <td key={i} style={{ ...TD, color, fontWeight: 700 }}>{text}</td>
                    }
                    return <td key={i} style={{ ...TD, fontWeight: 700 }}>{fmtN(v)}</td>
                  })}
                  {valTD(scGrandTotal, true)}
                </tr>
              </React.Fragment>
            )
          })}

          {tables.length > 1 && (
            <tr style={{ background: '#b8cce4', fontWeight: 700, borderTop: '2px solid #8ea9d8' }}>
              <td colSpan={2} style={{ ...TDL, paddingLeft: 10 }}>Grand Total</td>
              {colTotals.map((v, i) => {
                if (isDelta) {
                  const { text, color } = fmtDelta(v)
                  return <td key={i} style={{ ...TD, color, fontWeight: 700 }}>{text}</td>
                }
                return <td key={i} style={{ ...TD, fontWeight: 700 }}>{fmtN(v)}</td>
              })}
              {valTD(overallTotal, true)}
            </tr>
          )}
        </tbody>
      </table>
    </div>
  )
}

// Cache helpers 
function cacheKey(sel: string[] | null, all: string[]): string {
  if (!sel || sel.length === all.length) return 'ALL'
  return JSON.stringify([...sel].sort())
}

function mapPayload(p: Record<string, unknown>, base: ReportData): ReportData {
  return {
    reportId:        p.report_id as string,
    uploadId:        base.uploadId,
    ivChain:         base.ivChain,
    evChain:         base.evChain,
    machines:        base.machines,
    selectedMachines: base.selectedMachines,  // overwritten by caller
    evMonthly: p.ev_monthly as PivotTableData[],
    evDeltas:  p.ev_deltas  as ReportData['evDeltas'],
    ivMonthly: p.iv_monthly as PivotTableData[],
    ivDeltas:  p.iv_deltas  as ReportData['ivDeltas'],
    ppMonthly: p.pp_monthly as PivotTableData[],
    ppDeltas:  p.pp_deltas  as ReportData['ppDeltas'],
  }
}

export function ResultPage({ reportData, onReset }: Props) {
  const { uploadId, ivChain, evChain, machines } = reportData

  // ── Section navigation ───────────────────────────────────────────────────
  const [activeId, setActiveId] = useState<SectionId>('ev-monthly')
  const activeSection = SECTIONS.find(s => s.id === activeId)!
  const groups = ['EV', 'IV', 'Power Position'] as const

  // ── Machine filter + cache ───────────────────────────────────────────────
  // activeData is what gets rendered; initialised from the passed-in reportData.
  const [activeData, setActiveData]     = useState<ReportData>(reportData)
  const [activeKey, setActiveKey]       = useState<string>(() => cacheKey(reportData.selectedMachines, machines))

  // Cache: cacheKey → ReportData.  Pre-seed with the initial result.
  const [cache, setCache] = useState<Map<string, ReportData>>(() => {
    const m = new Map<string, ReportData>()
    m.set(cacheKey(reportData.selectedMachines, machines), reportData)
    return m
  })

  const [recomputing, setRecomputing]   = useState(false)
  const [recomputeError, setRecomputeError] = useState<string | null>(null)

  // ── Download state ───────────────────────────────────────────────────────
  const [downloading, setDownloading] = useState(false)

  // Machine popover
  const [showMenu, setShowMenu]         = useState(false)
  const [pendingSel, setPendingSel]     = useState<Set<string>>(
    () => new Set(reportData.selectedMachines ?? machines)
  )
  const menuRef = useRef<HTMLDivElement>(null)

  // Close popover on outside click
  useEffect(() => {
    if (!showMenu) return
    function onDown(e: MouseEvent) {
      if (menuRef.current && !menuRef.current.contains(e.target as Node))
        setShowMenu(false)
    }
    document.addEventListener('mousedown', onDown)
    return () => document.removeEventListener('mousedown', onDown)
  }, [showMenu])

  function togglePending(m: string) {
    setPendingSel(prev => {
      const next = new Set(prev)
      if (next.has(m)) { if (next.size > 1) next.delete(m) }
      else next.add(m)
      return next
    })
  }

  async function handleDownload() {
    setDownloading(true)
    try {
      const resp = await fetch('/api/reports/export', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          upload_id: activeData.uploadId,
          iv_chain:  activeData.ivChain,
          ev_chain:  activeData.evChain,
          selected_machines: activeData.selectedMachines,
        }),
      })
      if (!resp.ok) {
        const d = await resp.json().catch(() => ({}))
        throw new Error((d as { detail?: string })?.detail ?? `Download failed (${resp.status})`)
      }
      // Extract filename from Content-Disposition header if present
      const disposition = resp.headers.get('content-disposition') ?? ''
      const match = disposition.match(/filename="([^"]+)"/)
      const filename = match ? match[1] : `scenario_report_${Date.now()}.xlsx`

      const blob = await resp.blob()
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = filename
      document.body.appendChild(a)
      a.click()
      a.remove()
      URL.revokeObjectURL(url)
    } catch (e) {
      alert(e instanceof Error ? e.message : 'Download failed.')
    } finally {
      setDownloading(false)
    }
  }

  async function applyMachineFilter() {
    const sel = pendingSel.size === machines.length ? null : [...pendingSel].sort()
    const key = cacheKey(sel, machines)
    setShowMenu(false)
    setRecomputeError(null)

    if (cache.has(key)) {
      setActiveData(cache.get(key)!)
      setActiveKey(key)
      return
    }

    setRecomputing(true)
    try {
      const resp = await fetch('/api/reports/generate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ upload_id: uploadId, iv_chain: ivChain, ev_chain: evChain, selected_machines: sel }),
      })
      if (!resp.ok) {
        const d = await resp.json().catch(() => ({}))
        throw new Error((d as { detail?: string })?.detail ?? `Recompute failed (${resp.status})`)
      }
      const p = await resp.json()
      const newData: ReportData = { ...mapPayload(p, reportData), selectedMachines: sel }
      setCache(prev => new Map(prev).set(key, newData))
      setActiveData(newData)
      setActiveKey(key)
    } catch (e) {
      setRecomputeError(e instanceof Error ? e.message : 'Recompute failed.')
    } finally {
      setRecomputing(false)
    }
  }

  // Derived: is any filter active?
  const isFiltered = activeKey !== 'ALL'
  const activeMachineCount = isFiltered ? JSON.parse(activeKey).length : machines.length

  return (
    <div style={{ display: 'flex', gap: 0, minHeight: 'calc(100vh - 120px)', alignItems: 'flex-start' }}>
      {/* ── Sidebar ── */}
      <aside style={{
        width: 220, flexShrink: 0,
        borderRight: '1px solid var(--clr-border)', alignSelf: 'stretch',
        background: '#fff', position: 'sticky', top: 72,
        maxHeight: 'calc(100vh - 72px)', overflowY: 'auto',
      }}>
        <div style={{ padding: 'var(--sp-4)', borderBottom: '2px solid var(--clr-blue)' }}>
          <p style={{ fontSize: 'var(--text-xs)', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.08em', color: 'var(--clr-blue)', margin: 0 }}>
            Report Tables
          </p>
        </div>

        {groups.map(group => {
          const groupSections = SECTIONS.filter(s => s.group === group)
          return (
            <div key={group} style={{ borderBottom: '1px solid var(--clr-border)' }}>
              <p style={{ margin: 0, padding: '8px 16px 4px', fontSize: 9, fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.1em', color: 'var(--clr-text-muted)' }}>
                {group}
              </p>
              {groupSections.map(sec => {
                const count = getSectionCount(activeData, sec.id)
                const isActive = activeId === sec.id
                return (
                  <button
                    key={sec.id}
                    type="button"
                    onClick={() => setActiveId(sec.id)}
                    style={{
                      display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                      width: '100%', padding: '7px 16px', border: 'none', textAlign: 'left',
                      cursor: 'pointer', fontSize: 'var(--text-xs)',
                      background: isActive ? 'var(--clr-blue)' : 'transparent',
                      color: isActive ? '#fff' : 'var(--clr-text)',
                      fontWeight: isActive ? 700 : 'normal',
                      borderLeft: isActive ? '3px solid #005fa3' : '3px solid transparent',
                      transition: 'all 0.1s',
                    }}
                  >
                    <span>{sec.label}</span>
                    <span style={{
                      fontSize: 9, padding: '1px 5px', borderRadius: 10,
                      background: isActive ? 'rgba(255,255,255,0.25)' : 'var(--clr-bg)',
                      color: isActive ? '#fff' : 'var(--clr-text-muted)',
                    }}>
                      {count}
                    </span>
                  </button>
                )
              })}
            </div>
          )
        })}

        <div style={{ padding: 'var(--sp-4)' }}>
          <button className="btn btn--ghost btn--sm" onClick={onReset} style={{ width: '100%' }}>
            ← New Report
          </button>
        </div>
      </aside>

      {/* ── Main content ── */}
      <div style={{ flex: 1, minWidth: 0, padding: 'var(--sp-6)', display: 'flex', flexDirection: 'column', gap: 'var(--sp-4)' }}>

        {/* Header row */}
        <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: 'var(--sp-4)' }}>
          <div>
            <h2 style={{ fontSize: 'var(--text-lg)', fontWeight: 'var(--weight-semibold)', margin: 0 }}>
              {activeSection.group} — {activeSection.label}
            </h2>
            <p style={{ fontSize: 'var(--text-xs)', color: 'var(--clr-text-muted)', marginTop: 4 }}>
              Sum of <code style={{ background: 'var(--clr-bg)', padding: '1px 4px', borderRadius: 3 }}>{activeSection.metric}</code>
              {' · '}{getSectionCount(activeData, activeId)} table{getSectionCount(activeData, activeId) !== 1 ? 's' : ''}
              {isFiltered && (
                <span style={{ marginLeft: 8, padding: '1px 7px', borderRadius: 10, background: 'var(--clr-blue-light)', color: 'var(--clr-blue)', fontWeight: 600 }}>
                  {activeMachineCount}/{machines.length} machines
                </span>
              )}
            </p>
          </div>

          {/* Action buttons */}
          <div style={{ display: 'flex', gap: 'var(--sp-2)', flexShrink: 0, alignItems: 'center' }}>
            {/* Machine filter button + popover */}
            <div style={{ position: 'relative' }} ref={menuRef}>
              <button
                className="btn btn--ghost btn--sm"
                onClick={() => {
                  setPendingSel(new Set(isFiltered ? JSON.parse(activeKey) as string[] : machines))
                  setShowMenu(v => !v)
                }}
                style={{
                  borderColor: isFiltered ? 'var(--clr-blue)' : undefined,
                  color: isFiltered ? 'var(--clr-blue)' : undefined,
                  fontWeight: isFiltered ? 700 : undefined,
                }}
              >
                ⊙ {isFiltered ? `Machines (${activeMachineCount}/${machines.length})` : 'Machines (All)'}
              </button>

              {showMenu && (
                <div style={{
                  position: 'absolute', top: 'calc(100% + 6px)', right: 0, zIndex: 200,
                  background: '#fff', border: '1px solid var(--clr-border)',
                  borderRadius: 'var(--radius-md)', boxShadow: '0 6px 24px rgba(0,0,0,0.13)',
                  padding: 'var(--sp-4)', minWidth: 300,
                }}>
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 'var(--sp-3)' }}>
                    <p style={{ margin: 0, fontWeight: 700, fontSize: 'var(--text-sm)' }}>Machine Filter</p>
                    <div style={{ display: 'flex', gap: 'var(--sp-1)' }}>
                      <button
                        className="btn btn--ghost btn--sm"
                        onClick={() => setPendingSel(new Set(machines))}
                        disabled={pendingSel.size === machines.length}
                      >All</button>
                      <button
                        className="btn btn--ghost btn--sm"
                        onClick={() => setPendingSel(new Set([machines[0]]))}
                        disabled={pendingSel.size === 1}
                      >Clear</button>
                    </div>
                  </div>

                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: 'var(--sp-2)', marginBottom: 'var(--sp-4)', maxHeight: 200, overflowY: 'auto' }}>
                    {machines.map(m => {
                      const sel = pendingSel.has(m)
                      return (
                        <button
                          key={m}
                          type="button"
                          onClick={() => togglePending(m)}
                          style={{
                            padding: '4px 12px', borderRadius: 'var(--radius-md)', cursor: 'pointer',
                            fontSize: 'var(--text-xs)', fontWeight: sel ? 600 : 'normal',
                            background: sel ? 'var(--clr-blue)' : 'var(--clr-bg)',
                            color: sel ? '#fff' : 'var(--clr-text-muted)',
                            border: `1px solid ${sel ? 'var(--clr-blue)' : 'var(--clr-border)'}`,
                            transition: 'all 0.1s',
                          }}
                        >{m}</button>
                      )
                    })}
                  </div>

                  <div style={{ borderTop: '1px solid var(--clr-border)', paddingTop: 'var(--sp-3)', display: 'flex', gap: 'var(--sp-2)', alignItems: 'center' }}>
                    <button
                      className="btn btn--primary btn--sm"
                      onClick={applyMachineFilter}
                      disabled={pendingSel.size === 0 || recomputing}
                      style={{ flex: 1 }}
                    >
                      {recomputing
                        ? <><span className="spinner spinner--sm" aria-hidden="true" />Computing…</>
                        : cacheKey([...pendingSel].sort(), machines) === activeKey
                          ? 'Current selection'
                          : cache.has(cacheKey(pendingSel.size === machines.length ? null : [...pendingSel].sort(), machines))
                            ? 'Restore (cached)'
                            : 'Apply & Recompute'
                      }
                    </button>
                  </div>

                  {recomputeError && (
                    <p style={{ marginTop: 'var(--sp-2)', fontSize: 'var(--text-xs)', color: '#c0392b' }}>
                      {recomputeError}
                    </p>
                  )}
                </div>
              )}
            </div>

            <button
              className="btn btn--ghost btn--sm"
              onClick={handleDownload}
              disabled={downloading || recomputing}
            >
              {downloading
                ? <><span className="spinner spinner--sm" aria-hidden="true" />Downloading…</>
                : <>↓ Download Excel</>
              }
            </button>
          </div>
        </div>

        {/* Recomputing overlay + tables */}
        <div style={{ position: 'relative' }}>
          {recomputing && (
            <div style={{
              position: 'absolute', inset: 0, zIndex: 10, borderRadius: 'var(--radius-md)',
              background: 'rgba(255,255,255,0.65)', display: 'flex', alignItems: 'center', justifyContent: 'center',
            }}>
              <span className="spinner" aria-hidden="true" />
              <span style={{ marginLeft: 10, fontSize: 'var(--text-sm)', color: 'var(--clr-text-muted)' }}>
                Recomputing…
              </span>
            </div>
          )}

          {activeSection.isDeltas
            ? <YearlyDeltaSection tables={getYearlyDeltas(activeData, activeId)} metric={activeSection.metric} />
            : <ExcelPivotSection  tables={getMonthlyTables(activeData, activeId)} isDelta={false} />
          }
        </div>
      </div>
    </div>
  )
}
