# 외부 스킬 정적 검토 기록

검토일: 2026-10-15 (Asia/Seoul). 검토자: 현재 Codex의 별도 sources 역할 에이전트.

## 고정 범위와 방법

- 저장소: https://github.com/K-Dense-AI/scientific-agent-skills
- 고정 커밋: `a1043ef544e3a100c28e70a736b6cf32554d0677`
- 범위: `vendor-lock.json`에 열거한 44개 파일. 저장소 전체가 아닌 `literature-review`, `scientific-writing`의 선택된 하위 트리와 루트 LICENSE이다.
- 44개 파일을 UTF-8로 읽고 SHA-256 일치를 확인했다. 14개 Python 파일은 실행 없이 AST를 파싱하여 import·호출을 조사하고 네트워크·환경변수·파일 입출력·서브프로세스 지점을 검토했다. 스킬 본문, 참조 문서, 템플릿은 의존성·검증·인간 확인 요구를 대상으로 정적 검색했다. 네트워크/자격증명 관련 코드와 공통 I/O·주장 검증 코드의 해당 본문을 직접 읽었다.
- upstream 스크립트는 실행하거나 import하지 않았다. 의존 패키지 설치, 유료 모델 호출, `.env` 읽기를 수행하지 않았다.
- 이는 통합 범위 결정을 위한 정적 검토이며 전체 코드의 취약점 부재, 모든 문헌 지침의 정확성, 외부 서비스의 보안이나 미래 호환성을 보증하지 않는다. 새 커밋은 재검토 후 lock을 갱신한다.

## 라이선스

`vendor/LICENSE.md:1`은 MIT, 저작권은 K-Dense Inc. (2025)이다. `literature-review/SKILL.md:5`, `scientific-writing/SKILL.md:4`도 MIT를 명시한다. 원본 파일과 저작권·허가 고지는 유지한다. 본 프로젝트는 개별 스킬을 별도 설치해 자동 실행하는 방식이 아니라 이 고정 사본의 지침을 선별하여 채택한다.

## 실행·전송 경계

아래 경로는 `vendor/skills/` 기준이다. **모든 upstream Python 파일은 현재 자동 실행 경로에서 제외한다.** ‘오프라인 선택 검토 가능’은 현재 실행했다는 뜻이 아니다.

| 파일 | 확인한 동작·의존성 | 초기 통합 판정 |
|---|---|---|
| `literature-review/scripts/search_databases.py` | stdlib. 로컬 JSON 검색 결과의 정렬·중복 제거·Markdown/BibTeX/JSON 출력. 이름과 달리 실제 데이터베이스 검색 없음 (`:2–3`, `:98` 이후). 출력 파일 쓰기 가능. | 지침만 채택; 향후 오프라인 선택 검토 가능. 이를 실행했다고 검색 완료를 기록하지 않는다. |
| `literature-review/scripts/verify_citations.py` | `requests`. DOI를 `https://doi.org/api/handles/…` (`:70`) 및 `https://api.crossref.org/works/…` (`:90`)에 전송. 선택 이메일을 Crossref `mailto`로 전송 (`:91`). URL 접근성 helper는 전달 URL에 HEAD 및 redirect 수행 (`:132` 부근). 로컬 입력의 DOI를 추출하고 JSON 보고서 저장. | 자동 실행 제외. 자체 `sources.py` 어댑터 사용. DOI 등록과 의미 검증을 구분하는 지침만 채택. |
| `literature-review/scripts/generate_pdf.py` | stdlib + 외부 Pandoc/XeLaTeX. `subprocess.run`으로 의존성 확인 (`:15`) 및 변환 (`:68`). 로컬 CSL·서지·템플릿을 읽는다. Python 자체 HTTP 호출은 없지만 변환기 입력의 외부 리소스 처리까지 오프라인이라고 보증하지 않는다. | 사용 안 함. HWPX 자체 생성기 사용. |
| `literature-review/scripts/generate_schematic.py` | OpenRouter 키를 CLI, 환경변수, cwd와 모든 상위 폴더 및 스크립트 폴더의 `.env`에서 탐색 (`:44–77`). 선택 환경변수와 키를 자식 Python에 넘김 (`:80–85`, `:192`). | 비활성. 외부 `.env` 탐색·유료 호출을 도입하지 않는다. |
| `literature-review/scripts/generate_schematic_ai.py` | `requests`; 같은 `.env` 탐색 (`:114–150`). OpenRouter `/api/v1/images`에 prompt 전송 (`:240`, `:263`, `:365` 부근), `/chat/completions`에 prompt와 로컬 이미지의 base64 전송 (`:288–295`, `:320` 이후). Bearer 인증, 로컬 이미지·검토 결과 저장. 모델 slug는 고정 코드 값이며 사용 가능성 검증 안 함. | 비활성. 별도 모델 API·외부 문서 전송 없음. |
| `scientific-writing/scripts/_common.py` | stdlib. 크기 제한 JSON/CSV/UTF-8 읽기; 로컬 새 파일 쓰기, 덮어쓰기 거부 (`:216–235`), JSON 진단 stdout. | 공통 원칙 참고만. |
| `scientific-writing/scripts/audit_claims.py` | stdlib + 로컬 공통 모듈. 주장 hash, 근거 ID, CSV/JSON의 검증 필드·마커 검사 (`:79`, `:117`, `:146`). 의미 자체를 원문과 비교하지 않는다. | 원칙 채택. 자체 독립 검토 게이트와 구분. |
| `scientific-writing/scripts/check_consistency.py` | stdlib + 공통 모듈. 로컬 수치·방법/결과 장부 일관성 검사. | 오프라인 선택 검토 가능; 현 버전 실행 제외. |
| `scientific-writing/scripts/check_references.py` | stdlib + 공통/manifest 모듈. DOI/ISBN 형식·중복 등 로컬 검사, 실제 식별자 조회 없음. | 원칙만 채택; 서지 실재 확인을 대체하지 않음. |
| `scientific-writing/scripts/lint_manuscript.py` | stdlib + 공통 모듈. Markdown/manifest의 표현·형식 검사. | 영어/실증 중심 규칙은 한국어 문헌연구에 그대로 적용하지 않음. |
| `scientific-writing/scripts/scaffold_manuscript.py` | stdlib + 공통 모듈. 로컬 assets를 읽어 새 scaffold·manifest·장부를 기록. | 자체 한국어 골격으로 대체. |
| `scientific-writing/scripts/select_reporting_guidelines.py` | stdlib + 공통 모듈. 로컬 guideline registry와 coverage JSON 검사. | 연구 유형별 선택 원칙만 채택; 모든 문헌연구를 PRISMA/IMRaD로 강제하지 않음. |
| `scientific-writing/scripts/validate_authorship.py` | stdlib + 공통 모듈. 인간 저자·책임·AI 사용 공개와 사람 검증 완료 필드 검사 (`:197`). | 인간 저자 책임 원칙 유지. 에이전트 검토를 인간 검토로 바꾸지 않음. |
| `scientific-writing/scripts/validate_manifest.py` | stdlib + 공통 모듈. source/manuscript 구조와 사람 검증 필드 검사 (`:98`, `:236`, `:378`). | 자체 스키마 사용. upstream의 verified와 자체 agent_reviewed를 혼용하지 않음. |

scientific-writing 9개 Python 파일에서 네트워크/환경변수 접근 import 및 호출을 발견하지 않았다. 로컬 사용자 경로를 읽는 기능과 출력은 존재하므로 이를 무조건 샌드박스로 간주하지 않는다. `references/cli_reference.md:8`, `references/authorship_ai_confidentiality.md:86`의 오프라인 설명도 위 실제 호출 검토와 대조했다.

literature-review의 `references/search_and_citation.md:9–22`, `references/core_workflow.md:43–61`은 별도 인증된 `parallel-cli` 검색·추출을 제안한다. CLI 구현은 이번 고정 사본에 포함되지 않아 감사를 수행하지 않았다. 초기 버전은 설치·호출하지 않고 미설정으로 표시한다. 문서의 예시 검색을 실제 검색 실적으로 기록하지 않는다.

## 채택과 변경

채택: 검색식·일자·범위 기록, 원문 확보 실패 기록, 후보/근거 분리, 반론·한계 고려, 주장 hash와 근거 ID 연결, 인용 등록 여부와 주장 지지 여부의 구분, 최종 인간 책임.

변경: `scientific-writing/SKILL.md:56–57`, `:143`은 사람이 원문을 열어 확인하기 전 verified로 표시하지 말 것을 요구한다. 본 워크플로는 그 요구를 충족했다고 주장하지 않는다. 독립 에이전트 판정은 `agent_reviewed`, 사람 검토는 별도 상태로 관리하며 사람이 실제 확인하지 않은 결과는 `human_reviewed`로 전환하지 않는다. 최종 결과는 투고 전 검토용이고 인간 검토는 pending으로 명시한다. 사용자 승인 게이트는 질문/범위와 개요의 두 곳이다. 두 승인을 모든 원문에 대한 사람 검증으로 해석하지 않는다.

미채택: 유료 AI 그림 생성, 폴더를 거슬러 올라가는 `.env` 탐색, Parallel 설치, 과학 논문 전체에 대한 일률적 IMRaD/PRISMA 강제, 자동 출판·투고. upstream 말미의 자체 연구 소개·인용 권고는 이번 논문의 실질적 근거가 아닌 한 참고문헌에 자동 삽입하지 않는다.

## HWPX 템플릿 출처

`assets/template-provenance.json`에 기록된 `airmang/python-hwpx` 커밋 `3da8615c483dbda82be4f70307bbd3998ad62d28`의 `src/hwpx/data/Skeleton.hwpx`를 `assets/blank.hwpx`로 보관한다. 기록 SHA-256 `c91fb77a9933a3e5645a25778e2d2b99e98137ed99572a5d1dd29ef0c0fd4c98`과 실제 파일이 일치한다. 함께 받은 `assets/template-LICENSE`는 Apache-2.0이며 저작권은 airmang (Dr. Wily), 2025–2026이다. 라이선스 파일도 provenance hash와 일치한다. 원본 템플릿은 수정하지 않으며 생성 원고가 이 템플릿에서 변환된 사실을 보고서에 남긴다. 구조·내용 재추출 검사는 별도 출력 검증에서 수행하며, 이 출처 감사만으로 한컴의 실제 열기/렌더링 성공을 선언하지 않는다.
