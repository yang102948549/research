"""Read-only public downloads for the bounded integration pilot."""
import base64
import hashlib
import json
from pathlib import Path
from vendor_fetch import get

ROOT = Path(__file__).resolve().parents[1]

def main():
    repo = 'airmang/python-hwpx'
    sha = json.loads(get(f'https://api.github.com/repos/{repo}/commits/main'))['sha']
    assets = ROOT / 'assets'
    assets.mkdir(exist_ok=True)
    records = []
    for source, dest in [('src/hwpx/data/Skeleton.hwpx', 'blank.hwpx'), ('LICENSE', 'template-LICENSE')]:
        info = json.loads(get(f'https://api.github.com/repos/{repo}/contents/{source}?ref={sha}'))
        data = base64.b64decode(info['content'])
        (assets / dest).write_bytes(data)
        records.append({'source': source, 'local': dest, 'sha256': hashlib.sha256(data).hexdigest()})
    (assets / 'template-provenance.json').write_text(json.dumps({'repository': repo, 'commit': sha, 'files': records}, indent=2), encoding='utf-8')
    pilot = ROOT.parent / 'pilot-staging' / 'sources'
    pilot.mkdir(parents=True, exist_ok=True)
    urls = {
        'article.xml': 'https://www.ebi.ac.uk/europepmc/webservices/rest/PMC3743827/fullTextXML',
        'crossref.json': 'https://api.crossref.org/works/10.1371/journal.pone.0069841',
    }
    manifest = []
    for name, url in urls.items():
        data = get(url)
        (pilot / name).write_bytes(data)
        manifest.append({'path': name, 'url': url, 'sha256': hashlib.sha256(data).hexdigest()})
    (pilot / 'downloads.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    print('Template and public pilot source downloaded; no scripts executed from upstream.')

if __name__ == '__main__':
    main()
