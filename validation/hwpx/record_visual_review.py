"""Coordinator records completed native UI/render review; does not infer visual quality."""
from pathlib import Path
import sys, json, hashlib, shutil, re
import fitz
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'evidence-paper-workflow/scripts'))
from workflow import Ledger, now
from export import text_of_hwpx
base = Path(__file__).parent
root = Path('C:/Users/USER/Documents/ResearchWorkspace/pilot-kross-2013')
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
assert sha(root/'manuscript.hwpx') == sha(base/'manuscript-revised.hwpx')
with fitz.open(base/'manuscript-revised.pdf') as pdf:
    extracted = ''.join(p.get_text() for p in pdf)
    pages = len(pdf)
norm = lambda s: re.sub(r'\s+', '', s)
assert norm(extracted) == norm(''.join(text_of_hwpx(root/'manuscript.hwpx')))
dest = root/'validation/hwpx'
dest.mkdir(parents=True, exist_ok=True)
for source, target in [('manuscript-revised.pdf','manuscript-hancom.pdf'),('revised-page1.png','page1.png')]:
    shutil.copy2(base/source, dest/target)
review = dict(timestamp=now(), reviewer='coordinator-agent', human_reviewed=False,
    application='Hancom Hangul 2022; native File > Save as PDF',
    hwpx_sha256=sha(root/'manuscript.hwpx'), pdf_sha256=sha(dest/'manuscript-hancom.pdf'),
    pages=pages, pages_visually_reviewed=[1], visual_status='checked',
    rendered_text_match='pass_whitespace_normalized',
    findings=['Korean glyphs, title, five paragraphs, citations, reference DOI readable; no clipping or overlap on all 1 page.',
              'Original justified bibliography spacing repaired with left alignment; reopened revised HWPX and inspected rendered PDF.',
              'Mutable status banner replaced with reference to current verification report.'],
    limitations=['Agent visual review, not human acceptance.', 'Full HWPX schema and full APA typography not certified.'])
(dest/'visual-review.json').write_text(json.dumps(review,ensure_ascii=False,indent=2),encoding='utf-8')
report_path=root/'export-validation.json'
report=json.loads(report_path.read_text(encoding='utf-8'))
report.update(visual_review='checked', native_open='pass', rendered_text_match='pass_whitespace_normalized',
              visual_review_record='validation/hwpx/visual-review.json')
report['template_conversion']='Bundled template, ZIP/XML and exact HWPX re-extraction; Hangul 2022 native open/PDF render and all-page agent visual review. Full schema not validated.'
report_path.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
p=root/'verification-report.md'
s=p.read_text(encoding='utf-8').replace('사람의 원문 검토, HWPX 실제 열기·시각 검증, 전체 스키마 검증은 미완료.', '사람의 원문 검토와 전체 스키마 검증은 미완료. HWPX 실제 열기·렌더링 시각 검증은 완료(에이전트, 한글 2022, 전체 1쪽).')
s+='\n## 후속 실제 렌더링 검증\n\n한글 2022에서 수정본을 열어 PDF로 저장하고 전체 1쪽을 이미지로 대조했다. 한글·본문 인용·참고문헌·DOI의 표시와 잘림·겹침 없음을 확인했다. 영어 참고문헌의 과도한 단어 간격은 왼쪽 정렬로 수정했다. 렌더 PDF와 HWPX 재추출문은 공백 정규화 후 정확히 일치한다. 검토 해시와 범위는 `validation/hwpx/visual-review.json`에 기록했다.\n\n한국어 PDF/OCR은 별도 수능 문제지 및 모의 스캔 시험: 선택 문구 8/10 일치, 부정 표현·상자 문구 실패, 달력 머리글 실패. 모든 OCR 결과는 근거 승인 전 검토 대기다. 실제 학술논문·종이 스캔은 미검증. KCI는 실키 미설정이다.\n'
p.write_text(s,encoding='utf-8')
w=Ledger(root)
validation=dict(w.data['export_validation'])
validation['visual_status']='checked'
validation['visual_review_record']='validation/hwpx/visual-review.json'
validation['output_hashes']={name:sha(root/name) for name in validation['output_hashes']}
for name in ('visual-review.json','manuscript-hancom.pdf','page1.png'):
    validation['output_hashes']['validation/hwpx/'+name]=sha(dest/name)
w.record_export_validation('manuscript.hwpx',validation)
w.save()
assert Ledger(root).gate('final')['pass']
completion=root/'pilot-completion.json'
d=json.loads(completion.read_text(encoding='utf-8'))
d.update(visual_review='checked', visual_review_record='validation/hwpx/visual-review.json')
completion.write_text(json.dumps(d,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(review,ensure_ascii=False))
