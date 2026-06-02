import React, { useState } from 'react'
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

// ── Yearly-aggregate delta table (matches Excel screenshot format) ─────────

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
        const grandTotal = t.left_total + t.right_total
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
                    <th style={{ ...TH, minWidth: 140 }}>Sum of {metric}</th>
                    <th style={{ ...TH, minWidth: 140 }}>Dif of {metric}</th>
                  </tr>
                </thead>
                <tbody>
                  {/* RIGHT scenario (the "new" one) — shows both Sum and Dif */}
                  <tr style={{ background: '#ebf3fb' }}>
                    <td style={{ ...TDL, paddingLeft: 10, fontWeight: 700, color: 'var(--clr-blue)' }}>{t.right_name}</td>
                    <td style={{ ...TD, fontWeight: 700 }}>{fmtY(t.right_total)}</td>
                    <td style={{ ...TD, fontWeight: 700, color: t.delta_total < 0 ? '#c0392b' : 'var(--clr-blue)' }}>
                      {fmtDif(t.delta_total).text}
                    </td>
                  </tr>
                  {t.rows.map((row, ri) => {
                    const { text, color } = fmtDif(row.delta)
                    return (
                      <tr key={ri} style={{ background: ri % 2 === 0 ? '#fff' : '#fafafa' }}>
                        <td style={{ ...TDL, paddingLeft: 24 }}>{row.year}</td>
                        <td style={TD}>{fmtY(row.right_value)}</td>
                        <td style={{ ...TD, color }}>{text}</td>
                      </tr>
                    )
                  })}

                  {/* LEFT scenario (base) — Sum only, no Dif */}
                  <tr style={{ background: '#f5f5f5', borderTop: '1px solid var(--clr-border)' }}>
                    <td style={{ ...TDL, paddingLeft: 10, fontWeight: 700, color: 'var(--clr-text-muted)' }}>{t.left_name}</td>
                    <td style={{ ...TD, fontWeight: 700 }}>{fmtY(t.left_total)}</td>
                    <td style={TD} />
                  </tr>
                  {t.rows.map((row, ri) => (
                    <tr key={ri} style={{ background: ri % 2 === 0 ? '#fff' : '#fafafa' }}>
                      <td style={{ ...TDL, paddingLeft: 24 }}>{row.year}</td>
                      <td style={TD}>{fmtY(row.left_value)}</td>
                      <td style={TD} />
                    </tr>
                  ))}

                  {/* Grand Total */}
                  <tr style={{ background: '#b8cce4', fontWeight: 700, borderTop: '2px solid #8ea9d8' }}>
                    <td style={{ ...TDL, paddingLeft: 10 }}>Grand Total</td>
                    <td style={{ ...TD, fontWeight: 700 }}>{fmtY(grandTotal)}</td>
                    <td style={TD} />
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

export function ResultPage({ reportData, onReset }: Props) {
  const [activeId, setActiveId] = useState<SectionId>('ev-monthly')

  const activeSection = SECTIONS.find(s => s.id === activeId)!

  const groups = ['EV', 'IV', 'Power Position'] as const

  return (
    <div style={{ display: 'flex', gap: 0, minHeight: 'calc(100vh - 120px)', alignItems: 'flex-start' }}>
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
                const count = getSectionCount(reportData, sec.id)
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

      <div style={{ flex: 1, minWidth: 0, padding: 'var(--sp-6)', display: 'flex', flexDirection: 'column', gap: 'var(--sp-4)' }}>
        <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: 'var(--sp-4)' }}>
          <div>
            <h2 style={{ fontSize: 'var(--text-lg)', fontWeight: 'var(--weight-semibold)', margin: 0 }}>
              {activeSection.group} {`\u2014`} {activeSection.label}
            </h2>
            <p style={{ fontSize: 'var(--text-xs)', color: 'var(--clr-text-muted)', marginTop: 4 }}>
              Sum of <code style={{ background: 'var(--clr-bg)', padding: '1px 4px', borderRadius: 3 }}>{activeSection.metric}</code>
              {` \u00b7 `}{getSectionCount(reportData, activeId)} table{getSectionCount(reportData, activeId) !== 1 ? 's' : ''}
            </p>
          </div>
          <button className="btn btn--ghost btn--sm" disabled title="Excel download coming soon" style={{ flexShrink: 0 }}>
            ↓ Download Excel
          </button>
        </div>

        {activeSection.isDeltas
          ? <YearlyDeltaSection tables={getYearlyDeltas(reportData, activeId)} metric={activeSection.metric} />
          : <ExcelPivotSection  tables={getMonthlyTables(reportData, activeId)} isDelta={false} />
        }
      </div>
    </div>
  )
}
