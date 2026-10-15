import json, hashlib, datetime, csv
from pathlib import Path
import fitz

root=Path(__file__).parent
def write(name,value):
    (root/name).write_text(json.dumps(value,ensure_ascii=False,indent=2),encoding='utf-8')
def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
pdf=root/'article.pdf'
d=fitz.open(pdf)
scale=524.4000244140625/1343
def box(x0,y0,x1,y1): return [round(v*scale,3) for v in [x0,y0,x1,y1]]
panels=[
 ('income','주수입원 형태','2',['자립형','의존형','계(명)'],[['48.4','51.6','100.00 (2,048)'],['61.9','38.1','100.00 (1,250)'],['27.3','72.7','100.00 (797)'],['67.2','32.8','100.00 (811)'],['36.1','63.9','100.00 (1,236)'],['42.1','57.9','100.00 (1,166)'],['56.8','43.2','100.00 (882)']]),
 ('economy','주관적 경제평가','3',['어렵다','어렵지 않다','계(명)'],[['77.68','20.32','100.00 (2,054)'],['81.00','19.00','100.00 (1,251)'],['77.63','22.37','100.00 (802)'],['77.51','22.49','100.00 (815)'],['81.11','18.89','100.00 (1,239)'],['76.71','23.29','100.00 (1,168)'],['83.60','16.40','100.00 (885)']]),
 ('physical','신체적 부양자','4',['없음','있음','계(명)'],[['46.71','53.29','100.00 (548)'],['58.31','41.69','100.00 (207)'],['39.69','60.31','100.00 (342)'],['47.78','52.22','100.00 (164)'],['46.25','53.75','100.00 (385)'],['44.14','55.86','100.00 (288)'],['49.54','50.46','100.00 (261)']]),
 ('physical_satisfaction','신체적 부양 만족정도','5',['부족하다','부족하지 않다','계(명)'],[['15.92','84.08','100.00 (292)'],['24.26','75.74','100.00 (86)'],['12.46','87.54','100.00 (206)'],['7.00','93.00','100.00 (85)'],['19.59','80.41','100.00 (207)'],['15.71','84.29','100.00 (161)'],['16.19','83.81','100.00 (131)']]),
 ('emotional','정서적 부양자','6',['없음','있음','계(명)'],[['23.50','76.50','100.00 (1,946)'],['20.37','79.63','100.00 (1,221)'],['28.77','71.23','100.00 (725)'],['19.73','80.27','100.00 (775)'],['25.99','74.01','100.00 (1,170)'],['21.59','78.41','100.00 (1,113)'],['26.04','73.96','100.00 (832)']]),
 ('emotional_satisfaction','정서적 부양 만족정도','7',['부족하다','부족하지 않다','계(명)'],[['10.22','89.78','100.00 (1,487)'],['9.86','90.14','100.00 (972)'],['10.90','89.10','100.00 (516)'],['8.27','91.73','100.00 (622)'],['11.63','88.37','100.00 (865)'],['9.92','90.08','100.00 (873)'],['10.64','89.36','100.00 (614)']])]
row_paths=[['전체'],['연령','전기'],['연령','후기'],['성','남자'],['성','여자'],['지역','시부'],['지역','군부']]
ys=[[590,629,656,682,709,736,763],[897,936,962,989,1015,1043,1069],[1197,1236,1263,1289,1316,1343,1370]]
header_ys=[(483,522),(783,820),(1090,1128)]
cells=[]; groups=[]
for i,(pid,title,note,cols,rows) in enumerate(panels):
    left=i%2==0; xs=[(330,414),(435,512),(530,661)] if left else [(855,944),(963,1052),(1066,1198)]
    groups.append({'id':pid,'label':title,'row':0,'column':0,'row_span':1,'column_span':3,'bbox':box(xs[0][0],header_ys[i//2][0],xs[2][1],header_ys[i//2][1]),'note_ids':[note],'children':cols,'row_groups':[{'label':g,'row_start':r,'row_span':2} for g,r in [('연령',1),('성',3),('지역',5)]]})
    for r,values in enumerate(rows):
        for c,value in enumerate(values):
            cells.append({'id':f'{pid}-r{r+1}-c{c+1}','panel_id':pid,'row_index':r,'column_index':c,'row_path':row_paths[r],'column_path':[title,cols[c]],'value':value,'unit':'%' if c<2 else '%; 괄호 안 명','bbox':box(xs[c][0],ys[i//2][r]-12,xs[c][1],ys[i//2][r]+12),'note_ids':['1',note],'author':'scan_table_source','verification_status':'pending'})
notes=[('1','승수부여 관계로 총계가 일치하지 않을 수 있음.'),('2','무응답 10명 제외함.'),('3','무응답 4명 제외함.'),('4','일상생활 수행에 제한을 받고 있는 노인에 대한 분포임.'),('5','신체적 부양을 받고 있는 노인에 대한 분포임.'),('6','대리응답 111명, 무응답 1명 제외함.'),('7','정서적 부양을 받고 있는 노인에 대한 분포임(무응답 2명 제외함).'),('8','*: p<0.05')]
data={'paper_id':'LEE1994','source_sha256':sha(pdf),'pdf_page':5,'printed_page':'7','table_id':'표2','table_title':'年齡·性 및 地域에 따른 扶養實態의 分布','unit_label':'(단위: %)','table_bbox':box(130,430,1205,1645),'coordinate_space':'PDF points; approximate manually selected bounds, re-render for independent verification','merged_headers':groups,'cells':cells,'notes':[{'id':n,'text':t,'bbox':box(130,1422+(int(n)-1)*27,1000,1450+(int(n)-1)*27)} for n,t in notes],'source_anomalies':[{'cell_id':'economy-r1-c1','observation':'원본은 77.68로 읽힘. 인접 20.32와 합이98.00이며 총계100.00과 다름. 원문을79.68로 교정하지 않음.','status':'hold_for_interpretation'}],'status':'pending_independent_visual_review'}
write('table-transcription.json',data)
with (root/'cells.csv').open('w',newline='',encoding='utf-8-sig') as f:
    w=csv.writer(f); w.writerow(['id','row_path','column_path','value','unit','bbox','note_ids']);w.writerows([c['id'],' > '.join(c['row_path']),' > '.join(c['column_path']),c['value'],c['unit'],json.dumps(c['bbox']),','.join(c['note_ids'])] for c in cells)
r=json.loads((root/'ocr-page5.json').read_text(encoding='utf-8'));(root/'ocr-page5.txt').write_text(r['text'],encoding='utf-8')
for name,b in [('table',data['table_bbox']),('header',box(130,432,1205,570)),('notes',box(130,1410,1205,1640))]:
    d[4].get_pixmap(dpi=250,clip=fitz.Rect(b)).save(root/f'{name}.png')
write('metadata.json',{'paper_id':'LEE1994','title':'취약계층 노인의 부양실태 비교분석','authors':['이가옥','서미경','김정석'],'year':1994,'journal':'보건사회논집','volume':'14','issue':'2','pages':'3-19','metadata_url':'https://www.kihasa.re.kr/hswr/v.14/2/1994','source_url':'https://www.kihasa.re.kr/hswr/assets/pdf/191/journal-14-2-3.pdf','source_sha256':sha(pdf),'page_count':len(d),'scan_checks':[{'pdf_page':i+1,'text_characters':len(p.get_text()),'image_count':len(p.get_images())} for i,p in enumerate(d)],'not_synthetic':True,'identity_status':'metadata_compared','authors_initial_guess_corrected_before_artifact':True})
write('search-log.json',{'timestamp_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'scope':'official KIHASA journal archive; no KCI authenticated search','queries':['site:kihasa.re.kr/hswr 1994 소득','site:kihasa.re.kr/hswr 1995 빈곤'],'issue_url':'https://www.kihasa.re.kr/hswr/v.14/2/1994','selection':'First empirical elderly support article selected after contact-sheet inspection; 17 original scan pages. Table2 selected for6panels,3columns each,grouped rows,units8notes.','network_failure':'sandbox DNS failed; approved external read retry succeeded','ocr_failure':'sandbox Windows OCR E_ACCESSDENIED; approved local OCR retry succeeded','result_count_in_issue':8,'downloaded_papers':1})
write('handoff.json',{'research_id':'scan-table-validation-20261015','task_id':'source','role':'source_acquisition_and_table_transcription','input_version':0,'artifact_paths':['tasks/source/'+p.name for p in root.iterdir() if p.is_file() and p.name!='handoff.json'],'paper_ids':['LEE1994'],'evidence_ids':[],'unresolved':['Independent reviewer must check126cells and notes; source economic total discrepancy must remain hold; coordinates approximate.'],'verification_status':'pending','next_task':'independent_scan_table_review'})
