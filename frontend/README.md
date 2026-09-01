# Voxera frontend (Next.js)

ChatGPT-style two-pane workspace for the Voxera conversation-intelligence product.

Authoritative spec: [`docs/ARCHITECTURE.md`](../docs/ARCHITECTURE.md) §5 and [`docs/API.md`](../docs/API.md).

## Layout

```
app/
  layout.tsx         Root HTML shell
  page.tsx           Center-pane state machine (empty / detail / live)
  globals.css        Tailwind base + custom dark theme tokens
components/
  Sidebar.tsx        History list (§5 History)
  NewRecordingForm.tsx  Initial URL-input state (§5 Initial screen)
  ProcessingView.tsx  Status-driven progress UI (§5 Processing)
  ResultView.tsx     Sectioned analysis + transcript (§5 Result page)
  TranscriptView.tsx  Speaker/role-aware transcript renderer
  ActionItemsList.tsx  Action items with priority/status chips
  ErrorView.tsx      Safe error envelope (no stack traces)
lib/
  api.ts             Typed REST client (single seam to backend)
  format.ts          Pure formatters (status messages, timestamps, chips)
  types.ts           Wire types mirroring backend/app/models/*.py
  useRecordingPoll.ts  2s polling with 5-minute cap (§5)
  useRecordingsList.ts Sidebar list loader
```

## Quickstart

```bash
cd frontend
nvm use          # picks Node 20 from .nvmrc
npm install
cp .env.example .env.local
# set NEXT_PUBLIC_API_URL=http://localhost:8000

npm run dev      # http://localhost:3000
```

## Scripts

| Command | Purpose |
| --- | --- |
| `npm run dev` | Dev server with HMR |
| `npm run build` | Production build |
| `npm run start` | Run production build |
| `npm run typecheck` | TypeScript check |
| `npm run lint` | ESLint |

## Design notes

- Single typed client (`lib/api.ts`) — no Supabase or AI keys reach the browser.
- Polling stops on `completed` / `failed` and after a 5-minute cap; a passive
  "still processing" state is shown rather than polling forever.
- The center pane is a small explicit state machine — easy to extend and
  easy to test.
- All timestamps render in ISO 8601 UTC (`Z` suffix) per API §1.2.
- Dark theme tokens (`bg.*`, `border.*`, `fg.*`, `accent`, `ok`, `warn`, `danger`)
  in `tailwind.config.ts`; no UI library — just Tailwind.
