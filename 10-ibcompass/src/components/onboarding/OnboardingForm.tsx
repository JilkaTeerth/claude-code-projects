'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import CareerStep from './CareerStep'
import CountryStep from './CountryStep'
import GradesStep from './GradesStep'
import PreferencesStep from './PreferencesStep'
import { Button } from '@/components/ui/button'
import { Progress } from '@/components/ui/progress'
import type { RoadmapOutput } from '@/types'

interface FormState {
  careers: string[]
  countries: string[]
  gradeLevel: string
  currentGrades: Record<string, string>
  strengths: string[]
  workloadTolerance: number
  learningStyles: string[]
}

const STEPS = ['Career Goals', 'Target Countries', 'Current Grades', 'Preferences']

export default function OnboardingForm() {
  const router = useRouter()
  const [step, setStep] = useState(0)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const [form, setForm] = useState<FormState>({
    careers: [],
    countries: [],
    gradeLevel: '',
    currentGrades: {},
    strengths: [],
    workloadTolerance: 5,
    learningStyles: [],
  })

  function canContinue(): boolean {
    if (step === 0) return form.careers.length > 0
    if (step === 1) return form.countries.length > 0
    if (step === 2) return form.gradeLevel !== ''
    return true
  }

  async function handleGenerate() {
    setLoading(true)
    setError(null)
    try {
      const res = await fetch('/api/generate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(form),
      })

      if (!res.ok) {
        const data = await res.json()
        throw new Error(data.error || 'Generation failed')
      }

      const roadmap: RoadmapOutput = await res.json()

      // Store in sessionStorage so the results page can read it without a DB round-trip
      sessionStorage.setItem('pending_roadmap_input', JSON.stringify(form))
      sessionStorage.setItem('pending_roadmap_output', JSON.stringify(roadmap))

      router.push('/roadmap/preview')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Something went wrong. Please try again.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-slate-950 flex items-center justify-center px-4 py-12">
      <div className="w-full max-w-2xl">
        {/* Progress */}
        <div className="mb-8">
          <div className="flex items-center justify-between mb-3">
            {STEPS.map((s, i) => (
              <div key={s} className="flex items-center gap-2">
                <div
                  className={`w-7 h-7 rounded-full flex items-center justify-center text-xs font-bold transition-all ${
                    i < step
                      ? 'bg-violet-600 text-white'
                      : i === step
                      ? 'bg-violet-600/30 border border-violet-500/60 text-violet-300'
                      : 'bg-slate-800 text-slate-600'
                  }`}
                >
                  {i < step ? '✓' : i + 1}
                </div>
                <span className={`text-xs hidden sm:block ${i === step ? 'text-slate-300' : 'text-slate-600'}`}>{s}</span>
                {i < STEPS.length - 1 && <div className={`flex-1 h-px mx-2 ${i < step ? 'bg-violet-600/50' : 'bg-slate-800'}`} />}
              </div>
            ))}
          </div>
          <Progress value={((step + 1) / STEPS.length) * 100} className="h-1 bg-slate-800" />
        </div>

        {/* Card */}
        <div className="bg-slate-900 border border-slate-800 rounded-3xl p-8 shadow-2xl">
          {step === 0 && (
            <CareerStep selected={form.careers} onChange={careers => setForm(f => ({ ...f, careers }))} />
          )}
          {step === 1 && (
            <CountryStep selected={form.countries} onChange={countries => setForm(f => ({ ...f, countries }))} />
          )}
          {step === 2 && (
            <GradesStep
              gradeLevel={form.gradeLevel}
              currentGrades={form.currentGrades}
              strengths={form.strengths}
              onGradeLevelChange={gradeLevel => setForm(f => ({ ...f, gradeLevel }))}
              onGradesChange={currentGrades => setForm(f => ({ ...f, currentGrades }))}
              onStrengthsChange={strengths => setForm(f => ({ ...f, strengths }))}
            />
          )}
          {step === 3 && (
            <PreferencesStep
              workloadTolerance={form.workloadTolerance}
              learningStyles={form.learningStyles}
              onWorkloadChange={workloadTolerance => setForm(f => ({ ...f, workloadTolerance }))}
              onLearningStylesChange={learningStyles => setForm(f => ({ ...f, learningStyles }))}
            />
          )}

          {error && (
            <div className="mt-4 bg-red-900/20 border border-red-500/30 rounded-xl px-4 py-3 text-red-400 text-sm">
              {error}
            </div>
          )}

          <div className="flex gap-3 mt-8">
            {step > 0 && (
              <Button
                variant="outline"
                onClick={() => setStep(s => s - 1)}
                disabled={loading}
                className="border-slate-700 text-slate-300 hover:bg-slate-800 hover:text-white"
              >
                Back
              </Button>
            )}
            {step < STEPS.length - 1 ? (
              <Button
                onClick={() => setStep(s => s + 1)}
                disabled={!canContinue()}
                className="flex-1 bg-violet-600 hover:bg-violet-700 text-white"
              >
                Continue →
              </Button>
            ) : (
              <Button
                onClick={handleGenerate}
                disabled={loading}
                className="flex-1 bg-gradient-to-r from-violet-600 to-blue-600 hover:from-violet-700 hover:to-blue-700 text-white font-semibold"
              >
                {loading ? (
                  <span className="flex items-center gap-2">
                    <span className="inline-block w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                    Building your roadmap…
                  </span>
                ) : (
                  'Generate My Roadmap →'
                )}
              </Button>
            )}
          </div>
        </div>

        {/* Loading overlay */}
        {loading && (
          <div className="fixed inset-0 bg-slate-950/80 backdrop-blur-sm flex items-center justify-center z-50">
            <div className="bg-slate-900 border border-slate-700 rounded-3xl p-10 text-center max-w-sm mx-4">
              <div className="w-14 h-14 border-4 border-violet-500/30 border-t-violet-500 rounded-full animate-spin mx-auto mb-6" />
              <h3 className="text-white font-semibold text-lg mb-2">Analysing your profile…</h3>
              <p className="text-slate-400 text-sm">Matching careers → subjects → universities. This takes about 10 seconds.</p>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
