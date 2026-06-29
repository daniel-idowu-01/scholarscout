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

export default function OpportunityCard({ hit }: { hit: SearchHit }) {
  const deadline = formatDeadline(hit.deadline)
  const stipend = formatStipend(hit.stipend_amount)

  return (
    <Link
      href={`/opportunities/${hit.id}`}
      className="block bg-white rounded-xl border border-slate-200 p-5 hover:border-indigo-300 hover:shadow-md transition-all group"
    >
      <div className="flex items-start justify-between gap-4">
        <div className="flex-1 min-w-0">
          <h3 className="font-semibold text-slate-900 group-hover:text-indigo-600 transition-colors line-clamp-2 leading-snug">
            {hit.title}
          </h3>
          <p className="mt-1 text-sm text-slate-500">
            {hit.university_name}
            {hit.country && ` · ${hit.country}`}
          </p>
        </div>
        {stipend && (
          <div className="shrink-0 text-right">
            <span className="text-sm font-semibold text-emerald-600">{stipend}</span>
            <p className="text-xs text-slate-400">/year</p>
          </div>
        )}
      </div>

      <div className="mt-3 flex flex-wrap gap-1.5">
        {hit.degree_level && <Badge label={hit.degree_level} variant="degree" />}
        {hit.funding_type && <Badge label={hit.funding_type} variant="funding" />}
        {hit.departments.slice(0, 2).map(d => (
          <Badge key={d} label={d} variant="tag" />
        ))}
      </div>

      {hit.description && (
        <p className="mt-3 text-sm text-slate-600 line-clamp-2 leading-relaxed">
          {hit.description}
        </p>
      )}

      <div className="mt-3 flex items-center justify-between gap-2">
        <div className="flex gap-2 flex-wrap">
          {hit.tags.slice(0, 3).map(t => (
            <span key={t} className="text-xs text-slate-400">
              #{t}
            </span>
          ))}
        </div>
        {hit.deadline && (
          <span
            className={`text-xs font-medium shrink-0 ${
              deadline.urgent ? 'text-amber-600' : 'text-slate-400'
            }`}
          >
            {deadline.urgent && '! '}{deadline.text}
          </span>
        )}
      </div>
    </Link>
  )
}