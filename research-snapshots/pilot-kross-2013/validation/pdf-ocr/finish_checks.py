import json
import re
from pathlib import Path

base = Path(__file__).parent
read = lambda name: json.loads((base / name).read_text(encoding='utf-8'))
compact = lambda s: re.sub(r'\s+', '', s)
checks = read('checks.json')
ocr = read('scan-ocr.json')
for check in checks['checks']:
    if check['kind'] == 'footnote-definition':
        check['expected'] = '어사가 고을 원을 파면하고 관가의 창고를 잠금'
        check['whitespace_insensitive_match'] = compact(check['expected']) in compact(ocr[1]['regions'][0]['text'])
checks['passed'] = sum(c['whitespace_insensitive_match'] for c in checks['checks'])
checks['gold_transcription_note'] = 'Footnote gold corrected from 아사가 to 어사가 after 220dpi original-image crop inspection.'
calendar = read('calendar-ocr.json')
words = [w for l in calendar['lines'] for w in l['words']]
digits = {w['text']: w['bbox'] for w in words if w['text'] in list('1234567')}
checks['table'] = {'source_pdf_page':19, 'printed_page_top':'3', 'printed_page_footer':'19 / 20',
    'crop_pdf_bbox':[600,395,755,455], 'crop_dpi':300,
    'expected_columns':list('일월화수목금토'), 'expected_digits':list('1234567'),
    'digits_found':sorted(digits),
    'digit_cell_order_matches':len(digits)==7 and all(digits[str(i)][0] < digits[str(i+1)][0] for i in range(1,7)),
    'weekday_headers_complete':all(x in {w['text'] for w in words} for x in '일월화수목금토'),
    'closure_label_expected':'정기 휴관', 'closure_label_match':'정기휴관' in compact(calendar['text']),
    'status':'failed_requires_manual_transcription_and_review'}
source = read('source-extraction.json')
checks['native_text'] = []
for p in source['pages']:
    ids = [b['block_id'] for b in p['blocks']]
    proposed = p['proposed_block_order'] or []
    checks['native_text'].append({'pdf_page':p['pdf_page'], 'two_columns_detected':p['two_column_candidate'],
        'native_blocks_preserved':len(ids), 'proposal_has_all_blocks_once':len(proposed)==len(set(proposed))==len(ids),
        'ocr_region_count':len(p['ocr_regions']), 'reading_order_verified':False})
(base/'checks.json').write_text(json.dumps(checks,ensure_ascii=False,indent=2),encoding='utf-8')
