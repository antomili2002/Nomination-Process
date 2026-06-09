import type { PivotTableData } from './components/PivotTable'
import type { MachineYearlyDeltaTable, ReportData, YearlyDeltaTable } from './types/report'

export type SectionId =
  | 'ev-monthly' | 'ev-deltas' | 'ev-machine-deltas'
  | 'iv-monthly' | 'iv-deltas' | 'iv-machine-deltas'
  | 'pp-monthly' | 'pp-deltas' | 'pp-machine-deltas'
  | 'iv-heat-monthly' | 'iv-heat-deltas' | 'iv-heat-machine-deltas'
  | 'heat-prod-monthly' | 'heat-prod-deltas' | 'heat-prod-machine-deltas'

export type ReportGroup = 'EV' | 'IV' | 'Power Position' | 'IV Heat' | 'Heat Production'
export type TableType = 'monthly' | 'yearlyDelta' | 'machineYearlyDelta'

export interface Section {
  id: SectionId
  label: string
  metric: string
  group: ReportGroup
  tableType: TableType
  dataKey: keyof ReportData
}

export const SECTIONS: Section[] = [
  { id: 'ev-monthly', label: 'Monthly', metric: 'EXTRINSIC_VALUE', group: 'EV', tableType: 'monthly', dataKey: 'evMonthly' },
  { id: 'ev-deltas', label: 'Yearly Deltas', metric: 'EXTRINSIC_VALUE', group: 'EV', tableType: 'yearlyDelta', dataKey: 'evDeltas' },
  { id: 'ev-machine-deltas', label: 'Machine Yearly Deltas', metric: 'EXTRINSIC_VALUE', group: 'EV', tableType: 'machineYearlyDelta', dataKey: 'evMachineDeltas' },
  { id: 'iv-monthly', label: 'Monthly', metric: 'INTRINSIC_VALUE__CUR', group: 'IV', tableType: 'monthly', dataKey: 'ivMonthly' },
  { id: 'iv-deltas', label: 'Yearly Deltas', metric: 'INTRINSIC_VALUE__CUR', group: 'IV', tableType: 'yearlyDelta', dataKey: 'ivDeltas' },
  { id: 'iv-machine-deltas', label: 'Machine Yearly Deltas', metric: 'INTRINSIC_VALUE__CUR', group: 'IV', tableType: 'machineYearlyDelta', dataKey: 'ivMachineDeltas' },
  { id: 'pp-monthly', label: 'Monthly', metric: 'POWER_POS__GWH', group: 'Power Position', tableType: 'monthly', dataKey: 'ppMonthly' },
  { id: 'pp-deltas', label: 'Yearly Deltas', metric: 'POWER_POS__GWH', group: 'Power Position', tableType: 'yearlyDelta', dataKey: 'ppDeltas' },
  { id: 'pp-machine-deltas', label: 'Machine Yearly Deltas', metric: 'POWER_POS__GWH', group: 'Power Position', tableType: 'machineYearlyDelta', dataKey: 'ppMachineDeltas' },
  { id: 'iv-heat-monthly', label: 'Monthly', metric: 'IV_INCL_HEAT_COSTS', group: 'IV Heat', tableType: 'monthly', dataKey: 'ivHeatMonthly' },
  { id: 'iv-heat-deltas', label: 'Yearly Deltas', metric: 'IV_INCL_HEAT_COSTS', group: 'IV Heat', tableType: 'yearlyDelta', dataKey: 'ivHeatDeltas' },
  { id: 'iv-heat-machine-deltas', label: 'Machine Yearly Deltas', metric: 'IV_INCL_HEAT_COSTS', group: 'IV Heat', tableType: 'machineYearlyDelta', dataKey: 'ivHeatMachineDeltas' },
  { id: 'heat-prod-monthly', label: 'Monthly', metric: 'HEAT_PRODUCTION__GWH', group: 'Heat Production', tableType: 'monthly', dataKey: 'heatProdMonthly' },
  { id: 'heat-prod-deltas', label: 'Yearly Deltas', metric: 'HEAT_PRODUCTION__GWH', group: 'Heat Production', tableType: 'yearlyDelta', dataKey: 'heatProdDeltas' },
  { id: 'heat-prod-machine-deltas', label: 'Machine Yearly Deltas', metric: 'HEAT_PRODUCTION__GWH', group: 'Heat Production', tableType: 'machineYearlyDelta', dataKey: 'heatProdMachineDeltas' },
]

export const REPORT_GROUPS: ReportGroup[] = ['EV', 'IV', 'Power Position', 'IV Heat', 'Heat Production']

export function getSection(id: SectionId): Section {
  return SECTIONS.find(s => s.id === id)!
}

export function getMonthlyTables(d: ReportData, id: SectionId): PivotTableData[] {
  const section = getSection(id)
  if (section.tableType !== 'monthly') return []
  return d[section.dataKey] as PivotTableData[]
}

export function getYearlyDeltas(d: ReportData, id: SectionId): YearlyDeltaTable[] {
  const section = getSection(id)
  if (section.tableType !== 'yearlyDelta') return []
  return d[section.dataKey] as YearlyDeltaTable[]
}

export function getMachineYearlyDeltas(d: ReportData, id: SectionId): MachineYearlyDeltaTable[] {
  const section = getSection(id)
  if (section.tableType !== 'machineYearlyDelta') return []
  return d[section.dataKey] as MachineYearlyDeltaTable[]
}

export function getSectionCount(d: ReportData, id: SectionId): number {
  const section = getSection(id)
  if (section.tableType === 'monthly') return getMonthlyTables(d, id).length
  if (section.tableType === 'yearlyDelta') return getYearlyDeltas(d, id).length
  return getMachineYearlyDeltas(d, id).length
}
