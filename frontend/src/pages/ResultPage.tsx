import { useState } from 'react'
import { Download, FilePlus2 } from 'lucide-react'
import { buildApiUrl } from '../api'
import type { DimensionFilters, ReportData } from '../types/report'
import { buildSections, findMetric, sectionCount } from '../reportMetrics'
import { DimensionFilterPanel } from '../components/report/DimensionFilterPanel'
import {
  ExcelPivotSection,
  NonUkCategorySections,
  YearlyDeltaSection,
} from '../components/report/ReportSections'

interface Props {
  reportData: ReportData
  onReset: () => void
}

function mapPayload(p: Record<string, unknown>, base: ReportData): ReportData {
  return {
    reportId:        p.report_id as string,
    uploadId:        base.uploadId,
    asOfDate:        base.asOfDate,
    portfolioCountry: p.portfolio_country as string,
    layout:          p.layout as ReportData['layout'],
    ivChain:         base.ivChain,
    evChain:         base.evChain,
    machines:        base.machines,
    selectedMachines: base.selectedMachines,
    selectedMetrics: base.selectedMetrics,
    metrics: p.metrics as ReportData['metrics'],
    nonUkSections: p.non_uk_sections as ReportData['nonUkSections'],
    filterOptions: base.filterOptions,
  }
}

export function ResultPage({ reportData, onReset }: Props) {
  const isNonUk = reportData.layout === 'non_uk'

  const sections = buildSections(reportData.metrics)

  // -- Section navigation ---------------------------------------------------
  const [activeId, setActiveId] = useState<string>(() => sections[0]?.id ?? '')
  const activeSection = sections.find(s => s.id === activeId) ?? sections[0]
  const [nonUkOutputType, setNonUkOutputType] = useState<'IV' | 'EV'>('IV')
  const [nonUkPeriod, setNonUkPeriod] = useState<'monthly' | 'yearly'>('yearly')

  // -- Dimension filter comparison ------------------------------------------
  const [filteredData,  setFilteredData]  = useState<ReportData | null>(null)
  const [filterCache,   setFilterCache]   = useState<Map<string, ReportData>>(new Map())
  const [filtering,     setFiltering]     = useState(false)
  const [activeFilters, setActiveFilters] = useState<DimensionFilters | null>(null)

  const [filteredData2,  setFilteredData2]  = useState<ReportData | null>(null)
  const [filterCache2,   setFilterCache2]   = useState<Map<string, ReportData>>(new Map())
  const [filtering2,     setFiltering2]     = useState(false)
  const [activeFilters2, setActiveFilters2] = useState<DimensionFilters | null>(null)

  const [downloading, setDownloading] = useState(false)

  function filterKey(f: DimensionFilters): string {
    return JSON.stringify({
      m: [...(f.machineNames ?? [])].sort(),
      p: [...(f.plantNames ?? [])].sort(),
      u: [...(f.unitNames ?? [])].sort(),
      f: [...(f.fuelNames ?? [])].sort(),
    })
  }

  function filterLabel(f: DimensionFilters): string {
    const parts: string[] = []
    if (f.plantNames?.length)   parts.push(`Plant: ${f.plantNames.join(', ')}`)
    if (f.unitNames?.length)    parts.push(`Unit: ${f.unitNames.join(', ')}`)
    if (f.machineNames?.length) parts.push(`Machine: ${f.machineNames.join(', ')}`)
    if (f.fuelNames?.length)    parts.push(`Fuel: ${f.fuelNames.join(', ')}`)
    return parts.join(' · ') || 'Filtered'
  }

  async function applyDimensionFilter(filters: DimensionFilters | null) {
    setActiveFilters(filters)
    if (!filters) { setFilteredData(null); return }
    const key = filterKey(filters)
    if (filterCache.has(key)) { setFilteredData(filterCache.get(key)!); return }
    setFiltering(true)
    try {
      const resp = await fetch(buildApiUrl('/reports/generate'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          upload_id: reportData.uploadId,
          iv_chain:  reportData.ivChain,
          ev_chain:  reportData.evChain,
          selected_machines: null,
          selected_metrics:  reportData.selectedMetrics,
          dimension_filters: {
            machine_names: filters.machineNames,
            plant_names:   filters.plantNames,
            unit_names:    filters.unitNames,
            fuel_names:    filters.fuelNames,
          },
        }),
      })
      if (!resp.ok) throw new Error(`Filter failed (${resp.status})`)
      const p = await resp.json()
      const nd: ReportData = { ...mapPayload(p, reportData), selectedMachines: null }
      setFilterCache(prev => new Map(prev).set(key, nd))
      setFilteredData(nd)
    } catch {
      setFilteredData(null)
    } finally {
      setFiltering(false)
    }
  }

  async function applyDimensionFilter2(filters: DimensionFilters | null) {
    setActiveFilters2(filters)
    if (!filters) { setFilteredData2(null); return }
    const key = filterKey(filters)
    if (filterCache2.has(key)) { setFilteredData2(filterCache2.get(key)!); return }
    setFiltering2(true)
    try {
      const resp = await fetch(buildApiUrl('/reports/generate'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          upload_id: reportData.uploadId,
          iv_chain:  reportData.ivChain,
          ev_chain:  reportData.evChain,
          selected_machines: null,
          selected_metrics:  reportData.selectedMetrics,
          dimension_filters: {
            machine_names: filters.machineNames,
            plant_names:   filters.plantNames,
            unit_names:    filters.unitNames,
            fuel_names:    filters.fuelNames,
          },
        }),
      })
      if (!resp.ok) throw new Error(`Filter 2 failed (${resp.status})`)
      const p = await resp.json()
      const nd: ReportData = { ...mapPayload(p, reportData), selectedMachines: null }
      setFilterCache2(prev => new Map(prev).set(key, nd))
      setFilteredData2(nd)
    } catch {
      setFilteredData2(null)
    } finally {
      setFiltering2(false)
    }
  }

  // -- Download state -------------------------------------------------------

  async function handleDownload() {
    setDownloading(true)
    try {
      const resp = await fetch(buildApiUrl('/reports/export'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          upload_id: reportData.uploadId,
          iv_chain:  reportData.ivChain,
          ev_chain:  reportData.evChain,
          selected_machines: null,
          selected_metrics: reportData.selectedMetrics,
          dimension_filters: activeFilters ? {
            machine_names: activeFilters.machineNames,
            plant_names:   activeFilters.plantNames,
            unit_names:    activeFilters.unitNames,
            fuel_names:    activeFilters.fuelNames,
          } : null,
          dimension_filters_2: activeFilters2 ? {
            machine_names: activeFilters2.machineNames,
            plant_names:   activeFilters2.plantNames,
            unit_names:    activeFilters2.unitNames,
            fuel_names:    activeFilters2.fuelNames,
          } : null,
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

  // Derived: sections visible in the non-UK view for the active output type/period
  const activeNonUkSections = reportData.nonUkSections.filter(
    section => section.output_type === nonUkOutputType && section.period === nonUkPeriod
  )

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
          {reportData.asOfDate && (
            <p style={{ fontSize: 'var(--text-xs)', color: 'var(--clr-text-muted)', margin: '4px 0 0', fontWeight: 500 }}>
              As of: <strong>{reportData.asOfDate}</strong>
            </p>
          )}
        </div>

        {isNonUk ? (
          <div style={{ padding: 'var(--sp-3)', display: 'flex', flexDirection: 'column', gap: 'var(--sp-3)' }}>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 'var(--sp-1)' }}>
              {(['IV', 'EV'] as const).map(outputType => (
                <button
                  key={outputType}
                  type="button"
                  onClick={() => setNonUkOutputType(outputType)}
                  style={{
                    padding: '7px 8px', border: '1px solid var(--clr-border)', cursor: 'pointer',
                    background: nonUkOutputType === outputType ? 'var(--clr-blue)' : '#fff',
                    color: nonUkOutputType === outputType ? '#fff' : 'var(--clr-text)', fontWeight: 700,
                  }}
                >{outputType}</button>
              ))}
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--sp-1)' }}>
              {(['yearly', 'monthly'] as const).map(period => (
                <button
                  key={period}
                  type="button"
                  onClick={() => setNonUkPeriod(period)}
                  style={{
                    padding: '7px 10px', border: 'none', borderLeft: `3px solid ${nonUkPeriod === period ? 'var(--clr-blue)' : 'transparent'}`,
                    cursor: 'pointer', textAlign: 'left', background: nonUkPeriod === period ? 'var(--clr-blue-light)' : 'transparent',
                    color: 'var(--clr-text)', fontWeight: nonUkPeriod === period ? 700 : 400,
                  }}
                >{period === 'yearly' ? 'Yearly' : 'Monthly'}</button>
              ))}
            </div>
          </div>
        ) : reportData.metrics.map(metric => {
          const groupSections = sections.filter(s => s.metricKey === metric.key)
          return (
            <div key={metric.key} style={{ borderBottom: '1px solid var(--clr-border)' }}>
              <p style={{ margin: 0, padding: '8px 16px 4px', fontSize: 9, fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.1em', color: 'var(--clr-text-muted)' }}>
                {metric.label}
              </p>
              {groupSections.map(sec => {
                const count = sectionCount(reportData.metrics, sec.metricKey, sec.tableType)
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
              {isNonUk
                ? `${nonUkOutputType} - ${nonUkPeriod === 'yearly' ? 'Yearly' : 'Monthly'}`
                : `${activeSection?.metricLabel ?? ''} - ${activeSection?.label ?? ''}`}
            </h2>
            <p style={{ fontSize: 'var(--text-xs)', color: 'var(--clr-text-muted)', marginTop: 4 }}>
              {isNonUk
                ? `${activeNonUkSections.length} categor${activeNonUkSections.length === 1 ? 'y' : 'ies'}`
                : <>
                    Sum of <code style={{ background: 'var(--clr-bg)', padding: '1px 4px', borderRadius: 3 }}>{activeSection?.column}</code>
                    {' · '}{sectionCount(reportData.metrics, activeSection?.metricKey ?? '', activeSection?.tableType ?? 'monthly')} table{sectionCount(reportData.metrics, activeSection?.metricKey ?? '', activeSection?.tableType ?? 'monthly') !== 1 ? 's' : ''}
                  </>}
              {activeFilters && (
                <span style={{ marginLeft: 8, padding: '1px 7px', borderRadius: 10, background: 'var(--clr-blue-light)', color: 'var(--clr-blue)', fontWeight: 600 }}>
                  F1: {filterLabel(activeFilters)}
                </span>
              )}
              {activeFilters2 && (
                <span style={{ marginLeft: 4, padding: '1px 7px', borderRadius: 10, background: 'var(--clr-blue-light)', color: 'var(--clr-blue)', fontWeight: 600 }}>
                  F2: {filterLabel(activeFilters2)}
                </span>
              )}
            </p>
          </div>

          {/* Action buttons */}
          <div style={{ display: 'flex', gap: 'var(--sp-2)', flexShrink: 0, alignItems: 'center' }}>
            <DimensionFilterPanel
              options={reportData.filterOptions}
              activeFilters={activeFilters}
              onApply={applyDimensionFilter}
              loading={filtering}
              label="Filter 1"
            />
            <DimensionFilterPanel
              options={reportData.filterOptions}
              activeFilters={activeFilters2}
              onApply={applyDimensionFilter2}
              loading={filtering2}
              label="Filter 2"
            />
            <button
              className="btn btn--ghost btn--sm"
              onClick={handleDownload}
              disabled={downloading || filtering}
            >
              {downloading
                ? <><span className="spinner spinner--sm" aria-hidden="true" />Downloading…</>
                : <><Download size={14} aria-hidden="true" /> Download Excel</>
              }
            </button>
          </div>
        </div>

        {/* Tables — side-by-side when a filter is active */}
        <div style={{ display: 'flex', gap: 24 }}>
          {/* Original pane */}
          <div style={{ flex: 1, minWidth: 0, overflowX: 'auto' }}>
            {filteredData && (
              <p style={{ margin: '0 0 8px', fontSize: 11, fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.08em', color: 'var(--clr-text-muted)' }}>
                Original — All
              </p>
            )}
            {isNonUk && <NonUkCategorySections sections={activeNonUkSections} />}
            {!isNonUk && activeSection?.tableType === 'monthly' && (
              <ExcelPivotSection
                tables={findMetric(reportData.metrics, activeSection.metricKey)?.monthly ?? []}
                isDelta={false}
              />
            )}
            {!isNonUk && activeSection?.tableType === 'yearlyDelta' && (
              <YearlyDeltaSection
                tables={findMetric(reportData.metrics, activeSection.metricKey)?.deltas ?? []}
                metric={activeSection.column}
              />
            )}
          </div>

          {/* Filtered comparison pane */}
          {(filteredData || filtering) && (
            <div style={{ flex: 1, minWidth: 0, overflowX: 'auto', borderLeft: '2px solid var(--clr-blue)', paddingLeft: 24 }}>
              <p style={{ margin: '0 0 8px', fontSize: 11, fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.08em', color: 'var(--clr-blue)' }}>
                {activeFilters ? filterLabel(activeFilters) : 'Filter 1'}
              </p>
              {filtering && (
                <div style={{ padding: 32, textAlign: 'center', color: 'var(--clr-text-muted)' }}>
                  <span className="spinner" aria-hidden="true" />
                  <span style={{ marginLeft: 8 }}>Computing…</span>
                </div>
              )}
              {!filtering && filteredData && (() => {
                const filteredNonUkSections = filteredData.nonUkSections.filter(
                  s => s.output_type === nonUkOutputType && s.period === nonUkPeriod
                )
                return <>
                  {isNonUk && <NonUkCategorySections sections={filteredNonUkSections} />}
                  {!isNonUk && activeSection?.tableType === 'monthly' && (
                    <ExcelPivotSection
                      tables={findMetric(filteredData.metrics, activeSection.metricKey)?.monthly ?? []}
                      isDelta={false}
                    />
                  )}
                  {!isNonUk && activeSection?.tableType === 'yearlyDelta' && (
                    <YearlyDeltaSection
                      tables={findMetric(filteredData.metrics, activeSection.metricKey)?.deltas ?? []}
                      metric={activeSection.column}
                    />
                  )}
                </>
              })()}
            </div>
          )}

          {/* Filter 2 comparison pane */}
          {(filteredData2 || filtering2) && (
            <div style={{ flex: 1, minWidth: 0, overflowX: 'auto', borderLeft: '2px solid var(--clr-blue)', paddingLeft: 24 }}>
              <p style={{ margin: '0 0 8px', fontSize: 11, fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.08em', color: 'var(--clr-blue)' }}>
                {activeFilters2 ? filterLabel(activeFilters2) : 'Filter 2'}
              </p>
              {filtering2 && (
                <div style={{ padding: 32, textAlign: 'center', color: 'var(--clr-text-muted)' }}>
                  <span className="spinner" aria-hidden="true" />
                  <span style={{ marginLeft: 8 }}>Computing…</span>
                </div>
              )}
              {!filtering2 && filteredData2 && (() => {
                const filteredNonUkSections2 = filteredData2.nonUkSections.filter(
                  s => s.output_type === nonUkOutputType && s.period === nonUkPeriod
                )
                return <>
                  {isNonUk && <NonUkCategorySections sections={filteredNonUkSections2} />}
                  {!isNonUk && activeSection?.tableType === 'monthly' && (
                    <ExcelPivotSection
                      tables={findMetric(filteredData2.metrics, activeSection.metricKey)?.monthly ?? []}
                      isDelta={false}
                    />
                  )}
                  {!isNonUk && activeSection?.tableType === 'yearlyDelta' && (
                    <YearlyDeltaSection
                      tables={findMetric(filteredData2.metrics, activeSection.metricKey)?.deltas ?? []}
                      metric={activeSection.column}
                    />
                  )}
                </>
              })()}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}



