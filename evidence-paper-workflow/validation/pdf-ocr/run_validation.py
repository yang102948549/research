"""Local opt-in integration fixture. Source is an exam, NOT scholarly evidence.

Writes a controlled simulated-scan PDF from two rendered source pages, including
one image body with >20 characters of selectable header to exercise mixed content.
Run the PDF artifact marker before first execution.
"""
import hashlib
import json
import re
import sys
from pathlib import Path
import fitz

BASE = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE.parents[1] / 'scripts'))
from parsing import pdf_blocks
from local_ocr import ocr_pdf_regions, ocr_image


def save(name, value):
    (BASE / name).write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf-8')


def main():
    source = Path(sys.argv[1]).resolve(strict=True)
    parsed = pdf_blocks(source)
    selected = [1, 11, 18, 19]
    save('source-extraction.json', {**parsed, 'pages': [p for p in parsed['pages'] if p['pdf_page'] in selected]})
    with fitz.open(source) as doc:
        doc[10].get_pixmap(dpi=220, clip=fitz.Rect(440,805,760,845)).save(BASE / 'footnote-crop.png')
        doc[18].get_pixmap(dpi=300, clip=fitz.Rect(600,395,755,455)).save(BASE / 'calendar-crop.png')
        output = fitz.open()
        for number in (1, 11):
            src = doc[number - 1]
            pix = src.get_pixmap(dpi=200, alpha=False)
            pix.save(BASE / f'scan-source-page-{number}.png')
            page = output.new_page(width=src.rect.width, height=src.rect.height)
            page.insert_image(page.rect, stream=pix.tobytes('png'))
            if number == 11:
                page.insert_text((20, 20), 'SIMULATED SCAN - selectable header regression fixture', fontsize=8)
        output.save(BASE / 'simulated-scans.pdf')
        output.close()
    scans = pdf_blocks(BASE / 'simulated-scans.pdf')
    save('scan-extraction.json', scans)
    results = []
    for page in scans['pages']:
        results.append(ocr_pdf_regions(BASE / 'simulated-scans.pdf', page, dpi=200, scratch_dir=BASE))
    # The real mixed page contains rasterized notice/blog text, invisible to native extraction.
    mixed = ocr_pdf_regions(source, parsed['pages'][17], dpi=200, scratch_dir=BASE)
    save('scan-ocr.json', results)
    save('real-mixed-page-18-ocr.json', mixed)
    save('calendar-ocr.json', ocr_image(BASE / 'calendar-crop.png'))
    def compact(text): return re.sub(r'\s+', '', text)
    # Expectations transcribed from rendered originals, not obtained from OCR.
    expectations = [
        (0, 'negation', '설명하지는 않는다'),
        (0, 'number', '2026'),
        (0, 'left-column', '글을 읽고 그 의미를 이해하는 독해에는'),
        (0, 'right-column', '단순 관점에 대한 비판으로 가장 적절한 것은'),
        (1, 'footnote', '봉고파출'),
        (1, 'footnote-definition', '어사가 고을 원을 파면하고 관가의 창고를 잠금'),
    ]
    checks = []
    for index, kind, expected in expectations:
        actual = ' '.join(r['text'] for r in results[index]['regions'])
        checks.append({'scan_pdf_page': index+1, 'kind': kind, 'expected': expected,
                       'whitespace_insensitive_match': compact(expected) in compact(actual)})
    actual = ' '.join(r['text'] for r in mixed['regions'])
    for expected in ('월 5권 이내, 14일간', '09:00', '18:00', '3일간 재신청 불가'):
        checks.append({'source_pdf_page': 18, 'kind': 'raster-notice-number', 'expected': expected,
                       'whitespace_insensitive_match': compact(expected) in compact(actual)})
    save('checks.json', {'source_sha256': hashlib.sha256(source.read_bytes()).hexdigest(),
                        'scope': 'Real Korean two-column exam, controlled rasterized scans; not physical scan nor scholarly paper.',
                        'checks': checks, 'passed': sum(c['whitespace_insensitive_match'] for c in checks),
                        'total': len(checks), 'evidence_verified': False})
    print(json.dumps({'checks':len(checks),'passed':sum(c['whitespace_insensitive_match'] for c in checks),
                      'scan_regions':[len(r['regions']) for r in results], 'real_mixed_regions':len(mixed['regions'])}))


if __name__ == '__main__': main()
