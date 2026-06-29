import type { TokenResponse, SearchResponse, SearchParams, Opportunity, PageResult } from '@/types'

const API_BASE = '/api/v1'

function getHeaders(): Record<string, string> {
  const headers: Record<string, string> = { 'Content-Type': 'application/json' }
  if (typeof window !== 'undefined') {
    const token = localStorage.getItem('access_token')
    if (token) headers['Authorization'] = `Bearer ${token}`
  }
  return headers
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: { ...getHeaders(), ...init?.headers },
    credentials: 'include',
  })
  if (!res.ok) {
    const body = await res.json().catch(() => ({}))
    throw new Error((body as { detail?: string }).detail ?? `HTTP ${res.status}`)
  }
  return res.json() as Promise<T>
}

export const authApi = {
  register: (data: { email: string; password: string; name?: string }) =>
    request<TokenResponse>('/auth/register', {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  login: (data: { email: string; password: string }) =>
    request<TokenResponse>('/auth/login', {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  logout: (refresh_token: string) =>
    request<{ message: string }>('/auth/logout', {
      method: 'POST',
      body: JSON.stringify({ refresh_token }),
    }),
}

export const searchApi = {
  opportunities: (params: SearchParams) => {
    const cleaned = Object.fromEntries(
      Object.entries(params).filter(([, v]) => v !== undefined && v !== ''),
    ) as Record<string, string>
    const qs = new URLSearchParams(cleaned).toString()
    return request<SearchResponse>(`/search/opportunities${qs ? `?${qs}` : ''}`)
  },
}

export const opportunitiesApi = {
  get: (id: string) => request<Opportunity>(`/opportunities/${id}`),

  list: (params?: Record<string, string>) => {
    const qs = params ? new URLSearchParams(params).toString() : ''
    return request<PageResult<Opportunity>>(`/opportunities/${qs ? `?${qs}` : ''}`)
  },
}