"""Run local regression checks and persist honest coverage, not research approvals."""
import json
import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path
from check_installation import check

def main():
    root=Path(__file__).resolve().parents[1]
    check(root)
    suite=unittest.defaultTestLoader.discover(str(root/'tests'))
    result=unittest.TextTestRunner(verbosity=2).run(suite)
    report={'timestamp':datetime.now(timezone.utc).isoformat(), 'tests_run':result.testsRun,
            'failures':len(result.failures),'errors':len(result.errors),'skipped':len(result.skipped),
            'pass':result.wasSuccessful(), 'approval_scope':'Synthetic test records only; no actual research approval granted',
            'covered':['identifier mismatch','abstract exclusion','XML exact locator quote',
                       'version invalidation','separate claim and paragraph review','handoff integrity',
                       'bounded repair','resume','KCI mocked errors pagination redaction',
                       'HWPX structural/text roundtrip','bibliography consistency'],
            'not_validated_by_unit_suite':['live KCI authentication/schema','Korean two-column PDF visual reading',
                             'scan OCR','rendered HWPX appearance','real research end-to-end after both approvals']}
    (root/'validation-results.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    return 0 if result.wasSuccessful() else 1

if __name__=='__main__': sys.exit(main())
