# 데이터 계약 v0.1

Canonical: `ledger.json`, 총괄만 기록. SQLite 대신 초기 버전은 원자적 JSON 저장 + 파일 잠금 + 저장 전 디스크 해시 비교.
CSV/BibTeX/CSL/HWPX는 파생물이며 변경은 장부와 검토를 거친 뒤 다시 내보낸다.

`Ledger(root,research_id,actor='coordinator')`; `.data`는 읽기/검토용이며 정상 변경은 API를 사용한다.
`put(collection,id,record)` collection은 sources/evidence/claims/paragraphs.
`set_plan('research_question'|'outline', value)`; `save()`; `gate(name)`.

- source: title/authors/year/doi 또는 KCI ID/판본, identity_status, identity_check,
  fulltext_status, parse_status, path, file_hash, source_url, provider_verified.
- evidence: source_id, source_hash(장부 source 레코드 hash), quote, context, translation,
  interpretation, supports_claim_ids, limits, quote_check, locator.
- locator: XML/HTML kind+section+paragraph; PDF kind+pdf_page(1부터)+printed_page(확인한 경우만)+bbox.
  PDF 근거에는 추가로 [원본 이미지·독립 검토 계약](pdf-evidence-contract.md)을 적용한다.
- claim: text, kind(사실/원저자 견해/해석/종합), author, evidence_ids.
- paragraph: text, heading, author, claim_ids. 외부 사실이 없는 전환문도 검토 기록에 그 이유를 남긴다.

의미 검토 전 먼저 원문 바이트·구절 위치가 일치하는지 확인한다.
`review(cid, reviewer, verdict, rationale, review_kind='agent_reviewed')`;
`review_paragraph(pid, reviewer, verdict, rationale, review_kind='agent_reviewed')`.
동일 작성자 검토 거절; timestamp와 검토 대상 해시를 저장한다.
API가 reviewer 문자열의 실제 신원을 인증하지는 않는다. 총괄은 실제 하위 작업 결과를 근거로 기록한다.

`record_feasibility(source_ids,rationale)` 이후 실제 질문 사용자 승인:
`approve('research_question', {'explicit':True,'message_id':<실제 메시지 식별 기록>})`.
개요 승인도 동일. message_id가 제공되지 않는 호스트에서는 사용자 메시지의 정확한 인용·수신시각을
연구 내 approval-message.txt에 저장하고 그 파일을 식별값으로 사용한다. 승인문을 생성하거나 추정하지 않는다.
`approve()`는 실제 인간 발화를 자동 인증하는 보안 기능이 아니므로 호출 출처를 감사한다.

handoff: research_id/task_id/role/input_version/artifact_paths/paper_ids/evidence_ids/
unresolved/verification_status/next_task. 선택: claim_ids, artifact_hashes, assigned_input_version,
reconciliation_note. 총괄이 파일 경로·해시·버전을 확인하고 반영한다.
선택 `contributor_id`는 근거 생성에 기여한 작업자 식별자이며, 그 근거에 연결된 주장·문단의 검토자와 같으면 review가 거절한다(식별자 인증은 아님).
`Ledger.check_argument_map(argmap, required_objection_ids)`는 논증 기록의 구조·연결 오류 목록을 반환한다([인계 계약](orchestration.md) 참조).
`input_version`은 장부 정수 버전이며 `verification_status`는 pending/pass/revise/hold 중 하나다.
`output_paths`나 한글 키·자유 판정문은 이 계약과 다르므로 그대로 commit하지 않는다.
정규화가 필요하면 원본을 보존하고 `assigned_input_version`에 실제 배정 기준을,
`reconciliation_note`에 현재 장부와 재대조한 근거를 기록한다. 단순히 최신 버전값으로 덮어써 오래된 입력을 숨기지 않는다.

`repair(gate,cycle_id='initial')`은 최초 시도 후 수정 최대 2회. 수정을 위해 cycle_id 변경 금지.
`record_export_validation(artifact_path, report)`의 report는 structure_valid/content_reextracted/
citation_alignment=True, material_unresolved=[], visual_status=checked|not_completed를 요구한다.
not_completed이면 검토 원고 생성은 가능하지만 시각 검증을 완료했다고 보고하지 않는다.

초기 엔진 제한: 변경 시 모든 의미 검토를 보수적으로 무효화하며 선택적 의존성 재검증 최적화는 미구현.
Crossref 엄격 비교에서 표기 차이는 충돌로 반환해 사람/총괄의 출처 대조가 필요하다.
원문의 의미·표 숫자·간접 인용 탐지는 독립 검토 작업이며 문자열 검사만으로 통과하지 않는다.
