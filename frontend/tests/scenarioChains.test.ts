import test from 'node:test'
import assert from 'node:assert/strict'
import { buildInitialChains } from '../src/pages/scenarioChains.ts'

interface ScenarioRow {
  index: number
  scenarioName: string
  scenarioId: number
  marketArea: string
  scenarioType: string
  status: string
  role: string | null
}

function scenario(index: number, scenarioName: string, scenarioType: string): ScenarioRow {
  return {
    index,
    scenarioName,
    scenarioId: 100 + index,
    marketArea: 'UK',
    scenarioType,
    status: 'Active',
    role: null,
  }
}

test('buildInitialChains orders IV and EV scenarios by numeric name prefix', () => {
  const scenarios = [
    scenario(10, '2_Final_IV', 'IV'),
    scenario(20, '0_Base_EV', 'EV'),
    scenario(11, '0_Base_IV', 'IV'),
    scenario(21, '2_Final_EV', 'EV'),
    scenario(12, '1_Intermediate_IV', 'IV'),
    scenario(22, '1_Intermediate_EV', 'EV'),
  ]

  assert.deepEqual(buildInitialChains(scenarios), {
    iv: [11, 12, 10],
    ev: [20, 22, 21],
  })
})

test('buildInitialChains keeps non-conforming names after ordered names', () => {
  const scenarios = [
    scenario(1, 'Final_IV', 'IV'),
    scenario(2, '0_Base_IV', 'IV'),
    scenario(3, '10_Final_IV', 'IV'),
    scenario(4, 'Step_IV', 'IV'),
    scenario(5, '0_Base_EV', 'EV'),
    scenario(6, 'Final_EV', 'EV'),
  ]

  assert.deepEqual(buildInitialChains(scenarios), {
    iv: [2, 3, 1, 4],
    ev: [5, 6],
  })
})
