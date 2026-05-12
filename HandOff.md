# Git2Value — 프로젝트 HandOff 문서

> 작성일: 2026.04.01 | 최종 갱신: 2026.05.12 | 현재 스펙 버전: v3.0 | 현재 구현 버전: **v6.3**

새 컨텍스트에서 이 프로젝트를 이어받을 경우 이 문서를 먼저 읽으세요.

### HandOff 갱신 규칙 (에이전트·협업)

- **MultiDomain/사용자 피드백 수정 체크리스트**로 작업할 때는 **체크리스트의 각 단계(Step)를 완료할 때마다** 이 `HandOff.md`를 갱신한다.
- 갱신 내용: 해당 단계에서 바뀐 파일·동작 요약, 버전/이력 섹션 반영, 알려진 과제 목록 정합.
- 외부 문서(Spec_v3, 논문, 발표 자료)도 메이저 버전 변경 시 동기 갱신한다.

---

## 1. 프로젝트 개요

**Git2Value**는 **신입(0~3년) 개발자**를 주 대상으로, GitHub 레포지토리와 채용 공고(JD) 벡터 매칭을 결합해 **포트폴리오 진단**, **직무 적합도(상위 공고 매칭)**, **시장 연봉 밴드(참고)**를 **서로 독립된 모듈**로 제공하는 파이프라인입니다.

v4.0부터는 GitHub 점수로 연봉을 곱하는 **멀티플라이어 모델을 제거**했습니다(근거 부족·신뢰도 리스크). 연봉은 점핏·원티드 데이터 기반 **직무별 시장 구간**만 제시합니다.

v6.0~v6.1에서는 사용자(취준생) 관점 출력 품질을 대폭 개선하여, **레포별 카드 진단**(팀/개인 분리)·**경력 필터링**·**다중 도메인 균형 추천**·**종합 분석 블록**을 도입했습니다.

### 핵심 흐름

```
GitHub Username + 레포 URL 리스트 (최대 3개)
        ↓
GitHubExtractor (github_extractor.py)
  - API 수집 (커밋, 트리, README, 메타)
  - 의존성 파일(blob) 선택 조회 → 프레임워크 추출
  - 트리 경로 시그니처 기반 환경 감지
    (게임 엔진/Lua 호스트/모드 플랫폼/모바일·블록체인·인프라·도구)
  - 트리 경로 기반 도메인 시그널 감지
  - 두 종류 커밋 분리 수집 (v6.1):
    · 지원자 author 필터 커밋 → 기여도·커밋 메시지·커밋 리듬 평가
    · 레포 전체 커밋 → 팀/개인 판정 (distinct_author_count 산출)
  - 균등 샘플링 + SHA dedup
  - 점수 산출 (contribution: v5.5 동적 가중치 + Evidence LOC / quality / consistency)
        ↓
github_score + score_breakdown + per_repo + profile_for_matching
        ↓
profile_builder.build_profile_text() — JD 문체에 가까운 매칭용 텍스트
        ↓
run_git2value.py (E2E 데모)
  - FAISS k=20 + 임베딩 → 경력 필터 → 도메인 리랭킹 또는 균형 추천 (모듈 A)
  - portfolio_diagnosis.run_diagnosis() → 레포별 카드 진단 + 종합 분석 (모듈 B)
  - Git2ValueEngine.get_market_band() → realistic_range + 참고 직무 직접 조회 (모듈 C)
```

### 설계 원칙: 외부 API 의존 0

Git2Value는 **GitHub API**(데이터 수집)를 제외하면 외부 서비스 호출이 없습니다. ChatGPT, Claude 등 **외부 LLM API를 사용하지 않으며**, 전체 분석·매칭·진단 파이프라인이 로컬에서 동작합니다.

- 비용 0 (API 과금 없음)
- 네트워크 장애 시에도 정상 동작 (데모 안정성)
- 캡스톤 종합설계 취지에 부합 (자체 엔진 구축)

프로필 변환·README 평가가 부족할 경우의 단계적 전환 경로: (1) 룰베이스 템플릿 → (2) 로컬 오픈소스 모델 (RTX 4090 기준 Qwen2.5 등) → (3) 외부 API (최후 수단).

---

## 2. 파일 구조

```
basic/
├── github_extractor.py      # GitHubExtractor (수집·점수·per_repo 집계)
├── profile_builder.py       # 도메인·엔진 시그니처 감지, 의존성 파싱, build_profile_text()
├── portfolio_diagnosis.py   # 레포별 카드 진단 (v6.1: core 3 + extra 4 항목)
├── valuation_engine.py      # v4.0: get_market_band() + v6.0 realistic_range
├── experience_filter.py     # v6.0/v6.1: 경력 요건 필터링 (사이드카 캐시)
├── run_git2value.py         # E2E: 모듈 A/B/C 통합 출력 (v6.1)
├── requirements.txt         # 의존성 (sentence-transformers==2.6.1 버전 고정 중요)
├── .env                     # Github_api_token 환경변수 (버전 관리 제외)
├── HandOff.md               # 이 파일
│
├── vector/
│   ├── git2value_faiss.index
│   ├── git2value_metadata.json
│   ├── experience_cache.json    # v6.0 자동 생성 (경력 필터 사이드카, v6.1 requirement_type 포함)
│   ├── unified_jd_corpus.jsonl
│   └── wanted_job_ids.json
│
├── data/
│   ├── jumpit_data/
│   ├── wanted_data/
│   └── ...
│
├── kaggle/   (비활성, 무시)
├── used/     (비활성, 무시)
└── md/       (과거의 계획 파일, 필요할 때만 사용)
```

---

## 3. 핵심 파일별 역할

### `github_extractor.py` — GitHubExtractor 클래스

| 메서드 | 역할 |
|---|---|
| `_fetch_with_retry` | 모든 API 호출 게이트. 403/429 시 Retry-After 파싱 + 지수 백오프 (최대 3회) |
| `_fetch_repo_text_files` | **v4.0** 의존성 파일 등 contents API로 텍스트 조회 |
| `_fetch_all_commits_paginated` | 커밋 목록 수집. `MAX_COMMIT_PAGES=3` (최대 300커밋) 상한 |
| `_commit_author_key` (v6.1) | **신규**: GitHub login > email > name 우선순위로 작성자 안정 식별. prefix(`login:`/`email:`/`name:`)로 카테고리 충돌 방지 |
| `_commit_author_label` (v6.1) | **신규**: 리포트 표시용 작성자 이름 |
| `_stratified_sample_commits` | 초기/중간/최근 각 최대 25개씩, 레포 내부 + 전역 SHA dedup |
| `_cicd_and_test_ratio_from_tree` | tree blob size>200B로 CI/CD 실질성 판별, 테스트 파일 비율 계산 |
| `_count_active_weeks` | author 커밋 목록 기준 ISO 주(년+주차) 개수 |
| `_calc_consistency_score` | 커밋 간격 표준편차 → `max(0, 10 - std * 0.5)`. 전체 author 커밋 목록 기준 |
| `evaluate_repository` | 레포 1개 완전 분석. **v6.1**: 두 종류 커밋 분리 수집(`all_author_commits` + `all_repo_commits`), `repo_type`/`distinct_author_count`/`target_commit_*`/`repo_active_weeks` 산출 |
| `extract_applicant_profile` | LOC 가중 github_score + `profile_for_matching` + `domain_hits_merged` + `per_repo`(v6.1: `repo_type`·`repo_author_names`·`target_commit_count`·`total_repo_commits`·`target_commit_ratio`·`repo_active_weeks` 추가) |

**클래스 상수:** `MAX_COMMIT_PAGES = 3`

**환경변수:** `Github_api_token`

#### v6.1 신규: 두 종류 커밋 분리 수집

```python
# 지원자 기여도 계산용
commits_list_url = f"{repo_url}/commits?author={username}&sha={branch}&per_page=100"
# 팀/개인 판정용 (author 필터 없음)
repo_commits_list_url = f"{repo_url}/commits?sha={branch}&per_page=100"
```

- 이전(v6.0): `all_author_commits`만 수집 → 팀 레포여도 author 필터를 거친 커밋만 보면 작성자 1명으로만 보여서 개인 레포로 오판
- 이후(v6.1): 레포 전체 커밋도 별도 수집하여 `distinct_author_count` 산출 정확도 확보
- 폴백: 레포 전체 조회 실패 시 `all_repo_commits = list(all_author_commits)` (경고 출력)

#### v6.1 신규: 레포 분류 필드

| 필드 | 의미 |
|---|---|
| `repo_type` | `"team"` (distinct_author_count >= 2) 또는 `"personal"` |
| `distinct_author_count` | 레포 전체 커밋 작성자 수 (login > email > name 우선순위) |
| `repo_author_names` | 표시용 작성자 라벨 리스트 (최대 10명) |
| `target_commit_count` | 지원자 본인 커밋 수 |
| `total_repo_commits` | 레포 전체 커밋 수 |
| `target_commit_ratio` | 지원자 커밋 / 레포 전체 커밋 비율 |
| `repo_active_weeks` | 레포 전체 커밋 기준 활성 주 수 (지원자 기준 `active_weeks`와 별도) |

---

### `profile_builder.py` — v5.8

- **`ENGINE_SIGNATURES` / `detect_engine_signatures(tree_data)`** (v5.4~v5.8): 게임 엔진 4종 + 분석 환경 2종 + 신규 8종(모바일·블록체인·인프라·데이터·도구) 감지
- **`detect_signatures_with_content()`** (v5.8): manifest 내용 검증 비동기 함수 (Expo·VS Code 확장·Browser Extension)
- **`MOD_PLATFORM_SIGNATURES` / `detect_mod_platform()`** (v5.7): EDOPro·Garry's Mod·Factorio·Minecraft·Stardew Valley·WoW 6종
- **`LUA_HOST_SIGNATURES` / `detect_lua_host()`** (v5.6): Roblox·Love2D·Defold·Solar2D·Cocos2d-x·OpenResty·NodeMCU·Neovim 9종
- **`MAIN_LANGUAGES` / `SUB_LANGUAGE_SIGNALS`** (v5.6): 언어 메인/서브 분류
- **`categorize_languages(lang_stats)`** (v5.6): main/sub/trivial 분리
- **`detect_domain_hits` / `merge_domain_hits`**: 트리 경로 기반 도메인 히트. **고유 키워드 종류 수** 기준, 2종류 미만 도메인 제외 (v5.3.1)
- **`find_dependency_paths` / `parse_dependency_contents`**: package.json 등에서 프레임워크 라벨 추출
- **`has_deployment_signals`**: docker-compose, Vercel 등 배포 시그널
- **`compute_tree_structure_stats`**: 파일당 평균 LOC, `.gitignore` 여부
- **`build_profile_text`**: FAISS 질의용 공고형 문장. v5.6 `language_category`/`sub_language_host` 기반 메인/서브 분리 출력
- **`READ_KEYWORDS` / `extract_readme_keywords()`**: 도메인별 키워드 사전 + 압축 문장 추출 (v5.3.2 영어/CV/NLP 보강, v5.8 블록체인/데이터/도구개발 추가)

#### README 활용 분기 로직 (v5.3)

| 잔량 | 티어 | `build_profile_text` 반영 |
|---|---|---|
| 200자 이상 | long | 키워드 추출 성공 시에만 압축 문장 추가 |
| 50~199자 | medium | README 본문 미반영 (구조·언어·의존성 데이터만) |
| 49자 이하 | short | 동일 |

원칙: 부실 README는 프로필에 넣지 않는다. 키워드 추출 실패 시에도 **원문 폴백 없음** (v5.3).

---

### `portfolio_diagnosis.py` — v6.1 (레포별 카드 진단)

**v6.1 핵심 변경:** 진단 구조를 **전체 통합** → **레포별 카드**로 전환. 개인 레포와 팀 레포를 분리 평가.

#### 진단 구조

```
diagnose_single_repo(repo) →
  {
    "repo_name": "...",
    "repo_type": "personal" | "team",
    "core_items": {
      "readme_quality": {...},      # 모든 레포 공통
      "project_structure": {...},   # 모든 레포 공통
      "commit_quality": {...},      # 모든 레포 공통
    },
    "extra_items": {
      "test_coverage": {...},       # 팀 레포에서만 필수, 개인은 가산점
      "cicd": {...},                # 팀 레포에서만 필수, 개인은 가산점
      "deployment": {...},          # 팀 레포에서만 필수, 개인은 가산점
      "commit_pattern": {...},      # 지원자 본인 기준 (팀 레포에서 필수)
    },
  }
```

#### 주요 함수

| 함수 | 역할 |
|---|---|
| `classify_repo_type(repo)` (v6.1) | `repo.repo_type` 우선 사용, 폴백으로 `distinct_author_count >= 2` 판정 |
| `_readme_diagnosis_single(repo)` (v6.1) | 단일 레포 README 평가 (3차원 + 길이) |
| `_structure_diagnosis_single(repo)` (v6.1) | 단일 레포 구조 평가 |
| `_commit_quality_diagnosis_single(repo)` (v6.1) | 무의미 커밋 비율 + Conventional Commits 변환 힌트 |
| `_test_diagnosis_single(repo, game_engines)` (v6.1) | 단일 레포 테스트 (게임 엔진 맥락 반영) |
| `_cicd_diagnosis_single(repo, game_engines)` (v6.1) | 단일 레포 CI/CD |
| `_deployment_diagnosis_single(repo, game_engines)` (v6.1) | 단일 레포 배포 |
| `_commit_pattern_diagnosis_single(repo)` (v6.1) | **지원자 본인 기준** 커밋 리듬 (`target_commit_count` / `active_weeks`) |
| `_team_required_items(extra_items)` (v6.1) | 팀 레포의 extra를 "필수 미흡"으로 격상 |
| `diagnose_single_repo(repo)` (v6.1) | 레포 1개 진단 결과 반환 |
| `expected_level(per_repo_diags, team_repo_count)` (v6.1) | 등급 판정. **팀 레포가 없으면 Competitive 이상 도달 불가** |
| `evaluate_readme_quality(readme_text)` (v6.0) | 3차원 룰베이스 (목적/스택/시각화) |
| `COMMIT_REWRITE_HINTS` / `get_rewrite_hint(msg)` (v6.0) | 무의미 커밋 → Conventional Commits 변환 힌트 |
| `_aggregate_strengths(per_repo_diags)` (v6.1) | 양호 항목 빈도순 강점 추출 (개인 레포는 core만, 팀은 core+extra) |
| `_aggregate_quick_wins(per_repo_diags)` (v6.1) | 미흡 항목 빈도순 Quick wins 추출 |
| `_portfolio_composition_lines()` (v6.1) | 레포 구성 요약 (개인 N개 + 팀 M개) |
| `generate_summary_block()` (v6.1) | 종합 분석 블록 — GitHub 점수 + 레포 구성 + 강점 + Quick wins |
| `repo_classification_note(repo)` (v6.0) | 레포의 협업 여부 한 줄 요약 |
| `mod_context_message()` / `config_repo_message()` (v5.7) | 모드/설정 프로젝트 안내 |
| `blockchain_context_message()` / `data_engineer_context_message()` / `tool_dev_context_message()` (v5.8) | 신규 도메인 맥락 메시지 |
| `_build_repo_classifications(per_repo)` | 레포별 분류(main/mod/config) + 안내 메시지 |
| `run_diagnosis(profile)` (v6.1) | 진입점. 반환에 **`per_repo_diagnoses`** (이전 `portfolio_diagnosis` 대체) |

#### v6.1 등급 판정 로직 변경

```python
# Top: 팀 레포 1개 이상 + 모든 운영 항목 양호 + score >= 8
if readme_ok and multi_proj and team_repo_count >= 1
   and has_test and has_cicd and has_deploy and score >= 8:
    return "Top"

# Competitive: 팀 레포 1개 이상 + (CI/CD 또는 배포) + 멀티 프로젝트 + score >= 5
if readme_ok and team_repo_count >= 1
   and (has_cicd or has_deploy) and multi_proj and score >= 5:
    return "Competitive"

# 기본 Entry
return "Entry"
```

**중요:** 개인 레포만 있는 사용자는 절대 Competitive 이상 도달 불가. 신입 현실에 부합하는 보수적 기준.

#### 상태 라벨 (v6.1)

| 상태 | 의미 | _BAD_STATUSES 포함 |
|---|---|---|
| 양호 | 충족 | ❌ |
| 규칙적 | 커밋 리듬 양호 | ❌ |
| 보통 | 부분 충족 | ❌ |
| 미흡 | 부족 | ✅ |
| 개선 필요 | 일부 충돌 | ✅ |
| 미경험 | 시도 흔적 없음 | ✅ |
| 선택 가점 | 테스트 미감지 (Top 차별화 요소) | ✅ |
| **없음** (v6.1) | 운영 항목 부재 | ✅ |
| **필수 미흡** (v6.1) | 팀 레포에서 운영 항목 부재 | ✅ |
| **확인 필요** (v6.1) | 산출 불가 (커밋 리듬) | ✅ |

---

### `valuation_engine.py` — Git2ValueEngine (v4.0 + v6.0)

- `data/jumpit_data/korean_it_salary_lookup_2025.py` 동적 로드
- **`get_market_band(job_category, years_max=3)`**: 신입(0~3년) 구간, 점핏 junior P50 + 원티드 JSON(매핑 시) 교차 → `combined_range` 문자열
- **`realistic_range`** (v6.0): 중앙값 기준 ±15%/+20% 추정 분포 (P25, P75)
- **`category_comparison`**: 상위 12개 고연봉 직무 리스트 (참고용, **v6.1에서 모듈 C 출력은 직접 조회 방식으로 대체**)
- `JUMPIT_TO_WANTED_FILE`: 점핏 직무명 → `data/wanted_data/salary_data/*.json`

#### v6.1 출력 단의 변경 (run_git2value 측)

`category_comparison`에 의존하지 않고 `get_market_band(cat, ...)`로 직무별 직접 조회. 프론트엔드처럼 데이터가 있어도 상위 12개에 들지 못하는 직무가 누락되던 문제 해결.

---

### `experience_filter.py` — 경력 필터 모듈 (v6.0/v6.1)

**v6.1 변경:** `requirement_type` 필드 도입 + `is_applicant_eligible()` 분리 + `split_by_experience()` 추가.

```python
EXPERIENCE_PATTERNS = [
    (r"경력\s*무관|경력무관|...", "open_to_all"),    # v6.1 신규
    (r"신입|주니어|junior|entry\s*level", "junior_only"),
    (r"시니어|senior|리드|lead", "senior_only"),
    (r"경력\s*(\d+)\s*[년~\-]\s*(\d+)?\s*년", "range_years"),
    (r"(\d+)\s*년\s*이상", "min_years_exp"),
    (r"(\d+)\s*년차", "specific_years"),
]
```

| 함수 | 역할 |
|---|---|
| `extract_experience_requirement(position, text)` | 정규식으로 경력 요건 추출. `requirement_type` 6분류 (`unspecified`/`open_to_all`/`junior`/`senior`/`min_years`/`specific_years`) |
| `is_applicant_eligible(exp_req, applicant_years)` (v6.1) | 추천 후보 적격 여부. **0년차는 `unspecified`/`open_to_all`/`junior`만 허용 + `min_years <= 0`** |
| `load_or_build_cache(metadata, cache_path)` | 사이드카 캐시(`vector/experience_cache.json`) 로드/빌드. v6.1: 누락 항목(`requirement_type` 없음) 갱신 |
| `split_by_experience(top_matches, applicant_years, cache)` (v6.1) | 적격/제외 공고 분리 반환 |
| `filter_by_experience(...)` (하위 호환) | `split_by_experience` 결과를 합쳐서 반환 |

#### 0년차 기준 차이

| 패턴 | v6.0 처리 | v6.1 처리 |
|---|---|---|
| "1년 이상" | 신입+1년 여유로 통과 | **추천에서 제외** (`min_years > 0`) |
| "신입/경력" | `junior_only` 매칭 → 통과 | `open_to_all` 매칭 → 통과 |
| "경력무관" | `unspecified` 폴백 → 통과 | `open_to_all` 명시 → 통과 |

---

### `run_git2value.py` — E2E 파이프라인 (v6.1)

#### 기본 설정

- FAISS 인덱스(`vector/`) + `jhgan/ko-sroberta-multitask`
- 임베딩 입력: `profile_for_matching` (없으면 `applicant_resume` 폴백)
- **`MAX_REPO_COUNT = 3`** (v6.1): 입력 레포 최대 3개로 제한, 초과 시 앞 3개만 사용
- **FAISS k=20** (v6.0): 다중 도메인 균형 추천 + 경력 필터 여유분 확보

#### 모듈 A 핵심 함수

| 함수 | 역할 |
|---|---|
| `route_job_category_safe()` (v6.0) | 콤마/슬래시 포함 결과 방어 래퍼 |
| `rerank_by_domain()` (v5.3) | 단일 도메인에서 +0.05 가산. 다중 도메인 시 억제 |
| `recommend_multi_domain()` (v6.0) | 히트 비율 < 2배이면 도메인별 상위 1~2개씩 분리 추천 |
| `similarity_label()` (v6.1) | **절대값 기준 도입**: max_s < 0.70 시 "약함" 통일, score >= 0.85 시 "강함", 그 외 spread 기반 분기 |
| `diagnose_domain_mismatch()` (v6.0) | db_coverage/weak_signal/consistent/ambiguous 4분기 |
| `analyze_tech_match()` (v6.1) | **3단계 정교화**: 포함관계 처리(`TECH_INCLUSION_MAP`) + 도메인 무관 기술 필터(`DOMAIN_IRRELEVANT_TECHS`) + 미보유 3개 제한 + 학습 권장(`CATEGORY_TARGET_TECHS`) |
| `filter_techs_by_inclusion()` (v6.1) | Spring Boot 있으면 Spring 제거, Next.js 있으면 React 제거 등 |
| `filter_techs_by_domain()` (v6.1) | 매칭 직무와 무관한 기술 필터 |

#### 모듈 A 출력 (v6.1: 레포별 카드)

```
[지원자 요약]
  GitHub ID  : {username}
  경력       : {applicant_years}년차
  분석 레포  : {N}개 (개인 M / 팀 K)
  기술 스택  : {languages 비율 제거}

▼ 레포 1: {repo_name}  [개인 레포 / 팀 레포 · N명 협업]  (Unity/Spring 등)
  ─ 핵심 평가 항목 ─
    · README 품질 / 프로젝트 구조 / 커밋 메시지 (모든 레포 공통)
  ─ 필수 점검 항목 (팀 레포 기준) ─        # 팀 레포에서만 표시
    · 테스트 / CI/CD / 배포 / 커밋 리듬
        협업 신호: 전체 커밋 N개 중 지원자 커밋 M개 (X%)
```

#### 모듈 C 출력 (v6.1: 직접 조회)

```python
# category_comparison에 의존하지 않고 직무별로 get_market_band() 직접 조회
for cat in matched_categories_seen:
    ref_band = val_engine.get_market_band(job_category=cat, years_max=...)
    print(f"    {cat}: {ref_sr['combined_range']}")
```

#### 보조 상수

```python
TECH_INCLUSION_MAP = {           # 포함관계 (v6.1)
    "Spring Boot": ["Spring"],
    "Next.js": ["React"],
    "Nuxt": ["Vue"],
}

DOMAIN_IRRELEVANT_TECHS = {       # 도메인 무관 기술 (v6.1)
    "서버/백엔드": {"React", "Vue", "Flutter", "Swift", "Kotlin"},
    "프론트엔드": {"Spring", "Spring Boot", "FastAPI", "Django", "Kubernetes"},
    "게임 클라이언트": {"React", "Vue", "Spring Boot", "FastAPI", "Kubernetes"},
    ...
}

CATEGORY_TARGET_TECHS = {         # 학습 권장 (v6.1)
    "서버/백엔드": ["Spring Boot", "Docker", "AWS", "PostgreSQL", "Redis"],
    "프론트엔드": ["React", "TypeScript", "Next.js", "Tailwind CSS"],
    ...
}
```

#### 모듈 B 출력 (v6.1)

레포별 진단 카드 + 종합 분석 블록 (`generate_summary_block`):

```
[종합 분석]
  GitHub 점수  : {N}점 / 100점 (기여도 X / 성숙도 Y / 일관성 Z)
  포지셔닝     : {도메인} {Entry/Competitive/Top} 수준 포트폴리오 — {보강/유지 안내}

  포트폴리오 구성:
    · 레포 구성: 개인 N개 + 팀 M개 (총 K개)
    · 주요 도메인: {primary_domain}
    · 팀 프로젝트 1개 추가 시 협업 경험 어필에 유리합니다.   # 팀 레포 0개 시

  강점:
    · {양호 항목 상위 2개}

  실행 가능한 개선 (Quick Wins):
    1. {quick win 1}
    2. {quick win 2}
    3. {quick win 3}
```

---

## 4. 점수 산출 수식 (github_score, 진단 참고용) — v5.0 + v5.5

상세 근거: [`Scoring_Review.md`](Scoring_Review.md)

### Contribution (최대 60점)

로그 스케일로 변별력 확보. v5.5에서 Evidence LOC 보조·커밋 수 동적 가중치 추가.

```python
import math
loc_score_main = min(100, math.log(valid_loc / 100 + 1) / math.log(101) * 100)
loc_score_ev   = min(50,  math.log(evidence_loc / 500 + 1) / math.log(101) * 50)
loc_score      = min(100, loc_score_main + loc_score_ev)
commit_score   = min(100, math.log(analyzed_count / 5 + 1) / math.log(21) * 100)
if analyzed_count < 5:
    loc_w, commit_w = 0.9, 0.1
elif analyzed_count < 15:
    loc_w, commit_w = 0.6, 0.4
else:
    loc_w, commit_w = 0.5, 0.5
blend_100 = loc_score * loc_w + commit_score * commit_w
contribution_axis = (blend_100 / 100) * 60
```

- Fork 시 contribution에만 0.3배 패널티 (기존과 동일)

### Quality (최대 30점)

**CI/CD 10 + 테스트 10 + 활성 주 10**

| 항목 | 조건 | 점수 |
|---|---|---|
| CI/CD | 워크플로우/Dockerfile blob > 200B | 10 또는 0 |
| 테스트 비율 | < 5% | 0 / 5~20% → 5 / ≥20% → 10 |
| 활성 주 수 | `all_author_commits` ISO 주 개수 | ≥8주 → 10, ≥4주 → 5, 그 외 0 |

### Consistency (최대 10점)

```python
max(0.0, 10.0 - std * 0.5)   # std = 연속 커밋 간격(일)의 모표준편차
# 커밋 수 < 5개: 0점
```

타임스탬프 소스: 균등 샘플이 아니라 **전체 author 커밋 목록**(페이지네이션 상한 내).

### 전체 github_score 집계

LOC 가중 평균. **연봉 모듈 C에는 github_score를 사용하지 않음.**

### 기타 (v5.0/v5.5)

- `ignore_paths`: `__pycache__/`, `generated/`, `obj/`, `bin/`, `.next/`, `migrations/` 등
- `ignore_extensions` (v5.5): `.tf`, `.hcl`, `.proto`, `.sql` — 유효 LOC 대신 **`evidence_loc`**로만 집계

---

## 5. 출력 JSON 스키마

### `extract_applicant_profile()` 반환 (v6.1 갱신)

```json
{
  "github_score": 79.3,
  "score_breakdown": { "contribution": 42.0, "quality": 28.0, "consistency": 9.3 },
  "applicant_resume": "주요 기술 스택: … (레거시 미리보기용)",
  "profile_for_matching": "Python (90%) 기반 서버/백엔드 경험. FastAPI 활용 경험. …",
  "domain_hits_merged": { "서버/백엔드": 5, "웹 프론트엔드": 3 },
  "per_repo": [
    {
      "repo_name": "repo (main)",
      "readme": "…",
      "readme_has_image": true,
      "readme_tier": "long",
      "tree_stats": { "source_file_count": 42, "avg_loc_per_file": 120.5, "has_gitignore": true },
      "has_cicd": true,
      "has_tests": true,
      "has_deployment": false,
      "test_ratio": 0.12,
      "commit_messages": ["feat: …"],
      "distinct_author_count": 2,
      "repo_type": "team",
      "repo_author_names": ["alice", "bob"],
      "valid_loc": 5000,
      "evidence_loc": 120,
      "is_fork": false,
      "duration_days": 90,
      "active_weeks": 12,
      "repo_active_weeks": 18,
      "total_commits": 80,
      "total_repo_commits": 245,
      "target_commit_count": 80,
      "target_commit_ratio": 0.3265,
      "frameworks": ["FastAPI"],
      "detected_domains": ["서버/백엔드"],
      "language_category": { "main": [["Python", 90.0]], "sub": [["Shell", 10.0]], "trivial": [] },
      "sub_language_host": null,
      "is_config_repo": false,
      "mod_platform": null,
      "matching_included": true
    }
  ],
  "metrics_summary": {
    "total_valid_loc": 5000,
    "total_evidence_loc": 120,
    "top_languages": "…",
    "scanned_repos": 1,
    "total_commits_analyzed": 42
  },
  "warnings": [ … ]
}
```

#### v6.1 신규 필드

| 필드 | 의미 |
|---|---|
| `repo_type` | `"team"` / `"personal"` |
| `repo_author_names` | 표시용 작성자 리스트 (최대 10명) |
| `repo_active_weeks` | 레포 전체 커밋 기준 활성 주 |
| `total_repo_commits` | 레포 전체 커밋 수 (author 필터 없음) |
| `target_commit_count` | 지원자 본인 커밋 수 |
| `target_commit_ratio` | 지원자 / 레포 전체 비율 |

### `run_diagnosis()` 반환 (v6.1)

```json
{
  "per_repo_diagnoses": [
    {
      "repo_name": "...",
      "repo_type": "team",
      "distinct_author_count": 2,
      "repo_author_names": [...],
      "target_commit_count": 80,
      "total_repo_commits": 245,
      "target_commit_ratio": 0.3265,
      "is_fork": false,
      "context_label": "FastAPI / Spring Boot",
      "core_items": {
        "readme_quality": { "status": "양호", "detail": "...", "action": null },
        "project_structure": { ... },
        "commit_quality": { ... }
      },
      "extra_items": {
        "test_coverage": { "status": "양호" or "필수 미흡", ... },
        "cicd": { ... },
        "deployment": { ... },
        "commit_pattern": { "status": "규칙적/보통/불규칙", ... }
      }
    }
  ],
  "expected_level": { "level": "Competitive", "summary": "..." },
  "contribution_type": "...",
  "repo_classifications": [...],
  "summary_block": "[종합 분석] GitHub 점수 ... 강점 ... Quick Wins ..."
}
```

**중요:** v6.0의 `portfolio_diagnosis` 키는 v6.1에서 `per_repo_diagnoses`로 대체됨. 기존 호출자가 있다면 갱신 필요.

---

## 6. 버전 이력 및 주요 결정 사항

### v6.2 → v6.3 (2026.05.11)

UX 용어 정리 + 경력 필터 강화 + Quick Wins 게임 맥락 분기 + 캐시 버전 관리.

- **`experience_filter.py`**:
  - `CACHE_VERSION = 2` 상수 추가.
  - `load_or_build_cache()` — `__version__` 불일치 시 캐시 전체 재구축. 저장 시 `__version__` 기록.
  - `EXPERIENCE_PATTERNS` 보강 (7개):
    - `open_to_all`: `"신입 가능"` 추가.
    - `senior_only`: `"경력 개발자"`, `"경력직"`, `"experienced"` 추가.
    - `range_years`: `"경력"` prefix 제거 → `년` suffix만으로 구분.
    - `min_years_exp`: 영문 패턴 `(\d+)\+?\s*years?\s*(?:of\s+)?(?:experience|exp)?` 신규 추가.
  - `_self_test()` — 16개 → 25개 케이스 (v6.3 신규 9개 추가, 25/25 통과).
- **`portfolio_diagnosis.py`**:
  - `_QUICK_WINS_POOL` → `_QUICK_WINS_POOL_DEFAULT` / `_QUICK_WINS_POOL_GAME` 분리.
  - `_aggregate_quick_wins()` — `game_engines: Optional[Set[str]]` 파라미터 추가. 게임 감지 시 게임 맥락 풀 사용.
  - `generate_summary_block()` — `game_engines` 파라미터 추가. `_aggregate_quick_wins` 호출 시 전달.
  - `run_diagnosis()` — `_collect_game_engines(per_repo)` 호출 후 `generate_summary_block`에 전달.
  - 출력 용어 변경: `"기여도"` → `"개발 활동량"`, `"성숙도"` → `"프로젝트 운영도"`, `"일관성"` → `"작업 일관성"` (두 곳).
- **`run_git2value.py`**:
  - 버전 표기 `v6.3`.
- **`github_extractor.py`** (§7~§8 추가 적용):
  - `_BOT_LOGIN_PATTERN` 7종 → 22종 확장 — 배포/호스팅(Streamlit·Vercel·Netlify·Heroku·Railway), 의존성/보안(Snyk·Depfu·Greenkeeper·imgbot·allcontributors·Whitesource·Mend-bolt), 릴리스(semantic-release·release-drafter·changeset-bot) 봇 추가.
  - `_is_bot_author()` — 2차 체크 추가: `author.type == "Bot"` (패턴 목록 미등록 봇 자동 포착).
  - `evaluate_repository()` — `human_commit_count` 도입. `total_repo_commit_count = human_commit_count`로 변경 (봇 커밋 제외 → `target_commit_ratio` 정확화).
  - `_calc_fork_penalty()` — Fork 감점 면제 조건 추가: `contribution_ratio >= 0.8 AND target_commit_count >= 20` 시 계수 `1.0` 반환 (사실상 단독 저작 판정).
  - `_is_bot_author()` 버그픽스: 3차 이메일 체크에서 `users.noreply.github.com` 도메인의 봇 noreply(`{id}+{name}[bot]@users.noreply.github.com`)가 `return False`로 오통과되던 문제 수정 → `return "[bot]" in email`로 교체. 4차 체크 추가: raw git author name에 `[bot]` 포함 시 봇 판정 (GitHub `author` 객체 null 폴백).
  - **미연결 커밋 처리 (§8 결함 B)**: `evaluate_repository()` 루프에 `unlinked_count` 변수 추가. `author` 객체가 `null`인 커밋은 `human_commit_count`에는 포함하되 `repo_author_keys` 집계에서 제외. 미연결 커밋 3개 이상 시 `repo_warnings`에 경고 추가. — 서비스 자동 커밋(Streamlit push 등)의 email 기반 key가 `distinct_author_count`를 부풀려 개인 레포를 팀 레포로 오분류하던 결함 해소.
  - **`readme_raw` 필드 전달 (§9)**: `evaluate_repository()` 반환 dict에 `"readme_raw": readme_raw_text[:5000]` 추가. `extract_applicant_profile()` per_repo 구성에 `"readme_raw": res.get("readme_raw") or rm` 추가 (원본 없으면 정제본 폴백).
- **`portfolio_diagnosis.py`** (§9 추가 적용):
  - `_readme_diagnosis_single()` — `readme_text` 단일 변수에서 `readme_raw` + `readme_clean` 분리. `evaluate_readme_quality()` 인자를 `readme_clean` → `readme_raw`로 교체. 길이 판단(`n`)은 정제본 기준 유지. — `_clean_markdown` 이후 `##` 헤딩·이미지 마크다운이 제거된 텍스트로 평가해 거의 항상 "미흡"을 반환하던 문제 해소.

### v6.1 → v6.2 (2026.05.04)

v6.1 검증 중 발견된 필수 패치 1건 + 권장 보강 4건 + 정리 1건 (가) 계열,
+ 점수 공정성 피드백 4건 (나) 계열 통합 적용.

#### (가) 계열 — 코드 검증 후속 패치

- **`github_extractor.py`**:
  - `_BOT_LOGIN_PATTERN` / `_BOT_EMAIL_HINTS` 클래스 상수 추가.
  - `_is_bot_author()` 클래스 메서드 신규 — login/email 기반 봇 판별.
  - `evaluate_repository()` — `all_repo_commits` 순회 시 봇 작성자 제외, `distinct_author_count` 산출 정확도 확보. 봇 5개 이상 시 warning 추가.
- **`run_git2value.py`**:
  - `similarity_label()` — `score >= 0.65` 분기 추가로 "보통" 라벨 3단계 완전 복원 (0.65~0.75 구간).
  - `_print_repo_card()` — 개인 레포에서도 양호한 운영 항목을 "추가 강점 (참고)"으로 표시 (`_print_extra_one_liner` dead code 해소).
  - `_print_repo_card()` — 팀 레포 `commit_pattern` 아래 활동 기간 비율 표시 (`active_weeks` / `repo_active_weeks`).
  - 버전 표기 `v6.2`.
- **`portfolio_diagnosis.py`**:
  - `diagnose_single_repo()` 반환에 `active_weeks` / `repo_active_weeks` 필드 추가.
  - `expected_level()` — 팀 레포 0개 + 레포 2개 이상 시 Competitive 도달 불가 이유를 명시적 summary로 안내.
  - `generate_summary_block()` — Entry 등급에서 팀 레포 부재 시 포지셔닝 문구 강화("팀 프로젝트 경험 확보 권장").
- **`experience_filter.py`**:
  - `_self_test()` 함수 + `__main__` 블록 추가 — 16개 케이스 단위 테스트 (16/16 통과).

#### (나) 계열 — 점수 공정성 피드백

- **`github_extractor.py`**:
  - `_calc_fork_penalty()` 정적 메서드 신규 — 기여 비율 기반 3단계 패널티 (0.7 / 0.5 / 0.3).
  - `evaluate_repository()` — Fork 패널티 일괄 0.3배 → `_calc_fork_penalty()` 호출로 교체. 반환에 `fork_penalty` / `fork_penalty_log` 필드 추가.
  - `evaluate_repository()` — Quality 점수 개인/팀 분리: 팀은 기존(CI/CD 10 + 테스트 10 + 활성 주 10), 개인은 활성 주 중심(최대 20점) + CI/CD·테스트 가산점(각 5점). `score_breakdown`에 `quality_mode` 필드 추가.
  - `extract_applicant_profile()` — 총점 산출 방식 변경: LOC 가중 평균 → 대표 프로젝트(최고점) 70% + 전체 평균 30%. `per_repo` 각 항목에 `repo_total_score` / `score_breakdown` 필드 추가.
- **`portfolio_diagnosis.py`**:
  - `expected_level()` — 개인 레포 전용 "Competitive (개인)" 경로 추가 (core 3개 양호/보통 + 운영 항목 양호 2개 이상 + score >= 5).
  - `generate_summary_block()` — `per_repo_scores` 파라미터 추가, 레포별 점수 표시 블록 추가. `"Competitive (개인)"` 포지셔닝 문구 분기 추가.
  - `run_diagnosis()` — `per_repo`에서 레포별 점수 추출 후 `generate_summary_block()`에 전달.

### v6.0 → v6.1 (2026.05.04)

팀원 2차 개선안 반영 — 레포별 카드 진단 + 팀/개인 분리 + 출력 정교화.

- **`github_extractor.py`**:
  - `_commit_author_key()` / `_commit_author_label()` 신규 — login > email > name 우선순위.
  - `evaluate_repository()` — 레포 전체 커밋 별도 수집(`repo_commits_list_url`), `distinct_author_count`/`repo_type`/`target_commit_*`/`repo_active_weeks` 산출.
  - `extract_applicant_profile()` — `per_repo`에 v6.1 신규 필드 6종 노출.
- **`portfolio_diagnosis.py`**:
  - 진단 구조 전환: 통합 → **레포별 카드**.
  - `classify_repo_type()` 신규.
  - `diagnose_single_repo()` 신규 — core 3개 + extra 4개 항목.
  - `_team_required_items()` — 팀 레포 extra를 "필수 미흡"으로 격상.
  - `_commit_pattern_diagnosis_single()` — 지원자 본인 기준 커밋 리듬.
  - `expected_level()` 재구성 — 팀 레포 0개면 Competitive 이상 도달 불가.
  - `_aggregate_strengths()` / `_aggregate_quick_wins()` 신규 — 레포별 결과 집계.
  - `_portfolio_composition_lines()` 신규 — 레포 구성 요약.
  - `generate_summary_block()` 재구성 — GitHub 점수 분해 + 레포 구성 + 강점 + Quick wins.
  - `run_diagnosis()` 반환 키 `portfolio_diagnosis` → **`per_repo_diagnoses`**.
  - `_BAD_STATUSES` 확장: `없음`, `필수 미흡`, `확인 필요` 추가.
- **`run_git2value.py`**:
  - `MAX_REPO_COUNT = 3` 신규 — 입력 레포 최대 3개 제한.
  - `similarity_label()` 재설계 — 절대값 기준 도입(`max_s < 0.70` → "약함" 통일, `>= 0.85` → "강함"). spread 분포 + 평균 절대값 혼합 분기.
  - `analyze_tech_match()` 3단계 정교화 — `TECH_INCLUSION_MAP`/`DOMAIN_IRRELEVANT_TECHS`/`CATEGORY_TARGET_TECHS`.
  - `filter_techs_by_inclusion()` / `filter_techs_by_domain()` 신규.
  - 모듈 A 출력 — 레포별 카드 형식(`_print_repo_card`, `_print_diag_item`, `_print_extra_one_liner`).
  - `_print_applicant_summary()` — 4개 항목으로 단순화 (GitHub ID/경력/분석 레포/기술 스택, 비율 제거).
  - 모듈 C 출력 — `category_comparison` 의존 제거, 직무별 직접 `get_market_band()` 조회.
  - 출력 문구 정리: "이번 주 실행 가능한 개선" → "실행 가능한 개선", "다음 커밋부터 ..." → "...", 일부 noise 문구 제거.
  - 버전 표기 `v6.1`.
- **`experience_filter.py`**:
  - `EXPERIENCE_PATTERNS`에 `open_to_all` 패턴 추가 ("경력무관"·"신입/경력"·"신입 또는 경력" 등).
  - `extract_experience_requirement()` 반환에 `requirement_type` 필드 추가 (6분류).
  - `is_applicant_eligible()` 신규 — 0년차 기준 더 엄격 처리.
  - `split_by_experience()` 신규 — 적격/제외 분리 반환.
  - `filter_by_experience()` 하위 호환 래퍼로 전환.
  - `load_or_build_cache()` — 누락 항목 갱신 로직 (`requirement_type` 없으면 재추출).

### v5.8 → v6.0 (2026.05.02)

사용자(취준생) 관점 출력 품질 개선 + 다중 도메인 균형 추천.

- **`experience_filter.py`** (신규): 경력 요건 사이드카 캐시 + `filter_by_experience()`.
- **`run_git2value.py`**:
  - `route_job_category_safe()` — 콤마 포함 결과 방어.
  - FAISS k=5 → **20** 확장.
  - `recommend_multi_domain()` — 히트 비율 < 2배 시 도메인별 분리 추천.
  - `similarity_label()` → `tuple[str, str | None]` — spread < 0.02 시 `system_note`.
  - `diagnose_domain_mismatch()` — db_coverage/weak_signal/consistent/ambiguous 4분기.
  - `analyze_tech_match()` `detected_domains` 인자 추가.
  - 버전 표기 `v6.0`.
- **`portfolio_diagnosis.py`**:
  - 진단 항목 9→**7** (commit_pattern·growth_trajectory·collaboration 제거).
  - `README_QUALITY_INDICATORS` + `evaluate_readme_quality()` — 3차원 룰베이스.
  - `COMMIT_REWRITE_HINTS` + `get_rewrite_hint()` — 커밋 변환 힌트.
  - `repo_classification_note()` — 협업 항목 대체.
  - `generate_summary_block()` — 포지셔닝/강점/Quick wins 종합 분석.
- **`valuation_engine.py`**: `realistic_range` 추가 (±15%/+20% 추정 분포).
- **`vector/experience_cache.json`** (신규, 자동 생성).

### v5.7 → v5.8 (2026.04.27)

시그너처 오탐 강화 + 신규 환경 카테고리 8종.

- 새 시그너처 키 5종: `required_any_dirs`/`file_count_endswith`/`exclude_if_basename_exists`/`supporting_path_contains`/`manifest_signature_keywords`.
- `detect_signatures_with_content()` 비동기 manifest 검증.
- `ENGINE_SIGNATURES` 신규: Expo·React Native·Hardhat·Foundry·Helm Chart·dbt·VS Code 확장·Browser Extension.
- 강화: Flutter(android/ios 필수)·Jupyter/ML(.ipynb 3개)·Love2D(Solar2D 우선)·OpenResty(.lua 필수)·Minecraft(Bukkit 경로)·Stardew Valley(루트 한정)·Neovim(보조 시그너처).
- `DOMAIN_SIGNALS`에 블록체인·빅데이터 엔지니어·도구 개발 추가.

### v5.6 → v5.7 (2026.04.27)

모드 플랫폼 감지 + 설정 프로젝트 매칭 제외.

- `MOD_PLATFORM_SIGNATURES` + `detect_mod_platform()` (EDOPro 등 6종).
- `is_config_repo` → 매칭 입력 제외.
- `mod_context_message()` / `config_repo_message()`.

### v5.5 → v5.6 (2026.04.27)

언어 메인/서브 분류 + Lua 호스트 추론.

- `MAIN_LANGUAGES` / `SUB_LANGUAGE_SIGNALS` / `LUA_HOST_SIGNATURES`.
- `categorize_languages()` / `detect_lua_host()` / `resolve_sub_language_alone()`.
- `build_profile_text()` 메인/서브 분리 표기.

### v5.4 → v5.5 (2026.04.16)

협업 기여도 편향 해소 + 게임 진단 맥락.

- 커밋 수 동적 가중치(0.9/0.1·0.6/0.4·0.5/0.5).
- Evidence LOC + `loc_score_ev`.
- `expected_level` Competitive에서 테스트 제거, CI/CD 또는 배포 + 멀티 프로젝트.

### v5.3.6 → v5.4 (2026.04.13)

게임 엔진 시그너처 감지.

- `ENGINE_SIGNATURES` + `detect_engine_signatures()` (Unity/Unreal/Godot/Flutter).
- 테스트·CI/CD·배포 action을 게임 개발 맥락으로.

### v5.2 → v5.3 (2026.04.09)

도메인 기반 하이브리드 리랭킹.

- `rerank_by_domain()` — `DOMAIN_BOOST=0.05` 가산.
- v5.3.1: 다중 도메인 경합 시 리랭킹 억제.
- v5.3.2: README 키워드 영어/CV/NLP 보강.

### v5.0 → v5.1 (2026.04.06)

게임 카테고리 라우팅 + 키워드 압축.

- `route_job_category()` 게임 분기.
- README 키워드 사전 + `extract_readme_keywords()`.
- `check_domain_match_consistency()` / `similarity_label()` 신규.

### v4.0 → v5.0 (2026.04.06)

점수 수식 정교화.

- Contribution 로그 스케일.
- Quality 균등 배점 (10+10+10).
- Consistency 전체 author 커밋 기준.

### v3.0 → v4.0 (2026.04.06)

서비스 리프레이밍.

- 신입 개발자 포트폴리오 진단 + 취업 전략 리포트.
- 모듈 A/B/C 분리.
- 멀티플라이어 모델 제거.

---

## 7. 알려진 미해결 사항

### 해소됨 (✅)

1. ~~스펙 문서·구현 불일치~~ ✅ v3.0
2. ~~순차 레포 평가 성능~~ ✅ v3.0 병렬화
3. ~~run_git2value 연결 미완성~~ ✅ v3.0
4. ~~FAISS 입력 비대칭·공고 DB 불균형~~ ✅ v5.1 + v5.3 하이브리드 리랭킹
5. ~~연봉 멀티플라이어 근거 부족~~ ✅ v4.0
6. ~~Contribution 선형 만점·변별력 부족~~ ✅ v5.0
7. ~~Quality duration 편중·CI·테스트 무력화~~ ✅ v5.0
8. ~~게임 카테고리 라우팅 누락~~ ✅ v5.1
9. ~~FAISS 유사도 레이블 없음~~ ✅ v5.2 → v6.1 절대값 기준
10. ~~도메인 불일치 감지 없음~~ ✅ v5.1 + v6.0
11. ~~공통 기술 키워드 노이즈~~ ✅ v5.2 → v6.1 정교화
11b. ~~README/의존성 없을 때 엔진 미특정~~ ✅ v5.4
11c. ~~협업·데이터/설정 전담 기여도 과소~~ ✅ v5.5
11d. ~~Lua 등 서브 언어 단독 처리~~ ✅ v5.6
20. ~~모드/플러그인 플랫폼 감지~~ ✅ v5.7
21. ~~`is_config_repo` 매칭 입력 제외~~ ✅ v5.7
23. ~~시그너처 오탐 (7종)~~ ✅ v5.8
24. ~~모바일/블록체인/데이터/인프라/도구 미감지~~ ✅ v5.8
26. ~~경력직 공고 신입 상위 노출~~ ✅ v6.0 → v6.1 강화
27. ~~다중 도메인 프로젝트 균형 추천 없음~~ ✅ v6.0
28. ~~진단 항목 신뢰도 낮음~~ ✅ v6.0 7개 → v6.1 레포별 카드
29. ~~종합 행동 안내 없음~~ ✅ v6.0 → v6.1 GitHub 점수 분해 추가
33. ~~분석 레포 개수 제한 없음~~ ✅ v6.1 (`MAX_REPO_COUNT=3`)
34. ~~팀/개인 레포 판정 부정확~~ ✅ v6.1 (레포 전체 커밋 분리 수집)
35. ~~Fork 라벨이 개인/팀 판정과 섞임~~ ✅ v6.1 (별도 라벨 분리)
36. ~~커밋 리듬이 레포 전체 기준~~ ✅ v6.1 (지원자 본인 기준)
37. ~~매칭 직무와 참고 직무 혼동~~ ✅ v6.1
38. ~~참고 직무 연봉 누락 (프론트엔드 등)~~ ✅ v6.1 (직접 조회)
31. ~~봇 작성자 필터링~~ ✅ v6.2 (`_is_bot_author` + evaluate_repository 봇 제외)
32. ~~`similarity_label`에 "보통" 라벨 누락~~ ✅ v6.2 (`score >= 0.65` 분기 추가)
33. ~~`_print_extra_one_liner` dead code~~ ✅ v6.2 (개인 레포 양호 항목 표시에 활용)
34. ~~개인 레포만 있는 사용자 등급 안내 강화~~ ✅ v6.2 (`expected_level` + `generate_summary_block` 명시 안내)
37. ~~`repo_active_weeks` 사용처 정의~~ ✅ v6.2 (팀 레포 활동 기간 비율 표시에 활용)
39. ~~Fork 패널티 일괄 감산 불공정~~ ✅ v6.2 (기여 비율 기반 3단계: 0.7/0.5/0.3)
40. ~~총점 산출 LOC 가중 편중~~ ✅ v6.2 (대표 프로젝트 70% + 전체 평균 30%)
41. ~~Quality 점수 개인/팀 모순~~ ✅ v6.2 (개인 레포 활성 주 중심 + CI/CD·테스트 가산점)
42. ~~개인 레포 우수 사용자 등급 누락~~ ✅ v6.2 (`Competitive (개인)` 경로 추가)

### 남은 항목

12. **Consistency `0.5` 계수** — 임의값. 지수 감쇠 전환 검토.
13. **`migrations/` ignore** — Django 등에서 의도한 마이그레이션이 LOC에서 제외.
14. **`DOMAIN_BOOST`(0.05) 튜닝** — 데이터 기반 조정은 v7.
15. **유사도 레이블 정밀화** — 백분위 기반으로 개선 가능 (v6.2 0.65 분기는 단계적 진전).
16. **게임/정보보안 등 일부 직무** — 원티드 매핑 누락 시 점핏 단독.
17. **PR/이슈 협업 분석** — 추가 API 필요, 우선순위 낮음.
18. **공고 임베딩 재구성** — 직무명+요구기술만 추출 재임베딩.
19. **게임 포트폴리오 `expected_level` 웹 편향** — v5.4 피드백만 조정, 등급 산정 별도 검토.
22. **신규 도메인 매핑** — `HW/임베디드`/`DBA/데이터`/`그래픽스`는 `DOMAIN_TO_CATEGORIES` 미매핑.
25. **블록체인·도구 개발 공고 DB 매칭 품질** — 점핏 JD 코퍼스 보강 필요.
30. **차등 가산점 (시그너처 vs 휴리스틱)** — 정확도 측정 후 v7.
35. **리멤버 400개 데이터 처리 결정** — 신입 대상 피벗 후 분석 보류. 분석 스크립트 + 분포 확인 후 결정.
36. **LLM 도입 (로컬 Qwen2.5-32B-AWQ 등)** — README 평가의 룰베이스 한계 보완. v7 검토.

---

## 8. 의존성 주의사항

- `sentence-transformers==2.6.1` 버전 고정 필수
- `faiss-cpu==1.8.0` CPU 버전 유지
- `.env`에 `Github_api_token` 필요
- **외부 LLM API 의존 없음** — 분석·매칭·진단 전부 로컬 (설계 원칙)

---

## 9. 실행 방법

Windows 터미널에서 출력 시 `UnicodeEncodeError`가 나면 **`PYTHONUTF8=1`**(또는 `chcp 65001`)을 설정한 뒤 실행하세요.

### GitHub 추출기 단독 실행

```bash
python github_extractor.py
# target_username, target_repos를 __main__ 블록에서 수정
```

### E2E 데모 실행

```bash
python run_git2value.py
# vector/ 폴더에 FAISS 인덱스 필요
# data/jumpit_data/, data/wanted_data/salary_data/ (원티드 교차 시)
# TARGET_REPOS는 최대 3개까지 지정 (초과 시 앞 3개만 사용)
```

### 연봉 밴드 엔진 단독 테스트

```bash
python valuation_engine.py
```

---

## 10. 외부 문서 동기 갱신

v6.1 적용 시 다음 문서들도 함께 갱신해야 함:

| 문서 | 갱신 방향 |
|---|---|
| `Git2Value_Spec_v3.md` | Phase 7(모듈 B) 레포별 카드 진단 구조로 재작성, Phase 1-3 anti-cheating에 봇 필터링 한 줄 추가 |
| `Git2Value_논문_수정본.pdf` | 진단 구조 전환·팀/개인 분리 반영, 표 1 갱신 |
| 발표 슬라이드 | 큰 변경 없음 (v6.2는 안정성·완성도 마무리 작업) |

---

*Git2Value HandOff v6.3 — 2026.05.11*
