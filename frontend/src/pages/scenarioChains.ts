import type { ScenarioRow } from '../App'

export interface ChainState {
  iv: number[]
  ev: number[]
}

const EV_SCENARIO_RE = /(^|[^a-z0-9])ev([^a-z0-9]|$)/i
const IV_SCENARIO_RE = /(^|[^a-z0-9])iv([^a-z0-9]|$)/i
const SCENARIO_ORDER_RE = /^(\d+)_/

function isEvScenario(scenario: ScenarioRow): boolean {
  return EV_SCENARIO_RE.test(scenario.scenarioName) || scenario.scenarioType.toUpperCase() === 'EV'
}

function isIvScenario(scenario: ScenarioRow): boolean {
  return IV_SCENARIO_RE.test(scenario.scenarioName) || scenario.scenarioType.toUpperCase() === 'IV'
}

function scenarioOrder(scenario: ScenarioRow): number | null {
  const match = SCENARIO_ORDER_RE.exec(scenario.scenarioName)
  return match ? Number(match[1]) : null
}

function orderByNamingConvention(scenarios: ScenarioRow[]): ScenarioRow[] {
  return scenarios
    .map((scenario, uploadPosition) => ({
      scenario,
      uploadPosition,
      order: scenarioOrder(scenario),
    }))
    .sort((a, b) => {
      if (a.order !== null && b.order !== null) {
        return a.order - b.order || a.uploadPosition - b.uploadPosition
      }
      if (a.order !== null) return -1
      if (b.order !== null) return 1
      return a.uploadPosition - b.uploadPosition
    })
    .map(item => item.scenario)
}

export function buildInitialChains(scenarios: ScenarioRow[]): ChainState {
  const ev = orderByNamingConvention(scenarios.filter(isEvScenario)).map(s => s.index)
  const iv = orderByNamingConvention(scenarios.filter(s => isIvScenario(s) || !isEvScenario(s))).map(s => s.index)
  const fallback = orderByNamingConvention(scenarios).slice(0, 2).map(s => s.index)

  return {
    iv: iv.length >= 2 ? iv : fallback,
    ev: ev.length >= 2 ? ev : fallback,
  }
}
