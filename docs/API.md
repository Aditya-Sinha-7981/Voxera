# Hotel Conversation Intelligence — API Contract

## Purpose

This document defines the public REST API used by:

- the web frontend
- external developers
- future hotel systems

The backend architecture is defined in `ARCHITECTURE.md`.

The frontend MUST use this API rather than accessing Supabase or AI providers directly.

### Changelog vs. v1

Wire shapes (request/response bodies, statuses, endpoints) are unchanged from v1. This revision only makes previously-implicit behavior explicit:

- when URL validation happens relative to the `202` response (§3.1)
- a `GET /api/v1/health` endpoint (§13)
- CORS (§1.1)
- default pagination values and list ordering (§11)
- timestamp format (§1.2)
- that a `failed` job may have been retried once internally before failing (§9, informational only — not part of the wire contract)

---

# 1. Base URL

Development:

```text
http://localhost:<backend-port>
```

Production:

```text
https://<deployed-backend>
```

API prefix:

```text
/api/v1
```

Authentication:

```text
None for MVP
```

All request/response bodies use JSON unless otherwise stated.

## 1.1 CORS

The API is served cross-origin from the frontend's deployment. The backend enables CORS for the configured frontend origin (see `ARCHITECTURE.md` §6.2, §20). External developers calling the API directly (not from a browser) are unaffected by CORS.

## 1.2 Timestamps

All timestamps are ISO 8601, UTC, with a `Z` suffix (e.g. `2026-08-31T10:00:00Z`).

---

# 2. Core workflow

```text
POST /api/v1/recordings
        ↓
202 Accepted
        ↓
{ id, status }
        ↓
GET /api/v1/recordings/{id}
        ↓
processing status
        ↓
repeat
        ↓
completed result
```

The API is asynchronous because transcription and LLM processing may take significant time.

Do not hold the initial POST request open until processing completes.

---

# 3. POST /api/v1/recordings

Create a processing job for an audio recording.

## Request

```json
{
  "audio_url": "https://example.com/recording.mp3"
}
```

### Validation

`audio_url` must:

- be present
- be a syntactically valid URL
- use an appropriate remote protocol such as HTTPS

The backend rejects obviously invalid input (missing field, malformed URL, disallowed scheme) synchronously, before creating a processing job — see §3.1.

Do not download the file inside the request handler.

## 3.1 What "invalid" means at this endpoint

Two different things can be wrong with `audio_url`, and they surface differently:

- **Malformed input** (missing, not a URL, wrong scheme) → rejected immediately with `400`/`422` (§10) and no recording is created.
- **Unreachable or unusable content** (host doesn't respond, times out, wrong content type, file too large) → this is only discoverable by attempting the download, which happens *after* the `202` response, during the `downloading` stage. This surfaces as the recording transitioning to `failed` (§9), not as an error on the original POST.

If your client needs to know a URL is genuinely fetchable before committing to a job, poll the resulting recording and watch for an early `failed` status — there is no separate synchronous "check this URL" endpoint.

---

# 4. Successful submission

HTTP:

```text
202 Accepted
```

Response:

```json
{
  "id": "rec_abc123",
  "status": "pending"
}
```

The `id` is the identifier used for all future status/result requests.

---

# 5. GET /api/v1/recordings/{id}

Retrieve a recording's current processing state or final result.

## Processing response

Example:

```json
{
  "id": "rec_abc123",
  "status": "transcribing"
}
```

Other processing statuses:

```text
pending
downloading
transcribing
analyzing
saving
```

The frontend should map these to user-friendly progress messages.

Recommended client polling interval: every 2 seconds, with a client-side cap on total wait time (see `ARCHITECTURE.md` §5, Processing).

---

# 6. Completed response

When processing succeeds:

```text
status = completed
```

Response:

```json
{
  "id": "rec_abc123",
  "status": "completed",
  "created_at": "2026-08-31T10:00:00Z",
  "completed_at": "2026-08-31T10:01:42Z",
  "transcript": {
    "language": "hi-en",
    "text": "Full transcript...",
    "segments": [
      {
        "speaker": "Speaker 1",
        "role": "hotel_staff",
        "start": 0.0,
        "end": 4.2,
        "text": "Hello sir, how can I help you?"
      },
      {
        "speaker": "Speaker 2",
        "role": "guest",
        "start": 4.2,
        "end": 9.8,
        "text": "My AC is not working."
      }
    ]
  },
  "analysis": {
    "title": "AC complaint",
    "summary": "The guest reported an AC issue and requested assistance.",
    "conversation_type": "complaint",
    "sentiment": {
      "label": "negative",
      "score": 0.87
    },
    "key_points": [
      "Guest reported an AC problem."
    ],
    "complaints": [
      "AC is not functioning."
    ],
    "requests": [
      "Guest requested assistance."
    ],
    "action_items": [
      {
        "action": "Send maintenance staff to inspect the AC.",
        "department": "maintenance",
        "priority": "high",
        "status": "promised"
      }
    ],
    "important_details": [],
    "follow_up_required": true
  }
}
```

The exact field types must remain consistent with the schema described below.

---

# 7. Transcript schema

```json
{
  "language": "hi-en",
  "text": "Full transcript...",
  "segments": [
    {
      "speaker": "Speaker 1",
      "role": "hotel_staff",
      "start": 0.0,
      "end": 4.2,
      "text": "Hello sir."
    }
  ]
}
```

## `language`

String.

Examples:

```text
en
hi
hi-en
unknown
```

Do not require the user to specify the language.

## `text`

Full transcript as text.

This is the primary transcript representation.

Developers should not need to download a file just to read it.

## `segments`

Array.

Each segment may contain:

```text
speaker
role
start
end
text
```

Values unavailable from the selected STT provider may be null.

The API must not fabricate missing information.

---

# 8. Analysis schema

```json
{
  "title": "AC complaint",
  "summary": "...",
  "conversation_type": "complaint",
  "sentiment": {
    "label": "negative",
    "score": 0.87
  },
  "key_points": [],
  "complaints": [],
  "requests": [],
  "action_items": [],
  "important_details": [],
  "follow_up_required": true
}
```

## `title`

Short human-readable label used primarily by the frontend history sidebar.

Examples:

```text
AC complaint
Booking inquiry
Wi-Fi issue
```

## `summary`

Concise natural-language summary.

## `conversation_type`

Allowed suggested values:

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

The backend should validate against the defined values.

## `sentiment`

```json
{
  "label": "negative",
  "score": 0.87
}
```

Allowed labels:

```text
positive
neutral
negative
```

`score` is a model confidence/strength indicator.

Do not describe it to API users as a scientifically precise psychological measurement.

## `key_points`

Array of concise important facts.

## `complaints`

Array of complaints/issues explicitly present in the conversation.

## `requests`

Array of requests made by the guest.

## `action_items`

Array:

```json
{
  "action": "Send maintenance staff.",
  "department": "maintenance",
  "priority": "high",
  "status": "promised"
}
```

Allowed priority:

```text
low
medium
high
```

Allowed status:

```text
requested
promised
completed
unknown
```

## `important_details`

Array/object structure containing explicitly mentioned operational details.

Possible information includes:

- booking reference
- room number
- dates
- times
- requirements

Do not invent missing values.

## `follow_up_required`

Boolean.

---

# 9. Failed processing response

If processing fails:

```json
{
  "id": "rec_abc123",
  "status": "failed",
  "error": {
    "code": "PROCESSING_FAILED",
    "message": "The recording could not be processed."
  }
}
```

Messages must be safe for clients.

Do not expose:

- stack traces
- provider credentials
- internal secrets
- unnecessary internal filesystem information

Suggested `error.code` values, for clients that want to branch on failure category rather than parse the message:

```text
INVALID_AUDIO        — download stage: unreachable, timed out, too large, or not audio
TRANSCRIPTION_FAILED — STT provider failure
ANALYSIS_FAILED       — Gemini failure, or malformed output after one internal retry
PERSISTENCE_FAILED   — database write failure
INTERRUPTED          — recording was orphaned by a backend restart (ARCHITECTURE.md §7.4)
PROCESSING_FAILED    — fallback for anything not covered above
```

A client should treat `error.code` as best-effort categorization, not a stable enum it must exhaustively switch on — new codes may be added without a breaking version change, and unrecognized codes should be handled like `PROCESSING_FAILED`.

---

# 10. Error response

For API-level request errors:

```json
{
  "error": {
    "code": "INVALID_AUDIO_URL",
    "message": "The supplied audio URL is invalid."
  }
}
```

Use predictable HTTP statuses.

Recommended:

```text
400 = malformed/invalid request
404 = recording not found
422 = validation failure where appropriate
500 = unexpected server error
```

Processing failures should be represented by the recording's `failed` state rather than turning every long-running job failure into an HTTP 500 response from the original POST request.

---

# 11. GET /api/v1/recordings

Return saved recordings for the frontend history/sidebar.

## Query parameters

Optional:

```text
limit    — default 20, max 100
offset   — default 0
status   — filter to a single status value
```

Example:

```text
GET /api/v1/recordings?limit=20
```

## Ordering

Results are ordered by `created_at` descending (newest first), matching the sidebar's expected presentation.

## Response

```json
{
  "items": [
    {
      "id": "rec_abc123",
      "status": "completed",
      "title": "AC complaint",
      "conversation_type": "complaint",
      "sentiment": "negative",
      "created_at": "2026-08-31T10:00:00Z"
    }
  ],
  "total": 1
}
```

`title`, `conversation_type`, and `sentiment` are `null` for recordings that have not reached `completed` (analysis doesn't exist yet).

The list endpoint should return enough information to render the sidebar without loading the entire transcript for every item.

The frontend can call the detail endpoint when an item is selected.

---

# 12. API does not return audio

The API does not expose a stored recording because audio is intentionally temporary.

There is no:

```text
GET /recordings/{id}/audio
```

There is no permanent audio URL in the result.

The system stores only the original source URL as recording metadata.

---

# 13. GET /api/v1/health

Infrastructure endpoint for deployment platforms (uptime/readiness checks) — not part of the product's conversation-intelligence contract, and not something the frontend or a product-integrating developer needs to call.

## Response

```json
{
  "status": "ok"
}
```

`200` when the process is running and can reach the database. A non-`200` (or no response) indicates the service is not ready to accept traffic.

---

# 14. Frontend usage

The frontend performs:

```text
GET /api/v1/recordings
```

on initial load.

When the user submits a URL:

```text
POST /api/v1/recordings
```

Then poll:

```text
GET /api/v1/recordings/{id}
```

until:

```text
completed
```

or:

```text
failed
```

---

# 15. Developer usage example

A developer should be able to integrate with the product conceptually like:

```bash
curl -X POST "https://api.example.com/api/v1/recordings" \
  -H "Content-Type: application/json" \
  -d '{
    "audio_url": "https://example.com/guest-call.mp3"
  }'
```

Response:

```json
{
  "id": "rec_abc123",
  "status": "pending"
}
```

Then:

```bash
curl "https://api.example.com/api/v1/recordings/rec_abc123"
```

Eventually returns the completed transcript and analysis.

---

# 16. Authentication

None for MVP.

Do not require:

```text
Authorization
Bearer token
API key
JWT
```

The API is intentionally open for the showcase.

The endpoint structure should remain compatible with authentication being added later.

---

# 17. Provider independence

The API contract does not expose which STT provider was used.

A developer should receive the same transcript structure whether the backend used:

```text
Faster-Whisper
```

or:

```text
Google Speech-to-Text
```

This is intentional.

The provider switch is an internal deployment/configuration concern.

See `ARCHITECTURE.md`, especially the Speech-to-Text Provider Architecture section.

---

# 18. Stability requirements

The following must remain stable when changing STT providers:

- POST request shape
- GET request shape
- transcript schema
- analysis schema
- database schema
- frontend behavior

Only the provider implementation/configuration changes.

This is a core architectural requirement, not an optional refactor.

---

# 19. No file-based transcript API

The primary API returns transcript content as JSON/text.

Do not make `.txt`, `.docx`, or `.pdf` generation part of the MVP API.

The frontend may provide a local "copy/download transcript" convenience later, but it is not part of the core processing contract.

---

# 20. Definition of API done

The API is complete when:

1. A recording URL can be submitted.
2. The API immediately returns a recording ID.
3. Processing state can be queried.
4. A completed result contains transcript + structured analysis.
5. A failed job exposes a safe error, categorized where possible (§9).
6. History can be listed, paginated, and ordered newest-first.
7. Frontend and external developers use the same endpoints.
8. No audio is permanently exposed or stored.
9. STT provider changes do not change the API contract.
10. A health check exists for deployment, separate from the product contract.
