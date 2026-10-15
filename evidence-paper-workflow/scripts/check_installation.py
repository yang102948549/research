"""Verify immutable upstream and installation hashes, without executing upstream."""
import hashlib
import json
import zipfile
from pathlib import Path

def check(root=None):
    root=Path(root or Path(__file__).resolve().parents[1])
    lock=json.loads((root/'vendor-lock.json').read_text(encoding='utf-8'))
    archive=zipfile.ZipFile(root/'vendor-snapshot.zip') if (root/'vendor-snapshot.zip').exists() else None
    try:
        for record in lock['files']:
            data=archive.read(record['path']) if archive else (root/'vendor'/record['path']).read_bytes()
            if hashlib.sha256(data).hexdigest()!=record['sha256']:
                raise ValueError('Upstream hash changed: '+record['path'])
    finally:
        if archive: archive.close()
    manifest=root/'installation-manifest.json'
    if manifest.exists():
        for name,value in json.loads(manifest.read_text(encoding='utf-8'))['files'].items():
            if hashlib.sha256((root/name).read_bytes()).hexdigest()!=value:
                raise ValueError('Installed file changed: '+name)
    print(json.dumps({'commit':lock['commit'],'upstream_files':len(lock['files']),'status':'hashes_match'}))

if __name__=='__main__': check()
