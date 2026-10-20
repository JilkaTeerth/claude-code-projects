import { z } from 'zod'

export const onboardingSchema = z.object({
  careers: z.array(z.string()).min(1, 'Select at least one career interest'),
  countries: z.array(z.string()).min(1, 'Select at least one country'),
  gradeLevel: z.string().min(1, 'Select your current grade'),
  currentGrades: z.record(z.string(), z.string()).optional().default({}),
  strengths: z.array(z.string()).optional().default([]),
  workloadTolerance: z.number().min(1).max(10).default(5),
  learningStyles: z.array(z.string()).optional().default([]),
})

export type OnboardingFormData = z.infer<typeof onboardingSchema>
