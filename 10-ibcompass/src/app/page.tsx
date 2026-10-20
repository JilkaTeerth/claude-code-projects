import Link from 'next/link'
import { Button } from '@/components/ui/button'

export default function HomePage() {
  return (
    <div className="min-h-screen bg-slate-950 text-white">
      {/* Nav */}
      <nav className="border-b border-slate-800/50 bg-slate-950/80 backdrop-blur-sm sticky top-0 z-10">
        <div className="max-w-6xl mx-auto px-4 py-4 flex items-center justify-between">
          <span className="text-xl font-bold bg-gradient-to-r from-violet-400 to-blue-400 bg-clip-text text-transparent">
            IBCompass
          </span>
          <div className="flex items-center gap-3">
            <Link href="/login" className="text-slate-400 text-sm hover:text-white transition-colors">
              Sign in
            </Link>
            <Link href="/onboard">
              <Button className="bg-violet-600 hover:bg-violet-700 text-white text-sm h-9">
                Get Started
              </Button>
            </Link>
          </div>
        </div>
      </nav>

      {/* Hero */}
      <section className="relative overflow-hidden">
        <div className="absolute inset-0 bg-gradient-to-br from-violet-600/10 via-transparent to-blue-600/5 pointer-events-none" />
        <div className="absolute top-20 left-1/2 -translate-x-1/2 w-[600px] h-[600px] bg-violet-600/5 rounded-full blur-3xl pointer-events-none" />

        <div className="relative max-w-4xl mx-auto px-4 pt-24 pb-20 text-center">
          <div className="inline-flex items-center gap-2 bg-violet-600/10 border border-violet-500/20 rounded-full px-4 py-1.5 text-violet-400 text-xs font-medium mb-8">
            <span className="w-1.5 h-1.5 bg-violet-400 rounded-full animate-pulse" />
            AI-powered IB academic advisor
          </div>

          <h1 className="text-5xl sm:text-6xl font-bold leading-[1.1] mb-6">
            Choose your IB subjects
            <br />
            <span className="bg-gradient-to-r from-violet-400 via-blue-400 to-cyan-400 bg-clip-text text-transparent">
              with total clarity.
            </span>
          </h1>

          <p className="text-slate-400 text-lg sm:text-xl max-w-2xl mx-auto mb-10 leading-relaxed">
            Most IB students pick subjects with incomplete information. IBCompass maps your career goal → required subjects → university prerequisites → real outcomes — in one personalised roadmap.
          </p>

          <div className="flex flex-col sm:flex-row gap-3 justify-center">
            <Link href="/onboard">
              <Button className="bg-gradient-to-r from-violet-600 to-blue-600 hover:from-violet-700 hover:to-blue-700 text-white h-12 px-8 text-base font-semibold">
                Build My Roadmap — Free
              </Button>
            </Link>
            <Link href="/login">
              <Button variant="outline" className="border-slate-700 text-slate-300 hover:bg-slate-800 hover:text-white h-12 px-8 text-base">
                Sign In
              </Button>
            </Link>
          </div>

          <p className="text-slate-600 text-xs mt-4">No account required to generate. Takes 5 minutes.</p>
        </div>
      </section>

      {/* Problem statement */}
      <section className="max-w-4xl mx-auto px-4 py-16">
        <div className="bg-slate-900 border border-slate-800 rounded-3xl p-8 sm:p-10">
          <h2 className="text-2xl font-bold text-white mb-6">The IB subject choice problem is real.</h2>
          <div className="grid sm:grid-cols-2 gap-4">
            {[
              ['Which HLs are required?', 'Most students don\'t know that Medicine requires Biology + Chemistry HL, or that LSE expects Maths AA HL specifically.'],
              ['How do requirements differ by country?', 'UK, US, Canada, Singapore — each has completely different prerequisites and grade expectations.'],
              ['What are my realistic chances?', 'Not just "you need 38 points" — which subjects, what grades, and what supporting activities actually matter.'],
              ['What if my grades drop?', 'How does a backup plan work? What do you do if Maths AA HL is too hard and you need to switch?'],
            ].map(([q, a]) => (
              <div key={q} className="bg-slate-800/50 rounded-2xl p-5 border border-slate-700/50">
                <p className="text-white font-semibold text-sm mb-2">{q}</p>
                <p className="text-slate-400 text-sm leading-relaxed">{a}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* How it works */}
      <section className="max-w-4xl mx-auto px-4 py-8 pb-20">
        <h2 className="text-2xl font-bold text-white text-center mb-10">How it works</h2>
        <div className="grid sm:grid-cols-3 gap-4">
          {[
            ['01', 'Tell us your goal', 'Career interests, target countries, current grades, and how hard you want to push.', 'violet'],
            ['02', 'AI analyses everything', 'Cross-references your profile against IB requirements, university prerequisites, and career pathways.', 'blue'],
            ['03', 'Get your full roadmap', 'Subject combo, university targets, workload forecast, timeline, ECs, tests — all personalised.', 'cyan'],
          ].map(([num, title, desc]) => (
            <div key={num} className="bg-slate-900 border border-slate-800 rounded-2xl p-6 space-y-3">
              <span className="text-4xl font-bold text-violet-500/30">{num}</span>
              <h3 className="text-white font-semibold">{title}</h3>
              <p className="text-slate-400 text-sm leading-relaxed">{desc}</p>
            </div>
          ))}
        </div>
      </section>

      {/* CTA */}
      <section className="border-t border-slate-800 bg-gradient-to-br from-violet-600/5 to-slate-950">
        <div className="max-w-2xl mx-auto px-4 py-20 text-center">
          <h2 className="text-3xl font-bold text-white mb-4">Stop guessing. Start planning.</h2>
          <p className="text-slate-400 mb-8">Takes 5 minutes. No account needed to get your roadmap.</p>
          <Link href="/onboard">
            <Button className="bg-gradient-to-r from-violet-600 to-blue-600 hover:from-violet-700 hover:to-blue-700 text-white h-12 px-10 text-base font-semibold">
              Build My Roadmap →
            </Button>
          </Link>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-slate-800 py-6">
        <div className="max-w-6xl mx-auto px-4 flex items-center justify-between text-slate-600 text-xs">
          <span>IBCompass</span>
          <span>Built for IB students, by someone who was one.</span>
        </div>
      </footer>
    </div>
  )
}
