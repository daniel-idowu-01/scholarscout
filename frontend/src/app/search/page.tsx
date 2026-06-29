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
      <form action="/search" method="get" className="flex gap-2 mb-4">
        <input
          name="q"
          type="text"
          defaultValue={q}
          key={q}
          placeholder="Search opportunities..."
          className="flex-1 px-4 py-2.5 border border-slate-200 rounded-xl text-sm text-slate-900 bg-white focus:outline-none focus:ring-2 focus:ring-indigo-300"
        />
        <button
          type="submit"
          className="px-5 py-2.5 bg-indigo-600 text-white text-sm font-semibold rounded-xl hover:bg-indigo-700 transition-colors"
        >
          Search
        </button>
      </form>

      {data && (
        <p className="text-sm text-slate-500 mb-6">
          <span className="font-medium text-slate-800">{data.total.toLocaleString()}</span> opportunities found
          {q && (
            <>
              {' '}for <span className="font-medium text-slate-800">&ldquo;{q}&rdquo;</span>
            </>
          )}
          {data.took_ms > 0 && (
            <span className="text-slate-400"> &middot; {data.took_ms.toFixed(0)}ms</span>
          )}
        </p>
      )}

      <div className="flex gap-8">
        {/* Sidebar */}
        <div className="hidden lg:block w-52 shrink-0">
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
              <p className="text-slate-500 font-medium">Could not load results</p>
              <p className="text-sm text-slate-400 mt-1">{error}</p>
              <p className="text-sm text-slate-400 mt-1">Is the API running at localhost:8000?</p>
            </div>
          )}

          {!loading && !error && data && (
            <>
              {data.hits.length === 0 ? (
                <div className="py-20 text-center">
                  <p className="text-slate-500 font-medium">No opportunities found</p>
                  <p className="text-sm text-slate-400 mt-1">
                    Try adjusting your search query or filters
                  </p>
                </div>
              ) : (
                <div className="space-y-3">
                  {data.hits.map(hit => (
                    <OpportunityCard key={hit.id} hit={hit} />
                  ))}
                </div>
              )}

              {data.total_pages > 1 && (
                <div className="mt-8 flex items-center justify-center gap-2">
                  <button
                    disabled={data.page <= 1}
                    onClick={() => goToPage(data.page - 1)}
                    className="px-4 py-2 text-sm border border-slate-200 rounded-lg text-slate-600 bg-white hover:bg-slate-50 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
                  >
                    Previous
                  </button>
                  <span className="text-sm text-slate-500 px-2">
                    Page {data.page} of {data.total_pages}
                  </span>
                  <button
                    disabled={data.page >= data.total_pages}
                    onClick={() => goToPage(data.page + 1)}
                    className="px-4 py-2 text-sm border border-slate-200 rounded-lg text-slate-600 bg-white hover:bg-slate-50 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
                  >
                    Next
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
    <Suspense
      fallback={
        <div className="flex justify-center py-20">
          <Spinner />
        </div>
      }
    >
      <SearchContent />
    </Suspense>
  )
}