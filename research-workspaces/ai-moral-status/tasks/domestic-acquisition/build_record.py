import json, hashlib
from pathlib import Path
import pymupdf

root = Path(__file__).parent
ids = [('KR001','ART003263554'),('KR002','ART003155341'),('KR003','ART002439977'),('KR004','ART003160334'),('KR005','ART003160318')]
records = []
for paper, article in ids:
    preview = paper == 'KR001'
    path = root / (article + ('-preview.pdf' if preview else '.pdf'))
    doc = pymupdf.open(path)
    text_path = path.with_suffix('.pages.json')
    text_path.write_text(json.dumps([{'pdf_page':i+1,'text':p.get_text()} for i,p in enumerate(doc)],ensure_ascii=False,indent=2),encoding='utf-8')
    url = ('https://www.kci.go.kr/kciportal/ci/sereArticleSearch/artiPreView.kci?sereArticleSearchBean.artiId='+article+'&v=2019') if preview else ('https://www.kci.go.kr/kciportal/ci/sereArticleSearch/ciSereArtiOrteServHistIFrame.kci?sereArticleSearchBean.artiId='+article+'&sereArticleSearchBean.orteFileId=KCI_FI'+article[3:])
    records.append({'paper_id':paper,'kci_id':article,'source_url':url,'path':str(path.resolve()),'file_hash':hashlib.sha256(path.read_bytes()).hexdigest(),'size_bytes':path.stat().st_size,'pdf_pages':len(doc),'fulltext_status':'preview_only' if preview else 'acquired','identity_status':'first_page_title_author_matched','parse_status':'text_extracted_not_reviewed','evidence_verified':False,'text_path':str(text_path.resolve()),'notes':'KCI explicitly offers preview only; one-page abstract; no full body acquired.' if preview else 'Public KCI download via page-established session and Referer; direct request initially returned guidance to use KCI homepage. Last PDF page has no extracted text; bibliographic page count must not equal physical PDF page count.'})
data = {'research_id':'ai-moral-status','task_id':'domestic-acquisition','role':'fulltext_acquisition','input_version':1,'date':'2026-10-15','timezone':'Asia/Seoul','paper_ids':[x[0] for x in ids],'evidence_ids':[],'verification_status':'hold','records':records,'artifact_paths':[str(p.resolve()) for p in root.iterdir() if p.is_file()],'attempts':[{'scope':'all five','method':'Fetched official KCI article HTML and inspected actually exposed download/preview actions. HTML saved with KCI article IDs.'},{'scope':'KR002-KR005','method':'Initial direct download returned HTML: 원문 직접 열람이 불가능합니다. KCI 홈페이지에서 열람하세요. Then loaded article page and invoked its exact public link within same session, with page Referer; returned PDF.'},{'scope':'KR001','method':'Exact DOI web search found KCI and PhilPapers metadata only. KCI offers 원문 미리보기 instead of full download. Followed public embedded preview URL; returned 1-page PDF. No access restriction bypass attempted.'}],'search_queries':['"10.20433/jnkpa.2025.10.177"','"인공지능의 도덕적 지위와 관계론적 접근" filetype:pdf','"동물과 AI를 통한 인간의 도덕적 지위 탐구" pdf'],'unresolved':['KR001 full body unavailable in these bounded attempts; preview only.','Acquisition does not constitute semantic evidence validation.','KR004 last text page is printed 179 and final PDF page has no extracted text; KCI metadata ends 180. Retain discrepancy until visual review.'],'next_task':'Extract bounded, page-located evidence from KR002-KR005 and conduct independent source review; keep KR001 abstract-only pending lawful publisher/library access.'}
(root/'acquisition.json').write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'acquired_fulltext':4,'preview_only':1,'record':str((root/'acquisition.json').resolve())},ensure_ascii=False))
