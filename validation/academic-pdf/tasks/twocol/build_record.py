import json, hashlib, sys, re
from pathlib import Path
import fitz

root = Path(__file__).resolve().parent
doc = fitz.open(root/'article.pdf')
sha = hashlib.sha256((root/'article.pdf').read_bytes()).hexdigest()
def norm(s): return re.sub(r'\s+', '', s)
specs = [
 ('TW-E001','negation',2,292,[308,564,502,599], '도서관들이 접근성이 좋지 않은 위치에 자리 잡게 되는 경우들이 발생한 것 또한 사실이다. 이', '접근성이 좋지 않은 위치에 자리 잡는 경우가 발생했다는 저자의 서술', '접근성이 좋은 위치에 자리 잡았다는 반대 주장'),
 ('TW-E002','footnote',1,None,[98,650,490,662], '* 이 논문은 부산대표도서관 건립 기본계획 연구(부산광역시, 2014)를 축약한 것임.', '논문 첫 쪽 별표 각주가 2014년 기본계획 연구의 축약임을 명시한다.', '논문이 2014년 연구와 무관한 독립 연구라는 주장'),
 ('TW-E003','table_cell',4,294,[145,405,280,417], '증축 면적 20% 2,000㎡', '표 1의 증축 면적 행은 비중 20%, 대지면적 2,000㎡이다.', '증축 면적이 30%, 3,000㎡라는 주장'),
 ('TW-E004','table_total',4,294,[130,467,280,480], '합 계 100% 10,000㎡', '표 1 합계는 비중 100%, 대지면적 10,000㎡이다.', '합계 1,000㎡라는 주장')
]
cards=[]
for eid,typ,page,printed,box,trans,claim,mutant in specs:
    text=doc[page-1].get_text(clip=fitz.Rect(box))
    doc[page-1].get_pixmap(matrix=fitz.Matrix(3,3),clip=fitz.Rect(box)).save(root/f'{eid}.png')
    cards.append({'evidence_id':eid,'paper_id':'TW-P001','type':typ,'source_sha256':sha,
      'locator':{'kind':'pdf','pdf_page':page,'printed_page':printed,'bbox':box,
        'printed_page_note':'first page has no visible running page label; journal metadata starts at 291' if printed is None else 'visible running page label inspected'},
      'original_visual_transcription':trans,'extracted_text':text,'normalized_exact_match':norm(text)==norm(trans),
      'interpretation':claim,'translation':None,'negative_control_claim':mutant,
      'source_image':str(root/f'{eid}.png'),'review':{'reviewer':'academic_twocol','visual_checked':True,'semantic_expected_for_original':'pass','semantic_expected_for_mutant':'revise','human_reviewed':False},
      'limits':'A selected local excerpt test, not approval of complete paper or generalized conclusion. Footnote is a first-page provenance footnote, not a long discursive footnote.'})
(root/'evidence-candidates.json').write_text(json.dumps(cards,ensure_ascii=False,indent=2),encoding='utf-8')
record={'research_id':'academic-pdf-validation-20261015','task_id':'twocol','role':'source_and_parsing_validation','input_version':'installed-skill-before-current-turn-fixes','output_paths':[str(root/'article.pdf'),str(root/'extraction.json'),str(root/'evidence-candidates.json')],'paper_ids':['TW-P001'],'evidence_ids':[x[0] for x in specs],'unresolved':['mixed-layout proposed order is wrong; preserve needs_review','complete table structure not inferred','first-page printed label absent','PDF includes trailing blank page 20'], 'verification_status':'selected_visual_excerpts_checked; independent semantic gate pending','next_task':'coordinator independent gate review and parser mixed-layout correction',
 'source':{'title':'지역대표도서관 입지 선정에 관한 연구 - 부산광역시를 중심으로 -','authors':['유재우','구본진','장덕현'],'year':2015,'journal':'한국문헌정보학회지','volume':49,'issue':3,'pages':'291-309','doi':'10.4275/KSLIS.2015.49.3.291','url':'https://www.accesson.kr/kslis/assets/pdf/9356/journal-49-3-291.pdf','sha256':sha,'identity_check':'title/author/year/DOI/journal read in original first-page rendered image; source host official society journal AccessON','pdf_page_count':20,'two_column_visual_pages':[2,4]},
 'search_log':{'date_local':'2026-10-15','queries':['site.accesson.kr/liss "pdf" 도서관','site:accesson.kr/kslis/assets/pdf 도서관'],'scope':'web search discovery, official AccessON journal PDF','visible_results':18,'selection':'first result is real social-science journal, selectable Korean two-column prose, provenance footnote and numeric tables','other_candidates':'not downloaded; no systematic review claim','network_failure':'initial sandbox download DNS failure, escalated read-only official download succeeded'}}
(root/'handoff.json').write_text(json.dumps(record,ensure_ascii=False,indent=2),encoding='utf-8')
print([(c['evidence_id'],c['normalized_exact_match'],c['extracted_text']) for c in cards])
