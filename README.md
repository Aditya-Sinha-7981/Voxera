# Voxera — Hotel Conversation Intelligence

Voxera is a conversation-intelligence system for hotel/hostel guest interactions. It accepts a remote audio URL, temporarily downloads the recording, transcribes it through a configurable speech-to-text provider, analyzes the transcript with Gemini Flash, persists transcript + analysis to Supabase, and deletes the temporary audio.

## Repo layout

```
voxera/
├── frontend/                Next.js (App Router) + TypeScript + Tailwind
├── backend/                 FastAPI service
│   ├── app/
│   │   ├── api/             Routes (recordings, health)
│   │   ├── models/          Pydantic domain models
│   │   ├── services/        Storage, downloader, processing, reconciliation
│   │   ├── providers/       STT + Gemini (pluggable)
│   │   └── workers/         Background processing orchestration
│   ├── tests/
│   └── requirements.txt
├── supabase/migrations/     SQL migrations (001_initial_schema.sql)
├── docs/
│   ├── ARCHITECTURE.md      Authoritative implementation contract
│   └── API.md               Public REST API contract
└── README.md
```

The repository is a simple monorepo. **Treat `docs/ARCHITECTURE.md` and `docs/API.md` as authoritative** — when in doubt, the docs win.

## Quickstart

Detailed setup lives in each subdirectory:

- Backend: [`backend/README.md`](./backend/README.md)
- Frontend: [`frontend/README.md`](./frontend/README.md)
- Database: [`supabase/migrations/`](./supabase/migrations)

## Design principles (summary)

- No authentication for MVP (showcase).
- No permanent audio storage — audio is a temporary processing artifact only.
- One in-process worker (no Redis/Kafka/Celery/Kubernetes at current scale).
- Pluggable STT provider (`whisper` for dev, `google` for production).
- API contract is independent of the STT provider chosen.

See [`docs/ARCHITECTURE.md`](./docs/ARCHITECTURE.md) for the full architecture and [`docs/API.md`](./docs/API.md) for the public REST API.
