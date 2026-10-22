"""Download a verified ciphertext for recovery; never decrypt on Lara."""
import argparse
import json
from common import private_text
from drive import DriveStore


def main():
    """Save a new private ciphertext file without exposing account credentials."""
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('config'); parser.add_argument('backup_id'); parser.add_argument('destination')
    args=parser.parse_args()
    try:
        config=json.loads(private_text(args.config))
        DriveStore(config['backup']['credential_file']).download(args.backup_id,config['app'],args.destination)
        print('Verified encrypted backup downloaded; decryption requires the external recovery key.')
        return 0
    except Exception:
        print('Backup download failed; inspect the app configuration privately.')
        return 1


if __name__=='__main__':
    raise SystemExit(main())
