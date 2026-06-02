import { useState } from 'react'
import './App.css'
import { Header } from './components/Header'
import { StepIndicator } from './components/StepIndicator'
import { UploadPage } from './pages/UploadPage'
import { ConfigurePage } from './pages/ConfigurePage'
import { ResultPage } from './pages/ResultPage'
import type { PivotTableData } from './components/PivotTable'

export type AppStep = 'upload' | 'configure' | 'result'

export interface UploadContext {
  uploadId: string
  fileName: string
  scenarios: ScenarioRow[]
  machines: string[]
}

export interface ScenarioRow {
  index: number
  scenarioName: string
  scenarioId: number
  marketArea: string
  scenarioType: string
  status: string
  role: string | null
}

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
  reportId:        string
  uploadId:        string
  ivChain:         number[]
  evChain:         number[]
  machines:        string[]        // all available machines (from upload)
  selectedMachines: string[] | null // machines used for this report (null = all)
  evMonthly: PivotTableData[]
  evDeltas:  YearlyDeltaTable[]
  ivMonthly: PivotTableData[]
  ivDeltas:  YearlyDeltaTable[]
  ppMonthly: PivotTableData[]
  ppDeltas:  YearlyDeltaTable[]
}

function App() {
  const [step, setStep] = useState<AppStep>('upload')
  const [uploadCtx, setUploadCtx] = useState<UploadContext | null>(null)
  const [reportData, setReportData] = useState<ReportData | null>(null)

  return (
    <div style={{ display: 'flex', flexDirection: 'column', minHeight: '100vh' }}>
      <Header />

      <StepIndicator currentStep={step} />

      <main className="app-content">
        {step === 'upload' && (
          <UploadPage
            onSuccess={(ctx) => {
              setUploadCtx(ctx)
              setStep('configure')
            }}
          />
        )}

        {step === 'configure' && uploadCtx && (
          <ConfigurePage
            uploadCtx={uploadCtx}
            onBack={() => setStep('upload')}
            onSuccess={(data) => {
              setReportData(data)
              setStep('result')
            }}
          />
        )}

        {step === 'result' && reportData && (
          <ResultPage
            reportData={reportData}
            onReset={() => {
              setUploadCtx(null)
              setReportData(null)
              setStep('upload')
            }}
          />
        )}
      </main>

      <footer className="app-footer">
        Scenario Delta Report Generator - Uniper Energy SE
      </footer>
    </div>
  )
}

export default App
