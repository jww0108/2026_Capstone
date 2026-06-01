# Git2Value — GitHub Data Extraction Pipeline

**Specification Document v2.2**

> 버전: v2.2 (v2.1 대체) | 작성일: 2026.04.01 | 대상 사용자: 채용 기업 / 구직자 본인

---

## 0. 변경 이력

### v1.0 → v2.0 핵심 변경

| 항목                 | 상태    | 비고                                                       |
| -------------------- | ------- | ---------------------------------------------------------- |
| 포크/표절 탐지       | ✅ 충분 | 유지. fork 패널티 70% 삭감 그대로 적용                     |
| 블랙리스트 파일 제외 | ✅ 충분 | 유지. .meta/.unity 등 바이너리 제외 정상 작동              |
| 커밋 샘플링 방식     | ❌ 취약 | 최근 25개 고정 → 균등 샘플링으로 교체 (Phase 2 개정)       |
| LOC 계산 방식        | ❌ 취약 | additions 단순합산 → 커밋 수 보조 지표 추가 (Phase 4 개정) |
| 테스트/CI 실질성     | ⚠️ 부분 | 폴더 존재 유무 → 파일 비율 기반 proxy 지표로 개선          |
| 점수 설명 가능성     | ❌ 취약 | 단일 숫자 → score_breakdown 3개 축으로 분해 (신규)         |
| Rate Limit 대응      | ❌ 취약 | 조용한 실패 → Retry-After 파싱 + 지수 백오프 (신규)        |
| 중복 커밋 처리       | ❌ 취약 | SHA 기반 전역 dedup 추가 (신규)                            |

### v2.0 → v2.1 추가 반영

| 항목                        | 분류         | 비고                                                                       |
| --------------------------- | ------------ | -------------------------------------------------------------------------- |
| 오너십 확인 구현 방법 명시  | 🔧 구현 보완 | `per_page=1` 별도 호출로 최초 커밋 취득, warnings 출력 (Phase 1 개정)      |
| Consistency Score 수식 확정 | 🔧 구현 보완 | `max(0, 10 - std * 0.5)` 단순 선형으로 확정, 추후 교체 예정 (Phase 4 개정) |
| github_score 집계 방식 명시 | 🔧 구현 보완 | 단순 평균 → LOC 기반 가중 평균으로 변경 (Phase 5 개정)                     |
| FAISS 유사도 표현 즉시 수정 | 🐛 버그 수정 | `distances * 100` 퍼센트 표현 제거, 원시 유사도 값 출력으로 교체           |

### v2.1 → v2.2 추가 반영

| 항목                            | 분류         | 비고                                                                                                         |
| ------------------------------- | ------------ | ------------------------------------------------------------------------------------------------------------ |
| 오너십 확인 구현 방식 정정      | 🔧 문서 정합 | Phase 1-3 설명을 `per_page=1` 별도 API 호출 → `all_author_commits[-1]` 재활용으로 수정 (API 2회 절감 반영)  |
| asyncio 병렬 처리 설명 정정     | 🔧 문서 정합 | Phase 2 `asyncio.gather` 레포 간 병렬 처리 → 순차 처리(SHA dedup 보장)로 수정, 향후 asyncio.Lock 도입 예정 |
| run_git2value.py E2E 연결 완성  | ✅ 구현 완료 | 하드코딩 데모 프로필 제거, GitHubExtractor.extract_applicant_profile() 실제 호출로 교체                     |

---

## Phase 1: Ingestion & Validation (데이터 수집 및 검증)

### 1-1. Input

- 지원자의 GitHub Username
- 분석 대상 Repository URL 리스트 (브랜치 경로 포함 가능)
- 형식: `owner/repo` 또는 `owner/repo/tree/branch-name`

### 1-2. Auth

- 시스템 GitHub Personal Access Token (환경변수 `Github_api_token`)
- 향후: OAuth Token으로 교체 가능한 구조 유지

### 1-3. Validation — Anti-Cheating

- **Fork 탐지:** `fork: true` 레포지토리 식별 시 기여도 점수 가중치 70% 삭감 (기존 유지)
- **오너십 확인 ★ 구현 방법 확정 (v2.2 정정):** author 필터 커밋 목록(`all_author_commits`)의 마지막 항목(`all_author_commits[-1]`)을 재활용하여 최초 커밋을 추정. 해당 커밋의 `author.date`와 `repo_meta.created_at` 차이가 30일 이상이면 `warnings` 필드에 경고 출력
  - v2.1 문서의 `per_page=1&order=asc` 별도 API 호출 방식은 실제 구현에 반영되지 않음 — API 2회 절감을 위해 목록 재활용 방식을 채택
  - 단, 수집 상한(`MAX_COMMIT_PAGES × per_page = 300커밋`) 밖의 더 오래된 커밋은 반영되지 않을 수 있음 (허용된 트레이드오프)
  - 점수 차감 없이 경고만 출력 (판단은 사용자에게 위임)
- **중복 커밋 제거 (신규):** 전역 SHA set을 통해 여러 레포 스캔 시 동일 커밋 중복 집계 방지

> 💡 **설계 의도:** fork 레포지토리도 완전 제외하지 않고 0.3배 가중치를 부여하여, 오픈소스 기여 이력이 있는 지원자에게 불이익이 없도록 합니다.

---

## Phase 2: Parallel Fetching (비동기 데이터 추출)

`asyncio.gather`를 통해 **단일 레포 내부** 엔드포인트를 동시에 호출합니다. 레포 간(across-repo) 처리는 SHA dedup 정확성을 보장하기 위해 순차 처리합니다.

> **v2.2 정정:** v2.1 문서에서 레포 간도 `asyncio.gather`로 병렬 처리한다고 명시하였으나, 실제 구현은 전역 `seen_sha` set의 경쟁 조건(race condition) 방지를 위해 레포 간 순차 처리를 채택합니다. 향후 `asyncio.Lock`으로 `seen_sha`를 보호하여 레포 간 병렬화를 도입할 예정입니다.

### 2-1. 호출 엔드포인트 (변경 없음)

- Repository Meta: `/repos/{owner}/{repo}`
- Tree (파일 목록): `/repos/{owner}/{repo}/git/trees/{branch}?recursive=1`
- Commit History: `/repos/{owner}/{repo}/commits?author={username}&sha={branch}&per_page=100`
- Readme Content: `/repos/{owner}/{repo}/readme?ref={branch}`

### 2-2. 커밋 샘플링 방식 개정 ★

> ❌ **v1.0 문제:** 최근 25개 커밋만 분석 → 200개 커밋 프로젝트에서 초기 핵심 로직이 누락되고, 커밋 수가 적은 신규 프로젝트가 상대적으로 유리해지는 왜곡 발생

**✅ v2.0 개선: 균등 샘플링 (Stratified Sampling)**

- 전체 커밋 수를 먼저 파악한 뒤, 초기 / 중간 / 최근 구간에서 각 최대 25개씩 균등 추출
- 최대 분석 커밋 수: 75개 (기존 25개에서 3배 확장)
- SHA 기반 dedup으로 구간 중복 제거

```python
# 균등 샘플링 pseudo-code
total  = len(all_commits)
early  = all_commits[:25]
mid    = all_commits[total//2 - 12 : total//2 + 13]
recent = all_commits[-25:]

seen_sha = set()
sampled  = []
for c in early + mid + recent:
    if c['sha'] not in seen_sha:
        seen_sha.add(c['sha'])
        sampled.append(c)
```

### 2-3. Rate Limit 대응 ★ 신규

- 모든 API 호출에 응답 헤더 확인 로직 추가
- HTTP 403 / 429 수신 시 `Retry-After` 헤더 파싱 후 대기
- 최대 3회 지수 백오프 (1s → 2s → 4s) 재시도
- 3회 실패 시 해당 레포를 `valid: False`로 마킹하고 명시적 에러 로그 출력 (조용한 실패 금지)

---

## Phase 3: Data Cleansing & Context Parsing (데이터 정제)

### 3-1. Text Normalization (변경 없음)

- README 본문 Base64 디코딩
- 정규표현식으로 마크다운 이미지, 배지, HTML 태그 제거
- 프레임워크 보일러플레이트 패턴 제거 (bootstrapped with CRA 등)
- 순수 자연어 아키텍처 / 트러블슈팅 설명 텍스트만 추출, 최대 1500자

### 3-2. Language Aggregation (변경 없음)

- 커밋 분석 기반 확장자별 언어 추적 (GitHub API 브랜치 언어 유실 문제 해결 유지)
- LOC 기반 언어 비중(%) 산출, 상위 5개 언어만 출력

---

## Phase 4: Scoring Engine (품질 및 기여도 평가)

### 4-1. 점수 구조 개편 ★

v1.0의 단일 숫자 출력에서 **3개 축의 분해 점수**로 전환합니다.

| 축                    | 배점  | 산출 방식                                     |
| --------------------- | ----- | --------------------------------------------- |
| contribution (기여도) | ~60점 | 보정된 LOC + 커밋 횟수                        |
| quality (성숙도)      | ~30점 | CI/CD 실질성, 테스트 파일 비율, 유지보수 기간 |
| consistency (일관성)  | ~10점 | 커밋 주기 규칙성 (표준편차 기반)              |

### 4-2. Contribution Score 개정 ★

> ❌ **v1.0 문제:** `additions`만 단순 합산 → 리팩토링 커밋(additions ≈ 0)이 낮은 점수를 받고, 자동 생성 코드가 많을수록 유리해지는 왜곡 발생

**✅ v2.0 개선: 커밋 수 보조 지표 추가**

- 순수 LOC = additions (블랙리스트 제외 후)
- 커밋 횟수를 보조 지표로 추가 (총 분석 커밋 수 기준)
- 기준값(만점 LOC)은 하드코딩 1500 유지 → 향후 지원자 백분위 기반 상대값으로 교체 예정

```python
# v2.0 contribution score 산출
loc_score    = min(100, (valid_loc / 1500) * 100)
commit_score = min(100, (commit_count / 50) * 100)  # 보조 지표

contribution = (loc_score * 0.7) + (commit_score * 0.3)
```

### 4-3. Quality Score 개정 ★

> ❌ **v1.0 문제:** CI/CD 파일 존재 = 25점, 테스트 폴더 존재 = 25점 → 빈 폴더, `echo hello` 파이프라인도 만점

**✅ v2.0 개선: 실질성 proxy 지표 도입**

- **CI/CD:** `.github/workflows/` 또는 `Dockerfile` 파일이 존재하고 파일 크기 > 200B인 경우에만 점수 부여
- **테스트:** test 파일 수 / 전체 소스 파일 수 비율 계산 (`tree_data` 활용, 추가 API 호출 없음)
  - 비율 5% 미만: 0점 / 5~20%: 15점 / 20% 이상: 25점
- **유지보수 기간:** 기존 로직 유지 (30일 이상 30점, 7일 이상 15점, 이하 0점)

### 4-4. Consistency Score ★ 신규 (수식 확정)

- 분석된 커밋들의 타임스탬프를 추출하여 커밋 간격(일) 계산
- 표준편차가 낮을수록(규칙적일수록) 높은 점수 부여
- **확정 수식:** `max(0, 10 - std * 0.5)` (단순 선형 감쇠, 추후 지수 감쇠로 교체 가능)
  - std = 0 (완벽하게 규칙적): 10점 만점
  - std = 20일: 0점
- **적용 제외 조건:** 분석된 커밋 수 < 5개인 경우 (단기 스프린트 프로젝트 오염 방지)

> ⚠️ **수식 주의사항:** 현재 상수(0.5)는 임의값입니다. 지원자 데이터가 누적되면 실제 분포를 보고 조정해야 합니다. 지수 감쇠(`10 * exp(-std / K)`) 전환 시 K값도 데이터 기반으로 결정합니다.

---

## Phase 5: Assembly & Hand-over (최종 병합 및 엔진 전달)

### 5-1. Output JSON Schema ★ v1.0 대비 확장

```json
{
  "github_score": 79.3,
  "score_breakdown": {
    "contribution": 42,
    "quality": 28,
    "consistency": 9
  },
  "applicant_resume": "...",
  "metrics_summary": {
    "total_valid_loc": 29698,
    "top_languages": "C# (92%), JavaScript (5%)",
    "scanned_repos": 3,
    "total_commits_analyzed": 67
  },
  "warnings": [
    "repo 'Ttakji_lab' Rate Limit으로 인해 부분 스캔됨",
    "repo 'KGU_NSL_webpage' 최초 커밋이 repo 생성일보다 32일 늦음 — 오너십 확인 필요"
  ]
}
```

### 5-2. github_score 집계 방식 ★ 구현 확정

> ❌ **v2.0 미명시 문제:** `total_score / valid_repos` 단순 평균 사용 시, 커밋 2개짜리 레포와 커밋 150개짜리 레포가 동일한 가중치를 가져 최종 점수가 왜곡됨

**✅ v2.1 확정: LOC 기반 가중 평균**

```python
# LOC 기반 가중 평균 집계
weighted_sum = sum(res["score"] * res["valid_loc"] for res in valid_results)
total_loc    = sum(res["valid_loc"] for res in valid_results)

# valid_loc = 0인 레포(README only 등)는 가중치 0으로 자동 제외됨
# 단, 전체 LOC가 0이면 단순 평균으로 폴백
final_score = (weighted_sum / total_loc) if total_loc > 0 else (
    sum(r["score"] for r in valid_results) / len(valid_results)
)
```

### 5-3. 점수 설명 가능성 요건

`score_breakdown`은 필수 반환 필드입니다. 단일 숫자만 반환하는 블랙박스 구조는 v2.1에서 허용하지 않습니다.

- **채용 기업:** breakdown을 보고 어느 축이 강점/약점인지 판단 가능
- **구직자 본인:** 어느 항목을 개선하면 점수가 오르는지 피드백 제공 가능

---

## Phase 6: 개선 우선순위 로드맵

| 우선순위 | 개선 항목              | 현재 문제                             | 개선 방향                             |
| -------- | ---------------------- | ------------------------------------- | ------------------------------------- |
| 1순위    | 커밋 균등 샘플링       | 최근 25개 고정으로 장기 프로젝트 왜곡 | 초기/중간/최근 3구간 균등 추출        |
| 2순위    | 점수 분해 출력         | 단일 숫자라 신뢰 근거 설명 불가       | score_breakdown 3축 분리 반환         |
| 3순위    | 테스트 비율 proxy      | 폴더 존재 유무만 체크                 | test파일수 / 전체소스파일수 비율      |
| 4순위    | 커밋 수 보조 지표      | LOC만으로 리팩토링 불이익             | commit_count를 contribution에 가산    |
| 5순위    | Rate Limit + 에러처리  | 조용한 실패로 잘못된 점수 생성        | Retry-After + 지수 백오프 + 경고 필드 |
| 6순위    | SHA 기반 dedup         | 레포 간 중복 커밋 합산 가능           | 전역 seen_sha set으로 중복 제거       |
| 7순위    | LOC 가중 평균 집계     | 레포 규모 무관 단순 평균 왜곡         | valid_loc 기반 가중 평균으로 교체     |
| 8순위    | 오너십 확인 구현       | 스펙 명시만 있고 구현 없음            | per_page=1 별도 호출 + warnings 출력  |
| 즉시     | FAISS 유사도 표현 수정 | distances \* 100 퍼센트 오표현        | 원시 유사도 값 그대로 출력으로 교체   |

---

## 향후 과제 (v3.0 이후)

현재 구현 범위 밖이지만, 시스템 성숙 후 반드시 고려해야 할 항목입니다.

- **LOC 기준값 절대값 → 백분위 기반 상대 평가 전환** (지원자 데이터 누적 후)
- **applicant_resume 텍스트를 연봉 계산에 실질적으로 반영** (현재는 직무 라우팅에만 사용됨)
  - 기술 키워드 밀도, 수치 포함 여부, 프로젝트 설명 깊이 등 휴리스틱 기반 보정 계수 추가
- **FAISS 유사도 표현 고도화** (즉시 수정은 원시값 출력으로 완료 → 장기적으로 유사도 분포 기반 레이블화 "높음/보통/낮음" 도입)
- **Consistency Score 수식 고도화** (현재 선형 감쇠 → 데이터 누적 후 지수 감쇠 `10 * exp(-std / K)` 전환, K값 데이터 기반 결정)
- **멀티 브랜치 스캔 + SHA dedup**으로 브랜치별 커밋 누락 문제 완전 해소

---

_Git2Value Pipeline Spec v2.2 — 내부 기술 문서 — 2026.04.01_
