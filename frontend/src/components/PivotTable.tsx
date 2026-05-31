import React from 'react'

export interface PivotRow {
  year: number
  tariff: string
  values: number[]
}

export interface PivotTableData {
  title: string
  pair_type?: string | null
  step_number?: number | null
  months: number[]
  rows: PivotRow[]
}

interface Props {
  table: PivotTableData
  isDelta?: boolean
}

const MONTH_ABBR = ['', 'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
                        'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']

function fmt(v: number, isDelta: boolean): string {
  if (v === 0) return '—'
  const n = Math.abs(v)
  const s = n >= 1_000_000
    ? (v / 1_000_000).toFixed(2) + ' M'
    : n >= 1_000
    ? (v / 1_000).toFixed(2) + ' k'
    : v.toFixed(2)
  return v < 0 && isDelta ? `(${Math.abs(v / (n >= 1_000_000 ? 1_000_000 : n >= 1_000 ? 1_000 : 1)).toFixed(2)}${n >= 1_000_000 ? ' M' : n >= 1_000 ? ' k' : ''})` : s
}

export function PivotTable({ table, isDelta = false }: Props) {
  const { title, months, rows } = table

  const typeLabel = table.pair_type === 'cumulative'
    ? 'Cumulative'
    : table.pair_type === 'step'
    ? `Step ${table.step_number}`
    : null

  return (
    <div style={{ marginBottom: 'var(--sp-6)' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--sp-2)', marginBottom: 'var(--sp-2)' }}>
        {typeLabel && (
          <span style={{
            fontSize: 'var(--text-xs)', padding: '2px 8px', borderRadius: 'var(--radius-sm)',
            background: table.pair_type === 'cumulative' ? 'var(--clr-blue-light)' : 'var(--clr-bg)',
            border: `1px solid ${table.pair_type === 'cumulative' ? 'var(--clr-blue)' : 'var(--clr-border)'}`,
            color: table.pair_type === 'cumulative' ? 'var(--clr-blue)' : 'var(--clr-text-muted)',
            fontWeight: 600,
          }}>
            {typeLabel}
          </span>
        )}
        <span style={{ fontSize: 'var(--text-sm)', fontWeight: 'var(--weight-medium)', color: 'var(--clr-text)' }}>
          {title}
        </span>
      </div>

      <div className="table-wrapper" style={{ overflowX: 'auto' }}>
        <table className="table" style={{ minWidth: 'max-content', fontSize: 'var(--text-xs)' }}>
          <thead>
            <tr>
              <th style={{ textAlign: 'left', minWidth: 50 }}>Year</th>
              <th style={{ textAlign: 'left', minWidth: 70 }}>Tariff</th>
              {months.map(m => (
                <th key={m} style={{ textAlign: 'right', minWidth: 68 }}>
                  {MONTH_ABBR[m]}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map((row, i) => {
              const hasNeg = isDelta && row.values.some(v => v < 0)
              return (
                <tr key={i} style={{ color: hasNeg ? 'var(--clr-error, #d0021b)' : undefined }}>
                  <td style={{ fontVariantNumeric: 'tabular-nums' }}>{row.year}</td>
                  <td style={{ textTransform: 'capitalize' }}>{row.tariff}</td>
                  {row.values.map((v, j) => (
                    <td key={j} style={{ textAlign: 'right', fontVariantNumeric: 'tabular-nums',
                      color: isDelta && v < 0 ? 'var(--clr-error, #d0021b)' : isDelta && v > 0 ? 'var(--clr-blue)' : undefined }}>
                      {fmt(v, isDelta)}
                    </td>
                  ))}
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>
    </div>
  )
}
