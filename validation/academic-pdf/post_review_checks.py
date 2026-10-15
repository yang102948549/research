from pathlib import Path
import sys,copy,json,tempfile,shutil
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'evidence-paper-workflow/scripts'))
from workflow import Ledger,WorkflowError
root=Path(__file__).parent
for eid in Ledger(root).data['evidence']:assert not Ledger(root).evidence_errors(eid)
results=[]
with tempfile.TemporaryDirectory(dir=root) as folder:
    renamed=Path(folder)/'original.bin'
    shutil.copy2(root/'tasks/twocol/article.pdf',renamed)
    for name,path in [('pdf_format_downgrade','tasks/twocol/article.pdf'),('renamed_pdf_format_downgrade',renamed.relative_to(root).as_posix())]:
        w=Ledger(root)
        source=dict(w.data['sources']['TW-P001'],path=path)
        w.put('sources','TW-P001',source)
        e=copy.deepcopy(w.data['evidence']['TW-E001'])
        e.update(source_hash=w.data['sources']['TW-P001']['hash'],quote='Entirely absent invented quote',
                 locator={'kind':'html','section':'fake','paragraph':1,'printed_page':None})
        e.pop('pdf_review');w.put('evidence','TW-E001',e)
        errors=w.evidence_errors('TW-E001')
        assert 'PDF source requires PDF locator; format downgrade rejected' in errors
        try:w.review('T1','academic_scan','pass','Invalid control')
        except WorkflowError:pass
        else:raise AssertionError('Downgraded locator passed')
        results.append(dict(case=name,blocked=True,errors=errors))
p=root/'gate-results.json';report=json.loads(p.read_text(encoding='utf-8'))
names={r['case'] for r in results}
report['structural_mutations']=[r for r in report['structural_mutations'] if r['case'] not in names]+results
report['structural_mutations_blocked']=len(report['structural_mutations'])
p.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print('Actual PDF and renamed-PDF downgrade controls blocked; 7 valid evidence records still pass.')
