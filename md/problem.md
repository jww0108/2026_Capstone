# Git2Value Frontend — 구조·설계 점검 사항

Last updated: 2026-05-27

이 문서는 프로젝트 구조와 설계를 다방면으로 점검한 결과를 정리한 것이다.  
`handoff.md`가 현재 상태를 설명한다면, 이 문서는 **잠재 문제·리스크·개선 우선순위**를 기록한다.

---

## 종합 평가

| 항목 | 평가 |
|------|------|
| 전체 구조 | 양호 — mock UI에서 실 API UI로 전환 잘 됨 |
| 타입/매퍼 분리 | 양호 — `api.ts` → `mapAnalyzeResponse` → `analysis.ts` → pages 흐름 명확 |
| 상태 관리 | 양호 — `AnalysisContext` + sessionStorage로 결과 페이지 공유 |
| 확장성 | 주의 — 매퍼 비대화, UI 데이터 폭발 가능 |
| 운영 안정성 | 주의 — timeout 없음, runtime 검증 없음 |

캡스톤 데모·실사용 MVP 수준으로는 충분하나, API 필드 추가·응답 크기 증가가 계속되면 한계에 도달할 수 있다.

---

## 1. 높은 우선순위 (High)

### 1-1. 런타임 JSON 검증 없음

**현상**  
TypeScript 타입(`AnalyzeResponse`)은 컴파일 타임에만 동작한다. 실제 API 응답이 스키마와 다르면 런타임에서 예외가 발생할 수 있다.

**위험 시나리오**
- `salary_band.realistic_range` 누락
- `per_repo[].language_category.main` 누락
- `eligible_matches[].effective_score`가 문자열로 옴
- `diagnosis.extra_items.commit_pattern` 구조 변경

**관련 파일**
- `src/lib/mapAnalyzeResponse.ts`
- `src/types/api.ts`

**권장 조치**  
백엔드 스키마가 안정되기 전까지 `zod` 등 runtime parser 도입. 필수 필드 누락 시 graceful fallback 또는 사용자 친화적 에러 메시지.

---

### 1-2. `mapAnalyzeResponse.ts` 비대화

**현상**  
단일 파일(약 490줄)이 점수, 레포, 언어, README, 직무, 다중 도메인, 연봉, meta 등 모든 변환을 담당한다.

**위험**
- 다음 API 필드 추가 시 충돌·회귀 가능성 증가
- 단위 테스트·리뷰 어려움
- 책임 경계 불명확

**권장 분리**
| 모듈 | 담당 |
|------|------|
| `mapRepo.ts` | per_repo, diagnosis, language, collaboration |
| `mapJobs.ts` | eligible_matches, multi_domain_picks, postingText |
| `mapSalary.ts` | salary_band, reference_categories |
| `mapSummary.ts` | summary, level, meta, applicant |

---

### 1-3. sessionStorage 용량·민감도

**현상**  
분석 결과 전체를 `sessionStorage` 키 `git2value:analysis`에 저장한다.  
최근 추가된 `postingText`, `summaryText`, README 제안, `multi_domain_picks` 공고 본문까지 포함되어 용량이 커진다.

**위험**
- `multi_domain_picks`가 큰 응답(ver2 수준 이상)이면 브라우저 quota(보통 5~10MB) 근접 가능
- GitHub ID, repo 목록, 분석 결과, 채용 공고 본문이 탭 세션에 남음
- 새 탭에서는 결과 없음 (sessionStorage는 탭별)

**관련 파일**
- `src/context/AnalysisContext.tsx`

**권장 조치**
- 큰 텍스트(`postingText`, `summaryText`)는 저장 시 생략하거나 별도 키로 분리
- 또는 IndexedDB 검토 (용량·지속성 필요 시)

---

### 1-4. 동기 API + 무한 대기 가능

**현상**  
`/loading` 페이지는 `POST /v1/analyze` 완료까지 fake progress만 표시한다. **timeout·취소 로직이 없다.**

**위험**
- 백엔드 hang 시 96% 근처에서 오래 멈춤
- 사용자는 "분석 중"으로만 보이고 재시도·취소 불가

**관련 파일**
- `src/app/loading/page.tsx`
- `src/lib/analysisResult.ts`

**권장 조치**
- `AbortController` + timeout (예: 120초)
- "오래 걸리는 중" 상태 메시지
- 재시도 / 취소 버튼

---

### 1-5. 공고 본문 UI 폭발

**현상**  
`DomainJobPicksPanel`은 `<details open>`으로 공고 본문을 **기본 펼침** 상태로 표시한다.  
"가능한 전부 표시" 요구는 반영되었으나, ver2보다 큰 응답이 오면 페이지 길이가 급증한다.

**관련 파일**
- `src/components/jobs/DomainJobPicksPanel.tsx`
- `src/app/jobs/page.tsx` (TOP5 `postingText` details)

**권장 조치**
- 기본 접힘(`open` 제거) 또는 "전체 펼치기" 토글
- 섹션별 lazy render 검토

---

## 2. 중간 우선순위 (Medium)

### 2-1. `postingText` 매칭 키 충돌

**현상**  
TOP5 `postingText`는 `company_name::position` 문자열로 `multi_domain_picks.raw_top5` / `domain_picks`와 매칭한다.

**위험**  
같은 회사·같은 포지션명이 여러 건이면 잘못된 본문이 붙을 수 있다.

**관련 코드**  
`src/lib/mapAnalyzeResponse.ts` — `buildPostingTextLookup()`, `mapJobs()`

**권장 조치**  
API에 `job_id` 또는 `rank` 기반 매칭이 가능하면 그걸 사용.

---

### 2-2. `parseWeeklyCommits()` 문구 의존

**현상**  
주당 커밋 수는 `commit_pattern.detail`에서 정규식 `/약\s*([\d.]+)회/`로 파싱한다.

**위험**  
백엔드 문장 형식이 바뀌면 `weeklyCommits` StatRow가 비어 보인다.

**관련 코드**  
`src/lib/mapAnalyzeResponse.ts` — `parseWeeklyCommits()`

**권장 조치**  
가능하면 API에 `weekly_commits` 숫자 필드 추가 요청. 없으면 파싱 실패 시 detail 전체를 fallback 표시.

---

### 2-3. `totalPostings` 하드코딩

**현상**  
`mapJobSummary()`에서 `totalPostings: "3,400건"` 고정.

**위험**  
의도된 요구사항이지만, 나중에 API에 실제 건수가 생기면 mapper/UI를 함께 수정해야 한다. 잊기 쉬움.

**관련 코드**  
`src/lib/mapAnalyzeResponse.ts` L255

---

### 2-4. `techMatchNotes` 제한 제거

**현상**  
이전 `slice(0, 6)` / missing 3개 제한을 제거해, API가 주는 만큼 전부 표시한다.

**위험**  
응답이 커지면 `/jobs` 추천 근거 카드가 과밀해질 수 있다.

**관련 코드**  
`src/lib/mapAnalyzeResponse.ts` — `mapTechMatchNotes()`

---

### 2-5. `mockReport.ts` 수동 유지

**현상**  
`NEXT_PUBLIC_USE_MOCK=true` 시 `src/data/mockReport.ts`를 사용한다.  
실제 API 타입(`AnalysisResult`)과 수동 동기화 필요.

**위험**  
API/매퍼 변경 후 mock 업데이트 누락 시 mock 모드에서만 깨진 UI.

**권장 조치**  
mock는 `response.json` 또는 `response_ver2.json`을 `mapAnalyzeResponse`에 넣어 생성하는 스크립트 검토.

---

### 2-6. 접근성 (a11y)

**현상**
- `DomainJobPicksPanel` 도메인 탭 버튼에 `aria-pressed` 없음
- 긴 `pre` 공고 본문에 스크린 리더 구조 힌트 부족

**권장 조치**  
탭에 `role="tablist"`, `aria-selected` 등 WAI-ARIA 패턴 적용.

---

## 3. 낮은 우선순위 (Low)

### 3-1. UI/UX 세부

| 항목 | 설명 |
|------|------|
| jobs grid 고정 폭 | 긴 회사명·직무명·도메인에서 레이아웃 깨짐 가능 |
| `pre` 공고 본문 | 긴 줄에서 가로 스크롤·페이지 넓이 압박 |
| portfolio 헤더 | techStack·detectedDomains 많으면 좌우 높이 불균형 |
| ~~개인/팀 extra 진단 status~~ | **해결됨** — `없음`/`필수 미흡` explicit 매핑, `repoKind`별 포트폴리오 섹션 제목 분기 |
| ~~Gamepad2 아이콘~~ | **해결됨** — `src/lib/domainIcons.ts`로 도메인별 아이콘 매핑, `/result`·`/jobs` Gamepad2 하드코딩 제거 |

---

### 3-2. 리다이렉트 방식

**현상**  
`useAnalysis({ redirectIfMissing: true })`가 `window.location.href = "/"` 사용.

**영향**  
Next.js `router.replace()`보다 SPA 전환감이 거칠 수 있음. 기능상 큰 문제는 아님.

**관련 파일**  
`src/context/AnalysisContext.tsx`

---

### 3-3. 원본 JSON 미저장

**현상**  
매핑된 `AnalysisResult`만 sessionStorage에 저장. API raw JSON은 보관하지 않음.

**영향**  
디버깅·회귀 분석 시 Network 탭 또는 별도 저장 필요. 운영 이슈 추적에 불편할 수 있음.

---

## 4. 아직 미표시 API 필드 (의도적 제외 또는 API 한계)

다음은 백엔드에 있으나 UI에 아직 없거나, API가 제공하지 않는 항목이다.  
`handoff.md`와 중복되지만, "문제"라기보다 **향후 작업 후보**로 기록한다.

| 필드 | 상태 |
|------|------|
| `score_breakdown.quality_mode` | 미표시 |
| 플랫폼별 `count` (점핏/원티드 건수) | API 미제공 → UI `"—"` |
| `jobSummary.totalPostings` 실값 | 하드코딩 `3,400건` |
| `eligible_matches`만 있는 경우 TOP5 `postingText` | `multi_domain_picks` 없으면 본문 없음 |
| PDF/리포트 export | 미구현 |
| 분석 이력 (다중 세션) | sessionStorage 1세션만 |

---

## 5. 검증·운영 체크리스트

### 현재 확인된 상태
- `npm run typecheck` — 통과
- `npm run build` — 통과
- `ReadLints` (src) — 문제 없음

### 변경 후 권장 검증
```bash
npm run typecheck
npm run build
```

### 수동 스모크
1. `.env.local`에 `NEXT_PUBLIC_API_BASE_URL` 설정
2. `response.json` 유형 (2레포, ML/AI, domain_boosted) 분석
3. `response_ver2.json` 유형 (1레포, multi_domain, postingText) 분석
4. mock: `NEXT_PUBLIC_USE_MOCK=true` 로 UI 회귀

---

## 6. 개선 우선순위 요약

| 순위 | 항목 | 기대 효과 |
|------|------|-----------|
| 1 | `mapAnalyzeResponse` 모듈 분리 | 유지보수·회귀 방지 |
| 2 | API runtime validation (zod 등) | 프로덕션 안정성 |
| 3 | loading timeout / cancel | UX·운영 |
| 4 | sessionStorage 대용량 텍스트 처리 | quota·성능 |
| 5 | 공고 본문 기본 접힘 UX | 페이지 길이 제어 |
| 6 | postingText 매칭 키 개선 | 데이터 정확도 |
| 7 | mock 자동 생성 | mock/API drift 방지 |

---

## 7. 관련 문서

- [handoff.md](./handoff.md) — 현재 아키텍처·파일 역할·API 흐름
- [README.md](./README.md) — 실행 방법·환경 변수
- `backup_origin/` — 프로젝트 시작 시점 원본 스냅샷
- `response.json`, `response_ver2.json` — 실측 API 응답 샘플

---

## 8. 문서 갱신 규칙

- 구조 변경, 새 리스크 발견, 항목 해결 시 이 파일을 함께 업데이트한다.
- 해결된 항목은 섹션 하단 **해결 이력**에 날짜와 함께 기록하고, 본문에서는 "해결됨"으로 표시하거나 제거한다.

### 해결 이력

- **2026-05-27** — Gamepad2 도메인 아이콘 미스매치: `src/lib/domainIcons.ts` 추가, `/result`·`/jobs`에서 도메인 문자열 기반 아이콘 사용
- **2026-05-27** — 개인/팀 extra 진단 status 미스매치: `mapDiagnosisStatus` explicit 매핑, `RepoAnalysis.repoKind`, 포트폴리오 섹션 제목·`없음` Chip
