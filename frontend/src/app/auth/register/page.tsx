'use client'

import React, { useState } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import { authApi } from '@/lib/api'
import { useAuth } from '@/lib/auth-context'

function Field({ label, optional, children }: { label: string; optional?: boolean; children: React.ReactNode }) {
  return (
    <div>
      <label className="font-mono text-xs text-fog tracking-widest uppercase block mb-2">
        {label}{optional && <span className="text-fog normal-case ml-1">(optional)</span>}
      </label>
      {children}
    </div>
  )
}

const inputCls = 'w-full bg-surface text-cream text-sm px-4 py-3 focus:outline-none placeholder:text-fog'
const inputStyle = { border: '1px solid var(--border)' }

export default function RegisterPage() {
  const { login } = useAuth()
  const router = useRouter()
  const [name, setName] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  async function handleSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault()
    if (password.length < 8) { setError('Password must be at least 8 characters'); return }
    setError(null)
    setLoading(true)
    try {
      const token = await authApi.register({ email, password, name: name || undefined })
      login(token)
      router.push('/search')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Registration failed')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-[75vh] flex items-center justify-center px-4 py-12 bg-dot-grid">
      <div
        className="w-full max-w-sm bg-surface p-8 animate-fade-up"
        style={{ border: '1px solid var(--border)', animationFillMode: 'forwards' }}
      >
        <div className="mb-8">
          <h1 className="font-display text-2xl text-cream mb-1">Create your account</h1>
          <p className="font-mono text-xs text-fog tracking-wide">Start finding funded opportunities</p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-5">
          {error && (
            <div
              className="font-mono text-xs text-[#f87171] px-4 py-3"
              style={{ border: '1px solid rgba(248,113,113,0.2)', background: 'rgba(248,113,113,0.05)' }}
            >
              {error}
            </div>
          )}

          <Field label="Name" optional>
            <input type="text" value={name} onChange={e => setName(e.target.value)} autoComplete="name" placeholder="Your name" className={inputCls} style={inputStyle} />
          </Field>

          <Field label="Email">
            <input type="email" value={email} onChange={e => setEmail(e.target.value)} required autoComplete="email" placeholder="you@university.edu" className={inputCls} style={inputStyle} />
          </Field>

          <Field label="Password">
            <input type="password" value={password} onChange={e => setPassword(e.target.value)} required minLength={8} autoComplete="new-password" placeholder="Min. 8 characters" className={inputCls} style={inputStyle} />
          </Field>

          <button
            type="submit"
            disabled={loading}
            className="w-full py-3 bg-gold text-bg text-sm font-bold tracking-wide hover:bg-gold-bright disabled:opacity-50 transition-colors"
          >
            {loading ? 'Creating account...' : 'Create account'}
          </button>
        </form>

        <p className="mt-6 font-mono text-xs text-fog text-center">
          Already have an account?{' '}
          <Link href="/auth/login" className="text-gold hover:text-gold-bright transition-colors">Sign in</Link>
        </p>
      </div>
    </div>
  )
}