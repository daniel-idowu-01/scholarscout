'use client'

import { useEffect, useState } from 'react'
import { useParams, useRouter } from 'next/navigation'
import Badge from '@/components/Badge'
import Spinner from '@/components/Spinner'
import { opportunitiesApi } from '@/lib/api'
import type { Opportunity } from '@/types'

function formatDeadline(d: string | null) {
  if (!d) return null
  if (d.toLowerCase() === 'rolling') return { label: 'Rolling', urgent: false, days: null }
  const date = new Date(d)
  if (isNaN(date.getTime())) return { label: d, urgent: false, days: null }
  const days = Math.ceil((date.getTime() - Date.now()) / 86_400_000)
  if (days < 0) return { label: 'Deadline passed', urgent: false, days }
  return {
    label: date.toLocaleDateString('en-US', { month: 'long', day: 'numeric', year: 'numeric' }),
    urgent: days <= 30,
    days,
  }
}

function InfoCard({ label, children, accent }: { label: string; children: React.ReactNode; accent?: boolean }) {
  return (
    <div
      className="p-4"
      style={{
        background: accent ? 'rgba(94,189,138,0.05)' : '#1c1a16',
        border: `1px solid ${accent ? 'rgba(94,189,138,0.2)' : 'var(--border-dim)'}`,
      }}
    >
      <p className="font-mono text-xs text-fog tracking-widest uppercase mb-1">{label}</p>
      <div className={`text-sm font-medium ${accent ? 'text-mint' : 'text-cream'}`}>{children}</div>
    </div>
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

  if (loading) return <div className="flex justify-center py-24"><Spinner /></div>

  if (error || !opp) {
    return (
      <div className="max-w-3xl mx-auto px-4 py-24 text-center">
        <p className="font-mono text-sm text-mist">{error ?? 'Opportunity not found'}</p>
        <button onClick={() => router.back()} className="mt-4 font-mono text-xs text-gold hover:text-gold-bright transition-colors">
          ← go back
        </button>
      </div>
    )
  }

  const deadline = formatDeadline(opp.deadline)
  const stipend = opp.stipend_amount
    ? new Intl.NumberFormat('en-US', { style: 'currency', currency: opp.stipend_currency || 'USD', maximumFractionDigits: 0 }).format(opp.stipend_amount) + '/year'
    : null
  const languageEntries = Object.entries(opp.language_requirements ?? {})

  return (
    <main className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-10">
      <button
        onClick={() => router.back()}
        className="flex items-center gap-2 font-mono text-xs text-fog hover:text-mist mb-8 transition-colors tracking-wide"
      >
        ← back to results
      </button>

      <div
        className="bg-surface p-8 animate-fade-in"
        style={{ border: '1px solid var(--border-dim)', animationFillMode: 'forwards' }}
      >
        {/* Header */}
        <div className="flex items-start justify-between gap-6 flex-wrap mb-5">
          <h1 className="font-display text-2xl sm:text-3xl text-cream leading-tight flex-1 min-w-0">
            {opp.title}
          </h1>
          {opp.source_url && (
            <a
              href={opp.source_url}
              target="_blank"
              rel="noopener noreferrer"
              className="shrink-0 px-6 py-2.5 bg-gold text-bg text-sm font-bold tracking-wide hover:bg-gold-bright transition-colors"
            >
              Apply / Visit ↗
            </a>
          )}
        </div>

        {/* Badges */}
        <div className="flex flex-wrap gap-1.5 mb-7">
          {opp.degree_level && <Badge label={opp.degree_level} variant="degree" />}
          {opp.funding_type && <Badge label={opp.funding_type} variant="funding" />}
          {opp.departments.map(d => <Badge key={d} label={d} variant="tag" />)}
        </div>

        {/* Key info grid */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 mb-8">
          {stipend && <InfoCard label="Stipend" accent>{stipend}</InfoCard>}
          {deadline && (
            <InfoCard label={deadline.days !== null && deadline.days <= 30 ? `Deadline · ${deadline.days}d` : 'Deadline'}>
              <span className={deadline.urgent ? 'text-[#fbbf24]' : 'text-cream'}>{deadline.label}</span>
            </InfoCard>
          )}
          {opp.duration_years != null && <InfoCard label="Duration">{opp.duration_years} years</InfoCard>}
          {opp.gpa_minimum != null && <InfoCard label="Min. GPA">{opp.gpa_minimum}</InfoCard>}
          {opp.tuition_covered != null && (
            <InfoCard label="Tuition">{opp.tuition_covered ? 'Covered' : 'Not covered'}</InfoCard>
          )}
        </div>

        {/* Divider */}
        <div className="h-px w-full mb-8" style={{ background: 'var(--border-dim)' }} />

        {/* Description */}
        {opp.description && (
          <section className="mb-8">
            <p className="font-mono text-xs text-fog tracking-widest uppercase mb-3">Description</p>
            <p className="text-mist leading-relaxed">{opp.description}</p>
          </section>
        )}

        {/* Requirements */}
        {opp.requirements.length > 0 && (
          <section className="mb-8">
            <p className="font-mono text-xs text-fog tracking-widest uppercase mb-3">Requirements</p>
            <ul className="space-y-2">
              {opp.requirements.map((r, i) => (
                <li key={i} className="flex items-start gap-3 text-sm text-mist">
                  <span className="text-gold mt-0.5 shrink-0 font-mono">›</span>
                  {r}
                </li>
              ))}
            </ul>
          </section>
        )}

        {/* Language requirements */}
        {languageEntries.length > 0 && (
          <section className="mb-8">
            <p className="font-mono text-xs text-fog tracking-widest uppercase mb-3">Language Requirements</p>
            <div className="flex flex-wrap gap-2">
              {languageEntries.map(([lang, score]) => (
                <div
                  key={lang}
                  className="px-3 py-1.5"
                  style={{ border: '1px solid var(--border)' }}
                >
                  <span className="font-mono text-xs font-medium text-cream">{lang.toUpperCase()}</span>
                  <span className="font-mono text-xs text-mist ml-2">{score}</span>
                </div>
              ))}
            </div>
          </section>
        )}

        {/* Citizenship */}
        {opp.citizenship_restrictions && opp.citizenship_restrictions.length > 0 && (
          <section className="mb-8">
            <p className="font-mono text-xs text-fog tracking-widest uppercase mb-3">Citizenship</p>
            <p className="font-mono text-xs text-mist">{opp.citizenship_restrictions.join(', ')}</p>
          </section>
        )}

        {/* Tags */}
        {opp.tags.length > 0 && (
          <section className="mb-8">
            <p className="font-mono text-xs text-fog tracking-widest uppercase mb-3">Tags</p>
            <div className="flex flex-wrap gap-1.5">
              {opp.tags.map(t => <Badge key={t} label={t} variant="tag" />)}
            </div>
          </section>
        )}

        {/* Footer */}
        <div className="pt-6 flex items-center justify-between gap-4 flex-wrap" style={{ borderTop: '1px solid var(--border-dim)' }}>
          <span className="font-mono text-xs text-fog">
            Verified {new Date(opp.last_verified_at).toLocaleDateString('en-US', { year: 'numeric', month: 'long', day: 'numeric' })}
          </span>
          {opp.source_url && (() => {
            try {
              return (
                <a href={opp.source_url} target="_blank" rel="noopener noreferrer" className="font-mono text-xs text-gold hover:text-gold-bright transition-colors truncate max-w-xs">
                  {new URL(opp.source_url).hostname} ↗
                </a>
              )
            } catch { return null }
          })()}
        </div>
      </div>
    </main>
  )
}