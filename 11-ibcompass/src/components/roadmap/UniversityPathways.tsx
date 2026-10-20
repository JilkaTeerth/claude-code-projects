'use client'

import type { UniversityPathway } from '@/types'

const COUNTRY_FLAGS: Record<string, string> = {
  'UK': '🇬🇧', 'USA': '🇺🇸', 'Canada': '🇨🇦', 'Singapore': '🇸🇬',
  'Australia': '🇦🇺', 'Netherlands': '🇳🇱', 'Switzerland': '🇨🇭',
  'Germany': '🇩🇪', 'France': '🇫🇷', 'Japan': '🇯🇵',
}

function CompBar({ score }: { score: number }) {
  const color =
    score >= 9 ? 'bg-red-500' :
    score >= 7 ? 'bg-orange-500' :
    score >= 5 ? 'bg-yellow-500' : 'bg-emerald-500'
  const label =
    score >= 9 ? 'Extremely competitive' :
    score >= 7 ? 'Highly competitive' :
    score >= 5 ? 'Competitive' : 'Accessible'

  return (
    <div className="space-y-1.5">
      <div className="flex items-center justify-between">
        <span className="text-xs text-slate-500">{label}</span>
        <span className="text-xs font-bold text-slate-300">{score}/10</span>
      </div>
      <div className="h-1.5 bg-slate-700 rounded-full overflow-hidden">
        <div className={`h-full ${color} rounded-full transition-all`} style={{ width: `${score * 10}%` }} />
      </div>
    </div>
  )
}

export default function UniversityPathways({ pathways }: { pathways: UniversityPathway[] }) {
  return (
    <section className="space-y-4">
      <div>
        <h2 className="text-xl font-semibold text-white">University Pathways</h2>
        <p className="text-slate-400 text-sm mt-1">Relevant programs matched to your subject combination and target countries.</p>
      </div>

      <div className="space-y-3">
        {pathways.map((p, i) => (
          <div key={i} className="bg-slate-800/40 border border-slate-700/50 rounded-2xl p-5 space-y-4">
            <div className="flex items-start justify-between gap-3">
              <div>
                <div className="flex items-center gap-2">
                  <span className="text-lg">{COUNTRY_FLAGS[p.country] || '🌍'}</span>
                  <h3 className="text-white font-semibold">{p.university}</h3>
                </div>
                <p className="text-slate-500 text-xs mt-0.5">{p.country}</p>
              </div>
            </div>
            <CompBar score={p.competitiveness} />
            <div className="space-y-2">
              <div className="bg-slate-700/30 rounded-xl px-4 py-3">
                <p className="text-xs text-slate-500 mb-1 font-medium uppercase tracking-wider">Requirements</p>
                <p className="text-slate-300 text-sm">{p.requirements}</p>
              </div>
              {p.notes && (
                <p className="text-slate-500 text-xs leading-relaxed">{p.notes}</p>
              )}
            </div>
          </div>
        ))}
      </div>
    </section>
  )
}
