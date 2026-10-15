# AGENTS/스킬 분리 및 PDF 감사 조치

- 감사 원본: pdf-markdown-audit.json. 수정 전 53개 Markdown 대상이며 원본 행 번호는 변경 후와 다를 수 있다.
- 직접 PDF 삽입(이미지, HTML embed/object/iframe, PDF data URI): 0건.
- PDF 링크·파일명: 25줄, 27회. 과거 사례 보고서에는 선택 전사·수치가 있다. PDF 전체와 Markdown 전체의 문장 일치 검사는 하지 않았다.
- 루트 AGENTS.md: 범용 역할, 총괄+하위3명, 인계, 승인 정책을 소유한다.
- SKILL.md: 연구 도구 실행과 승인 레코드 확인만 유지한다. orchestration.md는 연구 장부 데이터 계약이다.
- SKILL.md의 고정 사용자 경로 및 특정 OCR 실패 서술을 제거하고 과거 표 시험 보고서를 필수 실행 지침에서 분리했다.
- pdf-evidence-contract.md의 특정 논문 실패 서술과 숫자를 일반화했다.
- 과거 references/*validation.md, 연구 원문/장부, vendor 파일은 증거 이력으로 보존한다. 과거 보고서는 현재 연구의 근거로 자동 사용하지 않는다.
- 레거시 install.py/CLI 기본 경로는 이번 문서 변경 범위에서 수정하지 않았다. README는 설치 주의와 명시적 --base 사용을 안내한다. 전역 설치는 실행하지 않았다.
- AGENTS.md의 자동 발견은 새 실행에서 적용된다. 현재 작업은 파일을 직접 읽어 적용했으며 파일만으로 상시 프로세스가 생성되지 않는다.

검증: skill-creator quick_validate 통과, 외부 참고 44파일 해시 일치. 독립 하위 검토에서 일반 코드/문헌연구 라우팅에 중대한 충돌 없음. 승인 기록 생성 문구의 모호성을 수정했다. 실행 코드 변경은 없어 회귀시험은 재실행하지 않았다.
