"""Keep the Instagram token alive. Runs on Dominic's PC, never in the repo.

    python ig_token.py --new   # paste a fresh token from the Meta dashboard (first time, or if it lapsed)
    python ig_token.py         # refresh it (tokens die after 60 days unless refreshed)

Either way the token is saved outside the repo at ~/.bitty-beasts/ig_token and copied
into this repo's IG_TOKEN secret with the GitHub CLI.
"""
import getpass
import json
import subprocess
import sys
import urllib.parse
import urllib.request
from pathlib import Path

TOKEN_FILE = Path.home() / '.bitty-beasts' / 'ig_token'
GH = r'C:\Program Files\GitHub CLI\gh.exe'


def main():
    if '--new' in sys.argv:
        token = getpass.getpass('Paste the Instagram token (it will not show): ').strip()
    else:
        old = TOKEN_FILE.read_text().strip()
        q = urllib.parse.urlencode({'grant_type': 'ig_refresh_token', 'access_token': old})
        with urllib.request.urlopen(f'https://graph.instagram.com/refresh_access_token?{q}', timeout=60) as r:
            reply = json.load(r)
        token = reply['access_token']
        print(f'Refreshed, good for {reply["expires_in"] // 86400} more days.')
    TOKEN_FILE.parent.mkdir(exist_ok=True)
    TOKEN_FILE.write_text(token)
    subprocess.run([GH, 'secret', 'set', 'IG_TOKEN'], input=token, text=True, check=True,
                   cwd=Path(__file__).parent)
    print('Saved, and the IG_TOKEN secret on GitHub is updated.')


if __name__ == '__main__':
    main()
