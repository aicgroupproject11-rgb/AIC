import { useState } from 'react'

import type { FormEvent } from 'react'

import { useKISSearch } from '../features/kis/hooks/useKISSearch'

export function KISSearchPage() {
  const [query, setQuery] = useState('')
  const { data, loading, error, search } = useKISSearch()

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()

    const normalizedQuery = query.trim()
    if (!normalizedQuery) return

    await search({
      query: normalizedQuery,
      top_k: 20,
    })
  }

  return (
    <div className="mx-auto max-w-7xl space-y-6">
      <section>
        <p className="text-sm font-semibold uppercase tracking-wider text-[#124874]">
          KIS
        </p>
        <h2 className="mt-2 text-3xl font-bold tracking-tight text-slate-950">
          Keyframe search
        </h2>
        <p className="mt-2 max-w-3xl text-slate-600">
          Nhập mô tả cần tìm. Có thể thêm collection tag như #L21 để lọc dữ liệu.
        </p>
      </section>

      <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
        <form className="flex flex-col gap-3 md:flex-row" onSubmit={handleSubmit}>
          <input
            className="min-w-0 flex-1 rounded-lg border border-slate-300 px-4 py-3 outline-none focus:border-[#124874]"
            type="text"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Ví dụ: a person riding a bicycle #L21"
          />
          <button
            type="submit"
            disabled={loading || !query.trim()}
            className="rounded-lg bg-[#124874] px-5 py-3 font-semibold text-white transition hover:bg-[#0e395c] disabled:cursor-not-allowed disabled:opacity-50"
          >
            {loading ? 'Searching...' : 'Search'}
          </button>
        </form>

        {error && (
          <p className="mt-4 rounded-lg bg-red-50 px-4 py-3 text-sm text-red-700">
            {error}
          </p>
        )}
      </section>

      {data && (
        <section className="space-y-4">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <p className="text-sm text-slate-600">
              Found <strong>{data.count}</strong> results for <strong>“{data.query}”</strong>
            </p>
            {data.filters.collection_ids.length > 0 && (
              <p className="text-sm text-slate-500">
                Collections: {data.filters.collection_ids.join(', ')}
              </p>
            )}
          </div>

          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
            {data.results.map((item) => (
              <article
                key={item.keyframe_id}
                className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm"
              >
                <img
                  src={item.image_url}
                  alt={`${item.video_id} frame ${item.frame_number}`}
                  className="aspect-video w-full bg-slate-100 object-cover"
                  loading="lazy"
                />
                <div className="space-y-2 p-4 text-sm">
                  <div className="flex items-center justify-between gap-3">
                    <strong className="text-slate-900">#{item.rank} · {item.video_id}</strong>
                    <span className="text-slate-500">{item.score.toFixed(4)}</span>
                  </div>
                  <p className="text-slate-600">
                    Frame {item.frame_number} · {Math.round(item.timestamp_ms / 1000)}s
                  </p>
                  {item.domains && item.domains.length > 0 && (
                    <div className="flex flex-wrap gap-1.5">
                      {item.domains.map((domain) => (
                        <span
                          key={domain}
                          className="rounded-full bg-sky-50 px-2 py-1 text-xs font-medium text-[#124874]"
                        >
                          {domain}
                        </span>
                      ))}
                    </div>
                  )}
                  {item.matched_objects && item.matched_objects.length > 0 && (
                    <p className="text-xs text-slate-500">
                      Object match: {item.matched_objects.join(', ')}
                    </p>
                  )}
                  <a
                    href={`${item.video_url}#t=${item.timestamp_ms / 1000}`}
                    target="_blank"
                    rel="noreferrer"
                    className="inline-block font-semibold text-[#124874] hover:underline"
                  >
                    Open video
                  </a>
                </div>
              </article>
            ))}
          </div>
        </section>
      )}
    </div>
  )
}
