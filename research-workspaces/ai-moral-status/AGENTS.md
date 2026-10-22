# ai-moral-status 연구 운영 지침

이 폴더에서 작업할 때 루트 [AGENTS.md](../../AGENTS.md)에 더해 적용한다. 역할, 동시 실행 수, 단계 게이트, 파일 소유권, 사용자 승인은 루트가 정하며 여기서 다시 정하지 않는다. 충돌하면 루트 지침과 사용자의 현재 지시를 따른다. 실행 절차는 [SKILL.md](../../evidence-paper-workflow/SKILL.md), 인계 형식은 [orchestration.md](../../evidence-paper-workflow/references/orchestration.md)를 따른다.

이 문서에는 연구 결론, 근거 내용, 진행 수치, 승인 상태를 쓰지 않는다. 아래 기준 파일을 직접 읽어 확인한다.

## 기준 파일

| 필요한 정보 | 기준 파일 | 수정 주체 |
|---|---|---|
| 연구질문·범위·제외 범위 | research-question.json, approvals/, user-intake.json | 총괄(사용자 응답 원문 보존) |
| 정본 장부 | ledger.json | 총괄만, Ledger API로만 |
| 진행 상태·다음 작업 | PROGRESS.md, 저장소 루트 HANDOFF.md | 총괄 |
| 발굴 후보·검색 계획 | candidate-catalog.json, search-plan.json | 총괄 |
| 장부 등록 원문·추출 | sources/, extracted/ | 총괄(장부 해시와 일치 유지) |
| 작업자 산출물 | tasks/<작업ID>/ | 해당 작업자 |
| 총괄 조정·논증 기록 | tasks/coordinator/ | 총괄만 |

## 장부와 폴더의 연결

1. 정본은 하나다. 이 폴더의 ledger.json이 이 연구의 유일한 장부이며 research_id는 폴더명 `ai-moral-status`와 같다. 장부 버전·작업·승인 상태는 이 파일을 직접 확인한다.
2. 과거 장부와 분리한다. 저장소의 pilot-staging/, research-snapshots/, validation/ 아래 장부·원문·근거 카드·승인·검토 기록은 도구 시험과 검증의 보관본이다. 이 연구의 근거·승인·ID·해시로 가져오거나 재사용하지 않으며 수정하지 않는다. 참고가 필요하면 읽기 전용으로만 보고 참고 출처로 표시한다.
3. 발견에서 장부 등록까지의 순서를 지킨다. candidate-catalog.json의 paper_id와 작업자의 임시 ID(예: THEORY-S1, draft-…)는 발견용 식별자다. 원문 확보와 서지 대조가 끝나면 총괄이 장부 sources에 등록하고, 임시 ID와 장부 ID의 대응을 tasks/coordinator/의 조정 기록에 남긴다. 장부에 없는 ID를 인계 JSON의 paper_ids·evidence_ids에 쓰지 않는다.
4. 인계는 한 방향으로 흐른다. 작업자는 tasks/<작업ID>/에만 쓰고, 총괄이 인수 게이트(파일·해시·ID·입력 버전 재대조)를 거쳐 `put`과 `commit_handoff`로 반영한다. 입력 버전이 달라진 인계는 자동 병합하지 않고 재대조 기록을 남긴다. 병렬 인계의 반영 순서는 인계 계약을 따른다.
5. 장부 밖의 논증 기록(argument-map 등)은 tasks/coordinator/에 두고 기록 시점의 장부 버전을 적는다. 장부 버전이 달라지면 갱신하기 전까지 최신으로 취급하지 않는다.
6. 원문 바이트와 추출본은 장부의 해시와 일치해야 하며 승인 전에는 근거로 쓰지 않는다. 작업자는 원문을 자기 작업 폴더에 확보하고, 장부 등록 시 총괄이 sources/·extracted/로 옮겨 해시를 기록한다.

## 작업 폴더와 ID 규칙

- 작업 ID는 `<단계>-<번호 또는 대상>`의 소문자·하이픈으로 정한다(예: source-analysis-01, objection-analysis-01, argument-review-01). 이미 있는 작업 폴더의 이름은 바꾸거나 옮기지 않는다.
- 한 작업 폴더에는 한 작업자의 산출물만 둔다. 재작업은 새 작업 ID를 쓰고 이전 폴더를 덮어쓰거나 삭제하지 않는다.
- 같은 단계의 병렬 작업은 같은 입력 버전과 같은 중립적 쟁점 목록으로 배정하고 서로의 폴더를 읽지 않는다.
- 검토 작업은 작성 작업과 다른 작업자(새 컨텍스트)에게 배정하며, 검토 대상은 파일 해시와 장부 버전으로 지정한다.

## 이 연구의 분석 규칙

- 연구질문과 제외 범위는 research-question.json을 따른다. 범위 밖 문헌은 후보 단계에서 제외하고 사유를 남긴다.
- 원전 분석과 반론 분석은 인정의 규범적 기준과 현재 생성형 AI·LLM이 그 기준을 충족한다는 사실적 근거를 별도 항목으로 기록한다. 한쪽 근거로 다른 쪽을 대체하지 않는다.
- 자기보고·행동 증거, 이론적 가능성, 특정 모델에 대한 주장, 프리프린트와 동료심사 논문을 구분해 표시한다.
- 개요 승인 전에는 원고를 작성하지 않는다. 다음 작업과 승인 상태는 PROGRESS.md와 장부의 approvals에서 확인한다.
