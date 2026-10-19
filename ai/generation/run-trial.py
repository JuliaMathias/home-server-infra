"""Run a single private, bounded CPU generation trial with host telemetry."""
import argparse
from datetime import datetime, timezone
import fcntl
import json
import os
from pathlib import Path
import subprocess
import threading
import time
import urllib.request

ROOT = Path(__file__).resolve().parent


def now():
    """Return an explicit UTC timestamp for machine-readable evidence."""
    return datetime.now(timezone.utc).isoformat()


def command(args, **kwargs):
    """Run a bounded host operation and capture its output without shell expansion."""
    return subprocess.check_output(args, text=True, timeout=30, **kwargs)


def telemetry(path, stop):
    """Sample temperatures, available RAM, throttle counters and container RAM."""
    with path.open('a') as output:
        while not stop.is_set():
            sample = {'at': now()}
            try:
                sample['temperatures_millidegrees'] = {str(p): int(p.read_text()) for p in Path('/sys/class/hwmon').glob('hwmon*/temp*_input')}
                sample['cpu_package_throttle_counts'] = {str(p): int(p.read_text()) for p in Path('/sys/devices/system/cpu').glob('cpu[0-9]*/thermal_throttle/package_throttle_count')}
                sample['mem_available_kib'] = int(next(line.split()[1] for line in Path('/proc/meminfo').read_text().splitlines() if line.startswith('MemAvailable:')))
                sample['gpu_csv'] = command(['nvidia-smi','--query-gpu=temperature.gpu,memory.used,utilization.gpu','--format=csv,noheader,nounits']).strip()
                sample['container_memory'] = command(['docker','stats','--no-stream','--format','{{.MemUsage}}','shared-generation-trial-generation-1'],stderr=subprocess.DEVNULL).strip()
            except Exception as error:
                sample['monitor_error'] = f'{type(error).__name__}: {error}'
            output.write(json.dumps(sample) + '\n'); output.flush()
            stop.wait(5)


def main():
    """Wait for verified weights, run evaluation cases once, and release trial RAM."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-dir', type=Path, required=True)
    parser.add_argument('--private-cases', type=Path)
    args = parser.parse_args()
    run = args.run_dir.resolve()
    repository = ROOT.parents[1]
    if run == repository or repository in run.parents:
        parser.error('Private run directory must be outside Git')
    run.mkdir(parents=True, exist_ok=True)
    lock = (run / 'trial.lock').open('a')
    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    status_file = run / 'status.json'
    if status_file.exists():
        raise RuntimeError('Trial already has a status record; use a new run directory')
    status = {'started_at': now(), 'state': 'waiting_for_verified_model', 'quality_review': 'pending', 'device': 'cpu'}
    def state(value, **fields):
        status.update(state=value, updated_at=now(), **fields)
        temporary = status_file.with_suffix('.tmp')
        temporary.write_text(json.dumps(status, indent=2) + '\n'); temporary.replace(status_file)
    state('waiting_for_verified_model')
    stop = threading.Event()
    monitor = None
    started_container = False
    compose = ['docker','compose','-f',str(ROOT / 'compose.yaml')]
    env = dict(os.environ)
    try:
        env['GENERATION_IMAGE'] = (ROOT / 'runtime-image.txt').read_text().strip()
        if '@sha256:' not in env['GENERATION_IMAGE']:
            raise ValueError('Runtime must be pinned by immutable digest')
        candidate = json.loads((ROOT / 'candidate.json').read_text())
        model_dir = Path('/srv/lara/ai/models/qwen3-14b')
        deadline = time.monotonic() + 7200
        while not (model_dir / 'source-manifest.json').exists():
            if time.monotonic() > deadline:
                raise TimeoutError('Verified model download not ready within two hours')
            with (model_dir / '.download.lock').open('a') as download_lock:
                try:
                    fcntl.flock(download_lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
                    raise RuntimeError('Downloader stopped before producing verified manifest; inspect download.log')
                except BlockingIOError:
                    pass
            time.sleep(10)
        manifest = json.loads((model_dir / 'source-manifest.json').read_text())
        if manifest != candidate or (model_dir / candidate['filename']).stat().st_size != candidate['bytes']:
            raise ValueError('Verified model manifest or file size differs from candidate')
        (run / 'candidate.json').write_text(json.dumps(candidate, indent=2) + '\n')
        (run / 'runtime-image.txt').write_text(env['GENERATION_IMAGE'] + '\n')
        command(compose + ['config','--quiet'], env=env)
        state('waiting_for_runtime_image')
        image_deadline = time.monotonic() + 900
        while time.monotonic() < image_deadline:
            try:
                command(['docker','image','inspect',env['GENERATION_IMAGE']],stderr=subprocess.DEVNULL)
                break
            except subprocess.CalledProcessError:
                time.sleep(10)
        else:
            raise TimeoutError('Official runtime pull did not finish within 15 minutes')
        help_text = command(['docker','run','--rm','--network','none',env['GENERATION_IMAGE'],'--help'])
        for flag in ['--chat-template-kwargs','--no-context-shift','--parallel','--n-gpu-layers']:
            if flag not in help_text:
                raise ValueError('Pinned runtime lacks required option: '+flag)
        (run / 'runtime-help.txt').write_text(help_text)
        monitor = threading.Thread(target=telemetry, args=(run / 'telemetry.jsonl',stop), daemon=True)
        monitor.start()
        state('loading_model')
        load_start = time.monotonic()
        started_container = True
        command(compose + ['up','-d','--pull','never'], env=env)
        endpoint = None
        deadline = time.monotonic() + 900
        while time.monotonic() < deadline:
            info = json.loads(command(['docker','inspect','shared-generation-trial-generation-1']))[0]
            if not info['State']['Running']:
                raise RuntimeError('Generation container stopped during model load; inspect server.log')
            address = info['NetworkSettings']['Networks']['lara-backend']['IPAddress']
            endpoint = f'http://{address}:8080'
            try:
                with urllib.request.urlopen(endpoint + '/health', timeout=3) as response:
                    if response.status == 200:
                        break
            except Exception:
                time.sleep(5)
        else:
            raise TimeoutError('Generation model did not become ready within 15 minutes')
        state('evaluating_synthetic_cases', model_load_and_warmup_seconds=time.monotonic()-load_start)
        with (run / 'client.log').open('a') as log:
            subprocess.run(['python3',str(ROOT / 'evaluate.py'),'--endpoint',endpoint,'--model','qwen3-14b-trial','--output',str(run / 'synthetic')],stdout=log,stderr=log,check=True,timeout=1900)
            if args.private_cases:
                state('generating_private_excerpt_draft')
                subprocess.run(['python3',str(ROOT / 'evaluate.py'),'--endpoint',endpoint,'--model','qwen3-14b-trial','--cases',str(args.private_cases.resolve()),'--output',str(run / 'private')],stdout=log,stderr=log,check=True,timeout=1000)
                for item in (run / 'private').glob('*.json'):
                    record=json.loads(item.read_text())
                    if 'response' in record:
                        content=record['response']['choices'][0]['message']['content']
                        item.with_suffix('.md').write_text('# Preliminary notes from a reviewed excerpt\n\nThis draft covers only the supplied excerpt. Source fidelity is pending review.\n\n'+content+'\n')
        state('completed_pending_review', finished_at=now())
    except Exception as error:
        state('failed', error=f'{type(error).__name__}: {error}', finished_at=now())
        raise
    finally:
        if started_container:
            try:
                (run / 'server.log').write_text(command(compose + ['logs','--no-color'], env=env))
                command(compose + ['stop'], env=env)
            except Exception as error:
                status['cleanup_error'] = str(error)
                state('failed', error='Trial cleanup failed; inspect container before retrying')
        stop.set()
        if monitor:
            monitor.join(timeout=15)
        lock.close()


if __name__ == '__main__':
    main()
