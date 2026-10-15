import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from kci_probe import probe, article_id
from sources import KCIClient, parse_kci


class ProbeTests(unittest.TestCase):
    def test_detail_without_total(self):
        payload = b'<result><outputData><record><articleInfo article-id="ART123"><title-group><article-title lang="original">Real title</article-title></title-group></articleInfo></record></outputData></result>'
        self.assertEqual(parse_kci(payload, operation='articleDetail')['status'], 'ok')
        self.assertEqual(parse_kci(payload, operation='articleSearch')['status'], 'unexpected_schema')
        self.assertEqual(parse_kci(b'<outputData><record/></outputData>', operation='articleDetail')['status'], 'unexpected_schema')

    def test_no_key_no_network(self):
        with patch.dict(os.environ, {}, clear=True):
            result = probe('test', KCIClient(fetch=lambda _: self.fail('network called'), retries=0))
        self.assertEqual(result['status'], 'not_configured')

    def test_bounded_requests_and_no_secret(self):
        calls = []
        payload = b'<result><total>1</total><outputData><record><articleInfo article-id="ART123"><article-title>Title</article-title></articleInfo></record></outputData></result>'
        with patch.dict(os.environ, {'KCI_API_KEY': 'dummy-secret'}):
            result = probe('test', KCIClient(fetch=lambda u: calls.append(u) or payload, retries=0))
        self.assertEqual(len(calls), 3)
        self.assertEqual(result['status'], 'ok')
        self.assertNotIn('dummy-secret', str(result))
        self.assertNotIn('request_url', str(result))
        self.assertTrue(all('displayCount=1' in u for u in (calls[0], calls[2])))

    def test_zero_not_auth_error(self):
        with patch.dict(os.environ, {'KCI_API_KEY': 'dummy'}):
            result = probe('test', KCIClient(fetch=lambda _: b'<result><total>0</total></result>', retries=0))
        self.assertEqual(result['status'], 'partial_no_article_id')
        self.assertEqual(result['checks'][0]['status'], 'zero_results')

    def test_auth_stops(self):
        calls = []
        with patch.dict(os.environ, {'KCI_API_KEY': 'dummy'}):
            result = probe('test', KCIClient(fetch=lambda u: calls.append(u) or '<error>등록되지 않은 key 입니다</error>'.encode(), retries=0))
        self.assertEqual(len(calls), 1)
        self.assertEqual(result['status'], 'authentication_error')

    def test_network_and_schema_distinct(self):
        def fail(_):
            raise OSError('secret must not leak')
        with patch.dict(os.environ, {'KCI_API_KEY': 'dummy'}):
            self.assertEqual(probe('x', KCIClient(fetch=fail, retries=0))['status'], 'network_error')
            self.assertEqual(probe('x', KCIClient(fetch=lambda _: b'<unknown/>', retries=0))['status'], 'unexpected_schema')

    def test_only_documented_identifier(self):
        self.assertIsNone(article_id({'records': [{'xml': '<record><id>ART1</id></record>'}]}))
        self.assertIsNone(article_id({'records': [{'xml': '<record><articleInfo article-id="bad&amp;key=x"/></record>'}]}))


if __name__ == '__main__':
    unittest.main()
