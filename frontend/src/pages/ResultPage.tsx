import { useEffect, useRef, useState } from 'react'
import { Download, FilePlus2, SlidersHorizontal } from 'lucide-react'
import type { ReportData } from '../types/report'
import type { PivotTableData } from '../components/PivotTable'
import {
  getMachineYearlyDeltas,
  getMonthlyTables,
  getSection,
  getSectionCount,
  getYearlyDeltas,
  REPORT_GROUPS,
  SECTIONS,
  type SectionId,
} from '../reportMetrics'
import {
  ExcelPivotSection,
  MachineYearlyDeltaSection,
  YearlyDeltaSection,
} from '../components/report/ReportSections'

interface Props {
  reportData: ReportData
  onReset: () => void
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
    evMachineDeltas: p.ev_machine_deltas as ReportData['evMachineDeltas'],
    ivMonthly: p.iv_monthly as PivotTableData[],
    ivDeltas:  p.iv_deltas  as ReportData['ivDeltas'],
    ivMachineDeltas: p.iv_machine_deltas as ReportData['ivMachineDeltas'],
    ppMonthly: p.pp_monthly as PivotTableData[],
    ppDeltas:  p.pp_deltas  as ReportData['ppDeltas'],
    ppMachineDeltas: p.pp_machine_deltas as ReportData['ppMachineDeltas'],
    ivHeatMonthly: p.iv_heat_monthly as PivotTableData[],
    ivHeatDeltas:  p.iv_heat_deltas as ReportData['ivHeatDeltas'],
    ivHeatMachineDeltas: p.iv_heat_machine_deltas as ReportData['ivHeatMachineDeltas'],
    heatProdMonthly: p.heat_prod_monthly as PivotTableData[],
    heatProdDeltas:  p.heat_prod_deltas as ReportData['heatProdDeltas'],
    heatProdMachineDeltas: p.heat_prod_machine_deltas as ReportData['heatProdMachineDeltas'],
  }
}

export function ResultPage({ reportData, onReset }: Props) {
  const { uploadId, ivChain, evChain, machines } = reportData

  // -- Section navigation ---------------------------------------------------
  const [activeId, setActiveId] = useState<SectionId>('ev-monthly')
  const activeSection = getSection(activeId)

  // -- Machine filter + cache -----------------------------------------------
  // activeData is what gets rendered; initialised from the passed-in reportData.
  const [activeData, setActiveData]     = useState<ReportData>(reportData)
  const [activeKey, setActiveKey]       = useState<string>(() => cacheKey(reportData.selectedMachines, machines))

  // Cache: cacheKey to ReportData. Pre-seed with the initial result.
  const [cache, setCache] = useState<Map<string, ReportData>>(() => {
    const m = new Map<string, ReportData>()
    m.set(cacheKey(reportData.selectedMachines, machines), reportData)
    return m
  })

  const [recomputing, setRecomputing]   = useState(false)
  const [recomputeError, setRecomputeError] = useState<string | null>(null)

  // -- Download state -------------------------------------------------------
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
      {/* -- Sidebar -- */}
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

        {REPORT_GROUPS.map(group => {
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
            <FilePlus2 size={14} aria-hidden="true" /> New Report
          </button>
        </div>
      </aside>

      {/* -- Main content -- */}
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
                <SlidersHorizontal size={14} aria-hidden="true" /> {isFiltered ? `Machines (${activeMachineCount}/${machines.length})` : 'Machines (All)'}
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
                : <><Download size={14} aria-hidden="true" /> Download Excel</>
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

          {activeSection.tableType === 'monthly' && (
            <ExcelPivotSection tables={getMonthlyTables(activeData, activeId)} isDelta={false} />
          )}
          {activeSection.tableType === 'yearlyDelta' && (
            <YearlyDeltaSection tables={getYearlyDeltas(activeData, activeId)} metric={activeSection.metric} />
          )}
          {activeSection.tableType === 'machineYearlyDelta' && (
            <MachineYearlyDeltaSection tables={getMachineYearlyDeltas(activeData, activeId)} metric={activeSection.metric} />
          )}
        </div>
      </div>
    </div>
  )
}




