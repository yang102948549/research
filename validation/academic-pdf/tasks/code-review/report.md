# PDF 근거 게이트 독립 코드 검토

검토자: academic_twocol. 원문 수집/스캔 의미 검토와 분리된 구현 검토. 코드 수정 없음. 검토 범위: pdf_evidence.py, workflow.py의 PDF 검증 연결, parsing.py mixed-layout 변경, test_pdf_evidence.py, 실제 gate-results.json. 2026-10-15.

## P1 — locator 종류 변경으로 PDF 검증을 우회할 수 있음

위치: workflow.py evidence_errors의 locator.kind 분기(대략 186–204행). 실제 원본 파일의 형식과 locator.kind가 일치하는지 검사하지 않는다. html 분기는 section/paragraph/nonprinted_page 유무만 검사하므로 실제 PDF에 HTML 위치를 붙이면 PDF 이미지·페이지·좌표·추출 원문·독립 시각검토를 전부 생략한다.

실제 validation/academic-pdf/ledger.json을 메모리에만 읽어 다음을 수행했다(디스크 저장 없음):

```python
w = Ledger('validation/academic-pdf')
e = copy.deepcopy(w.data['evidence']['TW-E001'])
e['locator'] = dict(kind='html', section='fake', paragraph=1, printed_page=None)
e.pop('pdf_review', None)
e['quote'] = 'Entirely absent invented quote'
w.put('evidence', 'TW-E001', e)
assert w.evidence_errors('TW-E001') == []  # 실제 관측: 오류 없음
w.put('claims', 'review-repro', dict(author='writer', text='invented assertion', evidence_ids=['TW-E001']))
w.review('review-repro', 'independent', 'pass', 'Reproduction only')  # 실제 관측: 승인됨
```

권고: 출처의 실제 파일 형식을 판별하고 locator 종류와 바인딩한다. PDF 확장자가 없거나 다르게 되어 있어도 PDF 원본은 PDF 게이트를 거쳐야 한다. 최소 PDF magic/is_pdf 검사 후 불일치 시 fail closed. 위의 실제 우회와 확장자 변경 케이스를 회귀시험에 추가한다. 지금의 8개 구조 변이 시험에는 locator kind 전환이 빠져 있다.

## 나머지 검토 결과와 범위

- PDF 경로 분기로 진입하는 경우 원본 해시, 실제 페이지 범위, 유한 bbox, context 포함관계, 원본 픽셀 재렌더와 저장 crop 비교, 독립 식별자와 critical feature 기록, native quote 위치 비교가 구현되어 있다. OCR 원문을 그대로 승인하는 method는 차단한다.
- mixed-layout 변경은 spanning body가 있으면 제안 순서를 비워 원본 표가 분해되는 앞선 실제 관측 문제를 보수적으로 처리한다. 이것은 정확한 읽기 순서 복원이 아니라 자동 순서 보류다.
- manual_visual의 전사 정확성과 리뷰어의 실제 원본 열람은 코드가 증명하지 않는다. 코드 주석에 감사 기록이지 인증은 아니라는 한계가 명시되어 있으며, 독립 시각 검토가 여전히 필요하다.
- 위 P1 외에 추가로 재현한 잘못된 통과 사례는 없다. 광범위한 보안 감사·모든 PDF 엔진 호환성 검사를 수행했다는 뜻은 아니다.

## 수정 후 재검토 — P1 재현 경로 차단 확인

동일 실제 academic-pdf 장부를 다시 메모리에만 읽고 위와 똑같이 HTML locator, 가짜 원문, 삭제된 PDF 리뷰를 적용했다. `evidence_errors`는 이제 `PDF source requires PDF locator; format downgrade rejected`를 반환했고, `review(..., 'pass', ...)`도 같은 메시지의 WorkflowError로 거절했다. 디스크 장부는 저장하지 않았다.

코드상 첫 1024바이트의 PDF signature 또는 .pdf 확장자로 실제 출처의 PDF 검증 강등을 차단하는 것을 확인했다. 새 회귀시험은 source.pdf/renamed.bin과 html/xml locator 조합 및 주장 pass 거절을 포함한다. 회귀시험 실행 통과는 총괄이 수행한 결과이며, 독립 검토자는 실제 장부를 통한 원래 HTML 우회 재현이 차단됨을 직접 실행 확인했다. 이 검토에서 발견한 P1은 수정 완료로 판정한다.
