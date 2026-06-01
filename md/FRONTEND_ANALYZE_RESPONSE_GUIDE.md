# Git2Value `/v1/analyze` 응답 항목 가이드 (프론트 전달용)

이 문서는 프론트엔드가 `POST /v1/analyze` 응답을 안정적으로 소비하기 위한 필드 설명서다.
백엔드 응답을 신뢰한다는 전제에서, 가능한 많은 케이스를 처리할 수 있도록
`nullable`, `누락 가능성`, `표시 우선순위`를 함께 명시한다.

동기화 기준:
- `HandOff.md` (최종 갱신 2026.05.30)
- `Git2Value_Spec_v4.md` (Specification v4.0)

기준 코드:
- `main.py` (`AnalyzeRequest`, `AnalyzeResponse`, `/v1/analyze`)
- `run_git2value.py` (`Git2ValuePipeline.analyze`, `_build_*_dict`)

---

## 1) 엔드포인트 계약

- URL: `POST /v1/analyze`
- Request JSON:
  - `github_username: string` (필수)
  - `repos: string[]` (필수, 1~3개)
  - `applicant_years?: number` (기본 0)

### HTTP 상태 코드

- `200`: 분석 성공 (`AnalyzeResponse`)
- `400`: 입력 검증 실패 (아이디/레포 포맷/개수)
- `500`: 분석 파이프라인 내부 오류 (`result.status == "error"`)
- `503`: 서버 초기화 실패(파이프라인 미구동)

주의:
- 백엔드는 내부적으로 `result.status == "error"`를 그대로 내려주지 않고 `HTTP 500`으로 변환한다.
- 즉 프론트는 `200` 응답에서 `status=success`를 기대하면 된다.

---

## 2) 최상위 응답 구조

```json
{
  "status": "success",
  "error": null,
  "github_score": {},
  "per_repo": [],
  "level": {},
  "summary": {},
  "job_matching": {},
  "salary_band": {},
  "tech_analysis": {},
  "meta": {}
}
```

### 최상위 필드 의미

- `status: string`
  - 성공 시 `"success"`.
- `error: string | null`
  - 성공 시 `null`.
- `github_score: object | null`
  - 종합 점수 블록.
- `per_repo: object[] | null`
  - 레포별 상세 카드 데이터.
- `level: object | null`
  - 등급/설명.
- `summary: object | null`
  - 요약 문장 + 강점/퀵윈.
- `job_matching: object | null`
  - 매칭 공고/도메인 일치 정보.
- `salary_band: object | null`
  - 연봉 밴드.
- `tech_analysis: object | null`
  - 기술 매칭 결과.
- `meta: object | null`
  - 버전, 분석시간 등 메타.

중요:
- API 응답에는 `_internal` 필드가 포함되지 않는다(백엔드에서 제거 후 반환).
- 모듈 A 정책은 현재 **룰 기반 리랭킹(`rerank_by_domain`) 고정**이며,
  AI 직무 분류 리랭킹(`ml/`, `experiments/`)은 연구 전용(도입 보류)이다.

---

## 3) `github_score`

- `total: number`
  - 최종 점수(0~100 스케일).
- `method: string`
  - 점수 계산 방식 설명 문자열.
- `breakdown: object`
  - 보통 `contribution`, `quality`, `consistency`.
- `breakdown_note: string`
  - breakdown 기준 설명(예: 최고 레포 기준).

프론트 권장:
- `total` 큰 숫자 카드.
- `breakdown` 막대 그래프.
- `method`/`breakdown_note`는 툴팁.

---

## 4) `per_repo[]` (핵심)

각 원소는 레포 카드 하나다.

### 식별/분류

- `repo_name: string`
- `repo_type: "team" | "personal"`
- `has_team_experience: boolean`
  - 티어 산정용 팀 경험 플래그.
- `distinct_author_count: number`
- `repo_author_names: string[]`

### 협업/기여 관련

- `target_commit_count: number`
- `total_repo_commits: number`
- `target_commit_ratio: number | null`
- `target_commit_ratio_census: number | null`
- `contribution_role: "주도 기여" | "적극 기여" | "협업" | null`
  - 팀 레포가 아닌 경우 `null` 가능.
- `dominance_ratio: number | null`
- `is_dominance_override: boolean`

### 점수/활동

- `repo_total_score: number | null`
- `score_breakdown: object | null`
- `active_weeks: number`
- `repo_active_weeks: number`
- `is_fork: boolean`
- `fork_penalty: number | null`

### 기술/도메인

- `detected_domains: string[]`
- `frameworks: string[]`
- `language_category: object | null`
  - `main/sub/trivial` 구조.

### 진단 블록

- `diagnosis.core_items: object`
  - `readme_quality`, `project_structure`, `commit_quality`.
- `diagnosis.extra_items: object`
  - `test_coverage`, `cicd`, `deployment`, `commit_pattern`.

각 항목 기본 형태:
- `status: string`
- `detail: string`
- `action: string | null`

프론트 권장:
- 카드 제목: `repo_name`.
- 서브 라벨: `repo_type`, `has_team_experience`, `contribution_role`.
- `is_dominance_override && has_team_experience`면
  "팀 경험 있음(배점은 개인 기준)" 안내 배지 표시.

---

## 5) `level`

- `grade: string`
  - 예: `Entry`, `Competitive`, `Top`, `Competitive (개인)`.
- `description: string`
  - 등급 설명 문장.

프론트 권장:
- `grade`를 강조 배지.
- `description`을 보조 문구.

---

## 6) `summary`

- `text: string`
  - 백엔드 생성 종합 블록 원문.
- `positioning: string`
  - 포지셔닝 문장 추출값(없을 수 있음).
- `strengths: string[]`
- `quick_wins: string[]`

프론트 권장:
- `strengths`/`quick_wins` 리스트 UI 우선.
- `text`는 접기/펼치기 영역.

---

## 7) `job_matching`

- `primary_domain: string | null`
- `detected_domains: string[]`
- `rerank_note: string`
  - 도메인 리랭킹/미적용 사유를 설명하는 사용자 표시용 문장.
- `is_multi_domain: boolean`
- `eligible_matches: object[]`
  - 각 항목:
    - `rank: number`
    - `position: string`
    - `company_name: string`
    - `category: string`
    - `similarity: number`
    - `effective_score: number`
    - `domain_boosted: boolean`
    - `similarity_label: string`
    - `experience_warning: string | null`
- `domain_mismatch: object | null`
- `domain_check: object`
- `multi_domain_picks: object | null`
- `jumpit_category: string`
- `company_types: string[]`

프론트 권장:
- `eligible_matches`를 정렬된 카드/테이블로 표시.
- `domain_mismatch != null`이면 경고 배너.
- `rerank_note`는 모듈 A 결과 설명의 1순위 문장으로 노출 권장.

---

## 8) `salary_band`

- `matched_category: string`
- `experience_level: string`
- `salary_range: object`
  - `jumpit_median: number | null`
  - `wanted_median: number | null`
  - `combined_range: string`
- `realistic_range: object`
- `source: string`
- `note: string`
- `reference_categories: {category, combined_range}[]`
- `alt_category_band: object | null`

프론트 권장:
- `combined_range`와 `realistic_range`를 메인으로.
- `reference_categories`는 아코디언/보조표시.

---

## 9) `tech_analysis`

- `matched_techs: string[]`
- `missing_techs: string[]`
- `learning_suggestions: string[]`
- `company_types: string[]`

프론트 권장:
- `matched_techs`는 긍정 태그.
- `missing_techs`는 개선 태그.

---

## 10) `meta`

- `version: string`
  - 현재 구현 기준 `v7.2-upgrade.4`.
- `llm_available: boolean`
- `analysis_time_seconds: number`
  - `main.py`에서 최종 덮어씀(실제 API 왕복 처리 시간에 가까움).
- `repos_analyzed: number`
- `applicant_years: number`

프론트 권장:
- `version`은 디버그 패널에 표시.
- 사용자 노출은 `analysis_time_seconds` 정도만 간단 표기.

---

## 11) 프론트 방어 처리 권장 규칙

백엔드 신뢰 전제에서도 UI 안정성을 위해 아래는 권장:

- 배열 필드: `null`이면 빈 배열로 렌더.
- 객체 필드: `null`이면 섹션 숨김.
- 숫자 필드: `null`이면 `"데이터 없음"` 표기.
- `contribution_role`:
  - `null`이면 개인 레포/역할미산출로 처리.
- `status != "success"`는 이론상 `200`에서 안 오지만,
  - 혹시 오면 공통 오류 토스트 + `error` 표시.

---

## 12) 운영 정책 반영 메모 (프론트 공통 문구 기준)

- 현재 운영 기준(2026.05.30):
  - **직무 매칭 리랭킹은 룰베이스(`rerank_by_domain`) 사용**
  - AI 리랭킹은 사용자 응답에 직접 노출되는 운영 경로가 아님
- 따라서 프론트 메시지/툴팁도 아래처럼 유지 권장:
  - "도메인 감지 기반 리랭킹"
  - "혼합 도메인 판단 시 리랭킹 미적용 가능"

---

## 13) 참고 파일

- 예시 응답 JSON: `analyze_response_v7_2_example.json`

