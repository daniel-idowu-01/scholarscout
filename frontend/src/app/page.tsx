import Link from 'next/link'

const POPULAR = [
  'Funded PhD Computer Science',
  'Masters Scholarship Germany',
  'Postdoc Machine Learning',
  'Fellowship Renewable Energy',
]

const STATS = [
  { value: '50,000+', label: 'Opportunities indexed' },
  { value: '500+',    label: 'Universities monitored' },
  { value: '100+',   label: 'Countries covered' },
  { value: 'Daily',  label: 'Crawler runs' },
]

const STEPS = [
  {
    num: '01',
    title: 'We crawl universities daily',
    body: 'Our engine monitors 500+ top universities worldwide, surfacing scholarships, funded PhDs, fellowships and research assistantships as they appear.',
  },
  {
    num: '02',
    title: 'AI extracts every detail',
    body: 'Deadlines, stipend amounts, GPA thresholds, language requirements and department scope — extracted and normalised from raw university pages.',
  },
  {
    num: '03',
    title: 'You search. You find. You apply.',
    body: 'Filter by field, country, funding type or degree level. Set alerts and receive digests when new matching opportunities are published.',
  },
]

export default function LandingPage() {
  return (
    <main className="bg-bg">

      {/* ── Hero ──────────────────────────────────────────────── */}
      <section className="relative overflow-hidden min-h-[92vh] flex flex-col justify-center">

        {/* Background layers */}
        <div className="absolute inset-0 bg-dot-grid" />
        <div
          className="absolute inset-0"
          style={{
            background:
              'radial-gradient(ellipse 100% 60% at 50% 0%, rgba(212,168,83,0.11) 0%, transparent 60%)',
          }}
        />
        {/* Bottom fade into body */}
        <div
          className="absolute bottom-0 left-0 right-0 h-32 pointer-events-none"
          style={{ background: 'linear-gradient(to bottom, transparent, #12100e)' }}
        />

        <div className="relative z-10 max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 pt-24 pb-32 w-full">

          {/* Eyebrow */}
          <div
            className="inline-flex items-center gap-2.5 px-4 py-2 mb-10 animate-fade-in"
            style={{ border: '1px solid rgba(212,168,83,0.3)', animationDelay: '0s' }}
          >
            <span className="w-1.5 h-1.5 bg-mint" style={{ borderRadius: 0 }} />
            <span className="font-mono text-[11px] text-mist tracking-[0.2em] uppercase">
              Graduate Opportunities Platform
            </span>
          </div>

          {/* Main headline — two-line editorial */}
          <h1
            className="font-display text-cream leading-[1.05] tracking-tight mb-8 animate-fade-up"
            style={{
              fontSize: 'clamp(2.8rem, 7vw, 5.5rem)',
              animationDelay: '0.08s',
            }}
          >
            Find funded research.<br />
            <span className="italic text-gradient-gold">Stop missing deadlines.</span>
          </h1>

          {/* Descriptor — tight, punchy */}
          <p
            className="text-mist text-xl max-w-xl leading-relaxed mb-12 animate-fade-up"
            style={{ animationDelay: '0.18s' }}
          >
            Scholarships, funded PhDs, fellowships and assistantships from 500+ universities —
            crawled daily, AI-extracted, instantly searchable.
          </p>

          {/* Search + CTA row */}
          <div
            className="flex flex-col sm:flex-row items-stretch gap-0 max-w-2xl animate-fade-up"
            style={{ animationDelay: '0.28s' }}
          >
            <form action="/search" method="get" className="flex flex-1">
              <input
                name="q"
                type="text"
                placeholder='e.g. "Fully funded AI PhD in Europe"'
                className="flex-1 px-5 py-4 bg-surface text-cream text-sm focus:outline-none placeholder:text-fog min-w-0"
                style={{ border: '1px solid rgba(212,168,83,0.25)', borderRight: 'none' }}
              />
              <button
                type="submit"
                className="px-7 py-4 bg-gold text-bg text-sm font-bold tracking-wide hover:bg-gold-bright transition-colors shrink-0 whitespace-nowrap"
              >
                Search
              </button>
            </form>
            <Link
              href="/auth/register"
              className="sm:ml-3 px-7 py-4 text-cream text-sm font-medium tracking-wide hover:text-gold transition-colors shrink-0 whitespace-nowrap text-center"
              style={{ border: '1px solid rgba(232,220,200,0.12)' }}
            >
              Create account
            </Link>
          </div>

          {/* Popular chips */}
          <div
            className="mt-6 flex flex-wrap items-center gap-x-4 gap-y-2 animate-fade-in"
            style={{ animationDelay: '0.44s' }}
          >
            <span className="font-mono text-[11px] text-fog tracking-widest uppercase">Popular:</span>
            {POPULAR.map((t, i) => (
              <Link
                key={t}
                href={`/search?q=${encodeURIComponent(t)}`}
                className="font-mono text-[11px] text-mist hover:text-gold transition-colors"
              >
                {t}{i < POPULAR.length - 1 && <span className="ml-4 text-fog">·</span>}
              </Link>
            ))}
          </div>
        </div>
      </section>

      {/* ── Stats strip ───────────────────────────────────────── */}
      <section
        className="py-10"
        style={{ borderTop: '1px solid rgba(232,220,200,0.06)', borderBottom: '1px solid rgba(232,220,200,0.06)' }}
      >
        <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 grid grid-cols-2 sm:grid-cols-4 divide-x divide-[rgba(232,220,200,0.06)]">
          {STATS.map(s => (
            <div key={s.label} className="px-8 py-4 first:pl-0 last:pr-0">
              <div className="font-mono text-3xl font-medium text-gold mb-1">{s.value}</div>
              <div className="font-mono text-[11px] text-fog tracking-[0.15em] uppercase">{s.label}</div>
            </div>
          ))}
        </div>
      </section>

      {/* ── How it works ──────────────────────────────────────── */}
      <section className="py-28">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8">

          <div className="mb-16">
            <p className="font-mono text-[11px] text-gold tracking-[0.2em] uppercase mb-3">How it works</p>
            <h2 className="font-display text-4xl sm:text-5xl text-cream leading-tight max-w-lg">
              Built for serious<br /><span className="italic">applicants.</span>
            </h2>
          </div>

          <div className="grid sm:grid-cols-3 gap-px bg-[rgba(232,220,200,0.06)]">
            {STEPS.map(item => (
              <div
                key={item.num}
                className="bg-bg p-8 group"
              >
                <div
                  className="font-mono text-[80px] font-bold leading-none mb-6 select-none"
                  style={{ color: 'rgba(212,168,83,0.08)', letterSpacing: '-0.04em' }}
                >
                  {item.num}
                </div>
                <h3 className="font-display text-xl text-cream mb-3 leading-snug">{item.title}</h3>
                <p className="text-mist text-sm leading-relaxed">{item.body}</p>
                <div
                  className="mt-6 h-px w-8 transition-all duration-300 group-hover:w-16"
                  style={{ background: 'rgba(212,168,83,0.4)' }}
                />
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── Feature callout ───────────────────────────────────── */}
      <section
        className="py-20 relative overflow-hidden"
        style={{ borderTop: '1px solid rgba(232,220,200,0.06)' }}
      >
        <div className="absolute inset-0 bg-dot-grid opacity-40" />
        <div className="relative z-10 max-w-6xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="grid sm:grid-cols-2 gap-12 items-center">
            <div>
              <p className="font-mono text-[11px] text-gold tracking-[0.2em] uppercase mb-4">Precision search</p>
              <h2 className="font-display text-4xl sm:text-5xl text-cream leading-tight mb-6">
                Filter what<br /><span className="italic text-gradient-gold">matters.</span>
              </h2>
              <p className="text-mist leading-relaxed mb-8">
                Narrow by country, degree level, funding type, GPA threshold, language of instruction
                and research department. No more wading through irrelevant listings.
              </p>
              <Link
                href="/search"
                className="inline-flex items-center gap-3 font-mono text-sm text-gold hover:text-gold-bright transition-colors group"
              >
                Start searching
                <span className="transition-transform duration-200 group-hover:translate-x-1">→</span>
              </Link>
            </div>

            {/* Mock filter panel */}
            <div
              className="bg-surface p-6 space-y-4"
              style={{ border: '1px solid rgba(212,168,83,0.12)' }}
            >
              {[
                { label: 'Degree level', value: 'PhD' },
                { label: 'Country', value: 'Germany, Netherlands, UK' },
                { label: 'Funding', value: 'Fully funded' },
                { label: 'Field', value: 'Machine Learning, NLP' },
                { label: 'GPA minimum', value: '3.5 / 4.0' },
              ].map(r => (
                <div key={r.label} className="flex items-center justify-between py-2.5" style={{ borderBottom: '1px solid rgba(232,220,200,0.06)' }}>
                  <span className="font-mono text-[11px] text-fog tracking-widest uppercase">{r.label}</span>
                  <span className="font-mono text-xs text-gold">{r.value}</span>
                </div>
              ))}
              <div className="pt-2">
                <div className="w-full py-3 bg-gold text-bg text-xs font-bold tracking-widest text-center font-mono">
                  APPLY FILTERS
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ── CTA ───────────────────────────────────────────────── */}
      <section
        className="py-32 relative overflow-hidden text-center"
        style={{ borderTop: '1px solid rgba(232,220,200,0.06)' }}
      >
        <div className="absolute inset-0 bg-dot-grid opacity-30" />
        <div
          className="absolute inset-0"
          style={{
            background:
              'radial-gradient(ellipse 60% 50% at 50% 100%, rgba(212,168,83,0.07) 0%, transparent 70%)',
          }}
        />
        <div className="relative z-10 max-w-3xl mx-auto px-4">
          <p className="font-mono text-[11px] text-gold tracking-[0.2em] uppercase mb-6">Free to use</p>
          <h2 className="font-display text-5xl sm:text-6xl text-cream leading-[1.05] mb-6">
            Your next opportunity<br />
            <span className="italic text-gradient-gold">is already indexed.</span>
          </h2>
          <p className="text-mist text-lg mb-12 max-w-md mx-auto leading-relaxed">
            Thousands of funded positions across every field and continent. Search now — no account required.
          </p>
          <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
            <Link
              href="/search"
              className="px-10 py-4 bg-gold text-bg text-sm font-bold tracking-wide hover:bg-gold-bright transition-colors w-full sm:w-auto text-center"
            >
              Browse opportunities
            </Link>
            <Link
              href="/auth/register"
              className="px-10 py-4 text-cream text-sm font-medium tracking-wide hover:text-gold transition-colors w-full sm:w-auto text-center"
              style={{ border: '1px solid rgba(232,220,200,0.15)' }}
            >
              Create free account
            </Link>
          </div>
        </div>
      </section>
    </main>
  )
}