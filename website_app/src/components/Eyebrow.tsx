export default function Eyebrow({ children, className = '' }: { children: string; className?: string }) {
  return (
    <p className={`label text-muted mb-6 flex items-center gap-3 ${className}`}>
      <span aria-hidden className="inline-block h-px w-8 bg-hot" />
      {children}
    </p>
  )
}
