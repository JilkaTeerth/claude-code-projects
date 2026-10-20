'use client'

import { useEffect, useState } from 'react'
import { useParams, useRouter } from 'next/navigation'
import SubjectRecommendations from '@/components/roadmap/SubjectRecommendations'
import UniversityPathways from '@/components/roadmap/UniversityPathways'
import WorkloadAnalysis from '@/components/roadmap/WorkloadAnalysis'
import CareerTimeline from '@/components/roadmap/CareerTimeline'
import { Button } from '@/components/ui/button'
import { createClient } from '@/lib/supabase/client'
import type { RoadmapOutput, OnboardingInput } from '@/types'

export default function RoadmapPage() {
  const { id } = useParams()
  const router = useRouter()
  const [roadmap, setRoadmap] = useState<RoadmapOutput | null>(null)
  const [input, setInput] = useState<OnboardingInput | null>(null)
  const [saving, setSaving] = useState(false)
  const [saved, setSaved] = useState(false)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (id === 'preview') {
      // Fresh generation — read from sessionStorage
      const rawInput = sessionStorage.getItem('pending_roadmap_input')
      const rawOutput = sessionStorage.getItem('pending_roadmap_output')
      if (rawInput && rawOutput) {
        setInput(JSON.parse(rawInput))
        setRoadmap(JSON.parse(rawOutput))
      } else {
        router.replace('/onboard')
      }
      setLoading(false)
    } else {
      // Saved roadmap — fetch from DB
      async function load() {
        const supabase = createClient()
        const { data, error } = await supabase
          .from('roadmaps')
          .select('input, output')
          .eq('id', id)
          .single()

        if (error || !data) {
          router.replace('/dashboard')
          return
        }
        setInput(data.input as OnboardingInput)
        setRoadmap(data.output as RoadmapOutput)
        setSaved(true)
        setLoading(false)
      }
      load()
    }
  }, [id, router])

  async function handleSave() {
    setSaving(true)
    try {
      const res = await fetch('/api/roadmap', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ input, output: roadmap }),
      })
      if (res.status === 401) {
        // Not logged in — redirect to signup with return URL
        router.push('/signup?next=/roadmap/preview')
        return
      }
      if (res.ok) {
        const { id: newId } = await res.json()
        sessionStorage.removeItem('pending_roadmap_input')
        sessionStorage.removeItem('pending_roadmap_output')
        router.replace(`/roadmap/${newId}`)
        setSaved(true)
      }
    } finally {
      setSaving(false)
    }
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-slate-950 flex items-center justify-center">
        <div className="w-10 h-10 border-4 border-violet-500/30 border-t-violet-500 rounded-full animate-spin" />
      </div>
    )
  }

  if (!roadmap || !input) return null

  return (
    <div className="min-h-screen bg-slate-950">
      {/* Header */}
      <div className="bg-gradient-to-br from-violet-600/10 via-slate-900 to-blue-600/5 border-b border-slate-800">
        <div className="max-w-3xl mx-auto px-4 py-10">
          <div className="flex items-start justify-between gap-4 flex-wrap">
            <div>
              <div className="flex flex-wrap gap-2 mb-3">
                {input.careers.map(c => (
                  <span key={c} className="px-3 py-1 bg-violet-600/20 text-violet-300 text-xs rounded-full border border-violet-500/30 font-medium">
                    {c}
                  </span>
                ))}
              </div>
              <h1 className="text-3xl font-bold text-white mb-2">Your IB Roadmap</h1>
              <p className="text-slate-400 text-sm max-w-xl leading-relaxed">{roadmap.summary}</p>
            </div>
            <div className="flex gap-2 shrink-0">
              {!saved && (
                <Button
                  onClick={handleSave}
                  disabled={saving}
                  className="bg-violet-600 hover:bg-violet-700 text-white text-sm"
                >
                  {saving ? 'Saving…' : 'Save Roadmap'}
                </Button>
              )}
              <Button
                variant="outline"
                onClick={() => router.push('/onboard')}
                className="border-slate-700 text-slate-300 hover:bg-slate-800 text-sm"
              >
                New Roadmap
              </Button>
            </div>
          </div>
        </div>
      </div>

      {/* Content */}
      <div className="max-w-3xl mx-auto px-4 py-10 space-y-12">
        <SubjectRecommendations
          hl={roadmap.subjectRecommendations.hl}
          sl={roadmap.subjectRecommendations.sl}
          alternates={roadmap.subjectRecommendations.alternates}
        />
        <UniversityPathways pathways={roadmap.universityPathways} />
        <WorkloadAnalysis analysis={roadmap.workloadAnalysis} />
        <CareerTimeline
          timeline={roadmap.timeline}
          extracurriculars={roadmap.extracurriculars}
          standardizedTests={roadmap.standardizedTests}
          backupPathways={roadmap.backupPathways}
        />
      </div>
    </div>
  )
}
