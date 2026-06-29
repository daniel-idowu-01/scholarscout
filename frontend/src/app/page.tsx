import Link from 'next/link'

const POPULAR = ['PhD Computer Science', 'Funded Masters Europe', 'Postdoc Biology USA']

const STEPS = [
  {
    step: '01',
    title: 'We crawl universities daily',
    body: 'Our crawler continuously monitors 500+ top universities worldwide for new funding opportunities — scholarships, funded PhDs, fellowships and assistantships.',
  },
  {
    step: '02',
    title: 'AI extracts the details',
    body: 'Deadlines, stipend amounts, GPA requirements, eligibility criteria and department info are extracted and normalized automatically.',
  },
  {
    step: '03',
    title: 'You get matched instantly',
    body: 'Search by field, country, funding type or degree level. Save searches and get email alerts when new matching opportunities appear.',
  },
]

const STATS = [
  { value: '50,000+', label: 'Opportunities' },
  { value: '500+', label: 'Universities' },
  { value: '100+', label: 'Countries' },
  { value: 'Daily', label: 'Updates' },
]

export default function LandingPage() {
  return (
    <main>
      {/* Hero */}
      <section className="relative bg-gradient-to-br from-indigo-600 via-indigo-700 to-violet-800 text-white overflow-hidden">
        <div
          className="absolute inset-0 opacity-10"
          style={{
            backgroundImage: 'radial-gradient(circle, white 1px, transparent 1px)',
            backgroundSize: '36px 36px',
          }}
        />
        <div className="relative max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-24 text-center">
          <h1 className="text-4xl sm:text-5xl lg:text-6xl font-bold tracking-tight leading-tight">
            Find Your Perfect<br />Graduate Opportunity
          </h1>
          <p className="mt-6 text-xl text-indigo-200 max-w-2xl mx-auto leading-relaxed">
            Continuously updated scholarships, funded PhDs, fellowships and assistantships
            from top universities worldwide.
          </p>

          <form action="/search" method="get" className="mt-10 flex gap-2 max-w-2xl mx-auto">
            <input
              name="q"
              type="text"
              placeholder='Try "Fully funded AI PhD Germany"'
              className="flex-1 px-5 py-4 rounded-xl text-slate-900 text-sm focus:outline-none focus:ring-2 focus:ring-white shadow-lg"
            />
            <button
              type="submit"
              className="px-6 py-4 bg-white text-indigo-700 font-semibold rounded-xl hover:bg-indigo-50 transition-colors shadow-lg shrink-0"
            >
              Search
            </button>
          </form>

          <p className="mt-4 text-sm text-indigo-300">
            Popular:{' '}
            {POPULAR.map((t, i) => (
              <span key={t}>
                <Link
                  href={`/search?q=${encodeURIComponent(t)}`}
                  className="hover:text-white underline underline-offset-2 transition-colors"
                >
                  {t}
                </Link>
                {i < POPULAR.length - 1 && ' · '}
              </span>
            ))}
          </p>
        </div>
      </section>

      {/* Stats */}
      <section className="bg-white border-b border-slate-100">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12 grid grid-cols-2 sm:grid-cols-4 gap-8 text-center">
          {STATS.map(s => (
            <div key={s.label}>
              <div className="text-3xl font-bold text-indigo-600">{s.value}</div>
              <div className="mt-1 text-sm text-slate-500">{s.label}</div>
            </div>
          ))}
        </div>
      </section>

      {/* How it works */}
      <section className="py-20 bg-slate-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <h2 className="text-3xl font-bold text-slate-900 text-center">How ScholarScout works</h2>
          <div className="mt-12 grid sm:grid-cols-3 gap-6">
            {STEPS.map(item => (
              <div key={item.step} className="bg-white rounded-2xl p-8 border border-slate-200">
                <div className="text-5xl font-black text-slate-100 leading-none">{item.step}</div>
                <h3 className="mt-3 text-lg font-semibold text-slate-900">{item.title}</h3>
                <p className="mt-2 text-sm text-slate-600 leading-relaxed">{item.body}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="py-20 bg-indigo-600 text-white text-center">
        <div className="max-w-2xl mx-auto px-4">
          <h2 className="text-3xl font-bold">Start finding opportunities today</h2>
          <p className="mt-4 text-indigo-200">Free to use. No credit card required.</p>
          <div className="mt-8 flex gap-4 justify-center flex-wrap">
            <Link
              href="/search"
              className="px-8 py-3 bg-white text-indigo-700 font-semibold rounded-xl hover:bg-indigo-50 transition-colors"
            >
              Browse opportunities
            </Link>
            <Link
              href="/auth/register"
              className="px-8 py-3 border border-indigo-400 text-white font-semibold rounded-xl hover:bg-indigo-500 transition-colors"
            >
              Create account
            </Link>
          </div>
        </div>
      </section>
    </main>
  )
}