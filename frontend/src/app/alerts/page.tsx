'use client'

import { useEffect } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import { useAuth } from '@/lib/auth-context'

const EXAMPLES = [
  { query: 'Funded PhD Computer Science', filters: 'Germany · Fully funded', count: 12 },
  { query: 'Postdoc Machine Learning', filters: 'USA, Canada · Any funding', count: 8 },
  { query: 'Masters Scholarship Renewable Energy', filters: 'Netherlands · Fully funded', count: 4 },
]

export default function AlertsPage() {
  const { isAuthenticated } = useAuth()
  const router = useRouter()

  useEffect(() => {
    if (!isAuthenticated) router.push('/auth/login')
  }, [isAuthenticated, router])

  if (!isAuthenticated) return null

  return (
    <main className="max-w-3xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
      <div className="flex items-baseline justify-between mb-8">
        <h1 className="font-display text-3xl text-cream">Search Alerts</h1>
        <Link href="/search" className="font-mono text-xs text-gold hover:text-gold-bright transition-colors">
          + New search
        </Link>
      </div>

      {/* Notice */}
      <div
        className="px-5 py-4 mb-6 font-mono"
        style={{ border: '1px solid rgba(212,168,83,0.2)', background: 'rgba(212,168,83,0.04)' }}
      >
        <p className="text-xs text-gold mb-1">Email alerts — coming soon</p>
        <p className="text-xs text-fog leading-relaxed">
          Save searches and receive daily or weekly digests when new matching opportunities appear.
          For now, bookmark the search URL to revisit your query.
        </p>
      </div>

      {/* Preview list */}
      <div className="bg-surface" style={{ border: '1px solid var(--border-dim)' }}>
        <div className="px-5 py-3" style={{ borderBottom: '1px solid var(--border-dim)' }}>
          <p className="font-mono text-xs text-fog tracking-widest uppercase">Preview — Example alerts</p>
        </div>
        {EXAMPLES.map((a, i) => (
          <div
            key={a.query}
            className="flex items-center justify-between px-5 py-4"
            style={{ borderBottom: i < EXAMPLES.length - 1 ? '1px solid var(--border-dim)' : 'none' }}
          >
            <div>
              <p className="text-sm text-cream font-medium">{a.query}</p>
              <p className="font-mono text-xs text-fog mt-0.5">{a.filters}</p>
            </div>
            <span
              className="font-mono text-xs text-gold px-2.5 py-1 shrink-0 ml-4"
              style={{ border: '1px solid var(--border-bright)' }}
            >
              {a.count} new
            </span>
          </div>
        ))}
        <div className="px-5 py-3 text-center" style={{ borderTop: '1px solid var(--border-dim)' }}>
          <Link href="/search" className="font-mono text-xs text-mist hover:text-gold transition-colors">
            Go to search to create an alert →
          </Link>
        </div>
      </div>
    </main>
  )
}