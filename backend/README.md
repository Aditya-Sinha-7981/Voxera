# Voxera backend (FastAPI)

FastAPI service implementing the Voxera conversation-intelligence pipeline.

Authoritative spec: [`docs/ARCHITECTURE.md`](../docs/ARCHITECTURE.md) and [`docs/API.md`](../docs/API.md).

## Layout

```
app/
  main.py             App factory, lifespan, CORS, startup sweeps
  config.py           pydantic-settings env loading
  api/
    recordings.py     POST/GET /api/v1/recordings, GET /api/v1/recordings/{id}
    health.py         GET /api/v1/health
    validation.py     §3.1 synchronous URL validation
    errors.py         §10 envelope helper
  models/
    recording.py      Recording, RecordingStatus, list/response shapes
    transcript.py     Transcript, Segment
    analysis.py       ConversationAnalysis (also used for Gemini validation)
    _serialization.py ISO-8601-Z datetime serialization (§1.2)
  services/
    storage.py        Supabase wrappers, terminal-state immutability
    downloader.py     §9 audio downloader with safety limits
    processing.py     §7.5 orchestration seam (download → STT → Gemini → persist → cleanup)
    reconciliation.py §7.4 startup reconcile + §10.3 orphan sweep
  providers/
    base.py           SpeechToTextProvider protocol
    whisper.py        FasterWhisperProvider (lazy-loaded, disposed on shutdown)
    google_stt.py     GoogleSTTProvider (production path; diarization enabled)
    gemini.py         GeminiAnalyzer (structured-output, §17.1 corrective retry)
  workers/
    processor.py      §7.1 in-process scheduler with §7.3 semaphore
```

## Quickstart

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
# fill in SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY, GEMINI_API_KEY

uvicorn app.main:app --reload --port 8000
```

## Tests

```bash
cd backend
.venv/bin/pytest
```

33 unit tests cover URL validation, model wire shapes, storage chokepoints, and downloader extension selection. **59 unit tests after Phase 3** — adds provider coverage including Gemini's §17.1 retry contract and Whisper's lazy-model discipline.

## API endpoints

| Method | Path | Purpose |
| --- | --- | --- |
| `POST` | `/api/v1/recordings` | Submit a recording URL (returns `202 {id, status}`) |
| `GET`  | `/api/v1/recordings` | List recordings, paginated, newest first |
| `GET`  | `/api/v1/recordings/{id}` | Status / detail (processing, completed, failed) |
| `GET`  | `/api/v1/health` | Readiness probe (200 if DB reachable) |
