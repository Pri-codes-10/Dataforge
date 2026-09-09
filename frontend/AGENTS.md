# SUTRA Frontend — Agent Guidelines

This repository is the **SUTRA frontend** — a standalone React application.
It is **not connected to Lovable** or any other hosted editor.

## Rules for AI Agents

- This is a **frontend-only** repository. Do not create a backend, database, authentication, or API endpoints.
- The routing system is **TanStack Start** (file-based routing in `src/routes/`). Do not use Next.js or Remix conventions.
- The `routeTree.gen.ts` file is **auto-generated** by TanStack Router — do not edit it manually.
- Design changes must preserve the approved SUTRA visual design (voice orb, sidebar, language panel, task pipeline, color scheme).
- Mock data lives in `src/data/`. Service interfaces live in `src/services/`. Types are in `src/types/`.
- The `VITE_API_URL` environment variable is the single point for the future backend URL.
- Do not expose API keys or secrets.

## Development Commands

```bash
npm install
npm run dev    # Start development server
npm run build  # Production build
npm run lint   # ESLint
```
