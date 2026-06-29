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
  { value: 'deadline', label: 'Deadline' },
  { value: 'stipend', label: 'Stipend' },
  { value: 'freshness', label: 'Newest' },
]

function SectionLabel({ children }: { children: React.ReactNode }) {
  return (
    <p className="font-mono text-xs text-fog tracking-widest uppercase mb-3">{children}</p>
  )
}

export default function FilterPanel({ facets }: { facets?: SearchFacets }) {
  const router = useRouter()
  const pathname = usePathname()
  const searchParams = useSearchParams()

  const update = useCallback(
    (key: string, value: string | null) => {
      const params = new URLSearchParams(searchParams.toString())
      if (!value) params.delete(key)
      else params.set(key, value)
      params.delete('page')
      router.push(`${pathname}?${params.toString()}`)
    },
    [router, pathname, searchParams],
  )

  const get = (key: string) => searchParams.get(key) ?? ''
  const hasFilters = ['degree_level', 'funding_type', 'country', 'min_stipend'].some(k => get(k))

  const radioStyle = (active: boolean) =>
    `flex items-center gap-2.5 cursor-pointer group py-1 ${active ? 'text-gold' : 'text-mist hover:text-cream'} transition-colors`

  return (
    <aside className="space-y-7">
      <div>
        <SectionLabel>Sort by</SectionLabel>
        <select
          value={get('sort_by') || 'relevance'}
          onChange={e => update('sort_by', e.target.value)}
          className="w-full font-mono text-xs bg-surface text-cream px-3 py-2 focus:outline-none appearance-none cursor-pointer"
          style={{ border: '1px solid var(--border)' }}
        >
          {SORT_OPTIONS.map(o => (
            <option key={o.value} value={o.value} className="bg-elevated">{o.label}</option>
          ))}
        </select>
      </div>

      <div>
        <SectionLabel>Degree Level</SectionLabel>
        <div className="space-y-0.5">
          {DEGREE_OPTIONS.map(o => {
            const count = facets?.degree_levels.find(f => f.key === o.value)?.count
            const active = get('degree_level') === o.value
            return (
              <label key={o.value} className={radioStyle(active)}>
                <input
                  type="radio"
                  name="degree_level"
                  value={o.value}
                  checked={active}
                  onChange={() => update('degree_level', o.value)}
                  className="hidden"
                />
                <span
                  className={`w-3 h-3 border flex items-center justify-center shrink-0 transition-colors ${
                    active ? 'border-gold bg-gold' : 'border-fog group-hover:border-mist'
                  }`}
                >
                  {active && <span className="w-1.5 h-1.5 bg-bg block" />}
                </span>
                <span className="font-mono text-xs flex-1">{o.label}</span>
                {count !== undefined && (
                  <span className="font-mono text-xs text-fog">{count}</span>
                )}
              </label>
            )
          })}
          {get('degree_level') && (
            <button onClick={() => update('degree_level', null)} className="font-mono text-xs text-gold hover:text-gold-bright mt-1 transition-colors">
              × clear
            </button>
          )}
        </div>
      </div>

      <div>
        <SectionLabel>Funding Type</SectionLabel>
        <div className="space-y-0.5">
          {FUNDING_OPTIONS.map(o => {
            const count = facets?.funding_types.find(f => f.key === o.value)?.count
            const active = get('funding_type') === o.value
            return (
              <label key={o.value} className={radioStyle(active)}>
                <input
                  type="radio"
                  name="funding_type"
                  value={o.value}
                  checked={active}
                  onChange={() => update('funding_type', o.value)}
                  className="hidden"
                />
                <span
                  className={`w-3 h-3 border flex items-center justify-center shrink-0 transition-colors ${
                    active ? 'border-gold bg-gold' : 'border-fog group-hover:border-mist'
                  }`}
                >
                  {active && <span className="w-1.5 h-1.5 bg-bg block" />}
                </span>
                <span className="font-mono text-xs flex-1">{o.label}</span>
                {count !== undefined && (
                  <span className="font-mono text-xs text-fog">{count}</span>
                )}
              </label>
            )
          })}
          {get('funding_type') && (
            <button onClick={() => update('funding_type', null)} className="font-mono text-xs text-gold hover:text-gold-bright mt-1 transition-colors">
              × clear
            </button>
          )}
        </div>
      </div>

      <div>
        <SectionLabel>Country</SectionLabel>
        <input
          type="text"
          placeholder="e.g. Germany"
          value={get('country')}
          onChange={e => update('country', e.target.value || null)}
          className="w-full font-mono text-xs bg-surface text-cream px-3 py-2 focus:outline-none placeholder:text-fog"
          style={{ border: '1px solid var(--border)' }}
        />
      </div>

      <div>
        <SectionLabel>Min. Stipend (USD)</SectionLabel>
        <input
          type="number"
          placeholder="e.g. 20000"
          min={0}
          step={5000}
          value={get('min_stipend')}
          onChange={e => update('min_stipend', e.target.value || null)}
          className="w-full font-mono text-xs bg-surface text-cream px-3 py-2 focus:outline-none placeholder:text-fog"
          style={{ border: '1px solid var(--border)' }}
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
          className="font-mono text-xs text-fog hover:text-mist transition-colors tracking-wide"
        >
          × clear all filters
        </button>
      )}
    </aside>
  )
}