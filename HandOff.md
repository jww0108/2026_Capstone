# Git2Value — 프로젝트 HandOff 문서

> 작성일: 2026.04.01 | 최종 갱신: 2026.04.06 | 현재 스펙 버전: v2.2 | 현재 구현 버전: **v5.1**

새 컨텍스트에서 이 프로젝트를 이어받을 경우 이 문서를 먼저 읽으세요.

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
  - 트리 경로 기반 도메인 시그널 감지
  - 균등 샘플링 + SHA dedup
  - 점수 산출 (contribution / quality / consistency, v5.0 수식)
        ↓
github_score + score_breakdown + per_repo + profile_for_matching
        ↓
profile_builder.build_profile_text() — JD 문체에 가까운 매칭용 텍스트
        ↓
run_git2value.py (E2E 데모)
  - FAISS + 임베딩 → 상위 5개 공고 매칭 (모듈 A)
  - portfolio_diagnosis.run_diagnosis() → 체크리스트 (모듈 B)
  - Git2ValueEngine.get_market_band() → 신입~3년 시장 밴드 (모듈 C)
```

---

## 2. 파일 구조

```
basic/
├── github_extractor.py      # GitHubExtractor (수집·점수·per_repo 집계)
├── profile_builder.py       # v4.0: 도메인 감지, 의존성 파싱, build_profile_text()
├── portfolio_diagnosis.py   # v4.0+: 진단 룰베이스 (v5.0 commit_pattern)
├── Scoring_Review.md        # 채점 로직 리뷰·v5.0 근거
├── valuation_engine.py      # v4.0: get_market_band() (멀티플라이어 제거)
├── run_git2value.py         # E2E: 모듈 A/B/C 통합 출력
├── requirements.txt         # 의존성 (sentence-transformers==2.6.1 버전 고정 중요)
├── .env                     # Github_api_token 환경변수 (버전 관리 제외)
├── Git2Value_Spec_v2.md     # 스펙 문서 v2.1 (설계 기준)
├── HandOff.md               # 이 파일
├── Plan3.md                 # v4.0 설계(Phase 4.0) 참고
│
├── vector/
│   ├── git2value_faiss.index
│   ├── git2value_metadata.json
│   ├── unified_jd_corpus.jsonl
│   └── wanted_job_ids.json
│
├── data/
│   ├── jumpit_data/
│   ├── wanted_data/
│   └── ...
│
├── kaggle/   (비활성, 무시)
└── used/     (비활성, 무시)
```

---

## 3. 핵심 파일별 역할

### `github_extractor.py` — GitHubExtractor 클래스

| 메서드                           | 역할                                                                       |
| -------------------------------- | -------------------------------------------------------------------------- |
| `_fetch_with_retry`              | 모든 API 호출 게이트. 403/429 시 Retry-After 파싱 + 지수 백오프 (최대 3회) |
| `_fetch_repo_text_files`         | **v4.0** 의존성 파일 등 contents API로 텍스트 조회                           |
| `_fetch_all_commits_paginated`   | author 필터 커밋 목록 수집. `MAX_COMMIT_PAGES=3` (최대 300커밋) 상한       |
| `_stratified_sample_commits`     | 초기/중간/최근 각 최대 25개씩, 레포 내부 + 전역 SHA dedup                  |
| `_cicd_and_test_ratio_from_tree` | tree blob size>200B로 CI/CD 실질성 판별, 테스트 파일 비율 계산             |
| `_count_active_weeks`            | **v5.0** author 커밋 목록 기준 ISO 주(년+주차) 개수                          |
| `_calc_consistency_score`        | 커밋 간격 표준편차 → `max(0, 10 - std * 0.5)`. **v5.0** 전체 목록 기준       |
| `evaluate_repository`            | 레포 1개 완전 분석. frameworks, detected_domains, tree_stats, active_weeks |
| `extract_applicant_profile`      | LOC 가중 github_score + **`profile_for_matching`** + **`per_repo`**        |

**클래스 상수:** `MAX_COMMIT_PAGES = 3`

**환경변수:** `Github_api_token`

---

### `profile_builder.py` — v5.1

- `detect_domain_hits` / `merge_domain_hits`: 트리 경로 기반 도메인 히트
- `find_dependency_paths` / `parse_dependency_contents`: package.json 등에서 프레임워크 라벨 추출
- `has_deployment_signals`: docker-compose, Vercel 등 배포 시그널
- `compute_tree_structure_stats`: 파일당 평균 LOC, `.gitignore` 여부
- `build_profile_text`: FAISS 질의용 공고형 문장 생성
- `readme_length_tier`: README 잔량 분기 (long/medium/short)
- **`README_KEYWORDS`**: 도메인별 키워드 사전 (게임/웹/서버/ML·AI/모바일/인프라) — v5.1
- **`extract_readme_keywords(readme_text)`**: README 원문 대신 도메인 키워드 압축 문장 반환. 키워드 없으면 빈 문자열 → `build_profile_text`에서 원문 300자 폴백 — v5.1

---

### `portfolio_diagnosis.py` — v4.0+

- `run_diagnosis(profile)`: README, 구조, 테스트, CI/CD, 커밋 메시지, **커밋 리듬(commit_pattern)**, 배포, 협업, 성장 궤적
- `expected_level`: Entry / Competitive / Top (룰베이스)

---

### `valuation_engine.py` — Git2ValueEngine (v4.0)

- `data/jumpit_data/korean_it_salary_lookup_2025.py` 동적 로드
- **`get_market_band(job_category, years_max=3)`**: 신입(0~3년) 구간, 점핏 junior P50 + 원티드 JSON(매핑 시) 교차 → `combined_range` 문자열
- **`calculate_valuation` 제거** (멀티플라이어·추천 연봉 단일값·가짜 백분위 제거)
- `JUMPIT_TO_WANTED_FILE`: 점핏 직무명 → `data/wanted_data/salary_data/*.json`

---

### `run_git2value.py` — E2E 파이프라인 (v5.1)

- FAISS 인덱스(`vector/`) + `jhgan/ko-sroberta-multitask`
- 임베딩 입력: **`profile_for_matching`** (없으면 `applicant_resume` 폴백)
- 최종 출력: **모듈 A**(매칭+패턴) / **모듈 B**(진단) / **모듈 C**(연봉 밴드) 분리
- `route_job_category()`: 1순위 공고 제목 → 점핏 카테고리. **v5.1에서 `"게임 클라이언트"` / `"게임 서버"` 분기 추가** (일반 서버/백엔드 규칙보다 앞에 위치)
- **`DOMAIN_TO_CATEGORIES`**: `detected_domains[0]` → 기대 점핏 카테고리 목록 매핑 — v5.1
- **`merged_detected_domains_from_profile(profile)`**: `per_repo` 전체의 `detected_domains`를 빈도순 병합 — v5.1
- **`check_domain_match_consistency(detected_domains, top_matches)`**: 도메인 감지 vs FAISS 라우팅 비교 → `consistent / warning / suggested_category` 반환 — v5.1
- **`similarity_label(score)`**: 정규화 코사인 유사도 → 높음(≥0.75) / 보통(≥0.60) / 낮음 레이블 — v5.1
- **모듈 A 출력**: 유사도 옆 레이블 표시, 도메인 불일치 시 경고 + 권장 직무 안내 — v5.1
- **모듈 C 출력**: 도메인 불일치 시 `suggested_category` 기준 보조 연봉 밴드 추가 출력 — v5.1

---

## 4. 점수 산출 수식 (github_score, 진단 참고용) — **v5.0**

상세 근거: [`Scoring_Review.md`](Scoring_Review.md)

### Contribution (최대 60점)

로그 스케일로 변별력 확보 (선형 만점 LOC·커밋 제거).

```python
import math
loc_score    = min(100, math.log(valid_loc / 100 + 1) / math.log(101) * 100)
commit_score = min(100, math.log(analyzed_count / 5 + 1) / math.log(21) * 100)
blend_100    = loc_score * 0.7 + commit_score * 0.3
contribution_axis = (blend_100 / 100) * 60
```

- Fork 시 contribution에만 0.3배 패널티 (기존과 동일)

### Quality (최대 30점)

**CI/CD 10 + 테스트 10 + 활성 주 10** — `min(30)` 캡 제거, duration 일수 대신 **활성 ISO 주** 사용.

| 항목 | 조건 | 점수 |
|------|------|------|
| CI/CD | 워크플로우/Dockerfile blob > 200B | 10 또는 0 |
| 테스트 비율 | &lt; 5% | 0 / 5~20% → 5 / ≥20% → 10 |
| 활성 주 수 | `all_author_commits`에서 커밋이 있는 ISO 주 개수 | ≥8주 → 10, ≥4주 → 5, 그 외 0 |

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

---

## 5. 출력 JSON 스키마 (v4.0 `extract_applicant_profile` 확장)

### 추가·변경 필드

```json
{
  "github_score": 79.3,
  "score_breakdown": { "contribution": 42.0, "quality": 28.0, "consistency": 9.3 },
  "applicant_resume": "주요 기술 스택: … (레거시 미리보기용)",
  "profile_for_matching": "Python 기반 서버/백엔드 경험. FastAPI 활용 경험. …",
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
      "is_fork": false,
      "duration_days": 90,
      "active_weeks": 12,
      "total_commits": 80,
      "frameworks": ["FastAPI"],
      "detected_domains": ["서버/백엔드"]
    }
  ],
  "metrics_summary": { … },
  "warnings": [ … ]
}
```

---

## 6. 버전 이력 및 주요 결정 사항

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

## 7. 알려진 미해결 사항 (v5.1 이후 과제)

1. ~~**스펙 문서와 구현 불일치**~~ ✅ v3.0~v2.2에서 정합
2. ~~**순차 레포 평가 성능**~~ ✅ v3.0 병렬화
3. ~~**run_git2value 연결 미완성**~~ ✅ v3.0
4. ~~**FAISS 입력 비대칭**~~ ✅ v4.0 1차 완화 → ✅ v5.1 README 키워드 압축으로 추가 완화
5. ~~**연봉 멀티플라이어 근거 부족**~~ ✅ v4.0 밴드 독립 제공
6. ~~**Contribution 선형 만점·변별력 부족**~~ ✅ v5.0 로그 스케일로 완화 (튜닝은 계속 가능)
7. ~~**Quality duration 편중·CI·테스트 무력화**~~ ✅ v5.0 균등 10+10+10·활성 주
8. ~~**게임 카테고리 라우팅 누락**~~ ✅ v5.1 `route_job_category()`에 게임 클라이언트/서버 분기 추가
9. ~~**FAISS 유사도 레이블 없음**~~ ✅ v5.1 절대값 임계치 기반 높음/보통/낮음 구현 (분포 기반 정밀 튜닝은 추후)
10. ~~**도메인 불일치 감지 없음**~~ ✅ v5.1 `check_domain_match_consistency()` + 경고 출력
11. **Consistency `0.5` 계수** — 여전히 임의값; 지수 감쇠 등 데이터 기반 튜닝 예정
12. **`migrations/` ignore** — Django 등에서 의도한 마이그레이션 코드가 LOC에서 제외됨; 필요 시 경로 조정
13. **유사도 임계치 정밀화** — 현재 절대값(0.75/0.60) 기반; 전체 메타데이터 분포 분석 후 백분위 기반으로 개선 예정
14. **게임/정보보안 등 일부 직무** — 원티드 JSON 매핑 없으면 `wanted_median` null, 점핏만으로 구간 표시
15. **PR/이슈 협업 분석** — 추가 API 필요, 우선순위 낮음 ([`Scoring_Review.md`](Scoring_Review.md))

---

## 8. 의존성 주의사항

- `sentence-transformers==2.6.1` 버전 고정 필수
- `faiss-cpu==1.8.0` CPU 버전 유지
- `.env`에 `Github_api_token` 필요

---

## 9. 실행 방법

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
