# AeroScout website

Single-page product site (React + TypeScript + Tailwind v4 + Framer Motion + GSAP ScrollTrigger + Lenis).

    npm install
    npm run dev      # http://localhost:5174
    npm run build

Layout: `src/sections/*` one file per section, `src/components/*` shared pieces, `src/data/*` field-map data and copy.
Theme tokens live in `src/index.css` (CSS variables, mapped into Tailwind via `@theme inline`).
All numbers on the page that come from the demo (areas, confidence, entropy, 1.2 km route) are sample data.
