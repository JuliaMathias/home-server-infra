"""Start, monitor and stop one bounded generation runtime for private evaluations.

Shared by the sequential batch runner and by multi-step private evaluation
workflows that need dependent requests against one loaded model. This module
owns the Compose invocation, device placement and GPU preconditions, model
identity verification, readiness, telemetry and cleanup. Callers own prompts,
outputs and evaluation logic, which stay outside Git with the run directory.
"""
import contextlib
import fcntl
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import threading
import time
import urllib.request

from candidate_config import candidate_settings

ROOT = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('trial_helpers', ROOT / 'run-trial.py')
helpers = importlib.util.module_from_spec(spec)
spec.loader.exec_module(helpers)

CONTAINER = 'shared-generation-trial-generation-1'
TRANSCRIPTION_CONTAINER = 'shared-transcription-transcription-1'
CONTEXT_SIZES = (4096, 8192, 16384, 32768)
LOCK_PATH = Path('/srv/lara/ai/data/generation-batch.lock')


def request(endpoint, path, payload, timeout=30):
    """Post a local inference request and decode a bounded JSON response."""
    req = urllib.request.Request(endpoint + path, data=json.dumps(payload).encode(), headers={'Content-Type':'application/json'})
    with urllib.request.urlopen(req, timeout=timeout) as response:
        raw = response.read(8 * 1024 * 1024 + 1)
    if len(raw) > 8 * 1024 * 1024:
        raise ValueError('Response exceeds 8 MiB')
    return json.loads(raw)


def device_settings(gpu_layers, memory_gib, root=ROOT):
    """Validate device placement and memory cap; return Compose files and env.

    `gpu_layers` 0 keeps the original CPU-only image with no GPU access. `auto`
    or a positive layer count selects the pinned CUDA image of the same llama.cpp
    build plus the GPU override; `auto` lets the runtime's --fit place layers
    (and MoE experts) within device memory. The memory cap bounds host RAM.
    """
    if gpu_layers in (0, '0'):
        device, image_file, files = 'cpu', 'runtime-image.txt', ['compose.yaml']
        layers = '0'
    elif gpu_layers == 'auto' or (type(gpu_layers) is int and 1 <= gpu_layers <= 200) or (isinstance(gpu_layers, str) and gpu_layers.isdigit() and 1 <= int(gpu_layers) <= 200):
        device, image_file, files = 'gpu', 'runtime-image-cuda.txt', ['compose.yaml', 'compose.gpu.yaml']
        layers = str(gpu_layers)
    else:
        raise ValueError('GPU layers must be 0, auto or an integer between 1 and 200')
    if type(memory_gib) is not int or not 4 <= memory_gib <= 28:
        raise ValueError('Memory cap must be an integer between 4 and 28 GiB')
    compose = ['docker', 'compose']
    for name in files:
        compose += ['-f', str(root / name)]
    env = {'GENERATION_IMAGE': (root / image_file).read_text().strip(),
           'GENERATION_GPU_LAYERS': layers,
           'GENERATION_MEMORY_LIMIT': f'{memory_gib}g'}
    return {'device': device, 'compose': compose, 'env': env}


def inspect_container(name):
    """Return (returncode, stdout, stderr) of `docker inspect` without raising."""
    result = subprocess.run(['docker', 'inspect', name], capture_output=True, text=True, timeout=30)
    return result.returncode, result.stdout, result.stderr


def container_running(name, inspect=inspect_container):
    """Report whether a named container is running; a missing container is not."""
    code, stdout, stderr = inspect(name)
    if code:
        if 'No such object' in stderr:
            return False
        raise RuntimeError(f'Cannot inspect {name}: ' + stderr.strip())
    return bool(json.loads(stdout)[0]['State']['Running'])


def ensure_gpu_available(inspect=inspect_container):
    """Refuse GPU generation while Whisper holds VRAM on the 4 GB card.

    Sequencing is deliberately manual: the operator stops transcription before a
    GPU evaluation and restarts it afterwards. Nothing here stops shared services.
    """
    if container_running(TRANSCRIPTION_CONTAINER, inspect):
        raise RuntimeError('Transcription is running and holds GPU memory; stop it explicitly '
                           '(docker compose -f ai/transcription/compose.yaml stop) before a GPU run')


@contextlib.contextmanager
def runtime(run, candidate_path, context, output_limit, reasoning_env, device):
    """Hold one loaded generation runtime for the duration of a `with` block.

    Writes candidate, resolved runtime configuration, image, telemetry and server
    log evidence into `run`. Yields endpoint, alias and load time. Always stops
    the container it started; never replaces another running workload.
    """
    if context not in CONTEXT_SIZES:
        raise ValueError('Unsupported context size')
    lock = LOCK_PATH.open('a')
    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    compose = device['compose']
    env = dict(os.environ, GENERATION_CONTEXT_SIZE=str(context), GENERATION_OUTPUT_LIMIT=str(output_limit), **device['env'], **reasoning_env)
    stop = threading.Event(); monitor = None; started = False
    try:
        if container_running(CONTAINER):
            raise RuntimeError('Generation container already running; do not replace another workload')
        if device['device'] == 'gpu':
            ensure_gpu_available()
        candidate, model, container_model_path, model_alias = candidate_settings(candidate_path)
        env.update(GENERATION_MODEL_PATH=container_model_path, GENERATION_MODEL_ALIAS=model_alias)
        (run/'candidate.json').write_text(json.dumps(candidate, indent=2)+'\n')
        manifest = json.loads((model/'source-manifest.json').read_text())
        if any(candidate[k] != manifest[k] for k in ('repository','revision','filename','bytes','sha256')) or (model/candidate['filename']).stat().st_size != candidate['bytes']:
            raise ValueError('Verified model identity mismatch')
        (run/'runtime-config.yaml').write_text(helpers.command(compose+['config'], env=env))
        (run/'runtime-image.txt').write_text(env['GENERATION_IMAGE']+'\n')
        monitor = threading.Thread(target=helpers.telemetry, args=(run/'telemetry.jsonl', stop), daemon=True); monitor.start()
        t = time.monotonic(); started = True
        helpers.command(compose+['up','-d','--pull','never'], env=env)
        deadline = time.monotonic()+900
        while time.monotonic() < deadline:
            info = json.loads(helpers.command(['docker','inspect',CONTAINER]))[0]
            if not info['State']['Running']:
                raise RuntimeError('Container stopped during load')
            endpoint = 'http://'+info['NetworkSettings']['Networks']['lara-backend']['IPAddress']+':8080'
            try:
                with urllib.request.urlopen(endpoint+'/health', timeout=3) as response:
                    if response.status == 200:
                        break
            except Exception:
                time.sleep(5)
        else:
            raise TimeoutError('Model readiness timeout')
        yield {'endpoint': endpoint, 'alias': model_alias, 'load_seconds': time.monotonic()-t}
    finally:
        try:
            if started:
                (run/'server.log').write_text(helpers.command(compose+['logs','--no-color'], env=env))
                helpers.command(compose+['stop'], env=env)
        finally:
            stop.set()
            if monitor:
                monitor.join(timeout=15)
            lock.close()
