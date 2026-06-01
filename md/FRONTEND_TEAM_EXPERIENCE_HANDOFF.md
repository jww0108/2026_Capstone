# Frontend Handoff — 팀 경험/개인 기여 분리 변경

대상 API: `POST /v1/analyze`  
적용 버전: 백엔드 `meta.version = "v7.2"`

---

## 1) 변경 배경

이전에는 `repo_type` 하나로 두 가지를 같이 표현했다.

1. 배점 기준(개인 모드/팀 모드)
2. 팀 경험 존재 여부(티어 경로 계산)

문제:
- 지배적 기여(`is_dominance_override=true`)가 걸리면 `repo_type="personal"`로 내려가며,
- 팀 경험이 실제로 있어도 UI/티어에서 팀 경험이 사라지는 부작용 발생.

현재는 팀 경험 신호를 분리했다.

---

## 2) 핵심 변경 요약

### A. `repo_type` 의미
- 여전히 배점 기준 필드로 사용.
- 값: `"team"` 또는 `"personal"`.
- 지배적 기여 조건에서 `"personal"`로 재판정될 수 있음.

### B. 신규/강화 필드
- `has_team_experience: boolean`
  - 팀 경험 여부 전용 플래그.
  - `distinct_author_count >= 2` 기반.
- `is_dominance_override: boolean`
  - 지배적 기여로 개인 재판정되었는지.
- `dominance_ratio: number | null`
  - 지원자 기준 기여 비율(0~1).
- `target_commit_ratio_census: number | null`
  - 전수 기준 지원자 커밋 비율.
- `contribution_role: "주도 기여" | "적극 기여" | "협업" | null`
  - 팀 레포 컨텍스트 역할 라벨.

### C. 서버 응답 구조
- 엔드포인트/상위 키는 그대로.
- `per_repo[]` 안에 위 필드가 포함되어 내려옴.
- `_internal`은 서버에서 제거되므로 프론트에는 오지 않음.

---

## 3) 프론트 렌더링 규칙 (권장)

프론트는 아래 우선순위로 표시하면 안정적이다.

1. `is_dominance_override && has_team_experience`
   - 라벨: `팀 경험 레포 · N명 중 주도 기여 (X%) · 배점: 개인 기준`
   - 의미: 팀 경험은 인정, 점수 배점은 개인 모드.

2. `repo_type === "team"`
   - 라벨: `팀 레포 · N명 중 {contribution_role} (X%)`
   - `contribution_role`가 null이면 ratio 기반 fallback 계산 가능:
     - `ratio >= 0.5` -> 주도 기여
     - `ratio >= 1/distinct` -> 적극 기여
     - else -> 협업

3. 그 외
   - 라벨: `개인 레포`

보조 배지:
- `has_team_experience=true` -> `팀 경험 있음`
- `is_dominance_override=true` -> `지배적 기여`

---

## 4) 필드별 프론트 처리 가이드

### `per_repo[].repo_type`
- 타입: `"team" | "personal"`
- 용도: 배점 해석/기본 라벨.
- 주의: 팀 경험 여부 자체를 완전히 대표하지 않음.

### `per_repo[].has_team_experience`
- 타입: `boolean`
- 용도: 티어 경로 설명, 팀 경험 UI 배지.
- 권장: 팀 경험 관련 UI/문구는 이 값 우선.

### `per_repo[].is_dominance_override`
- 타입: `boolean`
- 용도: 개인 재판정 발생 여부.
- 권장: true이면 설명 툴팁 제공.

### `per_repo[].dominance_ratio`
- 타입: `number | null` (0~1)
- 용도: 지배적 기여 설명 비율.
- 권장: `%` 표기 시 `Math.round(ratio * 100)`.

### `per_repo[].target_commit_ratio_census`
- 타입: `number | null` (0~1)
- 용도: 역할 라벨 및 협업 비율 표시.

### `per_repo[].contribution_role`
- 타입: 문자열 또는 null
- 권장:
  - team이면 보여주고,
  - personal이면 null 허용.

---

## 5) 티어/요약 화면 주의사항

- 티어는 백엔드 계산 결과(`level.grade`, `level.description`)를 그대로 신뢰.
- 프론트에서 `repo_type`만 보고 티어를 재추론하지 말 것.
- 팀 경험 안내는 `has_team_experience` 기반으로 표시.

---

## 6) QA 체크리스트 (프론트)

아래 3케이스 카드/배지/문구 확인:

1. `repo_type=personal`, `has_team_experience=true`, `is_dominance_override=true`
   - 기대: "팀 경험 있음" + "배점: 개인 기준" 설명.

2. `repo_type=team`, `contribution_role=협업`
   - 기대: 팀 레포 카드 + 협업 비율 표기.

3. `repo_type=personal`, `has_team_experience=false`
   - 기대: 일반 개인 레포 카드.

공통:
- `dominance_ratio`, `contribution_role` null이어도 렌더 에러 없어야 함.
- 숫자 null은 `"데이터 없음"`으로 표시.

---

## 7) 하위 호환성

- 기존 상위 응답 키(`github_score`, `per_repo`, `level`, `summary`, `job_matching`, `salary_band`, `tech_analysis`, `meta`) 유지.
- 신규 필드는 `per_repo` 내부 확장이라 기존 소비 로직을 깨지 않음.
- `meta.version`은 `v7.2`.

---

## 8) 프론트 구현 팁

- `per_repo` 카드 컴포넌트에 다음 우선 맵핑 함수 추가 권장:
  - `getRepoDisplayType(repo)`
  - `getContributionBadge(repo)`
  - `formatRatio(repo.target_commit_ratio_census ?? repo.target_commit_ratio)`

필수 원칙:
- `repo_type` = 배점 컨텍스트
- `has_team_experience` = 팀 경험 컨텍스트
- 둘을 분리해서 UI 설계

