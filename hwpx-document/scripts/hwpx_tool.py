"""HWPX 읽기·편집·생성·검증 도구 (표준 라이브러리만 사용).

HWPX는 ZIP 안의 XML 문서다. 이 도구는 본문 텍스트(Contents/section*.xml의 hp:t)만
다루며 문단 모양·글자 모양·표·그림 구조는 건드리지 않는다.
검증은 구조와 텍스트 왕복만 확인하며 한글 프로그램에서의 화면 표시는 확인하지 않는다.
"""
import argparse
import json
import re
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path
import xml.etree.ElementTree as ET

HP = 'http://www.hancom.co.kr/hwpml/2011/paragraph'
OPF = 'http://www.idpf.org/2007/opf/'
SECTION = re.compile(r'Contents/section\d+\.xml')
MIME = b'application/hwp+zip'
TEMPLATE = Path(__file__).resolve().parents[1] / 'assets/blank.hwpx'
PLACEHOLDER = re.compile(r'\{\{[^{}]+\}\}')


class HwpxError(Exception):
    pass


def _q(name):
    return f'{{{HP}}}{name}'


def _register_namespaces(raw):
    """원본 접두사를 유지하도록 모든 네임스페이스를 등록한다."""
    import io
    for _, (prefix, uri) in ET.iterparse(io.BytesIO(raw), events=('start-ns',)):
        try:
            ET.register_namespace(prefix, uri)
        except ValueError:
            pass


def _start_tag(raw_text):
    body = re.sub(r'^\s*<\?xml[^>]*\?>\s*', '', raw_text)
    m = re.match(r'<[^!?/][^>]*>', body)
    return m.group(0) if m else None


def _open_zip(path):
    try:
        return zipfile.ZipFile(path)
    except zipfile.BadZipFile as e:
        raise HwpxError(f'ZIP이 아닙니다. 구형 .hwp 바이너리는 지원하지 않습니다: {path}') from e


def section_names(z):
    return sorted((n for n in z.namelist() if SECTION.fullmatch(n)),
                  key=lambda n: int(re.search(r'\d+', n.rsplit('/', 1)[-1]).group()))


def own_text(p):
    """문단 자신의 텍스트. 표 셀 등 중첩 문단의 텍스트는 포함하지 않는다."""
    out = []
    for run in p.findall(_q('run')):
        for t in run.findall(_q('t')):
            out.append(t.text or '')
            for child in t:
                tag = child.tag.rsplit('}', 1)[-1]
                out.append({'tab': '\t', 'lineBreak': '\n'}.get(tag, ''))
                out.append(child.tail or '')
    return ''.join(out)


def _walk(node, in_table=False):
    for child in node:
        if child.tag == _q('p'):
            yield child, in_table
            yield from _walk(child, in_table)
        else:
            yield from _walk(child, in_table or child.tag == _q('tbl'))


def read_paragraphs(path):
    """문서 순서대로 [{section, index, in_table, text}]를 돌려준다."""
    rows = []
    with _open_zip(path) as z:
        for name in section_names(z):
            root = ET.fromstring(z.read(name))
            for i, (p, in_table) in enumerate(_walk(root)):
                rows.append({'section': name, 'index': i,
                             'in_table': in_table, 'text': own_text(p)})
    return rows


def inspect(path):
    with _open_zip(path) as z:
        names = z.namelist()
        info = z.infolist()[0] if names else None
        sections = section_names(z)
        tables = paragraphs = 0
        for name in sections:
            root = ET.fromstring(z.read(name))
            tables += len(list(root.iter(_q('tbl'))))
            paragraphs += sum(1 for _ in _walk(root))
        has_binary = [n for n in names if n.startswith('BinData/')]
        texts = [r['text'] for r in read_paragraphs(path)]
    placeholders = sorted({m for t in texts for m in PLACEHOLDER.findall(t)})
    return {'entries': len(names), 'sections': sections, 'paragraphs': paragraphs,
            'tables': tables, 'embedded_binaries': has_binary,
            'mimetype_first_and_stored': bool(info and info.filename == 'mimetype'
                                              and info.compress_type == zipfile.ZIP_STORED),
            'placeholders': placeholders,
            'encrypted_or_drm_suspected': any('Encrypt' in n or n.endswith('.enc') for n in names)}


def _replace_in_paragraph(p, old, new):
    """문단 안에서 old를 new로 바꾼다. 여러 런에 걸친 일치도 처리하며
    치환문은 일치가 시작한 런(서식)에 들어간다. 자식 요소(탭 등)가 있는 t는
    경계로 보아 그 너머로 이어지는 일치는 찾지 않는다. 반환값은 치환 횟수."""
    if not old:
        return 0
    nodes = [t for run in p.findall(_q('run')) for t in run.findall(_q('t'))]
    count = 0
    start = 0
    while True:
        segs = [(t, '\x00' if len(t) else (t.text or '')) for t in nodes]
        text = ''.join(s for _, s in segs)
        pos = text.find(old, start)
        if pos < 0:
            return count
        end = pos + len(old)
        offset = 0
        first = True
        for t, s in segs:
            lo, hi = offset, offset + len(s)
            offset = hi
            if hi > pos and lo < end and not len(t):
                a, b = max(pos, lo) - lo, min(end, hi) - lo
                cur = t.text or ''
                t.text = cur[:a] + (new if first else '') + cur[b:]
                first = False
        count += 1
        start = pos + len(new)


def replace_text(path, destination, mapping, allow_missing=False):
    """mapping {old: new}를 모든 구역의 문단에 적용해 destination에 저장한다."""
    if Path(path).resolve() == Path(destination).resolve():
        raise HwpxError('원본을 직접 덮어쓰지 않습니다. 다른 출력 경로를 지정하세요.')
    counts = {k: 0 for k in mapping}
    with _open_zip(path) as zin:
        infos = zin.infolist()
        data = {i.filename: zin.read(i.filename) for i in infos}
        for name in section_names(zin):
            raw = data[name]
            raw_text = raw.decode('utf-8')
            _register_namespaces(raw)
            root = ET.fromstring(raw)
            touched = False
            for p, _ in _walk(root):
                for old, new in mapping.items():
                    n = _replace_in_paragraph(p, old, new)
                    if n:
                        counts[old] += n
                        touched = True
                        for lsa in p.findall(_q('linesegarray')):
                            p.remove(lsa)  # 낡은 줄 배치 정보는 한글이 다시 만든다
            if touched:
                out = ET.tostring(root, encoding='unicode')
                orig_tag, new_tag = _start_tag(raw_text), _start_tag(out)
                if orig_tag and new_tag:
                    out = out.replace(new_tag, orig_tag, 1)
                decl = re.match(r'\s*<\?xml[^>]*\?>', raw_text)
                data[name] = ((decl.group(0) if decl else '<?xml version="1.0" encoding="UTF-8" standalone="yes" ?>')
                              + out).encode('utf-8')
        missing = [k for k, v in counts.items() if v == 0]
        if missing and not allow_missing:
            raise HwpxError('본문에서 찾지 못한 항목: ' + ', '.join(missing))
        if 'Preview/PrvText.txt' in data:
            data['Preview/PrvText.txt'] = '\r\n'.join(
                r['text'] for r in read_paragraphs_from(data)).encode('utf-8')
        _write(destination, infos, data)
    return {'replaced': counts, 'missing': missing}


def read_paragraphs_from(data):
    rows = []
    for name in sorted((n for n in data if SECTION.fullmatch(n)),
                       key=lambda n: int(re.search(r'\d+', n.rsplit('/', 1)[-1]).group())):
        root = ET.fromstring(data[name])
        rows.extend({'text': own_text(p)} for p, in_table in _walk(root) if not in_table)
    return rows


def _write(destination, infos, data):
    with zipfile.ZipFile(destination, 'w', zipfile.ZIP_DEFLATED) as zout:
        zout.writestr('mimetype', data['mimetype'], compress_type=zipfile.ZIP_STORED)
        for info in infos:
            if info.filename == 'mimetype':
                continue
            zout.writestr(info.filename, data[info.filename])


def create(lines, destination, template=None, title=None):
    """빈 서식(기본: assets/blank.hwpx)에 줄 단위 문단을 채워 새 문서를 만든다."""
    template = Path(template or TEMPLATE)
    with zipfile.ZipFile(template) as z:
        infos = z.infolist()
        data = {i.filename: z.read(i.filename) for i in infos}
    raw = data['Contents/section0.xml']
    _register_namespaces(raw)
    root = ET.fromstring(raw)
    first = root.find(_q('p'))
    if first is None or first.find(f'.//{_q("secPr")}') is None:
        raise HwpxError('서식에 구역·쪽 속성이 없습니다.')
    for p in list(root):
        if p is not first:
            root.remove(p)
    for child in list(first):
        if child.tag == _q('linesegarray'):
            first.remove(child)
        elif child.tag == _q('run') and child.find(_q('secPr')) is None:
            first.remove(child)
    for i, line in enumerate(lines):
        p = first if i == 0 else ET.SubElement(root, _q('p'), {
            'id': str(i), 'paraPrIDRef': '0', 'styleIDRef': '0',
            'pageBreak': '0', 'columnBreak': '0', 'merged': '0'})
        run = ET.SubElement(p, _q('run'), {'charPrIDRef': '0'})
        ET.SubElement(run, _q('t')).text = line
    raw_text = raw.decode('utf-8')
    out = ET.tostring(root, encoding='unicode')
    orig_tag, new_tag = _start_tag(raw_text), _start_tag(out)
    if orig_tag and new_tag:
        out = out.replace(new_tag, orig_tag, 1)
    decl = re.match(r'\s*<\?xml[^>]*\?>', raw_text)
    data['Contents/section0.xml'] = ((decl.group(0) if decl else '') + out).encode('utf-8')
    data['Preview/PrvText.txt'] = '\r\n'.join(lines).encode('utf-8')
    data.pop('Preview/PrvImage.png', None)
    infos = [i for i in infos if i.filename != 'Preview/PrvImage.png']
    package = ET.fromstring(data['Contents/content.hpf'])
    _register_namespaces(data['Contents/content.hpf'])
    for item in package.findall(f'.//{{{OPF}}}meta'):
        if item.get('name') in ('creator', 'lastsaveby'):
            item.text = 'hwpx-document'
        if item.get('name') in ('CreatedDate', 'ModifiedDate'):
            item.text = datetime.now(timezone.utc).isoformat()
    t = package.find(f'.//{{{OPF}}}title')
    if t is not None:
        t.text = title if title is not None else (lines[0] if lines else '')
    pkg_raw = data['Contents/content.hpf'].decode('utf-8')
    pkg_out = ET.tostring(package, encoding='unicode')
    ot, nt = _start_tag(pkg_raw), _start_tag(pkg_out)
    if ot and nt:
        pkg_out = pkg_out.replace(nt, ot, 1)
    pdecl = re.match(r'\s*<\?xml[^>]*\?>', pkg_raw)
    data['Contents/content.hpf'] = ((pdecl.group(0) if pdecl else '') + pkg_out).encode('utf-8')
    _write(destination, infos, data)
    return validate(destination, expected_lines=lines)


def validate(path, expected_lines=None):
    with _open_zip(path) as z:
        first = z.infolist()[0]
        if first.filename != 'mimetype' or first.compress_type != zipfile.ZIP_STORED:
            raise HwpxError('첫 항목이 압축 없는 mimetype이 아닙니다.')
        if z.read('mimetype') != MIME:
            raise HwpxError('mimetype 값이 올바르지 않습니다.')
        names = set(z.namelist())
        for n in names:
            if n.endswith(('.xml', '.hpf')):
                ET.fromstring(z.read(n))
        if 'Contents/content.hpf' not in names:
            raise HwpxError('패키지 목록(Contents/content.hpf)이 없습니다.')
        package = ET.fromstring(z.read('Contents/content.hpf'))
        for item in package.findall(f'.//{{{OPF}}}item'):
            href = item.get('href')
            if href and '://' not in href and href not in names:
                raise HwpxError(f'목록에 있으나 없는 항목: {href}')
        if not section_names(z):
            raise HwpxError('본문 구역(Contents/section*.xml)이 없습니다.')
    result = {'structure': 'pass', 'text_roundtrip': 'not_requested',
              'visual_review': 'not_performed', 'schema_validation': 'not_performed',
              'scope': 'ZIP·XML·패키지 링크(·요청 시 텍스트). 한글 프로그램의 화면 표시와 표준 적합성은 확인하지 않음'}
    if expected_lines is not None:
        got = [r['text'] for r in read_paragraphs(path) if not r['in_table']]
        if got != list(expected_lines):
            raise HwpxError('텍스트 왕복 불일치')
        result['text_roundtrip'] = 'pass'
    return result


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest='cmd', required=True)
    s = sub.add_parser('inspect'); s.add_argument('path')
    s = sub.add_parser('read'); s.add_argument('path'); s.add_argument('--json', action='store_true')
    s = sub.add_parser('replace'); s.add_argument('path'); s.add_argument('output')
    s.add_argument('--map', help='{"찾을말": "바꿀말"} JSON 파일')
    s.add_argument('--old'); s.add_argument('--new')
    s.add_argument('--allow-missing', action='store_true')
    s = sub.add_parser('create'); s.add_argument('output'); s.add_argument('--text', required=True, help='한 줄이 한 문단인 UTF-8 텍스트 파일')
    s.add_argument('--template'); s.add_argument('--title')
    s = sub.add_parser('validate'); s.add_argument('path')
    a = ap.parse_args(argv)
    try:
        if a.cmd == 'inspect':
            out = inspect(a.path)
        elif a.cmd == 'read':
            rows = read_paragraphs(a.path)
            if a.json:
                out = rows
            else:
                for r in rows:
                    print(('[표] ' if r['in_table'] else '') + r['text'])
                return 0
        elif a.cmd == 'replace':
            if a.map:
                mapping = json.loads(Path(a.map).read_text(encoding='utf-8'))
            elif a.old is not None and a.new is not None:
                mapping = {a.old: a.new}
            else:
                raise HwpxError('--map 또는 --old/--new가 필요합니다.')
            out = replace_text(a.path, a.output, mapping, a.allow_missing)
            out['validation'] = validate(a.output)
        elif a.cmd == 'create':
            lines = Path(a.text).read_text(encoding='utf-8').splitlines()
            if not lines:
                raise HwpxError('빈 텍스트입니다.')
            out = create(lines, a.output, a.template, a.title)
        else:
            out = validate(a.path)
    except (HwpxError, ET.ParseError, KeyError, OSError, ValueError) as e:
        print(f'오류: {e}', file=sys.stderr)
        return 1
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0


if __name__ == '__main__':
    sys.exit(main())
