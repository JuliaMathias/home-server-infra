"""Opt-in real GPU/API checks; run with private network and fixture mounts."""
import json
import time
from pathlib import Path

import httpx

base = 'http://transcription:8000'
results = []
with httpx.Client(base_url=base, timeout=60) as client:
    client.get('/health/ready').raise_for_status()
    for name, language, expected in [('jfk.flac', 'en', 'ask not'),
                                     ('portuguese.wav', 'pt', 'palavra'),
                                     ('silence.wav', 'pt', None),
                                     ('corrupt.wav', 'en', None)]:
        started = time.monotonic()
        with (Path('/fixtures') / name).open('rb') as source:
            response = client.post('/v1/transcriptions', files={'file': (name, source)},
                                   data={'language': language})
        assert response.status_code == 202, response.text
        identifier = response.json()['job_id']
        deadline = time.monotonic() + 600
        while time.monotonic() < deadline:
            response = client.get('/v1/transcriptions/' + identifier)
            response.raise_for_status()
            job = response.json()
            if job['status'] in ('completed', 'failed'):
                break
            time.sleep(1)
        else:
            raise AssertionError('Job timed out: ' + identifier)
        if name == 'corrupt.wav':
            assert job['status'] == 'failed', job['status']
        else:
            assert job['status'] == 'completed', job['error']
            result = job['result']
            assert result['device'] == 'cuda'
            assert result['compute_type'] == 'int8_float16'
            assert result['language'] == language
            if expected:
                assert expected in result['text'].lower(), 'Expected phrase missing from ' + name
                assert result['segments']
                for segment in result['segments']:
                    assert 0 <= segment['start'] <= segment['end'] <= result['duration_seconds'] + .1
            else:
                assert not result['segments']
                assert 'no_speech_detected' in result['warnings']
        summary = {'fixture': name, 'job_id': identifier, 'status': job['status'],
                   'wall_seconds': round(time.monotonic() - started, 2)}
        if job['result']:
            summary.update({key: job['result'][key] for key in
                            ['duration_seconds', 'processing_seconds', 'model_revision', 'device', 'compute_type']})
            summary['segment_count'] = len(job['result']['segments'])
        results.append(summary)
        print(json.dumps(summary), flush=True)
Path('/fixtures/smoke-results.json').write_text(json.dumps(results, indent=2) + '\n')
print('All real-inference smoke checks passed', flush=True)
