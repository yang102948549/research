# research

[AGENTS.md](AGENTS.md)를 기준으로 운영하는 범용 총괄 에이전트 작업 저장소입니다. 총괄 1명과 하위 작업자 최대 3명이 조사·실행·독립 검토를 분담하며 동시 실행 수는 AGENTS.md에서만 정합니다. 논증형 문헌연구는 원전 분석과 반론 분석을 병행하고, 총괄이 논증을 구성하고, 작성에 참여하지 않은 검토자가 대조한 뒤 총괄이 수정합니다. 실제 병렬 실행은 호스트 도구와 가용 슬롯을 사용합니다.

| 구분 | 책임 | 적용 시점 |
|---|---|---|
| 루트 AGENTS.md | 총괄·하위 역할, 동시 실행 수, 단계 게이트, 인계, 파일 소유권, 사용자 승인 게이트 | 이 저장소에서 작업할 때 |
| `research-workspaces/<연구ID>/AGENTS.md` | 해당 연구의 기준 파일, 장부·폴더 연결, 작업 폴더 규칙 | 그 연구 폴더에서 작업할 때 |
| evidence-paper-workflow/SKILL.md | 검색·파싱·OCR·근거 장부·HWPX 실행 절차와 스크립트 | 해당 문헌연구 단계에서 선택 |

일반 코드 수정에는 연구질문·개요 승인 게이트를 적용하지 않습니다. 특정 연구 주제·논문·검증 사례는 루트 운영 지침과 분리하며, 연구별 규칙은 그 연구 폴더의 AGENTS.md에 둡니다.

## 사용

저장소 루트를 작업 디렉터리로 열어 새 Codex 작업을 시작합니다. AGENTS.md는 지침 파일이며 스스로 프로세스를 생성하지 않습니다. 특정 연구를 진행할 때는 그 연구 폴더를 작업 디렉터리로 열면 루트 지침에 더해 그 폴더의 AGENTS.md가 적용되고, 저장소 루트에서 시작했다면 먼저 직접 읽습니다. 이 저장소 밖의 전역 설정은 변경하지 않습니다. 문헌연구가 필요하면 AGENTS.md의 단계 연결을 따라 스킬을 읽습니다. 현재 스킬 폴더는 자동 설치된 전역 스킬이 아닙니다.

공식 설명: [AGENTS.md의 지침 탐색](https://developers.openai.com/codex/guides/agents-md), [필요한 작업에서 선택하는 스킬](https://developers.openai.com/codex/skills).

## 문헌연구 실행 도구 상태

- 연구질문·핵심 개요의 사용자 승인, 버전·해시 기반 근거 장부, 작성자와 검토자 분리 구현.
- 회귀시험 82개. 2026-10-22 리눅스 점검에서 Windows 한국어 OCR 시험 2개를 제외한 80개가 통과했고, 제외한 2개는 변경 전에도 같은 오류가 났습니다. 실제 공개 논문 파일럿의 최종 게이트 통과.
- 실제 한국어 PDF·스캔·선택 표 셀 검증 기록 보존.
- KCI API 3종 정상 호출 확인. 논문검색 10/20건 페이지 표본 검증 통과. 참고문헌 API의 식별자·경계 응답은 미확정으로 수집을 보류합니다.
- 원전 분석·반론 분석 병행과 독립 대조는 운영 절차입니다. 논증 기록의 구조(`cli.py check-argument`)와 분석 기여자의 검토 배제(인계의 `contributor_id`)는 코드가 검사하지만 이의 처리가 적절한지는 검사하지 않습니다. 코드 검사와 절차 검사의 구분은 AGENTS.md의 단계 게이트에 있습니다.
- 전체 연구 워크플로의 무제한 품질 보증이나 투고 준비 완료를 뜻하지 않습니다. 동일 모델의 역할 분리는 완전한 독립성이 아닙니다.

## 문헌연구 도구 실행

아래 Python 도구를 실행할 때 Python 3, PyMuPDF, Pillow가 필요합니다. 총괄 지침을 읽는 데 설치는 필요하지 않습니다.

```powershell
python -m pip install pymupdf pillow
python -X utf8 -m unittest discover -s evidence-paper-workflow/tests -v
python -X utf8 evidence-paper-workflow/scripts/cli.py init my-research --base research-workspaces
python -X utf8 evidence-paper-workflow/scripts/cli.py status research-workspaces/my-research
```

스킬 사용법은 [SKILL.md](evidence-paper-workflow/SKILL.md), 재개 기록은 [HANDOFF.md](HANDOFF.md)를 확인하세요. 설치 스크립트에는 이전 컴퓨터의 `C:/Users/USER/...` 경로가 있으므로 실행 전 실제 환경에 맞춰 수정해야 합니다. API 키는 프로세스 환경변수로만 전달하며 저장소에 보관하지 않습니다.

## 구성

- `AGENTS.md`: 범용 총괄 운영 지침
- `research-workspaces/`: 개별 연구의 질문·자료·장부·진행 기록과 연구별 AGENTS.md
- `evidence-paper-workflow/`: 스킬·스크립트·회귀시험·고정된 외부 참고 스킬
- `research-snapshots/`: 연구 및 검증 보관본
- `validation/`: 실제·합성 검증 자료와 KCI 사용자 실행 결과
- `pilot-staging/`: 초기 파일럿 작업 기록

제3자 문헌·참고 스킬의 권리와 이용 조건은 원출처에 따릅니다. 외부 참고 스킬의 출처·고정 버전은 `evidence-paper-workflow/references/upstream-audit.md`에 기록되어 있습니다.

## PDF와 사례 감사

Markdown 53개를 대상으로 PDF 이미지/HTML 임베드와 PDF data URI를 검사한 결과 직접 삽입은 0건입니다. PDF 링크·파일명과 과거 검증 보고서의 일부 전사·수치는 존재합니다. 모든 PDF 원문과 Markdown의 문장 대조까지 수행한 결과는 아닙니다. 일반 실행 지침에서 특정 사례 서술과 숫자를 제거했으며 과거 검증 보고서는 재현용으로 보존했습니다. [감사와 조치 기록](validation/agent-architecture/RESOLUTION.md)을 참조하세요.
