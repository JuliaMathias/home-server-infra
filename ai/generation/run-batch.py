"""Execute private structured generation tasks sequentially with explicit resource bounds."""
import argparse
import json
from pathlib import Path
import time

import runtime_session
from runtime_session import helpers, request  # noqa: F401  (request kept for private wrappers)

ROOT = Path(__file__).resolve().parent


def runtime_reasoning_settings(mode, budget):
    """Return explicit runtime controls for a bounded thinking experiment.

    Default/off requests retain no-thinking behavior. The budget includes only
    the reasoning allowance; total response tokens remain separately bounded.
    """
    if mode not in ('off', 'on'):
        raise ValueError('Reasoning mode must be off or on')
    if type(budget) is not int or not 0 <= budget <= 2048:
        raise ValueError('Reasoning budget must be between zero and 2048 tokens')
    return {'GENERATION_REASONING':mode,
            'GENERATION_REASONING_BUDGET':str(budget if mode == 'on' else 0)}


def response_token_limit(value):
    """Validate a finite total-response ceiling before any model/container work.

    Reasoning and visible content share this ceiling. Explicit larger experiments
    may use 4096 tokens; the existing per-case default remains 2048.
    """
    if type(value) is not int or not 128 <= value <= 4096:
        raise ValueError('Output token bound must be an integer between 128 and 4096')
    return value


def main():
    """Run a bounded private batch once; preserve failures and stop its container."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-dir', type=Path, required=True)
    parser.add_argument('--cases', type=Path, required=True)
    parser.add_argument('--candidate', type=Path, default=ROOT/'candidate.json')
    parser.add_argument('--reasoning', choices=['off','on'], default='off')
    parser.add_argument('--reasoning-budget', type=int, default=256)
    parser.add_argument('--context', type=int, choices=runtime_session.CONTEXT_SIZES, default=8192)
    parser.add_argument('--gpu-layers', default='0', help="0 (CPU-only, default), auto, or a layer count")
    parser.add_argument('--memory-gib', type=int, default=16)
    args = parser.parse_args()
    reasoning_env = runtime_reasoning_settings(args.reasoning, args.reasoning_budget)
    device = runtime_session.device_settings(args.gpu_layers, args.memory_gib)
    run = args.run_dir.resolve()
    if run == ROOT.parents[1] or ROOT.parents[1] in run.parents:
        parser.error('Outputs must stay outside Git')
    cases = json.loads(args.cases.read_text())
    if not isinstance(cases,list) or not 1 <= len(cases) <= 32:
        raise ValueError('Expected one to 32 tasks')
    ids = set()
    output_limits = []
    for case in cases:
        case_id=case['id']
        if not case_id or any(c not in 'abcdefghijklmnopqrstuvwxyz0123456789_-' for c in case_id) or case_id in ids:
            raise ValueError('Invalid or duplicate task ID')
        ids.add(case_id)
        output_limits.append(response_token_limit(case.get('max_tokens',2048)))
    run.mkdir(parents=True,exist_ok=True)
    status_path=run/'status.json'
    if status_path.exists():
        raise RuntimeError('Existing run must not be restarted automatically')
    status={'started_at':helpers.now(),'state':'preparing','total_tasks':len(cases),'completed_tasks':0,'quality_review':'pending','device':device['device'],'gpu_layers':device['env']['GENERATION_GPU_LAYERS'],'memory_limit':device['env']['GENERATION_MEMORY_LIMIT'],'context_tokens':args.context,'reasoning':args.reasoning,'reasoning_token_budget':int(reasoning_env['GENERATION_REASONING_BUDGET'])}
    def state(value,**fields):
        status.update(state=value,updated_at=helpers.now(),**fields)
        p=status_path.with_suffix('.tmp');p.write_text(json.dumps(status,indent=2)+'\n');p.replace(status_path)
    try:
        state('loading_model')
        with runtime_session.runtime(run, args.candidate, args.context, max(output_limits), reasoning_env, device) as session:
            endpoint, model_alias = session['endpoint'], session['alias']
            state('generating',model_load_and_warmup_seconds=session['load_seconds'])
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


if __name__=='__main__':
    main()
