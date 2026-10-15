# KCI 실연결 설정

2026-10-15 공식 웹 명세 확인. 현재 실키를 이용한 성공 여부는 별도 실행 결과로 기록한다. 모의 응답 시험은 실연결 성공이 아니다.

1. [KCI OPEN API 목록](https://www.kci.go.kr/kciportal/po/openapi/openApiList.kci)의 **OPEN API 키신청**에서 키를 발급받는다. 계정 로그인이나 신청서가 요구되면 사용자 본인이 처리한다. 키 신청 화면은 이번 문서 점검에서 시간 초과하여 신청 세부 항목과 고정 유효기간은 확인하지 못했다. 발급 화면의 사용기간을 확인한다. 공식 오류 명세는 미등록 키와 사용기간 종료를 인증 오류로 구분한다.
2. Python 3와 KCI HTTPS 접속이 필요하다. 키는 `KCI_API_KEY` 프로세스 환경변수로만 전달한다. 채팅, 코드, 원고, 명령행 인수, 로그에 키를 입력하지 않는다.
3. 로컬 PowerShell에서 다음 스크립트를 실행하고 숨김 입력창에 키를 입력한다. 프로브 종료 후 이전 환경변수 값이 복구된다. 별도 유료 서비스는 필요하지 않다.

```powershell
& "$env:USERPROFILE/.codex/skills/evidence-paper-workflow/scripts/kci_probe.ps1" -Title '컴퓨터'
```

PowerShell 정책이 실행을 막으면 조직 정책을 우회하지 말고 허용된 실행 방법을 확인한다. Python 실행명이 다르면 `-Python 'C:/경로/python.exe'`를 지정한다.

이 스크립트는 자기 프로세스와 자식 Python에만 키를 전달한다. **이미 실행 중인 Codex는 다른 터미널에서 바꾼 환경변수를 상속하지 않는다.** 연구 자동 실행에는 Codex를 시작하는 실행 환경이나 승인된 비밀 관리 기능에서 키를 주입해야 한다. 이 프로브를 실행한 것만으로 Codex가 설정되었다고 기록하지 않는다. 영구 사용자 환경변수는 평문 저장이므로 이 스크립트는 만들지 않는다.

## 작은 읽기 시험과 판정

- [articleSearch](https://www.kci.go.kr/kciportal/po/openapi/openDataView.kci?datasetBean.dtstSeqNo=1): 제목 필수, 첫 페이지 1건. `articleInfo`의 `article-id` 속성을 읽는다.
- [articleDetail](https://www.kci.go.kr/kciportal/po/openapi/openDataView.kci?datasetBean.dtstSeqNo=21): 위에서 얻은 논문 ID가 있을 때만 1회 조회한다. 상세 명세에는 검색용 `total` 항목이 없다.
- [referenceSearch](https://www.kci.go.kr/kciportal/po/openapi/openDataView.kci?datasetBean.dtstSeqNo=2): 제목 필수, 첫 페이지 1건. 검색 API의 페이지당 최대값은 100건이다.

최대 3회 요청, 자동 재시도 0회. 최초 검색이 실패하면 나머지 요청을 중단한다. 검색 0건이면 상세 조회를 생략하여 전체 상태는 `partial_no_article_id`가 된다. 다른 검색어로 재실행해야 상세 기능까지 확인할 수 있다.

출력에는 상태·건수만 포함한다. `not_configured`는 미설정, `authentication_error`는 인증 실패 또는 만료, `zero_results`는 정상 응답 0건, `network_error`는 통신 실패, `unexpected_schema`/`malformed_xml`은 명세·XML 점검 필요를 뜻한다. 키·요청 URL·원문 XML은 출력하거나 파일로 저장하지 않는다. 종료 코드 0은 세 API 시험 성공, 2는 미설정·부분검증·실패이다.

실연결 기록에는 실행일, 공개 검색어, 각 API 상태·건수, 상세조회 생략 사유를 남긴다. KCI `verified`는 제공처 메타데이터이며 근거 검증 승인이 아니다. 본문은 제공하지 않으므로 원문 링크를 별도로 확보하고 원문·파싱 및 독립 검증 게이트를 거쳐야 한다.
