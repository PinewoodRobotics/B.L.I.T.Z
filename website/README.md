# BLITZ Website

A frontend-only Next.js app prepared for polished, accessible interface work and
deployment on Vercel.

The existing `design/` folder is reference material and remains separate from
the application source.

## Start developing

```bash
pnpm install
pnpm dev
```

Open [http://localhost:3000](http://localhost:3000). Application code lives in
`src/`, with routes in `src/app/`.

## UI stack

- Next.js App Router, React, TypeScript, ESLint, and Turbopack
- Tailwind CSS v4 with class sorting through Prettier
- shadcn/ui using the Base Nova style and accessible Base UI primitives
- Motion for layout, gesture, scroll, and enter/exit animation
- Lucide for icons
- next-themes for light, dark, and system themes
- React Hook Form, Zod, and the Hook Form resolvers for typed forms
- Sonner for toast notifications
- Zustand for lightweight client-side UI state
- cmdk for command menus and searchable palettes
- Embla Carousel for carousels
- Recharts for data visualization
- React DayPicker and date-fns for date interfaces
- input-otp for accessible one-time-code inputs

The shadcn CLI is initialized and ready to add source-owned components:

```bash
pnpm dlx shadcn@latest add dialog dropdown-menu card input
```

## Quality checks

```bash
pnpm lint
pnpm format:check
pnpm build
```

## Deploy

Import the `website` directory into Vercel. The standard `pnpm build` command
produces the production app.
