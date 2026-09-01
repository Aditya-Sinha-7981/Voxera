-- Voxera — initial schema
-- =============================================================================
-- Authoritative spec: docs/ARCHITECTURE.md §18 and docs/API.md §11.
--
-- Design choices (documented per "simplest sensible default" rule):
--   * `status` is TEXT + CHECK rather than a real ENUM type. A future state
--     (e.g. a deferred `queued`) can be added without an ALTER TYPE migration.
--     The CHECK constraint still guarantees the §8 state machine values.
--   * All timestamps are `timestamptz` (UTC). Application emits ISO 8601 UTC
--     with a `Z` suffix (API.md §1.2).
--   * JSONB is used for structured transcript/analysis fields; sections that
--     do not need querying are stored as opaque JSON.
--   * No audio is ever stored here (ARCHITECTURE §10, §24). Only the source
--     URL is retained on `recordings.audio_url` as metadata.
-- =============================================================================

-- ---------------------------------------------------------------------------
-- recordings
-- ---------------------------------------------------------------------------
create table if not exists public.recordings (
    id              text        primary key,
    audio_url       text        not null,
    status          text        not null
                                check (status in (
                                    'pending',
                                    'downloading',
                                    'transcribing',
                                    'analyzing',
                                    'saving',
                                    'completed',
                                    'failed'
                                )),
    error_code      text        null,
    error_message   text        null,
    created_at      timestamptz not null default now(),
    completed_at    timestamptz null,

    -- A failed/completed recording must not be re-transitioned. Enforced at
    -- the application layer (services/storage.py); a CHECK is not used here
    -- so the app can update `error_message` while marking a terminal status.
    constraint recordings_audio_url_nonempty check (length(audio_url) > 0)
);

create index if not exists recordings_status_idx
    on public.recordings (status);

create index if not exists recordings_created_at_desc_idx
    on public.recordings (created_at desc);

-- ---------------------------------------------------------------------------
-- transcripts
-- ---------------------------------------------------------------------------
create table if not exists public.transcripts (
    id            text        primary key,
    recording_id  text        not null
                              unique
                              references public.recordings (id)
                              on delete cascade,
    language      text        null,
    raw_text      text        not null,
    segments      jsonb       not null default '[]'::jsonb,
    created_at    timestamptz not null default now()
);

create index if not exists transcripts_recording_id_idx
    on public.transcripts (recording_id);

-- ---------------------------------------------------------------------------
-- analyses
-- ---------------------------------------------------------------------------
create table if not exists public.analyses (
    id                  text        primary key,
    recording_id        text        not null
                                    unique
                                    references public.recordings (id)
                                    on delete cascade,
    title               text        null,
    summary             text        null,
    conversation_type   text        null,
    sentiment           jsonb       null,
    key_points          jsonb       not null default '[]'::jsonb,
    complaints          jsonb       not null default '[]'::jsonb,
    requests            jsonb       not null default '[]'::jsonb,
    action_items        jsonb       not null default '[]'::jsonb,
    important_details   jsonb       not null default '[]'::jsonb,
    follow_up_required  boolean     null,
    created_at          timestamptz not null default now()
);

create index if not exists analyses_recording_id_idx
    on public.analyses (recording_id);
