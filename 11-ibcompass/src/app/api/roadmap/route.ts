import { NextRequest, NextResponse } from 'next/server'
import { createClient } from '@/lib/supabase/server'

export async function POST(req: NextRequest) {
  try {
    const supabase = await createClient()
    const { data: { user } } = await supabase.auth.getUser()

    if (!user) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
    }

    const { input, output } = await req.json()

    const { data, error } = await supabase
      .from('roadmaps')
      .insert({ user_id: user.id, input, output })
      .select('id')
      .single()

    if (error) throw error
    return NextResponse.json({ id: data.id })
  } catch (err) {
    console.error('[/api/roadmap POST]', err)
    return NextResponse.json({ error: 'Failed to save roadmap' }, { status: 500 })
  }
}

export async function GET() {
  try {
    const supabase = await createClient()
    const { data: { user } } = await supabase.auth.getUser()

    if (!user) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
    }

    const { data, error } = await supabase
      .from('roadmaps')
      .select('id, input, created_at')
      .eq('user_id', user.id)
      .order('created_at', { ascending: false })

    if (error) throw error
    return NextResponse.json(data)
  } catch (err) {
    console.error('[/api/roadmap GET]', err)
    return NextResponse.json({ error: 'Failed to fetch roadmaps' }, { status: 500 })
  }
}
