# Git2Value — 시스템 기술 명세서

**Specification Document v4.0**

> 버전: v4.0 (v3.0 대체) | 작성일: 2026.05.30 | 대상 사용자: 채용 기업 / 구직자 본인 / 개발 팀  
> 적용 시스템 버전: v7.2-upgrade.4  
> 동기화 기준 문서: `HandOff.md` (최종 갱신 2026.05.30)

---

## 0. 변경 이력

### v3.0 → v4.0 핵심 변경 (2026.05.02 ~ 2026.05.30)

본 문서는 v3.0(2026.05.02) 이후의 구현/운영 기준을 반영해 갱신한 명세서입니다.

| 영역 | v3.0 → v4.0 변경 요지 |
| --- | --- |
| 아키텍처 | `run_git2value.py`에 `Git2ValuePipeline` + `analyze()` 단일 진입점 정립 (v7.1) |
| API | `main.py` FastAPI 게이트웨이 기준 운영 (`/v1/analyze`) |
| 진단 | README LLM 평가 모듈 도입 (`llm_readme_evaluator.py`) + 골든셋 검증 체계 추가 |
| 팀 경험 판정 | 작성자 판정 전수 경로(`MAX_CENSUS_PAGES`)와 점수 경로(`MAX_COMMIT_PAGES`) 분리 |
| 모듈 A 정책 | AI 직무 분류 리랭킹은 연구 전용 유지, 프로덕션은 `rerank_by_domain()` 고정 |
| 실험 결론 | 2026.05.29~30 ex2 재실험 후 **현상 유지** 결정 (AI 전면 교체 보류) |

### 버전 매핑 (요약)

| 구현 버전 | 적용일 | 핵심 변경 |
| --- | --- | --- |
| v7.0 | 2026.05.14 | LLM README 평가 모듈 도입, FastAPI 기반 확장 준비 |
| v7.1 | 2026.05.18 | `Git2ValuePipeline` 클래스 + `/v1/analyze` 경로 정리 |
| v7.2-upgrade | 2026.05.28 | 도메인 체계 연결 보강 |
| v7.2-upgrade.1~.4 | 2026.05.29 | 과검출 완화, 작성자 전수 조사 분리, 팀 경험 플래그 정합화 |

---

## 1. 시스템 개요

Git2Value는 **신입(0~3년) 개발자**의 GitHub 포트폴리오를 분석해 아래 3개 모듈을 독립 제공하는 파이프라인이다.

- **모듈 A (직무 매칭)**: FAISS 임베딩 매칭 + 도메인 리랭킹/균형 추천
- **모듈 B (포트폴리오 진단)**: 레포별 카드 진단 + 종합 분석
- **모듈 C (시장 연봉 밴드)**: 직무별 신입 연봉 구간 및 인접 직무 비교

핵심 원칙은 다음과 같다.

- 모듈 독립성: 한 모듈 오류가 다른 모듈 결과를 오염시키지 않음
- 설명 가능성: 리랭킹/진단 근거를 텍스트로 추적 가능
- 외부 의존 최소화: GitHub API 외 외부 분석 API 의존을 최소화

---

## 2. 현재 파일 구조 기준 (v7.2-upgrade.4)

### 2-1. 프로덕션 핵심 경로

- `github_extractor.py`: 수집·점수·per_repo 집계
- `profile_builder.py`: 도메인/시그니처 감지 + 매칭용 프로필 텍스트 구성
- `run_git2value.py`: E2E 파이프라인(`Git2ValuePipeline.analyze()`)
- `portfolio_diagnosis.py`: 진단 항목 계산 + 종합 분석
- `valuation_engine.py`: 시장 연봉 밴드 조회
- `experience_filter.py`: 경력 조건 필터
- `main.py`: FastAPI 게이트웨이 (`/v1/analyze`)

### 2-2. 연구 전용(도입 보류) 경로

- `ml/`
- `experiments/`
- `run_git2value_trying_reranking.py`

이 경로들은 프로덕션 기본 범위에 포함하지 않는다.

---

## 3. 모듈별 동작 명세 (요약)

## Phase 1. Input & Validation

- 입력: `username`, `repos[]`(최대 3개 권장), `applicant_years`
- 인증: `Github_api_token`
- 비정상 입력/비공개 레포/수집 실패는 경고와 함께 안전 폴백

## Phase 2. Data Fetching

- 레포 단위 비동기 수집 + 재시도(403/429 대응)
- 커밋 데이터 분리 수집:
  - 점수 계산용 author 커밋
  - 팀/개인 판정용 전수 커밋(census)

## Phase 3. Feature & Context Build

- README 정제, 언어 비중 집계, 프레임워크 추출
- 트리 시그니처 기반 도메인/환경 감지
- `profile_for_matching`, `domain_hits_merged`, `detected_domains` 생성

## Phase 4. Scoring

- contribution / quality / consistency 스코어 산출
- 레포 단위 결과를 사용자 단위로 집계해 `github_score` 생성

## Phase 5. 모듈 A (직무 매칭)

1. 임베딩 기반 FAISS 후보 검색(k=20)
2. 경력 요건 필터링
3. `rerank_by_domain()` 적용 또는 `recommend_multi_domain()` 분기

`rerank_by_domain()` 핵심 정책:

- 도메인 미감지 시 FAISS 순서 유지
- 다중 도메인 히트 비율이 근접하면 리랭킹 미적용
- 해당 직무 공고가 Top-k에 없으면 가산 미적용
- 조건 충족 시 `DOMAIN_BOOST=0.05` 가산

## Phase 6. 모듈 B (포트폴리오 진단)

- 레포별 카드 진단 + 종합 요약 생성
- 팀 경험 관련 필드(`has_team_experience`, `target_commit_ratio_census`, `contribution_role`) 반영

## Phase 7. 모듈 C (시장 연봉 밴드)

- 점핏/원티드 기반 직무별 신입 구간 조회
- 인접 직무 비교와 함께 표시
- GitHub 점수 기반 연봉 배수(multiplier) 적용은 사용하지 않음

---

## 4. AI 직무 분류 리랭킹 상태 (HandOff 동기화)

> 상태: **도입 보류(Deferred) 유지**  
> 기준 결정일: **2026.05.30**  
> 결론: 프로덕션은 `run_git2value.py`의 `rerank_by_domain()` **현상 유지**

### 4-1. 실험 범위

`experiments/evaluate_ex2.py` 기준 3-way 비교:

- `faiss_only`
- `domain_rerank`
- `ai_classifier_rerank`

평가셋:

- `eval_v2` (n=29)
- `comments_refined` (n=13)
- `gpt_domain` 스냅샷 (n=150)

### 4-2. Top-1 결과 (%)

| 평가셋 | FAISS only | domain_rerank | AI rerank (base) | AI rerank (GPT 재학습) |
| --- | ---: | ---: | ---: | ---: |
| eval_v2 | 44.8 | 62.1 | **75.9** | 44.8 |
| comments_refined | 53.8 | **76.9** | 61.5 | - |
| gpt_domain | 1.3 | **10.7** | 7.3 | 10.7 |

### 4-3. 결정 근거

1. 평가셋별 승자가 달라 AI의 일관 우위가 확인되지 않음  
2. ex2의 `domain_rerank`와 프로덕션 `rerank_by_domain()`는 로직이 완전히 동일하지 않음  
3. 학습 표본/라벨 정합성/일반화 리스크가 여전함  
4. 프로덕션 룰은 다중 도메인 가드와 설명 가능성이 높고 운영 리스크가 낮음

### 4-4. 운영 규칙

- 기본 구현/리팩토링 범위에서 `ml/`, `experiments/`, `run_git2value_trying_reranking.py`는 제외
- AI 경로는 문서화·연구 재현 요청 시에만 접근
- 모듈 A 대체가 아니라 하이브리드 검토를 전제로 후속 실험 설계

---

## 5. API/출력 명세 요약

### 5-1. 분석 API

- 엔드포인트: `POST /v1/analyze`
- 반환: 모듈 A/B/C 결과 + 내부 진단 필드(`_internal`)를 포함한 구조화 응답

### 5-2. 리포팅 필드(핵심)

- `job_matching`: 상위 매칭, 리랭킹 노트, 다중 도메인 추천 정보
- `portfolio_diagnosis`: 레포별 카드 및 종합 분석
- `market_band`: 현실 구간 및 인접 직무 비교

---

## 6. 운영 제한 및 리스크

- GitHub API rate limit/네트워크 상태에 따라 일부 레포 수집 실패 가능
- 신입(0~3년) 중심 설계로 경력직 분석 일반화 한계 존재
- 도메인 체계와 채용공고 카테고리 체계 불일치 시 매칭 품질 저하 가능

---

## 7. 유지보수 규칙

1. `HandOff.md`와 스펙 문서는 메이저 의사결정(정책/도입 여부 변경) 시 동시 갱신
2. 프로덕션 정책 변경 시, 실험값 단순 인용이 아니라 프로덕션 로직 재검증을 선행
3. AI 리랭킹 도입 재개 전 최소 조건:
   - 프로덕션 로직 반영된 동일 조건 재실험
   - 모델/특징 컬럼 버전 고정
   - 데이터셋 분리(학습/검증/운영)와 라벨 정합성 확보

---

_Git2Value Specification v4.0 — 시스템 기술 명세서 — 2026.05.30_
