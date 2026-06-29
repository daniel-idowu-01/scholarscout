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
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold text-slate-900">Search Alerts</h1>
        <Link
          href="/search"
          className="text-sm font-medium text-indigo-600 hover:underline"
        >
          + New search
        </Link>
      </div>

      <div className="bg-indigo-50 border border-indigo-200 rounded-xl p-5 mb-6">
        <p className="text-sm font-semibold text-indigo-700">Email alerts are coming soon</p>
        <p className="text-xs text-indigo-500 mt-1 leading-relaxed">
          Save any search and receive daily or weekly email digests when new matching
          opportunities are posted. For now, bookmark the search URL to revisit it.
        </p>
      </div>

      <div className="bg-white rounded-2xl border border-slate-200 overflow-hidden">
        <div className="px-6 py-4 border-b border-slate-100">
          <h2 className="text-sm font-semibold text-slate-700">Preview — Example alerts</h2>
        </div>
        <div className="divide-y divide-slate-100">
          {EXAMPLES.map(a => (
            <div key={a.query} className="flex items-center justify-between px-6 py-4">
              <div>
                <p className="text-sm font-medium text-slate-800">{a.query}</p>
                <p className="text-xs text-slate-400 mt-0.5">{a.filters}</p>
              </div>
              <span className="text-xs font-semibold text-indigo-600 bg-indigo-50 px-2.5 py-1 rounded-full shrink-0 ml-4">
                {a.count} new
              </span>
            </div>
          ))}
        </div>
        <div className="px-6 py-4 border-t border-slate-100 text-center">
          <Link href="/search" className="text-sm text-indigo-600 hover:underline">
            Go to search to create an alert
          </Link>
        </div>
      </div>
    </main>
  )
}