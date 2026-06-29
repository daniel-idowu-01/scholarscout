const DEGREE_COLORS: Record<string, string> = {
  phd: 'bg-purple-100 text-purple-700',
  masters: 'bg-blue-100 text-blue-700',
  master: 'bg-blue-100 text-blue-700',
  bachelor: 'bg-cyan-100 text-cyan-700',
  postdoc: 'bg-violet-100 text-violet-700',
  undergraduate: 'bg-sky-100 text-sky-700',
}

const FUNDING_COLORS: Record<string, string> = {
  fully_funded: 'bg-emerald-100 text-emerald-700',
  partial: 'bg-amber-100 text-amber-700',
  tuition_only: 'bg-sky-100 text-sky-700',
  stipend_only: 'bg-teal-100 text-teal-700',
}

const FUNDING_LABELS: Record<string, string> = {
  fully_funded: 'Fully Funded',
  partial: 'Partial Funding',
  tuition_only: 'Tuition Only',
  stipend_only: 'Stipend Only',
}

interface BadgeProps {
  label: string
  variant?: 'degree' | 'funding' | 'tag'
}

export default function Badge({ label, variant = 'tag' }: BadgeProps) {
  const base = 'inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium'
  const key = label.toLowerCase()

  if (variant === 'degree') {
    const color = DEGREE_COLORS[key] ?? 'bg-slate-100 text-slate-600'
    const display = label.charAt(0).toUpperCase() + label.slice(1)
    return <span className={`${base} ${color}`}>{display}</span>
  }

  if (variant === 'funding') {
    const color = FUNDING_COLORS[key] ?? 'bg-slate-100 text-slate-600'
    const display = FUNDING_LABELS[key] ?? label
    return <span className={`${base} ${color}`}>{display}</span>
  }

  return <span className={`${base} bg-slate-100 text-slate-600`}>{label}</span>
}