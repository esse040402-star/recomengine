# Steam TOP 100 인기 게임 랭킹 — 2단계 (실시간 순위 수집)

## 기존 구조를 재사용한 구현

- 기존 `기존프로젝트/app/services/steam.py`의 HTTP 호출 래퍼 및 설정 사용
- 신규 `fetch_concurrent_top(limit=100)`: Steam 공식 `GetGamesByConcurrentPlayers`에서 순위, App ID, 현재 동시 접속자, 최고 동시 접속자 수 수집
- 기존 `app/services/market.py`의 10분 메모리 캐시 사용
- 신규 `GET /api/rankings/steam`: `{section, source, updatedAt, count, complete, data}` 구조 반환
- 기존 React용 `GET /api/market?section=rankings` (10개)와 뉴스·리뷰·설문·추천 코드 보존
- `app/docs.py`에 Swagger 설명 추가

## 호출

```text
GET http://localhost:8000/api/rankings/steam
```

응답의 각 게임 항목:

```json
{"rank":1,"app":730,"players":1000000,"peakPlayers":1200000}
```

위 수치는 **형식 설명용 예시**이며 실제 조회 결과가 아닙니다. `rank`는 Steam 공식 순위이며 재정렬·재번호 부여하지 않습니다. `count`가 100이 아니면 `complete=false`로 표시하며 누락 게임을 생성하지 않습니다.

Steam API 문서에는 `key` 파라미터가 표시되어 있습니다. `STEAM_API_KEY`가 환경에 있으면 기존 설정을 통해 전달하며, 없으면 키 없는 요청을 시도합니다. Steam이 인증을 요구하거나 응답 오류를 돌려주면 502를 반환합니다. 키는 React나 저장소에 기록하지 마세요.

## 테스트

기존 백엔드 작업 디렉터리(`기존프로젝트/`)에서:

```bash
python -m pytest -q tests/test_rankings_top100.py tests/test_api_market.py tests/test_docs_coverage.py
```

새 테스트는 외부 Steam 서버를 호출하지 않고 응답을 모의하여 100개 항목, 필드 대응, 비정상 응답, 메모리 캐시, 기존 API 독립성을 확인합니다. 실제 Steam 인증·네트워크 응답은 배포 환경에서 별도 확인해야 합니다.

## 3단계에서 이어서 진행할 항목

- TOP 100 App ID와 기존 Steam·IGDB 게임 이름/이미지/장르 통합
- 기존 카탈로그(137개 등)에 없는 App ID도 보강
- 상위 100개 전부 기존 React 상세 페이지로 이동할 수 있도록 준비
- 새로고침 이후 데이터 보존은 5단계에서 기존 브라우저 저장 기능과 통합

**참고:** 이 단계는 TOP 100 순위 수집까지만 구현합니다. 브라우저 화면은 아직 새 API를 소비하지 않습니다.


## GitHub 작업 위치

이 폴더는 반드시 `main` 브랜치의 `새작업물/` 안에만 보관하는 독립 전달본입니다.
- `구현코드/app/services/steam.py`: Steam 동시 접속 TOP 100 호출 함수 추가된 서비스 전체 파일
- `구현코드/app/services/market.py`: 기존 캐시 재사용 및 TOP 100 응답 조립 전체 파일
- `구현코드/app/routers/market.py`: `GET /api/rankings/steam` 라우터 추가된 전체 파일
- `구현코드/app/docs.py`: 신규 API Swagger 설명 추가된 전체 파일
- `구현코드/tests/`: 별도 TOP 100 모의 테스트 및 기존 Swagger 문서 테스트 갱신본

기존 `기존프로젝트/` 경로의 파일은 `main`에서 변경하지 않았습니다.
작업물은 **기존 프로젝트에 자동 적용된 상태가 아닙니다.** 최종 통합 담당자가 실제 대상 백엔드에
새 함수/라우터/문서 부분을 병합하여 적용해야 합니다. 다른 팀원이 원본을 수정했을 수 있으므로
파일 전체를 무조건 덮어쓰기보다는 신규 구현 부분만 비교 후 합치세요.
이 전달본의 테스트는 기존 프로젝트 패키지(`app`)가 존재하는 환경에서, 통합 후 실행하는 것을 전제로 합니다.

### 이번 단계 Git 관리 원칙

- 작업 브랜치 생성 금지, `main`에서만 신규 산출물 작성
- 신규 작업물은 전부 `새작업물/` 아래에 저장
- `기존프로젝트/` 수정 금지 (읽기·분석만)
- 변경된 파일, 테스트 결과, 미완료 검증을 각 단계 README에 구분 기록
