import React, { useMemo, useRef, useState } from 'react'
import type { UploadContext, ScenarioRow, ReportData } from '../App'
import { buildApiUrl } from '../api'
import { buildInitialChains } from './scenarioChains'
import type { ChainState } from './scenarioChains'
import type { MetricInfo } from '../types/report'

function groupMetricsByCategory(metrics: MetricInfo[]): [string, MetricInfo[]][] {
  const groups = new Map<string, MetricInfo[]>()
  for (const m of metrics) {
    const list = groups.get(m.category)
    if (list) list.push(m)
    else groups.set(m.category, [m])
  }
  return [...groups.entries()]
}

interface Props {
  uploadCtx: UploadContext
  onBack: () => void
  onSuccess: (data: ReportData) => void
}

interface DeltaPair {
  leftName: string
  rightName: string
  type: 'step' | 'cumulative'
  stepNumber: number | null
}

function computeDeltaPairs(chain: number[], scenarios: ScenarioRow[]): DeltaPair[] {
  const nameOf = (idx: number) =>
    scenarios.find(s => s.index === idx)?.scenarioName ?? `Scenario ${idx}`
  const pairs: DeltaPair[] = []
  for (let i = 1; i < chain.length; i++) {
    pairs.push({ leftName: nameOf(chain[i - 1]), rightName: nameOf(chain[i]), type: 'step', stepNumber: i })
  }
  if (chain.length > 2) {
    pairs.push({ leftName: nameOf(chain[0]), rightName: nameOf(chain[chain.length - 1]), type: 'cumulative', stepNumber: null })
  }
  return pairs
}

type DragSrc =
  | { kind: 'scenario'; idx: number }
  | { kind: 'chain-item'; chain: 'iv' | 'ev'; pos: number }

export function ConfigurePage({ uploadCtx, onBack, onSuccess }: Props) {
const { scenarios, machines, uploadId, fileName, availableMetrics, asOfDate } = uploadCtx

  const [chains, setChains] = useState<ChainState>(() => buildInitialChains(scenarios))
  const [selectedMetrics, setSelectedMetrics] = useState<Set<string>>(
    () => new Set(availableMetrics.filter(m => m.defaultSelected).map(m => m.key))
  )
  const metricsByCategory = useMemo(() => groupMetricsByCategory(availableMetrics), [availableMetrics])

  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // Drag state
  const dragSrc = useRef<DragSrc | null>(null)
  const [dropTarget, setDropTarget] = useState<{ chain: 'iv' | 'ev'; pos: number | null } | null>(null)

  function onScenarioDragStart(e: React.DragEvent, idx: number) {
    dragSrc.current = { kind: 'scenario', idx }
    e.dataTransfer.effectAllowed = 'copy'
  }

  function onChainItemDragStart(e: React.DragEvent, chain: 'iv' | 'ev', pos: number) {
    e.stopPropagation()
    dragSrc.current = { kind: 'chain-item', chain, pos }
    e.dataTransfer.effectAllowed = 'move'
  }

  function onChainDrop(e: React.DragEvent, chain: 'iv' | 'ev', insertAt: number | null) {
    e.preventDefault()
    e.stopPropagation()
    const src = dragSrc.current
    if (!src) return
    setChains(prev => {
      const arr = [...prev[chain]]
      if (src.kind === 'scenario') {
        if (arr.includes(src.idx)) return prev
        const pos = insertAt ?? arr.length
        arr.splice(pos, 0, src.idx)
      } else if (src.kind === 'chain-item' && src.chain === chain) {
        const [item] = arr.splice(src.pos, 1)
        const pos = insertAt !== null ? insertAt : arr.length
        arr.splice(pos, 0, item)
      }
      return { ...prev, [chain]: arr }
    })
    dragSrc.current = null
    setDropTarget(null)
  }

  function onChainRemove(chain: 'iv' | 'ev', pos: number) {
    setChains(prev => ({ ...prev, [chain]: prev[chain].filter((_, i) => i !== pos) }))
  }

  function toggleMetric(key: string) {
    setSelectedMetrics(prev => {
      const next = new Set(prev)
      if (next.has(key)) { if (next.size > 1) next.delete(key) }
      else next.add(key)
      return next
    })
  }

  async function handleGenerate() {
    setLoading(true)
    setError(null)
    try {
      const body = {
        upload_id: uploadId,
        iv_chain: chains.iv,
        ev_chain: chains.ev,
        selected_machines: null,
        selected_metrics: [...selectedMetrics],
      }
      const res = await fetch(buildApiUrl('/reports/generate'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      })
      if (!res.ok) {
        const d = await res.json().catch(() => ({}))
        throw new Error((d as { detail?: string })?.detail ?? `Generation failed (${res.status})`)
      }
      const payload = await res.json()
      onSuccess({
        reportId:        payload.report_id,
        uploadId:        uploadId,
        asOfDate:        asOfDate,
        portfolioCountry: payload.portfolio_country,
        layout:          payload.layout,
        ivChain:         chains.iv,
        evChain:         chains.ev,
        machines:        machines,
        selectedMachines: null,
        selectedMetrics: [...selectedMetrics],
        metrics: payload.metrics,
        nonUkSections: payload.non_uk_sections,
      })
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Report generation failed.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="page-container">
      <div className="page-header">
        <h1 className="page-title">Configure Report</h1>
        <p className="page-subtitle">
          File: <strong>{fileName}</strong> · {scenarios.length} scenarios found
        </p>
      </div>

      {/* Scenario table — rows are draggable */}
      <div className="card" style={{ padding: 0 }}>
        <div style={{ padding: 'var(--sp-4) var(--sp-6)', borderBottom: '1px solid var(--clr-border)' }}>
          <p className="section-label">Available scenarios</p>
          <p style={{ fontSize: 'var(--text-xs)', color: 'var(--clr-text-muted)', marginTop: 4 }}>
            Scenario chains are pre-filled from EV/IV naming and numeric prefixes like 0_, 1_, 2_. Drag rows below only when you need to adjust the order.
          </p>
        </div>
        <div className="table-wrapper" style={{ border: 'none', borderRadius: 0 }}>
          <table className="table">
            <thead>
              <tr>
                <th style={{ width: 28 }} />
                <th style={{ width: 44 }}>Idx</th>
                <th>Scenario Name</th>
                <th>ID</th>
                <th>Type</th>
              </tr>
            </thead>
            <tbody>
              {scenarios.map(s => (
                <tr
                  key={s.index}
                  draggable
                  onDragStart={e => onScenarioDragStart(e, s.index)}
                  style={{ cursor: 'grab', userSelect: 'none' }}
                >
                  <td style={{ color: 'var(--clr-blue)', textAlign: 'center', fontSize: 16, opacity: 0.5 }}>⠿</td>
                  <td>
                    <code style={{ fontFamily: 'var(--font-mono)', fontSize: 'var(--text-xs)', background: 'var(--clr-bg)', padding: '1px 5px', borderRadius: 3 }}>
                      {s.index}
                    </code>
                  </td>
                  <td style={{ fontWeight: 'var(--weight-medium)' }}>{s.scenarioName}</td>
                  <td style={{ color: 'var(--clr-text-muted)', fontSize: 'var(--text-xs)' }}>{s.scenarioId}</td>
                  <td><span className="badge badge--navy">{s.scenarioType || '—'}</span></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Chain drop zones */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 'var(--sp-6)' }}>
        {(['iv', 'ev'] as const).map(chain => {
          const items = chains[chain]
          const label = chain === 'iv' ? 'IV Scenario Chain' : 'EV Scenario Chain'
          const desc  = chain === 'iv'
            ? 'INTRINSIC_VALUE, POWER_POS, IV_HEAT_COST, HEAT_PRODUCTION_GWH'
            : 'EXTRINSIC_VALUE'
          const deltas = computeDeltaPairs(items, scenarios)
          const zoneActive = dropTarget?.chain === chain
          const nameOf = (idx: number) =>
            scenarios.find(s => s.index === idx)?.scenarioName ?? `Scenario ${idx}`

          return (
            <div
              key={chain}
              className="card"
              onDragOver={e => { e.preventDefault(); if (!dropTarget || dropTarget.chain !== chain) setDropTarget({ chain, pos: null }) }}
              onDragLeave={e => { if (!e.currentTarget.contains(e.relatedTarget as Node)) setDropTarget(null) }}
              onDrop={e => onChainDrop(e, chain, null)}
              style={{ borderColor: zoneActive ? 'var(--clr-blue)' : undefined, transition: 'border-color 0.15s' }}
            >
              <div style={{ marginBottom: 'var(--sp-3)' }}>
                <p className="section-label">{label}</p>
                <p style={{ fontSize: 'var(--text-xs)', color: 'var(--clr-text-muted)' }}>{desc}</p>
              </div>

              {items.length === 0 ? (
                <div style={{
                  border: '2px dashed var(--clr-border)', borderRadius: 'var(--radius-md)',
                  padding: 'var(--sp-6)', textAlign: 'center',
                  color: 'var(--clr-text-muted)', fontSize: 'var(--text-sm)',
                  background: zoneActive ? 'var(--clr-blue-light)' : undefined,
                  transition: 'background 0.15s',
                }}>
                  Drop scenario here
                </div>
              ) : (
                <div style={{ display: 'flex', flexDirection: 'column' }}>
                  {items.map((idx, pos) => {
                    const isBase  = pos === 0
                    const isFinal = pos === items.length - 1
                    const pillClass = isBase ? 'chain-pill chain-pill--base' : isFinal ? 'chain-pill chain-pill--final' : 'chain-pill chain-pill--middle'
                    const posLabel  = isBase ? 'Base' : isFinal ? 'Final' : `Step ${pos}`
                    const insertHere = dropTarget?.chain === chain && dropTarget.pos === pos

                    return (
                      <React.Fragment key={idx}>
                        {/* Insert-before drop indicator */}
                        <div
                          style={{
                            height: insertHere ? 3 : 2, margin: '2px 0', borderRadius: 2,
                            background: insertHere ? 'var(--clr-blue)' : 'transparent',
                            transition: 'all 0.1s',
                          }}
                          onDragOver={e => { e.preventDefault(); e.stopPropagation(); setDropTarget({ chain, pos }) }}
                          onDrop={e => onChainDrop(e, chain, pos)}
                        />

                        {/* Chain item */}
                        <div
                          draggable
                          onDragStart={e => onChainItemDragStart(e, chain, pos)}
                          style={{ display: 'flex', alignItems: 'center', gap: 'var(--sp-2)', marginBottom: 2 }}
                        >
                          <span style={{ color: 'var(--clr-text-muted)', fontSize: 13, cursor: 'grab', flexShrink: 0 }}>⠿</span>
                          <div style={{ flex: 1, minWidth: 0 }}>
                            <div style={{ fontSize: 9, fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.08em', color: isBase || isFinal ? 'var(--clr-blue)' : 'var(--clr-text-muted)', marginBottom: 2 }}>
                              {posLabel}
                            </div>
                            <span className={pillClass} style={{ display: 'flex', alignItems: 'center', gap: 6, width: '100%' }}>
                              <code style={{ fontSize: 'var(--text-xs)', opacity: 0.6, flexShrink: 0 }}>{idx}</code>
                              <span style={{ flex: 1, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                                {nameOf(idx)}
                              </span>
                              <button
                                type="button"
                                onClick={() => onChainRemove(chain, pos)}
                                style={{ background: 'none', border: 'none', padding: 0, color: 'var(--clr-text-muted)', fontSize: 11, cursor: 'pointer', flexShrink: 0 }}
                                aria-label={`Remove ${nameOf(idx)}`}
                              >✕</button>
                            </span>
                          </div>
                        </div>
                      </React.Fragment>
                    )
                  })}

                  {/* Append-at-end drop indicator */}
                  <div
                    style={{
                      height: zoneActive && dropTarget?.pos === null ? 3 : 2, margin: '2px 0', borderRadius: 2,
                      background: zoneActive && dropTarget?.pos === null ? 'var(--clr-blue)' : 'transparent',
                      transition: 'all 0.1s',
                    }}
                    onDragOver={e => { e.preventDefault(); e.stopPropagation(); setDropTarget({ chain, pos: null }) }}
                    onDrop={e => onChainDrop(e, chain, null)}
                  />
                </div>
              )}

              {/* Computed delta pairs */}
              {deltas.length > 0 && (
                <div style={{ marginTop: 'var(--sp-4)', borderTop: '1px solid var(--clr-border)', paddingTop: 'var(--sp-3)' }}>
                  <p style={{ fontSize: 'var(--text-xs)', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.06em', color: 'var(--clr-text-muted)', marginBottom: 'var(--sp-2)' }}>
                    Computed deltas
                  </p>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--sp-1)' }}>
                    {deltas.map((p, i) => (
                      <div key={i} style={{ display: 'flex', alignItems: 'center', gap: 'var(--sp-2)', fontSize: 'var(--text-xs)' }}>
                        <span style={{
                          display: 'inline-block', minWidth: 80, padding: '1px 6px',
                          borderRadius: 'var(--radius-sm)', textAlign: 'center',
                          background: p.type === 'cumulative' ? 'var(--clr-blue-light)' : 'var(--clr-bg)',
                          border: `1px solid ${p.type === 'cumulative' ? 'var(--clr-blue)' : 'var(--clr-border)'}`,
                          color: p.type === 'cumulative' ? 'var(--clr-blue)' : 'var(--clr-text-muted)',
                          fontWeight: p.type === 'cumulative' ? 'var(--weight-medium)' : 'normal',
                        }}>
                          {p.type === 'cumulative' ? 'Cumulative' : `Step ${p.stepNumber}`}
                        </span>
                        <span style={{ color: 'var(--clr-text-muted)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{p.leftName}</span>
                        <span style={{ color: 'var(--clr-text-muted)', flexShrink: 0 }}>→</span>
                        <span style={{ color: 'var(--clr-text)', fontWeight: 'var(--weight-medium)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{p.rightName}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )
        })}
      </div>

      {/* Metric selection — dynamic based on the columns found in the uploaded file */}
      <div className="card">
        <div style={{ marginBottom: 'var(--sp-3)' }}>
          <p className="section-label">Metrics to include</p>
          <p style={{ fontSize: 'var(--text-xs)', color: 'var(--clr-text-muted)' }}>
            Detected from the uploaded file, grouped by category. Only selected metrics get monthly and yearly delta tables.
          </p>
        </div>
        {availableMetrics.length === 0 ? (
          <p style={{ color: 'var(--clr-text-muted)', fontSize: 'var(--text-sm)' }}>
            No known metric columns were found in this file.
          </p>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--sp-4)' }}>
            {metricsByCategory.map(([category, metrics]) => (
              <div key={category}>
                <p style={{ fontSize: 'var(--text-xs)', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.06em', color: 'var(--clr-text-muted)', marginBottom: 'var(--sp-2)' }}>
                  {category}
                </p>
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: 'var(--sp-3)' }}>
                  {metrics.map(m => (
                    <label
                      key={m.key}
                      style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 'var(--text-sm)', cursor: 'pointer' }}
                    >
                      <input
                        type="checkbox"
                        checked={selectedMetrics.has(m.key)}
                        onChange={() => toggleMetric(m.key)}
                      />
                      {m.label}
                    </label>
                  ))}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {error && <div className="alert alert--error" role="alert">{error}</div>}

      <div style={{ display: 'flex', justifyContent: 'space-between', gap: 'var(--sp-4)' }}>
        <button className="btn btn--ghost" onClick={onBack} disabled={loading}>← Back</button>
        <button
          className="btn btn--primary btn--lg"
          onClick={handleGenerate}
          disabled={loading || chains.iv.length < 2 || chains.ev.length < 2 || selectedMetrics.size === 0}
        >
          {loading
            ? <><span className="spinner spinner--sm" aria-hidden="true" />Generating…</>
            : <>Generate Report →</>
          }
        </button>
      </div>
    </div>
  )
}

