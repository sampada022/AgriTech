import { ChartLine, Database, House, Layers, LayoutDashboard, ListChecks, LogOut, RefreshCw } from 'lucide-react'
import { useAuth } from '../hooks/auth'
import { useEffect, useState, type ReactNode } from 'react'
import ThemeToggle from '../components/ThemeToggle'
import DataPage from '../pages/DataPage'
import Insights from './Insights'
import Overview from './Overview'
import ScanDetail from './ScanDetail'
import Scans from './Scans'
import { StoreProvider, useStore } from './store'
import Tasks from './Tasks'

const NAV = [
  { key: '', label: 'Overview', Icon: LayoutDashboard },
  { key: 'scans', label: 'Fields', Icon: Layers },
  { key: 'tasks', label: 'Field tasks', Icon: ListChecks },
  { key: 'insights', label: 'Insights', Icon: ChartLine },
  { key: 'data', label: 'Data', Icon: Database },
]

function Shell({ route }: { route: string }) {
  const { user, logout } = useAuth()
  const { online, refresh, stats } = useStore(); const [spin, setSpin] = useState(false)
  const [page = '', id = ''] = route.replace(/^#\/dashboard\/?/, '').split('/')
  const active = page === '' ? '' : page
  useEffect(() => { document.title = 'AeroScout dashboard' }, [])
  const doRefresh = async () => { setSpin(true); await refresh(); setTimeout(() => setSpin(false), 500) }
  let body: ReactNode
  if (page === 'scans' && id) body = <ScanDetail id={id} />
  else if (page === 'scans') body = <Scans />
  else if (page === 'tasks') body = <Tasks />
  else if (page === 'insights') body = <Insights />
  else if (page === 'data') body = <DataPage embedded />
  else body = <Overview />
  const link = (n: (typeof NAV)[number]) => `#/dashboard${n.key ? '/' + n.key : ''}`
  return (
    <div className="min-h-screen lg:grid lg:grid-cols-[232px_1fr]">
      <aside className="no-print hidden border-r border-line bg-surface lg:block">
        <div className="sticky top-0 flex h-screen flex-col p-5">
          <a href="#/dashboard" className="flex items-baseline gap-2"><span className="font-display text-2xl font-bold tracking-tight">AeroScout</span><span className="label mono text-muted">dashboard</span></a>
          <nav aria-label="Dashboard" className="mt-10 flex flex-col gap-1">
            {NAV.map((n) => { const on = n.key === active; return (
              <a key={n.key} href={link(n)} aria-current={on ? 'page' : undefined} className={`flex items-center gap-3 rounded-ctl border-l-2 px-3 py-2.5 text-[15px] ${on ? 'border-hot bg-bg font-medium' : 'border-transparent text-muted hover:text-ink'}`}>
                <n.Icon aria-hidden size={18} strokeWidth={1.5} />{n.label}
                {n.key === 'tasks' && stats && stats.totals.open > 0 && <span className="label mono ml-auto rounded-full bg-hot px-2 py-0.5 text-on-hot" style={{ fontSize: 10 }}>{stats.totals.open}</span>}</a>) })}
          </nav>
          <div className="mt-auto flex flex-col gap-4">
            {user && <div className="border-t border-line pt-4"><p className="truncate text-sm font-medium">{user.name}</p><p className="mono truncate text-xs text-muted">{user.email}</p>
              <button onClick={async () => { location.hash = ''; await logout() }} className="link-u mt-2 text-sm text-muted"><LogOut size={14} strokeWidth={1.5} />Sign out</button></div>}
            <a href="#top" onClick={() => { location.hash = '' }} className="link-u text-sm text-muted"><House size={14} strokeWidth={1.5} />Back to the site</a>
            <p className="label mono flex items-center gap-2 text-muted"><span aria-hidden className={`h-2 w-2 rounded-full ${online ? 'bg-canopy' : 'bg-hot'}`} />{online === null ? 'Connecting' : online ? 'Server online' : 'Server offline'}</p>
          </div>
        </div>
      </aside>

      <div className="min-w-0 pb-24 lg:pb-0">
        <header className="no-print sticky top-0 z-30 flex items-center justify-between gap-3 border-b border-line bg-bg/80 px-4 py-3 backdrop-blur-md sm:px-8">
          <a href="#/dashboard" className="font-display text-xl font-bold tracking-tight lg:invisible">AeroScout</a>
          <div className="flex items-center gap-2">
            <p className="label mono mr-2 hidden items-center gap-2 text-muted sm:flex"><span aria-hidden className={`h-2 w-2 rounded-full ${online ? 'bg-canopy' : 'bg-hot'}`} />{online ? 'Live · refreshes every 20 s' : 'Offline'}</p>
            <button onClick={doRefresh} aria-label="Refresh data" className="grid h-10 w-10 place-items-center rounded-ctl border border-line hover:border-ink"><RefreshCw size={16} strokeWidth={1.5} className={spin ? 'animate-spin' : ''} /></button>
            <button onClick={async () => { location.hash = ''; await logout() }} aria-label="Sign out" className="grid h-10 w-10 place-items-center rounded-ctl border border-line hover:border-ink lg:hidden"><LogOut size={16} strokeWidth={1.5} /></button>
            <ThemeToggle />
          </div>
        </header>
        {online === false && <p role="alert" className="mx-4 mt-4 rounded-ctl border border-hot p-3 text-sm sm:mx-8">The analysis server is not reachable. Start it with <span className="mono">uv run uvicorn backend.app.main:app --port 8000</span></p>}
        <main className="px-4 py-8 sm:px-8 lg:py-10" id="main">{body}</main>
      </div>

      <nav aria-label="Dashboard" className="no-print fixed inset-x-0 bottom-0 z-40 grid grid-cols-5 border-t border-line bg-surface lg:hidden">
        {NAV.map((n) => { const on = n.key === active; return (
          <a key={n.key} href={link(n)} aria-current={on ? 'page' : undefined} className={`flex flex-col items-center gap-1 py-2.5 text-[11px] ${on ? 'text-hot' : 'text-muted'}`}><n.Icon aria-hidden size={20} strokeWidth={1.5} />{n.label.replace('Field tasks', 'Tasks')}</a>) })}
      </nav>
    </div>
  )
}

export default function DashboardApp({ route }: { route: string }) {
  return <StoreProvider><Shell route={route} /></StoreProvider>
}
