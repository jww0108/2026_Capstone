# Git2Value — 프로젝트 HandOff 문서

> 작성일: 2026.04.01 | 최종 갱신: 2026.05.02 | 현재 스펙 버전: v2.2 | 현재 구현 버전: **v6.0**

새 컨텍스트에서 이 프로젝트를 이어받을 경우 이 문서를 먼저 읽으세요.

### HandOff 갱신 규칙 (에이전트·협업)

- **MultiDomain 수정 체크리스트**(`multidomain_fix_checklist_*.plan.md` 등)로 작업할 때는 **체크리스트의 각 단계(Step)를 완료할 때마다** 이 `HandOff.md`를 갱신한다.
- 갱신 내용: 해당 단계에서 바뀐 파일·동작 요약, 버전/이력 섹션 반영, 알려진 과제 목록 정합.

---

## 1. 프로젝트 개요

**Git2Value**는 **신입(0~3년) 개발자**를 주 대상으로, GitHub 레포지토리와 채용 공고(JD) 벡터 매칭을 결합해 **포트폴리오 진단**, **직무 적합도(상위 공고 매칭)**, **시장 연봉 밴드(참고)**를 **서로 독립된 모듈**로 제공하는 파이프라인입니다.

v4.0부터는 GitHub 점수로 연봉을 곱하는 **멀티플라이어 모델을 제거**했습니다(근거 부족·신뢰도 리스크). 연봉은 점핏·원티드 데이터 기반 **직무별 시장 구간**만 제시합니다.

### 핵심 흐름

```
GitHub Username + 레포 URL 리스트
        ↓
GitHubExtractor (github_extractor.py)
  - API 수집 (커밋, 트리, README, 메타)
  - 의존성 파일(blob) 선택 조회 → 프레임워크 추출
  - 트리 경로 시그니처 기반 엔진 감지(Unity/Unreal/Godot/Flutter/Jupyter·ML/Kubernetes·IaC) + 의존성 결과 합산 (v5.4~v5.5)
  - 트리 경로 기반 도메인 시그널 감지
  - 균등 샘플링 + SHA dedup
  - 점수 산출 (contribution: v5.5 동적 가중치 + Evidence LOC / quality / consistency)
        ↓
github_score + score_breakdown + per_repo + profile_for_matching
        ↓
profile_builder.build_profile_text() — JD 문체에 가까운 매칭용 텍스트
        ↓
run_git2value.py (E2E 데모)
  - FAISS + 임베딩 → 상위 5개 공고 후보 → 도메인 기반 리랭킹 (모듈 A)
  - portfolio_diagnosis.run_diagnosis() → 체크리스트 (모듈 B)
  - Git2ValueEngine.get_market_band() → 신입~3년 시장 밴드 (모듈 C)
```

### 설계 원칙: 외부 API 의존 0

Git2Value는 **GitHub API**(데이터 수집)를 제외하면 외부 서비스 호출이 없습니다. ChatGPT, Claude 등 **외부 LLM API를 사용하지 않으며**, 전체 분석·매칭·진단 파이프라인이 로컬에서 동작합니다.

- 비용 0 (API 과금 없음)
- 네트워크 장애 시에도 정상 동작 (데모 안정성)
- 캡스톤 종합설계 취지에 부합 (자체 엔진 구축)

프로필 변환이 부족할 경우의 단계적 전환 경로: (1) 룰베이스 템플릿 (`build_profile_text`) → (2) 로컬 오픈소스 모델 → (3) 외부 API (최후 수단).

---

## 2. 파일 구조

```
basic/
├── github_extractor.py      # GitHubExtractor (수집·점수·per_repo 집계)
├── profile_builder.py       # 도메인·엔진 시그니처 감지, 의존성 파싱, build_profile_text()
├── portfolio_diagnosis.py   # 진단 룰베이스 (v6.0: 7개 항목, README 3차원, 종합 분석)
├── valuation_engine.py      # v4.0: get_market_band() + v6.0 realistic_range
├── experience_filter.py     # v6.0: 경력 요건 필터링 (사이드카 캐시)
├── run_git2value.py         # E2E: 모듈 A/B/C 통합 출력 (v6.0)
├── requirements.txt         # 의존성 (sentence-transformers==2.6.1 버전 고정 중요)
├── .env                     # Github_api_token 환경변수 (버전 관리 제외)
├── HandOff.md               # 이 파일
│
├── vector/
│   ├── git2value_faiss.index
│   ├── git2value_metadata.json
│   ├── experience_cache.json    # v6.0 자동 생성 (경력 필터 사이드카)
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
└── md/     (과거의 계획 파일, 필요할 때만 사용)
```

---

## 3. 핵심 파일별 역할

### `github_extractor.py` — GitHubExtractor 클래스

| 메서드                           | 역할                                                                                                                      |
| -------------------------------- | ------------------------------------------------------------------------------------------------------------------------- |
| `_fetch_with_retry`              | 모든 API 호출 게이트. 403/429 시 Retry-After 파싱 + 지수 백오프 (최대 3회)                                                |
| `_fetch_repo_text_files`         | **v4.0** 의존성 파일 등 contents API로 텍스트 조회                                                                        |
| `_fetch_all_commits_paginated`   | author 필터 커밋 목록 수집. `MAX_COMMIT_PAGES=3` (최대 300커밋) 상한                                                      |
| `_stratified_sample_commits`     | 초기/중간/최근 각 최대 25개씩, 레포 내부 + 전역 SHA dedup                                                                 |
| `_cicd_and_test_ratio_from_tree` | tree blob size>200B로 CI/CD 실질성 판별, 테스트 파일 비율 계산                                                            |
| `_count_active_weeks`            | **v5.0** author 커밋 목록 기준 ISO 주(년+주차) 개수                                                                       |
| `_calc_consistency_score`        | 커밋 간격 표준편차 → `max(0, 10 - std * 0.5)`. **v5.0** 전체 목록 기준                                                    |
| `evaluate_repository`            | 레포 1개 완전 분석. **`detect_engine_signatures` + `parse_dependency_contents` → frameworks**(dedup), detected_domains, tree_stats, active_weeks (**v5.4**). **v5.5**: `evidence_loc`, contribution 동적 가중치·Evidence LOC 보조 점수 |
| `_is_contribution_evidence` / `_analyze_sampled_commits` | **v5.5**: 커밋 파일별 `valid_loc` + **`evidence_loc`**(json/yml/md/Dockerfile 등 additions) 분리 집계 |
| `extract_applicant_profile`      | LOC 가중 github_score + **`profile_for_matching`** + **`domain_hits_merged`** + **`per_repo`**( **`evidence_loc`**, **`metrics_summary.total_evidence_loc`**) |

**클래스 상수:** `MAX_COMMIT_PAGES = 3`

**환경변수:** `Github_api_token`

---

### `profile_builder.py` — v5.8

- **`ENGINE_SIGNATURES` / `detect_engine_signatures(tree_data)`** (**v5.4**): GitHub 트리 경로만으로 Unity·Unreal Engine·Godot·Flutter 등을 감지 ([`Engine_Detection_Plan.md`](Engine_Detection_Plan.md)). blob·tree 항목 경로를 모두 스캔하며, `.meta` 등은 LOC `ignore_extensions`와 무관하게 존재 여부만 판별.
- **v5.5**: **`Jupyter/ML 실험`**, **`Kubernetes/IaC`** 시그니처 추가 ([`Contribution_Fairness_Plan.md`](Contribution_Fairness_Plan.md) §5).
- `detect_domain_hits` / `merge_domain_hits`: 트리 경로 기반 도메인 히트. **`detect_domain_hits`는 도메인별로 경로에 등장한 고유 키워드 종류 수**를 세며, **2종류 미만이면 해당 도메인을 제외**한다 (v5.3.1: 파일·경로 반복 매칭으로 인한 과대 카운트 방지).
- `find_dependency_paths` / `parse_dependency_contents`: package.json 등에서 프레임워크 라벨 추출
- `has_deployment_signals`: docker-compose, Vercel 등 배포 시그널
- `compute_tree_structure_stats`: 파일당 평균 LOC, `.gitignore` 여부
- `build_profile_text`: FAISS 질의용 공고형 문장 생성 — **v5.6** `language_category`/`sub_language_host` 기반 메인/서브 분리 출력. `top_languages` 키는 `language_category` 없을 때만 폴백. README 키워드/CI/테스트/배포 라인은 v5.3 정책 유지.
- `readme_length_tier`: README 잔량 분기 (long/medium/short)
- **`README_KEYWORDS`**: 도메인별 키워드 사전 (게임/웹/서버/ML·AI/모바일/인프라). v5.3.2에서 **`ML/AI`·`서버`·`인프라`** 키에 영어·운영 키워드 보강 (MultiDomain 체크리스트 Step 2).
- **`extract_readme_keywords(readme_text)`**: README에서 도메인 키워드 압축 문장 반환. 키워드 없으면 **추가하지 않음** (v5.3, 원문 폴백 없음)
- **`DOMAIN_CONTEXT`**: 참고용 템플릿 상수 (코드에 유지). **매칭용 `profile_for_matching`에는 삽입하지 않음** (v5.3)
- **v5.7 신규 상수·함수**:
  - **`MOD_PLATFORM_SIGNATURES`**: 모드/플러그인 플랫폼 시그너처 사전 6종 (EDOPro·Garry's Mod·Factorio·Minecraft·Stardew Valley·WoW 애드온). `regex_patterns`(정규식 파일명 매칭)·`required_dirs`·`required_files_basename`·`supporting_*`·`mod_context`·`is_hobby` 필드 지원.
  - **`_matches_mod_signature(sig, paths, basenames)`**: 모드 플랫폼 시그너처 매칭 헬퍼. 정규식 패턴(`min_pattern_count`) 포함.
  - **`detect_mod_platform(tree_data)`**: 모드/플러그인 플랫폼 감지. 첫 매칭 반환 `{"name", "domain", "label", "mod_context", "is_hobby"}`.
- **v5.6 신규 상수·함수**:
  - **`MAIN_LANGUAGES`**: 자체 직무 카테고리를 가지는 메인 언어 집합 (Python·Java·TypeScript 등 16종)
  - **`SUB_LANGUAGE_SIGNALS`**: 서브 언어 사전 (Lua/Shell/GLSL/HLSL/CSS/HTML/SQL 등 10종) — `alone_handler`(단독 처리 방식), `with_main_label`(메인과 결합 시 보조 라벨)
  - **`LUA_HOST_SIGNATURES`**: Lua 레포 호스트 환경 시그너처 9종 (Roblox/Love2D/Defold/Solar2D/Cocos2d-x/OpenResty/NodeMCU/Neovim 등) — `required_files_root`·`file_patterns_endswith`·`supporting_dirs` 등 다중 키 지원
  - **`DEFAULT_ALONE_DOMAINS`**: 서브 언어 단독 레포의 기본 도메인 매핑 (Shell→DevOps/인프라, GLSL→그래픽스 등)
  - **`categorize_languages(lang_stats)`**: LOC 통계에서 메인/서브/trivial 분류. 메인은 `MAIN_LANGUAGES` ∩ LOC ≥ 5%, 서브는 `SUB_LANGUAGE_SIGNALS` (비율 무관), 미지 언어 ≥ 5%도 메인 후보
  - **`_matches_lua_host_signature(sig, paths, basenames, root_files)`**: 단일 Lua 호스트 시그너처 매칭 헬퍼
  - **`detect_lua_host(tree_data)`**: Lua 호스트 환경 감지 — 첫 매칭 반환 `{"name", "domain", "label", "is_config"}`
  - **`resolve_sub_language_alone(lang, tree_data)`**: 서브 언어 단독 레포 처리 — Lua는 `detect_lua_host`, 나머지는 `DEFAULT_ALONE_DOMAINS`

#### README 활용 분기 로직 (`readme_length_tier` / `build_profile_text`)

정제된 README 문자열 기준 길이로 티어를 나누고, `build_profile_text`에는 **200자 이상(long)일 때만** `extract_readme_keywords()` 결과를 붙입니다.

| 잔량       | 티어   | `build_profile_text` 반영                      |
| ---------- | ------ | ---------------------------------------------- |
| 200자 이상 | long   | 키워드 추출 성공 시에만 압축 문장 추가         |
| 50~199자   | medium | README 본문 미반영 (구조·언어·의존성 데이터만) |
| 49자 이하  | short  | 동일                                           |

원칙: 부실 README는 프로필에 넣지 않는다. 키워드 추출 실패 시에도 **원문 폴백 없음** (v5.3).

---

### `portfolio_diagnosis.py` — v6.0

- `run_diagnosis(profile)`: **7개 항목** (v6.0: commit_pattern·growth_trajectory·collaboration 제거). 반환에 **`contribution_type`**, **`repo_classifications`**, **`summary_block`** (v6.0) 추가.
- **`evaluate_readme_quality(readme_text)`** (v6.0): 3차원 룰베이스 평가 (프로젝트 목적/기술 스택/결과물 시각화). 기존 길이 기반에 통합.
- **`COMMIT_REWRITE_HINTS` / `get_rewrite_hint(msg)`** (v6.0): 무의미 커밋 → Conventional Commits 변환 힌트.
- **`repo_classification_note(repo)`** (v6.0): 레포별 협업 여부 한 줄 요약 (협업 진단 항목 대체).
- **`generate_summary_block(diagnosis, level_dict, github_score, primary_domain)`** (v6.0): 포지셔닝/강점/Quick wins 종합 분석.
- **v5.7**: **`mod_context_message(mod_platform)`** — 모드 개발 프로젝트 안내 (`is_hobby` 분기). **`config_repo_message(host_name)`** — 설정/취미 프로젝트 안내. **`_build_repo_classifications(per_repo)`** — 레포별 분류(`main`/`mod`/`config`)·안내 메시지·`matching_included` 리스트 생성. `run_diagnosis()` 반환에 `repo_classifications` 추가.
- **`_collect_game_engines`** (**v5.4**): `per_repo[].frameworks`에서 Unity / Unreal Engine / Godot를 수집. 테스트·CI/CD·배포 항목이 **미흡/미경험**일 때 **엔진별 action 문구**로 대체 (웹 일반 문구 편향 완화, [`Engine_Detection_Plan.md`](Engine_Detection_Plan.md) §5).
- **`MEANINGLESS_COMMIT_PATTERNS`** (v5.3.3): Conventional Commits(`fix:`, `chore:` 등 콜론 뒤 설명)은 무의미로 보지 않음. 단독 키워드·`initial commit`만 엄격히 필터.
- **`expected_level` (v5.5)**: **Competitive** = README 양호/보통 + **(CI/CD 또는 배포)** + **멀티 프로젝트** + 체크 `s≥4` (테스트 조건 제거). **Top** = 기존과 동일(테스트+CI/CD+배포+멀티+`s≥6`).
- **`_test_diagnosis` (v5.5)**: 테스트 미감지 시 상태 **`선택 가점`**, Top 차별화 문구로 완화 ([`Contribution_Fairness_Plan.md`](Contribution_Fairness_Plan.md) §4).

---

### `valuation_engine.py` — Git2ValueEngine (v4.0)

- `data/jumpit_data/korean_it_salary_lookup_2025.py` 동적 로드
- **`get_market_band(job_category, years_max=3)`**: 신입(0~3년) 구간, 점핏 junior P50 + 원티드 JSON(매핑 시) 교차 → `combined_range` 문자열
- **`calculate_valuation` 제거** (멀티플라이어·추천 연봉 단일값·가짜 백분위 제거)
- `JUMPIT_TO_WANTED_FILE`: 점핏 직무명 → `data/wanted_data/salary_data/*.json`

---

### `experience_filter.py` — 경력 필터 모듈 (v6.0 신규)

- `extract_experience_requirement(position, text)`: 공고 제목+본문에서 경력 요건 정규식 추출
- `load_or_build_cache(metadata, cache_path)`: 사이드카 캐시(`vector/experience_cache.json`) 로드/빌드
- `filter_by_experience(top_matches, applicant_years, cache)`: 신입 기준 경력직 후순위 처리 (완전 제외 아님)

---

### `run_git2value.py` — E2E 파이프라인 (v6.0)

- FAISS 인덱스(`vector/`) + `jhgan/ko-sroberta-multitask`
- 임베딩 입력: **`profile_for_matching`** (없으면 `applicant_resume` 폴백)
- **FAISS k=20** (v6.0): 다중 도메인 균형 추천 + 경력 필터 여유분 확보
- **경력 필터 (v6.0)**: `experience_filter.filter_by_experience()` — 신입 기준 경력직 후순위 표시
- **다중 도메인 균형 추천 (v6.0)**: `recommend_multi_domain()` — 히트 비율 < 2배이면 도메인별 상위 1~2개씩 분리 출력
- **단일 도메인**: 기존 +0.05 가산점 + 상위 5개 출력 (변경 없음)
- **`route_job_category_safe()`** (v6.0): 콤마/슬래시 포함 결과 방어 래퍼
- **`similarity_label()`** (v6.0): `tuple[str, str | None]` — spread < 0.02 시 `system_note` 포함
- **`diagnose_domain_mismatch()`** (v6.0): db_coverage/weak_signal/consistent/ambiguous 4분기 원인 분류
- **`analyze_tech_match()`** (v6.0): `detected_domains` 추가 — 도메인 일치 공고만 미보유 기술 추출
- **`CATEGORY_TO_DOMAINS`** (v6.0): `DOMAIN_TO_CATEGORIES` 역매핑 (한 번 생성)
- **`find_adjacent_categories()` / `categorize_salary_comparison()`** (v6.0): 연봉 3그룹화
- **모듈 A 출력**: FAISS 유사도 + 경력 경고 표시 + 도메인 원인 분기 + 기술 매칭 분석
- **모듈 B (v6.0)**: 7개 항목 + `summary_block` 종합 분석 (포지셔닝/강점/Quick wins)
- **모듈 C (v6.0)**: realistic_range(±15%/+20%) + 내 직무/인접 직무/연봉 상위 3그룹화
- 버전 표기 `v6.0`

---

## 4. 점수 산출 수식 (github_score, 진단 참고용) — **v5.0 + v5.5 (Contribution)**

상세 근거: [`Scoring_Review.md`](Scoring_Review.md)

### Contribution (최대 60점)

로그 스케일로 변별력 확보 (선형 만점 LOC·커밋 제거). **v5.5**에서 Evidence LOC 보조·커밋 수 동적 가중치 추가 ([`Contribution_Fairness_Plan.md`](Contribution_Fairness_Plan.md)).

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

**CI/CD 10 + 테스트 10 + 활성 주 10** — `min(30)` 캡 제거, duration 일수 대신 **활성 ISO 주** 사용.

| 항목        | 조건                                             | 점수                         |
| ----------- | ------------------------------------------------ | ---------------------------- |
| CI/CD       | 워크플로우/Dockerfile blob > 200B                | 10 또는 0                    |
| 테스트 비율 | &lt; 5%                                          | 0 / 5~20% → 5 / ≥20% → 10    |
| 활성 주 수  | `all_author_commits`에서 커밋이 있는 ISO 주 개수 | ≥8주 → 10, ≥4주 → 5, 그 외 0 |

### Consistency (최대 10점)

```python
max(0.0, 10.0 - std * 0.5)   # std = 연속 커밋 간격(일)의 모표준편차
# 커밋 수 < 5개: 0점
```

- **v5.0:** 타임스탬프 소스는 균등 샘플이 아니라 **전체 author 커밋 목록**(페이지네이션 상한 내), 샘플링 인위 갭 완화.

### 전체 github_score 집계

LOC 가중 평균 (기존과 동일). **연봉 모듈 C에는 github_score를 사용하지 않음.**

### 기타 (v5.0)

- `ignore_paths`에 `__pycache__/`, `generated/`, `obj/`, `bin/`, `.next/`, `migrations/` 등 추가 (자동 생성·산출물 LOC 왜곡 완화).

### 기타 (v5.5)

- `ignore_extensions`에 `.tf`, `.hcl`, `.proto`, `.sql` 추가 — 유효 소스 LOC 대신 커밋 기반 **`evidence_loc`**로만 집계.

---

## 5. 출력 JSON 스키마 (v4.0 `extract_applicant_profile` 확장)

### 추가·변경 필드

```json
{
  "github_score": 79.3,
  "score_breakdown": { "contribution": 42.0, "quality": 28.0, "consistency": 9.3 },
  "applicant_resume": "주요 기술 스택: … (레거시 미리보기용)",
  "profile_for_matching": "Python (90%) 기반 서버/백엔드 경험. FastAPI 활용 경험. 셸 스크립팅 활용. …",
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
      "valid_loc": 5000,
      "evidence_loc": 120,
      "is_fork": false,
      "duration_days": 90,
      "active_weeks": 12,
      "total_commits": 80,
      "frameworks": ["FastAPI"],
      "detected_domains": ["서버/백엔드"],
      "language_category": { "main": [["Python", 90.0]], "sub": [["Shell", 10.0]], "trivial": [] },
      "sub_language_host": null,
      "is_config_repo": false
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

- **`language_category`** (v5.6): 레포별 언어 분류 결과 `{"main": [(lang, pct)], "sub": [...], "trivial": [...]}`. `categorize_languages()` 출력 그대로.
- **`sub_language_host`** (v5.6): Lua 등 서브 언어 단독 레포의 호스트 환경 추론 결과 `{"name", "domain", "label", "is_config"}`. 감지 실패 시 `null`.
- **`is_config_repo`** (v5.6): `sub_language_host.is_config == True`이면 `true`. Neovim 설정 레포 등.
- **`mod_platform`** (v5.7): 모드/플러그인 플랫폼 감지 결과 `{"name", "domain", "label", "mod_context", "is_hobby"}`. 감지 실패 시 `null`.
- **`matching_included`** (v5.7): `is_config_repo=True`인 레포는 `false`. 직무 매칭 입력에 포함 여부.

---

## 6. 버전 이력 및 주요 결정 사항

### v5.8 → v6.0 (2026.05.02)

사용자(취준생) 관점 출력 품질 개선 + 다중 도메인 균형 추천.

- **`experience_filter.py`** (신규): 경력 요건 사이드카 캐시 + `filter_by_experience()` — 신입 기준 경력직 후순위 표시 (A-2).
- **`run_git2value.py`**:
  - `route_job_category_safe()` 추가 — 콤마 포함 결과 방어 (A-4).
  - FAISS k=5 → **20** 확장.
  - `recommend_multi_domain()` 추가 — 히트 비율 < 2배 시 도메인별 1~2개 분리 추천 (A-3 신규 기능).
  - `similarity_label()` → `tuple[str, str | None]` — spread < 0.02 시 `system_note` (A-1).
  - `diagnose_domain_mismatch()` 추가 — db_coverage/weak_signal/consistent/ambiguous 4분기 (A-3).
  - `analyze_tech_match()` `detected_domains` 인자 추가 → 도메인 일치 공고 기준 미보유 기술 (A-5).
  - `CATEGORY_TO_DOMAINS` + `find_adjacent_categories()` + `categorize_salary_comparison()` 추가 (C-3).
  - 모듈 C: `realistic_range` 표시 + 3그룹 비교 (C-1/C-2/C-3).
  - 버전 표기 `v6.0`.
- **`portfolio_diagnosis.py`**:
  - 진단 항목 9→**7** (commit_pattern·growth_trajectory·collaboration 제거) (B-7/8/9).
  - `README_QUALITY_INDICATORS` + `evaluate_readme_quality()` — 3차원 룰베이스 (B-4).
  - `COMMIT_REWRITE_HINTS` + `get_rewrite_hint()` — 커밋 변환 힌트 (B-5).
  - `repo_classification_note()` — 협업 항목 대체 (B-8).
  - `generate_summary_block()` + `run_diagnosis()` 반환에 `summary_block` 추가 (B-총합).
- **`valuation_engine.py`**: `get_market_band()` 반환에 `realistic_range` 추가 (C-1).
- **`vector/experience_cache.json`** (신규, 자동 생성): 경력 필터 사이드카 캐시.

### v5.7 → v5.8 (2026.04.27)

- **`profile_builder.py`**: 시그너처 오탐 강화 ([`Signature_Audit_Plan.md`](Signature_Audit_Plan.md)) + 신규 환경 카테고리 확장 ([`Environment_Expansion_Plan.md`](Environment_Expansion_Plan.md)).
  - **새 키**: `required_any_dirs`(OR 조건 디렉토리) / `file_count_endswith`(확장자별 최소 파일 수) / `exclude_if_basename_exists`(부정 조건) / `supporting_path_contains`(경로 부분 문자열 보조) / `required_files_root`(`_matches_mod_signature` 신규).
  - **`detect_engine_signatures()`**: `required_any_dirs`·`file_count_endswith` 처리 추가. **v5.8 확장**: `required_files_root`·`exclude_if_basename_exists`·`supporting_files_endswith` 처리 추가. `manifest_signature_keywords` 있는 항목은 건너뜀(비동기 처리).
  - **`detect_signatures_with_content()`** (신규 비동기 함수): `manifest_signature_keywords`가 있는 ENGINE_SIGNATURES 항목을 비동기로 검증. Expo(`app.json`의 `"expo"` 키), VS Code 확장(`package.json`의 `vscode`·`contributes`), Browser Extension(`manifest.json`의 `manifest_version`·`permissions`) 내용 fetch 후 키워드 매칭.
  - **`_matches_lua_host_signature()`**: `exclude_if_basename_exists` 처리 추가.
  - **`_matches_mod_signature()`**: `required_files_root`·`exclude_if_basename_exists`·`supporting_path_contains` 처리 추가. `detect_mod_platform()`에서 `root_files` 계산 후 전달.
  - **`ENGINE_SIGNATURES`**: Flutter — `required_any_dirs: ["android/", "ios/"]`로 순수 Dart 라이브러리 오탐 차단. Jupyter/ML — `file_count_endswith: {".ipynb": 3}`으로 README 시각화용 노트북 1~2개 오탐 차단. **v5.8 신규 8개 카테고리**: Expo·React Native(모바일), Hardhat·Foundry(블록체인), Helm Chart(인프라), dbt(데이터 엔지니어링), VS Code 확장·Browser Extension(도구 개발).
  - **`LUA_HOST_SIGNATURES`**: Solar2D/Corona를 Love2D **앞**으로 이동(사전 순서 조정). Love2D — `exclude_if_basename_exists: ["build.settings"]` 추가. OpenResty — `min_supporting: 0 → 1` + `.lua` 파일 보조 조건 추가(일반 Nginx 설정 오탐 차단). Neovim — `min_supporting: 1 → 2`, `plugin/`·`after/` 보조 디렉토리 및 `lazy-lock.json`·`packer_compiled.lua` 보조 파일 추가.
  - **`MOD_PLATFORM_SIGNATURES`**: Stardew Valley — `required_files_basename → required_files_root` 변경(Unity `Packages/manifest.json` 오탐 해소). Minecraft 플러그인 — `supporting_path_contains: ["org/bukkit/", "io/papermc/", "net/md_5/bungee/"]` + `min_supporting: 0 → 1`(Jenkins 플러그인 오탐 차단).
  - **`DOMAIN_SIGNALS`**: `블록체인`·`빅데이터 엔지니어`·`도구 개발` 3개 도메인 추가.
  - **`DOMAIN_CONTEXT`**: 신규 3개 도메인 템플릿 추가.
  - **`README_KEYWORDS`**: `블록체인`·`데이터`·`도구개발` 키워드 섹션 추가.
  - **`_parse_package_json()`**: `react-native`, `@expo/cli`, `expo`, `hardhat`, `@nomicfoundation/hardhat-toolbox`, `discord.js`, `telegraf`, `@vscode/vsce` 라벨 추가.
  - **`_parse_requirements_txt()`**: `streamlit`, `gradio`, `apache-airflow`, `dbt-core`, `discord.py`, `python-telegram-bot`, `transformers` 라벨 추가.
- **`github_extractor.py`**: **`evaluate_repository()`** — `detect_engine_signatures()` 직후 `detect_signatures_with_content()` 비동기 호출 추가, 결과를 `engine_detected`에 병합. 엔진 시그너처 `domain` 필드 기반으로 `detected_domains`에도 자동 삽입.
- **`run_git2value.py`**: **`DOMAIN_TO_CATEGORIES`** — `블록체인`, `빅데이터 엔지니어`, `도구 개발` 3개 매핑 추가. **`route_job_category()`** — `expo` 크로스플랫폼 앱 분류 추가.
- **`portfolio_diagnosis.py`**: **`blockchain_context_message()`**·**`data_engineer_context_message()`**·**`tool_dev_context_message()`** 신규 메시지 함수 추가. **`_build_repo_classifications()`** — 신규 도메인 감지 시 해당 맥락 메시지 자동 출력.

### v5.6 → v5.7 (2026.04.27)

- **`profile_builder.py`**: **`MOD_PLATFORM_SIGNATURES`** 사전 추가(EDOPro·Garry's Mod·Factorio·Minecraft 플러그인·Stardew Valley·WoW 애드온 6종). **`_matches_mod_signature()`** — 정규식 파일명 패턴(`regex_patterns`/`min_pattern_count`) + 기존 `required_dirs`/`required_files_basename`/`supporting_*` 통합 매칭. **`detect_mod_platform(tree_data)`** — 첫 매칭 반환 `{"name", "domain", "label", "mod_context", "is_hobby"}`. ([`Mod_Platform_Plan.md`](Mod_Platform_Plan.md))
- **`github_extractor.py`**: **`evaluate_repository()`** — 엔진 감지 직후 `detect_mod_platform()` 호출. 모드 label을 `frameworks` 앞에 삽입, 모드 domain을 `detected_domains` 앞에 삽입(미포함 시). 모드 플랫폼 감지 시 Lua 호스트 추론 건너뜀. 반환에 `mod_platform` 필드 추가. **`extract_applicant_profile()`** — `is_config_repo=True` 레포를 `non_config_results`로 분리, `matching_results` 기반으로 `build_profile_text()` 호출. 모두 설정인 경우 `warnings`에 신뢰도 경고. `per_repo`에 `mod_platform`·`matching_included` 필드 추가. ([`Mod_Platform_Plan.md`](Mod_Platform_Plan.md) §4)
- **`portfolio_diagnosis.py`**: **`mod_context_message()`**·**`config_repo_message()`** — 모드/설정 프로젝트 안내 메시지 함수. **`_build_repo_classifications()`** — 레포별 분류(main/mod/config)·안내 메시지 리스트 생성. `run_diagnosis()` 반환에 **`repo_classifications`** 추가.
- **`run_git2value.py`**: 버전 표기 `v5.7` 갱신. `[지원자 요약]`에 매칭 사용/제외 레포 수 및 레포별 분류 표시. 모드·설정 레포가 있으면 `[프로젝트 분류 안내]` 블록 출력(모듈 A 직전).

### v5.5 → v5.6 (2026.04.27)

- **`profile_builder.py`**: **`MAIN_LANGUAGES`**(16종)·**`SUB_LANGUAGE_SIGNALS`**(10종)·**`LUA_HOST_SIGNATURES`**(9종)·**`DEFAULT_ALONE_DOMAINS`** 사전 추가. **`categorize_languages()`** — LOC 통계에서 메인/서브/trivial 분리. **`detect_lua_host()`** + **`_matches_lua_host_signature()`** — Roblox/Love2D/Defold/Solar2D/Cocos2d-x/OpenResty/NodeMCU/Neovim 등 트리 시그너처 기반 Lua 호스트 감지. **`resolve_sub_language_alone()`** — Lua 이외 서브 언어 단독 레포 기본 도메인 처리. **`build_profile_text()`** 재구성 — `language_category`/`sub_language_host` 기반 메인/서브 분리 표기, 기존 README/CI/테스트/배포 정책 유지. ([`Language_Categorization_Plan.md`](Language_Categorization_Plan.md))
- **`github_extractor.py`**: **`evaluate_repository()`** — `categorize_languages()` + Lua 호스트 추론 호출, 반환에 `language_category`·`sub_language_host`·`is_config_repo` 추가. **`extract_applicant_profile()`** — 전체 `global_languages` 재분류로 `merged_lang_category` 산출, `first_sub_host.domain`을 `merged_domains` 앞에 insert+dedup, `build_profile_text` 호출 dict에 신규 필드 전달, `per_repo[i]`에 `language_category`·`sub_language_host`·`is_config_repo` 노출.
- **의도된 결정**: `run_git2value.py`의 `DOMAIN_TO_CATEGORIES` 미수정 — 신규 도메인(`HW/임베디드`·`DBA/데이터`·`그래픽스`)은 "매핑 없음" fallback (FAISS 순서 유지). v5.7에서 `is_config_repo` 매칭 제외 처리 예정.

### v5.4 → v5.5 (2026.04.16)

- **`github_extractor.py`**: 커밋 수 기반 **동적 가중치**(LOC/commit 0.9/0.1 · 0.6/0.4 · 0.5/0.5) — [`Contribution_Fairness_Plan.md`](Contribution_Fairness_Plan.md) §3-1. **`evidence_loc`**(CONTRIBUTION_EVIDENCE_EXTENSIONS + Dockerfile) 및 **loc_score_ev**(최대 50 스케일)로 설정·데이터 기여 보정 — §3-2~3-3. `per_repo`·`metrics_summary.total_evidence_loc`.
- **`portfolio_diagnosis.py`**: **`contribution_type_note()`**, `run_diagnosis` 반환 **`contribution_type`**. **`expected_level`**: Competitive에서 테스트 제거, **CI/CD 또는 배포 + 멀티 프로젝트** — §4. **`_test_diagnosis`**: 테스트 없음 → **`선택 가점`** — §4-3.
- **`profile_builder.py`**: **`ENGINE_SIGNATURES`**에 **Jupyter/ML 실험**, **Kubernetes/IaC** — §5.
- **`run_git2value.py`**: 지원자 요약에 **`total_evidence_loc`**, 모듈 B에 기여 유형 안내 출력.

### v5.3.6 → v5.4 (2026.04.13)

- **`profile_builder.py`**: **`ENGINE_SIGNATURES`**, **`detect_engine_signatures()`**, **`_tree_all_paths_lower()`** — 트리 구조 기반 엔진/프레임워크 감지 ([`Engine_Detection_Plan.md`](Engine_Detection_Plan.md)).
- **`github_extractor.py`**: `evaluate_repository()`에서 엔진 감지 결과를 의존성 파싱 결과 앞에 합쳐 `frameworks`에 반영 (중복 제거).
- **`portfolio_diagnosis.py`**: Unity·Unreal·Godot가 `frameworks`에 있을 때 테스트/CI/CD/배포 **action**을 게임 개발 맥락으로 조정.

### v5.3.5 → v5.3.6 (2026.04.09)

- **`run_git2value.py`**: `route_job_category()` — **`풀스택`/`fullstack`** 및 **프론트+백엔드 키워드 동시 포함** 공고를 백엔드/프론트 단독 규칙보다 우선해 **`웹 풀스택`**으로 분류 (MultiDomain 체크리스트 Step 9).

### v5.3.4 → v5.3.5 (2026.04.09)

- **`run_git2value.py`**: **`rerank_by_domain()`** — `domain_hits` 인자, **`tuple[list[dict], str]`** 반환. `profile["domain_hits_merged"]` 기준 **다중 도메인 경합(1위 히트 < 2위 히트×2)** 시 리랭킹 억제. 모듈 A 하단은 **`rerank_note`** 출력. `domain_rerank_footer_note()` 제거 (MultiDomain 체크리스트 Step 5·**Step 6** 출력 정합 — Step 6 별도 코드 변경 없음).
- **회귀 (Step 7)**: `siheon012/Deepsentinel` E2E — 다중 도메인·**혼합 프로젝트·리랭킹 미적용** 메시지·README 키워드(ai, detection, cctv, video analysis 등) 프로필 반영 확인.
- **회귀 (Step 8)**: `tekyung/Ttakji_lab-mobile_development_dep/tree/M1_milestone`(Unity TCG) E2E — 1순위 도메인 **게임 개발**·`rerank_note`에 **가산 후 재정렬** 적용·1순위 공고 **게임 개발자** 유지([`Domain_Reranking_Plan.md`](Domain_Reranking_Plan.md) §6 예시와 동일 스코어 순서).

### v5.3.3 → v5.3.4 (2026.04.09)

- **`github_extractor.py`**: `extract_applicant_profile()` 반환에 **`domain_hits_merged`** 추가 — 분석 레포들의 `domain_hits`를 도메인 키별로 합산한 딕셔너리 (MultiDomain 체크리스트 Step 4, 이후 `rerank_by_domain` 등에서 사용).

### v5.3.2 → v5.3.3 (2026.04.09)

- **`portfolio_diagnosis.py`**: `MEANINGLESS_COMMIT_PATTERNS` — `fix:`/`chore:` 형식의 Conventional Commits 오탐 제거 (MultiDomain 체크리스트 Step 3).

### v5.3.1 → v5.3.2 (2026.04.09)

- **`profile_builder.py`**: `README_KEYWORDS` — `ML/AI`, `서버`, `인프라` 항목에 영어·CV/NLP·클라우드·DevOps 관련 키워드 추가 (README 압축 문장 품질·도메인 시그널 보강).

### v5.3 → v5.3.1 (2026.04.09)

- **`profile_builder.py`**: `detect_domain_hits()` — 트리 경로에서 **키워드 매칭 횟수(파일×키워드 누적)** 대신 **고유 키워드 종류 수**로 도메인 점수를 산출. 임계 `>= 2`는 유지.
- **`HandOff.md`**: 단계별 체크리스트 작업 시 Step마다 본 문서 갱신 규칙 명시.

### v5.2 → v5.3 (2026.04.09)

- **`profile_builder.py`**: `build_profile_text()`에서 v5.2 **LOC 규모·`DOMAIN_CONTEXT` 맥락 문장·README 원문 300자 폴백 제거**. 매칭용 프로필은 v5.1에 가깝게 유지 (공고 DB 불균형은 리랭킹으로 처리).
- **`run_git2value.py`**: **`rerank_by_domain()`** — FAISS 상위 5개에 대해 도메인 감지와 `route_job_category` 결과가 일치하면 **`DOMAIN_BOOST`(0.05)** 가산 후 `effective_score`로 재정렬. 모듈 A에 FAISS/유효 점수·가산 여부 투명 출력 (당시 하단 설명은 후속 **`rerank_note`** 로 통합, v5.3.5).
- **`HandOff.md`**: 외부 LLM API 비사용 원칙, README 분기 로직 표기.

### v5.1 → v5.2 (2026.04.09)

- **`profile_builder.py`**: `DOMAIN_CONTEXT` 상수 추가. `build_profile_text()`에 **프로젝트 규모 문장**(LOC > 5000 / 레포 ≥ 2) 및 **도메인 맥락 문장 템플릿** 추가. README 키워드 압축 후 프로필이 ~60자로 줄어 유사도 상한이 낮아지던 문제를 해소 (목표 150~200자).
- **`github_extractor.py`**: `build_profile_text()` 호출 dict에 `total_valid_loc` · `scanned_repos` 추가 전달.
- **`run_git2value.py`**: `similarity_label()`을 절대값 임계치 → **상위 5개 유사도 기준 상대 방식**으로 교체. `analyze_top_matches_pattern()` → **`analyze_tech_match()`** 교체 (지원자 보유 기술 vs 공고 요구 기술 교차 분석, 보유/미보유 분리 출력).

### v5.0 → v5.1 (2026.04.06)

- **`profile_builder.py`**: `README_KEYWORDS` 사전 + `extract_readme_keywords()` 추가. `build_profile_text()`가 README 원문 500자를 그대로 붙이던 방식을 **도메인 키워드 압축 문장**으로 교체 (키워드 없을 때 원문 300자 폴백). Unity TCG 게임 레포가 프론트엔드 공고로 오매칭되던 실증 버그 수정.
- **`run_git2value.py`**: `route_job_category()`에 **게임 클라이언트 / 게임 서버** 분기 추가 (기존 서버/백엔드 규칙보다 앞에 위치). `check_domain_match_consistency()` · `similarity_label()` 신규 함수 추가. 모듈 A에 유사도 레이블(높음/보통/낮음) 및 도메인 불일치 경고 출력. 모듈 C에 도메인 기반 보조 연봉 밴드 출력.

### v4.0 → v5.0 (2026.04.06)

- **Contribution**: 선형 만점(LOC 1500·커밋 50) → **로그 스케일** ([`Scoring_Review.md`](Scoring_Review.md) 반영)
- **Quality**: duration 일수 30점 편중 해소 → **CI/CD 10 + 테스트 10 + 활성 ISO 주 10**, 캡 제거
- **Consistency**: 샘플 커밋 → **`all_author_commits` 전체** 기준으로 간격 std 계산
- **`portfolio_diagnosis`**: `commit_pattern`(커밋 리듬) 항목 추가
- **`ignore_paths`**: 자동 생성·빌드 산출 경로 확장

### v3.0 → v4.0 (2026.04.06)

- **서비스 리프레이밍**: 신입 개발자 포트폴리오 진단 + 취업 전략 리포트 중심
- **`profile_builder.py`**: 임베딩 비대칭 완화를 위한 룰베이스 프로필 문장
- **`portfolio_diagnosis.py`**: 3축 점수를 사용자 친화 체크리스트로 재구성
- **`valuation_engine.py`**: `get_market_band()` 도입, GitHub 점수 기반 연봉 보정 **삭제**
- **`github_extractor.py`**: 의존성 파일 조회, 도메인 감지, `per_repo`·`profile_for_matching` 공급
- **`run_git2value.py`**: 모듈 A/B/C 분리 출력, 상위 5개 공고 패턴 요약

### v3.0 이전 요약

- v3.0: `run_git2value` E2E 연결, 레포 간 병렬 평가(`asyncio.Lock`), 스펙 v2.2 정합
- v2.x: contribution/quality/consistency, SHA dedup, fork 시 contribution만 패널티 등

---

## 7. 알려진 미해결 사항 (v5.5 이후 과제)

1. ~~**스펙 문서와 구현 불일치**~~ ✅ v3.0~v2.2에서 정합
2. ~~**순차 레포 평가 성능**~~ ✅ v3.0 병렬화
3. ~~**run_git2value 연결 미완성**~~ ✅ v3.0
4. ~~**FAISS 입력 비대칭·공고 DB 불균형**~~ ✅ v5.1 키워드 압축 → ✅ v5.3 **도메인 하이브리드 리랭킹** (`Domain_Reranking_Plan.md`)
5. ~~**연봉 멀티플라이어 근거 부족**~~ ✅ v4.0 밴드 독립 제공
6. ~~**Contribution 선형 만점·변별력 부족**~~ ✅ v5.0 로그 스케일로 완화
7. ~~**Quality duration 편중·CI·테스트 무력화**~~ ✅ v5.0 균등 10+10+10·활성 주
8. ~~**게임 카테고리 라우팅 누락**~~ ✅ v5.1 게임 클라이언트/서버 분기 추가
9. ~~**FAISS 유사도 레이블 없음**~~ ✅ v5.2 상대적 간이 방식 (v5.3은 유효 점수 기준)
10. ~~**도메인 불일치 감지 없음**~~ ✅ v5.1 `check_domain_match_consistency()` + 경고 출력
11. ~~**공통 기술 키워드가 지원자와 무관**~~ ✅ v5.2 `analyze_tech_match()` 보유/미보유 교차 분석으로 교체
11b. ~~**README/의존성 없을 때 Unity 등 엔진 미특정**~~ ✅ v5.4 `detect_engine_signatures()` ([`Engine_Detection_Plan.md`](Engine_Detection_Plan.md))
11c. ~~**협업·데이터/설정 전담 기여도 과소 반영·일괄 푸시 커밋 편향**~~ ✅ v5.5 Evidence LOC + 동적 가중치 ([`Contribution_Fairness_Plan.md`](Contribution_Fairness_Plan.md))
11d. ~~**서브 언어 단독 처리·Lua 환경 모호성** ("Lua (80%) 기반 게임 개발 경험" 같은 잘못된 표현)~~ ✅ v5.6 언어 메인/서브 분류 + Lua 호스트 추론 ([`Language_Categorization_Plan.md`](Language_Categorization_Plan.md))
12. **Consistency `0.5` 계수** — 여전히 임의값; 지수 감쇠 등 데이터 기반 튜닝 예정
13. **`migrations/` ignore** — Django 등에서 의도한 마이그레이션 코드가 LOC에서 제외됨; 필요 시 경로 조정
14. **`DOMAIN_BOOST`(0.05) 튜닝** — 레포 다양성 테스트 후 필요 시 조정 ([`Domain_Reranking_Plan.md`](Domain_Reranking_Plan.md) §7)
15. **유사도 레이블 정밀화** — 간이 상대 방식; 전체 DB 분포 사전 계산 후 백분위 기반으로 개선 가능 (`Similarity_TechMatch_Upgrade.md` §3)
16. **게임/정보보안 등 일부 직무** — 원티드 JSON 매핑 없으면 `wanted_median` null, 점핏만으로 구간 표시
17. **PR/이슈 협업 분석** — 추가 API 필요, 우선순위 낮음 ([`Scoring_Review.md`](Scoring_Review.md))
18. **(선택) 공고 임베딩 재구성** — 직무명+요구기술만 추출 재임베딩 (`Similarity_TechMatch_Upgrade.md` §5)
19. **게임 포트폴리오 `expected_level` 웹 편향** — v5.4는 진단 **피드백 문구**만 게임 맥락 조정; 등급 산정 로직은 별도 검토 ([`Engine_Detection_Plan.md`](Engine_Detection_Plan.md) §5)
20. ~~**모드/플러그인 플랫폼 감지**~~ ✅ v5.7 `MOD_PLATFORM_SIGNATURES` + `detect_mod_platform()` 구현 ([`Mod_Platform_Plan.md`](Mod_Platform_Plan.md))
21. ~~**`is_config_repo` 매칭 입력 제외**~~ ✅ v5.7 `extract_applicant_profile()`에서 `non_config_results` 필터링 구현 ([`Mod_Platform_Plan.md`](Mod_Platform_Plan.md) §4)
22. **신규 도메인 `DOMAIN_TO_CATEGORIES` 미매핑** — `HW/임베디드`·`DBA/데이터`·`그래픽스`는 현재 리랭킹 "매핑 없음" fallback(FAISS 순서 유지). 점핏 카테고리 확인 후 매핑 추가 가능.
23. ~~**시그너처 오탐 (Flutter·Jupyter/ML·Love2D·OpenResty·Minecraft·Stardew Valley·Neovim)**~~ ✅ v5.8 새 키 5종 + 시그너처 강화 ([`Signature_Audit_Plan.md`](Signature_Audit_Plan.md))
24. ~~**모바일(React Native/Expo)·블록체인(Hardhat/Foundry)·데이터(dbt)·인프라(Helm Chart)·도구 개발(VS Code 확장/Browser Extension) 오감지**~~ ✅ v5.8 `ENGINE_SIGNATURES` 8개 카테고리 추가 + `detect_signatures_with_content()` 비동기 manifest 검증 ([`Environment_Expansion_Plan.md`](Environment_Expansion_Plan.md))
25. **블록체인·도구 개발 공고 DB 매칭 품질** — 점핏 JD 코퍼스에 블록체인·도구 개발 공고가 적을 수 있어 FAISS 유사도가 낮게 나올 수 있음. 공고 데이터 보강 또는 fallback 처리 필요.
26. ~~**경력직 공고 신입 상위 노출**~~ ✅ v6.0 `experience_filter.py` 사이드카 캐시 + 후순위 처리.
27. ~~**다중 도메인 프로젝트 균형 추천 없음**~~ ✅ v6.0 `recommend_multi_domain()` + FAISS k=20.
28. ~~**진단 항목 신뢰도 낮은 항목 포함**~~ ✅ v6.0 commit_pattern·growth_trajectory·collaboration 제거, 7개로 축소.
29. ~~**종합 행동 안내 없음**~~ ✅ v6.0 `generate_summary_block()` — 포지셔닝/강점/Quick wins.
30. **`DOMAIN_BOOST` 0.05 튜닝** — 다중 도메인 균형 추천 도입으로 비중 감소. 데이터 기반 조정은 v7.
31. **차등 가산점 (시그너처 vs 휴리스틱)** — 정확도 측정 후 v7 도입 검토.
32. **LLM 도입** — 외부 API 0 원칙으로 v7 이월. 로컬 Qwen2-7B 검토 예정.

---

## 8. 의존성 주의사항

- `sentence-transformers==2.6.1` 버전 고정 필수
- `faiss-cpu==1.8.0` CPU 버전 유지
- `.env`에 `Github_api_token` 필요
- **외부 LLM API 의존 없음** — 분석·매칭·진단 전부 로컬 (설계 원칙, §1 참고)

---

## 9. 실행 방법

Windows 터미널에서 `—`·이모지 등 출력 시 `UnicodeEncodeError`가 나면 **`PYTHONUTF8=1`**(또는 `chcp 65001`)을 설정한 뒤 실행하세요.

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
```

### 연봉 밴드 엔진 단독 테스트

```bash
python valuation_engine.py
```
