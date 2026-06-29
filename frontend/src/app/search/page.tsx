'use client'

import { useEffect, useState, Suspense } from 'react'
import { useSearchParams, useRouter, usePathname } from 'next/navigation'
import OpportunityCard from '@/components/OpportunityCard'
import FilterPanel from '@/components/FilterPanel'
import Spinner from '@/components/Spinner'
import { searchApi } from '@/lib/api'
import type { SearchResponse } from '@/types'

function SearchContent() {
  const searchParams = useSearchParams()
  const router = useRouter()
  const pathname = usePathname()
  const [data, setData] = useState<SearchResponse | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const q = searchParams.get('q') ?? ''

  useEffect(() => {
    setLoading(true)
    setError(null)
    const params: Record<string, string> = { page: '1', page_size: '20' }
    for (const [k, v] of searchParams.entries()) {
      if (v) params[k] = v
    }
    searchApi
      .opportunities(params)
      .then(setData)
      .catch(e => setError((e as Error).message))
      .finally(() => setLoading(false))
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [searchParams.toString()])

  function goToPage(p: number) {
    const params = new URLSearchParams(searchParams.toString())
    params.set('page', String(p))
    router.push(`${pathname}?${params.toString()}`)
  }

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      {/* Search bar */}
      <form
        action="/search"
        method="get"
        className="flex mb-6"
        style={{ border: '1px solid var(--border-bright)' }}
      >
        <input
          name="q"
          type="text"
          defaultValue={q}
          key={q}
          placeholder="Search opportunities..."
          className="flex-1 px-5 py-3 bg-surface text-cream text-sm focus:outline-none placeholder:text-fog"
        />
        <button
          type="submit"
          className="px-6 py-3 bg-gold text-bg text-sm font-bold tracking-wide hover:bg-gold-bright transition-colors shrink-0"
        >
          Search
        </button>
      </form>

      {/* Result count */}
      {data && (
        <p className="font-mono text-xs text-fog mb-6">
          <span className="text-gold">{data.total.toLocaleString()}</span> opportunities
          {q && <> · query: <span className="text-mist">&ldquo;{q}&rdquo;</span></>}
          {data.took_ms > 0 && <> · {data.took_ms.toFixed(0)}ms</>}
        </p>
      )}

      <div className="flex gap-10">
        {/* Sidebar */}
        <div className="hidden lg:block w-48 shrink-0">
          <FilterPanel facets={data?.facets} />
        </div>

        {/* Results */}
        <div className="flex-1 min-w-0">
          {loading && (
            <div className="flex justify-center py-20">
              <Spinner />
            </div>
          )}

          {!loading && error && (
            <div className="py-20 text-center">
              <p className="font-mono text-sm text-mist">Failed to load results</p>
              <p className="font-mono text-xs text-fog mt-2">{error}</p>
              <p className="font-mono text-xs text-fog mt-1">Is the API running at localhost:8000?</p>
            </div>
          )}

          {!loading && !error && data && (
            <>
              {data.hits.length === 0 ? (
                <div className="py-20 text-center">
                  <p className="font-mono text-sm text-mist">No opportunities found</p>
                  <p className="font-mono text-xs text-fog mt-2">Try adjusting your search or filters</p>
                </div>
              ) : (
                <div className="space-y-2">
                  {data.hits.map((hit, i) => (
                    <OpportunityCard key={hit.id} hit={hit} index={i} />
                  ))}
                </div>
              )}

              {data.total_pages > 1 && (
                <div className="mt-10 flex items-center justify-center gap-3">
                  <button
                    disabled={data.page <= 1}
                    onClick={() => goToPage(data.page - 1)}
                    className="font-mono text-xs px-4 py-2 text-mist hover:text-cream disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
                    style={{ border: '1px solid var(--border)' }}
                  >
                    ← Prev
                  </button>
                  <span className="font-mono text-xs text-fog">
                    {data.page} / {data.total_pages}
                  </span>
                  <button
                    disabled={data.page >= data.total_pages}
                    onClick={() => goToPage(data.page + 1)}
                    className="font-mono text-xs px-4 py-2 text-mist hover:text-cream disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
                    style={{ border: '1px solid var(--border)' }}
                  >
                    Next →
                  </button>
                </div>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  )
}

export default function SearchPage() {
  return (
    <Suspense fallback={<div className="flex justify-center py-20"><Spinner /></div>}>
      <SearchContent />
    </Suspense>
  )
}