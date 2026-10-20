'use client'

import { Slider } from '@/components/ui/slider'
import { Label } from '@/components/ui/label'

const LEARNING_STYLES = [
  'Visual learner',
  'Problem-based learning',
  'Discussion & debate',
  'Independent study',
  'Collaborative work',
  'Practical / hands-on',
  'Reading & writing',
  'Project-based',
]

interface PreferencesStepProps {
  workloadTolerance: number
  learningStyles: string[]
  onWorkloadChange: (val: number) => void
  onLearningStylesChange: (styles: string[]) => void
}

const WORKLOAD_LABELS: Record<number, { label: string; description: string; color: string }> = {
  1: { label: 'Minimal', description: 'I want to keep stress very low', color: 'text-emerald-400' },
  2: { label: 'Light', description: 'A manageable pace is important', color: 'text-emerald-400' },
  3: { label: 'Moderate-light', description: 'Some challenge but balanced life', color: 'text-blue-400' },
  4: { label: 'Moderate', description: 'I can handle regular work', color: 'text-blue-400' },
  5: { label: 'Balanced', description: 'Work hard, but maintain balance', color: 'text-blue-400' },
  6: { label: 'Moderately challenging', description: 'I\'m okay pushing myself', color: 'text-yellow-400' },
  7: { label: 'Challenging', description: 'Strong work ethic, can handle pressure', color: 'text-yellow-400' },
  8: { label: 'Very challenging', description: 'I thrive under academic pressure', color: 'text-orange-400' },
  9: { label: 'Intense', description: 'I want the most demanding path', color: 'text-red-400' },
  10: { label: 'Maximum', description: 'All-in, top programs at any cost', color: 'text-red-400' },
}

export default function PreferencesStep({
  workloadTolerance,
  learningStyles,
  onWorkloadChange,
  onLearningStylesChange,
}: PreferencesStepProps) {
  const wl = WORKLOAD_LABELS[workloadTolerance]

  function toggleStyle(s: string) {
    if (learningStyles.includes(s)) {
      onLearningStylesChange(learningStyles.filter(x => x !== s))
    } else {
      onLearningStylesChange([...learningStyles, s])
    }
  }

  return (
    <div className="space-y-8">
      <div>
        <h2 className="text-2xl font-semibold text-white mb-1">How do you work best?</h2>
        <p className="text-slate-400 text-sm">This helps us calibrate your subject combination to your real capacity — not an idealised version of you.</p>
      </div>

      <div className="space-y-6 bg-slate-800/30 rounded-2xl p-6 border border-slate-700/50">
        <Label className="text-slate-300 text-sm font-medium">Workload tolerance</Label>
        <Slider
          min={1}
          max={10}
          step={1}
          value={[workloadTolerance]}
          onValueChange={(v) => { const val = Array.isArray(v) ? v[0] : v; onWorkloadChange(val as number) }}
          className="py-2"
        />
        <div className="flex justify-between text-xs text-slate-600 -mt-2">
          <span>Low stress</span>
          <span>Maximum intensity</span>
        </div>
        <div className="bg-slate-700/30 rounded-xl px-5 py-4 border border-slate-600/30">
          <div className="flex items-center gap-3">
            <span className="text-3xl font-bold text-white">{workloadTolerance}</span>
            <div>
              <p className={`text-sm font-semibold ${wl.color}`}>{wl.label}</p>
              <p className="text-slate-400 text-xs">{wl.description}</p>
            </div>
          </div>
        </div>
      </div>

      <div className="space-y-3">
        <Label className="text-slate-300 text-sm font-medium">How do you learn best? (optional)</Label>
        <div className="flex flex-wrap gap-2">
          {LEARNING_STYLES.map(s => {
            const isSelected = learningStyles.includes(s)
            return (
              <button
                key={s}
                onClick={() => toggleStyle(s)}
                className={`px-3 py-2 rounded-lg border text-xs transition-all ${
                  isSelected
                    ? 'bg-violet-600/20 border-violet-500/40 text-violet-300'
                    : 'bg-slate-800/30 border-slate-700/50 text-slate-300 hover:border-slate-600'
                }`}
              >
                {s}
              </button>
            )
          })}
        </div>
      </div>

      <div className="bg-gradient-to-br from-violet-600/10 to-blue-600/10 border border-violet-500/20 rounded-2xl p-5">
        <p className="text-slate-300 text-sm leading-relaxed">
          <span className="text-violet-400 font-medium">Almost there.</span> Once you hit Generate, IBCompass will analyze your profile against our database of IB subject requirements, university prerequisites, and career pathways to build your personalised roadmap.
        </p>
      </div>
    </div>
  )
}
