'use client'

import { useEffect } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import { useAuth } from '@/lib/auth-context'

const FIELDS = [
  { label: 'GPA / CGPA', placeholder: 'e.g. 3.8 / 4.0' },
  { label: 'IELTS / TOEFL', placeholder: 'e.g. IELTS 7.0' },
  { label: 'GRE Verbal', placeholder: 'e.g. 158' },
  { label: 'GRE Quant', placeholder: 'e.g. 167' },
]

export default function ProfilePage() {
  const { isAuthenticated, userEmail, logout } = useAuth()
  const router = useRouter()

  useEffect(() => {
    if (!isAuthenticated) router.push('/auth/login')
  }, [isAuthenticated, router])

  if (!isAuthenticated) return null

  return (
    <main className="max-w-3xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
      <h1 className="font-display text-3xl text-cream mb-8">Profile</h1>

      <div className="bg-surface" style={{ border: '1px solid var(--border-dim)' }}>
        {/* Email */}
        <div className="px-6 py-5" style={{ borderBottom: '1px solid var(--border-dim)' }}>
          <p className="font-mono text-xs text-fog tracking-widest uppercase mb-1.5">Email</p>
          <p className="font-mono text-sm text-cream">{userEmail}</p>
        </div>

        {/* Academic profile */}
        <div className="px-6 py-5" style={{ borderBottom: '1px solid var(--border-dim)' }}>
          <p className="font-display text-base text-cream mb-1">Academic Profile</p>
          <p className="font-mono text-xs text-fog mb-5">
            Extended profile editing coming soon — GPA, test scores, research interests and target countries.
          </p>
          <div className="grid sm:grid-cols-2 gap-3">
            {FIELDS.map(f => (
              <div key={f.label}>
                <label className="font-mono text-xs text-fog tracking-widest uppercase block mb-1.5">{f.label}</label>
                <input
                  disabled
                  placeholder={f.placeholder}
                  className="w-full font-mono text-xs text-fog px-3 py-2 bg-elevated cursor-not-allowed placeholder:text-fog"
                  style={{ border: '1px solid var(--border-dim)' }}
                />
              </div>
            ))}
          </div>
        </div>

        {/* Actions */}
        <div className="px-6 py-4 flex items-center justify-between">
          <Link href="/alerts" className="font-mono text-xs text-gold hover:text-gold-bright transition-colors">
            Manage alerts →
          </Link>
          <button
            onClick={() => { logout(); router.push('/') }}
            className="font-mono text-xs text-fog hover:text-mist transition-colors"
          >
            Sign out
          </button>
        </div>
      </div>
    </main>
  )
}