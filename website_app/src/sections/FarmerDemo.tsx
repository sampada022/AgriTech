import { Check, Download, MessageSquare, Plane, Sparkles } from 'lucide-react'
import { useEffect, useRef, useState } from 'react'
import { farmerDemoApi, type DemoRunOut, type SmsMessage } from '../api'
import { ButtonLink, Button } from '../components/Button'
import Eyebrow from '../components/Eyebrow'
import { Reveal } from '../components/Reveal'

type Stage = 'idle' | 'flying' | 'sent' | 'failed'

const STEPS = [
  { Icon: Plane, title: 'We fly, and we analyse.', body: 'A scheduled drone pass over the registered field, then the same classical-CV pipeline you saw above.' },
  { Icon: MessageSquare, title: 'The farmer gets one SMS.', body: 'No app, no login. Just a message on whatever phone they have.' },
  { Icon: Download, title: 'They tap it, and get the report.', body: 'A PDF with the map, the hotspots and what to check on the ground. That is the entire farmer-facing product.' },
]

export default function FarmerDemo() {
  const [stage, setStage] = useState<Stage>('idle')
  const [run, setRun] = useState<DemoRunOut | null>(null)
  const [msgs, setMsgs] = useState<SmsMessage[]>([])
  const [err, setErr] = useState('')
  const poll = useRef<ReturnType<typeof setInterval>>(undefined)

  useEffect(() => () => clearInterval(poll.current), [])

  const start = async () => {
    setStage('flying'); setErr(''); setMsgs([])
    try {
      const r = await farmerDemoApi.run()
      setRun(r)
      const deadline = Date.now() + 8000
      poll.current = setInterval(async () => {
        const list = await farmerDemoApi.sms(r.mobile).catch(() => [])
        const justSent = list.filter((m) => new Date(m.at).getTime() >= Date.now() - 15000)
        if (justSent.length) {
          setMsgs(justSent)
          setStage('sent')
          clearInterval(poll.current)
        } else if (Date.now() > deadline) {
          clearInterval(poll.current)
          setStage('failed'); setErr('The SMS did not arrive in time. Try again.')
        }
      }, 700)
    } catch (e) {
      setStage('failed'); setErr((e as Error).message)
    }
  }

  return (
    <section id="farmer-demo" aria-labelledby="farmer-demo-h" className="section">
      <div className="wrap">
        <Reveal className="max-w-3xl">
          <Eyebrow>10 / THE FARMER'S WHOLE EXPERIENCE</Eyebrow>
          <h2 id="farmer-demo-h">The farmer never opens this website.</h2>
          <p className="mt-6">They register once, in person, with us. From then on, we fly and we watch. All they ever get is a text message and a PDF. Run it below, exactly as it happens for Ramesh Gowda's field in Kikkeri.</p>
        </Reveal>

        <div className="mt-12 grid gap-10 lg:grid-cols-12">
          <div className="lg:col-span-5">
            <ol className="flex flex-col gap-6">
              {STEPS.map((s, i) => (
                <li key={s.title} className="flex gap-4">
                  <span aria-hidden className="grid h-10 w-10 shrink-0 place-items-center rounded-full border border-line bg-surface"><s.Icon size={18} strokeWidth={1.5} /></span>
                  <div><p className="label mono text-muted">Step {i + 1}</p><p className="font-display text-lg font-semibold">{s.title}</p><p className="mt-1 text-sm text-muted">{s.body}</p></div>
                </li>
              ))}
            </ol>
            <Button onClick={start} disabled={stage === 'flying'} className="mt-8">
              {stage === 'flying' ? 'Flying and analysing…' : stage === 'sent' ? 'Run it again' : 'Run today\'s drone check'}
            </Button>
            {err && <p role="alert" className="mt-3 text-sm text-hot">{err}</p>}
          </div>

          <div className="lg:col-span-7">
            <div className="mx-auto w-full max-w-sm rounded-[2rem] border-4 border-ink/80 bg-bg p-3 shadow-float">
              <div className="mb-2 flex items-center justify-between px-1 text-[11px]"><span className="label mono text-muted">{run?.masked_mobile ?? 'farmer\'s phone'}</span><span className="label mono text-muted">SMS</span></div>
              <div className="flex h-96 flex-col gap-2 overflow-y-auto rounded-ctl bg-mapbg p-3">
                {stage === 'idle' && <p className="m-auto max-w-[220px] text-center text-sm text-muted">No messages yet. Run the drone check on the left.</p>}
                {stage === 'flying' && <p className="m-auto flex items-center gap-2 text-sm text-muted"><Sparkles size={14} className="animate-pulse" strokeWidth={1.5} />Analysing the field…</p>}
                {msgs.map((m) => (
                  <div key={m.pk} className="max-w-[88%] rounded-card bg-surface p-3 text-sm shadow-sm">
                    <div className="mb-1 flex justify-between text-[10px] text-muted"><span className="label mono">AGRISCT</span><span>{new Date(m.at).toLocaleTimeString()}</span></div>
                    <p>{m.body}</p>
                  </div>
                ))}
                {stage === 'sent' && run?.report_id && (
                  <a href={run.report_id ? `/api/dev/demo/report/${run.report_id}` : undefined} target="_blank" rel="noreferrer"
                    className="label mono mt-1 inline-flex w-fit items-center gap-2 self-start rounded-ctl border border-ink bg-ink px-3 py-2 text-bg hover:opacity-90">
                    <Download size={14} strokeWidth={1.5} />Tap to view the PDF report
                  </a>
                )}
              </div>
            </div>
            {stage === 'sent' && (
              <p className="mt-4 flex items-center justify-center gap-2 text-center text-sm text-muted"><Check size={14} className="text-canopy" strokeWidth={1.5} />That's it. No account, no app, nothing else to learn.</p>
            )}
          </div>
        </div>

        <div className="mt-16 flex flex-col items-start gap-5 rounded-card border border-line bg-surface p-8 sm:flex-row sm:items-center sm:justify-between">
          <div><p className="font-display text-2xl font-semibold">Meanwhile, this is everything we're watching for them.</p><p className="mt-2 text-muted">The farmer never sees this. Your team does.</p></div>
          <ButtonLink href="#/dashboard">Open the monitoring dashboard</ButtonLink>
        </div>
      </div>
    </section>
  )
}
