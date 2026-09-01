# Voxera backend (FastAPI)

Placeholder package marker. Code lands in Phase 2.

Structure (target):

```
app/
├── main.py              # FastAPI app factory, lifespan, CORS, startup sweeps
├── config.py            # pydantic-settings env loading
├── api/
│   ├── recordings.py    # POST/GET /api/v1/recordings, GET /api/v1/recordings/{id}
│   └── health.py        # GET /api/v1/health
├── models/
│   ├── recording.py     # Recording, RecordingStatus, list-item
│   ├── transcript.py    # Transcript, Segment
│   └── analysis.py      # ConversationAnalysis (also used for Gemini validation)
├── services/
│   ├── storage.py       # Supabase wrappers
│   ├── downloader.py    # §9 audio downloader with safety limits
│   ├── processing.py    # §7.5 orchestration seam
│   └── reconciliation.py# §7.4 startup reconciliation + §10.3 orphan sweep
├── providers/
│   ├── base.py          # SpeechToTextProvider protocol
│   ├── whisper.py       # FasterWhisperProvider
│   ├── google_stt.py    # GoogleSTTProvider
│   └── gemini.py        # GeminiAnalyzer (§17 + §17.1 retry)
└── workers/
    └── processor.py     # Semaphore + asyncio.create_task scheduler
```
