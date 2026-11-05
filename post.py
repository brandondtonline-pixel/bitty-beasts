"""Post the next approved reel(s) in queue.json to Instagram.

Runs in GitHub Actions (see .github/workflows/post.yml). Needs IG_TOKEN, the never-expiring
system-user token from the Bitty Beasts Poster app (Instagram API with Unified login, which
goes through graph.facebook.com). Videos are fetched by Instagram from this repo's GitHub Pages site.

    python post.py                       # post one
    python post.py 3                     # post three in a row (e.g. launch day)
    python post.py --check wombat-cubes  # dry run: Instagram fetches and processes it, nothing is published
"""
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

API = 'https://graph.facebook.com/v26.0'
IG_USER = '17841474780085138'   # @bitty_beasts
HERE = Path(__file__).parent
QUEUE = HERE / 'queue.json'


def call(method, path, **params):
    data = urllib.parse.urlencode(params)
    url = f'{API}/{path}' + (f'?{data}' if method == 'GET' else '')
    req = urllib.request.Request(url, data=None if method == 'GET' else data.encode(), method=method,
                                 headers={'Authorization': f'Bearer {os.environ["IG_TOKEN"]}'})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        sys.exit(f'{method} {path} failed ({e.code}): {e.read().decode()}')


def pages_url():
    owner, name = os.environ['GITHUB_REPOSITORY'].split('/')
    return f'https://{owner.lower()}.github.io/{name}'


def upload(name):
    """Hand Instagram the reel and wait until it has processed it. Returns the container id."""
    caption = (HERE / 'videos' / f'{name}.txt').read_text(encoding='utf-8').strip()
    box = call('POST', f'{IG_USER}/media', media_type='REELS', share_to_feed='true',
               video_url=f'{pages_url()}/videos/{name}.mp4', caption=caption)['id']
    # Meta suggests checking about once a minute; give slow days up to 10 minutes.
    for _ in range(20):
        time.sleep(30)
        status = call('GET', box, fields='status_code,status')
        if status['status_code'] == 'FINISHED':
            return box
        if status['status_code'] in ('ERROR', 'EXPIRED'):
            sys.exit(f'Instagram could not process {name}: {status}')
    sys.exit(f'Instagram was still processing {name} after 10 minutes')


def post(name):
    return call('POST', f'{IG_USER}/media_publish', creation_id=upload(name))['id']


def main():
    if not os.environ.get('IG_TOKEN'):
        print('::warning::No IG_TOKEN secret yet, so nothing was posted.')
        return
    if sys.argv[1:2] == ['--check']:
        upload(sys.argv[2])
        print(f'{sys.argv[2]} processed fine (not published; the unused upload expires in 24 hours)')
        return
    count = int(sys.argv[1]) if len(sys.argv) > 1 else 1
    queue = json.loads(QUEUE.read_text(encoding='utf-8'))
    if os.environ.get('GITHUB_EVENT_NAME') in ('schedule', 'push'):
        # The evening trigger and GitHub's late backup run both land here; if a reel already went
        # up in the last 20 hours (or was posted by hand), skip so two don't land on the same evening.
        last = max((datetime.fromisoformat(r['posted']) for r in queue if r['posted']), default=None)
        if last and (datetime.now(timezone.utc) - last).total_seconds() < 20 * 3600:
            print(f'Skipped: a reel already went up at {last:%Y-%m-%d %H:%M} UTC.')
            return
    ready = [r for r in queue if r['approved'] and not r['posted']][:count]
    if not ready:
        print('::warning::No approved reels left in the queue.')
        return
    for reel in ready:
        reel['media_id'] = post(reel['name'])
        reel['posted'] = datetime.now(timezone.utc).isoformat(timespec='minutes')
        QUEUE.write_text(json.dumps(queue, indent=2) + '\n', encoding='utf-8')
        print(f'Posted {reel["name"]} (media {reel["media_id"]})')


if __name__ == '__main__':
    main()
