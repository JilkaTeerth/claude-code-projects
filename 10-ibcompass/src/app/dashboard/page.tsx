import { redirect } from 'next/navigation'
import { createClient } from '@/lib/supabase/server'
import Link from 'next/link'
import { Button } from '@/components/ui/button'

export const metadata = { title: 'Dashboard — IBCompass' }

interface SavedRoadmap {
  id: string
  input: { careers: string[]; countries: string[]; gradeLevel: string }
  created_at: string
}

export default async function DashboardPage() {
  const supabase = await createClient()
  const { data: { user } } = await supabase.auth.getUser()

  if (!user) redirect('/login')

  const { data: roadmaps } = await supabase
    .from('roadmaps')
    .select('id, input, created_at')
    .eq('user_id', user.id)
    .order('created_at', { ascending: false })

  const { data: profile } = await supabase
    .from('profiles')
    .select('full_name')
    .eq('id', user.id)
    .single()

  return (
    <div className="min-h-screen bg-slate-950">
      <div className="border-b border-slate-800 bg-slate-900/50">
        <div className="max-w-3xl mx-auto px-4 py-5 flex items-center justify-between">
          <Link href="/" className="text-xl font-bold bg-gradient-to-r from-violet-400 to-blue-400 bg-clip-text text-transparent">
            IBCompass
          </Link>
          <div className="flex items-center gap-3">
            <span className="text-slate-400 text-sm">{profile?.full_name || user.email}</span>
            <form action="/api/auth/signout" method="post">
              <button className="text-slate-500 text-sm hover:text-slate-300 transition-colors">Sign out</button>
            </form>
          </div>
        </div>
      </div>

      <div className="max-w-3xl mx-auto px-4 py-10">
        <div className="flex items-center justify-between mb-8">
          <div>
            <h1 className="text-2xl font-bold text-white">Your Roadmaps</h1>
            <p className="text-slate-400 text-sm mt-1">
              {roadmaps?.length ? `${roadmaps.length} saved roadmap${roadmaps.length === 1 ? '' : 's'}` : 'No roadmaps yet'}
            </p>
          </div>
          <Link href="/onboard">
            <Button className="bg-violet-600 hover:bg-violet-700 text-white text-sm">
              + New Roadmap
            </Button>
          </Link>
        </div>

        {!roadmaps?.length ? (
          <div className="text-center py-20 bg-slate-900 border border-slate-800 rounded-3xl">
            <p className="text-slate-500 text-4xl mb-4">🧭</p>
            <p className="text-white font-semibold mb-2">No roadmaps yet</p>
            <p className="text-slate-400 text-sm mb-6">Build your first IB roadmap in under 5 minutes.</p>
            <Link href="/onboard">
              <Button className="bg-violet-600 hover:bg-violet-700 text-white">
                Build My Roadmap
              </Button>
            </Link>
          </div>
        ) : (
          <div className="space-y-3">
            {(roadmaps as SavedRoadmap[]).map(rm => (
              <Link key={rm.id} href={`/roadmap/${rm.id}`}>
                <div className="bg-slate-900 border border-slate-800 hover:border-slate-700 rounded-2xl p-5 transition-all cursor-pointer group">
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <div className="flex flex-wrap gap-1.5 mb-2">
                        {rm.input.careers?.map((c: string) => (
                          <span key={c} className="px-2 py-0.5 bg-violet-600/15 text-violet-400 text-xs rounded-full border border-violet-500/20">
                            {c}
                          </span>
                        ))}
                      </div>
                      <p className="text-slate-400 text-xs">
                        {rm.input.countries?.join(', ')} · {rm.input.gradeLevel}
                      </p>
                    </div>
                    <div className="text-right shrink-0">
                      <p className="text-slate-600 text-xs">
                        {new Date(rm.created_at).toLocaleDateString('en-GB', {
                          day: 'numeric', month: 'short', year: 'numeric',
                        })}
                      </p>
                      <p className="text-violet-400 text-xs mt-1 group-hover:underline">View →</p>
                    </div>
                  </div>
                </div>
              </Link>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
