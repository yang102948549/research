"""Local HWPX export from gated, independently reviewed claim paragraphs."""
import csv
import hashlib
import io
import json
import re
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from xml.etree import ElementTree as ET
from workflow import WorkflowError

HP = 'http://www.hancom.co.kr/hwpml/2011/paragraph'
HS = 'http://www.hancom.co.kr/hwpml/2011/section'
OPF = 'http://www.idpf.org/2007/opf/'
ET.register_namespace('hp', HP)
ET.register_namespace('hs', HS)
ET.register_namespace('opf', OPF)

def normalized(value):
    return ''.join(c for c in str(value).casefold() if c.isalnum())


def bib_fields(text):
    """Deliberately restricted braced-field BibTeX, not a general parser."""
    entry = re.fullmatch(r'\s*@\w+\s*\{\s*([^,{}]+),\s*(.*?)\s*\}\s*', text, re.S)
    if not entry:
        raise WorkflowError('Unsupported BibTeX entry; use one normalized braced entry')
    fields = {}
    remaining = entry.group(2)
    while remaining.strip().strip(','):
        match = re.match(r'\s*,?\s*(\w+)\s*=\s*\{([^{}]*)\}\s*,?', remaining, re.S)
        if not match or match.group(1).lower() in fields:
            raise WorkflowError('Unsupported/duplicate BibTeX field')
        fields[match.group(1).lower()] = match.group(2)
        remaining = remaining[match.end():]
    return entry.group(1).strip(), fields


def validate_reference(sid, source):
    if not all(source.get(k) for k in ('reference_text', 'csl', 'bibtex')):
        raise WorkflowError('Normalized reference missing: ' + sid)
    if not all(source.get(k) for k in ('title', 'authors', 'year')):
        raise WorkflowError('Verified source bibliography missing: ' + sid)
    authors = [a.get('family', a.get('literal', '')) if isinstance(a, dict) else a for a in source['authors']]
    csl, ref = source['csl'], source['reference_text']
    key, fields = bib_fields(source['bibtex'])
    ca = [a.get('family', a.get('literal', '')) for a in csl.get('author', [])]
    ba = [a.strip().split(',')[0] for a in fields.get('author', '').split(' and ')]
    year = str(source['year'])
    try:
        csl_year = str(csl['issued']['date-parts'][0][0])
    except (KeyError, IndexError, TypeError):
        csl_year = ''
    if (key != sid or normalized(csl.get('title', '')) != normalized(source['title'])
            or normalized(fields.get('title', '')) != normalized(source['title'])
            or [normalized(a) for a in ca] != [normalized(a) for a in authors]
            or [normalized(a) for a in ba] != [normalized(a) for a in authors]
            or csl_year != year or fields.get('year') != year
            or normalized(source['title']) not in normalized(ref)
            or not re.search(r'(?<!\d)' + re.escape(year) + r'(?!\d)', ref)
            or any(normalized(a) not in normalized(ref) for a in authors)):
        raise WorkflowError('Normalized bibliography does not match source: ' + sid)
    doi = source.get('doi', '').lower().removeprefix('https://doi.org/')
    if doi:
        ref_dois = [x.rstrip('.,;') for x in re.findall(r'10\.\d{4,9}/[^\s<>]+', ref.lower())]
        if (csl.get('DOI', '').lower().removeprefix('https://doi.org/') != doi
                or fields.get('doi', '').lower().removeprefix('https://doi.org/') != doi
                or ref_dois != [doi]):
            raise WorkflowError('Normalized bibliography DOI mismatch: ' + sid)
    else:
        manual = source.get('bibliography_review', {})
        if not all(manual.get(k) for k in ('reviewer', 'timestamp', 'rationale')) or manual.get('verdict') != 'pass':
            raise WorkflowError('Identifier-free bibliography requires explicit manual review: ' + sid)
    return True


def verify_export_alignment(root, sources, cited):
    """Re-read serialized outputs rather than trusting in-memory construction."""
    refs = json.loads((root / 'references.csl.json').read_text(encoding='utf-8'))
    with (root / 'evidence.csv').open(encoding='utf-8-sig', newline='') as handle:
        rows = list(csv.DictReader(handle))
    trace = json.loads((root / 'manuscript-trace.json').read_text(encoding='utf-8'))
    bib = (root / 'references.bib').read_text(encoding='utf-8')
    bib_ids = re.findall(r'@\w+\s*\{\s*([^,{}]+),', bib)
    if (set(r['id'] for r in refs) != cited or len(refs) != len(cited)
            or set(bib_ids) != cited or len(bib_ids) != len(cited)
            or {r['paper_id'] for r in rows} != cited
            or {s for p in trace for s in p['source_ids']} != cited):
        raise WorkflowError('Serialized evidence/reference/source ID mismatch')
    for ref in refs:
        sid = ref['id']
        if ref != dict(sources[sid]['csl'], id=sid) or sources[sid]['bibtex'] not in bib:
            raise WorkflowError('Serialized normalized reference mismatch')
        validate_reference(sid, sources[sid])
    return True

def text_of_hwpx(path):
    with zipfile.ZipFile(path) as z:
        paragraphs = []
        for name in sorted(z.namelist()):
            if re.fullmatch(r'Contents/section\d+\.xml', name):
                root = ET.fromstring(z.read(name))
                paragraphs.extend(''.join(t.text or '' for t in p.iter(f'{{{HP}}}t'))
                                  for p in root.findall(f'{{{HP}}}p'))
        return paragraphs

def make_hwpx(lines, destination, template=None):
    template = Path(template or Path(__file__).resolve().parents[1] / 'assets/blank.hwpx')
    with zipfile.ZipFile(template) as z:
        files = {n: z.read(n) for n in z.namelist()}
    root = ET.fromstring(files['Contents/section0.xml'])
    first = root.find(f'{{{HP}}}p')
    if first is None or first.find(f'.//{{{HP}}}secPr') is None:
        raise WorkflowError('Template lacks section/page properties')
    for p in list(root):
        if p is not first:
            root.remove(p)
    for run in list(first):
        if run.tag == f'{{{HP}}}linesegarray':
            first.remove(run)  # stale layout data must be regenerated by Hancom
        elif run.tag == f'{{{HP}}}run' and run.find(f'{{{HP}}}secPr') is None:
            first.remove(run)
    for i, line in enumerate(lines):
        p = first if i == 0 else ET.SubElement(root, f'{{{HP}}}p', {
            'id': str(i), 'paraPrIDRef': '0', 'styleIDRef': '0',
            'pageBreak': '0', 'columnBreak': '0', 'merged': '0'})
        run = ET.SubElement(p, f'{{{HP}}}run', {'charPrIDRef': '0'})
        ET.SubElement(run, f'{{{HP}}}t').text = line
    files['Contents/section0.xml'] = ET.tostring(root, encoding='utf-8', xml_declaration=True)
    # Default justified alignment stretches English bibliography words excessively.
    header = ET.fromstring(files['Contents/header.xml'])
    for node in header.iter():
        if node.tag.rsplit('}', 1)[-1] == 'align' and 'horizontal' in node.attrib:
            node.set('horizontal', 'LEFT')
    files['Contents/header.xml'] = ET.tostring(header, encoding='utf-8', xml_declaration=True)
    files['Preview/PrvText.txt'] = '\r\n'.join(lines).encode('utf-8')
    files.pop('Preview/PrvImage.png', None)  # original preview is no longer accurate
    package = ET.fromstring(files['Contents/content.hpf'])
    for item in package.findall(f'.//{{{OPF}}}meta'):
        if item.get('name') in ('creator', 'lastsaveby'):
            item.text = 'evidence-paper-workflow; review draft'
        if item.get('name') in ('CreatedDate', 'ModifiedDate'):
            item.text = datetime.now(timezone.utc).isoformat()
        if item.get('name') == 'date':
            item.text = ''
    title = package.find(f'.//{{{OPF}}}title')
    if title is not None:
        title.text = lines[0]
    files['Contents/content.hpf'] = ET.tostring(package, encoding='utf-8', xml_declaration=True)
    with zipfile.ZipFile(destination, 'w', zipfile.ZIP_DEFLATED) as z:
        z.writestr('mimetype', files.pop('mimetype'), compress_type=zipfile.ZIP_STORED)
        for name, data in files.items():
            z.writestr(name, data)
    return validate_hwpx(destination, lines)

def validate_hwpx(path, lines):
    with zipfile.ZipFile(path) as z:
        first = z.infolist()[0]
        if first.filename != 'mimetype' or first.compress_type != zipfile.ZIP_STORED:
            raise WorkflowError('Invalid mimetype entry')
        if z.read('mimetype') != b'application/hwp+zip':
            raise WorkflowError('Invalid HWPX MIME')
        for name in z.namelist():
            if name.endswith(('.xml', '.hpf')):
                ET.fromstring(z.read(name))
        package = ET.fromstring(z.read('Contents/content.hpf'))
        for item in package.findall(f'.//{{{OPF}}}item'):
            if item.get('href') not in z.namelist():
                raise WorkflowError('Missing package member')
    if text_of_hwpx(path) != lines:
        raise WorkflowError('HWPX round-trip mismatch')
    return {'structure': 'pass', 'text_roundtrip': 'pass',
            'visual_review': 'not_performed', 'schema_validation': 'not_performed',
            'scope': 'ZIP/XML/package links and exact text; not full standard conformity or render proof'}

def export_bundle(ledger, title='근거 추적 시험 원고'):
    gate = ledger.gate('manuscript')
    if not gate['pass']:
        raise WorkflowError('Export blocked: ' + '; '.join(gate['errors']))
    d, root = ledger.data, ledger.root
    cited = set()
    lines = [title, '투고 전 검토용 · 에이전트 검토 · 최신 검증 상태는 verification-report.md 참조']
    trace = []
    for pid, p in d['paragraphs'].items():
        if p.get('heading'):
            lines.append(p['heading'])
        source_ids = sorted({d['evidence'][eid]['source_id']
                            for cid in p['claim_ids'] for eid in d['claims'][cid]['evidence_ids']})
        cited.update(source_ids)
        citations = '; '.join(d['sources'][sid]['citation_label'] for sid in source_ids)
        line = p['text'] + ' (' + citations + ').'
        lines.append(line)
        trace.append({'paragraph_id': pid, 'claim_ids': p['claim_ids'],
                      'source_ids': source_ids, 'rendered_text': line})
    lines.append('참고문헌')
    refs = []
    bib = []
    for sid in sorted(cited):
        source = d['sources'][sid]
        validate_reference(sid, source)
        lines.append(source['reference_text'])
        csl = dict(source['csl'], id=sid)
        refs.append(csl)
        bib.append(source['bibtex'])
    root.mkdir(parents=True, exist_ok=True)
    (root / 'manuscript.md').write_text('\n\n'.join(lines), encoding='utf-8')
    (root / 'references.csl.json').write_text(json.dumps(refs, ensure_ascii=False, indent=2), encoding='utf-8')
    (root / 'references.bib').write_text('\n\n'.join(bib), encoding='utf-8')
    (root / 'manuscript-trace.json').write_text(json.dumps(trace, ensure_ascii=False, indent=2), encoding='utf-8')
    rows = []
    for cid, claim in d['claims'].items():
        for eid in claim['evidence_ids']:
            e = d['evidence'][eid]
            rows.append({'claim_id': cid, 'claim': claim['text'], 'evidence_id': eid,
                         'paper_id': e['source_id'], 'source_hash': e['source_hash'],
                         'quote_original': e['quote'], 'translation': e.get('translation', ''),
                         'context': e['context'], 'locator': json.dumps(e['locator'], ensure_ascii=False),
                         'interpretation': e.get('interpretation', ''), 'limits': e['limits'],
                         'review_status': d['reviews'][cid]['review_kind']})
    with (root / 'evidence.csv').open('w', encoding='utf-8-sig', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    report = make_hwpx(lines, root / 'manuscript.hwpx')
    verify_export_alignment(root, d['sources'], cited)
    report.update({'ledger_version': d['version'], 'citation_reference_match': 'pass',
                   'cited_source_ids': sorted(cited), 'submission_ready': False,
                   'template_conversion': 'Bundled blank HWPX section/page properties retained; text inserted as XML; ZIP/XML and exact re-extraction checked; no rendering or full schema proof'})
    report['files'] = {name: hashlib.sha256((root / name).read_bytes()).hexdigest()
                       for name in ('manuscript.hwpx', 'manuscript.md', 'evidence.csv',
                                    'references.bib', 'references.csl.json', 'manuscript-trace.json')}
    (root / 'export-validation.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    (root / 'hwpx-reextracted.txt').write_text('\n\n'.join(text_of_hwpx(root / 'manuscript.hwpx')), encoding='utf-8')
    (root / 'verification-report.md').write_text(
        '# 검증 보고서\n\n투고 전 검토용 원고. 자동 투고하지 않음.\n\n'
        + f"장부 버전: {d['version']}\n\n"
        + '원고 게이트: 통과. 각 문단은 검토한 주장 문구에 연결됨.\n\n'
        + '검증 범위: 에이전트의 원문·맥락 대조, 파일 해시, ID 연결, HWPX XML/패키지 및 내용 재추출.\n\n'
        + '한계: 같은 모델 역할 분리는 완전한 독립성이나 무환각을 보장하지 않음. '
        + '사람의 원문 검토, HWPX 실제 열기·시각 검증, 전체 스키마 검증은 미완료.\n\n'
        + '## 주장별 한계\n\n' + '\n'.join('- ' + r['claim_id'] + ': ' + r['limits'] for r in rows)
        + '\n\nKCI 실연결·한국어 2단 PDF·OCR·표 수치 추출은 이 XML 시험으로 검증되지 않음.\n', encoding='utf-8')
    ledger.record_export_validation('manuscript.hwpx', dict(structure_valid=True,
        content_reextracted=True, citation_alignment=True, material_unresolved=[],
        visual_status='not_completed', validation_scope=report['scope'],
        output_hashes={**report['files'], **{name:hashlib.sha256((root/name).read_bytes()).hexdigest()
            for name in ('export-validation.json', 'hwpx-reextracted.txt', 'verification-report.md')}}))
    ledger.save()
    return report
