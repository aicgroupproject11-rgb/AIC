import { Outlet } from 'react-router-dom'

export function AppLayout() {
  return (
    <div className="min-h-screen bg-slate-50 text-slate-900">
      <header className="border-b border-slate-200 bg-white">
        <div className="mx-auto flex max-w-6xl items-center px-6 py-4">
          <span className="text-lg font-semibold text-blue-900">Base Platform</span>
        </div>
      </header>
      <main className="mx-auto max-w-6xl px-6 py-16">
        <Outlet />
      </main>
    </div>
  )
}

