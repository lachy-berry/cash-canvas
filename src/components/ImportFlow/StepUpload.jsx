import { useRef } from 'react'

/**
 * Step 1 — File picker.
 *
 * @param {{ onFile: (file: File, headers: string[]) => void }} props
 */
export function StepUpload({ onFile }) {
  const inputRef = useRef(null)

  function handleChange(e) {
    const file = e.target.files?.[0]
    if (!file) return

    const reader = new FileReader()
    reader.onload = (ev) => {
      const text = ev.target.result
      const firstLine = text.split('\n')[0] ?? ''
      // Strip UTF-8 BOM if present
      const clean = firstLine.replace(/^\uFEFF/, '')
      const headers = clean.split(',').map(h => h.trim()).filter(Boolean)
      onFile(file, headers)
    }
    reader.readAsText(file)

    // Reset so re-selecting the same file triggers onChange again
    if (inputRef.current) inputRef.current.value = ''
  }

  return (
    <div className="flex flex-col items-center gap-6 py-12">
      <div className="text-center">
        <h2 className="text-lg font-semibold text-gray-900 mb-1">Upload your bank CSV</h2>
        <p className="text-sm text-gray-500">Select a CSV file exported from your bank.</p>
      </div>

      <input
        ref={inputRef}
        type="file"
        accept=".csv,text/csv"
        className="hidden"
        onChange={handleChange}
      />

      <button
        onClick={() => inputRef.current?.click()}
        className="px-6 py-3 bg-indigo-600 text-white rounded-lg font-medium hover:bg-indigo-700 transition-colors"
      >
        Choose CSV file
      </button>
    </div>
  )
}
