import React from 'react'
import type { PivotTableData } from '../PivotTable'
import type { MachineYearlyDeltaTable, YearlyDeltaTable } from '../../types/report'

function fmtN(v: number): string {
  if (Math.abs(v) < 0.005) return '\u2014'
  return Math.round(v).toLocaleString('en-GB')
}

function fmtDelta(v: number): { text: string; color?: string } {
  if (Math.abs(v) < 0.005) return { text: '\u2014' }
  const abs = Math.round(Math.abs(v)).toLocaleString('en-GB')
  if (v < 0) return { text: `(${abs})`, color: '#c0392b' }
  return { text: abs, color: 'var(--clr-blue)' }
}

function fmtY(v: number): string {
  if (Math.abs(v) < 0.0005) return '\u2014'
  return Math.round(v).toLocaleString('en-GB')
}

function fmtDif(v: number): { text: string; color?: string } {
  if (Math.abs(v) < 0.0005) return { text: '' }
  const s = Math.round(Math.abs(v)).toLocaleString('en-GB')
  if (v < 0) return { text: `-${s}`, color: '#c0392b' }
  return { text: s, color: 'var(--clr-blue)' }
}

const TH: React.CSSProperties = {
  padding: '5px 10px',
  fontWeight: 700,
  fontSize: 'var(--text-xs)',
  background: '#d9e1f2',
  borderBottom: '2px solid #8ea9d8',
  whiteSpace: 'nowrap',
  borderRight: '1px solid #b8c9e0',
}

const TD: React.CSSProperties = {
  padding: '3px 10px',
  textAlign: 'right',
  fontVariantNumeric: 'tabular-nums',
  fontSize: 'var(--text-xs)',
  borderRight: '1px solid var(--clr-border)',
  whiteSpace: 'nowrap',
}

const TDL: React.CSSProperties = { ...TD, textAlign: 'left', fontVariantNumeric: 'normal' }

function PairBadge({ pairType, stepNumber, rightName, leftName }: {
  pairType?: string
  stepNumber?: number | null
  rightName: string
  leftName: string
}) {
  if (!pairType) return null
  return (
    <div style={{ marginBottom: 'var(--sp-2)', display: 'flex', alignItems: 'center', gap: 'var(--sp-2)' }}>
      <span style={{
        fontSize: 9, padding: '2px 8px', borderRadius: 3,
        background: pairType === 'cumulative' ? 'var(--clr-blue)' : '#6c757d', color: '#fff',
        fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.06em',
      }}>
        {pairType === 'cumulative' ? 'Cumulative' : `Step ${stepNumber}`}
      </span>
      <span style={{ fontSize: 'var(--text-xs)', color: 'var(--clr-text-muted)' }}>
        {rightName} vs {leftName}
      </span>
    </div>
  )
}

export function YearlyDeltaSection({ tables, metric }: { tables: YearlyDeltaTable[]; metric: string }) {
  if (tables.length === 0)
    return <p style={{ color: 'var(--clr-text-muted)', fontStyle: 'italic' }}>No data available.</p>

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--sp-5)' }}>
      {tables.map((t, ti) => (
        <div key={ti}>
          <PairBadge pairType={t.pair_type} stepNumber={t.step_number} rightName={t.right_name} leftName={t.left_name} />
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
      ))}
    </div>
  )
}

export function MachineYearlyDeltaSection({ tables, metric }: { tables: MachineYearlyDeltaTable[]; metric: string }) {
  if (tables.length === 0)
    return <p style={{ color: 'var(--clr-text-muted)', fontStyle: 'italic' }}>No data available.</p>

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--sp-5)' }}>
      {tables.map((t, ti) => {
        const machineNames = [...new Set(t.rows.map(r => r.machine_name))].sort()
        const machineTotals = machineNames.map(machineName => {
          const rows = t.rows.filter(r => r.machine_name === machineName)
          return {
            machineName,
            rows,
            leftTotal: rows.reduce((sum, r) => sum + r.left_value, 0),
            rightTotal: rows.reduce((sum, r) => sum + r.right_value, 0),
            deltaTotal: rows.reduce((sum, r) => sum + r.delta, 0),
          }
        })

        return (
          <div key={ti}>
            <PairBadge pairType={t.pair_type} stepNumber={t.step_number} rightName={t.right_name} leftName={t.left_name} />
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
                  {machineTotals.map(({ machineName, rows, leftTotal, rightTotal, deltaTotal }, mi) => {
                    const machineDif = fmtDif(deltaTotal)
                    return (
                      <React.Fragment key={machineName}>
                        <tr style={{ background: mi % 2 === 0 ? '#f3f7fb' : '#eef4fa', fontWeight: 700 }}>
                          <td style={{ ...TDL, paddingLeft: 10 }}>{machineName}</td>
                          <td style={{ ...TD, fontWeight: 700 }}>{fmtY(leftTotal)}</td>
                          <td style={{ ...TD, fontWeight: 700 }}>{fmtY(rightTotal)}</td>
                          <td style={{ ...TD, fontWeight: 700, color: machineDif.color }}>{machineDif.text}</td>
                        </tr>
                        {rows.map((row, ri) => {
                          const { text, color } = fmtDif(row.delta)
                          return (
                            <tr key={`${machineName}-${row.year}`} style={{ background: ri % 2 === 0 ? '#fff' : '#fafafa' }}>
                              <td style={{ ...TDL, paddingLeft: 28 }}>{row.year}</td>
                              <td style={TD}>{fmtY(row.left_value)}</td>
                              <td style={TD}>{fmtY(row.right_value)}</td>
                              <td style={{ ...TD, color }}>{text}</td>
                            </tr>
                          )
                        })}
                      </React.Fragment>
                    )
                  })}
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

export function ExcelPivotSection({ tables, isDelta }: { tables: PivotTableData[]; isDelta: boolean }) {
  if (tables.length === 0) return <p style={{ color: 'var(--clr-text-muted)', fontStyle: 'italic' }}>No data available.</p>

  const months = tables[0].months
  const colTotals = months.map((_, mi) =>
    tables.flatMap(t => t.rows).reduce((s, r) => s + (r.values[mi] ?? 0), 0)
  )
  const overallTotal = colTotals.reduce((s, v) => s + v, 0)

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
            <th style={{ ...TH, textAlign: 'left', minWidth: 56 }}>Year</th>
            <th style={{ ...TH, textAlign: 'left', minWidth: 72 }}>Tariff</th>
            {months.map(m => <th key={m} style={{ ...TH, minWidth: 72 }}>{m}</th>)}
            <th style={{ ...TH, minWidth: 90, borderLeft: '2px solid #8ea9d8' }}>Grand Total</th>
          </tr>
        </thead>
        <tbody>
          {tables.map((table, ti) => {
            const years = [...new Set(table.rows.map(r => r.year))].sort()
            const scMonthTotals = months.map((_, mi) => table.rows.reduce((s, r) => s + (r.values[mi] ?? 0), 0))
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
                    {table.title}
                  </td>
                </tr>
                {years.map(year => {
                  const yearRows = table.rows.filter(r => r.year === year)
                  return yearRows.map((row, ri) => (
                    <tr key={`${year}-${ri}`} style={{ background: ri % 2 === 0 ? '#fff' : '#fafafa' }}>
                      <td style={{ ...TDL, paddingLeft: 16 }}>{ri === 0 ? <strong>{year}</strong> : ''}</td>
                      <td style={{ ...TDL, paddingLeft: 24, textTransform: 'capitalize' }}>{row.tariff}</td>
                      {row.values.map((v, mi) => isDelta
                        ? <td key={mi} style={{ ...TD, color: fmtDelta(v).color }}>{fmtDelta(v).text}</td>
                        : <td key={mi} style={TD}>{fmtN(v)}</td>
                      )}
                      {valTD(row.values.reduce((s, v) => s + v, 0), false, '#edf2f7')}
                    </tr>
                  ))
                })}
                <tr style={{ background: '#dce3ed', fontWeight: 700, borderBottom: '1px solid #b8c9e0' }}>
                  <td colSpan={2} style={{ ...TDL, paddingLeft: 10, color: isDelta ? '#c0392b' : 'var(--clr-blue)' }}>
                    {table.title} Total
                  </td>
                  {scMonthTotals.map((v, i) => isDelta
                    ? <td key={i} style={{ ...TD, color: fmtDelta(v).color, fontWeight: 700 }}>{fmtDelta(v).text}</td>
                    : <td key={i} style={{ ...TD, fontWeight: 700 }}>{fmtN(v)}</td>
                  )}
                  {valTD(scGrandTotal, true)}
                </tr>
              </React.Fragment>
            )
          })}
          {tables.length > 1 && (
            <tr style={{ background: '#b8cce4', fontWeight: 700, borderTop: '2px solid #8ea9d8' }}>
              <td colSpan={2} style={{ ...TDL, paddingLeft: 10 }}>Grand Total</td>
              {colTotals.map((v, i) => isDelta
                ? <td key={i} style={{ ...TD, color: fmtDelta(v).color, fontWeight: 700 }}>{fmtDelta(v).text}</td>
                : <td key={i} style={{ ...TD, fontWeight: 700 }}>{fmtN(v)}</td>
              )}
              {valTD(overallTotal, true)}
            </tr>
          )}
        </tbody>
      </table>
    </div>
  )
}
