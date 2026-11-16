# API 가중치용 분류 통합 — 독립 전달본

이번 작업은 게임 개수와 무관한 공통 어휘·필드 통합입니다. 게임 목록 수집, 설문 점수 수치, 로그인, 화면, Render 서비스는 변경하지 않았습니다.

## 현재 완료 범위와 남은 확인

- Steam 공식 공개 태그 목록에서 확인한 429개 표기를 공통 사전에 반영했습니다.
- 공통 코드 444개, 동의어 표기 587개입니다. 모든 표기를 같은 뜻으로 합친 것이 아니라, 다른 뜻은 별도 코드로 보존합니다.
- IGDB 장르 23, 테마 22, 게임 모드 6, 시점 7개를 초기 대조 기준(seed)으로 넣었습니다.
- IGDB 인증 API로 최신 전체 사전을 가져온 상태는 아닙니다. 특히 keywords는 방대한 가변 목록이며, 모든 키워드의 의미 통합이 끝났다고 주장하지 않습니다.
- 미등록 값도 원본·출처·ID와 함께 보존하며, 자동 가중치를 부여하지 않습니다.
- Steam 공개 인기 태그 목록은 공개 스냅샷이며 앞으로 등장할 모든 태그까지 포함한다는 보장은 없습니다.
- 전체 데이터의 수집 완료(retrieval_complete)와 의미 통합 완료(semantic_complete)는 서로 다른 상태입니다.

## 팀원에게 전달할 파일

| 파일 | 용도 |
|---|---|
| [통합대응표.md](통합대응표.md) | 모든 공통 코드·동의어·상하위 관계 확인 |
| [필드통합기준.md](필드통합기준.md) | 가격·사양·시간·평점 등 처리 기준 |
| [vocabulary.json](vocabulary.json) | 언어에 관계없이 사용하는 공통 사전 |
| [normalization.py](normalization.py) | 기존 Render 게임 응답을 변환하는 Python 코드 |
| [sync_taxonomy.py](sync_taxonomy.py) | 인증된 기존 IGDB 호출 함수로 전체 분류·키워드 조회 및 누락 목록 생성 |
| [test_normalization.py](test_normalization.py) | Python 검증 테스트 |
| [검증결과.json](검증결과.json) | 이번 실행 환경에서 실제 확인한 범위 |

## 적용

normalization.py와 vocabulary.json을 같은 폴더에 두고 호출합니다.

~~~python
from normalization import normalize

facts = normalize(render_game_response)
# facts["codes"]             : 명시적 근거로 통합된 점수 후보 코드
# facts["evidence"]          : 원본 출처와 ID/표현
# facts["parent_codes"]      : 하위 분류에서 파생한 상위 관계 (자동 점수 합산 금지)
# facts["unmapped"]          : 신규/미검토 값, 삭제하지 않음
~~~

기존 테스트본의 normalization.py와 공통 코드 대부분을 유지하지만 버전 2의 세분화로 코드 집합이 달라집니다. 기존 가중치 결과에 바로 덮어쓰지 말고 새 버전을 명시해 재계산해야 합니다. 이번 커밋에서는 독립 폴더에만 추가했습니다.

## 최신 IGDB 전체 분류 대조

Render 서버 안에서 이미 인증·호출 제한을 처리하는 igdb(endpoint, query) 함수를 전달합니다. 비밀키를 공유하거나 JSON 파일에 넣을 필요가 없습니다.

~~~python
from sync_taxonomy import sync_igdb

snapshot = sync_igdb(igdb, "igdb_taxonomy_20261117.json")
~~~

genres/themes/game_modes/player_perspectives/keywords/platforms를 ID 순서로 끝까지 조회합니다.
조회 전후 count와 실제 수집 개수를 비교하며, 중단·개수 불일치는 완료로 표시하지 않습니다.
complete가 true여도 semantic_complete가 false면 아직 의미 통합을 검토할 값이 남아 있습니다.
keywords의 게임명·인물명·고유명사를 일반 취향 태그로 억지로 합치면 안 됩니다.
수집 파일의 review_required 항목을 검토한 뒤 사전에 동의어를 추가해야 합니다.
platforms는 기기 분류 검토용 원본으로 포함되며 취향 어휘 의미 완료 집계에서는 제외합니다.

## 검증

사전 충돌·Steam 스냅샷 전체 대응·IGDB seed 대응·동의어 일치·다른 개념 분리·부모 관계 순환 검사를 JavaScript 실행 환경에서 수행했습니다.
이번 세션에는 Python 실행 환경이 없어 Python 모듈 실행과 실제 인증 IGDB 동기화는 수행하지 못했습니다. 테스트 파일은 포함했습니다.

~~~text
python -m unittest test_normalization -v
~~~

## 출처

- Steam 공개 태그 스냅샷: https://store.steampowered.com/tag/browse/
- Steam 공식 태그 설명: https://partner.steamgames.com/doc/store/tags
- IGDB API 필드·인증·분류 엔드포인트: https://api-docs.igdb.com/

확인일: 2026-11-17.
