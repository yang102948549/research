# research

한국어 문헌연구를 위한 Codex 멀티에이전트 워크플로입니다. 총괄 1명과 하위 작업자 최대 3명이 동시에 문헌 검색, 원문 근거 추출, 논증·집필, 독립 검토, HWPX 출력을 수행합니다. 상시 서버가 아니라 Codex 스킬과 로컬 Python 스크립트의 조합입니다.

## 현재 상태

- 연구질문·핵심 개요의 사용자 승인, 버전·해시 기반 근거 장부, 작성자와 검토자 분리 구현.
- 회귀시험 78개 통과. 실제 공개 논문 파일럿의 최종 게이트 통과.
- 실제 한국어 PDF·스캔·선택 표 셀 검증 기록 보존.
- KCI API 3종 정상 호출 확인. 논문검색 10/20건 페이지 표본 검증 통과. 참고문헌 API의 식별자·경계 응답은 미확정으로 수집을 보류합니다.
- 전체 연구 워크플로의 무제한 품질 보증이나 투고 준비 완료를 뜻하지 않습니다. 동일 모델의 역할 분리는 완전한 독립성이 아닙니다.

## 시작

Python 3, PyMuPDF, Pillow가 필요합니다.

```powershell
python -m pip install pymupdf pillow
python -X utf8 -m unittest discover -s evidence-paper-workflow/tests -v
python -X utf8 evidence-paper-workflow/scripts/cli.py status research-snapshots/pilot-kross-2013
```

스킬 사용법은 [SKILL.md](evidence-paper-workflow/SKILL.md), 재개 기록은 [HANDOFF.md](HANDOFF.md)를 확인하세요. 설치 스크립트에는 이전 컴퓨터의 `C:/Users/USER/...` 경로가 있으므로 실행 전 실제 환경에 맞춰 수정해야 합니다. API 키는 프로세스 환경변수로만 전달하며 저장소에 보관하지 않습니다.

## 구성

- `evidence-paper-workflow/`: 스킬·스크립트·회귀시험·고정된 외부 참고 스킬
- `research-snapshots/`: 연구 및 검증 보관본
- `validation/`: 실제·합성 검증 자료와 KCI 사용자 실행 결과
- `pilot-staging/`: 초기 파일럿 작업 기록

제3자 문헌·참고 스킬의 권리와 이용 조건은 원출처에 따릅니다. 외부 참고 스킬의 출처·고정 버전은 `evidence-paper-workflow/references/upstream-audit.md`에 기록되어 있습니다.
