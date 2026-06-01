# Git2Value 점수/기여도 판정 로직 정리 (v7.2-upgrade.5)

이 문서는 현재 구현 기준으로 **점수 산출**, **팀/개인 판정**, **기여 역할 분류**, **최종 등급 산정**을 처음 보는 사람도 이해할 수 있게 풀어쓴다.

대상 코드:

- `github_extractor.py`
- `portfolio_diagnosis.py`
- `run_git2value.py`

---

## 0) 먼저 보는 변수 사전 (자주 등장)

- `valid_loc`: 실제 소스코드 라인 수(주석/문서 제외 중심)
- `evidence_loc`: 문서/설정/보조 산출물 라인 수(예: `md`, `json`, `yaml`)
- `analyzed_commit_count`: 점수 계산에 사용된 커밋 수(샘플링 구간)
- `total_census_authored`: 전수 조사에서 "작성자 연결 가능한" 전체 커밋 수
- `census_unlinked_count`: 작성자 계정과 매칭되지 않은 커밋 수(`author is None`)
- `distinct_author_count`: 유의미 작성자 수(임계값 통과 작성자만)
- `target_*`: 지원자(분석 대상 GitHub 사용자) 기준 값
- `ratio`: 비율값(0.0 ~ 1.0)

> 참고: 본 문서의 `%` 표기는 사람이 읽기 쉽게 쓴 표현이고, 코드 내부는 소수(예: `0.85`)를 사용한다.

---

## 1) 전체 흐름

1. `evaluate_repository()`에서 레포 단위 지표 계산
   - 작성자 전수 조사
   - 팀/개인 판정
   - 점수축 3개(Contribution/Quality/Consistency)
2. `extract_applicant_profile()`에서 다중 레포 합산
   - 최종 GitHub 점수: `best*0.7 + avg*0.3`
3. `run_diagnosis()` + `expected_level()`에서 등급(Top/Competitive/Entry) 산정

---

## 2) 작성자/기여도 판정 로직

### 2-1. 전수 조사 기준

- 작성자 판정은 `MAX_CENSUS_PAGES=20` 기준 전수 수집 사용.
- 봇/미연결 작성자 처리:
  - 봇: 팀/개인 판정에서 제외
  - `author is None`(미연결): 작성자 수 집계에서 제외

### 2-2. 유의미 작성자 필터

- 임계값 상수:
  - `MIN_AUTHOR_COMMITS_ABSOLUTE = 3`
  - `MIN_AUTHOR_COMMIT_RATIO = 0.02` (2%)
- 실제 적용 임계값:
  - `threshold = max(3, ceil(total_census_authored * 0.02))`
- 판정:
  - 각 작성자 커밋 수가 `count >= threshold`면 `significant_author_keys`로 인정.

수식 해석:

- 전체 커밋이 적은 레포에서는 최소 3커밋 규칙을 적용하고,
- 전체 커밋이 큰 레포에서는 2% 규칙을 적용해 "스쳐간 기여자"를 제거한다.

짧은 예시:

- `total_census_authored=120`이면 `ceil(2.4)=3`이므로 `threshold=3`
- `total_census_authored=700`이면 `ceil(14)=14`이므로 `threshold=14`

### 2-3. 팀/개인 판정의 기본 신호

- `distinct_author_count = len(significant_author_keys)` (데이터 부족 시 fallback 존재)
- `has_team_experience = (distinct_author_count >= 2)`

설명:

- `has_team_experience`는 "실제로 2인 이상이 유의미하게 기여했는가"를 나타내는 팀 경험 플래그다.
- 이 값은 등급 판단에서 팀 경험 신호로 우선 사용된다.

### 2-4. 지배적 기여자 재판정 (dominance override)

- 지원자 기준 지배 비율:
  - `dominance_ratio = target_effective_commits / total_authored`

변수 뜻:

- `target_effective_commits`: 지원자(author=username)의 유효 작성 커밋 수
- `total_authored`: 유의미 작성자들의 유효 작성 커밋 총합

재판정 조건(모두 충족 시):

- `distinct_author_count >= 2`
- `target_effective_commits > 0`
- `dominance_ratio >= 0.85` (85% 이상)

충족 시 결과:

- `is_dominance_override = True`
- `repo_type = "personal"`

미충족 시 기본 규칙:

- `repo_type = "team"` if `distinct_author_count >= 2` else `"personal"`

핵심 해석:

- 팀 레포라도 지원자 1인이 사실상 대부분(85%+)을 작성했다면 **배점 모드**를 개인으로 돌린다.
- 단, `has_team_experience`는 별도로 유지될 수 있어 `repo_type=personal` + `has_team_experience=true` 조합이 가능하다.

### 2-5. 지원자 비율/역할 라벨

- 전수 기준 지원자 비율:
  - `target_commit_ratio_census = target_commit_count / total_repo_commit_count`
  - `total_repo_commit_count = total_census_authored + census_unlinked_count`

역할 라벨(팀 컨텍스트에서만):

- `>= 0.5`: `주도 기여`
- `>= 1/distinct_author_count`: `적극 기여`
- 그 외: `협업`

개인 컨텍스트:

- `contribution_role = null`

역할 기준 해석:

- `1/distinct_author_count`는 "n명이 공정하게 나눴을 때 1인 몫"이다.
- 예: 유의미 작성자 4명이면 기준은 `0.25`(25%).

---

## 3) 레포 점수 산출 로직 (100점)

레포 총점:

- `repo_score = contribution_axis + quality_axis + consistency_axis`
- 각 축 최대점: `60 + 30 + 10 = 100`

### 3-1. Contribution axis (최대 60)

#### (1) LOC 점수

- `loc_score_main = log(valid_loc/100 + 1) / log(101) * 100`
- `loc_score_ev = log(evidence_loc/500 + 1) / log(101) * 50`
- `loc_score = min(100, loc_score_main + loc_score_ev)`

수식 해석:

- 로그 스케일을 써서 초반 증가(작은 프로젝트 성장)는 크게 반영하고, 큰 값으로 갈수록 증가폭을 완만하게 만든다.
- `evidence_loc`는 보조 증거이므로 최대 50 가중으로 제한된다.

#### (2) 개발 활동 이력 점수(커밋 기반)

- `commit_score = log(analyzed_commit_count/5 + 1) / log(21) * 100`
- `adjusted_commit_score = commit_score * commit_quality_factor`
- `commit_quality_factor`:
  - 무의미 커밋 비율 `< 0.15` → `1.0`
  - `< 0.35` → `0.9`
  - `>= 0.35` → `0.8` (하한 고정)

수식 해석:

- 커밋 신호도 로그 스케일이다.
- 초기 활동 이력(0→10 커밋)의 정보량은 크게 반영하고, 이후는 완만하게 반영한다.
- 커밋 개수만 많아도 메시지 품질이 낮으면 활동 점수가 일부 감산된다.

#### (3) LOC/개발 활동 이력 혼합 가중치

- `<5`: `loc_w=0.9`, `commit_w=0.1`
- `<15`: `loc_w=0.6`, `commit_w=0.4`
- `>=15`: `loc_w=0.5`, `commit_w=0.5`

해석:

- 커밋 수가 아주 적으면 활동 이력 신뢰도가 낮다고 보고 LOC 비중을 높인다.
- 활동 이력이 충분하면 LOC와 활동 신호를 균형 있게 본다.

#### (4) 축 환산

- `blend_100 = loc_score * loc_w + adjusted_commit_score * commit_w`
- `contribution_axis = (blend_100/100) * 60`

짧은 예시:

- `loc_score=70`, `commit_score=50`, 품질 계수 `0.9`, 커밋 20개(`0.5/0.5`)라면
- `adjusted_commit_score=45`, `blend_100=57.5`, `contribution_axis=34.5`

#### (5) Fork 패널티(해당 시)

- 비포크: 계수 `1.0`
- 사실상 단독 저작(`ratio>=0.8 && commits>=20`): `1.0`
- 공정기준 이상(`ratio>=1/distinct`): `0.7`
- 공정기준 50% 이상: `0.5`
- 그 외: `0.3`
- 최종: `contribution_axis *= fork_penalty`

해석:

- 포크 레포는 "얼마나 본인이 실제로 작업했는가"를 강하게 본다.
- 팀 내 공정 몫 이상이면 페널티를 완화(`0.7`)하고, 매우 낮으면 강한 감점(`0.3`)을 준다.

### 3-2. Quality axis (최대 30)

공통 입력:

- `has_cicd`: CI/CD 파이프라인 존재 여부(boolean)
- `test_ratio`: 테스트 파일/코드 비율(정규화된 비율)
- `active_weeks`: 활동한 주(week) 수

팀(`repo_type == team`) 모드:

- CI/CD: `0 or 10`
- 테스트: `<0.05 -> 0`, `<0.20 -> 5`, `>=0.20 -> 10`
- 활성 주: `<4 -> 0`, `<8 -> 5`, `>=8 -> 10`
- 합계 최대 30

개인(`repo_type == personal`) 모드:

- 활성 주: `<2 -> 2`, `<4 -> 6`, `<8 -> 12`, `>=8 -> 20`
- CI/CD 보너스: `0 or 5`
- 테스트 보너스: `<0.05 -> 0`, `<0.10 -> 3`, `>=0.10 -> 5`
- 합계 최대 30

모드 차이 해석:

- 팀 모드는 협업 품질 신호(CI/CD/테스트/운영 기간)를 균형 배점.
- 개인 모드는 지속성(`active_weeks`)을 크게 본다(최대 20점).

### 3-3. Consistency axis (최대 10)

- 커밋 5개 미만: `0`
- 그 외:
  - 커밋 간 일(day) 간격 표준편차 `std`
  - `consistency = max(0, 10 - std * 0.5)`

수식 해석:

- 커밋 간격의 흔들림(`std`)이 작을수록 규칙적 활동 이력으로 보고 점수가 높다.
- 표준편차가 커지면 선형으로 감점되고, 최저 0점으로 바닥 처리된다.

---

## 3-4) README는 어디에 반영되는가?

README는 **100점 점수축(contribution/quality/consistency)에 직접 배점되지 않는다.**
성장성(`growth_signal`)도 **점수축 직접 배점 없이 진단 신호로만** 제공된다.

대신 아래 경로로 반영된다.

- `portfolio_diagnosis.py`의 `readme_quality` 핵심 진단 항목
- `expected_level()`의 티어 gate (`readme_ok`)
- `run_git2value.py` 매칭용 프로필 생성 시 README 요약/키워드 보조 신호
- `merge_readme_domain_hits()`를 통한 도메인 보조 신호
- `.md` 변경은 `evidence_loc`로 contribution에 **간접** 보조 반영 가능

즉 README는 점수 본축보다는 **설명 가능성/티어 진입/매칭 보조**에 더 큰 영향을 준다.
성장성은 `per_repo[].diagnosis.extra_items.growth_signal`에서 확인한다.

---

## 4) 지원자 최종 GitHub 점수

유효 레포가 있을 때:

- 각 레포의 `(contribution + quality + consistency)` 계산
- `best_score = max(repo_scores)`
- `avg_score = mean(repo_scores)`
- `final_github_score = round(best_score * 0.7 + avg_score * 0.3, 1)`

해석:

- 가장 강한 대표 프로젝트를 70% 반영하면서,
- 나머지 레포들의 전체 평균도 30% 반영해 "한 방 성과 + 전반적 안정성"을 같이 본다.

유효 레포 없으면 `0.0`.

`run_git2value.py` 응답 `github_score.method`도 동일 규칙으로 표기.

---

## 5) 등급(Top/Competitive/Entry) 판정 로직

위치: `portfolio_diagnosis.expected_level()`

### 5-1. 팀 컨텍스트 집계

- `run_diagnosis()`의 `team_repo_count`:
  - `has_team_experience` 우선
  - 없으면 `repo_type == "team"` 폴백
- `expected_level()` 내부 팀 운영신호 집계(`team_diags`)도 동일 축:
  - `has_team_experience` 또는 `repo_type == "team"`

해석:

- 배점 모드(`repo_type`)가 개인으로 바뀐 케이스라도,
- 실제 팀 경험 신호(`has_team_experience`)가 있으면 등급 평가에서 팀 경험을 인정한다.

### 5-2. Top 조건

- `readme_ok`
- `multi_proj`(레포 2개 이상)
- `team_repo_count >= 1`
- `has_test && has_cicd && has_deploy`
- `score >= 8`

### 5-3. Competitive 조건

- `readme_ok`
- `team_repo_count >= 1`
- `(has_cicd or has_deploy)`
- `multi_proj`
- `score >= 5`

### 5-4. Competitive(개인) 조건

- `team_repo_count == 0`
- `n_repos >= 2`
- core 3개 상태가 모두 `양호/보통`
- 개인 레포 extra(`test/cicd/deploy`)에서 `양호/규칙적` 2개 이상
- `score >= 5`

그 외는 Entry.

해석 팁:

- `multi_proj`(2개 이상) 조건 때문에 단일 레포만으로 상위 등급 달성은 구조적으로 어렵다.

---

## 6) API 응답에서 확인 가능한 핵심 필드

`/v1/analyze` -> `per_repo[]`:

- `repo_type`: 점수 배점 모드용 팀/개인 분류
- `has_team_experience`: 실제 팀 경험 신호
- `distinct_author_count`: 유의미 작성자 수
- `dominance_ratio`: 지원자 지배 기여 비율
- `is_dominance_override`: 지배적 기여자 개인 재판정 여부
- `target_commit_ratio`: 샘플 커밋 기준 지원자 비율
- `target_commit_ratio_census`: 전수 커밋 기준 지원자 비율
- `contribution_role`: 팀 컨텍스트에서의 역할 라벨
- `score_breakdown`: `contribution/quality/consistency` 축별 점수
- `score_detail`: 축별/세부 항목별 `score`, `max_score`, `potential_gain`, `raw_value`, `improvement_hint`

`/v1/analyze` -> `github_score`:

- `breakdown`: 대표 레포 기준 60/30/10 축 점수
- `axes`: 대표 레포 기준 점수 해석 가이드(축별 세부 항목)
- `score_detail`: 대표 레포 기준 상세 구조(만점/획득점/개선 여지)

`level`:

- `grade` (`Top`/`Competitive`/`Competitive (개인)`/`Entry`)
- `description`

---

## 7) 해석 시 주의점

- `repo_type`와 `has_team_experience`는 목적이 다르다.
  - `repo_type`: 배점 방식 결정(quality 모드 포함)
  - `has_team_experience`: 등급에서 팀 경험 인정 신호
- 그래서 `repo_type=personal` + `has_team_experience=true`는 정상 케이스다.

- `target_commit_ratio`와 `target_commit_ratio_census`도 목적이 다르다.
  - 전자: 점수 계산 파이프라인에서 쓰는 샘플 기준 보조 신호
  - 후자: 작성자 전수 조사 기반 역할/기여 판단 신호

- 도메인 감지(`detected_domains`)는 직무 매칭 보조 신호이며, 점수식 자체와 분리되어 있다.
- 커밋 항목은 단순 커밋 개수 평가가 아니라 개발 활동 이력(활동량 + 지속성 + 리듬) 신호다.

---

## 8) 빠른 예시 1개 (끝까지 읽기 전 감 잡기)

가정:

- 유의미 작성자 3명(`distinct_author_count=3`)
- 지원자 유효 커밋 90, 유의미 작성자 전체 100
- `dominance_ratio=0.90`

결론:

1. 팀 경험 신호: `has_team_experience=true` (3명이라서)
2. 지배 재판정 발동: `is_dominance_override=true`, `repo_type=personal`
3. 따라서:
   - 점수 배점은 개인 모드(quality 개인 규칙)
   - 등급 평가에서는 팀 경험 레포로도 집계 가능(팀 신호 유지)

이 예시는 v7.2 정책의 핵심 의도(배점 모드와 팀 경험 신호 분리)를 보여준다.
