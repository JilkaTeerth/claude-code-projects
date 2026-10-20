'use client'

import { COUNTRIES } from '@/lib/knowledge-base/universities'

const COUNTRY_FLAGS: Record<string, string> = {
  'UK': '🇬🇧',
  'USA': '🇺🇸',
  'Canada': '🇨🇦',
  'Singapore': '🇸🇬',
  'Australia': '🇦🇺',
  'Netherlands': '🇳🇱',
  'Switzerland': '🇨🇭',
  'Germany': '🇩🇪',
  'France': '🇫🇷',
  'Japan': '🇯🇵',
}

interface CountryStepProps {
  selected: string[]
  onChange: (countries: string[]) => void
}

export default function CountryStep({ selected, onChange }: CountryStepProps) {
  function toggle(country: string) {
    if (selected.includes(country)) {
      onChange(selected.filter(c => c !== country))
    } else {
      onChange([...selected, country])
    }
  }

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-semibold text-white mb-1">Where do you want to study?</h2>
        <p className="text-slate-400 text-sm">Select all countries you're considering. We'll tailor university requirements accordingly.</p>
      </div>

      <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
        {COUNTRIES.map(country => {
          const isSelected = selected.includes(country)
          return (
            <button
              key={country}
              onClick={() => toggle(country)}
              className={`flex items-center gap-3 px-4 py-4 rounded-xl border text-sm transition-all ${
                isSelected
                  ? 'bg-blue-600/20 border-blue-500/50 text-blue-300'
                  : 'bg-slate-800/30 border-slate-700/50 text-slate-300 hover:border-slate-600 hover:bg-slate-800/50'
              }`}
            >
              <span className="text-xl">{COUNTRY_FLAGS[country] || '🌍'}</span>
              <span className="font-medium">{country}</span>
            </button>
          )
        })}
      </div>

      {selected.length > 0 && (
        <p className="text-slate-500 text-xs">
          {selected.length} {selected.length === 1 ? 'country' : 'countries'} selected
        </p>
      )}
    </div>
  )
}
