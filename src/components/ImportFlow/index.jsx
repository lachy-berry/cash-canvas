import { useState } from 'react'
import { StepUpload } from './StepUpload'
import { StepMapColumns } from './StepMapColumns'
import { StepReview } from './StepReview'
import { StepDone } from './StepDone'

const STEPS = ['upload', 'map', 'review', 'done']

/**
 * ImportFlow — orchestrates the 4-step CSV import process.
 */
export function ImportFlow() {
  const [step, setStep] = useState('upload')
  const [file, setFile] = useState(null)
  const [headers, setHeaders] = useState([])
  const [mapping, setMapping] = useState(null)
  const [result, setResult] = useState(null) // { imported, skipped, batchId }

  function handleFile(f, hdrs) {
    setFile(f)
    setHeaders(hdrs)
    setStep('map')
  }

  function handleMapping(m) {
    setMapping(m)
    setStep('review')
  }

  async function handleConfirm(rows, skippedDups = 0) {
    const res = await fetch('/api/import/confirm', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ rows }),
    })
    const data = await res.json()
    if (!res.ok) throw new Error(data.detail ?? 'Confirm failed.')
    // skippedDups is computed client-side: total duplicates minus those explicitly included
    setResult({ imported: data.imported, skipped: skippedDups, batchId: data.batch_id })
    setStep('done')
  }

  return (
    <div className="max-w-2xl mx-auto">
      {/* Step indicator */}
      <div className="flex items-center gap-2 mb-8 text-xs text-gray-400">
        {['Upload', 'Map columns', 'Review', 'Done'].map((label, i) => {
          const current = STEPS.indexOf(step)
          const isActive = i === current
          const isDone = i < current
          return (
            <span key={label} className="flex items-center gap-2">
              <span className={`font-medium ${isActive ? 'text-indigo-600' : isDone ? 'text-gray-400' : 'text-gray-300'}`}>
                {label}
              </span>
              {i < 3 && <span className="text-gray-200">›</span>}
            </span>
          )
        })}
      </div>

      {step === 'upload' && <StepUpload onFile={handleFile} />}
      {step === 'map' && (
        <StepMapColumns
          headers={headers}
          onNext={handleMapping}
        />
      )}
      {step === 'review' && (
        <StepReview
          file={file}
          mapping={mapping}
          onConfirm={handleConfirm}
          onBack={() => setStep('map')}
        />
      )}
      {step === 'done' && result && (
        <StepDone
          imported={result.imported}
          skipped={result.skipped}
          batchId={result.batchId}
        />
      )}
    </div>
  )
}
