import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
from urllib.parse import urlparse, parse_qs
from urllib.error import HTTPError

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from sources import KCIClient, parse_kci, record_identity
from kci_pagination_probe import probe


def payload(ids, total=21, operation='articleSearch', changed=False):
    if operation == 'articleSearch':
        body = '<outputData>' + ''.join(
            f'<record><articleInfo article-id="ART{i}"><article-title>{"changed" if changed else "title"}</article-title></articleInfo></record>' for i in ids) + '</outputData>'
    else:
        body = ''.join(f'<outputData article-id="ART{i}"><record>Reference {i}</record></outputData>' for i in ids)
    return f'<result><total>{total}</total>{body}</result>'.encode()


@patch.dict(os.environ, {'KCI_API_KEY': 'test-secret-not-real'})
class PaginationTests(unittest.TestCase):
    def client(self, transform=None):
        calls = []
        def fetch(url):
            q = {k: v[0] for k, v in parse_qs(urlparse(url).query).items()}
            calls.append(q)
            page, size = int(q['page']), int(q['displayCount'])
            if transform:
                page, size = transform(page, size)
            ids = list(range(1, 22))[(page-1)*size:page*size]
            return payload(ids, operation=q['apiCode'])
        return KCIClient(fetch=fetch, retries=0), calls

    def collect_result(self, fetch, page_size=10):
        with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parent) as directory:
            result = KCIClient(fetch=fetch, retries=0).collect('x', Path(directory)/'c.json', page_size=page_size)
        return result

    def test_probe_normal_boundaries_both_operations(self):
        client, calls = self.client()
        result = probe('인공지능', client)
        self.assertEqual(result['status'], 'sampled_pass')
        self.assertEqual(len(calls), 14)
        self.assertNotIn('test-secret-not-real', json.dumps(result))
        self.assertNotIn('<record>', json.dumps(result))
        self.assertTrue(all(e['checks']['first_two_match_size20'] for e in result['operations']))

    def test_probe_size_one_defaults_to_ten(self):
        client, _ = self.client(lambda p, s: (p, 10 if s == 1 else s))
        result = probe('x', client)
        self.assertEqual(result['status'], 'sampled_pass')
        self.assertTrue(all(e['status'] == 'sampled_pass_size1_not_honored' for e in result['operations']))

    def test_probe_ignored_page_and_ignored_size_detected(self):
        for transform in (lambda p, s: (1, s), lambda p, s: (p, 10)):
            client, _ = self.client(transform)
            self.assertEqual(probe('x', client)['status'], 'needs_review')

    def test_probe_missing_key_stops_before_network(self):
        with patch.dict(os.environ, {}, clear=True):
            result = probe('x', KCIClient(fetch=lambda _: self.fail('network attempted')))
        self.assertEqual(result['status'], 'not_configured')
        self.assertEqual(result['request_count'], 1)

    def test_last_page_http_failure_preserves_prefix_and_checks_other_api(self):
        client, _ = self.client()
        original = client.fetch
        def fetch(url):
            if 'articleSearch' in url and 'page=3&' in url:
                raise HTTPError(url, 500, 'secret error body', {}, None)
            return original(url)
        client.fetch = fetch
        result = probe('x', client)
        self.assertEqual(result['status'], 'needs_review')
        self.assertEqual(result['request_count'], 13)
        first, second = result['operations']
        self.assertEqual(first['status'], 'http_error')
        self.assertEqual(first['requests'][-1]['http_status'], 500)
        self.assertTrue(first['checks']['first_two_match_size20'])
        self.assertNotIn('last_page_count', first['checks'])
        self.assertEqual(second['status'], 'sampled_pass')
        self.assertNotIn('test-secret-not-real', json.dumps(result))
        self.assertNotIn('secret error body', json.dumps(result))

    def test_last_page_overlap_with_second_detected(self):
        client, _ = self.client()
        original = client.fetch
        client.fetch = lambda u: payload([11], operation=parse_qs(urlparse(u).query)['apiCode'][0]) if 'page=3&' in u else original(u)
        result = probe('x', client)
        self.assertEqual(result['status'], 'needs_review')
        self.assertFalse(result['operations'][0]['checks']['last_page_consistent_with_second'])

    def test_probe_reference_identity_requires_parent(self):
        client, _ = self.client()
        original = client.fetch
        client.fetch = lambda u: original(u).replace(b'<outputData article-id=', b'<outputData unknown=') if 'referenceSearch' in u else original(u)
        result = probe('x', client)
        self.assertEqual(result['status'], 'needs_review')
        self.assertIsNone(result['operations'][1]['checks']['first_two_pages_disjoint'])

    def test_collect_resume_10_10_1(self):
        client, calls = self.client()
        with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parent) as directory:
            path = Path(directory)/'c.json'
            first = client.collect('x', path, page_size=10, max_pages=1)
            self.assertEqual(first['status'], 'partial')
            final = client.collect('x', path, page_size=10)
            self.assertEqual(final['status'], 'complete')
            self.assertEqual(final['collected_count'], 21)
            self.assertEqual([q['page'] for q in calls], ['1', '2', '3'])

    def test_collect_size_mismatch_preserves_checkpoint(self):
        result = self.collect_result(lambda _: payload(range(1, 11)), page_size=1)
        self.assertEqual(result['status'], 'page_size_mismatch')
        self.assertEqual(result['collected_count'], 0)
        self.assertEqual(result['next_page'], 1)

    def test_duplicate_inside_page_not_complete(self):
        result = self.collect_result(lambda _: payload([1, 1], total=2), page_size=2)
        self.assertEqual(result['status'], 'duplicate_records_in_page')
        self.assertEqual(result['collected_count'], 0)

    def test_changed_metadata_same_identity_detected(self):
        result = self.collect_result(lambda u: payload([1], total=2, changed='page=2&' in u), page_size=1)
        self.assertEqual(result['status'], 'overlapping_pages')
        self.assertEqual(result['collected_count'], 1)

    def test_total_exceeded_and_short_page(self):
        self.assertEqual(self.collect_result(lambda _: payload([1, 2], total=1))['status'], 'total_exceeded')
        self.assertEqual(self.collect_result(lambda _: payload([1], total=21))['status'], 'page_size_mismatch')

    def test_reference_identity_preserves_citing_article(self):
        result = parse_kci(b'<result><total>2</total><outputData article-id="ART1"><record>same</record></outputData><outputData article-id="ART2"><record>same</record></outputData></result>', operation='referenceSearch')
        ids = [record_identity(r, 'referenceSearch') for r in result['records']]
        self.assertEqual(len(set(ids)), 2)

    def test_invalid_pagination_types_and_legacy_checkpoint(self):
        for value in (True, 1.5, '1.5', 0, -1):
            self.assertEqual(KCIClient().request('articleSearch', title='x', page=value)['status'], 'invalid_pagination')
        client, _ = self.client()
        with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parent) as directory:
            path = Path(directory)/'c.json'
            state = client.collect('x', path, page_size=10, max_pages=1)
            del state['pagination_contract']
            path.write_text(json.dumps(state))
            with self.assertRaisesRegex(ValueError, 'Legacy checkpoint'):
                client.collect('x', path, page_size=10)


if __name__ == '__main__':
    unittest.main()
