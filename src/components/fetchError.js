function readDetailFromJsonBody(body) {
  if (typeof body === 'string' && body.trim()) return body.trim()
  if (!body || typeof body !== 'object') return null

  if (typeof body.detail === 'string' && body.detail.trim()) return body.detail.trim()
  if (typeof body.message === 'string' && body.message.trim()) return body.message.trim()
  if (typeof body.error === 'string' && body.error.trim()) return body.error.trim()

  return null
}

export async function getFetchErrorMessage(res) {
  const fallback = `Server error ${res.status}`
  const contentType = res.headers.get('content-type') ?? ''

  if (contentType.includes('application/json')) {
    try {
      const body = await res.json()
      const detail = readDetailFromJsonBody(body)
      if (detail) return `${detail} (HTTP ${res.status})`
      return fallback
    } catch {
      return fallback
    }
  }

  try {
    const text = await res.text()
    if (text.trim()) return `${text.trim()} (HTTP ${res.status})`
    return fallback
  } catch {
    return fallback
  }
}
