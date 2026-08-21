import { NavLink, Outlet } from 'react-router-dom'

const navItems = [
  { name: 'Dashboard', path: '/' },
  { name: 'Video Analysis', path: '/analysis' },
  { name: 'Students', path: '/students' },
  { name: 'Behavior Graph', path: '/graph' },
]

export function AppLayout() {
  return (
    <div className="min-h-screen bg-slate-50 text-slate-900">
      <div className="flex min-h-screen">
        {/* Sidebar */}
        <aside className="hidden w-64 flex-col bg-[#124874] text-white md:flex">
          <div className="border-b border-white/15 px-6 py-6">
            <div className="text-2xl font-bold">AIC</div>
            <div className="mt-1 text-sm text-blue-100">
              Classroom Intelligence
            </div>
          </div>

          <nav className="flex-1 px-4 py-6">
            <p className="mb-3 px-3 text-xs font-semibold uppercase tracking-wider text-blue-200">
              Workspace
            </p>

            <div className="space-y-2">
              {navItems.map((item) => (
                <NavLink
                  key={item.path}
                  to={item.path}
                  className={({ isActive }) =>
                    `block rounded-lg px-4 py-3 text-sm font-medium transition ${
                      isActive
                        ? 'bg-white text-[#124874]'
                        : 'text-blue-50 hover:bg-white/10'
                    }`
                  }
                >
                  {item.name}
                </NavLink>
              ))}
            </div>
          </nav>

          <div className="border-t border-white/15 px-6 py-5">
            <div className="text-xs text-blue-200">AI Classroom Analysis</div>
            <div className="mt-1 text-sm font-medium">AIC v1.0</div>
          </div>
        </aside>

        {/* Main area */}
        <div className="flex min-w-0 flex-1 flex-col">
          {/* Top bar */}
          <header className="flex h-16 items-center justify-between border-b border-slate-200 bg-white px-6">
            <div>
              <h1 className="text-lg font-semibold text-slate-900">
                Classroom Dashboard
              </h1>
            </div>

            <div className="flex items-center gap-3">
              <div className="hidden text-right sm:block">
                <p className="text-sm font-medium text-slate-800">
                  Teacher
                </p>
                <p className="text-xs text-slate-500">AIC User</p>
              </div>

              <div className="flex h-9 w-9 items-center justify-center rounded-full bg-[#124874] text-sm font-semibold text-white">
                T
              </div>
            </div>
          </header>

          {/* Page */}
          <main className="flex-1 p-6 md:p-8">
            <Outlet />
          </main>
        </div>
      </div>
    </div>
  )
}

