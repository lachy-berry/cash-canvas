import { useState } from 'react'
import { Link } from 'react-router'

/**
 * Step 4 — Import complete with undo option.
 *
 * @param {{
 *   imported: number,
 *   skipped: number,
 *   batchId: number,
 * }} props
 */
export function StepDone({ imported, skipped, batchId }) {
  const [undone, setUndone] = useState(false)
  const [undoing, setUndoing] = useState(false)
  const [undoError, setUndoError] = useState(null)

  async function handleUndo() {
    setUndoing(true)
    setUndoError(null)
    try {
      const res = await fetch(`/api/import/batches/${batchId}`, { method: 'DELETE' })
      if (!res.ok) {
        const d = await res.json()
        throw new Error(d.detail ?? 'Undo failed.')
      }
      setUndone(true)
    } catch (err) {
      setUndoError(err.message)
    } finally {
      setUndoing(false)
    }
  }

  if (undone) {
    return (
      <div className="flex flex-col gap-4">
        <p className="text-sm text-gray-700">Import undone. All {imported} transactions have been removed.</p>
        <Link to="/" className="text-sm text-indigo-600 hover:underline">← Back to transactions</Link>
      </div>
    )
  }

  return (
    <div className="flex flex-col gap-4">
      <div>
        <h2 className="text-lg font-semibold text-gray-900 mb-1">Import complete</h2>
        <p className="text-sm text-gray-700">
          Imported {imported} transaction{imported !== 1 ? 's' : ''}.
          {skipped > 0 && ` ${skipped} duplicate${skipped !== 1 ? 's' : ''} skipped.`}
        </p>
      </div>

      <div className="flex items-center gap-4">
        <Link
          to="/"
          className="px-4 py-2 bg-indigo-600 text-white rounded-lg font-medium hover:bg-indigo-700 text-sm"
        >
          View transactions →
        </Link>

        <button
          onClick={handleUndo}
          disabled={undoing}
          className="text-sm text-gray-500 hover:text-red-600 disabled:opacity-50"
        >
          {undoing ? 'Undoing…' : 'Undo this import'}
        </button>
      </div>

      {undoError && <p className="text-sm text-red-600">{undoError}</p>}
    </div>
  )
}
