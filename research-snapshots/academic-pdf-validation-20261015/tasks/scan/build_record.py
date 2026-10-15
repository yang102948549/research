import json, hashlib, datetime
from pathlib import Path
import fitz

root = Path(__file__).resolve().parent
pdf = root / 'article.pdf'
sha = hashlib.sha256(pdf.read_bytes()).hexdigest()
ocr = json.loads((root/'ocr-page2.json').read_text(encoding='utf8'))
lines = ocr['regions'][0]['lines']
def box(start, stop):
    boxes = [w['pdf_bbox'] for l in lines[start:stop] for w in l['words']]
    return [min(b[0] for b in boxes)-2,min(b[1] for b in boxes)-2,max(b[2] for b in boxes)+2,max(b[3] for b in boxes)+2]
samples = [
 {'evidence_id':'SCAN-E001','excerpt_kind':'prose','lines':[19,21], 'context_lines':[17,22],
  'visual_transcription':'의 窮極的인 目標인 행복과 만족스러운 삶은 보장되지 못할 수 있다는 회의에서',
  'critical_text':'보장되지 못할 수 있다는', 'critical_match':True,
  'claim':'이 구절은 행복과 만족스러운 삶의 보장을 부정적으로 한정한다.',
  'limitation':'김동일·경철인(1980)을 인용하는 문맥이다. 이 논문의 직접 실증결과로 사용할 수 없다.',
  'mutation_to_reject':'행복과 만족스러운 삶은 보장된다는', 'citation_type':'secondary'},
 {'evidence_id':'SCAN-E002','excerpt_kind':'footnote','lines':[63,67], 'context_lines':[60,67],
  'visual_transcription':'Nester E. Terleckyj, Estimates of Possibilities for Improvements in the Quality of Life in the United States, 1971 ~ 1981, Washington: National Planning Association, 1973.',
  'critical_text':'1971 ~ 1981', 'critical_match':False, 'footnote_marker':'1)',
  'claim':'각주 1)의 서지 제목은 1971~1981년을 포함한다.',
  'limitation':'OCR는 기간을 7977 ~ 7987로 오인식했다. 원래 인용된 저작은 확보하지 않았으며 원 논문 각주에 실린 서지의 재인용이다.',
  'mutation_to_reject':'7977 ~ 7987', 'citation_type':'secondary'},
 {'evidence_id':'SCAN-E003','excerpt_kind':'prose','lines':[22,23], 'context_lines':[22,28],
  'visual_transcription':'1960년 美國에서 『國家目標에 관한 大統領諮問',
  'critical_text':'1960년', 'critical_match':False,
  'claim':'본문에 제시된 연도는 1960년이다.',
  'limitation':'OCR는 1960을 1%0으로 인식했다. 역사적 사실 자체의 독립 검증이 아닌 원문 전사 시험이다.',
  'mutation_to_reject':'1%0년', 'citation_type':'secondary'}]
with fitz.open(pdf) as doc:
    page=doc[1]
    for s in samples:
        start,stop=s.pop('lines'); a,b=s.pop('context_lines')
        s.update(paper_id='SCAN-KIHASA-1994-14-2-62',source_sha256=sha,
                 pdf_page=2,printed_page='63',bbox=box(start,stop),context_bbox=box(a,b),
                 original_ocr='\n'.join(l['text'] for l in lines[start:stop]),
                 original_context_ocr='\n'.join(l['text'] for l in lines[a:b]),
                 visual_review={'reviewer':'academic_scan','tool':'PyMuPDF render + view_image','status':'critical_text_match' if s['critical_match'] else 'ocr_mismatch_hold'},
                 evidence_verified=False,human_reviewed=False,
                 gate_expected='hold_until_independent_review' if s['critical_match'] else 'hold_ocr_mismatch')
        path=root/(s['evidence_id']+'.png')
        page.get_pixmap(dpi=240,clip=fitz.Rect(s['context_bbox'])).save(path)
        s['context_image']=str(path)
    pages=[{'pdf_page':i+1,'text_chars':len(p.get_text()),'image_count':len(p.get_image_info()),'image_area_fraction':round(sum((fitz.Rect(im['bbox'])&p.rect).get_area() for im in p.get_image_info())/p.rect.get_area(),5)} for i,p in enumerate(doc)]
record={'research_id':'academic-pdf-validation','paper_id':'SCAN-KIHASA-1994-14-2-62',
 'title':'가족영역에서의 ‘삶의 질’의 분석방법 연구','authors':['장현섭','김현옥'],
 'year':1994,'journal':'보건사회논집','volume':14,'issue':2,'pages':'62-81',
 'pdf_url':'https://www.kihasa.re.kr/hswr/assets/pdf/186/journal-14-2-62.pdf',
 'metadata_url':'https://www.kihasa.re.kr/hswr/v.14/2/62/',
 'sha256':sha,'scan_classification':'publisher-supplied raster scan; no text layer',
 'observed_layout':'first page one column; body two columns; footnotes in right column on PDF page 2',
 'page_diagnostics':pages,'ocr_tested_pages':[2],'ocr_engine':'Windows.Media.Ocr ko, local only','samples':samples,
 'limitations':['Only one selected page OCR-tested; not full-paper semantic validation.','This conceptual paper was not used for numeric table testing.','Page 1 printed number absent; page 2 printed 63 directly observed.']}
(root/'evidence-candidates.json').write_text(json.dumps(record,ensure_ascii=False,indent=2),encoding='utf8')
(root/'search-log.json').write_text(json.dumps({'date':'2026-10-15','query':'site.kihasa.re.kr/hswr "가족영역에서의" "장현섭"','scope':'official publisher web search + one direct PDF download','relevant_results':1,'selected':record['paper_id'],'excluded':'repository research report 94-30.pdf excluded: report not journal article','download_attempts':[{'status':'sandbox_dns_failure'},{'status':'download_success_after_authorized_network_access'}],'source':record['pdf_url'],'sha256':sha},ensure_ascii=False,indent=2),encoding='utf8')
print(sha)
