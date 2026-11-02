import { ArrowLeft, Eye, EyeOff } from 'lucide-react'
import { motion } from 'framer-motion'
import { useEffect, useState } from 'react'
import { Button } from '../components/Button'
import FieldMap from '../components/FieldMap'
import ThemeToggle from '../components/ThemeToggle'
import { NEXT_KEY, useAuth } from '../hooks/auth'
import { EASE } from '../lib'

const DEMO = { email: 'demo@aeroscout.app', password: 'aeroscout-demo' }

export default function LoginPage() {
  const { user, login, register } = useAuth()
  const [mode, setMode] = useState<'in' | 'up'>('in')
  const [name, setName] = useState(''), [email, setEmail] = useState(''), [pw, setPw] = useState(''), [show, setShow] = useState(false)
  const [busy, setBusy] = useState(false), [err, setErr] = useState('')
  useEffect(() => { document.title = 'Sign in · AeroScout' }, [])
  useEffect(() => {
    if (!user) return
    let next = '#/dashboard'; try { next = sessionStorage.getItem(NEXT_KEY) || next; sessionStorage.removeItem(NEXT_KEY) } catch { /* ignore */ }
    location.hash = next.startsWith('#/dashboard') ? next : '#/dashboard'
  }, [user])

  const submit = async (e: React.FormEvent) => {
    e.preventDefault(); setBusy(true); setErr('')
    try { if (mode === 'in') await login(email, pw); else await register(name, email, pw) } catch (x) { setErr((x as Error).message) } finally { setBusy(false) }
  }
  const field = 'mt-1 w-full rounded-ctl border border-line bg-surface px-4 py-3 text-ink placeholder:text-muted'
  return (
    <div className="grid min-h-screen lg:grid-cols-12">
      <div className="relative hidden flex-col justify-between border-r border-line p-10 lg:col-span-6 lg:flex xl:col-span-7">
        <a href="#top" onClick={() => { location.hash = '' }} className="flex items-baseline gap-2"><span className="font-display text-2xl font-bold tracking-tight">AeroScout</span><span className="label mono text-muted">by 9Eleven</span></a>
        <div>
          <FieldMap mode="class" route={1} label="Field map with three red hotspots and a walking route, shown as a preview of the dashboard." hud={{ alt: '35.0 M', vari: '0.21', entropy: '4.8', hotspots: '03' }} className="w-full max-w-[640px]" />
          <h2 className="mt-10 max-w-md !text-[clamp(1.75rem,2.6vw,2.5rem)]">Find the three sick patches. Skip the fifty healthy acres.</h2>
          <p className="mt-4 max-w-md text-muted">Sign in to upload field photos, plan the walk and track every hotspot from first scan to treatment.</p>
        </div>
        <p className="label mono text-muted">LEAP Agritech Hackathon 2026 · Team 9Eleven</p>
      </div>

      <div className="flex flex-col p-6 sm:p-10 lg:col-span-6 xl:col-span-5">
        <div className="flex items-center justify-between">
          <a href="#top" onClick={() => { location.hash = '' }} className="link-u label mono text-muted"><ArrowLeft size={14} strokeWidth={1.5} />Back to site</a>
          <ThemeToggle />
        </div>
        <motion.div initial={{ opacity: 0, y: 24 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.8, ease: EASE }} className="mx-auto my-auto w-full max-w-sm py-12">
          <p className="label mono mb-4 flex items-center gap-3 text-muted"><span aria-hidden className="inline-block h-px w-8 bg-hot" />{mode === 'in' ? 'Sign in' : 'Create account'}</p>
          <h1 className="!text-[clamp(2rem,4vw,3rem)]">{mode === 'in' ? 'Welcome back.' : 'Start scouting.'}</h1>
          <p className="mt-3 text-muted">{mode === 'in' ? 'Open your dashboard to see which hotspots need a visit.' : 'One account for the dashboard and the field tasks on your phone.'}</p>

          <form onSubmit={submit} className="mt-8" noValidate>
            {mode === 'up' && <label className="mb-4 block text-sm">Your name<input value={name} onChange={(e) => setName(e.target.value)} autoComplete="name" required className={field} /></label>}
            <label className="block text-sm">Email<input type="email" value={email} onChange={(e) => setEmail(e.target.value)} autoComplete="email" placeholder="you@example.com" required className={field} /></label>
            <label className="mt-4 block text-sm">Password{mode === 'up' && <span className="text-muted"> (8+ characters)</span>}
              <span className="relative block">
                <input type={show ? 'text' : 'password'} value={pw} onChange={(e) => setPw(e.target.value)} autoComplete={mode === 'in' ? 'current-password' : 'new-password'} required className={`${field} pr-12`} />
                <button type="button" onClick={() => setShow(!show)} aria-label={show ? 'Hide password' : 'Show password'} className="absolute right-2 top-1/2 grid h-9 w-9 -translate-y-1/2 place-items-center rounded-ctl text-muted hover:text-ink">{show ? <EyeOff size={16} strokeWidth={1.5} /> : <Eye size={16} strokeWidth={1.5} />}</button></span></label>
            {err && <p role="alert" className="mt-4 rounded-ctl border border-hot p-3 text-sm">{err}</p>}
            <Button type="submit" disabled={busy || !email || !pw || (mode === 'up' && !name)} className="mt-6 w-full">{busy ? 'Please wait…' : mode === 'in' ? 'Sign in' : 'Create account'}</Button>
          </form>

          <p className="mt-6 text-sm text-muted">{mode === 'in' ? 'New here? ' : 'Already have an account? '}
            <button onClick={() => { setMode(mode === 'in' ? 'up' : 'in'); setErr('') }} className="link-u font-medium text-ink">{mode === 'in' ? 'Create an account' : 'Sign in'}</button></p>

          <div className="mt-8 rounded-card border border-dashed border-line p-4">
            <p className="label mono text-muted">Demo account</p>
            <p className="mono mt-2 text-sm">{DEMO.email}<br />{DEMO.password}</p>
            <button onClick={() => { setMode('in'); setEmail(DEMO.email); setPw(DEMO.password); setErr('') }} className="link-u mt-3 text-sm font-medium">Fill in the demo account</button>
          </div>
        </motion.div>
      </div>
    </div>
  )
}
