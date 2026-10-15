"""Prepare the real-source pilot; never fabricate either user approval."""
import argparse
import hashlib
import json
from pathlib import Path
from datetime import datetime, timezone, timedelta
from xml.etree import ElementTree as ET
from workflow import Ledger
from parsing import jats_blocks

QUESTION = {'text': 'Kross 외(2013)의 Facebook 이용과 주관적 안녕감 연구가 뒷받침하는 주장과 인과·일반화의 한계는 무엇인가?',
            'scope': '공개 원문 1편의 근거 추적 기술 시험. 분야 전체 문헌고찰이나 최신 결론이 아님.',
            'review_type': 'single_source_methodological_pilot', 'language': 'ko',
            'length': '사용자가 승인할 짧은 시험 원고', 'venue': None, 'deadline': None}

def prepare(root):
    root = Path(root)
    ledger = Ledger(root, 'pilot-kross-2013')
    source_file = root / 'sources/article.xml'
    lock = json.loads((Path(__file__).resolve().parents[1] / 'assets/pilot-source-lock.json').read_text(encoding='utf-8'))
    for name, expected in lock['files'].items():
        if hashlib.sha256((root / 'sources' / name).read_bytes()).hexdigest() != expected:
            raise ValueError('Pilot bytes differ from manually inspected snapshot; re-review required')
    article = ET.parse(source_file).getroot()
    metadata = json.loads((root / 'sources/crossref.json').read_text(encoding='utf-8'))['message']
    title = ''.join(article.find('.//article-title').itertext())
    doi = next(n.text for n in article.findall('.//article-id') if n.get('pub-id-type') == 'doi')
    names = [x.findtext('surname') for x in article.findall('.//article-meta/contrib-group[@content-type="author"]/contrib/name')]
    years = {int(n.text) for n in article.findall('.//article-meta/pub-date/year')}
    match = (title.casefold() == metadata['title'][0].casefold() and doi.lower() == metadata['DOI'].lower()
             and names == [x['family'] for x in metadata['author']]
             and metadata['published']['date-parts'][0][0] in years)
    if not match:
        raise ValueError('Pilot source identity conflict')
    extraction = jats_blocks(source_file)
    (root / 'extracted').mkdir(exist_ok=True)
    (root / 'extracted/article.json').write_text(json.dumps(extraction, ensure_ascii=False, indent=2), encoding='utf-8')
    ref = ('Kross, E., Verduyn, P., Demiralp, E., Park, J., Lee, D. S., Lin, N., Shablack, H., '
           'Jonides, J., & Ybarra, O. (2013). Facebook use predicts declines in subjective well-being '
           'in young adults. PLOS ONE, 8(8), e69841. https://doi.org/10.1371/journal.pone.0069841')
    csl = {'type': 'article-journal', 'title': title, 'author': [dict(family=x['family'], given=x['given']) for x in metadata['author']],
           'issued': {'date-parts': [[2013]]}, 'container-title': 'PLOS ONE', 'volume': '8', 'issue': '8',
           'page': 'e69841', 'DOI': doi}
    bib = '@article{S001,\n  title = {' + title + '},\n  author = {' + ' and '.join(x['family']+', '+x['given'] for x in metadata['author']) + '},\n  year = {2013},\n  journal = {PLOS ONE},\n  volume = {8},\n  number = {8},\n  pages = {e69841},\n  doi = {'+doi+'}\n}'
    ledger.put('sources', 'S001', {'title': title, 'doi': doi, 'authors': names, 'year': 2013,
        'identity_status': 'matched', 'identity_check': 'Crossref DOI/title/ordered author surnames/year compared with original JATS front matter',
        'fulltext_status': 'available', 'parse_status': 'checked', 'parse_review': 'Coordinator read body sections, method and limitations in JATS; no table evidence used',
        'path': 'sources/article.xml', 'file_hash': hashlib.sha256(source_file.read_bytes()).hexdigest(),
        'citation_label': 'Kross et al., 2013', 'reference_text': ref, 'csl': csl, 'bibtex': bib,
        'provider_verified': None, 'human_reviewed': False,
        'correction_retraction_status': 'not_comprehensively_checked', 'source_url': 'https://www.ebi.ac.uk/europepmc/webservices/rest/PMC3743827/fullTextXML'})
    ledger.set_plan('research_question', QUESTION)
    ledger.record_feasibility(['S001'], 'Full original XML, original metadata and Crossref match; explicit results and causal/generalization limitations are present.')
    ledger.save()
    (root / 'research-question.json').write_text(json.dumps(QUESTION, ensure_ascii=False, indent=2), encoding='utf-8')
    search = {'purpose': 'known-item feasibility pilot; not systematic search', 'date': lock['reviewed_at'],
              'queries': [{'source': 'Crossref', 'query': doi, 'scope': 'single DOI', 'retrieved_count': 1},
                          {'source': 'Europe PMC', 'query': 'PMC3743827/fullTextXML', 'scope': 'single known item', 'retrieved_count': 1}],
              'selection': [{'paper_id': 'S001', 'decision': 'include', 'reason': 'public full text and explicit causal limitations for integration test'}],
              'failed_candidates': [{'id': 'PMC4066473', 'reason': 'fullTextXML acquisition failed; no evidence extracted'}],
              'kci': 'not_searched', 'paid_services': 'not_configured'}
    (root / 'search-log.json').write_text(json.dumps(search, ensure_ascii=False, indent=2), encoding='utf-8')
    return ledger

def outline(root):
    ledger = Ledger(root)
    if not ledger.gate('research_question')['pass']:
        raise ValueError('Research-question approval required before evidence outline')
    blocks = jats_blocks(ledger.root / 'sources/article.xml')['blocks']
    def para(sec, n):
        return next(b['text'] for b in blocks if b['locator']['section']==sec and b['locator']['paragraph']==n)
    entries = [
        ('E001','C001','s2c2',1, 'Participants were text-messaged 5 times per day between 10am and midnight over 14-days.',
         '연구진은 14일 동안 하루 다섯 차례 문자메시지를 보내 참여자의 경험을 조사했다', '방법 보고',
         '원문에 보고된 자료 수집 절차이며 무작위 처치 실험을 뜻하지 않는다.'),
        ('E002','C002','s4',1, 'These analyses indicated that Facebook use predicts declines in the two components of subjective well-being: how people feel moment to moment and how satisfied they are with their lives.',
         '연구진은 Facebook 이용이 순간적 감정과 삶의 만족도라는 두 안녕감 요소의 저하를 예측한다고 보고했다', '원저자 결과 보고',
         '해당 표본과 분석에서의 예측 관계이며 모든 이용자에게 동일한 인과 효과가 있다는 주장이 아니다.'),
        ('E003','C003','s4a',3, 'experiments that manipulate Facebook use in daily life are needed to corroborate these findings and establish definitive causal relations.',
         '저자들은 명확한 인과관계를 확립하려면 일상생활에서 Facebook 이용을 조작하는 실험이 필요하다고 밝혔다', '원저자 한계',
         '종단 분석의 시간적 정보와 확정적인 인과관계를 구분해야 한다.'),
        ('E004','C004','s4a',1, 'However, examining whether these findings generalize to additional age groups is important.',
         '저자들은 다른 연령집단에 대한 일반화 여부를 추가로 검토할 필요가 있다고 밝혔다', '원저자 한계',
         '청년 중심의 단일 연구를 다른 연령층이나 모든 소셜네트워크로 확대하지 않는다.'),
    ]
    for eid,cid,sec,n,quote,text,kind,limits in entries:
        context = para(sec,n)
        if quote not in context:
            raise ValueError('Quote does not occur at exact locator: '+eid)
        ledger.put('evidence', eid, {'source_id':'S001', 'source_hash':ledger.data['sources']['S001']['hash'],
            'quote':quote, 'context':context, 'translation':text, 'interpretation':text,
            'supports_claim_ids':[cid], 'limits':limits, 'quote_check':'source_compared',
            'locator':{'kind':'xml','section':sec,'paragraph':n,'printed_page':None}})
        ledger.put('claims', cid, {'text':text,'kind':kind,'author':'coordinator','evidence_ids':[eid]})
    outline_data = {'version':1, 'thesis':'원문의 예측 관계와 인과·일반화의 한계를 구분한다.',
        'sections':[{'title':'서론: 검토 대상과 방법','claim_ids':['C001'],'evidence_ids':['E001']},
                    {'title':'본론: 보고된 관계와 해석의 한계','claim_ids':['C002','C003','C004'],'evidence_ids':['E002','E003','E004']},
                    {'title':'결론: 주장 범위','claim_ids':['C003','C004'],'evidence_ids':['E003','E004']}],
        'limits':'단일 논문 기술 시험. 체계적 검색·분야 전체 결론·독자적 실증 결과 없음.'}
    ledger.set_plan('outline', outline_data)
    ledger.save()
    (ledger.root/'outline-v1.json').write_text(json.dumps(outline_data,ensure_ascii=False,indent=2),encoding='utf-8')
    return ledger

if __name__ == '__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('action',choices=['prepare','outline'])
    parser.add_argument('root',type=Path)
    args=parser.parse_args()
    ledger=prepare(args.root) if args.action=='prepare' else outline(args.root)
    print(json.dumps({'version':ledger.data['version'],'question_gate':ledger.gate('research_question')},ensure_ascii=False))
