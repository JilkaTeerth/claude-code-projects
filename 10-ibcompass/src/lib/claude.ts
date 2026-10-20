import Groq from 'groq-sdk'
import { IB_SUBJECTS } from './knowledge-base/subjects'
import { CAREER_REQUIREMENTS } from './knowledge-base/careers'
import { UNIVERSITY_REQUIREMENTS } from './knowledge-base/universities'
import { roadmapOutputSchema } from './schemas/roadmap'
import type { OnboardingInput, RoadmapOutput } from '@/types'

const groq = new Groq({ apiKey: process.env.GROQ_API_KEY })

function buildKnowledgeBase(): string {
  const subjects = IB_SUBJECTS.map(
    s => `${s.name} | Group ${s.group}: ${s.groupName} | HL: ${s.availableHL} | SL: ${s.availableSL}`
  ).join('\n')

  const careers = CAREER_REQUIREMENTS.map(
    c =>
      `${c.career} (${c.category})\n  Required HL: ${c.requiredHL.join(', ') || 'none'}\n  Recommended HL: ${c.recommendedHL.join(', ') || 'none'}\n  Notes: ${c.notes}`
  ).join('\n\n')

  const universities = UNIVERSITY_REQUIREMENTS.map(
    u =>
      `${u.university} | ${u.country} | Min points: ${u.minimumPoints} | Competitiveness: ${u.competitivenessScore}/10\n  Notes: ${u.notes}`
  ).join('\n\n')

  return `=== IB SUBJECT DATABASE ===\n${subjects}\n\n=== CAREER REQUIREMENTS DATABASE ===\n${careers}\n\n=== UNIVERSITY REQUIREMENTS DATABASE ===\n${universities}`
}

const SYSTEM_PROMPT = `You are IBCompass, an expert IB Diploma Programme academic advisor and university admissions consultant.

You help IB students make optimal subject choices based on their career goals and target universities. Give honest, data-driven advice.

RULES:
- Always recommend exactly 3 HL subjects and 3 SL subjects
- Subjects must come from different groups where possible (IB requires subjects from Groups 1-5, with Group 6 optional)
- Never recommend a subject as both HL and SL
- Base university pathway competitiveness on realistic IB averages, not optimistic projections
- Be specific about why each subject is recommended — reference the career and university requirements
- If workload tolerance is low (1-4), avoid recommending 3 demanding HLs together
- Timeline phases must be: "Grade 10 Preparation", "IB Year 1 (Grade 11)", "IB Year 2 (Grade 12)", "University Applications", "Post-IB"
- Only recommend standardized tests relevant to the target countries (UCAT/LNAT for UK, SAT/ACT for US, etc.)

${buildKnowledgeBase()}

You MUST respond with ONLY a valid JSON object. No markdown, no explanation, no code fences. Pure JSON only.`

export async function generateRoadmap(input: OnboardingInput): Promise<RoadmapOutput> {
  const userPrompt = `Generate an IB roadmap for this student:

Career interests: ${input.careers.join(', ')}
Target countries: ${input.countries.join(', ')}
Current grade level: ${input.gradeLevel}
Current grades: ${JSON.stringify(input.currentGrades)}
Subject strengths: ${input.strengths.join(', ') || 'not specified'}
Workload tolerance: ${input.workloadTolerance}/10
Learning preferences: ${input.learningStyles.join(', ') || 'not specified'}

Return ONLY a JSON object with this exact structure:
{
  "subjectRecommendations": {
    "hl": [{"subject": "string", "group": number, "level": "HL", "why": "string"}, ...],
    "sl": [{"subject": "string", "group": number, "level": "SL", "why": "string"}, ...],
    "alternates": [{"subject": "string", "group": number, "tradeoff": "string"}, ...]
  },
  "universityPathways": [{"university": "string", "country": "string", "requirements": "string", "competitiveness": number, "notes": "string"}, ...],
  "workloadAnalysis": {"difficulty": number, "hoursPerWeek": number, "hardestSubject": "string", "tips": ["string"]},
  "timeline": [{"phase": "string", "actions": ["string"]}, ...],
  "extracurriculars": ["string"],
  "standardizedTests": ["string"],
  "backupPathways": [{"scenario": "string", "adjustment": "string"}, ...],
  "summary": "string"
}`

  const response = await groq.chat.completions.create({
    model: 'llama-3.3-70b-versatile',
    messages: [
      { role: 'system', content: SYSTEM_PROMPT },
      { role: 'user', content: userPrompt },
    ],
    response_format: { type: 'json_object' },
    temperature: 0.3,
    max_tokens: 4096,
  })

  const raw = response.choices[0]?.message?.content?.trim()
  if (!raw) throw new Error('No response from Groq')

  let parsed: unknown
  try {
    parsed = JSON.parse(raw)
  } catch {
    throw new Error('Groq returned invalid JSON')
  }

  const validated = roadmapOutputSchema.safeParse(parsed)
  if (!validated.success) {
    const retryResponse = await groq.chat.completions.create({
      model: 'llama-3.3-70b-versatile',
      messages: [
        { role: 'system', content: SYSTEM_PROMPT },
        { role: 'user', content: userPrompt },
        { role: 'assistant', content: raw },
        { role: 'user', content: `Fix these validation errors and return corrected JSON only: ${validated.error.message}` },
      ],
      response_format: { type: 'json_object' },
      temperature: 0.1,
      max_tokens: 4096,
    })
    const retryRaw = retryResponse.choices[0]?.message?.content?.trim() ?? ''
    const retryParsed = JSON.parse(retryRaw)
    return roadmapOutputSchema.parse(retryParsed) as RoadmapOutput
  }

  return validated.data as RoadmapOutput
}
