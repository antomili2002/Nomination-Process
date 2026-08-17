import type { MetricSection } from './types/report'

export type TableType = 'monthly' | 'yearlyDelta'

export interface Section {
  id: string
  label: string
  metricKey: string
  metricLabel: string
  column: string
  tableType: TableType
}

/** Build sidebar sections (Monthly + Yearly Deltas per metric) from a report's metrics list. */
export function buildSections(metrics: MetricSection[]): Section[] {
  const sections: Section[] = []
  for (const m of metrics) {
    sections.push({ id: `${m.key}::monthly`, label: 'Monthly', metricKey: m.key, metricLabel: m.label, column: m.column, tableType: 'monthly' })
    sections.push({ id: `${m.key}::deltas`, label: 'Yearly Deltas', metricKey: m.key, metricLabel: m.label, column: m.column, tableType: 'yearlyDelta' })
  }
  return sections
}

export function findMetric(metrics: MetricSection[], key: string): MetricSection | undefined {
  return metrics.find(m => m.key === key)
}

export function sectionCount(metrics: MetricSection[], metricKey: string, tableType: TableType): number {
  const metric = findMetric(metrics, metricKey)
  if (!metric) return 0
  return tableType === 'monthly' ? metric.monthly.length : metric.deltas.length
}

