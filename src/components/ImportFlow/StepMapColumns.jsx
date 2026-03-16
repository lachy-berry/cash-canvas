import { useState } from 'react'
import { guessColumns } from './guessColumns'

/**
 * Step 2 — Column mapping.
 *
 * @param {{
 *   headers: string[],
 *   onNext: (mapping: object) => void,
 * }} props
 */
export function StepMapColumns({ headers, onNext }) {
  const guessed = guessColumns(headers)

  const [dateCol, setDateCol] = useState(guessed.date ?? '')
  const [descCol, setDescCol] = useState(guessed.description ?? '')
  const [balanceCol, setBalanceCol] = useState(guessed.balance ?? '')

  // Amount mode: 'single' or 'double'
  const [amountMode, setAmountMode] = useState('single')
  const [amountCol, setAmountCol] = useState(guessed.amount ?? '')
  const [creditCol, setCreditCol] = useState('')
  const [debitCol, setDebitCol] = useState('')

  const [error, setError] = useState(null)

  function validate() {
    if (!dateCol) return 'Please select the Date column.'
    if (!descCol) return 'Please select the Description column.'
    if (amountMode === 'single' && !amountCol) return 'Please select the Amount column.'
    if (amountMode === 'double' && (!creditCol || !debitCol)) return 'Please select both Credit and Debit columns.'
    return null
  }

  function handleNext() {
    const err = validate()
    if (err) { setError(err); return }
    setError(null)
    const mapping = {
      date_col: dateCol,
      desc_col: descCol,
      balance_col: balanceCol || undefined,
      ...(amountMode === 'single'
        ? { amount_col: amountCol }
        : { credit_col: creditCol, debit_col: debitCol }),
    }
    onNext(mapping)
  }

  return (
    <div className="flex flex-col gap-6">
      <div>
        <h2 className="text-lg font-semibold text-gray-900 mb-1">Map columns</h2>
        <p className="text-sm text-gray-500">
          Tell us which CSV column maps to each field. We've pre-filled our best guess.
        </p>
      </div>

      <div className="grid gap-4">
        <Field label="Date" required>
          <ColSelect value={dateCol} onChange={setDateCol} headers={headers} />
        </Field>

        <Field label="Description" required>
          <ColSelect value={descCol} onChange={setDescCol} headers={headers} />
        </Field>

        <Field label="Amount" required>
          <div className="flex flex-col gap-2">
            <div className="flex gap-4 text-sm">
              <label className="flex items-center gap-1.5 cursor-pointer">
                <input
                  type="radio"
                  name="amountMode"
                  value="single"
                  checked={amountMode === 'single'}
                  onChange={() => setAmountMode('single')}
                />
                Single column
              </label>
              <label className="flex items-center gap-1.5 cursor-pointer">
                <input
                  type="radio"
                  name="amountMode"
                  value="double"
                  checked={amountMode === 'double'}
                  onChange={() => setAmountMode('double')}
                />
                Credit &amp; Debit columns
              </label>
            </div>

            {amountMode === 'single' ? (
              <ColSelect value={amountCol} onChange={setAmountCol} headers={headers} />
            ) : (
              <div className="flex items-center gap-2">
                <ColSelect value={creditCol} onChange={setCreditCol} headers={headers} placeholder="Credit column" />
                <span className="text-gray-400">−</span>
                <ColSelect value={debitCol} onChange={setDebitCol} headers={headers} placeholder="Debit column" />
              </div>
            )}
          </div>
        </Field>

        <Field label="Balance" hint="optional">
          <ColSelect value={balanceCol} onChange={setBalanceCol} headers={headers} allowEmpty />
        </Field>
      </div>

      {error && <p className="text-sm text-red-600">{error}</p>}

      <button
        onClick={handleNext}
        className="px-4 py-2 bg-indigo-600 text-white rounded-lg font-medium hover:bg-indigo-700 w-fit"
      >
        Review import →
      </button>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

function Field({ label, required, hint, children }) {
  return (
    <div className="flex flex-col gap-1">
      <label className="text-sm font-medium text-gray-700">
        {label}
        {required && <span className="text-red-500 ml-0.5">*</span>}
        {hint && <span className="ml-1 text-gray-400 font-normal">({hint})</span>}
      </label>
      {children}
    </div>
  )
}

function ColSelect({ value, onChange, headers, placeholder = 'Select column…', allowEmpty = false }) {
  return (
    <select
      value={value}
      onChange={e => onChange(e.target.value)}
      className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm bg-white focus:outline-none focus:ring-2 focus:ring-indigo-500"
    >
      <option value="">{placeholder}</option>
      {headers.map(h => (
        <option key={h} value={h}>{h}</option>
      ))}
    </select>
  )
}
