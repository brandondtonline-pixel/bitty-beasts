"""Post the next approved reel(s) in queue.json to Instagram.

Runs in GitHub Actions (see .github/workflows/post.yml). Needs IG_TOKEN, a long-lived
Instagram Login token. Videos are fetched by Instagram from this repo's GitHub Pages site.

    python post.py        # post one
    python post.py 3      # post three in a row (e.g. launch day)
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

API = 'https://graph.instagram.com/v26.0'
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


def post(name):
    caption = (HERE / 'videos' / f'{name}.txt').read_text(encoding='utf-8').strip()
    me = call('GET', 'me', fields='user_id')['user_id']
    box = call('POST', f'{me}/media', media_type='REELS', share_to_feed='true',
               video_url=f'{pages_url()}/videos/{name}.mp4', caption=caption)['id']
    # Meta suggests checking about once a minute; give slow days up to 10 minutes.
    for _ in range(20):
        time.sleep(30)
        status = call('GET', box, fields='status_code,status')
        if status['status_code'] == 'FINISHED':
            return call('POST', f'{me}/media_publish', creation_id=box)['id']
        if status['status_code'] in ('ERROR', 'EXPIRED'):
            sys.exit(f'Instagram could not process {name}: {status}')
    sys.exit(f'Instagram was still processing {name} after 10 minutes')


def main():
    if not os.environ.get('IG_TOKEN'):
        print('::warning::No IG_TOKEN secret yet, so nothing was posted.')
        return
    count = int(sys.argv[1]) if len(sys.argv) > 1 else 1
    queue = json.loads(QUEUE.read_text(encoding='utf-8'))
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
