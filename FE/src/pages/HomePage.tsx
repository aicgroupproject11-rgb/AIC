import { useState } from 'react'

import { uploadKISVideos } from '../features/kis/services/kisApi'

import type { ChangeEvent, FormEvent } from 'react'
import type { KISVideoUploadResponse } from '../features/kis/types/kis'

export function HomePage() {
  const [videos, setVideos] = useState<File[]>([])
  const [result, setResult] = useState<KISVideoUploadResponse | null>(null)
  const [error, setError] = useState('')
  const [uploading, setUploading] = useState(false)

  function handleVideoSelection(event: ChangeEvent<HTMLInputElement>) {
    setVideos(Array.from(event.target.files ?? []))
    setResult(null)
    setError('')
  }

  async function handleUpload(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (videos.length === 0) return

    setUploading(true)
    setError('')
    try {
      setResult(await uploadKISVideos(videos))
    } catch (uploadError) {
      setError(uploadError instanceof Error ? uploadError.message : 'Upload thất bại.')
    } finally {
      setUploading(false)
    }
  }

  return (
    <section className="rounded-2xl border border-slate-200 bg-white p-10 shadow-sm">
      <p className="mb-3 text-sm font-semibold uppercase tracking-widest text-blue-700">KIS videos</p>
      <h1 className="text-4xl font-bold tracking-tight text-slate-950">Upload nhiều video</h1>
      <p className="mt-4 text-slate-600">Chọn tối đa 20 video trong một lần tải lên.</p>

      <form className="mt-8 space-y-5" onSubmit={handleUpload}>
        <input
          type="file"
          accept="video/mp4,video/quicktime,video/x-msvideo,video/x-matroska,video/webm"
          multiple
          onChange={handleVideoSelection}
          className="block w-full rounded-lg border border-slate-300 p-3"
        />

        {videos.length > 0 && (
          <div className="rounded-lg bg-slate-50 p-4">
            <p className="font-semibold">Đã chọn {videos.length} video:</p>
            <ul className="mt-2 list-inside list-disc text-sm text-slate-600">
              {videos.map((video) => <li key={`${video.name}-${video.lastModified}`}>{video.name}</li>)}
            </ul>
          </div>
        )}

        <button
          type="submit"
          disabled={videos.length === 0 || uploading}
          className="rounded-lg bg-blue-800 px-5 py-3 font-semibold text-white disabled:opacity-50"
        >
          {uploading ? 'Đang upload...' : 'Upload videos'}
        </button>
      </form>

      {error && <p className="mt-5 text-red-700">{error}</p>}
      {result && (
        <div className="mt-6 rounded-lg bg-green-50 p-4 text-green-900">
          <p className="font-semibold">Đã upload thành công {result.count} video.</p>
          <ul className="mt-2 list-inside list-disc text-sm">
            {result.videos.map((video) => <li key={video.stored_name}>{video.original_name}</li>)}
          </ul>
        </div>
      )}
    </section>
  )
}
