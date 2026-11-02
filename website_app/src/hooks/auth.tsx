import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from 'react'
import { authApi, type User } from '../api'

interface Auth { user: User | null; loading: boolean; login: (e: string, p: string) => Promise<void>; register: (n: string, e: string, p: string) => Promise<void>; logout: () => Promise<void> }
const Ctx = createContext<Auth | null>(null)
export const useAuth = () => { const c = useContext(Ctx); if (!c) throw new Error('no auth'); return c }

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null), [loading, setLoading] = useState(true)
  useEffect(() => { authApi.me().then(setUser).finally(() => setLoading(false)) }, [])
  // any API call that comes back 401 means the session ended
  useEffect(() => { const on = () => setUser(null); addEventListener('aero:unauth', on); return () => removeEventListener('aero:unauth', on) }, [])
  const login = useCallback(async (e: string, p: string) => setUser(await authApi.login(e, p)), [])
  const register = useCallback(async (n: string, e: string, p: string) => setUser(await authApi.register(n, e, p)), [])
  const logout = useCallback(async () => { await authApi.logout(); setUser(null) }, [])
  const v = useMemo(() => ({ user, loading, login, register, logout }), [user, loading, login, register, logout])
  return <Ctx.Provider value={v}>{children}</Ctx.Provider>
}

/** Where to send the user after signing in (set by the route guard). */
export const NEXT_KEY = 'aeroscout-next'
