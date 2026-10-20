import { z } from 'zod'

const subjectRecommendationSchema = z.object({
  subject: z.string(),
  group: z.number().int().min(1).max(6),
  level: z.enum(['HL', 'SL']),
  why: z.string(),
})

const alternateSubjectSchema = z.object({
  subject: z.string(),
  group: z.number().int().min(1).max(6),
  tradeoff: z.string(),
})

const universityPathwaySchema = z.object({
  university: z.string(),
  country: z.string(),
  requirements: z.string(),
  competitiveness: z.number().int().min(1).max(10),
  notes: z.string(),
})

const workloadAnalysisSchema = z.object({
  difficulty: z.number().int().min(1).max(10),
  hoursPerWeek: z.number().int().min(10).max(60),
  hardestSubject: z.string(),
  tips: z.array(z.string()),
})

const timelinePhaseSchema = z.object({
  phase: z.string(),
  actions: z.array(z.string()),
})

const backupPathwaySchema = z.object({
  scenario: z.string(),
  adjustment: z.string(),
})

export const roadmapOutputSchema = z.object({
  subjectRecommendations: z.object({
    hl: z.array(subjectRecommendationSchema).length(3),
    sl: z.array(subjectRecommendationSchema).length(3),
    alternates: z.array(alternateSubjectSchema).max(3),
  }),
  universityPathways: z.array(universityPathwaySchema).min(3).max(8),
  workloadAnalysis: workloadAnalysisSchema,
  timeline: z.array(timelinePhaseSchema).min(3),
  extracurriculars: z.array(z.string()).min(3).max(8),
  standardizedTests: z.array(z.string()).min(1).max(6),
  backupPathways: z.array(backupPathwaySchema).min(2).max(4),
  summary: z.string().min(50).max(400),
})

export type RoadmapOutputSchema = z.infer<typeof roadmapOutputSchema>
