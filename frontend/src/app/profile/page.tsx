'use client'

import { useEffect } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import { useAuth } from '@/lib/auth-context'

export default function ProfilePage() {
  const { isAuthenticated, userEmail, logout } = useAuth()
  const router = useRouter()

  useEffect(() => {
    if (!isAuthenticated) router.push('/auth/login')
  }, [isAuthenticated, router])

  if (!isAuthenticated) return null

  return (
    <main className="max-w-3xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
      <h1 className="text-2xl font-bold text-slate-900 mb-6">Profile</h1>

      <div className="bg-white rounded-2xl border border-slate-200 divide-y divide-slate-100">
        <div className="p-6">
          <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-1">Email</p>
          <p className="text-slate-800 font-medium">{userEmail}</p>
        </div>

        <div className="p-6">
          <h2 className="text-sm font-semibold text-slate-800 mb-3">Academic Profile</h2>
          <div className="bg-indigo-50 border border-indigo-100 rounded-xl p-5">
            <p className="text-sm font-medium text-indigo-700">Coming soon</p>
            <p className="text-xs text-indigo-500 mt-1 leading-relaxed">
              Set your GPA, language scores, research interests and target countries.
              ScholarScout will use these to personalize your recommendations.
            </p>
          </div>

          <div className="mt-4 grid sm:grid-cols-2 gap-3">
            {[
              { label: 'GPA / CGPA', placeholder: 'e.g. 3.8 / 4.0' },
              { label: 'IELTS / TOEFL', placeholder: 'e.g. IELTS 7.0' },
              { label: 'GRE Verbal', placeholder: 'e.g. 158' },
              { label: 'GRE Quant', placeholder: 'e.g. 167' },
            ].map(f => (
              <div key={f.label}>
                <label className="block text-xs font-medium text-slate-500 mb-1">{f.label}</label>
                <input
                  disabled
                  placeholder={f.placeholder}
                  className="w-full border border-slate-200 rounded-lg px-3 py-2 text-sm text-slate-400 bg-slate-50 cursor-not-allowed"
                />
              </div>
            ))}
          </div>
        </div>

        <div className="p-6 flex items-center justify-between">
          <Link href="/alerts" className="text-sm text-indigo-600 hover:underline font-medium">
            Manage search alerts
          </Link>
          <button
            onClick={() => {
              logout()
              router.push('/')
            }}
            className="text-sm text-red-500 hover:text-red-700 transition-colors"
          >
            Sign out
          </button>
        </div>
      </div>
    </main>
  )
}