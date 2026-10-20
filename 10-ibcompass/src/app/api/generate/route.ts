import { NextRequest, NextResponse } from 'next/server'
import { generateRoadmap } from '@/lib/claude'
import { onboardingSchema } from '@/lib/schemas/onboarding'

export async function POST(req: NextRequest) {
  try {
    const body = await req.json()
    const parsed = onboardingSchema.safeParse(body)

    if (!parsed.success) {
      return NextResponse.json(
        { error: 'Invalid input', details: parsed.error.flatten() },
        { status: 400 }
      )
    }

    const roadmap = await generateRoadmap(parsed.data)
    return NextResponse.json(roadmap)
  } catch (err) {
    console.error('[/api/generate]', err)
    return NextResponse.json(
      { error: 'Failed to generate roadmap. Please try again.' },
      { status: 500 }
    )
  }
}
