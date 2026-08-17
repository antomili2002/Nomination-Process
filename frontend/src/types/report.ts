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

export interface MetricInfo {
  key: string
  label: string
  column: string
  category: string
  defaultSelected: boolean
}

export interface MetricSection {
  key: string
  label: string
  column: string
  monthly: PivotTableData[]
  deltas: YearlyDeltaTable[]
}

export interface NonUkReportColumn {
  label: string
  kind: string
}

export interface NonUkReportRow {
  metric_key: string
  metric_label: string
  metric_column: string
  year: number
  month?: number | null
  values: number[]
}

export interface NonUkReportSection {
  output_type: 'IV' | 'EV'
  period: 'monthly' | 'yearly'
  category: string
  columns: NonUkReportColumn[]
  rows: NonUkReportRow[]
}

export interface ReportData {
  reportId: string
  uploadId: string
  portfolioCountry: string
  layout: 'uk' | 'non_uk'
  ivChain: number[]
  evChain: number[]
  machines: string[]
  selectedMachines: string[] | null
  selectedMetrics: string[]
  metrics: MetricSection[]
  nonUkSections: NonUkReportSection[]
}

