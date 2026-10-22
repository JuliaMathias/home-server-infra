"""Command entry point for a pinned version of Lara app delivery."""
import argparse
import json
import re
from pathlib import Path
import sys

from backup import require_recovery
from common import DeliveryError, private_text
from github_source import GitHubSource
from runtime import HookAdapter, Runner, app_lock


def main():
    """Run a single timer invocation; status is local and requires no credentials."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('operation', choices=['check', 'backup', 'status'])
    parser.add_argument('config')
    args = parser.parse_args()
    try:
        config = json.loads(private_text(args.config))
        if config.get('contract') != 1 or not re.fullmatch(r'[a-z][a-z0-9-]{0,62}', config.get('app', '')):
            raise DeliveryError('Unsupported app configuration')
        state = Path(config['state_dir'])
        with app_lock(state):
            adapter = HookAdapter(config['adapter'], args.config)
            runner = Runner(state, adapter)
            current = runner.ready() if args.operation != 'status' else runner.load('current')
            if current['app'] != config['app']:
                raise DeliveryError('Current state belongs to another application')
            if args.operation == 'status':
                transaction = runner.load('transaction') if (state / 'transaction.json').exists() else None
                print(json.dumps({'current_revision': current['revision'], 'transaction': transaction}))
            elif args.operation == 'backup':
                runner.daily_backup()
                print('Verified app backup completed')
            else:
                releases = state / 'releases'
                releases.mkdir(mode=0o700, exist_ok=True)
                require_recovery(config['backup'])
                try:
                    candidate = GitHubSource(config).candidate(current, releases)
                except Exception:
                    runner.record('select-release', 'failed')
                    raise
                if candidate:
                    runner.deploy(candidate)
                    print('App release activated: ' + candidate['revision'])
                else:
                    print('No eligible newer completed release')
        return 0
    except DeliveryError as error:
        print(str(error), file=sys.stderr)
        return 1
    except Exception:
        # API/config/child errors can contain tokens or interpolated credentials.
        print('Delivery operation failed; inspect private state and configuration', file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
