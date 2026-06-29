import Link from 'next/link'
import Badge from './Badge'
import type { SearchHit } from '@/types'

function formatDeadline(deadline: string | null): { text: string; urgent: boolean } {
  if (!deadline) return { text: 'Rolling', urgent: false }
  if (deadline.toLowerCase() === 'rolling') return { text: 'Rolling', urgent: false }
  const date = new Date(deadline)
  if (isNaN(date.getTime())) return { text: deadline, urgent: false }
  const days = Math.ceil((date.getTime() - Date.now()) / 86_400_000)
  if (days < 0) return { text: 'Closed', urgent: false }
  if (days <= 30) return { text: `${days}d left`, urgent: true }
  return {
    text: date.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' }),
    urgent: false,
  }
}

function formatStipend(amount: number | null): string | null {
  if (!amount) return null
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    maximumFractionDigits: 0,
  }).format(amount)
}

export default function OpportunityCard({ hit, index = 0 }: { hit: SearchHit; index?: number }) {
  const deadline = formatDeadline(hit.deadline)
  const stipend = formatStipend(hit.stipend_amount)

  return (
    <Link
      href={`/opportunities/${hit.id}`}
      className="card-accent block bg-surface p-5 group transition-all duration-200 hover:bg-elevated animate-fade-up"
      style={{
        border: '1px solid var(--border-dim)',
        animationDelay: `${index * 0.04}s`,
        animationFillMode: 'forwards',
        opacity: 0,
      }}
    >
      <div className="flex items-start justify-between gap-4">
        <div className="flex-1 min-w-0 pl-3">
          <h3 className="font-display text-base font-semibold text-cream group-hover:text-gold-bright transition-colors line-clamp-2 leading-snug">
            {hit.title}
          </h3>
          <p className="mt-1 font-mono text-xs text-mist">
            {hit.university_name}
            {hit.country && <span className="text-fog"> · {hit.country}</span>}
          </p>
        </div>

        {stipend && (
          <div className="shrink-0 text-right">
            <span className="font-mono text-sm font-medium text-mint">{stipend}</span>
            <p className="font-mono text-xs text-fog">/year</p>
          </div>
        )}
      </div>

      <div className="mt-3 pl-3 flex flex-wrap gap-1.5">
        {hit.degree_level && <Badge label={hit.degree_level} variant="degree" />}
        {hit.funding_type && <Badge label={hit.funding_type} variant="funding" />}
        {hit.departments.slice(0, 2).map(d => (
          <Badge key={d} label={d} variant="tag" />
        ))}
      </div>

      {hit.description && (
        <p className="mt-3 pl-3 text-sm text-mist line-clamp-2 leading-relaxed">
          {hit.description}
        </p>
      )}

      <div className="mt-3 pl-3 flex items-center justify-between gap-2">
        <div className="flex gap-2 flex-wrap">
          {hit.tags.slice(0, 3).map(t => (
            <span key={t} className="font-mono text-xs text-fog">
              #{t}
            </span>
          ))}
        </div>
        {hit.deadline && (
          <span
            className={`font-mono text-xs shrink-0 ${
              deadline.urgent ? 'text-[#fbbf24]' : 'text-fog'
            }`}
          >
            {deadline.urgent && '↯ '}{deadline.text}
          </span>
        )}
      </div>
    </Link>
  )
}