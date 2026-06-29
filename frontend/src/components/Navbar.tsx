'use client'

import Link from 'next/link'
import { usePathname, useRouter } from 'next/navigation'
import { useAuth } from '@/lib/auth-context'
import { useState } from 'react'

export default function Navbar() {
  const { isAuthenticated, userEmail, logout } = useAuth()
  const pathname = usePathname()
  const router = useRouter()
  const [open, setOpen] = useState(false)

  function handleLogout() {
    logout()
    router.push('/')
  }

  const isActive = (href: string) => pathname.startsWith(href) && href !== '/'

  return (
    <header
      className="sticky top-0 z-50"
      style={{
        background: 'rgba(18, 16, 14, 0.85)',
        backdropFilter: 'blur(16px)',
        WebkitBackdropFilter: 'blur(16px)',
        borderBottom: '1px solid var(--border-dim)',
      }}
    >
      <nav className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-14 flex items-center justify-between gap-4">
        {/* Logo */}
        <Link href="/" className="flex items-center gap-2.5 shrink-0 group">
          <div className="w-6 h-6 flex items-center justify-center">
            <svg viewBox="0 0 24 24" fill="none" className="w-5 h-5 text-gold">
              <path
                d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5"
                stroke="currentColor"
                strokeWidth="1.5"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
            </svg>
          </div>
          <span className="font-display font-semibold text-cream text-base tracking-wide">
            Scholar<span className="text-gold">Scout</span>
          </span>
        </Link>

        {/* Desktop nav */}
        <div className="hidden md:flex items-center gap-8">
          {[{ href: '/search', label: 'Search' }].map(({ href, label }) => (
            <Link
              key={href}
              href={href}
              className={`text-sm tracking-wide transition-colors font-medium ${
                isActive(href) ? 'text-gold' : 'text-mist hover:text-cream'
              }`}
              style={isActive(href) ? { textShadow: '0 0 20px rgba(212,168,83,0.4)' } : {}}
            >
              {label}
            </Link>
          ))}
        </div>

        {/* Auth */}
        <div className="hidden md:flex items-center gap-4">
          {isAuthenticated ? (
            <>
              <span className="font-mono text-xs text-fog truncate max-w-[160px]">{userEmail}</span>
              {[
                { href: '/profile', label: 'Profile' },
                { href: '/alerts', label: 'Alerts' },
              ].map(({ href, label }) => (
                <Link
                  key={href}
                  href={href}
                  className="text-sm text-mist hover:text-cream transition-colors"
                >
                  {label}
                </Link>
              ))}
              <button
                onClick={handleLogout}
                className="text-sm text-fog hover:text-cream transition-colors"
              >
                Logout
              </button>
            </>
          ) : (
            <>
              <Link href="/auth/login" className="text-sm text-mist hover:text-cream transition-colors">
                Log in
              </Link>
              <Link
                href="/auth/register"
                className="text-sm font-semibold px-4 py-1.5 text-bg bg-gold hover:bg-gold-bright transition-colors"
                style={{ letterSpacing: '0.02em' }}
              >
                Get started
              </Link>
            </>
          )}
        </div>

        {/* Mobile toggle */}
        <button
          className="md:hidden p-1.5 text-mist hover:text-cream"
          onClick={() => setOpen(!open)}
          aria-label="Toggle menu"
        >
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            {open ? (
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M6 18L18 6M6 6l12 12" />
            ) : (
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M4 6h16M4 12h16M4 18h16" />
            )}
          </svg>
        </button>
      </nav>

      {/* Mobile menu */}
      {open && (
        <div
          className="md:hidden px-4 py-4 flex flex-col gap-3"
          style={{ borderTop: '1px solid var(--border-dim)' }}
        >
          <Link href="/search" className="text-sm text-cream" onClick={() => setOpen(false)}>Search</Link>
          {isAuthenticated ? (
            <>
              <Link href="/profile" className="text-sm text-mist" onClick={() => setOpen(false)}>Profile</Link>
              <Link href="/alerts" className="text-sm text-mist" onClick={() => setOpen(false)}>Alerts</Link>
              <button onClick={() => { handleLogout(); setOpen(false) }} className="text-sm text-fog text-left">Logout</button>
            </>
          ) : (
            <>
              <Link href="/auth/login" className="text-sm text-mist" onClick={() => setOpen(false)}>Log in</Link>
              <Link href="/auth/register" className="text-sm text-gold font-medium" onClick={() => setOpen(false)}>Get started</Link>
            </>
          )}
        </div>
      )}
    </header>
  )
}