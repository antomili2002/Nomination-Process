import type { AppStep } from '../App'

interface Step {
  id: AppStep
  title: string
  desc: string
}

const STEPS: Step[] = [
  { id: 'upload',    title: 'Upload',    desc: 'Excel workbook' },
  { id: 'configure', title: 'Configure', desc: 'Chains & machines' },
  { id: 'result',    title: 'Download',  desc: 'Excel report' },
]

const ORDER: AppStep[] = ['upload', 'configure', 'result']

interface Props {
  currentStep: AppStep
}

export function StepIndicator({ currentStep }: Props) {
  const currentIdx = ORDER.indexOf(currentStep)

  return (
    <nav className="step-bar" aria-label="Workflow steps">
      <div className="step-bar__inner">
        {STEPS.map((step, idx) => {
          const isDone   = idx < currentIdx
          const isActive = idx === currentIdx

          return (
            <div key={step.id} style={{ display: 'flex', alignItems: 'center', flex: 1 }}>
              <div
                className={[
                  'step-item',
                  isActive ? 'step-item--active' : '',
                  isDone   ? 'step-item--done'   : '',
                ].join(' ')}
              >
                <div className="step-item__circle" aria-hidden="true">
                  {isDone ? (
                    // Checkmark
                    <svg width="12" height="12" viewBox="0 0 12 12" fill="none">
                      <path
                        d="M2 6l3 3 5-5"
                        stroke="currentColor"
                        strokeWidth="1.8"
                        strokeLinecap="round"
                        strokeLinejoin="round"
                      />
                    </svg>
                  ) : (
                    idx + 1
                  )}
                </div>
                <div className="step-item__label">
                  <span className="step-item__title">{step.title}</span>
                  <span className="step-item__desc">{step.desc}</span>
                </div>
              </div>

              {/* Connector line between steps */}
              {idx < STEPS.length - 1 && (
                <div
                  className={[
                    'step-item__connector',
                    isDone ? 'step-item__connector--done' : '',
                  ].join(' ')}
                  aria-hidden="true"
                />
              )}
            </div>
          )
        })}
      </div>
    </nav>
  )
}
