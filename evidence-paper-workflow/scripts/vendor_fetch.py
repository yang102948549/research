"""Fetch only audited-scope upstream resources at an immutable Git commit."""
import hashlib
import json
import urllib.request
import time
import base64
from pathlib import Path

SHA = 'a1043ef544e3a100c28e70a736b6cf32554d0677'
REPO = 'K-Dense-AI/scientific-agent-skills'
ROOT = Path(__file__).resolve().parents[1]

def get(url):
    req = urllib.request.Request(url, headers={'User-Agent': 'evidence-paper-workflow-audit/0.1'})
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                return r.read()
        except Exception:
            if attempt == 2:
                raise RuntimeError('Upstream download failed; no code executed') from None
            time.sleep(1)

def main():
    tree = json.loads(get(f'https://api.github.com/repos/{REPO}/git/trees/{SHA}?recursive=1'))
    if tree.get('truncated'):
        raise RuntimeError('Incomplete upstream tree')
    files = []
    prefixes = ('skills/literature-review/', 'skills/scientific-writing/')
    for item in tree['tree']:
        name = item['path']
        if item['type'] != 'blob' or not (name.startswith(prefixes) or name == 'LICENSE.md'):
            continue
        dest = ROOT / 'vendor' / name
        if dest.exists():
            data = dest.read_bytes()
            actual = hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest()
            if actual != item['sha']:
                raise RuntimeError('Existing vendor file hash mismatch')
        else:
            data = base64.b64decode(json.loads(get(item['url']))['content'])
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(data)
        files.append({'path': name, 'sha256': hashlib.sha256(data).hexdigest(), 'bytes': len(data)})
    lock = {'repository': f'https://github.com/{REPO}', 'commit': SHA,
            'review_status': 'pending', 'files': files}
    (ROOT / 'vendor-lock.json').write_text(json.dumps(lock, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({'commit': SHA, 'downloaded_files': len(files)}))

if __name__ == '__main__':
    main()
