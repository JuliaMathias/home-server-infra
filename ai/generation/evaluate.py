#!/usr/bin/env python3
"""Record sequential generation cases; do not equate successful requests with quality."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import time
import urllib.error
import urllib.parse
import urllib.request


def read_cases(path):
    """Validate uniquely identified source-grounded evaluation cases."""
    cases = json.loads(path.read_text())
    if not isinstance(cases, list) or not cases or len(cases) > 8:
        raise ValueError('Expected between one and eight cases')
    seen = set()
    for case in cases:
        case_id = case.get('id', '')
        if not case_id or any(c not in 'abcdefghijklmnopqrstuvwxyz0123456789_-' for c in case_id):
            raise ValueError('Invalid case ID')
        if case_id in seen:
            raise ValueError('Duplicate case ID')
        seen.add(case_id)
        messages = case.get('messages')
        if not isinstance(messages, list) or not messages:
            raise ValueError('Missing messages')
        for message in messages:
            if message.get('role') not in ('system', 'user', 'assistant'):
                raise ValueError('Invalid message role')
            if not isinstance(message.get('content'), str) or not message['content'].strip():
                raise ValueError('Missing message content')
        if not case.get('review_requirements'):
            raise ValueError('Missing human review requirements')
    return cases


def main():
    """Validate fixtures or record a bounded, sequential evaluation run."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cases', type=Path, default=Path(__file__).with_name('cases.json'))
    parser.add_argument('--validate-only', action='store_true')
    parser.add_argument('--endpoint')
    parser.add_argument('--model')
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    cases = read_cases(args.cases)
    if args.validate_only:
        print(f'Validated {len(cases)} cases; no inference requested.')
        return 0
    if not args.endpoint or not args.model or not args.output:
        parser.error('--endpoint, --model and --output are required for inference')
    endpoint = urllib.parse.urlparse(args.endpoint)
    if endpoint.scheme not in ('http', 'https') or not endpoint.hostname or endpoint.username or endpoint.password or endpoint.query or endpoint.fragment or endpoint.path not in ('', '/'):
        parser.error('--endpoint must be a base HTTP(S) URL without credentials, query or path')
    output = args.output.resolve()
    repository = Path(__file__).resolve().parents[2]
    if output == repository or repository in output.parents:
        parser.error('Run outputs must remain outside the infrastructure checkout')
    output.mkdir(parents=True, exist_ok=False)
    summary = {'started_at': datetime.now(timezone.utc).isoformat(), 'endpoint': args.endpoint,
               'model': args.model, 'quality_review': 'pending', 'cases': [],
               'limitations': ['Non-streaming wall time only; no TTFT', 'Collect hardware telemetry separately',
                               'Successful requests are not evidence of source fidelity']}
    for case in cases:
        request = {'model': args.model, 'messages': case['messages'], 'stream': False,
                   'max_tokens': 768, 'temperature': 0.7, 'top_p': 0.8, 'seed': 42}
        record = {'case': case, 'request': request, 'started_at': datetime.now(timezone.utc).isoformat()}
        started = time.monotonic()
        http_request = urllib.request.Request(args.endpoint.rstrip('/') + '/v1/chat/completions',
                    data=json.dumps(request).encode(), headers={'Content-Type': 'application/json'})
        try:
            with urllib.request.urlopen(http_request, timeout=900) as response:
                raw = response.read(8 * 1024 * 1024 + 1)
            if len(raw) > 8 * 1024 * 1024:
                raise ValueError('Response exceeded 8 MiB')
            result = json.loads(raw)
            record['response'] = result
            choice = result['choices'][0]
            if not isinstance(choice['message']['content'], str) or not choice['message']['content'].strip():
                raise ValueError('Missing generated content')
            if choice.get('finish_reason') != 'stop':
                raise ValueError('Generation did not finish normally; inspect truncation or runtime behavior')
            record['status'] = 'completed_pending_human_review'
        except (urllib.error.URLError, TimeoutError, ValueError, KeyError, IndexError, TypeError) as error:
            record['status'] = 'failed'
            record['error'] = f'{type(error).__name__}: {error}'
        record['wall_seconds'] = time.monotonic() - started
        (output / (case['id'] + '.json')).write_text(json.dumps(record, ensure_ascii=False, indent=2) + '\n')
        summary['cases'].append({'id': case['id'], 'status': record['status'], 'wall_seconds': record['wall_seconds']})
        print(f"{case['id']}: {record['status']} ({record['wall_seconds']:.2f}s)", flush=True)
    summary['finished_at'] = datetime.now(timezone.utc).isoformat()
    (output / 'summary.json').write_text(json.dumps(summary, indent=2) + '\n')
    return int(any(case['status'] == 'failed' for case in summary['cases']))


if __name__ == '__main__':
    raise SystemExit(main())
