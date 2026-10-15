# PDF 근거의 원문 추적 계약

`pdf_evidence.py`는 원본 페이지·좌표·검토 이미지의 대응을 검사한다. 의미 판정이나 검토자의 실제 신원을 자동 인증하지 않는다. 작성과 분리된 에이전트가 실제 원본과 앞뒤 문맥을 보고 판단한 뒤 총괄이 기록해야 한다.

1. `locator`: `kind=pdf`, 실제 1부터 시작하는 `pdf_page`, 페이지 안의 유한한 `bbox=[x0,y0,x1,y1]`, 확인한 `printed_page` 또는 null. `context_bbox`는 인용 영역을 포함하는 문맥 영역이다. 표는 머리글·행·단위·주석을 포함하는 문맥 좌표가 필수다. 인쇄 쪽수는 화면에서 확인하며, 서지상 시작 쪽수는 별도 메타데이터로만 저장한다.
2. 근거: `author`, `excerpt_kind=prose|footnote|table`, `transcription_method=native_text|manual_visual`, `citation_type=direct|secondary`. `direct`는 현재 확보한 원문의 직접 진술이며, 원문이 인용한 다른 저작을 확보했다는 뜻으로 쓰지 않는다. 각주는 `footnote_marker`, 표는 `table_context={label,row,column,unit}`를 기록한다. 단위가 없으면 그 사실을 명시한다.
3. `native_text`는 해당 좌표에서 추출한 글과 공백 정규화 후 일치해야 한다. 일치는 의미·읽기 순서 검증이 아니다. 스캔/추출 오류는 `manual_visual`과 `transcription_note`를 쓰고, 원 OCR는 `ocr_text_raw`/`ocr_context_raw`로 분리 보존한다. 숫자·부정 표현을 추측해 수정하지 않는다.
4. `render_proof(source_path, locator, crop_path, dpi=150)`로 검토용 PNG를 만든다. 이 함수는 판정을 만들지 않는다. 반환된 `proof`에 연구 루트 기준 `crop_path`를 추가한다. 주석 오버레이를 제외한 원 PDF 렌더를 기준으로 한다. 페이지 전체도 읽어 문맥을 확인한다.
5. 독립 검토 후 `pdf_review`에 `reviewer`, `timestamp`, `verdict=pass|revise|hold`, `rationale`, `proof`, 원 검토 기록의 경로를 보존한다. `checked_features`에는 실제 확인한 `reading_order, context, negation, numbers, page_label, citation_status`를 기록한다. 각주는 `footnote_marker`, 표는 `table_headers, table_units, table_notes`를 추가한다. 해당 항목이 없으면 이유를 검토 기록에 남기고 불필요하게 내용을 만들어내지 않는다.
6. 최종 근거의 `binding(evidence)`를 `pdf_review.evidence_binding`에 기록한다. 생성 이후 구절·맥락·쪽수·좌표·인용 유형 등이 바뀌면 검토를 다시 받아야 한다. 이전 기록의 해시만 다시 계산해 변경을 승인하지 않는다.

`Ledger.evidence_errors(eid)`는 미검토·변경된 근거, 범위 밖 쪽수, 원본과 다른 검토 이미지, native 구절 불일치, 미검토 raw OCR를 거부한다. 실제 PDF 원문을 HTML/XML 위치 유형으로 바꿔 PDF 검사를 우회할 수 없다. 검토자는 이어서 주장의 범위·부정·재인용·표의 행과 단위를 대조하고 `review()`에 의미 판정을 남긴다. 문구 일치 검사만으로 의미 검토를 대체할 수 없다.

실제 학술논문 시험에서 전폭 표와 2단 본문이 섞인 페이지의 읽기 순서 제안이 표를 분해했고, 실스캔의 각주 기간과 본문 연도가 오인식됐다. `reading_order_blockers`가 있거나 `layout_status=unknown_no_native_text`이면 원본을 수동 확인한다. 문서 전체의 파싱 품질과 선택한 근거 영역의 검토 범위를 구분한다. [실제 학술논문 검증 결과](academic-pdf-validation.md)를 참고한다.

## 스캔 표의 선택 셀 추적

`manual_visual` 표에는 `table_context.cell_trace`가 필수다. 전체 표 자동 복원을 뜻하지 않으며, 선택 셀마다 다음을 원본에서 확인한다. 복잡한 텍스트 표에도 이 형식을 사용할 수 있다.

- `value`: 원문 그대로의 선택 셀(quote와 일치), `bbox`: locator와 동일. 괄호 안 인원수와 백분율을 혼동하지 않는다.
- `row_index`, `column_index`: 패널 내부 0부터 시작하는 행·열. `row_headers`, `column_headers`는 상위에서 하위 순서의 `{text,bbox,span:[시작,끝]}` 목록이다. 병합/묶음 범위는 선택 인덱스를 포함하며 자식 범위는 부모 안에 있어야 한다. table_context의 row/column은 텍스트를 ` > `로 연결한다.
- `unit`: `{text,status:printed|not_printed,bbox}`. 인쇄 단위가 없으면 rationale을 기록한다. 합계 셀의 `100.00 (548)`은 `% (명)`처럼 혼합 단위를 명시한다.
- `notes`: 원본 주석 목록의 `{text,bbox,scope,applies_to_cell:boolean}`. 관련 없는 주석도 범위를 구분한다. 주석이 없으면 해당 사실과 표 영역 bbox를 명시한 항목을 기록한다. `population_scope`에 분모/응답 대상 제한을 기록한다.
- 검토자는 `merged_headers,cell_mapping,note_scope,unit_origin`도 확인한다. 모든 좌표는 검토용 context 안에 있어야 한다. 원 OCR 및 오류가 난 토큰은 별도로 보존한다.

코드는 구조·해시·좌표 대응을 확인한다. 독립 검토자는 숫자, 부정 표현, 그룹의 적용 범위, 가중치·결측·제외 조건과 유의성 기호를 직접 대조한다. 원문의 합계 불일치는 OCR 오류와 구분하고 임의로 합계100에 맞추지 않는다. 실제 원문에 없는 숫자를 새 pass 기록으로 위조하는 행위를 코드가 의미적으로 판별한다고 주장하지 않는다.
