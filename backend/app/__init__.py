"""Backend application package.

Structure (target):
    app/
        main.py             FastAPI app factory, lifespan, CORS, startup sweeps
        config.py           pydantic-settings env loading
        api/
            recordings.py   POST/GET /api/v1/recordings, GET /api/v1/recordings/{id}
            health.py       GET /api/v1/health
        models/
            recording.py    Recording, RecordingStatus, list-item
            transcript.py   Transcript, Segment
            analysis.py     ConversationAnalysis (used for Gemini validation)
        services/
            storage.py      Supabase wrappers
            downloader.py   audio downloader with safety limits
            processing.py   orchestration seam
            reconciliation  startup reconciliation + orphan sweep
        providers/
            base.py         SpeechToTextProvider protocol
            whisper.py      FasterWhisperProvider
            google_stt.py   GoogleSTTProvider
            gemini.py       GeminiAnalyzer
        workers/
            processor.py    Semaphore + asyncio.create_task scheduler
"""
