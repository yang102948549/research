"""Install this reviewed skill and copy pilot data, without touching Onitime."""
import hashlib
import json
import shutil
import zipfile
from pathlib import Path

SOURCE = Path(__file__).resolve().parents[1]
TARGET = Path('C:/Users/USER/.codex/skills/evidence-paper-workflow')
RESEARCH = Path('C:/Users/USER/Documents/ResearchWorkspace/pilot-kross-2013')

def sha(data): return hashlib.sha256(data).hexdigest()

def main():
    # Fixed user-requested destinations; no recursive delete/move.
    if TARGET.resolve().parent != Path('C:/Users/USER/.codex/skills').resolve():
        raise ValueError('Unexpected skill destination')
    old_path = TARGET / 'installation-manifest.json'
    old = json.loads(old_path.read_text(encoding='utf-8')) if old_path.exists() else {'files': {}}
    planned = {}
    for path in SOURCE.rglob('*'):
        if not path.is_file() or '__pycache__' in path.parts or any(p in path.relative_to(SOURCE).parts for p in ('vendor', 'validation')):
            continue
        relative = path.relative_to(SOURCE).as_posix()
        planned[relative] = path.read_bytes()
    # Quarantined ZIP prevents discovery of two nested SKILL.md entrypoints.
    import io
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, 'w', zipfile.ZIP_DEFLATED) as z:
        for path in sorted((SOURCE / 'vendor').rglob('*')):
            if path.is_file(): z.write(path, path.relative_to(SOURCE / 'vendor').as_posix())
    planned['vendor-snapshot.zip'] = buffer.getvalue()
    for relative, data in planned.items():
        dest = TARGET / relative
        if dest.exists() and sha(dest.read_bytes()) != sha(data):
            if old['files'].get(relative) != sha(dest.read_bytes()):
                raise ValueError('Existing unmanaged or user-modified skill file: '+relative)
    TARGET.mkdir(parents=True, exist_ok=True)
    for relative, data in planned.items():
        dest=TARGET / relative
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(data)
    manifest={'files':{n:sha(d) for n,d in planned.items()}, 'upstream_commit':json.loads((SOURCE/'vendor-lock.json').read_text())['commit']}
    old_path.write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
    if RESEARCH.exists():
        print('Research destination already exists; preserved without changes.')
    else:
        shutil.copytree(SOURCE.parent/'pilot-staging',RESEARCH,ignore=shutil.ignore_patterns('__pycache__'))
    print(json.dumps({'skill':str(TARGET),'research':str(RESEARCH),'installed_files':len(planned)},ensure_ascii=False))

if __name__=='__main__': main()
