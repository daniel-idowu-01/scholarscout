const DEGREE: Record<string, string> = {
  phd: 'bg-[#1e1428] text-[#c084fc] border-[#6d28a0]',
  masters: 'bg-[#0f1e2e] text-[#60a5fa] border-[#1d4e8a]',
  master: 'bg-[#0f1e2e] text-[#60a5fa] border-[#1d4e8a]',
  bachelor: 'bg-[#0e2020] text-[#34d399] border-[#065f46]',
  postdoc: 'bg-[#1a1020] text-[#a78bfa] border-[#5b21b6]',
  undergraduate: 'bg-[#0e2020] text-[#34d399] border-[#065f46]',
}

const FUNDING: Record<string, string> = {
  fully_funded: 'bg-[#0e1e14] text-[#4ade80] border-[#14532d]',
  partial: 'bg-[#1e1800] text-[#fbbf24] border-[#78350f]',
  tuition_only: 'bg-[#0f1e2e] text-[#38bdf8] border-[#0369a1]',
  stipend_only: 'bg-[#0e1e1a] text-[#2dd4bf] border-[#134e4a]',
}

const FUNDING_LABELS: Record<string, string> = {
  fully_funded: 'Fully Funded',
  partial: 'Partial',
  tuition_only: 'Tuition Only',
  stipend_only: 'Stipend Only',
}

interface BadgeProps {
  label: string
  variant?: 'degree' | 'funding' | 'tag'
}

export default function Badge({ label, variant = 'tag' }: BadgeProps) {
  const base = 'inline-flex items-center px-2 py-0.5 text-xs font-mono border'
  const key = label.toLowerCase()

  if (variant === 'degree') {
    const cls = DEGREE[key] ?? 'bg-[#1a1814] text-mist border-[var(--border)]'
    return <span className={`${base} ${cls}`}>{label.toUpperCase()}</span>
  }

  if (variant === 'funding') {
    const cls = FUNDING[key] ?? 'bg-[#1a1814] text-mist border-[var(--border)]'
    return <span className={`${base} ${cls}`}>{FUNDING_LABELS[key] ?? label}</span>
  }

  return (
    <span
      className="inline-flex items-center px-2 py-0.5 font-mono text-xs text-fog"
      style={{ border: '1px solid var(--border-dim)' }}
    >
      {label}
    </span>
  )
}