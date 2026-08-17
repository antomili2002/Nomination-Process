import { useState } from 'react'
import './App.css'
import { Header } from './components/Header'
import { StepIndicator } from './components/StepIndicator'
import { UploadPage } from './pages/UploadPage'
import { ConfigurePage } from './pages/ConfigurePage'
import { ResultPage } from './pages/ResultPage'
import type { MetricInfo, ReportData } from './types/report'
export type { ReportData } from './types/report'

export type AppStep = 'upload' | 'configure' | 'result'

export interface UploadContext {
  uploadId: string
  fileName: string
  portfolioCountry: string
  asOfDate: string | null
  scenarios: ScenarioRow[]
  machines: string[]
  availableMetrics: MetricInfo[]
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
