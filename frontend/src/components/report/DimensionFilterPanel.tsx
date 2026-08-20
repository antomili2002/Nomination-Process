import { useEffect, useRef, useState } from "react"
import { SlidersHorizontal } from "lucide-react"
import type { DimensionFilters, FilterOptions } from "../../types/report"

interface Props {
  options: FilterOptions
  activeFilters: DimensionFilters | null
  onApply: (filters: DimensionFilters | null) => void
  loading: boolean
  label?: string
}

const EMPTY: DimensionFilters = { machineNames: null, plantNames: null, unitNames: null, fuelNames: null }

function isEmpty(f: DimensionFilters): boolean {
  return !f.machineNames && !f.plantNames && !f.unitNames && !f.fuelNames
}

function activeCount(f: DimensionFilters | null): number {
  if (!f) return 0
  return [f.plantNames, f.unitNames, f.machineNames, f.fuelNames].filter(v => v !== null).length
}

export function DimensionFilterPanel({ options, activeFilters, onApply, loading, label = "Filter" }: Props) {
  const [isOpen, setIsOpen] = useState(false)
  const [pending, setPending] = useState<DimensionFilters>(EMPTY)
  const ref = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!isOpen) return
    function onDown(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) setIsOpen(false)
    }
    document.addEventListener("mousedown", onDown)
    return () => document.removeEventListener("mousedown", onDown)
  }, [isOpen])

  const dims: { key: keyof DimensionFilters; label: string; values: string[] }[] = (
    [
      { key: "plantNames"   as const, label: "Plant",   values: options.plantNames },
      { key: "unitNames"    as const, label: "Unit",    values: options.unitNames },
      { key: "machineNames" as const, label: "Machine", values: options.machines },
      { key: "fuelNames"    as const, label: "Fuel",    values: options.fuelNames },
    ] as { key: keyof DimensionFilters; label: string; values: string[] }[]
  ).filter(d => d.values.length > 0)

  if (dims.length === 0) return null

  const count = activeCount(activeFilters)
  const isActive = count > 0

  function handleToggle() {
    if (!isOpen) setPending(activeFilters ?? EMPTY)
    setIsOpen(v => !v)
  }

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

  function handleApply() { setIsOpen(false); onApply(isEmpty(pending) ? null : pending) }
  function handleClear()  { setIsOpen(false); setPending(EMPTY); onApply(null) }

  return (
    <div ref={ref} style={{ position: "relative" }}>
      <button
        className="btn btn--ghost btn--sm"
        onClick={handleToggle}
        style={{
          borderColor: isActive ? "var(--clr-blue)" : undefined,
          color:       isActive ? "var(--clr-blue)" : undefined,
          fontWeight:  isActive ? 700 : undefined,
        }}
      >
        <SlidersHorizontal size={14} aria-hidden="true" />
        {isActive ? `${label} (${count})` : label}
      </button>

      {isOpen && (
        <div style={{
          position: "absolute", top: "calc(100% + 6px)", right: 0, zIndex: 200,
          background: "#fff", border: "1px solid var(--clr-border)",
          borderRadius: "var(--radius-md)", boxShadow: "0 6px 24px rgba(0,0,0,0.13)",
          padding: "var(--sp-4)", minWidth: 380, maxWidth: 540,
        }}>
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "var(--sp-3)" }}>
            <p style={{ margin: 0, fontWeight: 700, fontSize: "var(--text-sm)" }}>Compare with filter</p>
            <button className="btn btn--ghost btn--sm" onClick={() => setPending(EMPTY)}>Reset</button>
          </div>

          <div style={{ display: "flex", flexDirection: "column", gap: "var(--sp-3)", maxHeight: 280, overflowY: "auto", marginBottom: "var(--sp-3)" }}>
            {dims.map(({ key, label, values }) => (
              <div key={key}>
                <p style={{ margin: "0 0 4px", fontSize: 9, fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.08em", color: "var(--clr-text-muted)" }}>{label}</p>
                <div style={{ display: "flex", flexWrap: "wrap", gap: 4 }}>
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

          <div style={{ borderTop: "1px solid var(--clr-border)", paddingTop: "var(--sp-3)", display: "flex", gap: "var(--sp-2)" }}>
            <button className="btn btn--ghost btn--sm" onClick={handleClear} disabled={loading}>Clear all</button>
            <button className="btn btn--primary btn--sm" style={{ flex: 1 }} disabled={loading || isEmpty(pending)} onClick={handleApply}>
              {loading ? <><span className="spinner spinner--sm" aria-hidden="true" /> Computing&hellip;</> : "Apply"}
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
