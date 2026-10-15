import sys, tempfile, unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from workflow import Ledger
import workflow

class WindowsSaveTests(unittest.TestCase):
    def test_transient_replace_retry_and_persistent_failure_preserves_ledger(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parent) as folder:
            w = Ledger(folder, 'save-test')
            w.save()
            original = w.path.read_bytes()
            replace = workflow.os.replace
            calls = []
            def transient(a, b):
                calls.append(1)
                if len(calls) < 3: raise PermissionError('busy')
                return replace(a, b)
            with patch('workflow.os.replace', side_effect=transient), patch('workflow.time.sleep'):
                w.save()
            self.assertEqual(len(calls), 3)
            with patch('workflow.os.replace', side_effect=PermissionError('busy')) as mock, patch('workflow.time.sleep'):
                with self.assertRaises(PermissionError): w.save()
                self.assertEqual(mock.call_count, 3)
            self.assertEqual(w.path.read_bytes(), original)
            self.assertFalse((Path(folder)/'.ledger.lock').exists())
