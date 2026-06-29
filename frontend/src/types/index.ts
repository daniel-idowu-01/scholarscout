export interface TokenResponse {
  access_token: string
  token_type: string
  expires_in: number
}

export interface SearchHit {
  id: string
  score: number
  title: string
  university_name: string
  country: string
  degree_level: string
  funding_type: string
  stipend_amount: number | null
  deadline: string | null
  description: string
  departments: string[]
  tags: string[]
}

export interface Facet {
  key: string
  count: number
}

export interface SearchFacets {
  degree_levels: Facet[]
  funding_types: Facet[]
  countries: Facet[]
  departments: Facet[]
}

export interface SearchResponse {
  hits: SearchHit[]
  total: number
  page: number
  page_size: number
  total_pages: number
  facets: SearchFacets
  took_ms: number
  query_type: string
}

export interface Opportunity {
  id: string
  university_id: string
  source_page_id: string | null
  title: string
  degree_level: string
  funding_type: string
  status: string
  stipend_amount: number | null
  stipend_currency: string
  tuition_covered: boolean | null
  deadline: string | null
  source_url: string
  description: string
  requirements: string[]
  departments: string[]
  tags: string[]
  language_requirements: Record<string, string>
  citizenship_restrictions: string[] | null
  gpa_minimum: number | null
  duration_years: number | null
  last_verified_at: string
  created_at: string
  updated_at: string
}

export interface PageResult<T> {
  items: T[]
  total: number
  page: number
  page_size: number
  total_pages: number
  has_next: boolean
  has_prev: boolean
}

export interface SearchParams {
  q?: string
  page?: string
  page_size?: string
  degree_level?: string
  funding_type?: string
  country?: string
  department?: string
  min_stipend?: string
  sort_by?: string
  [key: string]: string | undefined
}