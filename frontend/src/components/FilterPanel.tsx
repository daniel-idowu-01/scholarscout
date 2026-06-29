'use client'

import { useRouter, useSearchParams, usePathname } from 'next/navigation'
import { useCallback } from 'react'
import type { SearchFacets } from '@/types'

const DEGREE_OPTIONS = [
  { value: 'phd', label: 'PhD' },
  { value: 'masters', label: 'Masters' },
  { value: 'bachelor', label: 'Bachelor' },
  { value: 'postdoc', label: 'Postdoc' },
]

const FUNDING_OPTIONS = [
  { value: 'fully_funded', label: 'Fully Funded' },
  { value: 'partial', label: 'Partial' },
  { value: 'tuition_only', label: 'Tuition Only' },
  { value: 'stipend_only', label: 'Stipend Only' },
]

const SORT_OPTIONS = [
  { value: 'relevance', label: 'Relevance' },
  { value: 'deadline', label: 'Deadline (soonest)' },
  { value: 'stipend', label: 'Stipend (highest)' },
  { value: 'freshness', label: 'Newest first' },
]

export default function FilterPanel({ facets }: { facets?: SearchFacets }) {
  const router = useRouter()
  const pathname = usePathname()
  const searchParams = useSearchParams()

  const update = useCallback(
    (key: string, value: string | null) => {
      const params = new URLSearchParams(searchParams.toString())
      if (!value) {
        params.delete(key)
      } else {
        params.set(key, value)
      }
      params.delete('page')
      router.push(`${pathname}?${params.toString()}`)
    },
    [router, pathname, searchParams],
  )

  const get = (key: string) => searchParams.get(key) ?? ''

  const hasFilters = ['degree_level', 'funding_type', 'country', 'min_stipend'].some(k => get(k))

  return (
    <aside className="space-y-6">
      <div>
        <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-2">Sort by</p>
        <select
          value={get('sort_by') || 'relevance'}
          onChange={e => update('sort_by', e.target.value)}
          className="w-full text-sm border border-slate-200 rounded-lg px-3 py-2 text-slate-700 bg-white focus:outline-none focus:ring-2 focus:ring-indigo-300"
        >
          {SORT_OPTIONS.map(o => (
            <option key={o.value} value={o.value}>{o.label}</option>
          ))}
        </select>
      </div>

      <div>
        <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-2">Degree Level</p>
        <div className="space-y-2">
          {DEGREE_OPTIONS.map(o => {
            const count = facets?.degree_levels.find(f => f.key === o.value)?.count
            return (
              <label key={o.value} className="flex items-center gap-2 cursor-pointer group">
                <input
                  type="radio"
                  name="degree_level"
                  value={o.value}
                  checked={get('degree_level') === o.value}
                  onChange={() => update('degree_level', o.value)}
                  className="accent-indigo-600"
                />
                <span className="text-sm text-slate-700 flex-1">{o.label}</span>
                {count !== undefined && (
                  <span className="text-xs text-slate-400">{count}</span>
                )}
              </label>
            )
          })}
          {get('degree_level') && (
            <button onClick={() => update('degree_level', null)} className="text-xs text-indigo-500 hover:underline">
              Clear
            </button>
          )}
        </div>
      </div>

      <div>
        <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-2">Funding Type</p>
        <div className="space-y-2">
          {FUNDING_OPTIONS.map(o => {
            const count = facets?.funding_types.find(f => f.key === o.value)?.count
            return (
              <label key={o.value} className="flex items-center gap-2 cursor-pointer">
                <input
                  type="radio"
                  name="funding_type"
                  value={o.value}
                  checked={get('funding_type') === o.value}
                  onChange={() => update('funding_type', o.value)}
                  className="accent-indigo-600"
                />
                <span className="text-sm text-slate-700 flex-1">{o.label}</span>
                {count !== undefined && (
                  <span className="text-xs text-slate-400">{count}</span>
                )}
              </label>
            )
          })}
          {get('funding_type') && (
            <button onClick={() => update('funding_type', null)} className="text-xs text-indigo-500 hover:underline">
              Clear
            </button>
          )}
        </div>
      </div>

      <div>
        <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-2">Country</p>
        <input
          type="text"
          placeholder="e.g. Germany"
          value={get('country')}
          onChange={e => update('country', e.target.value || null)}
          className="w-full text-sm border border-slate-200 rounded-lg px-3 py-2 placeholder-slate-400 text-slate-700 focus:outline-none focus:ring-2 focus:ring-indigo-300"
        />
      </div>

      <div>
        <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-2">
          Min. Stipend (USD/yr)
        </p>
        <input
          type="number"
          placeholder="e.g. 20000"
          min={0}
          step={5000}
          value={get('min_stipend')}
          onChange={e => update('min_stipend', e.target.value || null)}
          className="w-full text-sm border border-slate-200 rounded-lg px-3 py-2 placeholder-slate-400 text-slate-700 focus:outline-none focus:ring-2 focus:ring-indigo-300"
        />
      </div>

      {hasFilters && (
        <button
          onClick={() => {
            const params = new URLSearchParams(searchParams.toString())
            ;['degree_level', 'funding_type', 'country', 'min_stipend', 'page'].forEach(k =>
              params.delete(k),
            )
            router.push(`${pathname}?${params.toString()}`)
          }}
          className="w-full text-sm py-2 border border-slate-200 rounded-lg text-slate-500 hover:bg-slate-50 transition-colors"
        >
          Clear all filters
        </button>
      )}
    </aside>
  )
}