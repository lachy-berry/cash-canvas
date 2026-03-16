/**
 * guessColumns — pure function that maps CSV header names to field slots.
 *
 * Given an array of header strings from a CSV file, returns a best-guess
 * mapping of field name → matched CSV header (or null if no match found).
 *
 * Matching is case-insensitive. The first candidate that appears in the
 * headers array wins.
 *
 * @param {string[]} headers - Column names from the uploaded CSV
 * @returns {{ date: string|null, description: string|null, amount: string|null, balance: string|null }}
 */
export function guessColumns(headers) {
  const normalised = headers.map(h => h.trim().toLowerCase())

  const candidates = {
    date: [
      'date',
      'transaction date',
      'trans date',
      'tran_date',
      'txn date',
      'txn_date',
    ],
    description: [
      'description',
      'narrative',
      'details',
      'memo',
      'particulars',
      'transaction details',
      'trans description',
    ],
    amount: [
      'amount',
      'debit/credit',
      'transaction amount',
      'value',
      'net amount',
    ],
    balance: [
      'balance',
      'running balance',
      'closing balance',
      'account balance',
    ],
  }

  const result = { date: null, description: null, amount: null, balance: null }

  for (const [field, options] of Object.entries(candidates)) {
    for (const candidate of options) {
      const idx = normalised.indexOf(candidate)
      if (idx !== -1) {
        result[field] = headers[idx] // use the original (un-lowercased) header
        break
      }
    }
  }

  return result
}
