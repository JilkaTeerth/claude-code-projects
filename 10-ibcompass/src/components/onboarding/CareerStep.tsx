'use client'

import { Badge } from '@/components/ui/badge'
import { Input } from '@/components/ui/input'
import { CAREER_CATEGORIES, CAREER_NAMES, CAREER_REQUIREMENTS } from '@/lib/knowledge-base/careers'
import { useState } from 'react'

interface CareerStepProps {
  selected: string[]
  onChange: (careers: string[]) => void
}

const CATEGORY_COLORS: Record<string, string> = {
  'Health & Science': 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20',
  'Business & Finance': 'bg-blue-500/10 text-blue-400 border-blue-500/20',
  'Technology': 'bg-violet-500/10 text-violet-400 border-violet-500/20',
  'Law & Humanities': 'bg-amber-500/10 text-amber-400 border-amber-500/20',
  'Design & Engineering': 'bg-orange-500/10 text-orange-400 border-orange-500/20',
  'Arts & Design': 'bg-pink-500/10 text-pink-400 border-pink-500/20',
}

export default function CareerStep({ selected, onChange }: CareerStepProps) {
  const [search, setSearch] = useState('')
  const [activeCategory, setActiveCategory] = useState<string | null>(null)

  const filtered = CAREER_NAMES.filter(c => {
    const matchesSearch = c.toLowerCase().includes(search.toLowerCase())
    const matchesCategory = !activeCategory ||
      CAREER_REQUIREMENTS.find(r => r.career === c)?.category === activeCategory
    return matchesSearch && matchesCategory
  })

  function toggle(career: string) {
    if (selected.includes(career)) {
      onChange(selected.filter(c => c !== career))
    } else if (selected.length < 4) {
      onChange([...selected, career])
    }
  }

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-semibold text-white mb-1">What do you want to become?</h2>
        <p className="text-slate-400 text-sm">Select up to 4 career interests. Be honest — we'll find the best subject path.</p>
      </div>

      <Input
        placeholder="Search careers..."
        value={search}
        onChange={e => setSearch(e.target.value)}
        className="bg-slate-800/50 border-slate-700 text-white placeholder:text-slate-500"
      />

      <div className="flex flex-wrap gap-2">
        {CAREER_CATEGORIES.map(cat => (
          <button
            key={cat}
            onClick={() => setActiveCategory(activeCategory === cat ? null : cat)}
            className={`px-3 py-1 rounded-full text-xs font-medium border transition-all ${
              activeCategory === cat
                ? CATEGORY_COLORS[cat]
                : 'bg-slate-800/50 text-slate-400 border-slate-700 hover:border-slate-600'
            }`}
          >
            {cat}
          </button>
        ))}
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 max-h-72 overflow-y-auto pr-1">
        {filtered.map(career => {
          const isSelected = selected.includes(career)
          const isDisabled = !isSelected && selected.length >= 4
          return (
            <button
              key={career}
              onClick={() => toggle(career)}
              disabled={isDisabled}
              className={`text-left px-4 py-3 rounded-xl border text-sm transition-all ${
                isSelected
                  ? 'bg-violet-600/20 border-violet-500/50 text-violet-300'
                  : isDisabled
                  ? 'opacity-30 cursor-not-allowed bg-slate-800/20 border-slate-700/50 text-slate-500'
                  : 'bg-slate-800/30 border-slate-700/50 text-slate-300 hover:border-slate-600 hover:bg-slate-800/50'
              }`}
            >
              {career}
            </button>
          )
        })}
      </div>

      {selected.length > 0 && (
        <div className="flex flex-wrap gap-2 pt-2 border-t border-slate-800">
          <span className="text-slate-500 text-xs self-center">Selected:</span>
          {selected.map(c => (
            <Badge key={c} variant="secondary" className="bg-violet-600/20 text-violet-300 border-violet-500/30 cursor-pointer" onClick={() => toggle(c)}>
              {c} ×
            </Badge>
          ))}
        </div>
      )}
    </div>
  )
}
