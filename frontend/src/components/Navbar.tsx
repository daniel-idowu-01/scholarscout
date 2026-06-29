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

  const link = (href: string, label: string) => (
    <Link
      href={href}
      className={`text-sm font-medium transition-colors ${
        pathname.startsWith(href) && href !== '/'
          ? 'text-indigo-600'
          : 'text-slate-600 hover:text-slate-900'
      }`}
    >
      {label}
    </Link>
  )

  return (
    <header className="sticky top-0 z-50 bg-white border-b border-slate-200 shadow-sm">
      <nav className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between gap-4">
        <Link href="/" className="flex items-center gap-2 shrink-0">
          <svg className="w-6 h-6 text-indigo-600" fill="currentColor" viewBox="0 0 24 24">
            <path d="M12 3L1 9l4 2.18v6L12 21l7-3.82v-6l2-1.09V17h2V9L12 3zm6.82 6L12 12.72 5.18 9 12 5.28 18.82 9zM17 15.99l-5 2.73-5-2.73v-3.72L12 15l5-2.73v3.72z" />
          </svg>
          <span className="font-bold text-slate-900 text-lg">ScholarScout</span>
        </Link>

        <div className="hidden md:flex items-center gap-6">
          {link('/search', 'Search')}
        </div>

        <div className="hidden md:flex items-center gap-3">
          {isAuthenticated ? (
            <>
              <span className="text-xs text-slate-400 truncate max-w-[160px]">{userEmail}</span>
              {link('/profile', 'Profile')}
              {link('/alerts', 'Alerts')}
              <button
                onClick={handleLogout}
                className="text-sm font-medium text-red-500 hover:text-red-700 transition-colors"
              >
                Logout
              </button>
            </>
          ) : (
            <>
              <Link href="/auth/login" className="text-sm font-medium text-slate-600 hover:text-slate-900">
                Log in
              </Link>
              <Link
                href="/auth/register"
                className="text-sm font-semibold px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 transition-colors"
              >
                Get started
              </Link>
            </>
          )}
        </div>

        <button
          className="md:hidden p-2 text-slate-500 hover:text-slate-700"
          onClick={() => setOpen(!open)}
          aria-label="Toggle menu"
        >
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            {open ? (
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            ) : (
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
            )}
          </svg>
        </button>
      </nav>

      {open && (
        <div className="md:hidden border-t border-slate-100 bg-white px-4 py-4 flex flex-col gap-3">
          <Link href="/search" className="text-sm text-slate-700" onClick={() => setOpen(false)}>Search</Link>
          {isAuthenticated ? (
            <>
              <Link href="/profile" className="text-sm text-slate-700" onClick={() => setOpen(false)}>Profile</Link>
              <Link href="/alerts" className="text-sm text-slate-700" onClick={() => setOpen(false)}>Alerts</Link>
              <button onClick={() => { handleLogout(); setOpen(false) }} className="text-sm text-red-500 text-left">Logout</button>
            </>
          ) : (
            <>
              <Link href="/auth/login" className="text-sm text-slate-700" onClick={() => setOpen(false)}>Log in</Link>
              <Link href="/auth/register" className="text-sm font-medium text-indigo-600" onClick={() => setOpen(false)}>Get started</Link>
            </>
          )}
        </div>
      )}
    </header>
  )
}