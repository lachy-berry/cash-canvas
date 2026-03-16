import { useState, useEffect } from 'react'

const PREVIEW_LIMIT = 20

/**
 * Step 3 — Review new rows and resolve duplicates.
 *
 * @param {{
 *   file: File,
 *   mapping: object,
 *   onConfirm: (rows: object[]) => void,
 *   onBack: () => void,
 * }} props
 */
export function StepReview({ file, mapping, onConfirm, onBack }) {
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [newRows, setNewRows] = useState([])
  const [duplicates, setDuplicates] = useState([])
  // Track which duplicates the user wants to include anyway
  const [includedDups, setIncludedDups] = useState(new Set())

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    setError(null)

    const formData = new FormData()
    formData.append('file', file)
    Object.entries(mapping).forEach(([k, v]) => {
      if (v != null) formData.append(k, v)
    })

    fetch('/api/import/preview', { method: 'POST', body: formData })
      .then(res => {
        if (!res.ok) return res.json().then(d => Promise.reject(d.detail ?? 'Preview failed.'))
        return res.json()
      })
      .then(data => {
        if (!cancelled) {
          setNewRows(data.new ?? [])
          setDuplicates(data.duplicates ?? [])
        }
      })
      .catch(err => { if (!cancelled) setError(String(err)) })
      .finally(() => { if (!cancelled) setLoading(false) })

    return () => { cancelled = true }
  }, [file, mapping])

  function toggleDup(fingerprint) {
    setIncludedDups(prev => {
      const next = new Set(prev)
      if (next.has(fingerprint)) next.delete(fingerprint)
      else next.add(fingerprint)
      return next
    })
  }

  function handleImport() {
    const chosenDups = duplicates.filter(r => includedDups.has(r.fingerprint))
    onConfirm([...newRows, ...chosenDups])
  }

  const totalToImport = newRows.length + includedDups.size

  if (loading) return <p className="text-sm text-gray-500">Analysing file…</p>
  if (error) return (
    <div className="flex flex-col gap-3">
      <p className="text-sm text-red-600">Error: {error}</p>
      <button onClick={onBack} className="text-sm text-indigo-600 hover:underline w-fit">← Back</button>
    </div>
  )

  return (
    <div className="flex flex-col gap-6">
      <div>
        <h2 className="text-lg font-semibold text-gray-900 mb-1">Review import</h2>
        <p className="text-sm text-gray-500">
          <strong>{newRows.length} new</strong> transaction{newRows.length !== 1 ? 's' : ''} ready to import
          {duplicates.length > 0 && `, ${duplicates.length} possible duplicate${duplicates.length !== 1 ? 's' : ''} detected`}.
        </p>
      </div>

      {/* New rows preview */}
      {newRows.length > 0 && (
        <div>
          <h3 className="text-sm font-medium text-gray-700 mb-2">
            New transactions
            {newRows.length > PREVIEW_LIMIT && (
              <span className="ml-1 font-normal text-gray-400">(showing {PREVIEW_LIMIT} of {newRows.length})</span>
            )}
          </h3>
          <div className="overflow-x-auto rounded-lg border border-gray-200">
            <table className="min-w-full text-sm">
              <thead className="bg-gray-50 text-gray-500 uppercase text-xs">
                <tr>
                  <th className="px-3 py-2 text-left">Date</th>
                  <th className="px-3 py-2 text-left">Description</th>
                  <th className="px-3 py-2 text-right">Amount</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {newRows.slice(0, PREVIEW_LIMIT).map((row, i) => (
                  <tr key={i} className="hover:bg-gray-50">
                    <td className="px-3 py-2 whitespace-nowrap text-gray-500">{row.date}</td>
                    <td className="px-3 py-2 text-gray-900 max-w-xs truncate">{row.description}</td>
                    <td className={`px-3 py-2 text-right tabular-nums font-medium ${row.amount < 0 ? 'text-red-600' : 'text-green-600'}`}>
                      {row.amount < 0 ? '-' : '+'}${Math.abs(row.amount).toFixed(2)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {newRows.length > PREVIEW_LIMIT && (
            <p className="text-xs text-gray-400 mt-1">…and {newRows.length - PREVIEW_LIMIT} more</p>
          )}
        </div>
      )}

      {/* Duplicates list */}
      {duplicates.length > 0 && (
        <div>
          <h3 className="text-sm font-medium text-gray-700 mb-2">
            {duplicates.length} possible duplicate{duplicates.length !== 1 ? 's' : ''}
          </h3>
          <div className="overflow-y-auto max-h-64 rounded-lg border border-amber-200 bg-amber-50">
            {duplicates.map((row) => (
              <div key={row.fingerprint} className="flex items-center justify-between gap-3 px-3 py-2 border-b border-amber-100 last:border-0">
                <div className="flex-1 min-w-0">
                  <span className="text-xs text-gray-500 mr-2">{row.date}</span>
                  <span className="text-sm text-gray-800 truncate">{row.description}</span>
                </div>
                <span className={`text-sm tabular-nums font-medium shrink-0 ${row.amount < 0 ? 'text-red-600' : 'text-green-600'}`}>
                  {row.amount < 0 ? '-' : '+'}${Math.abs(row.amount).toFixed(2)}
                </span>
                <button
                  onClick={() => toggleDup(row.fingerprint)}
                  className={`shrink-0 text-xs px-2 py-1 rounded border transition-colors ${
                    includedDups.has(row.fingerprint)
                      ? 'bg-indigo-600 text-white border-indigo-600'
                      : 'text-indigo-600 border-indigo-300 hover:bg-indigo-50'
                  }`}
                >
                  {includedDups.has(row.fingerprint) ? '✓ Included' : '+ Include anyway'}
                </button>
              </div>
            ))}
          </div>
        </div>
      )}

      <div className="flex items-center gap-3">
        <button
          onClick={handleImport}
          disabled={totalToImport === 0}
          className="px-4 py-2 bg-indigo-600 text-white rounded-lg font-medium hover:bg-indigo-700 disabled:opacity-40 disabled:cursor-not-allowed"
        >
          Import {totalToImport} transaction{totalToImport !== 1 ? 's' : ''}
        </button>
        <button onClick={onBack} className="text-sm text-gray-500 hover:text-gray-700">
          ← Back
        </button>
      </div>
    </div>
  )
}
