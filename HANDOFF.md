# 다른 컴퓨터 작업 재개 안내

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
