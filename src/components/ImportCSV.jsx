import { useRef, useState } from 'react'

/**
 * ImportCSV — file picker that uploads a CSV to POST /api/import.
 *
 * @param {{ onImported: (count: number) => void }} props
 */
export function ImportCSV({ onImported }) {
  const inputRef = useRef(null)
  const [status, setStatus] = useState(null)  // null | { ok: true, count: number } | { ok: false, message: string }
  const [loading, setLoading] = useState(false)

  async function handleFile(file) {
    if (!file) return
    setLoading(true)
    setStatus(null)

    const formData = new FormData()
    formData.append('file', file)

    try {
      const res = await fetch('/api/import', { method: 'POST', body: formData })
      const data = await res.json()

      if (!res.ok) {
        setStatus({ ok: false, message: data.detail ?? 'Upload failed.' })
        return
      }

      setStatus({ ok: true, count: data.imported })
      onImported(data.imported)
    } catch {
      setStatus({ ok: false, message: 'Network error — could not reach server.' })
    } finally {
      setLoading(false)
      // Reset input so the same file can be re-uploaded if needed
      if (inputRef.current) inputRef.current.value = ''
    }
  }

  return (
    <div className="flex flex-col gap-3">
      <input
        ref={inputRef}
        type="file"
        accept=".csv,text/csv"
        className="hidden"
        onChange={(e) => handleFile(e.target.files?.[0])}
      />

      <button
        onClick={() => inputRef.current?.click()}
        disabled={loading}
        className="px-4 py-2 bg-indigo-600 text-white rounded-lg font-medium hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed w-fit"
      >
        {loading ? 'Importing…' : 'Import CSV'}
      </button>

      {status?.ok && (
        <p className="text-sm text-green-700">
          Imported {status.count} transactions
        </p>
      )}

      {status && !status.ok && (
        <p className="text-sm text-red-600">
          Error: {status.message}
        </p>
      )}
    </div>
  )
}
