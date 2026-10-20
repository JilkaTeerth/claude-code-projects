'use client'

import type { TimelinePhase, BackupPathway } from '@/types'

export default function CareerTimeline({
  timeline,
  extracurriculars,
  standardizedTests,
  backupPathways,
}: {
  timeline: TimelinePhase[]
  extracurriculars: string[]
  standardizedTests: string[]
  backupPathways: BackupPathway[]
}) {
  return (
    <section className="space-y-6">
      <div>
        <h2 className="text-xl font-semibold text-white">Your Roadmap Timeline</h2>
        <p className="text-slate-400 text-sm mt-1">From now to your career — phase by phase.</p>
      </div>

      {/* Timeline */}
      <div className="space-y-0">
        {timeline.map((phase, i) => (
          <div key={i} className="flex gap-4">
            <div className="flex flex-col items-center">
              <div className={`w-8 h-8 rounded-full flex items-center justify-center text-xs font-bold shrink-0 ${
                i === 0 ? 'bg-violet-600 text-white' : 'bg-slate-800 border border-slate-700 text-slate-400'
              }`}>
                {i + 1}
              </div>
              {i < timeline.length - 1 && <div className="w-px flex-1 bg-slate-800 my-1" />}
            </div>
            <div className={`pb-6 ${i < timeline.length - 1 ? '' : ''}`}>
              <p className="text-white font-semibold text-sm mb-2">{phase.phase}</p>
              <ul className="space-y-1.5">
                {phase.actions.map((action, j) => (
                  <li key={j} className="text-slate-400 text-sm flex items-start gap-2">
                    <span className="text-slate-600 mt-0.5 shrink-0">·</span>
                    {action}
                  </li>
                ))}
              </ul>
            </div>
          </div>
        ))}
      </div>

      {/* Extracurriculars */}
      <div className="bg-slate-800/40 border border-slate-700/50 rounded-2xl p-5 space-y-3">
        <h3 className="text-sm font-semibold text-white">Recommended Extracurriculars</h3>
        <div className="flex flex-wrap gap-2">
          {extracurriculars.map((ec, i) => (
            <span key={i} className="px-3 py-1.5 bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 text-xs rounded-full">
              {ec}
            </span>
          ))}
        </div>
      </div>

      {/* Standardized Tests */}
      <div className="bg-slate-800/40 border border-slate-700/50 rounded-2xl p-5 space-y-3">
        <h3 className="text-sm font-semibold text-white">Standardized Tests to Consider</h3>
        <div className="flex flex-wrap gap-2">
          {standardizedTests.map((test, i) => (
            <span key={i} className="px-3 py-1.5 bg-blue-500/10 border border-blue-500/20 text-blue-400 text-xs rounded-full font-medium">
              {test}
            </span>
          ))}
        </div>
      </div>

      {/* Backup Pathways */}
      <div className="space-y-3">
        <h3 className="text-sm font-semibold text-white">Backup Pathways</h3>
        {backupPathways.map((bp, i) => (
          <div key={i} className="bg-slate-800/30 border border-slate-700/40 rounded-2xl p-4 space-y-1">
            <p className="text-slate-400 text-xs font-medium">{bp.scenario}</p>
            <p className="text-slate-300 text-sm">{bp.adjustment}</p>
          </div>
        ))}
      </div>
    </section>
  )
}
