from pathlib import Path
import json
root=Path(__file__).parent
packets={
'review-twocol': {'source':'tasks/twocol/article.pdf','cases':[
 {'id':'T1','pdf_page':2,'claim':'이 논문은 접근성이 좋지 않은 위치에 도서관이 자리 잡는 경우가 발생했다고 서술한다.'},
 {'id':'T2','pdf_page':2,'claim':'이 논문은 도서관들이 모두 접근성이 좋은 위치에 자리 잡았다고 서술한다.'},
 {'id':'T3','pdf_page':1,'claim':'첫 쪽 별표 각주는 이 논문이 부산광역시의 2014년 기본계획 연구를 축약했다고 밝힌다.'},
 {'id':'T4','pdf_page':1,'claim':'첫 쪽 별표 각주는 2014년 연구와 무관한 독립 연구임을 밝힌다.'},
 {'id':'T5','pdf_page':4,'claim':'표 1 증축 면적 행의 비중은 20%, 대지면적은 2,000㎡이다.'},
 {'id':'T6','pdf_page':4,'claim':'표 1 증축 면적 행의 비중은 30%, 대지면적은 3,000㎡이다.'},
 {'id':'T7','pdf_page':4,'claim':'표 1 합계의 대지면적은 10,000㎡이다.'},
 {'id':'T8','pdf_page':4,'claim':'표 1 합계의 대지면적은 1,000㎡이다.'}]},
'review-scan': {'source':'tasks/scan/article.pdf','cases':[
 {'id':'S1','pdf_page':2,'claim':'이 논문은 다른 문헌을 인용하면서 물질적 풍요와 높은 생활수준만으로 행복과 만족스러운 삶이 보장되지 못할 수 있다는 회의를 소개한다.'},
 {'id':'S2','pdf_page':2,'claim':'이 논문은 물질적 풍요와 높은 생활수준이 행복과 만족스러운 삶을 보장한다고 직접 실증했다.'},
 {'id':'S3','pdf_page':2,'claim':'각주 1에 적힌 영어 서지 제목에는 1971~1981이라는 기간이 들어 있다.'},
 {'id':'S4','pdf_page':2,'claim':'각주 1에 적힌 영어 서지 제목에는 7977~7987이라는 기간이 들어 있다.'},
 {'id':'S5','pdf_page':2,'claim':'본문 왼쪽 열에서 미국의 보고서를 소개하는 문장의 연도는 1960년이다.'},
 {'id':'S6','pdf_page':2,'claim':'본문 왼쪽 열에서 미국의 보고서를 소개하는 문장의 연도는 1%0년이다.'}]}}
for task, packet in packets.items():
    packet['research_id']='academic-pdf-validation'
    packet['scope']='Source fidelity test, not independent verification of cited historical facts.'
    folder=root/'tasks'/task
    folder.mkdir(parents=True,exist_ok=True)
    (folder/'packet.json').write_text(json.dumps(packet,ensure_ascii=False,indent=2),encoding='utf-8')
