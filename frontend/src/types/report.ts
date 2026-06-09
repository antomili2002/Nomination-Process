import type { PivotTableData } from '../components/PivotTable'

export interface YearlyDeltaRow {
  year: number
  left_value: number
  right_value: number
  delta: number
}

export interface MachineYearlyDeltaRow extends YearlyDeltaRow {
  machine_name: string
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

export interface MachineYearlyDeltaTable extends Omit<YearlyDeltaTable, 'rows'> {
  rows: MachineYearlyDeltaRow[]
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
  evMachineDeltas: MachineYearlyDeltaTable[]
  ivMonthly: PivotTableData[]
  ivDeltas: YearlyDeltaTable[]
  ivMachineDeltas: MachineYearlyDeltaTable[]
  ppMonthly: PivotTableData[]
  ppDeltas: YearlyDeltaTable[]
  ppMachineDeltas: MachineYearlyDeltaTable[]
  ivHeatMonthly: PivotTableData[]
  ivHeatDeltas: YearlyDeltaTable[]
  ivHeatMachineDeltas: MachineYearlyDeltaTable[]
  heatProdMonthly: PivotTableData[]
  heatProdDeltas: YearlyDeltaTable[]
  heatProdMachineDeltas: MachineYearlyDeltaTable[]
}
