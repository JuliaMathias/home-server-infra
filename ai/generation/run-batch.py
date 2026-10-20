"""Execute private structured generation tasks sequentially with explicit resource bounds."""
import argparse
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


def request(endpoint, path, payload, timeout=30):
    """Post a local inference request and decode a bounded JSON response."""
    req = urllib.request.Request(endpoint + path, data=json.dumps(payload).encode(), headers={'Content-Type':'application/json'})
    with urllib.request.urlopen(req, timeout=timeout) as response:
        raw = response.read(8 * 1024 * 1024 + 1)
    if len(raw) > 8 * 1024 * 1024:
        raise ValueError('Response exceeds 8 MiB')
    return json.loads(raw)


def main():
    """Run a bounded private batch once; preserve failures and stop its container."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-dir', type=Path, required=True)
    parser.add_argument('--cases', type=Path, required=True)
    parser.add_argument('--candidate', type=Path, default=ROOT/'candidate.json')
    parser.add_argument('--context', type=int, choices=[4096,8192], default=8192)
    args = parser.parse_args()
    run = args.run_dir.resolve()
    if run == ROOT.parents[1] or ROOT.parents[1] in run.parents:
        parser.error('Outputs must stay outside Git')
    cases = json.loads(args.cases.read_text())
    if not isinstance(cases,list) or not 1 <= len(cases) <= 32:
        raise ValueError('Expected one to 32 tasks')
    ids = set()
    for case in cases:
        case_id=case['id']
        if not case_id or any(c not in 'abcdefghijklmnopqrstuvwxyz0123456789_-' for c in case_id) or case_id in ids:
            raise ValueError('Invalid or duplicate task ID')
        ids.add(case_id)
        if not 128 <= case.get('max_tokens',2048) <= 2048:
            raise ValueError('Invalid output token bound')
    run.mkdir(parents=True,exist_ok=True)
    lock = Path('/srv/lara/ai/data/generation-batch.lock').open('a')
    fcntl.flock(lock,fcntl.LOCK_EX | fcntl.LOCK_NB)
    status_path=run/'status.json'
    if status_path.exists():
        raise RuntimeError('Existing run must not be restarted automatically')
    status={'started_at':helpers.now(),'state':'preparing','total_tasks':len(cases),'completed_tasks':0,'quality_review':'pending','device':'cpu','context_tokens':args.context}
    def state(value,**fields):
        status.update(state=value,updated_at=helpers.now(),**fields)
        p=status_path.with_suffix('.tmp');p.write_text(json.dumps(status,indent=2)+'\n');p.replace(status_path)
    env=dict(os.environ,GENERATION_IMAGE=(ROOT/'runtime-image.txt').read_text().strip(),GENERATION_CONTEXT_SIZE=str(args.context),GENERATION_OUTPUT_LIMIT='2048')
    compose=['docker','compose','-f',str(ROOT/'compose.yaml')]
    stop=threading.Event();monitor=None;started=False
    try:
        state('preparing')
        inspected=subprocess.run(['docker','inspect','shared-generation-trial-generation-1'],capture_output=True,text=True,timeout=30)
        if inspected.returncode and 'No such object' not in inspected.stderr:
            raise RuntimeError('Cannot inspect generation container: '+inspected.stderr.strip())
        old=json.loads(inspected.stdout)[0] if inspected.returncode==0 else None
        if old and old['State']['Running']:
            raise RuntimeError('Generation container already running; do not replace another workload')
        candidate, model, container_model_path, model_alias = candidate_settings(args.candidate)
        env.update(GENERATION_MODEL_PATH=container_model_path, GENERATION_MODEL_ALIAS=model_alias)
        (run/'candidate.json').write_text(json.dumps(candidate,indent=2)+'\n')
        manifest=json.loads((model/'source-manifest.json').read_text())
        if any(candidate[k]!=manifest[k] for k in ('repository','revision','filename','bytes','sha256')) or (model/candidate['filename']).stat().st_size!=candidate['bytes']:
            raise ValueError('Verified model identity mismatch')
        (run/'runtime-config.yaml').write_text(helpers.command(compose+['config'],env=env))
        (run/'runtime-image.txt').write_text(env['GENERATION_IMAGE']+'\n')
        monitor=threading.Thread(target=helpers.telemetry,args=(run/'telemetry.jsonl',stop),daemon=True);monitor.start()
        state('loading_model');t=time.monotonic();started=True
        helpers.command(compose+['up','-d','--pull','never'],env=env)
        deadline=time.monotonic()+900
        while time.monotonic()<deadline:
            info=json.loads(helpers.command(['docker','inspect','shared-generation-trial-generation-1']))[0]
            if not info['State']['Running']: raise RuntimeError('Container stopped during load')
            endpoint='http://'+info['NetworkSettings']['Networks']['lara-backend']['IPAddress']+':8080'
            try:
                with urllib.request.urlopen(endpoint+'/health',timeout=3) as response:
                    if response.status==200: break
            except Exception: time.sleep(5)
        else: raise TimeoutError('Model readiness timeout')
        state('generating',model_load_and_warmup_seconds=time.monotonic()-t)
        for index,case in enumerate(cases):
            state('generating',active_task=case['id'])
            record={'task':case,'started_at':helpers.now()};t=time.monotonic()
            try:
                rendered=request(endpoint,'/apply-template',{'messages':case['messages']})['prompt']
                token_count=len(request(endpoint,'/tokenize',{'content':rendered,'add_special':True})['tokens'])
                record['prompt_token_preflight']=token_count
                if token_count+case.get('max_tokens',2048)+64>args.context:
                    raise ValueError('Input plus output exceeds context; no automatic truncation')
                payload={'model':model_alias,'messages':case['messages'],'stream':False,'max_tokens':case.get('max_tokens',2048),'temperature':0.7,'top_p':0.8,'seed':42,'response_format':{'type':'json_object','schema':case['schema']}}
                record['request']=payload
                response=request(endpoint,'/v1/chat/completions',payload,timeout=1800)
                record['response']=response
                if response['choices'][0]['finish_reason']!='stop': raise ValueError('Truncated generation; output not accepted')
                parsed=json.loads(response['choices'][0]['message']['content']);record['parsed']=parsed
                if case.get('source_ids'):
                    allowed=set(case['source_ids'])
                    for paragraph in parsed.get('paragraphs',[]):
                        if not paragraph.get('sources') or not set(paragraph['sources'])<=allowed:
                            raise ValueError('Unknown or missing source identifier')
                record['status']='completed_pending_review'
            except Exception as error:
                record.update(status='failed',error=f'{type(error).__name__}: {error}')
                raise
            finally:
                record['wall_seconds']=time.monotonic()-t
                (run/(case['id']+'.json')).write_text(json.dumps(record,ensure_ascii=False,indent=2)+'\n')
            state('generating',completed_tasks=index+1)
        state('completed_pending_review',finished_at=helpers.now(),active_task=None)
    except Exception as error:
        state('failed',error=f'{type(error).__name__}: {error}',finished_at=helpers.now());raise
    finally:
        if started:
            try:
                (run/'server.log').write_text(helpers.command(compose+['logs','--no-color'],env=env))
                helpers.command(compose+['stop'],env=env)
            except Exception as error:
                state('failed',cleanup_error=str(error))
        stop.set()
        if monitor: monitor.join(timeout=15)
        lock.close()


if __name__=='__main__':
    main()
