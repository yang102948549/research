from pathlib import Path
import sys, shutil
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'evidence-paper-workflow/scripts'))
from workflow import Ledger
from export import export_bundle
root = Path('C:/Users/USER/Documents/ResearchWorkspace/pilot-kross-2013')
backup = root / 'versions/pre-visual-fix'
backup.mkdir(parents=True, exist_ok=True)
for name in ('manuscript.hwpx','manuscript.md','export-validation.json','verification-report.md','hwpx-reextracted.txt','ledger.json'):
    if not (backup/name).exists(): shutil.copy2(root/name, backup/name)
w = Ledger(root)
export_bundle(w, 'Facebook 이용과 주관적 안녕감: Kross 외(2013)의 주장 범위 검토')
shutil.copy2(root/'manuscript.hwpx', Path(__file__).parent/'manuscript-revised.hwpx')
print(w.gate('final'))
