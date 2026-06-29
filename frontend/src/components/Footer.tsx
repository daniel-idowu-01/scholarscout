import Link from 'next/link'

export default function Footer() {
  return (
    <footer className="border-t border-slate-200 bg-white">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 flex flex-col sm:flex-row items-center justify-between gap-4">
        <p className="text-sm text-slate-400">
          ScholarScout — Graduate opportunity discovery
        </p>
        <div className="flex gap-6 text-sm text-slate-400">
          <Link href="/search" className="hover:text-slate-600 transition-colors">Search</Link>
          <Link href="/auth/register" className="hover:text-slate-600 transition-colors">Sign up</Link>
        </div>
      </div>
    </footer>
  )
}