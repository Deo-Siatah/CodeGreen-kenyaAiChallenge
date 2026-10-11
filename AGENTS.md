# AGENTS.md — Hifadhi

Monorepo: `backend/` (FastAPI, Postgres on Neon) and `frontend/` (React 19, Vite, TypeScript).
This file governs the frontend. If `backend/AGENTS.md` exists, it governs the backend.

## Commands (run from `frontend/`)
- `npm run dev` — Vite dev server on http://localhost:5173. API base is `VITE_API_URL` (default http://localhost:8000).
- `npm run check` — typecheck + lint + unit tests. It MUST pass before you say a task is done.
- `npm test` / `npm run test:watch` — Vitest.
- `npm run e2e` — Playwright. Needs the backend running against a TEST database branch, never main.
- `npm run gen:api` — regenerate `src/api/generated/schema.d.ts` from the running backend's `/openapi.json`.

## How to work
1. Plan first. For anything larger than one file, outline the change and wait for approval.
2. Tests first. Write the failing tests, run them, and paste the red output. Then implement. Then paste the green output.
3. Small steps. One section of the task file per session. Stop at the section boundary.
4. Evidence, not claims. End every task with the raw output of `npm run check` (and `npm run build` if you touched config). Never write "should work" or "tests pass" without pasted output.
5. If a command fails twice for the same reason, stop and report what you tried. Never make a test pass by weakening or deleting it.
6. Show diffs for every file you changed. Do not summarise code you did not paste.

## Architecture rules (hard)
- The UI is a function of an event log. Graph state comes only from the pure reducer in `src/domain/graph`. Components never mutate graph state directly; API results become `GraphEvent`s.
- `src/domain` has no React, no axios and no DOM. It is pure and unit-tested.
- All HTTP goes through `src/api` (axios client). Components never import axios. Every response is validated with zod at the boundary. Request bodies are `.strict()` because the backend rejects unknown fields.
- No mock data in runtime code. Test fixtures live in `src/test/`. Recorded replays live in `src/replay/`, generated from the real backend by a script and clearly labelled.
- Force-layout ticks must not call `setState`. Write positions to motion values or refs.
- No `any`, no `as` casts on API data, no non-null `!` on data that came from the network.
- Respect `prefers-reduced-motion`.

## Dependencies
Ask before adding a dependency. Prefer what is already installed. UI components come from shadcn through the shadcn MCP (`npx shadcn@latest add ...`). Do not hand-write a component the registry already provides.

## Backend facts that bite
- Request bodies must match the Pydantic schema exactly. Unknown fields return 422 `extra_forbidden`.
- IDs are UUID strings. Timestamps are ISO-8601.
- `GET /api/verify/{id}/explanation` can take about 60 seconds (LLM call). Use a long timeout, show progress, support cancel.
- Error shapes: `{"detail": "..."}` or `{"detail": [{"loc": [...], "msg": "...", "type": "..."}]}`.
- Conflicts return 409 (already answered, invalid loan state). Validation returns 422. Missing returns 404.
- There is no authentication yet. Keep one interceptor seam in `src/api/client.ts` for it.
- Scoring is deterministic. A farmer's `character_score` is the pooled community evidence; `capacity_score` can be null when no satellite reading exists.

## Design language
"Night harvest": near-black green canvas, luminous nodes, restrained motion with purpose. Tokens live in `src/styles/tokens.css`; use them and do not hard-code hex values in components. Fonts: Fraunces (display), Hanken Grotesk (UI), JetBrains Mono (data), self-hosted through @fontsource-variable.

## Repo hygiene
- One conventional commit per section. Never commit `.env`.
- The legacy UI is tagged `legacy-ui-v1`. Do not resurrect it into `src/`.