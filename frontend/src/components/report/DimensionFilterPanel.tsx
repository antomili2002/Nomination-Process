import { useState } from "react"
import type { DimensionFilters, FilterOptions } from "../../types/report"

interface Props {
  options: FilterOptions
  onApply: (filters: DimensionFilters | null) => void
  loading: boolean
}

const EMPTY_FILTERS: DimensionFilters = { machineNames: null, plantNames: null, unitNames: null, fuelNames: null }

function isEmpty(f: DimensionFilters): boolean {
  return !f.machineNames && !f.plantNames && !f.unitNames && !f.fuelNames
}

export function DimensionFilterPanel({ options, onApply, loading }: Props) {
  const [pending, setPending] = useState<DimensionFilters>(EMPTY_FILTERS)

  const dims: { key: keyof DimensionFilters; label: string; values: string[] }[] = (
    [
      { key: "plantNames"   as const, label: "Plant",   values: options.plantNames },
      { key: "unitNames"    as const, label: "Unit",    values: options.unitNames },
      { key: "machineNames" as const, label: "Machine", values: options.machines },
      { key: "fuelNames"   as const, label: "Fuel",    values: options.fuelNames },
    ] as { key: keyof DimensionFilters; label: string; values: string[] }[]
  ).filter(d => d.values.length > 0)

  if (dims.length === 0) return null

  function toggle(dimKey: keyof DimensionFilters, value: string, allValues: string[]) {
    setPending(prev => {
      const cur = (prev[dimKey] as string[] | null) ?? allValues
      const next = cur.includes(value) ? cur.filter(v => v !== value) : [...cur, value]
      return { ...prev, [dimKey]: next.length === allValues.length ? null : [...next].sort() }
    })
  }

  function isSelected(dimKey: keyof DimensionFilters, value: string): boolean {
    const cur = pending[dimKey] as string[] | null
    return cur === null || cur.includes(value)
  }

  function handleClear() { setPending(EMPTY_FILTERS); onApply(null) }

  return (
    <div style={{ border: "1px solid var(--clr-border)", borderRadius: "var(--radius-md)", padding: "var(--sp-4)", marginBottom: "var(--sp-4)", background: "#fafbfc" }}>
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "var(--sp-3)" }}>
        <p style={{ margin: 0, fontWeight: 700, fontSize: "var(--text-sm)" }}>Compare with filter</p>
        <div style={{ display: "flex", gap: "var(--sp-2)" }}>
          <button className="btn btn--ghost btn--sm" onClick={handleClear} disabled={loading}>Clear</button>
          <button className="btn btn--primary btn--sm" disabled={loading || isEmpty(pending)} onClick={() => onApply(isEmpty(pending) ? null : pending)}>
            {loading ? <><span className="spinner spinner--sm" aria-hidden="true" /> Computing&hellip;</> : "Apply"}
          </button>
        </div>
      </div>
      <div style={{ display: "flex", flexWrap: "wrap", gap: "var(--sp-5)" }}>
        {dims.map(({ key, label, values }) => (
          <div key={key}>
            <p style={{ margin: "0 0 4px", fontSize: 9, fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.08em", color: "var(--clr-text-muted)" }}>{label}</p>
            <div style={{ display: "flex", flexWrap: "wrap", gap: 4, maxWidth: 340 }}>
              {values.map(v => {
                const sel = isSelected(key, v)
                return (
                  <button key={v} type="button" onClick={() => toggle(key, v, values)} style={{
                    padding: "3px 10px", borderRadius: "var(--radius-md)", cursor: "pointer",
                    fontSize: "var(--text-xs)", fontWeight: sel ? 600 : "normal",
                    background: sel ? "var(--clr-blue)" : "var(--clr-bg)",
                    color: sel ? "#fff" : "var(--clr-text-muted)",
                    border: `1px solid ${sel ? "var(--clr-blue)" : "var(--clr-border)"}`,
                    transition: "all 0.1s",
                  }}>{v}</button>
                )
              })}
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
