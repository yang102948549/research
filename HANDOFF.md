# 다른 컴퓨터 작업 재개 안내

> 현재 운영 기준은 루트 AGENTS.md입니다. 아래 이전 시점의 동시 실행 수·설치 경로 기록은 이력이며 최신 정책이 아닙니다.

작성일: 2026-10-15. 구현 기준 커밋: `a9e2411`.
브랜치: `codex/evidence-paper-workflow`.
이 문서는 구현 커밋 후 작성되었으며 별도 문서 커밋으로 보존한다.

## 현재 완료 상태

이 스킬은 문헌 검색 → 원문 확보 → 근거 카드 → 논증·개요 → 작성 → 독립 검토 → HWPX의 연구 작업 흐름이다. 별도 상시 서버가 아니라 Codex의 하위 에이전트와 로컬 스크립트를 조합한다. 총괄 포함 동시3개, 연구질문·핵심개요 사용자 승인2곳을 유지한다.

- K-Dense2개 스킬 검토·버전 고정: a1043ef544e3a100c28e70a736b6cf32554d0677. upstream44파일 해시 일치. 원본 스크립트 미실행.
- Kross2013 실제 공개원문1편의 사용자 승인 질문·개요, 한국어 원고, 독립 검토, HWPX 생성·재추출 및 한글2022 실제 열기/1쪽 시각 대조 완료. 스냅샷에서 final gate 재확인 통과.
- 실제 한국어2단PDF/스캔의 부정·각주·위치 검증, 복잡한 실제 스캔표6개 패널 시험 완료.
- 이번 독립 표 검토16사례: pass6/revise10. 실제 선택 셀 코드검사1개 통과, 변조7개 차단. 전체126셀은 승인하지 않았다.
- 회귀시험64개 통과, 스킬 형식 검사 통과, 설치본47파일 갱신 완료.
- 자세한 결과: `validation/scan-table/REPORT.md`와 `evidence-paper-workflow/references/scan-table-validation.md`.

## 이전할 자료

작업 폴더 전체를 복사하거나 `evidence-paper-workflow-transfer.bundle`을 복사한다. bundle은 이 문서 커밋까지의 로컬 Git 이력을 포함하며 원격 업로드하지 않았다.

```powershell
git clone evidence-paper-workflow-transfer.bundle literature-workflow
cd literature-workflow
```

원본 파일 바이트와 해시 보존을 위해 `.gitattributes`에서 줄바꿈 자동변환을 껐다. 사용자 홈에 상위 저장소가 있어 이 프로젝트만 별도 Git 저장소로 초기화했다. Git 작성자 미설정으로 커밋별 `Codex <codex@localhost>`를 사용했으며 전역 설정은 바꾸지 않았다.

- `evidence-paper-workflow/`: 설치할 스킬 원본과 테스트·고정 upstream.
- `research-snapshots/pilot-kross-2013/`: 완료된 실제 원고 연구의 최신 보관본. 이전 `pilot-staging/`보다 이 스냅샷을 우선한다.
- `research-snapshots/academic-pdf-validation-20261015/`: 앞선 실제 한국어PDF 시험 보관본.
- `validation/scan-table/`: 이번 원본·OCR·이미지·전사·독립 검토·실행 결과.
- 다른 validation 하위 폴더: 이전 합성시험과 시각 검증 자료. 시험 종류를 혼동하지 않는다.

## 새 컴퓨터 설치·재현

Python3, PyMuPDF와 Pillow가 필요하다. 현재 검증환경은 Python3.13. Windows 로컬OCR에는 한국어OCR 언어팩이 필요하며 HWPX 실제 시각검증에는 한글 앱 등 실제 렌더러가 별도로 필요하다. 이 문서의 명령은 프로젝트 루트 기준이다.

```powershell
python -m pip install pymupdf pillow
python -X utf8 -m unittest discover -s evidence-paper-workflow/tests -v
python -X utf8 validation/scan-table/tasks/source/run_gate_test.py
python -X utf8 evidence-paper-workflow/scripts/cli.py status research-snapshots/pilot-kross-2013
```

시험 재실행은 시간/경로 기록을 갱신하므로 기존 기록을 보존하려면 복사본에서 실행한다. OCR 원자료는 보존되어 있어 위 게이트 재현은 OCR 재실행이 필요 없다.

`install.py`의 TARGET/RESEARCH는 기존 사용자 요청에 따라 `C:/Users/USER/...`로 고정되어 있다. 새 컴퓨터의 사용자 이름이나 연구 경로가 다르면 **실행 전에** 두 경로와 TARGET 부모 검사 경로를 실제 위치로 수정한다. 기존 스킬이 있으면 설치기가 관리하지 않는 변경을 덮어쓰지 않는다. 연구를 이전하려면 최신 research-snapshots를 먼저 원하는 ResearchWorkspace에 복사한다. 기존 연구는 installer가 보존한다.

```powershell
python -X utf8 evidence-paper-workflow/scripts/install.py
python -X utf8 "$env:USERPROFILE/.codex/skills/evidence-paper-workflow/scripts/check_installation.py"
```

원래 환경의 canonical 경로는 `C:/Users/USER/Documents/ResearchWorkspace/` 아래 pilot-kross-2013, academic-pdf-validation-20261015, scan-table-validation-20261015였다. 새 위치의 장부는 내부 상대경로를 유지한다. 과거 보고서의 절대경로는 실행 당시 감사 기록이며 자동으로 살아있는 경로라고 가정하지 않는다. 과거 원문/검토 해시나 승인 기록을 이동 때문에 다시 만들지 않는다. 스킬 설치 후 Codex 새 대화에서 스킬 발견 여부를 확인한다.

## 남은 일과 제한

1. KCI 실키 인증 및 실제 XML 응답3종 검증은 미완료. `references/kci-setup.md`와 `scripts/kci_probe.ps1`을 확인하고 키를 KCI_API_KEY 프로세스 환경으로만 전달한다. 키를 채팅·Git·로그에 남기지 않는다.
2. 더 다양한 복잡표/스캔의 검증 범위 확대. 현재 선택 표·셀 시험을 전체 문헌 정확도로 일반화하지 않는다.
3. 서지 exporter는 제한된 형식이며 완전한 APA CSL 엔진이 아니다.
4. 같은 모델의 역할 분리는 완전 독립성이나 무환각 보장이 아니다. 코드의 구조검사와 실제 독립 검토자의 의미 판정을 구분한다.
5. 표 원문의77.68+20.32 불일치 원인은 미확정. 임의정정 없이 관련 해석 보류.

## 다음 대화에 붙일 요청

“이 폴더의 HANDOFF.md와 evidence-paper-workflow/SKILL.md를 먼저 읽고 현재 완료 상태를 확인해줘. 기존 승인·원문·검토 기록을 보존하고, 내가 지정하는 다음 연구 또는 남은 KCI 실연결 시험만 진행해줘.”

사용자 요청에 따라 이번 작업은 커밋·인수인계 문서 작성 후 종료한다. 자동 후속 실행이나 자동 투고는 설정하지 않았다.


## 2026-10-15 현재 컴퓨터 재개 점검

- Python 회귀시험 64개 통과.
- pilot-kross-2013 스냅샷의 하위 폴더 파일 누락을 확인했다. 전달 bundle 커밋 c633fc41ca63c324ba1022cc1724df19ed4be3d4와 기존 파일의 바이트 일치를 확인한 후, 누락 41개 파일만 복원했다. 기존 장부·승인·원고는 변경하지 않았다.
- 복원 후 cli.py status의 research_question, outline, manuscript, final 게이트 모두 통과했다. 보존된 검토 기록의 재검증이며, 현재 컴퓨터에서 한글을 새로 열어 검토했다는 의미는 아니다.
- 복원 파일과 SHA-256 목록: validation/pilot-recovery.json. 복구용 저장소: validation/transfer-recovery (no-checkout). 기존 프로젝트 .git에서는 HEAD 객체를 읽지 못했으며 덮어쓰거나 초기화하지 않았다.
- KCI 프로브 결과: not_configured. 현재 프로세스에 KCI_API_KEY가 없어 실제 인증·XML 3종 시험은 미완료다. 키를 채팅에 보내지 말고 로컬 PowerShell에서 아래 명령을 실행해 숨김 입력으로 제공한다. 결과의 상태·건수만 공유하면 후속 판정이 가능하다.

```powershell
& 'C:/Users/yang4/OneDrive/claude/논문검색/문헌검색/evidence-paper-workflow/scripts/kci_probe.ps1' -Title '컴퓨터'
```


## 2026-10-15 KCI 사용자 실행 결과 수신

- 사용자 제공 프로브 출력에서 articleSearch / articleDetail / referenceSearch 모두 ok 확인. 논문검색 총 2,816건 중 10건, 상세 1건, 참고문헌검색 총 19,706건 중 10건 반환.
- 기본 인증·3종 응답 파싱의 실연결 성공은 사용자 실행 결과 기준으로 확인했다. 원문 XML을 직접 검토하거나 현재 Codex 프로세스의 키 설정을 확인한 것은 아니다. evidence_verified=false는 정상이며 원문 근거 검토는 별도다.
- 검색어는 앞서 '컴퓨터'를 안내했으나 수신 출력에는 없으므로 확정 기록하지 않았다. 최상위 status도 발췌에 없어 추가하지 않았다.
- 로컬 프로브는 displayCount=1을 요청하지만 제공 결과는 두 검색 모두 10건이다. 공식 명세의 기본값은 10, 최대값은 100이다. 10건 반환 원인은 미확정이며 페이지 크기·다음 페이지 검증은 남아 있다. 대량 수집 완료로 해석하지 않는다.
- 기록: validation/kci-live/user-reported-result.json. 다음 연구 착수에는 연구 주제·범위 설정 및 연구질문 승인이 필요하다.


## GitHub 업로드 준비

전달 bundle의 정상 이력을 기반으로 최신 재개·KCI 기록을 반영했다. 현재 폴더의 build-status.json은 0.3으로 오래되어 업로드 작업본에서는 bundle의 0.4 기록을 기준으로 최신 KCI 상태를 추가했다. 원래 폴더의 파일과 손상된 .git은 보존했다.


## 2026-10-15 KCI 페이지 검증 및 새 연구 준비

정상 작업본은 validation/transfer-recovery이다. 페이지 처리 코드 보완 후 77개 회귀시험 통과. 실서버 페이지 검증은 API 키 부재로 대기하며 validation/kci-pagination/REPORT.md의 명령으로 실행한다. 현재 생성형 AI·LLM의 도덕적 지위 문헌연구를 research-workspaces/ai-moral-status에 준비했다. 예비 후보 6건과 질문 제안만 기록했고 질문·개요 승인이나 본문 작성은 수행하지 않았다. 이번 변경은 아직 GitHub에 푸시하지 않았다.

사용자는 총괄-하위 구조를 명시했다. 현재 스킬은 총괄 1명과 동시 하위 최대 2명이며, 검색·분석·집필·독립검토는 단계별 역할이다. 현재 세션은 총괄 포함 4개 실행 슬롯을 제공하므로 하위 2명은 스킬 설정상의 제한이다. 사용자가 규모를 검토 중이며 제한 변경은 아직 적용하지 않았다.


## 2026-10-15 사용자 요청에 따른 동시 실행 구성 변경

이 절은 앞선 동시 3개/하위 2명 제한 기록을 대체한다. 총괄 1명 + 동시 하위 최대 3명(총 4개)으로 SKILL.md, orchestration.md, README 및 연구 설정을 변경했다. 총괄만 공통 장부를 수정하며 하위 재위임은 하지 않는다. 호스트 슬롯 부족 시 대기열로 운영한다. 현재 KCI_API_KEY는 미설정이며 실서버 페이지 검증은 사용자 로컬 실행 결과를 기다린다.


## 2026-10-15 20:08 KCI 실서버 결과 판정

articleSearch는 1/10/20건 및 2페이지 응답 확인, 마지막 1911페이지 network_error로 미완료. referenceSearch는 미실행. assessment-20261015-200850.json에 증명 가능한 관찰만 기록. 부분 판정 보존 및 HTTP 상태 진단 보완 후 78개 시험 통과. 재시험 검색어는 생성형 인공지능. 연구 검색계획은 research-workspaces/ai-moral-status/search-plan.json에 준비했으며 아직 실행/질문 승인으로 기록하지 않았다.


## 2026-10-15 20:12 이후 연구 진행

KCI articleSearch 표본 통과, referenceSearch는 식별자·경계 응답 문제로 보류. 최신 판정 assessment-20261015-201156.json 참조. 사용자는 잠정적 보호를 제외하고 도덕적 지위 인정 근거에 집중하도록 범위를 수정했으며 실제 응답을 질문 해시와 함께 기록했다. 총괄+하위3명의 조사로 신규 후보14편을 통합하고 공개 HTML2편을 확보·초기 추출했다. 연구 진행과 다음 작업은 research-workspaces/ai-moral-status/PROGRESS.md 참조. 원고/개요 승인·의미 검증은 아직 미완료다.


## 연구 자료 확보 및 첫 근거 검토 기록

구조·지침/KCI 변경 커밋 21f179a를 GitHub main에 푸시했다. 국내 전체 PDF4편 및 미리보기1편 확보. 국외 HTML2편에서 E001–E004/C001–C004를 작성자와 분리된 검토자가 선택 문단 범위로 검증했으며 장부 검사 통과. 원문 전체 추출 검증은 미완료다. 근거대장·원문 해시·독립 검토 기록은 research-workspaces/ai-moral-status에 보존한다. 다음 단계는 국내 PDF 핵심 구절 검증과 규범적 인정 기준의 근거 보강이다.

## 2026-10-15 범용 AGENTS와 실행 스킬 분리

총괄+하위 최대3명의 역할·인계·승인 정책을 루트 AGENTS.md로 이전했습니다. SKILL.md와 orchestration.md에는 연구 실행 및 장부 계약을 남겼습니다. 연구 전용 승인 게이트는 일반 개발 작업에 적용하지 않습니다. 특정 PDF 임베드는 발견하지 못했으며 실행 지침에 섞인 특정 사례와 수치는 일반화했습니다. 원자료·연구 장부·기존 검증 보고서는 보존했습니다. 상세 감사는 validation/agent-architecture/RESOLUTION.md를 확인합니다.


## 2026-10-22 원전 분석·반론 분석 개편과 인계·게이트 재정비

AGENTS.md에 논증형 문헌연구의 단계(원전 분석·반론 분석 병행 → 총괄 논증 구성 → 작성에 참여하지 않은 검토자의 대조 → 총괄 수정), 단계 게이트 G0–G4(코드 검사와 절차 검사 구분), 파일 소유권, 동시 실행 한도의 단일 기준을 정리했다. 원전 분석은 찬반 입장 없이 저자 입장의 정확한 재구성을, 반론 분석은 결론 반대가 아니라 논증이 견뎌야 할 가장 강한 이의 탐색을 맡는다. SKILL.md에 분석·대조 기준을, orchestration.md에 병렬 인계 반영 순서와 작업 산출물 형식을 추가했다. 새 연구 폴더의 research-workspaces/ai-moral-status/AGENTS.md에 기준 파일과 장부·폴더 연결 방식을 명시했다. 스크립트·장부·기존 연구 기록은 변경하지 않았다.

재검토에서 확인한 한계(코드 미변경, 문서 절차로 보완):

1. 커밋된 인계의 unresolved가 남아 있으면 원고 게이트가 막히고 커밋된 task_id는 바꿀 수 없다. ai-moral-status 장부의 발굴 작업 3건에 각각 미해결 1건이 있어 원고 게이트 전에 처분이 필요하다.
2. 검토자 독립성은 주장 작성자와의 문자열 비교뿐이다. 분석 작성자와의 분리는 배정 기록으로만 확인한다.
3. 이의 처리의 완결성은 코드가 검사하지 않는다.
4. `put`은 모든 의미 검토를 무효화하고 출처·근거·주장 변경은 개요 승인을 해제한다. 장부 반영을 모두 끝낸 뒤 검토 판정을 기록해야 한다.


## 2026-10-22 검토자 분리·논증 기록 코드 검사 추가

위 한계 2·3을 부분 보완했다. workflow.py에 인계의 선택 키 `contributor_id`와 검토자 불일치 검사(`review`·`review_paragraph`), `check_argument_map`을 추가했고 cli.py에 `check-argument`를 추가했다. 키가 없는 기존 인계와 장부는 동작이 같다. 시험 4개를 추가해 82개가 되었으며 리눅스 점검에서 Windows OCR 시험 2개를 제외한 80개가 통과했다(제외한 2개는 변경 전에도 같은 오류). 이의 처리가 적절한지와 분석 인계에 `contributor_id`를 실제로 적었는지는 여전히 총괄·검토자의 절차다. 한계 1(unresolved 잠금)은 아래 항목에서 보완했다.


## 2026-10-22 미해결 항목 처분 기록 기능

workflow.py에 `record_disposition`을 추가하고 cli.py에 `dispose`를 추가했다. 커밋된 인계는 바꾸지 않고 unresolved 항목별 처분(resolved·carried_as_limitation·out_of_scope)과 사유를 항목 해시에 묶어 `dispositions`에 덧붙이며, 원고 게이트는 처분 없는 항목만 오류로 센다. 장부 버전을 올리지 않아 기존 검토를 무효화하지 않는다. 시험 3개를 추가해 85개가 되었고 리눅스 점검에서 Windows OCR 시험 2개를 제외한 83개가 통과했다(제외한 2개는 변경 전에도 같은 오류). ai-moral-status 장부의 발굴 작업 3건의 미해결 항목에는 처분을 기록하지 않았다. 연구 판단이 필요하므로 사용자의 지시 후 총괄이 기록한다.


## 2026-10-22 ai-moral-status 발굴 작업 3건의 처분 기록

사용자 지시로 domestic-discovery, international-discovery, theory-discovery의 미해결 항목 각 1건에 `carried_as_limitation`을 기록했다(`dispositions`만 추가, 장부 버전 33 유지, 원본 인계 불변). 항목의 내용(출처 단위의 원문·추출 검증 필요, 승인된 주장 없음)은 해결되지 않았다. 국내는 PDF 확보와 서지 확인 단계, 국외는 2편의 선택 문단 4건만 검증, 이론 5편은 원문 미확보이므로 `resolved`로 기록하지 않았다. 이월 위치는 PROGRESS.md와 장부 sources의 상태 필드이며, 개요·논증 기록을 만들 때 한계 서술로 다시 옮겨야 한다. 처분은 원고 게이트의 항목 오류만 해소하고 근거별 원문 대조와 독립 검토 요건은 그대로다. 이 장부는 CRLF이고 `save()`는 LF로 쓰므로 저장 뒤 줄바꿈을 CRLF로 되돌려 diff를 32줄로 유지했다.


## 2026-10-22 루트 지침의 범용화

루트 AGENTS.md에 섞여 있던 문헌연구 전용 내용(원전 분석·반론 분석 표, 논증 구성, 연구 승인 게이트, 문헌 검증 규칙, 게이트의 장부 코드 매핑)을 evidence-paper-workflow/references/argument-pipeline.md로 옮겼다. 루트는 주제와 작업 유형에 관계없는 규칙만 둔다: 동시 실행 한도, 복합 작업의 표준 단계(기준 분석·도전 분석 → 총괄 통합 → 독립 검토 → 총괄 수정), 게이트 G0–G4, 파일 소유권, 일반 사용자 승인, 전문 절차 연결 표. 기준 분석은 문헌연구에서 원전 분석, 도전 분석은 반론 분석에 대응한다. 사용자가 정한 파이프라인과 역할 정책의 내용은 바뀌지 않았다. 새 전문 절차는 루트의 연결 표에 한 줄만 추가한다. 스크립트는 변경하지 않았다. 남은 환경 종속: install.py·score_evaluation.py·cli.py 기본값의 C:/Users/USER 경로(스킬 쪽 이식성 문제로, 이번에는 고치지 않았다).

## 2026-10-22 역할 카드와 HWPX 스킬
- 판단이 필요한 역할은 `evidence-paper-workflow/roles/`의 카드 5종(원문 확보, 원전 분석, 반론 분석, 독립 검토, 초안 작성)으로, 절차 지식은 스킬로 나눴다. SKILL.md의 역할 기준 본문은 카드로 옮겼다. 폴더 구조와 코드 경로는 바꾸지 않았다.
- 새 스킬 `hwpx-document/`: 읽기(`read`), 구조 확인(`inspect`), 문구 치환·서식 채우기(`replace`, 원본 보존), 줄 단위 생성(`create`), 구조 검증(`validate`). 시험 10개 통과.
- 한계: 한글 프로그램의 화면 표시는 검사하지 못한다(`visual_review: not_performed`). 문단·표 행 추가, 그림 교체, 각주 편집, 구형 .hwp 바이너리는 지원하지 않는다. 실제 한글 문서(표·서식이 많은 공문서 등)로 열어 보는 시험은 아직 하지 않았다.
- 미해결: C:/Users/USER 하드코딩 경로, `Ledger.save()`의 줄바꿈 보존, 연구 폴더 AGENTS.md 템플릿(`init` 지원).
