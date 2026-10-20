'use client'

import { Badge } from '@/components/ui/badge'
import { Card } from '@/components/ui/card'
import type { SubjectRecommendation, AlternateSubject } from '@/types'

const GROUP_COLORS: Record<number, string> = {
  1: 'bg-blue-500/10 text-blue-400 border-blue-500/20',
  2: 'bg-teal-500/10 text-teal-400 border-teal-500/20',
  3: 'bg-amber-500/10 text-amber-400 border-amber-500/20',
  4: 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20',
  5: 'bg-violet-500/10 text-violet-400 border-violet-500/20',
  6: 'bg-pink-500/10 text-pink-400 border-pink-500/20',
}

const GROUP_NAMES: Record<number, string> = {
  1: 'Language & Lit',
  2: 'Language Acq.',
  3: 'Individuals & Societies',
  4: 'Sciences',
  5: 'Mathematics',
  6: 'The Arts',
}

function SubjectCard({ rec }: { rec: SubjectRecommendation }) {
  return (
    <Card className="bg-slate-800/40 border-slate-700/50 p-5 rounded-2xl space-y-3">
      <div className="flex items-start justify-between gap-2">
        <div>
          <p className="text-white font-semibold leading-tight">{rec.subject}</p>
          <p className="text-slate-500 text-xs mt-0.5">{GROUP_NAMES[rec.group]}</p>
        </div>
        <div className="flex gap-2 shrink-0">
          <Badge className={`${GROUP_COLORS[rec.group]} border text-xs`}>Group {rec.group}</Badge>
          <Badge className={`${rec.level === 'HL' ? 'bg-violet-600/20 text-violet-300 border-violet-500/30' : 'bg-slate-700/50 text-slate-400 border-slate-600/50'} border text-xs font-bold`}>
            {rec.level}
          </Badge>
        </div>
      </div>
      <p className="text-slate-400 text-sm leading-relaxed">{rec.why}</p>
    </Card>
  )
}

interface Props {
  hl: SubjectRecommendation[]
  sl: SubjectRecommendation[]
  alternates: AlternateSubject[]
}

export default function SubjectRecommendations({ hl, sl, alternates }: Props) {
  return (
    <section className="space-y-6">
      <div>
        <h2 className="text-xl font-semibold text-white">Recommended Subject Combination</h2>
        <p className="text-slate-400 text-sm mt-1">Based on your career goals, target universities, and workload preference.</p>
      </div>

      <div>
        <div className="flex items-center gap-2 mb-3">
          <span className="text-xs font-bold text-violet-400 uppercase tracking-wider">Higher Level (HL)</span>
          <div className="flex-1 h-px bg-violet-500/20" />
          <span className="text-xs text-slate-600">3 subjects</span>
        </div>
        <div className="grid gap-3 sm:grid-cols-1">
          {hl.map((rec, i) => <SubjectCard key={i} rec={rec} />)}
        </div>
      </div>

      <div>
        <div className="flex items-center gap-2 mb-3">
          <span className="text-xs font-bold text-slate-400 uppercase tracking-wider">Standard Level (SL)</span>
          <div className="flex-1 h-px bg-slate-700" />
          <span className="text-xs text-slate-600">3 subjects</span>
        </div>
        <div className="grid gap-3 sm:grid-cols-1">
          {sl.map((rec, i) => <SubjectCard key={i} rec={rec} />)}
        </div>
      </div>

      {alternates.length > 0 && (
        <div className="bg-slate-800/20 border border-slate-700/30 rounded-2xl p-5 space-y-3">
          <h3 className="text-sm font-semibold text-slate-300">Alternate Options</h3>
          {alternates.map((alt, i) => (
            <div key={i} className="flex items-start gap-3">
              <Badge className={`${GROUP_COLORS[alt.group]} border text-xs shrink-0`}>Group {alt.group}</Badge>
              <div>
                <p className="text-slate-300 text-sm font-medium">{alt.subject}</p>
                <p className="text-slate-500 text-xs mt-0.5">{alt.tradeoff}</p>
              </div>
            </div>
          ))}
        </div>
      )}
    </section>
  )
}
