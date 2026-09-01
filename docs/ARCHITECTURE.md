# Hotel Conversation Intelligence — Architecture

## Why this doc exists

This is the master implementation contract for the Hotel Conversation Intelligence product.

The system accepts a remotely hosted audio recording URL, temporarily downloads the recording, transcribes it through a configurable speech-to-text provider, analyzes the transcript with Gemini Flash, stores the transcript and structured analysis in Supabase, and deletes the temporary audio after reliable persistence.

This document defines **what goes where and why**. It is intentionally detailed so a CLI coding agent (Claude Code) can implement the system end-to-end without inventing unnecessary architecture.

`API.md` is the companion contract for the public REST API. It must be read together with this document.

### Implementation rule

Treat `ARCHITECTURE.md` and `API.md` as authoritative.

Do not:

- add features not described here
- introduce infrastructure not required here
- replace the architecture with a different pattern because it is fashionable
- create authentication for the MVP
- create permanent audio storage
- add queues/Kafka/Redis/Kubernetes for the current scale
- expose provider credentials to the frontend
- make the frontend bypass the backend

If a small implementation detail is genuinely unspecified, choose the simplest sensible implementation and document the decision in code comments. Do not expand the scope.

### Changelog vs. v1

This revision keeps the v1 product, contract, and deferred-scope decisions unchanged, and tightens the parts of v1 that were underspecified enough to cause real implementation bugs:

- explicit **event-loop safety** rule for CPU-bound work (Whisper) inside an async app (§7.2)
- explicit **concurrency cap** on simultaneous processing jobs (§7.3)
- explicit **startup reconciliation** for jobs orphaned by a backend restart, since the in-process worker has no persistence across restarts (§7.4)
- explicit **today vs. later** framing for the background worker, since the showcase build intentionally uses the simplest option (§7)
- explicit **URL validation** boundary — what "reject obviously invalid input" and "must be accessible" actually mean at request time vs. download time (§9.1)
- explicit **download safety limits** with concrete numbers instead of "reasonable" (§9.2)
- explicit **orphaned temp-file sweep** as a second line of defense behind the try/finally cleanup (§10.3)
- explicit **CORS** requirement, missing from v1 despite the frontend/backend being separately deployed (§26)
- explicit **health check** endpoint for deployment platforms (§6.1)
- explicit **Gemini retry contract** — what changes between the first and second attempt (§17.1)

Nothing here contradicts v1's product scope, deferred-features list, or database shape. `API.md`'s wire contract is unchanged; a couple of previously-implicit behaviors are now stated explicitly there too.

---

# 1. Product

## Product name

Use a generic internal/product name for the implementation. The final branding can be changed independently of the architecture.

The product is a conversation-intelligence system for hotel/hostel guest interactions.

The primary use case is a conversation between:

- Guest/client
- Hotel/hostel staff

Recordings may be:

- English
- Hindi
- Hindi-English code-switched
- Informal
- Imperfectly transcribed
- Noisy

The system must be useful even when the transcript is not perfectly clean.

---

# 2. Product interfaces

There are exactly two application-facing interfaces.

## 2.1 Web application

A ChatGPT-style workspace.

The user:

1. Opens the hosted web application.
2. Sees previous processed conversations in a left sidebar.
3. Can start a new analysis.
4. Pastes an audio URL.
5. Starts processing.
6. Sees processing progress.
7. Sees the transcript and structured conversation analysis.
8. Can click older conversations to reopen them.
9. Can refresh the page without losing history.

The web application is a client of the REST API.

It does not directly communicate with Google STT, Whisper, Gemini, or Supabase.

## 2.2 REST API

The API is a real product interface, not a special backend created only for the frontend.

A developer can:

```text
POST recording URL
      ↓
receive job ID
      ↓
poll job/result
      ↓
receive transcript + analysis
```

See `API.md` for the exact API contract.

The frontend must use the same API.

---

# 3. High-level architecture

```text
                         INTERNET
                            |
             +--------------+--------------+
             |                             |
             v                             v
     +---------------+             +---------------+
     |   Web App     |             |   Developer   |
     | Next.js/React |             | API Consumer  |
     +-------+-------+             +-------+-------+
             |                             |
             +--------------+--------------+
                            |
                            | HTTP REST (CORS-enabled)
                            v
                    +---------------+
                    |    FastAPI    |
                    |    Backend    |
                    +-------+-------+
                            |
                    Create recording row
                    (status = pending)
                            |
                    Schedule processing task
                    (in-process, bounded by
                     a concurrency semaphore)
                            |
                            v
                  +--------------------+
                  |  Processing Task   |
                  +---------+----------+
                            |
                            v
                  +--------------------+
                  | Temporary Downloader|
                  +---------+----------+
                            |
                            v
                 +----------------------+
                 | SpeechToTextProvider |
                 +----------+-----------+
                            |
                 +----------+-----------+
                 |                      |
                 v                      v
        Faster-Whisper               Google STT
       (runs in a thread            PRODUCTION
        pool executor —
        never on the event loop)
                 |                      |
                 +----------+-----------+
                            |
                            v
                  Normalized Transcript
                            |
                            v
                  +--------------------+
                  |    Gemini Flash    |
                  +---------+----------+
                            |
                            v
                  Structured Analysis
                  (Pydantic-validated,
                   1 retry on failure)
                            |
                            v
                  +--------------------+
                  | Supabase PostgreSQL|
                  +--------------------+
                            |
                            v
                  Delete temporary audio
                  (guaranteed, try/finally)
```

---

# 4. Repository structure

Use a simple monorepo.

```text
hotel-conversation-intelligence/
├── frontend/
│   ├── app/
│   ├── components/
│   ├── lib/
│   ├── public/
│   ├── package.json
│   └── ...
│
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── config.py
│   │   │
│   │   ├── api/
│   │   │   └── recordings.py
│   │   │
│   │   ├── models/
│   │   │   ├── recording.py
│   │   │   ├── transcript.py
│   │   │   └── analysis.py
│   │   │
│   │   ├── services/
│   │   │   ├── processing.py
│   │   │   ├── downloader.py
│   │   │   ├── storage.py
│   │   │   └── reconciliation.py
│   │   │
│   │   ├── providers/
│   │   │   ├── base.py
│   │   │   ├── whisper.py
│   │   │   ├── google_stt.py
│   │   │   └── gemini.py
│   │   │
│   │   └── workers/
│   │       └── processor.py
│   │
│   ├── tests/
│   ├── requirements.txt
│   └── .env.example
│
├── supabase/
│   └── migrations/
│       └── 001_initial_schema.sql
│
├── docs/
│   ├── ARCHITECTURE.md
│   └── API.md
│
└── README.md
```

`services/reconciliation.py` is new vs. v1 — see §7.4.

The exact framework-specific files may differ, but the responsibilities must remain separated.

---

# 5. Frontend

## Responsibility

The frontend owns presentation and user interaction.

It is responsible for:

- URL input
- New analysis state
- Processing progress
- History sidebar
- Selected recording
- Transcript display
- Analysis display
- Error display

It is NOT responsible for:

- STT
- Gemini
- database access
- provider credentials
- audio processing

## Initial screen

The center pane should show a simple product-oriented empty state:

```text
Analyze a hotel conversation

Paste an audio recording URL below.

[ Audio URL __________________________ ]

[ Analyze Recording ]
```

The left sidebar displays existing recordings.

## History

On page load:

```text
GET /api/v1/recordings
```

Use the response to populate the sidebar.

Each item should show a generated short title and useful metadata such as time and conversation type.

Example:

```text
AC complaint
Today, 10:42 AM

Booking inquiry
Today, 09:15 AM

Wi-Fi issue
Yesterday
```

The title is a UI convenience, not a separate AI product feature. It may be generated as part of analysis.

## New analysis

Clicking `New Analysis` clears the selected recording and returns the center pane to URL input.

## Processing

After submitting:

```text
POST /api/v1/recordings
```

receive an ID.

Poll:

```text
GET /api/v1/recordings/{id}
```

Render backend-reported states:

```text
Downloading audio...
Transcribing conversation...
Analyzing conversation...
Saving results...
```

Do not fake completion states.

Poll every 2 seconds. Stop polling when the backend reports:

```text
completed
```

or:

```text
failed
```

Cap total polling duration client-side (e.g. 5 minutes) and surface a "still processing, check back later" state rather than polling forever if something has gone wrong upstream.

## Result page

Show, in this general order:

1. Summary
2. Sentiment
3. Conversation type
4. Key points
5. Complaints
6. Requests
7. Action items
8. Follow-up requirement
9. Transcript

The transcript should preserve bilingual text.

Speaker labels should be shown when available.

---

# 6. FastAPI backend

The backend is the central application boundary.

It owns:

- API routes
- validation
- job creation
- processing orchestration
- provider selection
- database access
- error handling
- temporary audio lifecycle

Routes must remain thin.

Do not put the entire processing pipeline into the route handler.

The route creates/returns a recording and delegates processing.

## 6.1 Health check

Expose:

```text
GET /api/v1/health
```

Returns `200 { "status": "ok" }` when the process is up and can reach the database. This is for deployment platforms (uptime checks, load balancer readiness) — it is infrastructure, not a product feature, and is not part of `API.md`'s product contract.

## 6.2 CORS

The frontend and backend are deployed separately (§26). The backend must enable CORS for the configured `FRONTEND_URL` origin. Do not use a wildcard origin in production; the dev default may be permissive.

---

# 7. Processing model

The API is asynchronous from the client's perspective.

When:

```text
POST /api/v1/recordings
```

is received:

```text
validate URL (syntax + protocol — see §9.1)
   ↓
create recording row
   ↓
status = pending
   ↓
schedule processing (in-process task, see §7.1)
   ↓
return 202 + recording ID
```

The API does not wait for transcription and Gemini processing.

The frontend and external developers use:

```text
GET /api/v1/recordings/{id}
```

to observe progress.

## 7.1 Worker choice: today vs. later

For today's showcase, at the current expected scale of a few recordings per day, use the simplest mechanism: an in-process async background task (FastAPI `BackgroundTasks`, or `asyncio.create_task`). This has **no persistence across a backend restart** — a job in flight when the process restarts is lost from the worker's perspective, though its DB row remains in a non-terminal state. §7.4 defines how that is handled.

This is an explicit, accepted trade-off for the showcase, not an oversight.

**Do not introduce Redis, Kafka, Celery, or Kubernetes.**

The upgrade path, when needed, is a lightweight DB-backed poller: a loop that reads recordings in `pending` status, claims one (e.g. via an atomic `UPDATE ... WHERE status = 'pending' RETURNING`), and processes it — still a single Python process, still no external queue. This upgrade must not change the API contract, database schema, or provider abstraction. Do not build this now; the interface between "create a recording" and "process a recording" (§7.5) should simply make swapping the trigger mechanism a small, local change later.

## 7.2 Event-loop safety

FastAPI's request handling runs on an asyncio event loop. Faster-Whisper transcription is CPU-bound and blocking — it must **never** run directly inside an `async def` request or task on the event loop, or it will stall all other requests (including status polling) for the duration of transcription.

Run Whisper transcription in a thread pool executor (e.g. `asyncio.to_thread` or `loop.run_in_executor`). Google STT's client calls are I/O-bound and may be awaited directly if using an async client, or also dispatched to a thread pool if only a sync client is available.

## 7.3 Concurrency cap

Bound the number of recordings processing simultaneously with a semaphore (e.g. `asyncio.Semaphore(2)`), configurable via environment. This exists because Whisper transcription is memory- and CPU-heavy; an unbounded number of concurrent jobs on one instance (§25, one backend instance is sufficient) can exhaust resources and degrade or crash the process. A capped queue simply means additional submissions stay in `pending` slightly longer, which is acceptable at "a few recordings per day."

## 7.4 Startup reconciliation

Because the in-process worker (§7.1) does not survive a restart, on backend startup the application must sweep for recordings stuck in a non-terminal state (`pending`, `downloading`, `transcribing`, `analyzing`, `saving`) that are older than a short grace period (e.g. 2 minutes, to avoid racing a job that is genuinely still in flight from before the sweep runs) and mark them `failed` with a safe message such as "Processing was interrupted and did not complete." This keeps the database honest — the required invariant from §21 ("a failed job exposes a safe error," never a false `completed`) must hold even across a crash or redeploy, not just within a single successful run.

This reconciliation step becomes unnecessary once the DB-backed poller upgrade (§7.1) is in place, since that design re-claims `pending` rows naturally; it can remain as a harmless safety net regardless.

## 7.5 Orchestration seam

Structure `services/processing.py` so that "given a recording ID, run it through download → STT → Gemini → persist → cleanup" is a single async function with no knowledge of *how* it was invoked. The route handler, the startup reconciliation sweep, and (later) the DB-backed poller should all be able to call this same function. This is what makes the §7.1 upgrade path small later.

---

# 8. Recording state machine

The recording lifecycle is:

```text
pending
   ↓
downloading
   ↓
transcribing
   ↓
analyzing
   ↓
saving
   ↓
completed
```

Any stage may transition to:

```text
failed
```

The database status is the source of truth for processing progress.

The frontend only renders what the backend reports.

`failed` and `completed` are terminal. Once a recording reaches either, no further state transition is written for it.

---

# 9. Audio downloader

The downloader receives the remote URL.

Responsibilities:

1. Validate the URL.
2. Download the recording.
3. Save it to a unique temporary location.
4. Verify the download is usable for STT.
5. Return the temporary file path.
6. Never create permanent audio storage.

Example:

```text
/tmp/hotel-ai/
    <recording-id>/
        audio.<extension>
```

Never use a globally shared filename.

## 9.1 URL validation boundary

Validation happens in two places, and they check different things:

**At `POST` time (request handler, before creating the recording row):**

- syntactically valid URL
- scheme is `http` or `https` (recommend rejecting plain `http` in production, but do not hard-fail dev/testing over it)
- reject a request if the scheme is something else (e.g. `file://`, `ftp://`) or the URL is malformed

This is fast, synchronous, in-process validation. It does **not** involve downloading or even connecting to the remote host — that would make the POST request slow and defeats the async design (§7).

**At download time (inside the processing task, `downloading` state):**

- attempt the actual download with the limits in §9.2
- if the host is unreachable, times out, returns a non-2xx status, or returns a content-type that isn't audio, this is a processing failure (→ `failed` state with a safe error), not a `400` on the original POST

"Be accessible by the backend" (from the product requirement) is verified here, asynchronously, not synchronously in the request handler. A URL can be syntactically perfect and still turn out to be inaccessible, and that must not block the client's POST request.

## 9.2 Download safety limits

Concrete defaults (configurable via environment, not hardcoded magic numbers in code):

```text
MAX_AUDIO_FILE_SIZE_MB=100
DOWNLOAD_CONNECT_TIMEOUT_SECONDS=10
DOWNLOAD_TOTAL_TIMEOUT_SECONDS=60
```

- Reject (fail the job) if `Content-Length` exceeds the max, when the header is present.
- If `Content-Length` is absent, stream the download and abort once the max size is exceeded, rather than trusting an untrusted server.
- Enforce both a connect timeout and a total transfer timeout.
- Validate `Content-Type` starts with `audio/` where the header is present; if absent, proceed but let STT failure be the fallback signal rather than blocking on a missing header.

The MVP does not need elaborate media infrastructure beyond these limits.

---

# 10. Critical audio retention policy

This is a hard requirement.

The system must not retain audio after processing.

The required lifecycle is:

```text
Remote URL
   ↓
Temporary local audio
   ↓
STT
   ↓
Transcript
   ↓
Gemini
   ↓
Analysis
   ↓
Persist transcript + analysis
   ↓
Delete temporary audio
```

The database does not contain audio.

Do not create a Supabase Storage audio bucket.

Do not upload the downloaded recording to Supabase.

Do not keep an archive of recordings.

## 10.1 Deletion condition

The audio can be considered safe to delete only after:

- STT completed successfully
- Gemini analysis completed successfully
- transcript persistence succeeded
- analysis persistence succeeded
- recording can safely be marked completed

Cleanup must also be attempted on failure, at whatever stage failure occurred.

## 10.2 Guaranteed cleanup

Use guaranteed cleanup/finally-style logic (e.g. a `try/finally` wrapping the whole per-recording temp directory, deleting it unconditionally on exit — success or failure).

If persistence fails, do not falsely mark the recording completed.

## 10.3 Orphaned temp-file sweep

Because the process can crash mid-job (before `finally` runs, e.g. on an OOM kill or a hard process kill), add a lightweight startup sweep that deletes any per-recording directory under the temp root (§9, `/tmp/hotel-ai/<recording-id>/`) that is older than a short grace period. This is a second line of defense behind §10.2, not a replacement for it, and reuses the same startup hook as §7.4's reconciliation sweep.

---

# 11. Speech-to-text abstraction

This is the most important architecture seam.

The application must never hardcode Google STT into the processing service.

Define an interface conceptually equivalent to:

```python
class SpeechToTextProvider:
    def transcribe(self, audio_path) -> Transcript:
        ...
```

Implement two providers:

```text
FasterWhisperProvider
GoogleSTTProvider
```

## Development provider

Use Faster-Whisper locally.

This is what will be used for the showcase, since Google Cloud credentials are not yet available.

Example:

```env
STT_PROVIDER=whisper
WHISPER_MODEL=small
```

The Whisper model must be configurable. Recall §7.2: the call into this provider must be dispatched off the event loop.

## Production/client provider

Google Cloud Speech-to-Text.

When the client provides a billing-enabled Google Cloud project and credentials:

```env
STT_PROVIDER=google
```

No other part of the product should need to change.

The API contract stays identical.

The database schema stays identical.

Gemini stays identical.

Frontend stays identical.

Processing orchestration stays identical.

Only the provider selected through configuration changes.

---

# 12. Normalized transcript contract

Both STT providers must return the same internal representation.

Conceptually:

```json
{
  "language": "hi-en",
  "text": "Full transcript...",
  "segments": [
    {
      "speaker": "Speaker 1",
      "role": null,
      "start": 0.0,
      "end": 4.2,
      "text": "Hello sir, how can I help you?"
    }
  ]
}
```

Fields may be null when unavailable.

Do not fabricate:

- speakers
- roles
- timestamps
- language

If the selected provider cannot provide speaker diarization, the transcript must simply omit/leave those fields unavailable.

---

# 13. Speaker diarization

Use diarization where supported by the selected provider.

Do not assume:

```text
Speaker 1 = Guest
Speaker 2 = Hotel Staff
```

The transcript representation must support speaker information.

Gemini may infer roles such as:

```text
guest
hotel_staff
```

from context if enough evidence exists.

If there is insufficient evidence, role may remain null/unknown.

Never invent a speaker role.

---

# 14. Bilingual conversations

The system is explicitly expected to handle:

- Hindi
- English
- Hindi-English code switching

Do not require users to choose a language before processing.

Do not translate the transcript automatically.

Preserve what was spoken.

Gemini should be prompted to understand bilingual/code-switched conversation and imperfect STT.

---

# 15. Gemini analysis

Gemini Flash is the second AI stage.

Input:

```text
Normalized transcript
```

Output:

```text
Structured ConversationAnalysis
```

Gemini must not be used to perform application control flow.

It produces structured information consumed by the application.

The output must be validated with Pydantic before database persistence.

---

# 16. Required analysis fields

The analysis must contain:

### Title

Short history/sidebar title.

Examples:

```text
AC complaint
Booking inquiry
Wi-Fi issue
```

### Summary

A concise summary of the conversation.

### Conversation type

Suggested values:

```text
booking
complaint
inquiry
cancellation
check_in
check_out
maintenance
request
general
other
```

### Sentiment

```json
{
  "label": "positive",
  "score": 0.87
}
```

Labels:

```text
positive
neutral
negative
```

The score is a model confidence/strength indicator, not a scientifically precise psychological measurement.

### Key points

Important facts discussed.

### Complaints

Problems or dissatisfaction expressed.

### Requests

Things requested by the guest.

### Action items

Each action should contain:

```json
{
  "action": "Send maintenance staff.",
  "department": "maintenance",
  "priority": "high",
  "status": "promised"
}
```

Priority:

```text
low
medium
high
```

Status:

```text
requested
promised
completed
unknown
```

### Important details

Extract only information explicitly present, such as:

- booking reference
- room number
- dates
- times
- guest requirements
- operational details

### Follow-up

Boolean:

```text
true
false
```

Indicates whether additional action/follow-up appears necessary.

---

# 17. Gemini reliability

The prompt must explicitly state:

- The transcript may contain STT errors.
- Hindi and English may be mixed.
- Speech may be informal.
- Do not invent facts.
- Do not invent missing booking details.
- Do not invent speaker identities.
- Use null/empty arrays when information is unavailable.
- Return the exact structured schema.

Pydantic validates the result.

## 17.1 Retry contract

If Gemini returns output that fails Pydantic validation:

1. Retry exactly once, appending the specific validation error(s) to the prompt so the retry is corrective, not identical (e.g. "Your previous response failed validation because: `<error>`. Return only valid JSON matching the schema.").
2. If the retry also fails validation, mark processing `failed` with a safe error (e.g. `"code": "ANALYSIS_FAILED"`) — do not persist malformed analysis as a successful result, and do not fall back to a partially-filled or guessed analysis object.

---

# 18. Database

Use Supabase PostgreSQL.

Persistent entities:

```text
recordings
transcripts
analyses
```

Relationships:

```text
recordings
    |
    +---- transcripts (1:1)
    |
    +---- analyses   (1:1)
```

A recording may temporarily exist without transcript/analysis during processing.

A completed recording must have both.

## recordings

```text
id
audio_url
status
error_message
created_at
completed_at
```

The URL is metadata describing the input source. It is not an audio copy.

## transcripts

```text
id
recording_id
language
raw_text
segments JSONB
created_at
```

## analyses

```text
id
recording_id
title
summary
conversation_type
sentiment JSONB
key_points JSONB
complaints JSONB
requests JSONB
action_items JSONB
important_details JSONB
follow_up_required
created_at
```

Use JSONB for structured arrays/objects where appropriate.

Create indexes for:

- recording status
- recording creation time
- transcript recording ID
- analysis recording ID

The exact SQL migration is part of the implementation.

---

# 19. Database access

The backend uses Supabase server-side.

Environment:

```env
SUPABASE_URL=
SUPABASE_SERVICE_ROLE_KEY=
```

The service role key must never reach the browser.

The frontend does not directly query Supabase.

The frontend uses FastAPI.

This keeps database credentials and future authorization logic behind one application boundary.

---

# 20. Configuration

Use environment configuration.

Example:

```env
# Application
FRONTEND_URL=

# Processing
MAX_CONCURRENT_JOBS=2
MAX_AUDIO_FILE_SIZE_MB=100
DOWNLOAD_CONNECT_TIMEOUT_SECONDS=10
DOWNLOAD_TOTAL_TIMEOUT_SECONDS=60
RECONCILIATION_GRACE_PERIOD_SECONDS=120

# STT
STT_PROVIDER=whisper
WHISPER_MODEL=small

# Google STT, only required when STT_PROVIDER=google
GOOGLE_CLOUD_PROJECT=
GOOGLE_APPLICATION_CREDENTIALS=

# Gemini
GEMINI_API_KEY=
GEMINI_MODEL=gemini-2.5-flash

# Database
SUPABASE_URL=
SUPABASE_SERVICE_ROLE_KEY=
```

No secrets in source control.

Provide `.env.example`.

Development may use Whisper without any Google credentials.

Later the client can provide Google credentials and only the STT configuration changes.

`GEMINI_MODEL` is configurable rather than hardcoded so the specific Flash model version can be updated without a code change as Google's model lineup evolves.

---

# 21. Error handling

Expected failures:

- invalid URL
- inaccessible URL
- download timeout
- unsupported media
- corrupted audio
- excessive file size
- Whisper failure
- Google STT failure
- Gemini failure
- invalid Gemini schema (after retry — §17.1)
- database failure
- cleanup failure
- backend restart mid-job (§7.4)

For a processing failure:

1. Log the recording ID and stage.
2. Set recording status to `failed`.
3. Store a safe error message.
4. Attempt temporary audio cleanup.
5. Expose a safe error through the API.

Do not expose:

- API keys
- credentials
- stack traces
- internal filesystem paths unnecessarily

---

# 22. Logging

Useful logs:

```text
recording_id
processing stage
provider
duration
success/failure
error category
```

Do not log complete transcripts by default.

Never log secrets.

---

# 23. No authentication for MVP

There is intentionally no:

- login
- user registration
- OAuth
- JWT
- API key authentication
- roles
- permissions

The showcase is intentionally unauthenticated.

The endpoint structure must still be clean enough that authentication can be added later.

Do not build authentication "just in case."

---

# 24. No permanent audio storage

This deserves repetition because it is a hard product requirement.

Do not:

- store audio in Supabase Storage
- store audio blobs in PostgreSQL
- keep audio on persistent disk
- create an audio archive
- return permanent audio URLs

Audio is a temporary processing artifact.

---

# 25. Current scale

Expected usage:

```text
A few recordings per day
```

Therefore:

- simple in-process background processing is sufficient (§7)
- local temporary filesystem is sufficient
- Supabase PostgreSQL is sufficient
- one backend instance is sufficient
- no distributed queue is required

If the client later needs hundreds/thousands of recordings per day, scaling can be addressed separately.

Do not design for that traffic now.

---

# 26. Deployment

Deploy:

```text
Frontend
Backend
Supabase
```

The frontend needs:

```env
NEXT_PUBLIC_API_URL=
```

The backend needs the variables described in §20, plus `FRONTEND_URL` for CORS (§6.2).

The backend must be capable of running the local Whisper provider in the deployed environment for the showcase.

This matters: local Whisper means the deployed backend must have sufficient CPU/RAM and the selected model must be available there.

If the showcase backend cannot reasonably run Whisper at the chosen model size, choose a smaller configurable model (e.g. `tiny` or `base` instead of `small`) rather than redesigning the system.

When Google STT is enabled later, the backend no longer needs to run Whisper for production transcription.

---

# 27. API relationship

`API.md` defines:

- endpoints
- request schemas
- response schemas
- HTTP statuses
- processing statuses
- examples
- error format

The frontend must consume the API exactly as defined in `API.md`.

If a UI requirement conflicts with the API contract, update the architecture/API documentation before changing implementation.

---

# 28. Testing requirements

At minimum:

## API

- valid submission
- invalid URL
- processing status
- completed result
- failed result
- history listing
- health check

## Processing

- download success
- download failure (timeout, oversized, non-audio content-type)
- STT success
- STT failure
- Gemini success
- Gemini malformed response, then successful retry
- Gemini malformed response on both attempts → failed
- database persistence
- cleanup on success
- cleanup on failure
- startup reconciliation marks a stale in-flight recording as `failed`
- concurrency cap actually bounds simultaneous jobs

## Provider abstraction

Test that:

```text
STT_PROVIDER=whisper
```

uses Whisper.

Test that:

```text
STT_PROVIDER=google
```

selects Google.

The downstream processing code must remain provider-agnostic.

## Critical retention test

Verify that temporary audio is deleted after successful processing.

Also verify cleanup is attempted after failure, and that the orphan sweep (§10.3) removes a directory left behind by a simulated hard crash.

---

# 29. Deliberately deferred

Do not implement these now:

- authentication
- multi-tenancy
- billing
- user accounts
- admin roles
- analytics dashboards
- email notifications
- WhatsApp integration
- CRM integration
- permanent audio storage
- audio playback
- advanced speaker diarization infrastructure
- Redis
- Kafka
- Celery
- Kubernetes
- distributed workers
- advanced rate limiting
- DB-backed poller upgrade (§7.1) — the seam for it should exist, but building it is not part of today's showcase

These may become future requirements.

They are not part of this implementation.

---

# 30. Definition of done

The MVP is complete when:

1. A user can open the deployed web application.
2. They can paste a remote audio URL.
3. The backend accepts it.
4. The recording enters `pending`.
5. The backend downloads the audio temporarily, off the request-handling path.
6. Faster-Whisper transcribes it without blocking the event loop.
7. A normalized transcript is produced.
8. Gemini Flash analyzes it, with one corrective retry on schema failure.
9. Structured analysis is validated.
10. Transcript and analysis are persisted in Supabase.
11. Temporary audio is deleted, guaranteed, even on failure.
12. Recording becomes `completed`.
13. The UI displays the transcript and analysis.
14. Refreshing the page shows the recording in history.
15. Clicking history reopens the result.
16. The same workflow is usable through the REST API.
17. Switching `STT_PROVIDER` is sufficient to select Google STT later.
18. No secrets are exposed to the frontend.
19. Failed processing is visible and does not masquerade as success, including when the failure was caused by a backend restart mid-job.
20. A simple, unauthenticated health check exists for deployment.

This is the complete MVP boundary.
