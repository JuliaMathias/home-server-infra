import threading
import time
from concurrent.futures import ThreadPoolExecutor

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from service import Settings, Store, create_app


class FakeEngine:
    def __init__(self, settings):
        pass

    def transcribe(self, path, language):
        assert path.read_bytes() == b'audio'
        return {'language': language, 'segments': [{'start': 0, 'end': 1, 'text': 'test'}]}


def wait_for(client, identifier, status='completed'):
    for _ in range(100):
        job = client.get('/v1/transcriptions/' + identifier).json()
        if job['status'] == status:
            return job
        time.sleep(.02)
    raise AssertionError(job)


def wait_ready(client):
    for _ in range(100):
        if client.get('/health/ready').status_code == 200:
            return
        time.sleep(.01)
    raise AssertionError('worker never became ready')


def test_full_lifecycle_and_persistence(tmp_path):
    settings = Settings(data_dir=tmp_path)
    with TestClient(create_app(settings, FakeEngine)) as client:
        wait_ready(client)
        response = client.post('/v1/transcriptions', files={'file': ('../../unsafe.wav', b'audio')}, data={'language':'pt'})
        assert response.status_code == 202
        identifier = response.json()['job_id']
        job = wait_for(client, identifier)
        assert job['result']['language'] == 'pt'
        assert (tmp_path / (identifier + '.media')).read_bytes() == b'audio'
        assert not (tmp_path.parent / 'unsafe.wav').exists()
    with TestClient(create_app(settings, FakeEngine)) as client:
        assert client.get('/v1/transcriptions/' + identifier).json()['status'] == 'completed'


def test_invalid_inputs_and_missing_jobs(tmp_path):
    with TestClient(create_app(Settings(data_dir=tmp_path), FakeEngine)) as client:
        wait_ready(client)
        assert client.post('/v1/transcriptions', files={'file': ('a', b'audio')}, data={'language':'invalid'}).status_code == 422
        assert client.post('/v1/transcriptions', files={'file': ('a', b'')}).status_code == 422
        assert client.get('/v1/transcriptions/00000000-0000-0000-0000-000000000000').status_code == 404
        assert client.get('/v1/transcriptions/not-a-uuid').status_code == 422
        assert not list(tmp_path.glob('*.part'))


def test_size_limit_including_chunked_multipart(tmp_path):
    with TestClient(create_app(Settings(data_dir=tmp_path, max_upload_bytes=10), FakeEngine)) as client:
        wait_ready(client)
        assert client.post('/v1/transcriptions', files={'file': ('a', b'a' * 11)}).status_code == 413
        boundary = b'--test\r\nContent-Disposition: form-data; name="file"; filename="a.wav"\r\nContent-Type: audio/wav\r\n\r\n'
        chunks = iter([boundary, b'a' * 70000, b'\r\n--test--\r\n'])
        response = client.post('/v1/transcriptions', content=chunks, headers={'Content-Type':'multipart/form-data; boundary=test'})
        assert response.status_code == 413
        assert not list(tmp_path.glob('*.part'))


def test_bounded_queue_atomic_under_concurrency(tmp_path):
    store = Store(tmp_path)
    def reserve(_):
        try:
            return store.reserve(None, 2)
        except HTTPException as exc:
            assert exc.status_code == 429
            return None
    with ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(reserve, range(12)))
    assert len([item for item in results if item]) == 2


def test_restart_fails_interrupted_preserves_queued(tmp_path):
    store = Store(tmp_path)
    uploading = store.reserve(None, 5)
    running = store.reserve(None, 5)
    queued = store.reserve(None, 5)
    store.update(running, 'running')
    store.update(queued, 'queued')
    (tmp_path / (uploading + '.part')).write_bytes(b'incomplete')
    store.recover()
    assert store.get(uploading)['status'] == 'failed'
    assert store.get(running)['error'].startswith('service_restarted')
    assert not list(tmp_path.glob('*.part'))
    assert store.claim()['id'] == queued


def test_inference_error_is_persisted(tmp_path):
    class BrokenEngine(FakeEngine):
        def transcribe(self, path, language):
            raise ValueError('private/path')
    with TestClient(create_app(Settings(data_dir=tmp_path), BrokenEngine)) as client:
        wait_ready(client)
        response = client.post('/v1/transcriptions', files={'file': ('a', b'audio')})
        job = wait_for(client, response.json()['job_id'], 'failed')
        assert job['error'] == 'transcription_failed:ValueError'
        assert 'private/path' not in str(job)


def test_loading_failure_rejects_submission(tmp_path):
    def broken(settings):
        raise RuntimeError('missing model')
    with TestClient(create_app(Settings(data_dir=tmp_path), broken)) as client:
        assert client.get('/health/ready').status_code == 503
        assert client.get('/health/live').status_code == 200
        assert client.post('/v1/transcriptions', files={'file': ('a', b'audio')}).status_code == 503


def test_second_worker_cannot_own_same_database(tmp_path):
    settings = Settings(data_dir=tmp_path)
    with TestClient(create_app(settings, FakeEngine)):
        with pytest.raises(BlockingIOError):
            with TestClient(create_app(settings, FakeEngine)):
                pass


def test_queue_full_via_api_and_one_active_inference(tmp_path):
    entered, release = threading.Event(), threading.Event()
    class SlowEngine(FakeEngine):
        def transcribe(self, path, language):
            entered.set()
            assert release.wait(5)
            return super().transcribe(path, language)
    try:
        with TestClient(create_app(Settings(data_dir=tmp_path, max_pending=1), SlowEngine)) as client:
            wait_ready(client)
            first = client.post('/v1/transcriptions', files={'file': ('a', b'audio')})
            assert first.status_code == 202
            assert entered.wait(2)
            assert client.post('/v1/transcriptions', files={'file': ('b', b'audio')}).status_code == 429
            release.set()
            wait_for(client, first.json()['job_id'])
    finally:
        release.set()


def test_real_audio_decoder_dependency_compatibility(tmp_path):
    import wave
    from faster_whisper.audio import decode_audio
    path = tmp_path / 'sample.wav'
    with wave.open(str(path), 'wb') as audio:
        audio.setnchannels(1)
        audio.setsampwidth(2)
        audio.setframerate(16000)
        audio.writeframes(b'\0' * 32000)
    decoded = decode_audio(str(path))
    assert len(decoded) == 16000
    assert decoded.max() == 0
