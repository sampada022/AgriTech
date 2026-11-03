import Lenis from 'lenis'
import gsap from 'gsap'
import { ScrollTrigger } from 'gsap/ScrollTrigger'
import { useCallback, useEffect, useState } from 'react'
import Preloader from './components/Preloader'
import { IntroContext } from './hooks/intro'
import LiveScan from './sections/LiveScan'
import DataPage from './pages/DataPage'
import DashboardApp from './dashboard/DashboardApp'
import LoginPage from './pages/LoginPage'
import { AuthProvider, NEXT_KEY, useAuth } from './hooks/auth'
import Cursor from './components/Cursor'
import Navbar from './components/Navbar'
import ScrollProgress from './components/ScrollProgress'
import { setLenis } from './lib'
import { useReduced } from './hooks/useMedia'
import Hero from './sections/Hero'
import Problem from './sections/Problem'
import WhyDronesGetItWrong from './sections/WhyDronesGetItWrong'
import Compare from './sections/Compare'
import HowItWorks from './sections/HowItWorks'
import LearningLoop from './sections/LearningLoop'
import Technology from './sections/Technology'
import Dashboard from './sections/Dashboard'
import FarmerDemo from './sections/FarmerDemo'
import Impact from './sections/Impact'
import Team from './sections/Team'
import FinalCTA from './sections/FinalCTA'
import Footer from './sections/Footer'

gsap.registerPlugin(ScrollTrigger)

export default function App() {
  return <AuthProvider><AppInner /></AuthProvider>
}

function AppInner() {
  const { user, loading } = useAuth()
  const reduced = useReduced()
  const [route, setRoute] = useState(location.hash)
  useEffect(() => { const on = () => { setRoute(location.hash); if (location.hash.startsWith('#/')) scrollTo(0, 0) }; addEventListener('hashchange', on); return () => removeEventListener('hashchange', on) }, [])
  const dataPage = route.startsWith('#/data'), dash = route.startsWith('#/dashboard'), login = route.startsWith('#/login')
  const standalone = dash || login
  // The dashboard needs a signed-in user: remember where they were going, send them to the login page.
  useEffect(() => {
    if (dash && !loading && !user) { try { sessionStorage.setItem(NEXT_KEY, route) } catch { /* ignore */ } location.hash = '#/login' }
  }, [dash, loading, user, route])
  // The preloader plays once per page load, only when landing on the site itself (not a dashboard/data deep link) and with motion allowed.
  const [showPre, setShowPre] = useState(() => !reduced && !location.hash.startsWith('#/'))
  const [ready, setReady] = useState(!showPre)
  const reveal = useCallback(() => setReady(true), [])
  const done = useCallback(() => { setShowPre(false); setTimeout(() => ScrollTrigger.refresh(), 50) }, [])
  useEffect(() => {
    if (reduced || standalone) return
    const lenis = new Lenis({ duration: 1.1, easing: (t) => 1 - Math.pow(1 - t, 4) })
    setLenis(lenis)
    lenis.on('scroll', ScrollTrigger.update)
    const tick = (t: number) => lenis.raf(t * 1000)
    gsap.ticker.add(tick); gsap.ticker.lagSmoothing(0)
    return () => { gsap.ticker.remove(tick); lenis.destroy(); setLenis(null) }
  }, [reduced, standalone])
  if (login) return <LoginPage />
  if (dash) return loading || !user ? <div className="grid min-h-screen place-items-center"><p className="label mono text-muted">Checking your session…</p></div> : <DashboardApp route={route} />
  return (
    <IntroContext.Provider value={ready}>
    {showPre && <Preloader onReveal={reveal} onDone={done} />}
    <>
      <a href="#main" className="sr-only-x focus:not-sr-only focus:fixed focus:left-4 focus:top-4 focus:z-[200] focus:rounded-ctl focus:bg-hot focus:px-4 focus:py-2 focus:text-on-hot">Skip to content</a>
      <ScrollProgress /><Cursor /><Navbar />
      {dataPage ? <DataPage /> : <main id="main">
        <Hero /><Problem /><WhyDronesGetItWrong /><Compare /><HowItWorks /><LearningLoop />
        <Technology /><FarmerDemo /><Dashboard /><LiveScan /><Impact /><Team /><FinalCTA />
      </main>}
      <Footer />
    </>
    </IntroContext.Provider>
  )
}
