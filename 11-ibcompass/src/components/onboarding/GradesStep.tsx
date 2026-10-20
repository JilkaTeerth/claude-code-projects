'use client'

import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Label } from '@/components/ui/label'

const GRADE_LEVELS = ['Grade 10', 'Grade 11', 'Grade 12', 'IB Year 1', 'IB Year 2']
const IB_SCORES = ['7', '6', '5', '4', '3', '2', '1', 'Not taking yet']

const COMMON_SUBJECTS = [
  'Mathematics',
  'English',
  'Sciences (Biology/Chemistry/Physics)',
  'Humanities (History/Geography/Economics)',
  'Languages',
  'Arts',
]

const STRENGTHS = [
  'Analytical thinking',
  'Essay writing',
  'Problem solving',
  'Memorisation',
  'Creative thinking',
  'Research',
  'Lab work',
  'Quantitative skills',
  'Verbal communication',
  'Independent learning',
]

interface GradesStepProps {
  gradeLevel: string
  currentGrades: Record<string, string>
  strengths: string[]
  onGradeLevelChange: (level: string) => void
  onGradesChange: (grades: Record<string, string>) => void
  onStrengthsChange: (strengths: string[]) => void
}

export default function GradesStep({
  gradeLevel,
  currentGrades,
  strengths,
  onGradeLevelChange,
  onGradesChange,
  onStrengthsChange,
}: GradesStepProps) {
  function toggleStrength(s: string) {
    if (strengths.includes(s)) {
      onStrengthsChange(strengths.filter(x => x !== s))
    } else if (strengths.length < 5) {
      onStrengthsChange([...strengths, s])
    }
  }

  return (
    <div className="space-y-8">
      <div>
        <h2 className="text-2xl font-semibold text-white mb-1">Where are you right now?</h2>
        <p className="text-slate-400 text-sm">Current grades help us set realistic expectations. Be honest — this helps you, not hurts you.</p>
      </div>

      <div className="space-y-3">
        <Label className="text-slate-300 text-sm font-medium">Current grade level</Label>
        <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
          {GRADE_LEVELS.map(level => (
            <button
              key={level}
              onClick={() => onGradeLevelChange(level)}
              className={`px-4 py-3 rounded-xl border text-sm transition-all ${
                gradeLevel === level
                  ? 'bg-emerald-600/20 border-emerald-500/50 text-emerald-300'
                  : 'bg-slate-800/30 border-slate-700/50 text-slate-300 hover:border-slate-600'
              }`}
            >
              {level}
            </button>
          ))}
        </div>
      </div>

      <div className="space-y-3">
        <Label className="text-slate-300 text-sm font-medium">Approximate current scores (optional)</Label>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          {COMMON_SUBJECTS.map(subject => (
            <div key={subject} className="flex items-center gap-3 bg-slate-800/30 rounded-xl px-4 py-3 border border-slate-700/50">
              <span className="text-slate-300 text-sm flex-1 truncate">{subject}</span>
              <Select
                value={currentGrades[subject] || ''}
                onValueChange={val => onGradesChange({ ...currentGrades, [subject]: val ?? '' })}
              >
                <SelectTrigger className="w-32 bg-slate-700/50 border-slate-600 text-white h-8 text-sm">
                  <SelectValue placeholder="Score" />
                </SelectTrigger>
                <SelectContent className="bg-slate-800 border-slate-700">
                  {IB_SCORES.map(score => (
                    <SelectItem key={score} value={score} className="text-slate-200 focus:bg-slate-700">
                      {score}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          ))}
        </div>
      </div>

      <div className="space-y-3">
        <Label className="text-slate-300 text-sm font-medium">Your academic strengths (up to 5)</Label>
        <div className="flex flex-wrap gap-2">
          {STRENGTHS.map(s => {
            const isSelected = strengths.includes(s)
            return (
              <button
                key={s}
                onClick={() => toggleStrength(s)}
                className={`px-3 py-2 rounded-lg border text-xs transition-all ${
                  isSelected
                    ? 'bg-emerald-600/20 border-emerald-500/40 text-emerald-300'
                    : strengths.length >= 5
                    ? 'opacity-40 cursor-not-allowed bg-slate-800/20 border-slate-700/30 text-slate-500'
                    : 'bg-slate-800/30 border-slate-700/50 text-slate-300 hover:border-slate-600'
                }`}
              >
                {s}
              </button>
            )
          })}
        </div>
      </div>
    </div>
  )
}
