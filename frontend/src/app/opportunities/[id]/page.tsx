'use client'

import { useEffect, useState } from 'react'
import { useParams, useRouter } from 'next/navigation'
import Badge from '@/components/Badge'
import Spinner from '@/components/Spinner'
import { opportunitiesApi } from '@/lib/api'
import type { Opportunity } from '@/types'

function formatDeadline(d: string | null) {
  if (!d) return null
  if (d.toLowerCase() === 'rolling') return { label: 'Rolling', urgent: false }
  const date = new Date(d)
  if (isNaN(date.getTime())) return { label: d, urgent: false }
  const days = Math.ceil((date.getTime() - Date.now()) / 86_400_000)
  if (days < 0) return { label: 'Deadline passed', urgent: false }
  return {
    label: date.toLocaleDateString('en-US', { month: 'long', day: 'numeric', year: 'numeric' }),
    urgent: days <= 30,
    daysLeft: days,
  }
}

function formatStipend(amount: number | null, currency = 'USD') {
  if (!amount) return null
  return (
    new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency,
      maximumFractionDigits: 0,
    }).format(amount) + '/year'
  )
}

export default function OpportunityDetailPage() {
  const { id } = useParams<{ id: string }>()
  const router = useRouter()
  const [opp, setOpp] = useState<Opportunity | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    opportunitiesApi
      .get(id)
      .then(setOpp)
      .catch(e => setError((e as Error).message))
      .finally(() => setLoading(false))
  }, [id])

  if (loading) {
    return (
      <div className="flex justify-center py-24">
        <Spinner />
      </div>
    )
  }

  if (error || !opp) {
    return (
      <div className="max-w-3xl mx-auto px-4 py-24 text-center">
        <p className="text-slate-500">{error ?? 'Opportunity not found'}</p>
        <button onClick={() => router.back()} className="mt-4 text-sm text-indigo-600 hover:underline">
          Go back
        </button>
      </div>
    )
  }

  const deadline = formatDeadline(opp.deadline)
  const stipend = formatStipend(opp.stipend_amount, opp.stipend_currency)
  const languageEntries = Object.entries(opp.language_requirements ?? {})

  return (
    <main className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-10">
      <button
        onClick={() => router.back()}
        className="flex items-center gap-1 text-sm text-slate-500 hover:text-slate-800 mb-6 transition-colors"
      >
        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
        </svg>
        Back to results
      </button>

      <div className="bg-white rounded-2xl border border-slate-200 p-8">
        {/* Header */}
        <div className="flex items-start justify-between gap-6 flex-wrap">
          <div className="flex-1 min-w-0">
            <h1 className="text-2xl font-bold text-slate-900 leading-snug">{opp.title}</h1>
          </div>
          {opp.source_url && (
            <a
              href={opp.source_url}
              target="_blank"
              rel="noopener noreferrer"
              className="shrink-0 px-6 py-2.5 bg-indigo-600 text-white text-sm font-semibold rounded-xl hover:bg-indigo-700 transition-colors"
            >
              Apply / Visit
            </a>
          )}
        </div>

        {/* Badges */}
        <div className="mt-4 flex flex-wrap gap-2">
          {opp.degree_level && <Badge label={opp.degree_level} variant="degree" />}
          {opp.funding_type && <Badge label={opp.funding_type} variant="funding" />}
          {opp.departments.map(d => (
            <Badge key={d} label={d} variant="tag" />
          ))}
        </div>

        {/* Key info cards */}
        <div className="mt-6 grid grid-cols-2 sm:grid-cols-4 gap-3">
          {stipend && (
            <div className="col-span-2 sm:col-span-1 bg-emerald-50 rounded-xl p-4">
              <p className="text-xs font-semibold text-emerald-600 uppercase tracking-wide">Stipend</p>
              <p className="mt-1 text-lg font-bold text-emerald-700">{stipend}</p>
            </div>
          )}
          {deadline && (
            <div className={`col-span-2 sm:col-span-1 rounded-xl p-4 ${deadline.urgent ? 'bg-amber-50' : 'bg-slate-50'}`}>
              <p className={`text-xs font-semibold uppercase tracking-wide ${deadline.urgent ? 'text-amber-600' : 'text-slate-500'}`}>
                Deadline{deadline.urgent && deadline.daysLeft !== undefined ? ` · ${deadline.daysLeft}d` : ''}
              </p>
              <p className={`mt-1 text-sm font-semibold ${deadline.urgent ? 'text-amber-700' : 'text-slate-800'}`}>
                {deadline.label}
              </p>
            </div>
          )}
          {opp.duration_years != null && (
            <div className="bg-slate-50 rounded-xl p-4">
              <p className="text-xs font-semibold text-slate-500 uppercase tracking-wide">Duration</p>
              <p className="mt-1 text-sm font-semibold text-slate-800">{opp.duration_years} years</p>
            </div>
          )}
          {opp.gpa_minimum != null && (
            <div className="bg-slate-50 rounded-xl p-4">
              <p className="text-xs font-semibold text-slate-500 uppercase tracking-wide">Min. GPA</p>
              <p className="mt-1 text-sm font-semibold text-slate-800">{opp.gpa_minimum}</p>
            </div>
          )}
          {opp.tuition_covered != null && (
            <div className="bg-slate-50 rounded-xl p-4">
              <p className="text-xs font-semibold text-slate-500 uppercase tracking-wide">Tuition</p>
              <p className="mt-1 text-sm font-semibold text-slate-800">
                {opp.tuition_covered ? 'Covered' : 'Not covered'}
              </p>
            </div>
          )}
        </div>

        {/* Description */}
        {opp.description && (
          <section className="mt-8">
            <h2 className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-3">Description</h2>
            <p className="text-slate-700 leading-relaxed">{opp.description}</p>
          </section>
        )}

        {/* Requirements */}
        {opp.requirements.length > 0 && (
          <section className="mt-8">
            <h2 className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-3">Requirements</h2>
            <ul className="space-y-2">
              {opp.requirements.map((r, i) => (
                <li key={i} className="flex items-start gap-2 text-sm text-slate-700">
                  <svg
                    className="w-4 h-4 text-indigo-400 mt-0.5 shrink-0"
                    fill="currentColor"
                    viewBox="0 0 20 20"
                  >
                    <path
                      fillRule="evenodd"
                      d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z"
                      clipRule="evenodd"
                    />
                  </svg>
                  {r}
                </li>
              ))}
            </ul>
          </section>
        )}

        {/* Language requirements */}
        {languageEntries.length > 0 && (
          <section className="mt-8">
            <h2 className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-3">
              Language Requirements
            </h2>
            <div className="flex flex-wrap gap-3">
              {languageEntries.map(([lang, score]) => (
                <div key={lang} className="bg-slate-50 rounded-lg px-3 py-2">
                  <span className="text-sm font-semibold text-slate-700">{lang.toUpperCase()}</span>
                  <span className="text-sm text-slate-500 ml-1.5">{score}</span>
                </div>
              ))}
            </div>
          </section>
        )}

        {/* Citizenship restrictions */}
        {opp.citizenship_restrictions && opp.citizenship_restrictions.length > 0 && (
          <section className="mt-8">
            <h2 className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-3">
              Citizenship
            </h2>
            <p className="text-sm text-slate-700">{opp.citizenship_restrictions.join(', ')}</p>
          </section>
        )}

        {/* Tags */}
        {opp.tags.length > 0 && (
          <section className="mt-8">
            <h2 className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-3">Tags</h2>
            <div className="flex flex-wrap gap-2">
              {opp.tags.map(t => (
                <Badge key={t} label={t} variant="tag" />
              ))}
            </div>
          </section>
        )}

        {/* Footer */}
        <div className="mt-8 pt-6 border-t border-slate-100 flex items-center justify-between text-xs text-slate-400 gap-4 flex-wrap">
          <span>
            Last verified:{' '}
            {new Date(opp.last_verified_at).toLocaleDateString('en-US', {
              year: 'numeric',
              month: 'long',
              day: 'numeric',
            })}
          </span>
          {opp.source_url && (() => {
            try {
              return (
                <a
                  href={opp.source_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-indigo-400 hover:text-indigo-600 truncate max-w-xs transition-colors"
                >
                  {new URL(opp.source_url).hostname}
                </a>
              )
            } catch {
              return null
            }
          })()}
        </div>
      </div>
    </main>
  )
}