import React, { useState } from 'react'
import type { UploadContext, ScenarioRow } from '../App'

interface Props {
  uploadCtx: UploadContext
  onBack: () => void
  onSuccess: () => void
}

// Chain state for IV and EV
interface ChainState {
  iv: number[]
  ev: number[]
}

// Mirrors the backend build_delta_pairs logic
interface DeltaPairDisplay {
  leftName: string
  rightName: string
  type: 'step' | 'cumulative'
  stepNumber: number | null
}

function computeDeltaPairs(
  chain: number[],
  scenarios: ScenarioRow[],
): DeltaPairDisplay[] {
  const nameOf = (idx: number) =>
    scenarios.find(s => s.index === idx)?.scenarioName ?? `Scenario ${idx}`

  const pairs: DeltaPairDisplay[] = []
  for (let i = 1; i < chain.length; i++) {
    pairs.push({
      leftName: nameOf(chain[i - 1]),
      rightName: nameOf(chain[i]),
      type: 'step',
      stepNumber: i,
    })
  }
  if (chain.length > 2) {
    pairs.push({
      leftName: nameOf(chain[0]),
      rightName: nameOf(chain[chain.length - 1]),
      type: 'cumulative',
      stepNumber: null,
    })
  }
  return pairs
}

export function ConfigurePage({ uploadCtx, onBack, onSuccess }: Props) {
  const { scenarios, machines, uploadId, fileName } = uploadCtx

  // Start with the first two scenarios as the default chain; user edits from there
  const fallback = scenarios.slice(0, 2).map(s => s.index)

  const [chains, setChains] = useState<ChainState>(() => ({ iv: fallback, ev: fallback }))
  const [selectedMachines, setSelectedMachines] = useState<string[] | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function handleGenerate() {
    setLoading(true)
    setError(null)
    try {
      const body = {
        upload_id: uploadId,
        iv_chain: chains.iv,
        ev_chain: chains.ev,
        selected_machines: selectedMachines,
      }
      const res = await fetch('/api/reports/generate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      })
      if (!res.ok) {
        const d = await res.json().catch(() => ({}))
        throw new Error((d as { detail?: string })?.detail ?? `Generation failed (${res.status})`)
      }
      onSuccess()
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Report generation failed.')
    } finally {
      setLoading(false)
    }
  }

  const allMachinesSel = selectedMachines === null

  return (
    <div className="page-container">
      <div className="page-header">
        <h1 className="page-title">Configure Report</h1>
        <p className="page-subtitle">
          File: <strong>{fileName}</strong> · {scenarios.length} scenarios found
        </p>
      </div>

      {/* Scenario table */}
      <div className="card" style={{ padding: 0 }}>
        <div style={{ padding: 'var(--sp-4) var(--sp-6)', borderBottom: '1px solid var(--clr-border)' }}>
          <p className="section-label">Available scenarios</p>
        </div>
        <div className="table-wrapper" style={{ border: 'none', borderRadius: 0 }}>
          <table className="table">
            <thead>
              <tr>
                <th style={{ width: 48 }}>Idx</th>
                <th>Scenario Name</th>
                <th>Scenario ID</th>
                <th>Type</th>
              </tr>
            </thead>
            <tbody>
              {scenarios.map((s) => (
                <tr key={s.index}>
                  <td>
                    <code style={{ fontFamily: 'var(--font-mono)', fontSize: 'var(--text-xs)', background: 'var(--clr-bg)', padding: '1px 5px', borderRadius: 3 }}>
                      {s.index}
                    </code>
                  </td>
                  <td style={{ fontWeight: 'var(--weight-medium)' }}>{s.scenarioName}</td>
                  <td style={{ color: 'var(--clr-text-muted)', fontSize: 'var(--text-xs)' }}>{s.scenarioId}</td>
                  <td><span className="badge badge--navy">{s.scenarioType}</span></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Chain selectors */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 'var(--sp-6)' }}>
        <ChainEditor
          label="IV Scenario Chain"
          description="INTRINSIC_VALUE + POWER_POS"
          chain={chains.iv}
          scenarios={scenarios}
          deltaPairs={computeDeltaPairs(chains.iv, scenarios)}
          onChange={(iv) => setChains(c => ({ ...c, iv }))}
        />
        <ChainEditor
          label="EV Scenario Chain"
          description="EXTRINSIC_VALUE"
          chain={chains.ev}
          scenarios={scenarios}
          onChange={(ev) => setChains(c => ({ ...c, ev }))}
          deltaPairs={computeDeltaPairs(chains.ev, scenarios)}
        />
      </div>

      {/* Machine filter */}
      <div className="card">
        <p className="section-label">Machine Filter</p>
        <div style={{ display: 'flex', gap: 'var(--sp-3)', alignItems: 'center', flexWrap: 'wrap' }}>
          <label style={{ display: 'flex', alignItems: 'center', gap: 'var(--sp-2)', cursor: 'pointer', fontSize: 'var(--text-sm)' }}>
            <input
              type="checkbox"
              checked={allMachinesSel}
              onChange={() => setSelectedMachines(allMachinesSel ? [] : null)}
              style={{ accentColor: 'var(--clr-blue)', width: 16, height: 16 }}
            />
            All machines
          </label>
          {!allMachinesSel && (
            <span className="badge badge--blue">
              {selectedMachines?.length ?? 0} selected
            </span>
          )}
        </div>
        {!allMachinesSel && (
          <div style={{ marginTop: 'var(--sp-3)', display: 'flex', flexWrap: 'wrap', gap: 'var(--sp-2)' }}>
            {machines.map(m => (
              <label
                key={m}
                style={{ display: 'flex', alignItems: 'center', gap: 'var(--sp-1)', cursor: 'pointer', fontSize: 'var(--text-xs)', background: 'var(--clr-bg)', border: '1px solid var(--clr-border)', borderRadius: 'var(--radius-md)', padding: '3px 8px' }}
              >
                <input
                  type="checkbox"
                  checked={selectedMachines?.includes(m) ?? false}
                  onChange={() => {
                    setSelectedMachines(prev => {
                      const list = prev ?? []
                      return list.includes(m) ? list.filter(x => x !== m) : [...list, m]
                    })
                  }}
                  style={{ accentColor: 'var(--clr-blue)', width: 13, height: 13 }}
                />
                {m}
              </label>
            ))}
          </div>
        )}
      </div>

      {/* Error */}
      {error && (
        <div className="alert alert--error" role="alert">
          {error}
        </div>
      )}

      {/* Actions */}
      <div style={{ display: 'flex', justifyContent: 'space-between', gap: 'var(--sp-4)' }}>
        <button className="btn btn--ghost" onClick={onBack} disabled={loading}>
          ← Back
        </button>
        <button
          className="btn btn--primary btn--lg"
          onClick={handleGenerate}
          disabled={loading || chains.iv.length < 2 || chains.ev.length < 2}
        >
          {loading ? (
            <><span className="spinner spinner--sm" aria-hidden="true" />Generating…</>
          ) : (
            <>Generate Report →</>
          )}
        </button>
      </div>
    </div>
  )
}

// Chain editor sub-component
interface ChainEditorProps {
  label: string
  description: string
  chain: number[]
  scenarios: ScenarioRow[]
  deltaPairs: DeltaPairDisplay[]
  onChange: (chain: number[]) => void
}

function ChainEditor({ label, description, chain, scenarios, deltaPairs, onChange }: ChainEditorProps) {
  const [adding, setAdding] = useState(false)
  const [addIdx, setAddIdx] = useState<number>(scenarios[0]?.index ?? 0)

  const nameOf = (idx: number) =>
    scenarios.find(s => s.index === idx)?.scenarioName ?? `Scenario ${idx}`

  function removeAt(pos: number) {
    onChange(chain.filter((_, i) => i !== pos))
  }

  function addToChain() {
    if (chain.includes(addIdx)) return
    onChange([...chain, addIdx])
    setAdding(false)
  }

  return (
    <div className="card">
      <div style={{ marginBottom: 'var(--sp-3)' }}>
        <p className="section-label">{label}</p>
        <p style={{ fontSize: 'var(--text-xs)', color: 'var(--clr-text-muted)' }}>{description}</p>
      </div>

      {chain.length === 0 && (
        <p style={{ fontSize: 'var(--text-sm)', color: 'var(--clr-text-muted)', fontStyle: 'italic' }}>
          No scenarios added yet.
        </p>
      )}

      <div className="chain-row">
        {chain.map((idx, pos) => {
          const pillClass =
            pos === 0               ? 'chain-pill chain-pill--base'   :
            pos === chain.length - 1 ? 'chain-pill chain-pill--final'  :
                                      'chain-pill chain-pill--middle'
          return (
            <React.Fragment key={idx}>
              {pos > 0 && <span className="chain-arrow" aria-hidden="true">→</span>}
              <span className={pillClass}>
                <code style={{ fontSize: 'var(--text-xs)', opacity: 0.6 }}>{idx}</code>
                {nameOf(idx).length > 28 ? nameOf(idx).slice(-26) + '…' : nameOf(idx)}
                <button
                  type="button"
                  onClick={() => removeAt(pos)}
                  style={{ background: 'none', border: 'none', padding: 0, color: 'var(--clr-text-muted)', fontSize: 11, lineHeight: 1, cursor: 'pointer', marginLeft: 2 }}
                  aria-label={`Remove ${nameOf(idx)}`}
                >
                  ✕
                </button>
              </span>
            </React.Fragment>
          )
        })}
      </div>

      {adding ? (
        <div style={{ display: 'flex', gap: 'var(--sp-2)', marginTop: 'var(--sp-3)' }}>
          <select
            className="select"
            value={addIdx}
            onChange={e => setAddIdx(Number(e.target.value))}
            style={{ flex: 1 }}
          >
            {scenarios
              .filter(s => !chain.includes(s.index))
              .map(s => (
                <option key={s.index} value={s.index}>
                  [{s.index}] {s.scenarioName}
                </option>
              ))}
          </select>
          <button className="btn btn--primary btn--sm" onClick={addToChain}>Add</button>
          <button className="btn btn--ghost btn--sm" onClick={() => setAdding(false)}>Cancel</button>
        </div>
      ) : (
        <button
          className="btn btn--ghost btn--sm"
          style={{ marginTop: 'var(--sp-3)' }}
          onClick={() => setAdding(true)}
          disabled={chain.length >= scenarios.length}
        >
          + Add scenario
        </button>
      )}

      {chain.length >= 2 && (
        <div style={{ marginTop: 'var(--sp-4)', borderTop: '1px solid var(--clr-border)', paddingTop: 'var(--sp-3)' }}>
          <p style={{ fontSize: 'var(--text-xs)', fontWeight: 'var(--weight-medium)', color: 'var(--clr-text-muted)', textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: 'var(--sp-2)' }}>
            Computed deltas
          </p>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--sp-1)' }}>
            {deltaPairs.map((p, i) => (
              <div key={i} style={{ display: 'flex', alignItems: 'center', gap: 'var(--sp-2)', fontSize: 'var(--text-xs)' }}>
                <span style={{
                  display: 'inline-block', minWidth: 80,
                  padding: '1px 6px', borderRadius: 'var(--radius-sm)', textAlign: 'center',
                  background: p.type === 'cumulative' ? 'var(--clr-blue-light)' : 'var(--clr-bg)',
                  border: `1px solid ${p.type === 'cumulative' ? 'var(--clr-blue)' : 'var(--clr-border)'}`,
                  color: p.type === 'cumulative' ? 'var(--clr-blue)' : 'var(--clr-text-muted)',
                  fontWeight: p.type === 'cumulative' ? 'var(--weight-medium)' : 'normal',
                }}>
                  {p.type === 'cumulative' ? 'Cumulative' : `Step ${p.stepNumber}`}
                </span>
                <span style={{ color: 'var(--clr-text-muted)' }}>{p.leftName}</span>
                <span style={{ color: 'var(--clr-text-muted)' }}>→</span>
                <span style={{ color: 'var(--clr-text)', fontWeight: 'var(--weight-medium)' }}>{p.rightName}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
