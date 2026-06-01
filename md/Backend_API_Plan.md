# Git2Value — 백엔드 API화 계획 (Phase 1)

> 작성일: 2026.05.17 | 대상: run_git2value.py 리팩토링 + main.py 확장
> 전제: Phase 2(Tailscale Funnel) 완료, Phase 3(프론트 연동)은 팀원 담당

---

## 1. 목표

`run_git2value.py`의 E2E 파이프라인(`run_e2e_pipeline()`)은 현재 `print()` 기반 CLI 스크립트다. 이를 **JSON dict를 반환하는 함수**로 분리하고, `main.py`에 `POST /v1/analyze` 엔드포인트를 추가하여 프론트엔드가 호출할 수 있게 한다.

**원칙:** 기존 CLI 동작을 깨뜨리지 않는다. dict 반환 함수를 새로 만들고, `__main__` 블록에서는 기존처럼 print하되 내부적으로 새 함수를 호출한다.

---

## 2. 현재 `run_e2e_pipeline()` 분석

총 1058줄 중 E2E 파이프라인(`run_e2e_pipeline`, line 703~1038)이 약 335줄이다. 이 중 **로직(데이터 수집·매칭·진단·연봉)이 약 100줄**, **print 출력이 약 235줄**이다.

### 파이프라인 단계별 분류

| 단계 | 라인 | 역할 | API 반환에 필요 |
|---|---|---|---|
| Step 1: 인프라 로딩 | 726~733 | FAISS·모델·캐시 로드 | 서버 시작 시 1회 (요청마다 X) |
| Step 2: GitHub 스캔 | 736~739 | extractor 호출 | ✅ profile dict |
| Step 3: FAISS 매칭 | 746~791 | 임베딩·검색·리랭킹·필터 | ✅ job_matching dict |
| Step 4: 진단 | 793~795 | run_diagnosis() | ✅ diagnosis dict |
| Step 5: 연봉 밴드 | 797~805 | get_market_band() | ✅ salary_band dict |
| Step 6: 기술 매칭 | 807~819 | analyze_tech_match() | ✅ tech_result dict |
| 출력: 지원자 요약 | 832 | print | ❌ dict로 전환 |
| 출력: 모듈 A | 850~864 | print (레포 카드) | ❌ dict로 전환 |
| 출력: 모듈 B | 866~936 | print (직무 매칭) | ❌ dict로 전환 |
| 출력: 모듈 C | 942~1037 | print (연봉) | ❌ dict로 전환 |

핵심 관찰: **로직 단계(Step 1~6)는 이미 dict를 생성하고 있다.** print 단계에서 이 dict를 풀어서 출력하는 것이므로, dict 반환 함수는 print 단계를 건너뛰고 로직 단계의 결과를 구조화하여 반환하면 된다.

---

## 3. 리팩토링 전략

### 3-1. 함수 분리 구조

```
run_e2e_pipeline()              ← 기존 CLI (print 유지)
  │
  └─ calls ──→ run_full_analysis()  ← 신규 (dict 반환)
                    │
                    ├─ _build_github_score_dict()
                    ├─ _build_per_repo_dict()
                    ├─ _build_job_matching_dict()
                    ├─ _build_diagnosis_dict()
                    └─ _build_salary_band_dict()
```

`run_full_analysis()`가 순수 dict 반환 함수이고, `run_e2e_pipeline()`은 이 dict를 받아서 print하는 래퍼다. 기존 CLI 동작은 100% 유지된다.

### 3-2. 인프라 로딩 분리

현재 `run_e2e_pipeline()` 안에서 매번 FAISS·모델을 로드한다. CLI에서는 1회 실행이니 괜찮지만, API 서버에서는 요청마다 로드하면 안 된다.

```python
# run_git2value.py 모듈 레벨

class Git2ValuePipeline:
    """E2E 파이프라인. 인프라는 init에서 1회 로드, analyze()는 요청마다 호출."""

    def __init__(self):
        current_dir = os.path.dirname(os.path.abspath(__file__))
        index_path = os.path.join(current_dir, "vector", "git2value_faiss.index")
        meta_path  = os.path.join(current_dir, "vector", "git2value_metadata.json")
        cache_path = os.path.join(current_dir, "vector", "experience_cache.json")

        self.index = faiss.read_index(index_path)
        with open(meta_path, "r", encoding="utf-8") as f:
            self.metadata = json.load(f)
        self.model = SentenceTransformer("jhgan/ko-sroberta-multitask")
        self.val_engine = Git2ValueEngine()
        self.exp_cache = load_or_build_cache(self.metadata, cache_path)
        self.extractor = GitHubExtractor()

    async def analyze(
        self,
        username: str,
        repos: list[str],
        applicant_years: int = 0,
    ) -> dict:
        """E2E 분석. dict 반환. print 없음."""
        ...
```

---

## 4. `analyze()` 반환 스키마

### 4-1. 최상위 구조

```python
{
    "status": "success",                    # "success" | "error"
    "error": None,                          # 에러 시 메시지

    "github_score": { ... },                # §4-2
    "per_repo": [ ... ],                    # §4-3
    "level": { ... },                       # §4-4
    "summary": { ... },                     # §4-5
    "job_matching": { ... },                # §4-6
    "salary_band": { ... },                 # §4-7
    "tech_analysis": { ... },               # §4-8

    "meta": {                               # §4-9
        "version": "v7.0",
        "llm_available": true,
        "analysis_time_seconds": 18.3
    }
}
```

### 4-2. `github_score`

```python
{
    "total": 72.4,
    "method": "대표 프로젝트 70% + 전체 평균 30%",
    "breakdown": {
        "contribution": 42,
        "quality": 22,
        "consistency": 8
    },
    "breakdown_note": "최고 레포 기준"
}
```

데이터 출처: `profile["github_score"]`, `profile["score_breakdown"]`

### 4-3. `per_repo` (레포별 정보)

```python
[
    {
        "repo_name": "project-a",
        "repo_url": "https://github.com/user/project-a",
        "repo_type": "team",                    # "team" | "personal"
        "distinct_author_count": 3,
        "is_fork": false,
        "fork_penalty": null,                   # float 또는 null
        "fork_penalty_log": null,
        "dominance_ratio": null,                # v6.4: 지배적 기여자 비율
        "is_dominance_override": false,
        "repo_total_score": 83.0,
        "score_breakdown": {
            "contribution": 45,
            "quality": 30,
            "consistency": 8,
            "quality_mode": "team"
        },
        "target_commit_count": 120,
        "total_repo_commits": 200,
        "target_commit_ratio": 0.6,
        "active_weeks": 12,
        "repo_active_weeks": 16,
        "diagnosis": {
            "core_items": {
                "readme_quality": {
                    "status": "양호",
                    "detail": "...",
                    "action": null,
                    "llm_used": true,
                    "llm_scores": { "purpose": 4, "tech": 5, "setup": 3, "visual": 4, "overall": 4 },
                    "llm_suggestions": ["...", "..."]
                },
                "project_structure": { "status": "...", "detail": "...", "action": "..." },
                "commit_quality": { "status": "...", "detail": "...", "action": "..." }
            },
            "extra_items": {
                "test_coverage": { "status": "...", "detail": "...", "action": "..." },
                "cicd": { "status": "...", "detail": "...", "action": "..." },
                "deployment": { "status": "...", "detail": "...", "action": "..." },
                "commit_pattern": { "status": "...", "detail": "...", "action": "..." }
            }
        }
    }
]
```

데이터 출처: `profile["per_repo"]` + `diag_bundle["per_repo_diagnoses"]` 병합

### 4-4. `level`

```python
{
    "grade": "Competitive",                 # "Top" | "Competitive" | "Competitive (개인)" | "Entry"
    "description": "...",
    "team_repo_count": 1,
    "score": 5
}
```

데이터 출처: `diag_bundle["level"]`

### 4-5. `summary`

```python
{
    "positioning": "서버/백엔드 신입 지원 시 경쟁력 있는 포트폴리오",
    "strengths": ["README 품질", "테스트 코드", "CI/CD"],
    "quick_wins": [
        "docker-compose.yml로 로컬 실행 가능하게 구성",
        "주요 API 엔드포인트 목록을 README에 추가"
    ],
    "github_score_text": "GitHub 종합 점수: 72.4점 / 100점\n  산출 기준: ..."
}
```

데이터 출처: `diag_bundle["summary_block"]` (현재 문자열 → 구조화 필요)

### 4-6. `job_matching`

```python
{
    "primary_domain": "서버/백엔드",
    "detected_domains": ["서버/백엔드", "웹 프론트엔드"],
    "rerank_note": "도메인 감지: '서버/백엔드' → ...",
    "is_multi_domain": false,
    "eligible_matches": [
        {
            "rank": 1,
            "position": "백엔드 개발자",
            "company_name": "A사",
            "category": "서버/백엔드",
            "similarity": 0.847,
            "effective_score": 0.897,
            "domain_boosted": true,
            "similarity_label": "강함",
            "experience_requirement": {
                "raw_label": "신입/주니어",
                "requirement_type": "junior",
                "min_years": 0
            }
        }
    ],
    "flagged_matches": [],
    "domain_mismatch": null,
    "multi_domain_picks": null
}
```

데이터 출처: `top_matches_5` + `rerank_note` + `multi_domain_result` + `mismatch_diag`

### 4-7. `salary_band`

```python
{
    "matched_category": "서버/백엔드",
    "experience_level": "신입 (0~3년)",
    "salary_range": {
        "jumpit_median": 38000000,
        "wanted_median": 36000000,
        "combined_range": "3,600만 ~ 3,800만원"
    },
    "realistic_range": {
        "p25_estimate": 31450000,
        "median": 37000000,
        "p75_estimate": 44400000
    },
    "reference_categories": [
        { "category": "프론트엔드", "range": "3,200만 ~ 3,600만원" }
    ]
}
```

데이터 출처: `band_report["market_salary_band"]` + 참고 직무 직접 조회

### 4-8. `tech_analysis`

```python
{
    "matched_techs": ["Python", "FastAPI", "Docker"],
    "missing_techs": ["Spring Boot", "AWS", "Redis"],
    "learning_suggestions": ["Kubernetes", "Terraform"],
    "company_types": ["스타트업 유사 공고 3건", "중견기업 유사 공고 2건"]
}
```

데이터 출처: `tech_result`

### 4-9. `meta`

```python
{
    "version": "v7.0",
    "llm_available": true,
    "analysis_time_seconds": 18.3,
    "repos_analyzed": 2,
    "applicant_years": 0
}
```

---

## 5. `generate_summary_block()` 구조화

현재 `generate_summary_block()`은 **포맷된 문자열**을 반환한다. API에서는 이걸 그대로 보내면 프론트엔드가 파싱할 수 없다.

두 가지 선택지가 있다:

**선택 A: summary_block 문자열을 그대로 전달 + 구조화 dict 병렬 제공**

```python
"summary": {
    "text": "GitHub 종합 점수: 72.4점 / 100점\n  ...",   # 기존 문자열 (CLI 호환)
    "positioning": "서버/백엔드 신입 지원 시 ...",          # 구조화
    "strengths": ["README 품질", "테스트 코드"],
    "quick_wins": ["...", "..."]
}
```

**선택 B: `generate_summary_block()`을 dict 반환으로 리팩토링**

이건 `portfolio_diagnosis.py`까지 건드려야 해서 공수가 크다.

**권장: 선택 A.** 기존 함수를 변경하지 않고, `diag_bundle`에서 이미 사용 가능한 데이터(`level_dict`, `strengths`, `quick_wins`)를 직접 조합한다. `summary_block` 문자열은 `text` 필드에 그대로 보존하여 CLI 호환성 유지.

---

## 6. `main.py` 확장

```python
# main.py에 추가

from run_git2value import Git2ValuePipeline
from pydantic import BaseModel
from typing import List, Optional
from fastapi import HTTPException
from fastapi.middleware.cors import CORSMiddleware
import re
import time

# ── 입력 검증 패턴 ────────────────────────────────────
GITHUB_USERNAME_RE = re.compile(r"^[a-zA-Z0-9\-]{1,39}$")
GITHUB_REPO_RE = re.compile(
    r"^https://github\.com/[\w\-]+/[\w.\-]+(/tree/[\w.\-/]+)?$"
)

# ── CORS ──────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://your-app.vercel.app",     # 프론트 배포 도메인
        "http://localhost:3000",            # 로컬 개발
        "http://localhost:5173",            # Vite 기본
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

# ── 파이프라인 싱글톤 (서버 시작 시 1회 로드) ─────────
pipeline: Optional[Git2ValuePipeline] = None

@app.on_event("startup")
async def startup():
    global pipeline
    pipeline = Git2ValuePipeline()


# ── 요청/응답 모델 ────────────────────────────────────
class AnalyzeRequest(BaseModel):
    github_username: str
    repos: List[str]
    applicant_years: Optional[int] = 0


# ── 엔드포인트 ────────────────────────────────────────
@app.post("/v1/analyze")
async def analyze(req: AnalyzeRequest):
    # 입력 검증
    if not GITHUB_USERNAME_RE.match(req.github_username):
        raise HTTPException(400, "유효하지 않은 GitHub 사용자명")
    if not req.repos or len(req.repos) == 0:
        raise HTTPException(400, "최소 1개 레포를 입력하세요")
    if len(req.repos) > 3:
        raise HTTPException(400, "최대 3개 레포까지 분석 가능합니다")
    for repo in req.repos:
        if not GITHUB_REPO_RE.match(repo):
            raise HTTPException(400, f"유효하지 않은 레포 URL: {repo}")

    start = time.time()

    try:
        result = await pipeline.analyze(
            username=req.github_username,
            repos=req.repos,
            applicant_years=req.applicant_years or 0,
        )
    except Exception as e:
        raise HTTPException(500, f"분석 실패: {str(e)}")

    result["meta"]["analysis_time_seconds"] = round(time.time() - start, 1)
    return result
```

---

## 7. 적용 순서

```
Step 1: Git2ValuePipeline 클래스 생성 (30분)
  ├─ __init__(): FAISS, 모델, 캐시, extractor 로드
  └─ analyze(): run_e2e_pipeline의 로직 부분만 이식

Step 2: 내부 dict 빌더 함수 작성 (1시간 30분) ★ 최대 공수
  ├─ _build_github_score_dict(profile)
  ├─ _build_per_repo_dict(profile, per_repo_diags)
  ├─ _build_job_matching_dict(top_matches_5, rerank_note, ...)
  ├─ _build_salary_band_dict(band_report, ref_categories, ...)
  ├─ _build_tech_analysis_dict(tech_result)
  ├─ _build_level_dict(diag_bundle)
  └─ _build_summary_dict(diag_bundle)

Step 3: run_e2e_pipeline() CLI 래퍼 전환 (30분)
  └─ analyze() 호출 → 결과 dict를 기존 print 형식으로 출력
     (기존 print 로직은 유지, 데이터 소스만 analyze() 결과로 교체)

Step 4: main.py 확장 (30분)
  ├─ CORS 설정
  ├─ Git2ValuePipeline 싱글톤 초기화
  ├─ POST /v1/analyze 엔드포인트
  └─ 입력 검증

Step 5: 통합 테스트 (30분)
  ├─ CLI: python run_git2value.py → 기존과 동일 출력 확인
  ├─ API: curl -X POST /v1/analyze → JSON 응답 확인
  ├─ 에러: 잘못된 username/repo → 400 응답 확인
  └─ LLM 다운: 룰베이스 폴백 + llm_available=false 확인
```

**총 공수: 약 3시간 30분.**

---

## 8. 주의사항

### 8-1. 기존 CLI 깨뜨리지 않기

`__main__` 블록은 변경하지 않는다. `run_e2e_pipeline()`은 내부적으로 `Git2ValuePipeline.analyze()`를 호출하고, 그 결과를 기존 print 형식으로 출력하는 래퍼가 된다.

```python
async def run_e2e_pipeline(target_username, target_repos, applicant_years):
    pipeline = Git2ValuePipeline()
    result = await pipeline.analyze(target_username, target_repos, applicant_years)

    # 기존 print 로직 (result dict에서 데이터를 꺼내서 출력)
    _print_full_report(result, target_username, applicant_years)
```

### 8-2. similarity_label은 서버에서 계산

`similarity_label()`은 top5 전체 점수 분포가 필요하므로, 프론트에서 계산할 수 없다. 서버에서 계산하여 `eligible_matches[].similarity_label`에 포함한다.

### 8-3. company_name 노출

현재 출력에 회사명이 포함된다. API 응답에도 그대로 포함한다. 저작권 이슈는 별도 논의 사항이며, 프론트엔드가 표시 여부를 결정할 수 있다.

### 8-4. 응답 크기

레포 3개 + 매칭 5개 + 연봉 기준, JSON 응답은 약 15~30KB다. 프론트엔드에서 문제 없는 크기다.

### 8-5. 동시 요청

FastAPI는 async이므로 동시 요청을 처리할 수 있지만, GitHub API 토큰이 1개이므로 rate limit 공유가 발생한다. 캡스톤 데모에서 동시 사용자가 2~3명 이내이면 문제없다. 그 이상이면 요청 큐잉이 필요하지만 현 단계에서는 과도하다.

---

## 9. 파일 변경 요약

| 파일 | 변경 | 규모 |
|---|---|---|
| `run_git2value.py` | `Git2ValuePipeline` 클래스 + `analyze()` + dict 빌더 7개 + `run_e2e_pipeline` 래퍼 전환 | **대규모** |
| `main.py` | CORS + 싱글톤 + `/v1/analyze` + 입력 검증 | 중간 |
| 기타 | 변경 없음 | — |

### 변경하지 않는 파일

`github_extractor.py`, `profile_builder.py`, `portfolio_diagnosis.py`, `valuation_engine.py`, `experience_filter.py`, `llm_readme_evaluator.py` — 모두 변경 없음. `run_git2value.py`가 이 모듈들의 출력을 dict로 재구성하는 것이지, 모듈 내부를 바꾸는 것이 아니다.

---

*Git2Value 백엔드 API화 계획 (Phase 1) — 2026.05.17*
