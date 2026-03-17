import { useEffect, useState } from 'react'
import { Link } from 'react-router'

const PAGE_SIZE = 50

/**
 * TransactionList — paginated read-only table of imported transactions.
 *
 * @param {{ refreshKey: number }} props
 *   Increment refreshKey from the parent to trigger a reload.
 */
export function TransactionList({ refreshKey = 0 }) {
  const [transactions, setTransactions] = useState([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(0)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  const offset = page * PAGE_SIZE

  useEffect(() => {
    let cancelled = false

    async function loadTransactions() {
      try {
        const res = await fetch(`/api/transactions?limit=${PAGE_SIZE}&offset=${offset}`)
        if (!res.ok) throw new Error(`Server error ${res.status}`)
        const data = await res.json()
        if (!cancelled) {
          setTransactions(data.transactions)
          setTotal(data.total)
        }
      } catch (err) {
        if (!cancelled) setError(err.message)
      } finally {
        if (!cancelled) setLoading(false)
      }
    }

    loadTransactions()

    return () => { cancelled = true }
  }, [page, offset, refreshKey])

  const totalPages = Math.ceil(total / PAGE_SIZE)

  if (loading) return <p className="text-sm text-gray-400">Loading…</p>
  if (error) return <p className="text-sm text-red-600">Failed to load: {error}</p>

  if (!transactions.length) {
    return (
      <div className="text-center py-16 text-gray-400">
        <p className="text-sm mb-3">No transactions yet.</p>
        <Link to="/import" className="text-sm text-indigo-600 hover:underline">Import a CSV to get started →</Link>
      </div>
    )
  }

  return (
    <div className="flex flex-col gap-4">
      <p className="text-sm text-gray-500">{total} transaction{total !== 1 ? 's' : ''}</p>

      <div className="overflow-x-auto rounded-lg border border-gray-200">
        <table className="min-w-full text-sm">
          <thead className="bg-gray-50 text-gray-500 uppercase text-xs">
            <tr>
              <th className="px-4 py-3 text-left">Date</th>
              <th className="px-4 py-3 text-left">Description</th>
              <th className="px-4 py-3 text-right">Amount</th>
              <th className="px-4 py-3 text-right">Balance</th>
              <th className="px-4 py-3 text-left">Label</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {transactions.map(tx => (
              <tr key={tx.id} className="hover:bg-gray-50">
                <td className="px-4 py-3 whitespace-nowrap text-gray-500">{tx.date}</td>
                <td className="px-4 py-3 text-gray-900 max-w-xs truncate">{tx.description}</td>
                <td className={`px-4 py-3 text-right tabular-nums font-medium ${tx.amount < 0 ? 'text-red-600' : 'text-green-600'}`}>
                  {tx.amount < 0 ? '-' : '+'}${Math.abs(tx.amount).toFixed(2)}
                </td>
                <td className="px-4 py-3 text-right tabular-nums text-gray-400">
                  {tx.balance != null ? `$${tx.balance.toFixed(2)}` : '—'}
                </td>
                <td className="px-4 py-3 text-gray-400 text-xs">{tx.label_broad ?? '—'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {totalPages > 1 && (
        <div className="flex items-center gap-3 text-sm">
          <button
            onClick={() => setPage(p => Math.max(0, p - 1))}
            disabled={page === 0}
            className="px-3 py-1 rounded border border-gray-300 disabled:opacity-40"
          >
            Prev
          </button>
          <span className="text-gray-400">Page {page + 1} of {totalPages}</span>
          <button
            onClick={() => setPage(p => Math.min(totalPages - 1, p + 1))}
            disabled={page >= totalPages - 1}
            className="px-3 py-1 rounded border border-gray-300 disabled:opacity-40"
          >
            Next
          </button>
        </div>
      )}
    </div>
  )
}
