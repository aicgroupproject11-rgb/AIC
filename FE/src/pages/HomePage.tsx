import { useEffect, useState } from 'react'

import type { ChangeEvent } from 'react'

type Behavior = {
  student: string
  action: string
  object: string
  time: string
  confidence: string
}

const demoBehaviors: Behavior[] = [
  {
    student: 'Student 01',
    action: 'Writing',
    object: 'Notebook',
    time: '00:14',
    confidence: '96%',
  },
  {
    student: 'Student 02',
    action: 'Raising hand',
    object: '—',
    time: '00:28',
    confidence: '91%',
  },
  {
    student: 'Student 03',
    action: 'Reading',
    object: 'Book',
    time: '00:43',
    confidence: '94%',
  },
  {
    student: 'Student 01',
    action: 'Looking at board',
    object: 'Board',
    time: '01:02',
    confidence: '89%',
  },
  {
    student: 'Student 04',
    action: 'Writing',
    object: 'Notebook',
    time: '01:17',
    confidence: '95%',
  },
]

export function HomePage() {
  const [video, setVideo] = useState<string | null>(null)
  const [fileName, setFileName] = useState('')
  const [isAnalyzing, setIsAnalyzing] = useState(false)
  const [analyzed, setAnalyzed] = useState(false)

  useEffect(() => {
    return () => {
      if (video) {
        URL.revokeObjectURL(video)
      }
    }
  }, [video])

  const handleVideoUpload = (event: ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0]

    if (!file) return

    if (video) {
      URL.revokeObjectURL(video)
    }

    setVideo(URL.createObjectURL(file))
    setFileName(file.name)
    setAnalyzed(false)
  }

  const analyzeVideo = () => {
    if (!video) return

    setIsAnalyzing(true)

    // Demo AI processing.
    // Later this button will call the backend API.
    setTimeout(() => {
      setIsAnalyzing(false)
      setAnalyzed(true)
    }, 1800)
  }

  return (
    <div className="mx-auto max-w-7xl space-y-8">
      {/* Header */}
      <section>
        <p className="text-sm font-semibold uppercase tracking-wider text-[#124874]">
          AI Classroom Analysis
        </p>

        <h2 className="mt-2 text-3xl font-bold tracking-tight text-slate-950">
          Understand student learning behavior
        </h2>

        <p className="mt-2 max-w-3xl text-slate-600">
          Upload a classroom video and EduGraph will organize detected
          students, objects, actions, and temporal relationships into
          structured learning information.
        </p>
      </section>

      {/* Statistics */}
      <section className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard
          title="Videos analyzed"
          value="12"
          description="This month"
        />

        <StatCard
          title="Students detected"
          value="28"
          description="Across analyzed videos"
        />

        <StatCard
          title="Behaviors detected"
          value="356"
          description="Recognized actions"
        />

        <StatCard
          title="Avg. confidence"
          value="93%"
          description="AI recognition"
        />
      </section>

      {/* Upload */}
      <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
        <div className="flex flex-col justify-between gap-4 md:flex-row md:items-center">
          <div>
            <h3 className="text-lg font-semibold text-slate-900">
              Analyze classroom video
            </h3>

            <p className="mt-1 text-sm text-slate-500">
              Upload a video file to begin classroom behavior analysis.
            </p>
          </div>

          <label className="cursor-pointer rounded-lg bg-[#124874] px-5 py-3 text-sm font-semibold text-white transition hover:bg-[#0e395c]">
            Choose video
            <input
              type="file"
              accept="video/*"
              className="hidden"
              onChange={handleVideoUpload}
            />
          </label>
        </div>

        {fileName && (
          <div className="mt-6 rounded-xl border border-slate-200 bg-slate-50 p-4">
            <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
              <div>
                <p className="text-sm font-medium text-slate-900">
                  Selected video
                </p>

                <p className="mt-1 text-sm text-slate-500">
                  {fileName}
                </p>
              </div>

              <button
                onClick={analyzeVideo}
                disabled={isAnalyzing}
                className="rounded-lg bg-[#cf373d] px-5 py-3 text-sm font-semibold text-white transition hover:bg-red-700 disabled:cursor-not-allowed disabled:opacity-60"
              >
                {isAnalyzing ? 'Analyzing...' : 'Analyze Video'}
              </button>
            </div>
          </div>
        )}
      </section>

      {/* Video + timeline */}
      {video && (
        <section className="grid gap-6 lg:grid-cols-3">
          <div className="overflow-hidden rounded-2xl border border-slate-200 bg-black shadow-sm lg:col-span-2">
            <video
              src={video}
              controls
              className="aspect-video w-full object-contain"
            />

            <div className="bg-white p-4">
              <p className="text-sm font-semibold text-slate-900">
                Classroom Video
              </p>

              <p className="mt-1 text-xs text-slate-500">
                {fileName}
              </p>
            </div>
          </div>

          <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
            <h3 className="font-semibold text-slate-900">
              Analysis Status
            </h3>

            <div className="mt-5">
              <div className="flex items-center gap-3">
                <div
                  className={`h-3 w-3 rounded-full ${
                    analyzed
                      ? 'bg-green-500'
                      : isAnalyzing
                        ? 'animate-pulse bg-yellow-500'
                        : 'bg-slate-300'
                  }`}
                />

                <span className="text-sm text-slate-600">
                  {analyzed
                    ? 'Analysis complete'
                    : isAnalyzing
                      ? 'AI is analyzing the video...'
                      : 'Ready to analyze'}
                </span>
              </div>

              {analyzed && (
                <div className="mt-6 space-y-4">
                  <ProgressItem label="Student detection" value="98%" />
                  <ProgressItem label="Action recognition" value="93%" />
                  <ProgressItem label="Object detection" value="91%" />
                  <ProgressItem label="Temporal analysis" value="89%" />
                </div>
              )}
            </div>
          </div>
        </section>
      )}

      {/* Behavior results */}
      <section className="rounded-2xl border border-slate-200 bg-white shadow-sm">
        <div className="border-b border-slate-200 p-6">
          <div className="flex flex-col justify-between gap-2 md:flex-row md:items-center">
            <div>
              <h3 className="text-lg font-semibold text-slate-900">
                Detected behaviors
              </h3>

              <p className="mt-1 text-sm text-slate-500">
                Structured student actions detected by EduGraph.
              </p>
            </div>

            <span className="w-fit rounded-full bg-blue-50 px-3 py-1 text-xs font-semibold text-[#124874]">
              Demo analysis
            </span>
          </div>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full min-w-[700px] text-left">
            <thead className="bg-slate-50 text-xs uppercase tracking-wider text-slate-500">
              <tr>
                <th className="px-6 py-4 font-semibold">Student</th>
                <th className="px-6 py-4 font-semibold">Action</th>
                <th className="px-6 py-4 font-semibold">Object</th>
                <th className="px-6 py-4 font-semibold">Time</th>
                <th className="px-6 py-4 font-semibold">Confidence</th>
              </tr>
            </thead>

            <tbody className="divide-y divide-slate-100">
              {demoBehaviors.map((behavior, index) => (
                <tr
                  key={index}
                  className="transition hover:bg-slate-50"
                >
                  <td className="px-6 py-4 text-sm font-medium text-slate-900">
                    {behavior.student}
                  </td>

                  <td className="px-6 py-4 text-sm text-slate-700">
                    {behavior.action}
                  </td>

                  <td className="px-6 py-4 text-sm text-slate-500">
                    {behavior.object}
                  </td>

                  <td className="px-6 py-4 text-sm font-mono text-slate-500">
                    {behavior.time}
                  </td>

                  <td className="px-6 py-4">
                    <span className="rounded-full bg-green-50 px-3 py-1 text-xs font-semibold text-green-700">
                      {behavior.confidence}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      {/* Behavior relationship graph */}
      <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
        <div>
          <h3 className="text-lg font-semibold text-slate-900">
            Behavior relationship graph
          </h3>

          <p className="mt-1 text-sm text-slate-500">
            Example of how EduGraph connects students, actions, and objects.
          </p>
        </div>

        <div className="mt-8 flex flex-wrap items-center justify-center gap-4 py-8">
          <GraphNode label="Student 01" type="student" />

          <GraphArrow label="performs" />

          <GraphNode label="Writing" type="action" />

          <GraphArrow label="uses" />

          <GraphNode label="Notebook" type="object" />

          <GraphArrow label="at 00:14" />

          <GraphNode label="Classroom" type="context" />
        </div>
      </section>

      {/* Timeline */}
      <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
        <h3 className="text-lg font-semibold text-slate-900">
          Activity timeline
        </h3>

        <p className="mt-1 text-sm text-slate-500">
          Chronological sequence of detected classroom activities.
        </p>

        <div className="mt-8 space-y-5">
          {demoBehaviors.map((behavior, index) => (
            <div key={index} className="flex gap-4">
              <div className="flex w-16 shrink-0 justify-end pt-1 font-mono text-xs text-slate-400">
                {behavior.time}
              </div>

              <div className="relative flex-1 border-l border-slate-200 pl-6">
                <div className="absolute -left-1.5 top-1 h-3 w-3 rounded-full bg-[#124874]" />

                <p className="text-sm font-semibold text-slate-900">
                  {behavior.student}
                </p>

                <p className="mt-1 text-sm text-slate-600">
                  {behavior.action}
                  {behavior.object !== '—' && ` → ${behavior.object}`}
                </p>
              </div>
            </div>
          ))}
        </div>
      </section>
    </div>
  )
}

function StatCard({
  title,
  value,
  description,
}: {
  title: string
  value: string
  description: string
}) {
  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
      <p className="text-sm text-slate-500">{title}</p>
      <p className="mt-2 text-3xl font-bold text-slate-950">{value}</p>
      <p className="mt-1 text-xs text-slate-400">{description}</p>
    </div>
  )
}

function ProgressItem({
  label,
  value,
}: {
  label: string
  value: string
}) {
  return (
    <div>
      <div className="mb-2 flex justify-between text-xs">
        <span className="text-slate-600">{label}</span>
        <span className="font-semibold text-slate-800">{value}</span>
      </div>

      <div className="h-2 overflow-hidden rounded-full bg-slate-100">
        <div
          className="h-full rounded-full bg-[#124874]"
          style={{ width: value }}
        />
      </div>
    </div>
  )
}

function GraphNode({
  label,
  type,
}: {
  label: string
  type: 'student' | 'action' | 'object' | 'context'
}) {
  const styles = {
    student: 'border-blue-200 bg-blue-50 text-blue-800',
    action: 'border-red-200 bg-red-50 text-red-800',
    object: 'border-green-200 bg-green-50 text-green-800',
    context: 'border-purple-200 bg-purple-50 text-purple-800',
  }

  return (
    <div
      className={`rounded-xl border px-5 py-3 text-sm font-semibold ${styles[type]}`}
    >
      {label}
    </div>
  )
}

function GraphArrow({ label }: { label: string }) {
  return (
    <div className="flex items-center gap-2 text-xs font-medium text-slate-400">
      <span>→</span>
      <span>{label}</span>
    </div>
  )
}


