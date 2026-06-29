import Link from 'next/link'

export default function Footer() {
  return (
    <footer style={{ borderTop: '1px solid var(--border-dim)' }} className="bg-bg mt-auto">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 flex flex-col sm:flex-row items-center justify-between gap-4">
        <span className="font-display italic text-mist text-sm">ScholarScout</span>
        <div className="flex gap-6 text-xs font-mono text-fog">
          <Link href="/search" className="hover:text-mist transition-colors tracking-widest uppercase">Search</Link>
          <Link href="/auth/register" className="hover:text-mist transition-colors tracking-widest uppercase">Sign up</Link>
        </div>
      </div>
    </footer>
  )
}