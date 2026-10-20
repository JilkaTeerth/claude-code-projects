export interface IBSubject {
  name: string
  group: number
  groupName: string
  availableHL: boolean
  availableSL: boolean
}

export interface CareerRequirement {
  career: string
  category: string
  requiredHL: string[]
  recommendedHL: string[]
  requiredSL: string[]
  notes: string
}

export interface UniversityRequirement {
  university: string
  country: string
  region: string
  requiresHL: string[]
  minimumPoints: number
  notes: string
  competitivenessScore: number // 1-10
}

export interface OnboardingInput {
  careers: string[]
  countries: string[]
  gradeLevel: string
  currentGrades: Record<string, string>
  strengths: string[]
  workloadTolerance: number // 1-10
  learningStyles: string[]
}

export interface SubjectRecommendation {
  subject: string
  group: number
  level: 'HL' | 'SL'
  why: string
}

export interface AlternateSubject {
  subject: string
  group: number
  tradeoff: string
}

export interface UniversityPathway {
  university: string
  country: string
  requirements: string
  competitiveness: number // 1-10
  notes: string
}

export interface TimelinePhase {
  phase: string
  actions: string[]
}

export interface BackupPathway {
  scenario: string
  adjustment: string
}

export interface WorkloadAnalysis {
  difficulty: number
  hoursPerWeek: number
  hardestSubject: string
  tips: string[]
}

export interface RoadmapOutput {
  subjectRecommendations: {
    hl: SubjectRecommendation[]
    sl: SubjectRecommendation[]
    alternates: AlternateSubject[]
  }
  universityPathways: UniversityPathway[]
  workloadAnalysis: WorkloadAnalysis
  timeline: TimelinePhase[]
  extracurriculars: string[]
  standardizedTests: string[]
  backupPathways: BackupPathway[]
  summary: string
}

export interface SavedRoadmap {
  id: string
  user_id: string
  input: OnboardingInput
  output: RoadmapOutput
  created_at: string
}
