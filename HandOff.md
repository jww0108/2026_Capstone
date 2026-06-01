# Git2Value — 프로젝트 HandOff 문서

> 작성일: 2026.04.01 | 최종 갱신: 2026.06.01 | 현재 스펙 버전: v4.0 | 현재 구현 버전: **v7.2-upgrade.7**

새 컨텍스트에서 이 프로젝트를 이어받을 경우 이 문서를 먼저 읽으세요.

### HandOff 갱신 규칙 (에이전트·협업)

- **MultiDomain/사용자 피드백 수정 체크리스트**로 작업할 때는 **체크리스트의 각 단계(Step)를 완료할 때마다** 이 `HandOff.md`를 갱신한다.
- 갱신 내용: 해당 단계에서 바뀐 파일·동작 요약, 버전/이력 섹션 반영, 알려진 과제 목록 정합.
- 외부 문서(Spec_v3, 논문, 발표 자료)도 메이저 버전 변경 시 동기 갱신한다.

### 에이전트 필수 안내 — 도입 보류 영역 (당분간 무시)

**아래 경로·파일은 프로덕션 파이프라인에 포함되지 않습니다.** 기능 구현·리팩토링·API 연동·의존성 추가·버그 수정 범위를 잡을 때 **기본적으로 고려하지 마세요.** 사용자가 명시적으로 “ML 리랭킹 도입”을 요청한 경우에만 해당 영역을 다룹니다.

| 상태          | 경로·파일                           | 비고                                                                   |
| ------------- | ----------------------------------- | ---------------------------------------------------------------------- |
| **도입 보류** | `ml/`                               | RandomForest 직무 분류기 학습·추론 (연구용)                            |
| **도입 보류** | `experiments/`                      | FAISS/키워드/도메인·AI 리랭킹 비교 실험                                |
| **도입 보류** | `run_git2value_trying_reranking.py` | `rerank_by_ai_classifier` 시험 적용본. **메인은 `run_git2value.py`만** |

**프로덕션 모듈 A 리랭킹**은 v7.1 기준 **`run_git2value.py`의 `rerank_by_domain()`** (트리 기반 `detected_domains` + `DOMAIN_BOOST=0.05`)만 사용합니다. 상세: [§2.1 도입 보류 — AI 직무 분류 리랭킹 연구](#21-도입-보류--ai-직무-분류-리랭킹-연구).

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
├── portfolio_diagnosis.py   # 레포별 카드 진단 (v7.2-upgrade.7: LLM 통합, core 3 + extra 5 항목)
├── valuation_engine.py      # v4.0: get_market_band() + v6.0 realistic_range
├── experience_filter.py     # v6.0/v6.1: 경력 요건 필터링 (사이드카 캐시)
├── run_git2value.py         # E2E: Git2ValuePipeline 클래스 + analyze() + CLI 래퍼 (v7.1)
├── llm_readme_evaluator.py  # ★ v7.0 신규: ReadmeEvaluator 클래스 (vLLM 연동)
├── requirements.txt         # 의존성 (sentence-transformers==2.6.1 버전 고정 중요)
├── .env                     # Github_api_token 환경변수 (버전 관리 제외)
├── HandOff.md               # 이 파일
│
├── eval_readme.py           # ★ v7.0 신규: 단일 README LLM 채점 스크립트 (CLI)
├── main.py                  # ★ v7.1: FastAPI 백엔드 게이트웨이 (LLM 평가 + E2E 분석 API, 포트 8080)
├── tests/                   # ★ v7.0 신규: 골든 셋 검증
│   ├── test_golden_set.py   # LLM README 평가 골든 셋 (25개 케이스)
│   └── fixtures/            # 골든 셋용 README 샘플 25개
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
├── md/       (과거의 계획 파일, 필요할 때만 사용)
│
├── ml/                          # ⛔ 도입 보류 — 연구 전용 (§2.1)
│   ├── feature_extractor.py
│   ├── train_job_classifier.py
│   ├── job_classifier.py
│   ├── dataset/job_training_data.csv
│   └── models/                  # job_classifier.pkl은 보통 미커밋 (report.json만 있을 수 있음)
│
├── experiments/                 # ⛔ 도입 보류 — 연구 전용 (§2.1)
│   ├── collect_eval_profiles.py
│   ├── evaluate_ex1.py / evaluate_ex2.py
│   ├── embedding_matcher.py / keyword_matcher.py
│   ├── eval_repos_v*.csv
│   ├── cache/ / results/
│   └── ml/feature_extractor.py  # experiments 쪽 복사본 (루트 ml/와 중복 가능)
│
└── run_git2value_trying_reranking.py  # ⛔ 도입 보류 — AI 리랭킹 시험 E2E (run_git2value.py 미대체)
```

---

## 2.1 도입 보류 — AI 직무 분류 리랭킹 연구

> **상태: 도입 보류 (Deferred)** — 당분간 `run_git2value.py` / `main.py` / `Git2ValuePipeline`에 병합하지 않음.  
> **2026.05.30 결정:** ex2 재실험 후에도 프로덕션은 **`rerank_by_domain()` 현상 유지** (§2.1 실험 결과 참조).

### 목적 (연구만 해당)

FAISS Top-k 후보 공고에 대해, GitHub 프로필을 **8개 직무군**으로 분류한 **RandomForest 확률**을 가산해 순위를 조정하는 2단계 매칭 실험.

```text
effective_score = faiss_similarity + α × P(직무 | profile)   # 시험본 α=0.10
```

기존 프로덕션 방식(`rerank_by_domain`, `DOMAIN_BOOST=0.05`, 다중 도메인 억제 등)과 **대체 관계가 아니라** 실험적 후보입니다.

### 폴더·파일 역할

| 경로                                   | 역할                                                                                                      |
| -------------------------------------- | --------------------------------------------------------------------------------------------------------- |
| `experiments/collect_eval_profiles.py` | `eval_repos_v*.csv` 레포 → `cache/*_profiles.json` 수집                                                   |
| `experiments/evaluate_ex1.py`          | 키워드 vs FAISS 임베딩 Top-k 정확도                                                                       |
| `experiments/evaluate_ex2.py`          | FAISS only vs 도메인 리랭킹 vs AI 분류 리랭킹 (3-way)                                                     |
| `ml/feature_extractor.py`              | 프로필 → 77차원 특징 (`domain_hits_merged` 기본 제외)                                                     |
| `ml/train_job_classifier.py`           | `job_training_data.csv` → `job_classifier.pkl`                                                            |
| `ml/job_classifier.py`                 | pkl 로드·레포별 `probabilities` 예측                                                                      |
| `run_git2value_trying_reranking.py`    | E2E에서 `rerank_by_domain` 대신 `rerank_by_ai_classifier` 호출 시험 (v7.1 `Git2ValuePipeline` **미반영**) |
| `github_domain_dataset.csv`            | GPT 수집 OSS 레포·도메인 라벨 (150건, 15클래스) — **2026.05.30** ex2 추가 평가용                       |
| `experiments/cache/eval_profiles_gpt_domain_snapshot_20260530.json` | gpt_domain 프로필 **고정 스냅샷** (n=150) — 공정 비교용 |
| `ml/models/job_classifier_from_gpt_domain_20260530.pkl` | gpt_domain 특징으로 재학습한 시험 모델 (base `job_classifier.pkl`과 별도) |
| `experiments/results/comparison_all_datasets_20260530.csv` | 3개 평가셋 × 방법 × 모델 통합 요약 |

### 실험 결과 (2026.05.29 ~ 2026.05.30)

`experiments/evaluate_ex2.py`로 **FAISS only / domain_rerank / ai_classifier_rerank** 3-way 비교를 수행했다.  
지표는 정답 라벨(도메인)과 Top-k 예측 채용공고 `category` 일치율(Top-1·Top-3·Top-5).

#### 평가셋

| 평가셋 | n | 프로필 캐시 | 비고 |
| ------ | - | ----------- | ---- |
| **eval_v2** | 29 | `experiments/cache/eval_profiles_v2.json` | 기존 연구용 개인 레포 |
| **comments_refined** | 13 | `experiments/cache/eval_profiles_run_git2value_comments_refined.json` | `run_git2value.py` 주석 레포 URL 정제본 |
| **gpt_domain** | 150 | `experiments/cache/eval_profiles_gpt_domain_snapshot_20260530.json` | `github_domain_dataset.csv` → 프로필 수집 후 **스냅샷 고정** |

#### Top-1 정확도 (%)

| 평가셋 | FAISS only | domain_rerank (룰) | AI rerank (base `job_classifier.pkl`) | AI rerank (GPT 재학습 모델) |
| ------ | ---------- | ------------------ | --------------------------------------- | --------------------------- |
| eval_v2 | 44.8 | 62.1 | **75.9** | 44.8 |
| comments_refined | 53.8 | **76.9** | 61.5 | — |
| gpt_domain | 1.3 | **10.7** | 7.3 | 10.7 |

- **Top-3·Top-5** 및 전체 행: `experiments/results/comparison_all_datasets_20260530.csv`
- gpt_domain 상세: `experiments/results/ex2_gpt_domain_snapshot_base_model_20260530_summary.csv`, `…_gpt_model_…_summary.csv`
- **CLASSIFIER_ALPHA** 스윕(0.05~0.20): Top-1 변화 미미 → 병목은 α가 아닌 **데이터·가드·과제 정합성** 쪽으로 판단.

#### 해석 (요약)

- **데이터셋마다 승자가 다름** — eval_v2만 base AI가 룰보다 +13.8%p 앞섬. comments_refined는 룰이 AI보다 +15.4%p 앞섬.
- **ex2 `domain_rerank` ≠ 프로덕션 `rerank_by_domain`** (다중 도메인 가드·혼합 프로젝트 억제 등 단순화). eval_v2 AI 75.9%를 프로덕션 기대치로 직접 쓰지 말 것.
- **gpt_domain**은 OSS **조직 레포** + 프로필 템플릿화(평균 `profile_for_matching` ~105자)로 FAISS·리랭킹 모두 Top-1 ~10%대. AI 재학습(`job_classifier_from_gpt_domain_20260530.pkl`)은 같은 스냅샷에서 base 대비 Top-1 +3.4%p(7.3→10.7)이나 **룰과 동률**, eval_v2에서는 **75.9→44.8%**로 일반화 악화.
- GPT 모델 교차검증 정확도 ~45.7% (14클래스, DBA 등 일부 라벨 표본 극소).

### 결정 (2026.05.30 — **현상 유지**)

| 항목 | 결정 |
| ---- | ---- |
| **프로덕션 리랭킹** | **`run_git2value.py`의 `rerank_by_domain()` 유지** — AI 분류기로 교체하지 않음 |
| **AI 연구 경로** | `ml/`, `experiments/`, `run_git2value_trying_reranking.py` **도입 보류(Deferred) 지속** |
| **근거** | (1) 평가셋별 AI 일관 우위 없음 (2) ex2↔프로덕션 로직 불일치 (3) 학습 n≈80·재학습 시 타 셋 성능 하락 (4) 룰의 다중 도메인 가드·`rerank_note` 설명 가능성·pkl 비의존 |
| **향후 검토 방향** | 룰 **대체**가 아니라 **하이브리드**(프로덕션 가드 + 조건부 AI 보조). gpt_domain류 데이터는 **개인 개발자 레포**·라벨–채용 카테고리 정합 후 재평가 |

### 보류 사유 (요약)

- 학습·평가 표본 소규모(학습 CSV 약 80건, ex2 평가 n≈29) — **2026.05.30 ex2 3셋 재실험 후에도 AI 전면 도입 근거 부족 확인**.
- `ml/models/job_classifier.pkl`이 저장소에 없을 수 있어 시험본은 로드 실패 시 FAISS-only 폴백.
- 시험본은 프로덕션 `rerank_by_domain`의 다중 도메인 가드 등을 **끄고** AI만 적용한 상태.
- ex2의 `domain_rerank`는 프로덕션 `rerank_by_domain`과 동일하지 **않음** — 수치를 그대로 프로덕션 기대치로 쓰지 말 것.
- 3레포 E2E 입력 vs 특징 추출 `per_repo[0]`만 사용 등 **입력 불일치** 잔존.

### 도입 재개 시 최소 체크리스트 (참고용, 지금 수행하지 않음)

1. `job_classifier.pkl` 빌드·버전 관리 및 `feature_columns` 번들 검증.
2. `evaluate_ex2.py`에 **실제** `run_git2value.rerank_by_domain` 로직 반영 후 3-way 재실험.
3. `Git2ValuePipeline.analyze()` 단일 진입점 + 도메인 가드와 **하이브리드** 설계.
4. `HandOff.md` 본 절 상태를 “도입 완료”로 갱신.

### 에이전트 동작 규칙

- 일반 태스크에서 `ml/`, `experiments/`, `run_git2value_trying_reranking.py`를 import·병합·테스트 대상에 넣지 않는다.
- `DOMAIN_BOOST` 튜닝 이슈(§7 #14)를 AI 분류기로 **대체했다고 가정하지 않는다** — 프로덕션은 여전히 `rerank_by_domain`이다.
- 연구 폴더 정리·문서화만 요청된 경우에만 해당 경로를 읽는다.

---

## 3. 핵심 파일별 역할

### `github_extractor.py` — GitHubExtractor 클래스

| 메서드                           | 역할                                                                                                                                                                                                                |
| -------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `_fetch_with_retry`              | 모든 API 호출 게이트. 403/429 시 Retry-After 파싱 + 지수 백오프 (최대 3회)                                                                                                                                          |
| `_fetch_repo_text_files`         | **v4.0** 의존성 파일 등 contents API로 텍스트 조회                                                                                                                                                                  |
| `_fetch_all_commits_paginated`   | 커밋 목록 수집. `MAX_COMMIT_PAGES=3` (최대 300커밋) 상한                                                                                                                                                            |
| `_fetch_author_census` (v7.2-upgrade.2) | 작성자 판정 전용 전수 커밋 수집. `MAX_CENSUS_PAGES=20` (최대 2000커밋) 상한                                                                                                                                       |
| `_commit_author_key` (v6.1)      | **신규**: GitHub login > email > name 우선순위로 작성자 안정 식별. prefix(`login:`/`email:`/`name:`)로 카테고리 충돌 방지                                                                                           |
| `_commit_author_label` (v6.1)    | **신규**: 리포트 표시용 작성자 이름                                                                                                                                                                                 |
| `_stratified_sample_commits`     | 초기/중간/최근 각 최대 25개씩, 레포 내부 + 전역 SHA dedup                                                                                                                                                           |
| `_cicd_and_test_ratio_from_tree` | tree blob size>200B로 CI/CD 실질성 판별, 테스트 파일 비율 계산                                                                                                                                                      |
| `_count_active_weeks`            | author 커밋 목록 기준 ISO 주(년+주차) 개수                                                                                                                                                                          |
| `_calc_consistency_score`        | 커밋 간격 표준편차 → `max(0, 10 - std * 0.5)`. 전체 author 커밋 목록 기준                                                                                                                                           |
| `evaluate_repository`            | 레포 1개 완전 분석. **v7.2-upgrade.4**: 점수 경로(`MAX_COMMIT_PAGES`)와 작성자 판정 경로(`MAX_CENSUS_PAGES`) 분리. `distinct_author_count`는 전수 기준, `dominance_ratio`는 **지원자 기준 비율**로 계산하고 `has_team_experience`/`target_commit_ratio_census`/`contribution_role`를 함께 반환 |
| `extract_applicant_profile`      | LOC 가중 github_score + `profile_for_matching` + `domain_hits_merged` + `per_repo`(v7.2-upgrade.4: `has_team_experience`·`target_commit_ratio_census`·`contribution_role` 포함) |

**클래스 상수:** `MAX_COMMIT_PAGES = 3`, `MAX_CENSUS_PAGES = 20`, `MIN_AUTHOR_COMMITS_ABSOLUTE = 3`, `MIN_AUTHOR_COMMIT_RATIO = 0.02`

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

| 필드                    | 의미                                                               |
| ----------------------- | ------------------------------------------------------------------ |
| `repo_type`             | `"team"` (distinct_author_count >= 2) 또는 `"personal"`            |
| `distinct_author_count` | 레포 전체 커밋 작성자 수 (login > email > name 우선순위)           |
| `repo_author_names`     | 표시용 작성자 라벨 리스트 (최대 10명)                              |
| `target_commit_count`   | 지원자 본인 커밋 수                                                |
| `total_repo_commits`    | 레포 전체 커밋 수                                                  |
| `target_commit_ratio`   | 지원자 커밋 / 레포 전체 커밋 비율                                  |
| `has_team_experience` (v7.2-upgrade.4) | 티어 판정용 팀 경험 플래그 (`distinct_author_count >= 2`) |
| `target_commit_ratio_census` (v7.2-upgrade.2) | 전수 기준 지원자 커밋 / 레포 전체(봇 제외) 비율 |
| `contribution_role` (v7.2-upgrade.2) | 팀 레포 기여 역할 (`주도 기여` / `적극 기여` / `협업`) |
| `repo_active_weeks`     | 레포 전체 커밋 기준 활성 주 수 (지원자 기준 `active_weeks`와 별도) |

---

### `profile_builder.py` — v5.8

- **`ENGINE_SIGNATURES` / `detect_engine_signatures(tree_data)`** (v5.4~v5.8): 게임 엔진 4종 + 분석 환경 2종 + 신규 8종(모바일·블록체인·인프라·데이터·도구) 감지
- **`detect_signatures_with_content()`** (v5.8): manifest 내용 검증 비동기 함수 (Expo·VS Code 확장·Browser Extension)
- **`MOD_PLATFORM_SIGNATURES` / `detect_mod_platform()`** (v5.7): EDOPro·Garry's Mod·Factorio·Minecraft·Stardew Valley·WoW 6종
- **`LUA_HOST_SIGNATURES` / `detect_lua_host()`** (v5.6): Roblox·Love2D·Defold·Solar2D·Cocos2d-x·OpenResty·NodeMCU·Neovim 9종
- **`MAIN_LANGUAGES` / `SUB_LANGUAGE_SIGNALS`** (v5.6): 언어 메인/서브 분류
- **`categorize_languages(lang_stats)`** (v5.6): main/sub/trivial 분리
- **`detect_domain_hits` / `merge_domain_hits`**: 트리 경로 기반 도메인 히트. **고유 키워드 종류 수** 기준, 2종류 미만 도메인 제외 (v5.3.1). v7.2-upgrade.5: 모바일/게임은 강증거(엔진/네이티브 경로) 없으면 신규 도메인 생성 억제
- **`find_dependency_paths` / `parse_dependency_contents`**: package.json 등에서 프레임워크 라벨 추출
- **`has_deployment_signals`**: docker-compose, Vercel 등 배포 시그널
- **`compute_tree_structure_stats`**: 파일당 평균 LOC, `.gitignore` 여부
- **`build_profile_text`**: FAISS 질의용 공고형 문장. v5.6 `language_category`/`sub_language_host` 기반 메인/서브 분리 출력
- **`READ_KEYWORDS` / `extract_readme_keywords()`**: 도메인별 키워드 사전 + 압축 문장 추출 (v5.3.2 영어/CV/NLP 보강, v5.8 블록체인/데이터/도구개발 추가)

#### README 활용 분기 로직 (v5.3)

| 잔량       | 티어   | `build_profile_text` 반영                      |
| ---------- | ------ | ---------------------------------------------- |
| 200자 이상 | long   | 키워드 추출 성공 시에만 압축 문장 추가         |
| 50~199자   | medium | README 본문 미반영 (구조·언어·의존성 데이터만) |
| 49자 이하  | short  | 동일                                           |

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
      "growth_signal": {...},       # 성장성/활동 지속성 신호 (점수 미반영 진단)
    },
  }
```

#### 주요 함수

| 함수                                                                                                     | 역할                                                                      |
| -------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------- |
| `classify_repo_type(repo)` (v6.1)                                                                        | `repo.repo_type` 우선 사용, 폴백으로 `distinct_author_count >= 2` 판정    |
| `_readme_diagnosis_single(repo)` (v6.1)                                                                  | 단일 레포 README 평가 (3차원 + 길이)                                      |
| `_extract_readme_doc_signals(readme_text)` (v7.2-upgrade.7)                                             | README 실행/환경/기술/시각화 근거 보조 진단                              |
| `analyze_commit_message_quality(messages)` (v7.2-upgrade.7)                                              | 무의미 커밋 비율 + 점수 보정 계수(1.0/0.9/0.8) 공용 계산                  |
| `_structure_diagnosis_single(repo)` (v6.1)                                                               | 단일 레포 구조 평가                                                       |
| `_commit_quality_diagnosis_single(repo)` (v6.1)                                                          | 무의미 커밋 비율 + Conventional Commits 변환 힌트                         |
| `_test_diagnosis_single(repo, game_engines)` (v6.1)                                                      | 단일 레포 테스트 (게임 엔진 맥락 반영)                                    |
| `_cicd_diagnosis_single(repo, game_engines)` (v6.1)                                                      | 단일 레포 CI/CD                                                           |
| `_deployment_diagnosis_single(repo, game_engines)` (v6.1)                                                | 단일 레포 배포                                                            |
| `_commit_pattern_diagnosis_single(repo)` (v6.1)                                                          | **지원자 본인 기준** 커밋 리듬 (`target_commit_count` / `active_weeks`)   |
| `_growth_signal_diagnosis_single(repo)` (v7.2-upgrade.7)                                                | 성장성/활동 지속성 신호 (`growth_signal`) 진단 (점수 미반영)              |
| `_team_required_items(extra_items)` (v6.1)                                                               | 팀 레포의 extra를 "필수 미흡"으로 격상                                    |
| `diagnose_single_repo(repo)` (v6.1)                                                                      | 레포 1개 진단 결과 반환                                                   |
| `expected_level(per_repo_diags, team_repo_count)` (v6.1)                                                 | 등급 판정. **팀 레포가 없으면 Competitive 이상 도달 불가**                |
| `evaluate_readme_quality(readme_text)` (v6.0)                                                            | 3차원 룰베이스 (목적/스택/시각화)                                         |
| `COMMIT_REWRITE_HINTS` / `get_rewrite_hint(msg)` (v6.0)                                                  | 무의미 커밋 → Conventional Commits 변환 힌트                              |
| `_aggregate_strengths(per_repo_diags)` (v6.1)                                                            | 양호 항목 빈도순 강점 추출 (개인 레포는 core만, 팀은 core+extra)          |
| `_aggregate_quick_wins(per_repo_diags)` (v6.1)                                                           | 미흡 항목 빈도순 Quick wins 추출                                          |
| `_portfolio_composition_lines()` (v6.1)                                                                  | 레포 구성 요약 (개인 N개 + 팀 M개)                                        |
| `generate_summary_block()` (v6.1)                                                                        | 종합 분석 블록 — GitHub 점수 + 레포 구성 + 강점 + Quick wins              |
| `repo_classification_note(repo)` (v6.0)                                                                  | 레포의 협업 여부 한 줄 요약                                               |
| `mod_context_message()` / `config_repo_message()` (v5.7)                                                 | 모드/설정 프로젝트 안내                                                   |
| `blockchain_context_message()` / `data_engineer_context_message()` / `tool_dev_context_message()` (v5.8) | 신규 도메인 맥락 메시지                                                   |
| `_build_repo_classifications(per_repo)`                                                                  | 레포별 분류(main/mod/config) + 안내 메시지                                |
| `run_diagnosis(profile)` (v6.1)                                                                          | 진입점. 반환에 **`per_repo_diagnoses`** (이전 `portfolio_diagnosis` 대체) |

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

| 상태                 | 의미                            | \_BAD_STATUSES 포함 |
| -------------------- | ------------------------------- | ------------------- |
| 양호                 | 충족                            | ❌                  |
| 규칙적               | 커밋 리듬 양호                  | ❌                  |
| 보통                 | 부분 충족                       | ❌                  |
| 미흡                 | 부족                            | ✅                  |
| 개선 필요            | 일부 충돌                       | ✅                  |
| 미경험               | 시도 흔적 없음                  | ✅                  |
| 선택 가점            | 테스트 미감지 (Top 차별화 요소) | ✅                  |
| **없음** (v6.1)      | 운영 항목 부재                  | ✅                  |
| **필수 미흡** (v6.1) | 팀 레포에서 운영 항목 부재      | ✅                  |
| **확인 필요** (v6.1) | 산출 불가 (커밋 리듬)           | ✅                  |

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

| 함수                                                              | 역할                                                                                                                             |
| ----------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------- |
| `extract_experience_requirement(position, text)`                  | 정규식으로 경력 요건 추출. `requirement_type` 6분류 (`unspecified`/`open_to_all`/`junior`/`senior`/`min_years`/`specific_years`) |
| `is_applicant_eligible(exp_req, applicant_years)` (v6.1)          | 추천 후보 적격 여부. **0년차는 `unspecified`/`open_to_all`/`junior`만 허용 + `min_years <= 0`**                                  |
| `load_or_build_cache(metadata, cache_path)`                       | 사이드카 캐시(`vector/experience_cache.json`) 로드/빌드. v6.1: 누락 항목(`requirement_type` 없음) 갱신                           |
| `split_by_experience(top_matches, applicant_years, cache)` (v6.1) | 적격/제외 공고 분리 반환                                                                                                         |
| `filter_by_experience(...)` (하위 호환)                           | `split_by_experience` 결과를 합쳐서 반환                                                                                         |

#### 0년차 기준 차이

| 패턴        | v6.0 처리                 | v6.1 처리                           |
| ----------- | ------------------------- | ----------------------------------- |
| "1년 이상"  | 신입+1년 여유로 통과      | **추천에서 제외** (`min_years > 0`) |
| "신입/경력" | `junior_only` 매칭 → 통과 | `open_to_all` 매칭 → 통과           |
| "경력무관"  | `unspecified` 폴백 → 통과 | `open_to_all` 명시 → 통과           |

---

### `run_git2value.py` — E2E 파이프라인 (v7.1)

#### 기본 설정

- FAISS 인덱스(`vector/`) + `jhgan/ko-sroberta-multitask`
- 임베딩 입력: `profile_for_matching` (없으면 `applicant_resume` 폴백)
- **`MAX_REPO_COUNT = 3`** (v6.1): 입력 레포 최대 3개로 제한, 초과 시 앞 3개만 사용
- **FAISS k=20** (v6.0): 다중 도메인 균형 추천 + 경력 필터 여유분 확보

#### v7.1 신규: `Git2ValuePipeline` 클래스

API 서버 환경에서 인프라를 1회 로드하고 요청마다 분석만 실행하는 클래스.

| 메서드                                      | 역할                                                                                                                        |
| ------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------- |
| `__init__()`                                | FAISS 인덱스·메타데이터, `SentenceTransformer`, `Git2ValueEngine`, 경험 캐시, `GitHubExtractor`, `ReadmeEvaluator` 1회 로드 |
| `check_llm()`                               | vLLM 서버 가용 여부 확인 + `self.llm_available` 설정. `lifespan` 또는 CLI 시작 시 1회 호출                                  |
| `analyze(username, repos, applicant_years)` | E2E 분석. **print 없이 dict 반환.** 오류 시 `{"status": "error", "error": "..."}`                                           |

`analyze()` 반환 dict:

- **API 공개 키**: `status`, `error`, `github_score`, `per_repo`, `level`, `summary`, `job_matching`, `salary_band`, `tech_analysis`, `meta`
- **`_internal`** (CLI 출력 전용, API에서 자동 제거): `profile`, `per_repo_diags`, `diag_bundle`, `top_matches_5`, `rerank_note`, `multi_domain_result`, `mismatch_diag`, `domain_check`, `detected_domains_merged`, `band_report`, `matched_categories_seen`, `ref_salary_categories`, `alt_salary_band`, `jumpit_category`, `has_mod_or_config`, `repo_classifications`, `tech_result`

#### v7.1 신규: dict 빌더 함수 7개

`analyze()` 내부에서 호출하는 순수 변환 함수. 모두 모듈 레벨 정의.

| 함수                                                                           | 역할                                                                                              |
| ------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------------- |
| `_build_github_score_dict(profile)`                                            | `github_score`, `score_breakdown` 구조화                                                          |
| `_build_per_repo_dict(profile, per_repo_diags)`                                | `profile["per_repo"]`와 `diag_bundle["per_repo_diagnoses"]` 를 `repo_name` 기준으로 병합          |
| `_build_job_matching_dict(...)`                                                | FAISS 매칭 + 도메인 리랭킹 + `similarity_label` 포함                                              |
| `_build_salary_band_dict(band_report, ref_salary_categories, alt_salary_band)` | 연봉 밴드 + 참고 직무                                                                             |
| `_build_tech_analysis_dict(tech_result)`                                       | 기술 매칭 분석 그대로 전달                                                                        |
| `_build_level_dict(diag_bundle)`                                               | `expected_level` dict                                                                             |
| `_build_summary_dict(diag_bundle, per_repo_diags)`                             | `summary_block` 텍스트 + `_aggregate_strengths` / `_aggregate_quick_wins` 구조화 데이터 병렬 제공 |

#### v7.1 신규: `_print_full_report()` / `run_e2e_pipeline()` 래퍼 전환

- **`_print_full_report(result, target_username, applicant_years)`**: `analyze()` 반환 dict(`_internal` 포함)를 받아 기존 CLI 보고서 형식 그대로 출력.
- **`run_e2e_pipeline()`**: `Git2ValuePipeline()` 생성 → `check_llm()` → `analyze()` → `_print_full_report()` 의 얇은 래퍼. CLI 동작 100% 유지.

#### 모듈 A 핵심 함수

| 함수                                 | 역할                                                                                                                                                            |
| ------------------------------------ | --------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `route_job_category_safe()` (v6.0)   | 콤마/슬래시 포함 결과 방어 래퍼                                                                                                                                 |
| `rerank_by_domain()` (v5.3)          | 단일 도메인에서 +0.05 가산. 다중 도메인 시 억제                                                                                                                 |
| `recommend_multi_domain()` (v6.0)    | 히트 비율 < 2배이면 도메인별 상위 1~2개씩 분리 추천                                                                                                             |
| `similarity_label()` (v6.1)          | **절대값 기준 도입**: max_s < 0.70 시 "약함" 통일, score >= 0.85 시 "강함", 그 외 spread 기반 분기                                                              |
| `diagnose_domain_mismatch()` (v6.0)  | db_coverage/weak_signal/consistent/ambiguous 4분기                                                                                                              |
| `analyze_tech_match()` (v6.1)        | **3단계 정교화**: 포함관계 처리(`TECH_INCLUSION_MAP`) + 도메인 무관 기술 필터(`DOMAIN_IRRELEVANT_TECHS`) + 미보유 3개 제한 + 학습 권장(`CATEGORY_TARGET_TECHS`) |
| `filter_techs_by_inclusion()` (v6.1) | Spring Boot 있으면 Spring 제거, Next.js 있으면 React 제거 등                                                                                                    |
| `filter_techs_by_domain()` (v6.1)    | 매칭 직무와 무관한 기술 필터                                                                                                                                    |

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

### `main.py` — FastAPI 백엔드 게이트웨이 (v7.1)

#### 엔드포인트 전체 (v7.1 기준)

| 메서드     | 경로                       | 입력          | 응답                         | 비고                      |
| ---------- | -------------------------- | ------------- | ---------------------------- | ------------------------- |
| `GET`      | `/health`                  | —             | `HealthResponse`             | vLLM 연결 상태            |
| `POST`     | `/v1/readme/evaluate`      | JSON body     | `EvaluateReadmeResponse`     | README LLM 평가           |
| `POST`     | `/v1/readme/evaluate/file` | multipart     | `EvaluateWithSourceResponse` | 파일 업로드               |
| `POST`     | `/v1/readme/evaluate/url`  | form          | `EvaluateWithSourceResponse` | GitHub URL                |
| **`POST`** | **`/v1/analyze`**          | **JSON body** | **`AnalyzeResponse`**        | **★ v7.1 신규: E2E 분석** |

#### `POST /v1/analyze` 요청 / 응답 모델

```python
# 요청
class AnalyzeRequest(BaseModel):
    github_username: str          # GitHub ID (영문/숫자/-, 1~39자)
    repos: List[str]              # 레포 경로 목록 (1~3개)
    applicant_years: Optional[int] = 0  # 경력 년수 (신입=0)

# repos 예시: ["user/repo", "user/repo2/tree/branch"]
```

```python
# 응답
class AnalyzeResponse(BaseModel):
    status: str                           # "success" | "error"
    error: Optional[str]
    github_score: Optional[Dict[str, Any]]
    per_repo: Optional[List[Dict[str, Any]]]
    level: Optional[Dict[str, Any]]
    summary: Optional[Dict[str, Any]]
    job_matching: Optional[Dict[str, Any]]
    salary_band: Optional[Dict[str, Any]]
    tech_analysis: Optional[Dict[str, Any]]
    meta: Optional[Dict[str, Any]]        # version, llm_available, analysis_time_seconds 등
```

#### 싱글톤 / lifespan (v7.1)

- **`_pipeline: Git2ValuePipeline`**: 앱 시작 시(`lifespan`) 1회 초기화. FAISS·모델·캐시 재로드 없이 모든 요청 공유.
- 초기화 실패 시 `_pipeline = None`으로 설정 → `/v1/analyze` 요청 시 **503** 반환.
- 기존 `ReadmeEvaluator` 싱글톤(`_evaluator`) 및 vLLM health check는 변경 없이 유지.

#### CORS (v7.1 변경)

기존 `allow_origins=["*"]` → **명시적 출처 목록** (`Vercel 배포 도메인 + localhost:3000/5173`).  
환경변수 `CORS_ORIGINS`에 콤마 구분 URL을 넣으면 오버라이드 가능:

```bash
set CORS_ORIGINS=https://git2value.vercel.app,http://localhost:3000
python main.py
```

#### 입력 검증

- `github_username`: `^[a-zA-Z0-9\-]{1,39}$` — 정규식 불일치 시 **400**
- 각 repo: `user/repo` 또는 `user/repo/tree/branch` 형식 — 불일치 시 **400**
- repos 0개 또는 4개 이상 — **400**

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

| 항목        | 조건                              | 점수                         |
| ----------- | --------------------------------- | ---------------------------- |
| CI/CD       | 워크플로우/Dockerfile blob > 200B | 10 또는 0                    |
| 테스트 비율 | < 5%                              | 0 / 5~20% → 5 / ≥20% → 10    |
| 활성 주 수  | `all_author_commits` ISO 주 개수  | ≥8주 → 10, ≥4주 → 5, 그 외 0 |

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

| 필드                  | 의미                                 |
| --------------------- | ------------------------------------ |
| `repo_type`           | `"team"` / `"personal"`              |
| `repo_author_names`   | 표시용 작성자 리스트 (최대 10명)     |
| `repo_active_weeks`   | 레포 전체 커밋 기준 활성 주          |
| `total_repo_commits`  | 레포 전체 커밋 수 (author 필터 없음) |
| `target_commit_count` | 지원자 본인 커밋 수                  |
| `target_commit_ratio` | 지원자 / 레포 전체 비율              |
| `has_team_experience` | 팀 경험 플래그 (`distinct>=2`)       |
| `target_commit_ratio_census` | 전수 기준 지원자 / 레포 전체 비율 |
| `contribution_role` | 팀 레포 역할 라벨 (`주도 기여`/`적극 기여`/`협업`) |

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

### `POST /v1/analyze` 응답 JSON (v7.1)

```json
{
  "status": "success",
  "error": null,
  "github_score": {
    "total": 72.4,
    "method": "대표 프로젝트(최고점) 70% + 전체 평균 30%",
    "breakdown": { "contribution": 42.0, "quality": 20.0, "consistency": 10.4 },
    "breakdown_note": "최고 레포 기준"
  },
  "per_repo": [
    {
      "repo_name": "user/repo",
      "repo_type": "team",
      "distinct_author_count": 3,
      "is_fork": false,
      "repo_total_score": 72.4,
      "detected_domains": ["서버/백엔드"],
      "frameworks": ["FastAPI"],
      "diagnosis": {
        "core_items": { "readme_quality": {...}, "project_structure": {...}, "commit_quality": {...} },
        "extra_items": { "test_coverage": {...}, "cicd": {...}, "deployment": {...}, "commit_pattern": {...} }
      }
    }
  ],
  "level": { "grade": "Competitive", "description": "팀 프로젝트 + CI/CD 확인 → 경쟁력 있는 포트폴리오." },
  "summary": {
    "text": "[종합 분석]\n  GitHub 점수 : 72.4점 / 100점 ...",
    "positioning": "서버/백엔드 Competitive 수준 포트폴리오",
    "strengths": ["README 품질", "CI/CD"],
    "quick_wins": ["테스트 코드 추가", "Docker Compose 작성"]
  },
  "job_matching": {
    "primary_domain": "서버/백엔드",
    "detected_domains": ["서버/백엔드"],
    "is_multi_domain": false,
    "rerank_note": "도메인 감지: '서버/백엔드' → ... 재정렬했습니다.",
    "eligible_matches": [
      {
        "rank": 1,
        "position": "백엔드 개발자",
        "company_name": "XXXX",
        "category": "서버/백엔드",
        "similarity": 0.8512,
        "effective_score": 0.9012,
        "domain_boosted": true,
        "similarity_label": "강함",
        "experience_warning": null
      }
    ],
    "domain_mismatch": null,
    "multi_domain_picks": null,
    "jumpit_category": "서버/백엔드",
    "company_types": ["서버/백엔드 유사 공고 3건"]
  },
  "salary_band": {
    "matched_category": "서버/백엔드",
    "experience_level": "신입~3년",
    "salary_range": { "jumpit_median": 36000000, "wanted_median": 38000000, "combined_range": "3,600만~3,800만원" },
    "realistic_range": { "median": 37000000, "p25_estimate": 31450000, "p75_estimate": 44400000 },
    "source": "점핏 2025 공채 기준",
    "note": "GitHub 점수 미반영 — 시장 참고용",
    "reference_categories": [{ "category": "웹 풀스택", "combined_range": "3,800만~4,000만원" }],
    "alt_category_band": null
  },
  "tech_analysis": {
    "matched_techs": ["Python", "FastAPI", "Docker"],
    "missing_techs": ["AWS"],
    "learning_suggestions": ["Spring Boot", "PostgreSQL"],
    "company_types": ["서버/백엔드 유사 공고 3건"]
  },
  "meta": {
    "version": "v7.0",
    "llm_available": true,
    "analysis_time_seconds": 18.3,
    "repos_analyzed": 1,
    "applicant_years": 0
  }
}
```

---

## 6. 버전 이력 및 주요 결정 사항

### v7.2-upgrade.7 (2026.06.01 — 커밋 품질 계수 + 성장성/문서화 진단 보강)

**60/30/10 축은 유지하면서, 커밋 점수에 메시지 품질 보정 계수를 연결하고 성장성/문서화는 점수 미반영 진단 신호로 확장.**

- **`portfolio_diagnosis.py`**:
  - `analyze_commit_message_quality()` 공용 함수 추가(무의미 커밋 비율, 계수 1.0/0.9/0.8, 샘플 메시지).
  - `_commit_quality_diagnosis_single()`이 공용 분석 결과를 재사용하도록 변경.
  - `_growth_signal_diagnosis_single()` 추가, `diagnose_single_repo().extra_items.growth_signal`로 노출.
  - README 룰베이스 진단에 `_extract_readme_doc_signals()`을 추가해 실행 방법/환경 설정/기술 설명/시각화 근거를 detail/action에 반영.
- **`github_extractor.py`**:
  - `commit_score` 산출 후 `commit_quality_factor`를 적용한 `adjusted_commit_score` 도입.
  - `blend_100 = loc_score*loc_w + adjusted_commit_score*commit_w`로 contribution 계산.
  - `score_detail.axes[].items[key=commit_activity].raw_value`에
    `commit_score_100`, `adjusted_commit_score_100`, `commit_quality_factor`, `bad_message_ratio` 추가.
- **`run_git2value.py`**:
  - CLI `[점수 해석 가이드]`에 커밋 품질 계수 반영 사실 명시.
  - `EXTRA_LABELS`에 `growth_signal` 추가해 성장성 진단을 카드 출력 경로에 포함.
- **`main.py`**:
  - `AnalyzeResponse` 및 `/v1/analyze` description에
    `commit_quality_factor`, `growth_signal`, 문서화 근거 진단 포함 가능성을 명시.
- **문서 동기화**:
  - `SCORING_CONTRIBUTION_LOGIC.md`에 커밋 품질 계수 수식/해석 및 성장성(점수 미반영) 정책 기록.

---

### v7.2-upgrade.6 (2026.05.31 — 티어 의미 정렬 + 점수 해석/응답 문서화 강화)

**티어/점수 문구를 “개발자 등급 판정”이 아니라 “GitHub 포트폴리오 해석·진단” 의미로 정렬하고, API 응답 설명을 확장.**

- **`portfolio_diagnosis.py`**:
  - `expected_level()` 요약 문구를 `Top/Competitive/Entry GitHub Portfolio Tier` 의미로 조정.
  - `generate_summary_block()`의 포지셔닝 문구를 `Primary Domain Portfolio Tier` 관점으로 정리.
- **`run_git2value.py`**:
  - `level` 응답에 하위 호환 유지(`grade`/`description`) + 확장 키 추가:
    - `tier_label`, `tier_context`, `primary_domain_tier`, `caveat`
  - CLI `[점수 해석 가이드]`에 커밋 항목이 단순 개수 평가가 아니라 **개발 활동 이력**(지속성·리듬 포함)임을 명시.
- **`main.py`**:
  - `AnalyzeResponse` 필드 설명 보강 (`github_score.axes`, `score_detail`, `per_repo[].score_detail`, `level` 확장 키).
  - `/v1/analyze` description을 “GitHub 포트폴리오 해석·진단/주요 직무 매칭/시장 연봉 밴드” 관점으로 조정.
- **문서 정리**:
  - `# Portfolio Tier System 개선 제안.md`: **현재 구현(Primary Domain Tier)** vs **로드맵(직무별 독립 티어)** 분리.
  - `SCORING_CONTRIBUTION_LOGIC.md`:
    - README는 100점 직접 배점이 아니라 진단/gate/매칭 보조 및 evidence LOC 간접 반영임을 명시.
    - `score_detail` 응답 구조와 커밋 항목 해석(개발 활동 이력)을 문서화.

---

### v7.2-upgrade.5 (2026.05.30 — 팀 경험 정합 완성 + 모바일/게임 과검출 완화)

**`has_team_experience`를 등급 내부 팀 신호 집계까지 확장해 Entry 고정 현상을 해소하고, 모바일/게임 도메인 오탐을 보수적으로 억제.**

- **`portfolio_diagnosis.py`**:
  - `expected_level()`의 `team_diags` 산정을 `has_team_experience` 우선 기준(없으면 `repo_type=="team"` 폴백)으로 전환.
  - 효과: `repo_type="personal"` + `has_team_experience=true` 레포도 팀 운영 신호(`test/cicd/deploy/commit_pattern`) 평가 경로에 반영.
- **`profile_builder.py`**:
  - `detect_domain_hits()`에 모바일/게임 강증거 게이트 추가.
    - 모바일: `android/`, `ios/`, React Native/Expo 단서(예: `metro.config.js`, `app.json`) 없으면 키워드만으로 신규 생성 금지.
    - 게임: Unity/Unreal/Godot/Cocos 계열 경로·확장자·`assets/projectsettings` 등 강증거 없으면 키워드만으로 신규 생성 금지.
  - `merge_readme_domain_hits()`에서 README 단독 신규 생성 제한 도메인에 `모바일 앱`, `게임 개발` 추가(`도구 개발`과 동일 정책).
- **`run_git2value.py`**:
  - `_filtered_domains_for_mixed_check()`에 저신뢰 도메인(`도구 개발`, `모바일 앱`, `게임 개발`) 약신호 제외 규칙 확장.
  - `merged_detected_domains_from_profile()`에서 약신호 도메인은 primary 선정에 후순위 배치(응답에는 유지).
- **`tests/test_domain_taxonomy.py` + fixtures**:
  - 과검출 억제 fixture(`ai_backend_noise_tree.json`) 추가.
  - 정상 검출 fixture(`mobile_react_native_tree.json`, `game_engine_tree.json`) 추가.
  - 회귀 결과: `19 passed`.
- **실측 검증**:
  - `siheon012` 3레포(`Deepsentinel` + `langgraph-api` + `korean_finetuning`) 분석 시 등급 `Top` 확인.
  - `Deepsentinel` 단일 3계정 시나리오는 단일 레포 조건(`multi_proj` 미충족)으로 `Entry` 유지(의도된 동작).

---

### v7.2-upgrade.4 (2026.05.29 — 팀 경험 플래그 분리)

**`repo_type`(배점 기준)과 팀 경험(`has_team_experience`, 티어 기준)을 분리해 지배적 기여자 레포의 팀 경험 소실 부작용을 완화.**

- **`github_extractor.py`**:
  - `evaluate_repository()` 반환에 `has_team_experience` 추가 (`distinct_author_count >= 2`).
  - `extract_applicant_profile()`의 `per_repo`에도 `has_team_experience` 전달.
- **`portfolio_diagnosis.py`**:
  - `diagnose_single_repo()` 반환에 `has_team_experience`, `target_commit_ratio_census`, `contribution_role`, `dominance_ratio`, `is_dominance_override` 포함.
  - `run_diagnosis()`의 `team_repo_count` 산정을 `has_team_experience` 우선 기준으로 전환(없으면 기존 `repo_type=="team"` 폴백).
- **`run_git2value.py`**:
  - `_build_per_repo_dict()`에 `has_team_experience` 포함.
  - `_print_repo_card()`에서 `is_dominance_override=True` + `has_team_experience=True` 조합을
    `"팀 경험 레포 · N명 중 주도 기여 (X%) · 배점: 개인 기준"`으로 명시 출력.

---

### v7.2-upgrade.3 (2026.05.29 — 동일 레포 다계정 판정 정합화)

**같은 레포를 서로 다른 GitHub 계정으로 분석할 때, 팀/개인 판정이 의도와 다르게 동일해지는 문제를 보정.**

- **`github_extractor.py`**:
  - `evaluate_repository()`의 dominance override 기준을 **최다 기여자(global)** 에서 **지원자(target) 기여 비율**로 변경.
  - 조건: `distinct_author_count >= 2`이고, 지원자 비율(`dominance_ratio`)이 `>= 0.85`일 때만 `repo_type = "personal"` 재판정.
  - 효과: 같은 팀 레포라도 지원자별로 `repo_type`이 달라질 수 있음.
- **검증 (실측):**
  - 레포 `siheon012/Deepsentinel`
  - `siheon012` → personal (`is_dominance_override=True`, `dominance_ratio=0.946`)
  - `protove` → team (`is_dominance_override=False`, `dominance_ratio=0.054`)
  - `Kimdoyeon123` → team (`is_dominance_override=False`, `target_commit_ratio_census=0.0049`)

---

### v7.2-upgrade.2 (2026.05.29 — 작성자 전수 조사 분리 + 팀 기여 역할 라벨)

**작성자 판정 정확도를 높이기 위해 점수 경로와 작성자 전수 경로를 분리하고, 팀 레포에 역할 라벨을 노출.**

- **`github_extractor.py`**:
  - `MAX_CENSUS_PAGES = 20`, `_fetch_author_census()` 추가 (작성자 판정 전용 전수 수집).
  - `MIN_AUTHOR_COMMITS_ABSOLUTE=3`, `MIN_AUTHOR_COMMIT_RATIO=0.02` 이중 게이트 추가.
  - `evaluate_repository()`에서 `distinct_author_count`/`dominance_ratio`를 전수 기준으로 계산.
  - `target_commit_ratio_census`, `contribution_role` 반환 필드 추가.
  - 전수 실패 시 제한 페이지 데이터로 폴백 + 경고 누적.
- **`run_git2value.py`**:
  - `_print_repo_card()` 팀 라벨을 `팀 레포 · N명 중 {역할} (X%)` 형식으로 확장.
  - `_build_per_repo_dict()`에 `target_commit_ratio_census`, `contribution_role` 포함.
- **출력/호환성**:
  - 기존 `target_commit_ratio`/`repo_type` 필드 유지(하위 호환).
  - 신규 필드는 선택적 확장으로 추가되어 API 응답 구조를 깨지 않음.

---

### v7.2-upgrade.1 (2026.05.29 — 도구 개발 과검출 완화 + README 키워드 버그 픽스)

**`도구 개발` 도메인 오탐으로 인한 false mixed를 줄이고, README 키워드 압축 경로 NameError를 수정.**

- **`profile_builder.py`**:
  - `DOMAIN_SIGNALS["도구 개발"]` 키워드 정밀화 (`manifest`/`plugin` 단순 substring 의존 완화).
  - `_match_tool_domain_keywords()` 신규 — 브라우저 확장/VS Code 확장 패턴 기반 보강 신호 추가.
  - `merge_readme_domain_hits()` 가드 추가:
    - `도구 개발`은 README 단독 신호로 신규 생성하지 않고, tree 선행 신호가 있을 때만 +1 허용.
  - `extract_readme_keywords()` 버그 픽스: `text_lower` 누락 선언 복구 (`name 'text_lower' is not defined` 해소).
- **`run_git2value.py`**:
  - `_filtered_domains_for_mixed_check()` 신규.
  - `rerank_by_domain()` / `recommend_multi_domain()`에 저강도 `도구 개발` hit 보수 처리 규칙 적용:
    - `도구 개발` hit가 낮고(<=3), 타 도메인이 충분히 강하면 mixed 비율 계산에서 제외.
  - 목적: 프론트/백엔드 주도 레포에서 `도구 개발` 동반 false mixed 감소.
- **`tests/test_domain_taxonomy.py`**:
  - `extract_readme_keywords()` NameError 회귀 테스트 추가.
  - `도구 개발` 과검출 억제/정상검출/mixed 완화 회귀 테스트 확장.
- **`tests/fixtures/trees/`**:
  - `frontend_manifest_noise_tree.json` 추가 (일반 웹 레포 노이즈 fixture).
  - `browser_extension_tree.json` 추가 (실제 확장 레포 fixture).

**검증 결과:**

- `.venv\\Scripts\\python.exe -m pytest tests/test_domain_taxonomy.py -q`
- `16 passed, 3 warnings`

---

### v7.2-upgrade (2026.05.28 — 도메인 체계 연결 보강)

**README 보조 도메인 병합 + 웹개발 라우팅 보강 + 누락 카테고리 매핑 추가.**

- **`profile_builder.py`**:
  - `README_DOMAIN_ALIAS` 추가 (`데이터 -> 빅데이터 엔지니어`, `도구개발 -> 도구 개발` 포함).
  - `README_DOMAIN_BOOST = 1` 정책 추가 (README는 보조 신호만 반영).
  - `_count_readme_domain_hits()` 신규.
  - `merge_readme_domain_hits()` 신규 — tree 기반 `domain_hits`에 README 보조치(+1) 병합.
  - `extract_readme_keywords()`는 `_count_readme_domain_hits()`를 재사용하도록 정리.
- **`github_extractor.py`**:
  - `evaluate_repository()`에서 `detect_domain_hits()` 직후 `merge_readme_domain_hits()` 호출.
  - README 키워드가 트리 신호 부재 레포에서 보조 도메인으로 반영됨.
- **`run_git2value.py`**:
  - `route_job_category()`에 "웹 개발" 분기 추가.
    - 우선순위: 풀스택 -> 웹개발+프론트 단서 -> 웹개발+백엔드 단서 -> 웹개발 단독(웹 풀스택).
  - `DOMAIN_TO_CATEGORIES` 확장:
    - `HW/임베디드 -> ["HW/임베디드"]`
    - `DBA/데이터 -> ["DBA"]`
    - `그래픽스 -> ["VR/AR/3D"]`
- **`tests/test_domain_taxonomy.py`** (신규):
  - README 보조 병합, 웹개발 라우팅, 신규 매핑, 리랭킹 분기 테스트 추가.
  - 다중 도메인 히트 근접 시 리랭킹 미적용(기존 가드) 테스트 고정.
- **`tests/fixtures/trees/frontend_mini_tree.json`** (신규):
  - `detect_domain_hits()` 고정 fixture.

**Phase 3 판단(다중 도메인 disambiguation):**

- 현재 `rerank_by_domain()`의 히트 비율 가드(`top < second * 2`)가 동작 중이라,
  v7.2-upgrade에서는 정렬 강제 규칙 추가를 **보류**.
- 동일 패턴 오분류 재현 케이스가 누적될 때만 최소 규칙 추가 예정.

---

### HandOff 갱신 (2026.05.30 — AI 리랭킹 ex2 재실험 결과·현상 유지 결정)

- **§2.1**에 `evaluate_ex2` 3-way 재실험 결과(eval_v2 n=29, comments_refined n=13, gpt_domain n=150) 및 **프로덕션 `rerank_by_domain` 유지** 결정 기록.
- 산출물: `experiments/results/comparison_all_datasets_20260530.csv`, gpt_domain 스냅샷·GPT 재학습 모델(`job_classifier_from_gpt_domain_20260530.pkl`) 경로 명시.
- §7 #30 보류 사유에 재실험 확인 내용 반영. **코드·프로덕션 파이프라인 변경 없음** (문서만).

---

### HandOff 갱신 (2026.05.19 — AI 직무 분류 리랭킹 연구 도입 보류 명시)

- **`ml/`**, **`experiments/`**, **`run_git2value_trying_reranking.py`**를 **도입 보류(Deferred)** 로 문서화.
- 에이전트용 상단 안내·§2.1·§7 #51 추가. 프로덕션 모듈 A는 **`run_git2value.py`의 `rerank_by_domain()`** 만 유효함을 명시.
- 코드 변경 없음 (문서만).

---

### v7.1 (2026.05.18 — E2E 분석 API 엔드포인트 + Git2ValuePipeline 리팩토링)

**백엔드 API화: `run_git2value.py`를 클래스 기반으로 리팩토링하고 `POST /v1/analyze` 엔드포인트 추가.**

- **`run_git2value.py`**:
  - `Git2ValuePipeline` 클래스 신규 — 인프라(FAISS·임베딩 모델·캐시·연봉 엔진·GitHub 추출기·LLM 평가기)를 `__init__()`에서 1회 로드. 이후 `analyze()` 호출마다 재로드 없음.
  - `check_llm()` 비동기 메서드 — vLLM 서버 가용 여부 확인 + `self.llm_available` 설정.
  - `analyze(username, repos, applicant_years)` 비동기 메서드 — 기존 `run_e2e_pipeline()` 로직을 **print 없이** 구현, 구조화 dict 반환. 오류 시 `{"status": "error", ...}`.
  - dict 빌더 7개 신규(`_build_github_score_dict`, `_build_per_repo_dict`, `_build_job_matching_dict`, `_build_salary_band_dict`, `_build_tech_analysis_dict`, `_build_level_dict`, `_build_summary_dict`).
  - `_build_summary_dict()` — `portfolio_diagnosis._aggregate_strengths()` / `_aggregate_quick_wins()`를 직접 호출해 `summary_block` 텍스트와 구조화 데이터(strengths, quick_wins)를 병렬 제공.
  - `_print_full_report(result, target_username, applicant_years)` 신규 — `analyze()` 반환 dict의 `_internal`에서 데이터를 꺼내 기존 CLI 보고서 형식 그대로 출력.
  - `run_e2e_pipeline()` 래퍼 전환 — `Git2ValuePipeline()` 생성 → `check_llm()` → `analyze()` → `_print_full_report()`. **기존 CLI 동작 100% 유지. `__main__` 블록 변경 없음.**
  - `import time`, `from portfolio_diagnosis import ..., _aggregate_strengths, _aggregate_quick_wins` 추가.

- **`main.py`**:
  - `from run_git2value import Git2ValuePipeline` 추가.
  - `_pipeline: Optional[Git2ValuePipeline]` 싱글톤 변수 추가.
  - `lifespan` 수정 — 앱 시작 시 `Git2ValuePipeline()` 초기화 + `check_llm()` 실행. 초기화 실패 시 `_pipeline = None`으로 graceful 처리.
  - `AnalyzeRequest` / `AnalyzeResponse` Pydantic 모델 신규 추가.
  - 입력 검증 정규식 2개 신규 (`_GITHUB_USERNAME_RE`, `_GITHUB_REPO_RE`).
  - `POST /v1/analyze` 엔드포인트 신규 — 입력 검증 → `_pipeline.analyze()` → `_internal` 제거 후 JSON 반환.
  - CORS 변경: `allow_origins=["*"]` → **명시적 출처 목록** (Vercel + localhost:3000/5173). `CORS_ORIGINS` 환경변수로 오버라이드 가능.
  - `import re` 추가.

- **변경하지 않은 파일**: `github_extractor.py`, `profile_builder.py`, `portfolio_diagnosis.py`, `valuation_engine.py`, `experience_filter.py`, `llm_readme_evaluator.py`.

---

### v7.0 이후 개선 (2026.05.15 — FastAPI 게이트웨이 + eval_readme 출력 개선)

**vLLM 연동 HTTP API 서버 추가 + CLI 출력 완전 표시.**

- **`main.py`** (신규):
  - FastAPI 기반 LLM 게이트웨이. vLLM(`localhost:8000`)과 `ReadmeEvaluator`를 HTTP API로 노출.
  - 기본 포트 **8080** (vLLM 8000과 분리). `PORT` 환경변수로 변경 가능.
  - 앱 수준 싱글톤 `ReadmeEvaluator` + **TTL 60초** health 캐시 (매 요청마다 vLLM 왕복 방지).
  - 기동 시 `lifespan`에서 vLLM 연결 사전 확인 및 로그 출력.
  - CORS 전체 허용 (`allow_origins=["*"]`) — 팀원 테스트용 (→ v7.1에서 명시적 출처 목록으로 변경).
  - 엔드포인트 3종 (→ v7.1에서 `/v1/analyze` 추가):
    | 경로 | 방식 | 입력 | 용도 |
    |------|------|------|------|
    | `GET /health` | GET | — | vLLM 연결 상태 확인 |
    | `POST /v1/readme/evaluate` | JSON body | `readme_raw` + `meta` | 프로그래밍 통합용 |
    | `POST /v1/readme/evaluate/file` | multipart form | README.md 파일 + form | 파일 직접 업로드 |
    | `POST /v1/readme/evaluate/url` | form | GitHub URL + form | GitHub URL 즉시 평가 |
  - 오류 코드 분리: 50자 미만 → **422**, vLLM 미연결 → **503**, LLM 파싱 실패 → **502**.
  - GitHub `blob` URL(`/blob/`) → `raw.githubusercontent.com` 자동 변환.
  - `readme_raw` 최대 50,000자 제한 (Pydantic `max_length`).
  - `languages` 필드를 `Dict[str, float]`로 선언 (소수점 비율 허용).
  - `/docs` Swagger UI에서 파일 업로드·URL 입력 모두 브라우저에서 직접 테스트 가능.
- **`requirements.txt`**:
  - `python-multipart>=0.0.9` 추가 (파일 업로드 엔드포인트 필수 의존성).
- **`eval_readme.py`**:
  - `reason` 출력 잘림(`[:72]`) 제거 → reason 전체 텍스트 표시.

### v7.0 이후 개선 (2026.05.14 — 동일 세션)

**LLM 평가 품질 향상 + 골든 셋 확장 + 단일 채점 CLI 추가.**

- **`llm_readme_evaluator.py`**:
  - `LLM_MAX_TOKENS`: 600 → **1000** (JSON 중간 절단으로 인한 파싱 실패 방지).
  - `SYSTEM_PROMPT` 개선 3종:
    1. **tier 경계 정수화**: `"보통" (score 2.5-3.9)` → `"양호": score 4-5 / "보통": score 3 / "미흡": score 1-2`. 소수점 경계로 인한 혼선 제거.
    2. **도메인 가중치 힌트**: 게임(visual_demo 비중↑), ML(성능 지표 인정), CLI(실행 예시 대체), 모바일(빌드 복잡성 반영), 데이터 분석(차트·결과표 인정) 5개 도메인 조건 추가.
    3. **Few-shot 예시**: 미흡·보통·양호 각 1건 대표 예시를 프롬프트 끝에 추가해 경계 케이스 일관성 향상.
  - `_build_prompt()` — 이미지 링크 `![alt](url)` → `[screenshot: alt]` placeholder로 치환 후 개수 카운트. `has_screenshots` 필드를 컨텍스트에 명시 (`"yes (N image(s) detected)"` 형식).
  - `USER_PROMPT_TEMPLATE` — `readme_raw` → `readme_clean` (이미지 치환본), `{has_screenshots}` 필드 추가.
- **`tests/test_golden_set.py`**:
  - 골든 셋 **15개 → 25개** 확장 (케이스 #16~#25 신규).
  - Case #04 · #06: `expected_tier` "보통" → "미흡", `expected_tier_range: ["미흡", "보통"]` 추가 (LLM 엄격 판정이 더 합리적).
  - Case #05: `expected_tier` "보통" → "미흡", `expected_tier_range: ["미흡", "보통"]` 추가.
  - Case #11: `expected_llm_call` `False` → `True` (fixture 파일이 실제 50자 초과).
  - 헤더·출력 문구 "15개" → "25개". 통과 기준 주석 업데이트.
- **`tests/fixtures/`** (10개 신규):
  - `16_frontend_mid_korean.md` — 한국어 프론트엔드 중간 수준 (스크린샷 1개, 실행 불완전) → 보통
  - `17_cli_tool_english.md` — CLI 도구 영문, 실행 예시 상세, 시각 없음 → 보통
  - `18_architecture_diagram.md` — 아키텍처 다이어그램 + 데모 GIF → 양호
  - `19_docker_oneclick.md` — Docker 원클릭 + 스크린샷 2개 → 양호
  - `20_data_analysis.md` — 데이터 분석, 모델 성능표 + 시각화 → 양호
  - `21_react_native_basic.md` — React Native 기초, 설명 빈약 → 미흡
  - `22_automation_script.md` — 자동화 스크립트, 설명 없음 → 미흡
  - `23_crawler_project.md` — 크롤러, 한국어, 설명+실행 있음 → 보통
  - `24_english_mid_backend.md` — 영문 중간 수준 백엔드 API → 보통
  - `25_perfect_korean_readme.md` — 한국어 완벽 README (문제정의+아키텍처+GIF) → 양호
- **`eval_readme.py`** (신규):
  - 단일 README를 LLM으로 채점하는 독립 CLI 스크립트.
  - 로컬 파일 경로 또는 GitHub raw URL 지원.
  - `--domain`, `--langs`, `--sigs`, `--repo-type` 옵션으로 meta 지정 가능 (미지정 시 Unknown 폴백).
  - `REASON_WRAP_WIDTH = 120` — reason 텍스트를 120자 단위로 줄바꿈해 출력.
  - 종합 평가 아이콘(🟢🟡🔴) + 5차원 점수 바(█░) + 개선 제안 2개 출력.

**골든 셋 검증 결과 (25개):**

| 지표            | 값               | 기준     |
| --------------- | ---------------- | -------- |
| tier 일치율     | **91% (21/23)**  | 80% 이상 |
| 1단계 이내 오차 | **100% (23/23)** | 100%     |
| JSON 파싱 오류  | 0건              | 0건      |

---

### v6.4 → v7.0 (2026.05.14)

로컬 LLM README 평가 시스템 통합. 설계 문서: `v7_0_LLM_README_Evaluation_Plan.md`.

- **`llm_readme_evaluator.py`** (신규):
  - `ReadmeEvaluator` 클래스: vLLM 서버(Qwen2.5-32B-AWQ, `localhost:8000`)와 통신.
  - `health_check()` — 서버 가용성 최초 1회 확인 후 캐시. 미가동 시 모든 평가가 룰베이스로 폴백.
  - `evaluate(readme_raw, meta)` — README(최대 3000자) + 언어/도메인/시그니처/레포타입 메타를 LLM에 전송.
  - 5차원 평가: 목적 명확성·기술 설명·실행 가이드·시각 자료·종합(tier: 양호/보통/미흡) 각 1~5점.
  - `guided_json` 강제로 파싱 실패 최소화. 모든 오류(타임아웃/HTTP오류/파싱실패) → `None` → 룰베이스.
  - `temperature=0.1`, `max_tokens=600`, `LLM_TIMEOUT=5.0초`.
- **`portfolio_diagnosis.py`**:
  - `_item()` — `llm_used`/`llm_scores`/`llm_suggestions` 파라미터 추가 (기존 호출부 하위 호환).
  - `_validate_llm_result_for_diag()` 신규 — LLM 출력 최소 스키마 검증.
  - `_readme_diagnosis_single(repo, llm_result=None)` — `llm_result` 유효 시 LLM tier·요약·제안 채택. 없으면 기존 v6.4 룰베이스.
  - `_aggregate_quick_wins()` — LLM `improvement_suggestions` 있으면 정적 풀 대신 최우선 사용.
  - `diagnose_single_repo(repo, llm_result=None)` — LLM 결과를 `_readme_diagnosis_single()`에 전달.
  - `run_diagnosis(profile, llm_results=None)` — `llm_results`(per_repo와 동일 인덱스 리스트)로 각 레포 LLM 결과 주입.
  - 모듈 docstring을 v7.0으로 갱신.
- **`run_git2value.py`**:
  - `from llm_readme_evaluator import ReadmeEvaluator` 추가.
  - Step 1에 `ReadmeEvaluator` 초기화 + `health_check()` 추가 (LLM 가용 여부 출력).
  - Step 3.5(신규): GitHub 스캔 직후, FAISS 매칭과 독립적으로 `asyncio.gather()`로 레포별 LLM README 평가 병렬 실행.
  - Step 4에 `run_diagnosis(profile, llm_results=...)` 전달.
  - `_print_readme_llm_detail()` 신규 — AI 분석 라벨 + 5차원 점수 바(█░) 출력.
  - `_print_repo_card()` — README 항목 출력 후 `_print_readme_llm_detail()` 호출.
  - 버전 표기 `v6.4` → `v7.0`.
- **`tests/`** (신규):
  - `tests/test_golden_set.py` — 15개 케이스 골든 셋 검증 스크립트.
  - `tests/fixtures/` — 골든 셋 README 샘플 15개 (README 없음·보일러플레이트·영문/한국어 완성·Unity·ML·완벽 등).

#### v7.0 설계 원칙 (변경 없는 항목)

- LLM은 Optional — 서버 다운 시 룰베이스 단독 동작. `github_score`, 모듈 A(매칭), 모듈 C(연봉)에 영향 없음.
- `expected_level()`, 등급 판정 로직은 변경 없음 — LLM이 반환하는 tier("양호"/"보통"/"미흡")가 기존 status와 동일 값 공간이므로 하위 호환.

### v6.3 → v6.4 (2026.05.13)

README 패턴 커버리지 보강 + 지배적 기여자 판정.

- **`portfolio_diagnosis.py`**:
  - `README_QUALITY_INDICATORS` 패턴 보강 (3개 차원에 각 2~3개 패턴 추가).
    - "프로젝트 목적 명시": `## About`, `## Description`, `## Summary`, `## 프로젝트 설명/소개`, `## What is` 추가.
    - "기술 스택 설명": `## Built With`, `## Requirements`, `## Dependencies`, `## 개발 환경`, `## 의존성`, `## 기술 구성` 추가.
    - "결과물 시각화": `<video>` 태그, YouTube/Vimeo 링크, `## Demo`, `## 데모`, `## Screenshots`, `## 스크린샷`, `## Preview` 섹션 헤딩 추가.
- **`github_extractor.py`**:
  - `evaluate_repository()` — `author_commit_counts: Dict[str, int]` 집계 추가. 봇/미연결 제외 후 작성자 key별 커밋 수 카운트.
  - 지배적 기여자 판정: `distinct_author_count >= 2`여도 최다 기여자 커밋 비율 `>= 0.85`이면 `repo_type = "personal"` 재판정 + `is_dominance_override = True`. 85%는 "나머지 전원 합계 < 15%" 기준.
  - 반환 dict에 `dominance_ratio` (소수점 3자리) + `is_dominance_override` 필드 추가.
  - `extract_applicant_profile()` per_repo에 `dominance_ratio` / `is_dominance_override` 전달.
- **`run_git2value.py`**:
  - `_print_repo_card()` — `is_dominance_override` 시 "개인 (작성자 N명이나 본인 기여 X%로 개인 판정)" 형식으로 표시.
  - 버전 표기 `v6.4`.

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

- 점수 공정성 피드백 4건 (나) 계열 통합 적용.

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
12. ~~모드/플러그인 플랫폼 감지~~ ✅ v5.7
13. ~~`is_config_repo` 매칭 입력 제외~~ ✅ v5.7
14. ~~시그너처 오탐 (7종)~~ ✅ v5.8
15. ~~모바일/블록체인/데이터/인프라/도구 미감지~~ ✅ v5.8
16. ~~경력직 공고 신입 상위 노출~~ ✅ v6.0 → v6.1 강화
17. ~~다중 도메인 프로젝트 균형 추천 없음~~ ✅ v6.0
18. ~~진단 항목 신뢰도 낮음~~ ✅ v6.0 7개 → v6.1 레포별 카드
19. ~~종합 행동 안내 없음~~ ✅ v6.0 → v6.1 GitHub 점수 분해 추가
20. ~~분석 레포 개수 제한 없음~~ ✅ v6.1 (`MAX_REPO_COUNT=3`)
21. ~~팀/개인 레포 판정 부정확~~ ✅ v6.1 (레포 전체 커밋 분리 수집)
22. ~~Fork 라벨이 개인/팀 판정과 섞임~~ ✅ v6.1 (별도 라벨 분리)
23. ~~커밋 리듬이 레포 전체 기준~~ ✅ v6.1 (지원자 본인 기준)
24. ~~매칭 직무와 참고 직무 혼동~~ ✅ v6.1
25. ~~참고 직무 연봉 누락 (프론트엔드 등)~~ ✅ v6.1 (직접 조회)
26. ~~봇 작성자 필터링~~ ✅ v6.2 (`_is_bot_author` + evaluate_repository 봇 제외)
27. ~~`similarity_label`에 "보통" 라벨 누락~~ ✅ v6.2 (`score >= 0.65` 분기 추가)
28. ~~`_print_extra_one_liner` dead code~~ ✅ v6.2 (개인 레포 양호 항목 표시에 활용)
29. ~~개인 레포만 있는 사용자 등급 안내 강화~~ ✅ v6.2 (`expected_level` + `generate_summary_block` 명시 안내)
30. ~~`repo_active_weeks` 사용처 정의~~ ✅ v6.2 (팀 레포 활동 기간 비율 표시에 활용)
31. ~~Fork 패널티 일괄 감산 불공정~~ ✅ v6.2 (기여 비율 기반 3단계: 0.7/0.5/0.3)
32. ~~총점 산출 LOC 가중 편중~~ ✅ v6.2 (대표 프로젝트 70% + 전체 평균 30%)
33. ~~Quality 점수 개인/팀 모순~~ ✅ v6.2 (개인 레포 활성 주 중심 + CI/CD·테스트 가산점)
34. ~~개인 레포 우수 사용자 등급 누락~~ ✅ v6.2 (`Competitive (개인)` 경로 추가)
35. ~~README 평가 패턴 커버리지 부족 (About/Built With 등 누락)~~ ✅ v6.4 (패턴 8개 추가)
36. ~~사실상 1인 프로젝트가 팀으로 오분류 (기여 1~3커밋 팀원)~~ ✅ v6.4 (지배적 기여자 85% 임계값 판정)
37. ~~LLM 도입 (로컬 Qwen2.5-32B-AWQ 등)~~ ✅ v7.0 (`llm_readme_evaluator.py` + `portfolio_diagnosis.py` 통합. vLLM 서버 Optional, 다운 시 룰베이스 폴백)
38. ~~`extract_readme_keywords()` NameError (`text_lower` 미정의)~~ ✅ v7.2-upgrade.1 (README 200자 이상 경로 런타임 오류 해소)
39. ~~`도구 개발` 저강도 신호로 인한 false mixed 빈발~~ ✅ v7.2-upgrade.1 (도메인 감지/혼합 판정 보수 처리 규칙 추가)

### 남은 항목

12. **Consistency `0.5` 계수** — 임의값. 지수 감쇠 전환 검토.
13. **`migrations/` ignore** — Django 등에서 의도한 마이그레이션이 LOC에서 제외.
14. **`DOMAIN_BOOST`(0.05) 튜닝** — 데이터 기반 조정 검토.
15. **유사도 레이블 정밀화** — 백분위 기반으로 개선 가능 (v6.2 0.65 분기는 단계적 진전).
16. **게임/정보보안 등 일부 직무** — 원티드 매핑 누락 시 점핏 단독.
17. **PR/이슈 협업 분석** — 추가 API 필요, 우선순위 낮음.
18. **공고 임베딩 재구성** — 직무명+요구기술만 추출 재임베딩.
19. **게임 포트폴리오 `expected_level` 웹 편향** — v5.4 피드백만 조정, 등급 산정 별도 검토.
20. ~~**신규 도메인 매핑**~~ ✅ v7.2-upgrade (`HW/임베디드`/`DBA/데이터`/`그래픽스` 매핑 반영)
21. **블록체인·도구 개발 공고 DB 매칭 품질** — 점핏 JD 코퍼스 보강 필요.
22. **차등 가산점 (시그너처 vs 휴리스틱)** — 정확도 측정 후 결정.
23. **리멤버 400개 데이터 처리 결정** — 신입 대상 피벗 후 분석 보류. 분석 스크립트 + 분포 확인 후 결정.
24. ~~**LLM 골든 셋 검증 실행**~~ ✅ 91% 달성 (25개 케이스, tier 일치율 21/23, 1단계 이내 오차 100%).
25. **LLM 프롬프트 A/B 테스트** — 골든 셋 확장(30개+) 후 프롬프트 변형별 일치율 비교 (v7.1 검토).
26. **커밋 메시지 품질 LLM 평가** — 현재 룰베이스 무의미 커밋 비율 판정의 정확도 한계 보완 (v7.1 검토).
27. **LLM 결과를 FAISS 키워드 압축 폴백으로 활용** — 도메인 사전 미등록 README의 매칭 개선 (v7.2 검토).
28. **`/v1/analyze` 동시 요청 제어** — GitHub API 토큰 1개 기준 2~3 요청 이내 가정 (캡스톤 데모 규모). 프로덕션 전환 시 Rate Limiter 또는 큐 도입 필요.
29. **`CORS_ORIGINS` 환경변수 미설정 시 Vercel 도메인 하드코딩** — 실제 프로덕션 배포 전 `CORS_ORIGINS` 확인 필요.
30. **AI 직무 분류 리랭킹 (`ml/` + `experiments/`)** — **도입 보류 (2026.05.30 재확인, 현상 유지)**. ex2 3-way 재실험(eval_v2·comments_refined·gpt_domain) 결과 AI 일관 우위 없음 → 프로덕션 **`rerank_by_domain` 유지**. 시험본 `run_git2value_trying_reranking.py`는 메인 미대체. 상세 수치·결정: **§2.1**. 재개 전 §2.1 체크리스트·프로덕션 로직 반영 재실험 필요. **에이전트는 당분간 본 항목을 구현 대상으로 삼지 않음.**
31. **풀스택/이중 hit primary disambiguation** — v7.2-upgrade에서 기존 히트 비율 가드 유지, 추가 규칙은 재현 데이터 축적 후 판단.
32. **직무별 독립 Portfolio Tier 산정** — 현재는 `Primary Domain Portfolio Tier` 중심. `Backend/DevOps/AI/Data` 독립 티어는 점수 규칙 분리 설계 후 단계적 도입 필요.

---

## 8. 의존성 주의사항

- `sentence-transformers==2.6.1` 버전 고정 필수
- `faiss-cpu==1.8.0` CPU 버전 유지
- `.env`에 `Github_api_token` 필요
- **외부 LLM API 의존 없음** — 분석·매칭·진단 전부 로컬 (설계 원칙)
- **v7.0 LLM 서버 (Optional)**: vLLM 서버(`localhost:8000`)가 없으면 README 평가는 룰베이스로 자동 폴백. `aiohttp==3.9.3`은 이미 `requirements.txt`에 포함.
  - 서버 실행 예시: `vllm serve Qwen/Qwen2.5-32B-Instruct-AWQ --gpu-memory-utilization 0.85 --max-model-len 8192`
  - VRAM 요건: AWQ 4bit ≈ 18GB (RTX 4090 24GB에서 6GB 여유)
- **v7.0+ FastAPI 게이트웨이 (Optional)**: `main.py` + `python-multipart>=0.0.9` 필요.
  - `pip install python-multipart` 후 `python main.py` (포트 8080).
  - 외부 접속: 방화벽 8080 포트 개방 또는 Tailscale/ngrok 터널 연결.

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

### LLM README 골든 셋 검증 (v7.0)

```bash
# vLLM 서버 실행 후:
python tests/test_golden_set.py
# tier 일치율 80% 이상, 1단계 이내 오차 100% 확인
```

### 단일 README LLM 채점 (v7.0 이후)

```bash
# 로컬 파일
python eval_readme.py path/to/README.md

# GitHub raw URL
python eval_readme.py https://raw.githubusercontent.com/user/repo/main/README.md

# meta 정보 지정 (선택)
python eval_readme.py README.md --domain 서버/백엔드 --langs "Python 80,TypeScript 20" --sigs "FastAPI,Docker" --repo-type team
```

### FastAPI LLM 게이트웨이 (v7.0+ 이후)

```bash
# 서버 실행 (기본 8080)
python main.py

# 또는 uvicorn 직접 실행
uvicorn main:app --host 0.0.0.0 --port 8080

# 환경변수로 포트·모델 변경
set PORT=8001
set VLLM_BASE_URL=http://localhost:8000/v1
python main.py
```

Swagger UI: `http://localhost:8080/docs`

| 엔드포인트                      | 설명                                              |
| ------------------------------- | ------------------------------------------------- |
| `GET /health`                   | vLLM 연결 상태 확인                               |
| `POST /v1/readme/evaluate`      | JSON body로 평가 (프로그래밍 통합용)              |
| `POST /v1/readme/evaluate/file` | README.md 파일 업로드 → 평가                      |
| `POST /v1/readme/evaluate/url`  | GitHub URL → 평가 (blob/raw 모두 가능)            |
| **`POST /v1/analyze`**          | **GitHub 포트폴리오 E2E 분석 → JSON 반환 (v7.1)** |

### E2E 분석 API 호출 (v7.1)

```bash
# 서버 실행 (포트 8080)
python main.py

# E2E 분석 요청
curl -X POST http://localhost:8080/v1/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "github_username": "siheon012",
    "repos": ["siheon012/Deepsentinel"],
    "applicant_years": 0
  }'

# 브랜치 지정 예시
curl -X POST http://localhost:8080/v1/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "github_username": "tekyung",
    "repos": [
      "Virtual-Company-Mal-Geum/ai-server/tree/tekyung",
      "tekyung/kyonggi-university_network-system-laboratory_webpage"
    ],
    "applicant_years": 1
  }'
```

**입력 제약:**

- `github_username`: 영문/숫자/`-` 조합, 1~39자
- `repos`: 1~3개. 형식: `user/repo` 또는 `user/repo/tree/branch`
- `applicant_years`: 0 이상 정수 (신입=0)

**에러 코드:**

- `400` — 입력 검증 실패 (잘못된 username / repo 형식 / 개수 초과)
- `503` — 파이프라인 초기화 실패 (서버 재시작 필요)
- `500` — 분석 중 오류 (GitHub API 한도 초과 등)

---

## 10. 외부 문서 동기 갱신

v6.1 적용 시 다음 문서들도 함께 갱신해야 함:

| 문서                        | 갱신 방향                                                                                      |
| --------------------------- | ---------------------------------------------------------------------------------------------- |
| `Git2Value_Spec_v3.md`      | Phase 7(모듈 B) 레포별 카드 진단 구조로 재작성, Phase 1-3 anti-cheating에 봇 필터링 한 줄 추가 |
| `Git2Value_논문_수정본.pdf` | 진단 구조 전환·팀/개인 분리 반영, 표 1 갱신                                                    |
| 발표 슬라이드               | 큰 변경 없음 (v6.2는 안정성·완성도 마무리 작업)                                                |

---

_Git2Value HandOff v7.2-upgrade.7 — 2026.06.01 (커밋 품질 계수 + 성장성/문서화 진단 보강)_
