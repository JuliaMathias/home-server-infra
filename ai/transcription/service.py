"""Private, durable transcription jobs with a single model-owning worker."""
from __future__ import annotations

import asyncio
import fcntl
import json
import logging
import os
import sqlite3
import threading
import time
import uuid
from contextlib import asynccontextmanager, contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from fastapi import FastAPI, File, HTTPException, UploadFile, Form
from starlette.formparsers import MultiPartException
from starlette.responses import JSONResponse

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
log = logging.getLogger("transcription")


@dataclass(frozen=True)
class Settings:
    data_dir: Path = Path(os.getenv("DATA_DIR", "/data"))
    model_path: str = os.getenv("MODEL_PATH", "/models/large-v3")
    model_revision: str = os.getenv("MODEL_REVISION", "unrecorded")
    device: str = os.getenv("DEVICE", "cuda")
    compute_type: str = os.getenv("COMPUTE_TYPE", "int8_float16")
    max_upload_bytes: int = int(os.getenv("MAX_UPLOAD_BYTES", str(512 * 1024 * 1024)))
    max_pending: int = int(os.getenv("MAX_PENDING", "4"))

    def __post_init__(self):
        if self.max_upload_bytes < 1 or self.max_pending < 1:
            raise ValueError("Upload and queue limits must be positive")


class Store:
    def __init__(self, directory: Path):
        self.directory = directory
        directory.mkdir(parents=True, exist_ok=True)
        self.database = directory / "jobs.sqlite3"
        with self.connect() as connection:
            connection.execute("PRAGMA journal_mode=WAL")
            connection.execute("""CREATE TABLE IF NOT EXISTS jobs (
                id TEXT PRIMARY KEY, status TEXT NOT NULL, language TEXT,
                created_at REAL NOT NULL, updated_at REAL NOT NULL,
                result TEXT, error TEXT)""")

    @contextmanager
    def connect(self):
        connection = sqlite3.connect(self.database, timeout=10)
        connection.row_factory = sqlite3.Row
        try:
            with connection:
                yield connection
        finally:
            connection.close()

    def reserve(self, language: str | None, limit: int) -> str:
        identifier = str(uuid.uuid4())
        with self.connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            pending = connection.execute(
                "SELECT count(*) FROM jobs WHERE status IN ('uploading','queued','running')"
            ).fetchone()[0]
            if pending >= limit:
                raise HTTPException(429, "Transcription queue is full", headers={"Retry-After": "30"})
            now = time.time()
            connection.execute("INSERT INTO jobs VALUES (?, 'uploading', ?, ?, ?, NULL, NULL)",
                               (identifier, language, now, now))
        return identifier

    def update(self, identifier: str, status: str, *, result=None, error=None):
        with self.connect() as connection:
            connection.execute(
                "UPDATE jobs SET status=?, updated_at=?, result=?, error=? WHERE id=?",
                (status, time.time(), json.dumps(result) if result is not None else None,
                 error, identifier))

    def get(self, identifier: str):
        with self.connect() as connection:
            row = connection.execute("SELECT * FROM jobs WHERE id=?", (identifier,)).fetchone()
        if row is None:
            return None
        job = dict(row)
        job["result"] = json.loads(job["result"]) if job["result"] is not None else None
        return job

    def recover(self):
        with self.connect() as connection:
            connection.execute("""UPDATE jobs SET status='failed', updated_at=?,
                error='service_restarted: interrupted job; submit the original again'
                WHERE status IN ('uploading','running')""", (time.time(),))
        for part in self.directory.glob("*.part"):
            part.unlink()

    def claim(self):
        with self.connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                "SELECT * FROM jobs WHERE status='queued' ORDER BY created_at LIMIT 1"
            ).fetchone()
            if row is not None:
                connection.execute("UPDATE jobs SET status='running', updated_at=? WHERE id=?",
                                   (time.time(), row["id"]))
        return dict(row) if row else None


class WhisperEngine:
    def __init__(self, settings: Settings):
        from faster_whisper import WhisperModel
        self.settings = settings
        self.model = WhisperModel(settings.model_path, device=settings.device,
                                  compute_type=settings.compute_type, cpu_threads=4,
                                  num_workers=1, local_files_only=True)

    def transcribe(self, path: Path, language: str | None):
        started = time.monotonic()
        segments, info = self.model.transcribe(str(path), language=language,
            beam_size=5, vad_filter=True, word_timestamps=True,
            condition_on_previous_text=False)
        output = []
        for segment in segments:
            output.append({"start": segment.start, "end": segment.end,
                "text": segment.text, "avg_logprob": segment.avg_logprob,
                "no_speech_prob": segment.no_speech_prob,
                "words": [{"start": word.start, "end": word.end, "word": word.word,
                           "probability": word.probability} for word in (segment.words or [])]})
        return {"language": info.language, "language_probability": info.language_probability,
            "requested_language": language, "duration_seconds": info.duration,
            "speech_duration_seconds": info.duration_after_vad,
            "segments": output, "text": "".join(s["text"] for s in output).strip(),
            "model": "large-v3", "model_revision": self.settings.model_revision,
            "device": self.settings.device, "compute_type": self.settings.compute_type,
            "processing_seconds": time.monotonic() - started,
            "warnings": [] if output else ["no_speech_detected"]}


class Worker:
    def __init__(self, store: Store, settings: Settings, factory: Callable):
        self.store, self.settings, self.factory = store, settings, factory
        self.stop = threading.Event()
        self.ready = threading.Event()
        self.error = None
        self.thread = threading.Thread(target=self.run, daemon=True, name="transcription-worker")

    def run(self):
        try:
            engine = self.factory(self.settings)
            self.ready.set()
        except Exception:
            log.exception("Model initialization failed")
            self.error = "model_initialization_failed"
            return
        while not self.stop.is_set():
            job = self.store.claim()
            if job is None:
                self.stop.wait(0.25)
                continue
            log.info("Processing job %s", job["id"])
            try:
                result = engine.transcribe(self.store.directory / (job["id"] + ".media"),
                                           job["language"])
                self.store.update(job["id"], "completed", result=result)
            except Exception as exc:
                log.exception("Transcription failed for job %s", job["id"])
                # Keep traceback in operator logs, never expose file paths in API errors.
                self.store.update(job["id"], "failed", error="transcription_failed:" + type(exc).__name__)


class BodyLimit:
    """Bound multipart parsing as well as the final saved audio file."""
    def __init__(self, app, limit: int):
        self.app, self.limit = app, limit
        self.slots = asyncio.Semaphore(1)

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http" or scope.get("method") != "POST":
            return await self.app(scope, receive, send)
        total = 0
        exceeded = False
        async def bounded_receive():
            nonlocal total, exceeded
            message = await receive()
            total += len(message.get("body", b""))
            if total > self.limit:
                exceeded = True
                # Starlette closes all spooled files on this exception.
                raise MultiPartException("Upload exceeds configured limit")
            return message
        async def bounded_send(message):
            if exceeded:
                return
            await send(message)
        async with self.slots:
            await self.app(scope, bounded_receive, bounded_send)
        if exceeded:
            await JSONResponse({"detail": "Upload exceeds configured limit"}, status_code=413)(
                scope, receive, send)


def create_app(settings: Settings | None = None, engine_factory=WhisperEngine):
    settings = settings or Settings()

    @asynccontextmanager
    async def lifespan(app):
        settings.data_dir.mkdir(parents=True, exist_ok=True)
        lock = (settings.data_dir / "worker.lock").open("a")
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            store = Store(settings.data_dir)
            store.recover()
            worker = Worker(store, settings, engine_factory)
            app.state.store, app.state.worker = store, worker
            worker.thread.start()
            yield
        finally:
            if hasattr(app.state, "worker"):
                app.state.worker.stop.set()
                app.state.worker.thread.join()  # Finish current job before releasing ownership.
            lock.close()

    app = FastAPI(title="Shared transcription", version="1.0.0", lifespan=lifespan)
    app.add_middleware(BodyLimit, limit=settings.max_upload_bytes + 65536)

    @app.get("/health/live")
    def live():
        return {"status": "alive"}

    @app.get("/health/ready")
    def ready():
        worker = app.state.worker
        if not worker.ready.is_set() or not worker.thread.is_alive():
            raise HTTPException(503, worker.error or "model_loading")
        return {"status": "ready", "model": "large-v3", "device": settings.device,
                "compute_type": settings.compute_type}

    @app.post("/v1/transcriptions", status_code=202)
    async def submit(file: UploadFile = File(...), language: str | None = Form(None)):
        from faster_whisper.tokenizer import _LANGUAGE_CODES
        if language is not None and language not in _LANGUAGE_CODES:
            await file.close()
            raise HTTPException(422, "Use a supported Whisper language code or omit language")
        ready()
        store = app.state.store
        identifier = None
        try:
            identifier = store.reserve(language, settings.max_pending)
            part = store.directory / (identifier + ".part")
            size = 0
            with part.open("xb") as destination:
                while chunk := await file.read(1024 * 1024):
                    size += len(chunk)
                    if size > settings.max_upload_bytes:
                        raise HTTPException(413, "Audio file exceeds configured limit")
                    destination.write(chunk)
                destination.flush()
                os.fsync(destination.fileno())
            if size == 0:
                raise HTTPException(422, "Audio file is empty")
            part.replace(store.directory / (identifier + ".media"))
            store.update(identifier, "queued")
            return {"job_id": identifier, "status": "queued",
                    "status_url": "/v1/transcriptions/" + identifier}
        except BaseException:
            if identifier:
                store.update(identifier, "failed", error="upload_failed")
                (store.directory / (identifier + ".part")).unlink(missing_ok=True)
            raise
        finally:
            await file.close()

    @app.get("/v1/transcriptions/{job_id}")
    def retrieve(job_id: uuid.UUID):
        job = app.state.store.get(str(job_id))
        if job is None:
            raise HTTPException(404, "Unknown transcription job")
        job["job_id"] = job.pop("id")
        return job

    return app


app = create_app()
