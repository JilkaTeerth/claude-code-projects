'use client'

import type { WorkloadAnalysis as WA } from '@/types'

export default function WorkloadAnalysis({ analysis }: { analysis: WA }) {
  const diffColor =
    analysis.difficulty >= 8 ? 'text-red-400' :
    analysis.difficulty >= 6 ? 'text-orange-400' :
    analysis.difficulty >= 4 ? 'text-yellow-400' : 'text-emerald-400'

  const diffLabel =
    analysis.difficulty >= 8 ? 'Very Demanding' :
    analysis.difficulty >= 6 ? 'Challenging' :
    analysis.difficulty >= 4 ? 'Moderate' : 'Manageable'

  return (
    <section className="space-y-4">
      <div>
        <h2 className="text-xl font-semibold text-white">Workload Analysis</h2>
        <p className="text-slate-400 text-sm mt-1">What to realistically expect from this combination.</p>
      </div>

      <div className="grid grid-cols-2 gap-3">
        <div className="bg-slate-800/40 border border-slate-700/50 rounded-2xl p-5 text-center">
          <p className={`text-4xl font-bold ${diffColor}`}>{analysis.difficulty}<span className="text-xl text-slate-500">/10</span></p>
          <p className="text-slate-400 text-xs mt-1">Difficulty</p>
          <p className={`text-xs font-medium mt-1 ${diffColor}`}>{diffLabel}</p>
        </div>
        <div className="bg-slate-800/40 border border-slate-700/50 rounded-2xl p-5 text-center">
          <p className="text-4xl font-bold text-blue-400">{analysis.hoursPerWeek}<span className="text-xl text-slate-500">h</span></p>
          <p className="text-slate-400 text-xs mt-1">Per week</p>
          <p className="text-xs font-medium mt-1 text-blue-400">Study estimate</p>
        </div>
      </div>

      <div className="bg-slate-800/40 border border-slate-700/50 rounded-2xl p-5 space-y-2">
        <p className="text-xs text-slate-500 font-medium uppercase tracking-wider">Most demanding subject</p>
        <p className="text-white font-semibold">{analysis.hardestSubject}</p>
      </div>

      {analysis.tips.length > 0 && (
        <div className="bg-slate-800/40 border border-slate-700/50 rounded-2xl p-5 space-y-3">
          <p className="text-xs text-slate-500 font-medium uppercase tracking-wider">Survival tips</p>
          <ul className="space-y-2">
            {analysis.tips.map((tip, i) => (
              <li key={i} className="flex items-start gap-2 text-slate-300 text-sm">
                <span className="text-violet-400 mt-0.5 shrink-0">→</span>
                <span>{tip}</span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </section>
  )
}
