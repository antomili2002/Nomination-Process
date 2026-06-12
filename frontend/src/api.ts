const API_PREFIX = '/api'

function normalizeBaseUrl(baseUrl: string): string {
  return baseUrl.replace(/\/+$/, '')
}

export function buildApiUrl(path: string, apiBaseUrl = import.meta.env.VITE_API_BASE_URL ?? ''): string {
  const normalizedPath = path.startsWith('/') ? path : `/${path}`

  if (!apiBaseUrl) {
    return `${API_PREFIX}${normalizedPath}`
  }

  const normalizedBaseUrl = normalizeBaseUrl(apiBaseUrl)
  return `${normalizedBaseUrl}${normalizedPath}`
}
