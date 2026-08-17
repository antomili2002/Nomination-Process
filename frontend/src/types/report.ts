import type { PivotTableData } from '../components/PivotTable'

export interface YearlyDeltaRow {
  year: number
  left_value: number
  right_value: number
  delta: number
}

export interface YearlyDeltaTable {
  left_name: string
  right_name: string
  pair_type: string
  step_number: number | null
  rows: YearlyDeltaRow[]
  left_total: number
  right_total: number
  delta_total: number
}

export interface ReportData {
  reportId: string
  uploadId: string
  ivChain: number[]
  evChain: number[]
  machines: string[]
  selectedMachines: string[] | null
  evMonthly: PivotTableData[]
  evDeltas: YearlyDeltaTable[]
  ivMonthly: PivotTableData[]
  ivDeltas: YearlyDeltaTable[]
  ppMonthly: PivotTableData[]
  ppDeltas: YearlyDeltaTable[]
  ivHeatMonthly: PivotTableData[]
  ivHeatDeltas: YearlyDeltaTable[]
  heatProdMonthly: PivotTableData[]
  heatProdDeltas: YearlyDeltaTable[]
}

