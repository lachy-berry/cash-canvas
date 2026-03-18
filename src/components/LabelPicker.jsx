import { useEffect, useState } from 'react'

/**
 * LabelPicker — category dropdown for a single transaction row.
 *
 * @param {{ txId: number, layerId: string, currentValue: string|null, categories: Array<{id:string,name:string}> }} props
 */
export function LabelPicker({ txId, layerId, currentValue, categories }) {
  const [value, setValue] = useState(currentValue ?? '')
  const [error, setError] = useState(null)
  const [saving, setSaving] = useState(false)

  // Sync local state when the prop changes (e.g. parent reloads transaction data).
  useEffect(() => {
    setValue(currentValue ?? '')
  }, [currentValue])

  async function handleChange(e) {
    const next = e.target.value
    const prev = value
    setValue(next)
    setError(null)
    setSaving(true)

    try {
      const res = await fetch(`/api/transactions/${txId}/labels`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          layer: layerId,
          category: next === '' ? null : next,
        }),
      })
      if (!res.ok) throw new Error(`Server error ${res.status}`)
    } catch (err) {
      // Revert picker and show inline error
      setValue(prev)
      setError('Could not save label — please try again.')
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="flex flex-col gap-1">
      <select
        data-testid="label-picker"
        value={value}
        onChange={handleChange}
        disabled={saving}
        className="text-xs border border-gray-200 rounded px-2 py-1 bg-white text-gray-700 disabled:opacity-50 focus:outline-none focus:ring-1 focus:ring-indigo-400"
      >
        <option value="">— unlabelled —</option>
        {categories.map(cat => (
          <option key={cat.id} value={cat.id}>{cat.name}</option>
        ))}
      </select>
      {error && (
        <p className="text-xs text-red-600">{error}</p>
      )}
    </div>
  )
}
