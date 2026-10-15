"""Bounded KCI pagination diagnostics. No keys, URLs or XML in output."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

from sources import KCIClient, record_identity


def probe(title, client=None):
    client = client or KCIClient(retries=0)
    report = {'schema_version': 1, 'started_at': datetime.now(timezone.utc).isoformat(),
              'title': title, 'sortNm': 'title', 'request_limit': 14, 'request_count': 0,
              'operations': [], 'evidence_verified': False,
              'scope': 'Sampled page boundaries only; not proof of entire result-set completeness'}
    for operation in ('articleSearch', 'referenceSearch'):
        entry = {'operation': operation, 'requests': [], 'checks': {}, 'status': 'pending'}
        report['operations'].append(entry)
        samples = {}

        def request(label, page, size):
            result = client.request(operation, title=title, page=page, displayCount=size, sortNm='title')
            report['request_count'] += 1
            identities = [record_identity(r, operation) for r in result.get('records', [])]
            row = {'label': label, 'page': page, 'requested_size': size,
                   'status': result.get('status', 'unexpected_schema'),
                   'total': result.get('total'), 'returned_records': len(identities),
                   'identifiable_records': sum(i is not None for i in identities),
                   'identity_sequence_sha256': hashlib.sha256(json.dumps(identities).encode()).hexdigest()}
            if isinstance(result.get('http_status'), int):
                row['http_status'] = result['http_status']
            entry['requests'].append(row)
            samples[label] = (row, identities)
            return row

        for label, page, size in [('size1', 1, 1), ('first10', 1, 10), ('second10', 2, 10),
                                  ('first20', 1, 20), ('repeat10', 1, 10)]:
            row = request(label, page, size)
            if row['status'] not in {'ok', 'zero_results'}:
                entry['status'] = row['status']
                report['status'] = row['status']
                return report
        total = samples['first10'][0]['total']
        if not isinstance(total, int) or total < 0:
            entry['status'] = report['status'] = 'unexpected_schema'
            return report
        last_page = max(1, (total + 9) // 10)
        first, second, twenty, repeat = [samples[k][1] for k in
                                         ('first10', 'second10', 'first20', 'repeat10')]
        prefix_ids_ok = all(r['identifiable_records'] == r['returned_records'] for r in entry['requests'])
        entry['checks'].update({
            'prefix_totals_stable': all(r['total'] == total for r in entry['requests']),
            'size1_honored': samples['size1'][0]['returned_records'] == min(1, total),
            'size10_honored': len(first) == min(10, total) and len(second) == min(10, max(0, total-10)),
            'size20_honored': len(twenty) == min(20, total),
            'prefix_identities_available': prefix_ids_ok,
            'prefix_unique_within_pages': all(len(ids) == len(set(ids)) for _, ids in samples.values()) if prefix_ids_ok else None,
            'first_two_pages_disjoint': not set(first).intersection(second) if prefix_ids_ok else None,
            'first_two_match_size20': first + second == twenty if prefix_ids_ok else None,
            'repeat_first_page_stable': first == repeat if prefix_ids_ok else None,
        })
        tail_failed = False
        for label, page in [('last10', last_page), ('after_last10', last_page + 1)]:
            row = request(label, page, 10)
            if row['status'] not in {'ok', 'zero_results'}:
                entry['status'] = row['status']
                entry['boundary_validation'] = 'incomplete'
                if row['status'] in {'not_configured', 'authentication_error'}:
                    report['status'] = row['status']
                    return report
                tail_failed = True
                break
        if tail_failed:
            continue
        first, second, twenty, repeat, last, after = [samples[k][1] for k in
            ('first10', 'second10', 'first20', 'repeat10', 'last10', 'after_last10')]
        rows = entry['requests']
        identities_ok = all(r['identifiable_records'] == r['returned_records'] for r in rows)
        totals_stable = all(r['total'] == total for r in rows)
        checks = entry['checks']
        checks['totals_stable'] = totals_stable
        checks['size1_honored'] = samples['size1'][0]['returned_records'] == min(1, total)
        checks['size10_honored'] = len(first) == min(10, total) and len(second) == min(10, max(0, total - 10))
        checks['size20_honored'] = len(twenty) == min(20, total)
        checks['identities_available'] = identities_ok
        checks['unique_within_pages'] = all(len(ids) == len(set(ids)) for _, ids in samples.values()) if identities_ok else None
        checks['first_two_pages_disjoint'] = not set(first).intersection(second) if identities_ok else None
        checks['first_two_match_size20'] = first + second == twenty if identities_ok else None
        checks['repeat_first_page_stable'] = first == repeat if identities_ok else None
        checks['last_page_count'] = len(last) == (total - (last_page - 1) * 10 if total else 0)
        checks['after_last_empty'] = not after
        checks['last_page_distinct_from_first'] = (not set(last).intersection(first) if last_page > 1 else last == first) if identities_ok else None
        checks['last_page_consistent_with_second'] = (not set(last).intersection(second) if last_page > 2 else last == second if last_page == 2 else not second) if identities_ok else None
        critical = [value for name, value in checks.items() if name != 'size1_honored']
        if total <= 10:
            entry['status'] = 'insufficient_results' if all(v is True for v in critical) else 'needs_review'
        else:
            entry['status'] = ('sampled_pass' if checks['size1_honored'] else 'sampled_pass_size1_not_honored') if all(v is True for v in critical) else 'needs_review'
    report['status'] = 'sampled_pass' if all(e['status'].startswith('sampled_pass') for e in report['operations']) else 'needs_review'
    report['finished_at'] = datetime.now(timezone.utc).isoformat()
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--title', default='인공지능')
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    result = probe(args.title)
    rendered = json.dumps(result, ensure_ascii=False, indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        # Preserve prior runs instead of silently overwriting them.
        with args.output.open('x', encoding='utf-8') as out:
            out.write(rendered + '\n')
    print(rendered)
    return 0 if result['status'] == 'sampled_pass' else 2


if __name__ == '__main__':
    raise SystemExit(main())
