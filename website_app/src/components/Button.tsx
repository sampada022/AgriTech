import { ArrowRight } from 'lucide-react'
import type { AnchorHTMLAttributes, ButtonHTMLAttributes, ReactNode } from 'react'
import { scrollToHash } from '../lib'

type Variant = 'primary' | 'secondary'
type Common = { variant?: Variant; children: ReactNode; className?: string; arrow?: boolean }
const base = 'group relative inline-flex items-center justify-center gap-3 overflow-hidden rounded-ctl px-6 py-3 font-medium leading-none active:scale-[0.97] transition-transform duration-200'
const tone: Record<Variant, string> = {
  primary: 'bg-hot text-on-hot',
  secondary: 'bg-canopy text-on-canopy',
}
const sweepCls = 'absolute inset-0 origin-left scale-x-0 transition-transform duration-500 ease-[cubic-bezier(.22,1,.36,1)] group-hover:scale-x-100 group-focus-visible:scale-x-100'
const sweepBg = (v: Variant) => ({ background: `color-mix(in srgb, var(--${v === 'primary' ? 'hot' : 'canopy'}) 78%, var(--text))` })

function Inner({ variant, children, arrow }: { variant: Variant; children: ReactNode; arrow: boolean }) {
  return (
    <>
      <span aria-hidden className={sweepCls} style={sweepBg(variant)} />
      <span className="relative">{children}</span>
      {arrow && <ArrowRight aria-hidden strokeWidth={1.5} size={18} className="relative transition-transform duration-300 group-hover:translate-x-1" />}
    </>
  )
}

export function Button({ variant = 'primary', children, className = '', arrow = true, ...rest }: Common & ButtonHTMLAttributes<HTMLButtonElement>) {
  return <button {...rest} className={`${base} ${tone[variant]} ${className}`}><Inner variant={variant} arrow={arrow}>{children}</Inner></button>
}
export function ButtonLink({ variant = 'primary', children, className = '', arrow = true, href = '#', ...rest }: Common & AnchorHTMLAttributes<HTMLAnchorElement>) {
  return (
    <a {...rest} href={href} className={`${base} ${tone[variant]} ${className}`}
      onClick={(e) => { if (href.startsWith('#') && !href.startsWith('#/')) { e.preventDefault(); scrollToHash(href) } }}>
      <Inner variant={variant} arrow={arrow}>{children}</Inner>
    </a>
  )
}
export function TextLink({ href, children, arrow = false, className = '' }: { href: string; children: ReactNode; arrow?: boolean; className?: string }) {
  return (
    <a href={href} className={`link-u ${className}`} onClick={(e) => { if (href.startsWith('#') && !href.startsWith('#/')) { e.preventDefault(); scrollToHash(href) } }}>
      {children}{arrow && <ArrowRight aria-hidden size={16} strokeWidth={1.5} />}
    </a>
  )
}
