# Git2Value — 업그레이드 계획 v3
**Phase 4.0 설계 문서**
> 작성일: 2026.04.06 | 전제: Plan2 + 아키텍처 리뷰 전면 반영
> v3.1 → v4.0 변경: 서비스 방향 전환, 연봉 산출 분리, LLM 의존 제거, 임베딩 비대칭 해결

---

## 0. Plan2 대비 핵심 변경 요약

| 항목 | Plan2 (v3.1) | Plan3 (v4.0) | 변경 근거 |
|---|---|---|---|
| 타겟 사용자 | 채용 기업 / 구직자 전체 | **신입 개발자(취준생) 전용** | 경력직은 깃허브 밖 변수가 너무 많아 추정 신뢰도 부족 |
| 연봉 산출 방식 | github_score × multiplier → 단일 추천 연봉 | **시장 연봉 밴드 독립 제공** (깃허브 점수와 분리) | multiplier 공식(0.80~1.25)에 경험적 근거 없음 |
| LLM 코드 리뷰 (F2) | Claude API로 상위 20% 코드 리뷰 | **삭제** | 비용 대비 효과 불확실, 캡스톤 데모 안정성 저하 |
| resume LLM 평가 (F2-B) | Claude API로 전체 실행 | **삭제** → 룰베이스 변환 레이어로 대체 | 구조화 데이터→텍스트 변환은 LLM 과잉 |
| 외부 API 의존 | Claude Sonnet API 필수 | **외부 API 0건** (필요시 로컬 Qwen 폴백) | 네트워크 의존 제거, 데모 안정성, 비용 0 |
| 리포트 구조 | 단일 추천 연봉 중심 | **3개 독립 모듈** (직무매칭 + 진단 + 연봉밴드) | 하나가 부정확해도 나머지 오염 방지 |
| 임베딩 입력 | README 날것 + 통계 이어붙이기 | **공고 문체 변환 레이어** 추가 | 깃허브↔공고 텍스트 비대칭 해소 |
| 도메인 판별 | 언어 통계에만 의존 | **파일명/폴더명 도메인 감지** 추가 | C# 게임 레포→SW 오분류 등 방지 |

---

## 1. 서비스 리프레이밍

### 변경 전
> "GitHub 분석 기반 적정 연봉 산출 서비스"

### 변경 후
> **"신입 개발자를 위한 깃허브 포트폴리오 진단 & 취업 전략 리포트"**

### 리프레이밍 근거

**왜 신입 전용인가:**
- 경력직은 회사 경력이 본체이고 깃허브는 그림자 — 깃허브만으로 역량/연봉 추정이 불가능
- 신입은 깃허브가 사실상 유일한 코드 포트폴리오 — 분석 가치가 높음
- 신입 연봉은 회사 티어별로 밴드가 좁음(3,500만~5,500만) — 범위 제시가 현실적
- 레벨 추정 불필요 — 모두 신입

**왜 연봉 "추정"이 아니라 "밴드 정보 제공"인가:**
- `multiplier = 0.80 + (github_score / 100.0) * 0.45` 공식의 0.80, 0.45는 근거 없는 임의 상수
- `percentile = github_score`는 동어반복 — 통계적 의미 없음
- `P25 = base × 0.85`, `P75 = base × 1.15`는 실제 분포가 아닌 기계적 곱셈
- 깃허브 점수 X인 사람이 실제 연봉 Y를 받는다는 쌍(pair) 데이터가 존재하지 않음
- **결론:** 깃허브 점수와 연봉 사이에 검증된 상관관계가 없는 상태에서 정밀한 숫자를 제시하면 서비스 신뢰도를 깎아먹음

---

## 2. 최종 리포트 구조 (3개 독립 모듈)

```
GitHub ID 입력
    ↓
[파이프라인 A] 기술 스택 추출 → 직무 매칭 (상위 3~5개 공고)
    ↓
[파이프라인 B] 포트폴리오 진단 → 항목별 체크리스트 + 개선 가이드
    ↓
[파이프라인 C] 매칭된 직무의 시장 연봉 밴드 조회 (깃허브 점수와 독립)
    ↓
[최종 리포트] 세 가지를 나란히 출력 (합치지 않음)
```

각 파이프라인이 독립적이라 하나가 부정확해도 나머지가 오염되지 않음.

---

## 3. 파이프라인 A: 직무 매칭 (FAISS)

### 3-1. 현재 문제: 임베딩 비대칭

**공고 쪽 텍스트:**
> "3년 이상의 Spring Boot 경험자 우대, MSA 설계 가능자, REST API 개발 경험 필수"

**깃허브 쪽 텍스트 (현재 applicant_resume):**
> "주요 기술 스택: Java (60%), Python (25%)\n\n[repo1 요약]: REST API 서버를 구축했습니다"

문체, 구조, 어휘가 완전히 달라서 같은 벡터 공간에서 의미 있는 유사도가 나오기 어려움.

### 3-2. 해결: 프로필 변환 레이어 추가

깃허브 추출 데이터를 **공고와 동일한 문체의 구조화 텍스트**로 변환.

**구현 방식 — 룰베이스 템플릿 (LLM 불필요):**

도메인 감지(3-5절), 의존성 파싱(3-4절), README 잔량 분기(8절)의 결과를 통합하여 공고 문체 텍스트를 생성한다.
최종 `build_profile_text()` 구현은 **3-5절**에 도메인 감지 통합 버전으로 명시.

**왜 LLM이 아닌 룰베이스인가:**
- 입력이 구조화 데이터이고 출력 패턴이 고정적 — 고난도 추론이 아님
- 임베딩 모델은 자연스러운 문장 vs 키워드 나열을 큰 차이로 구별하지 않음
- 외부 의존 0, 비용 0, 데모 안정성 최고
- 품질 부족 시 로컬 Qwen2-7B로 단계적 전환 가능 (RTX 4090 보유)

### 3-3. 추가 기능: 매칭 공고 패턴 분석

매칭된 상위 5개 공고의 공통점을 요약하여 "회사 티어 가이드"를 대체:

```json
{
  "top_5_pattern": {
    "common_tech_stack": ["Python", "Docker", "AWS"],
    "company_types": ["시리즈B 스타트업 3곳", "중견 IT기업 2곳"],
    "common_requirements": "REST API 설계 경험, 협업 도구 사용 경험"
  }
}
```

특정 회사를 티어로 분류하지 않으므로 논란 없이 "네 수준에서 어떤 회사들이 매칭되는가"를 보여줌.

### 3-4. 의존성 파일 파싱 (신규)

README가 비어 있을 때 프로젝트 정보를 보충하는 추가 소스.
GitHub tree API에서 이미 파일 목록을 갖고 있으므로 추가 API 호출 불필요.

| 파일 | 추출 정보 |
|---|---|
| package.json | dependencies → 프레임워크 (React, Express, Next.js 등) |
| requirements.txt | 라이브러리 (FastAPI, Django, PyTorch 등) |
| build.gradle / pom.xml | Java 프레임워크 (Spring Boot 등) |
| Gemfile | Ruby 프레임워크 (Rails 등) |
| go.mod | Go 모듈 |
| Cargo.toml | Rust 크레이트 |

파싱 결과를 `build_profile_text()`의 `frameworks` 필드로 전달.

### 3-5. 파일명/폴더명 도메인 감지 (신규)

**해결하는 문제:**
언어 통계와 의존성 파일만으로는 도메인을 오분류하는 케이스가 존재한다.
예: 유니티 의존성을 의도적으로 낮춘 C# 게임 코어 로직 레포 → C# SW 개발로 오분류.
README에 "유니티 UI 연결 가이드"가 있어도, 언어 통계의 "C# 기반 개발 경험"이 임베딩 벡터를 SW 쪽으로 끌어감.

**해결 방법:**
tree_data에서 이미 갖고 있는 전체 파일/폴더 목록의 **이름 패턴**을 분석하여 도메인 시그널을 추출한다.
추가 API 호출 불필요.

```python
# 도메인 키워드 사전 (파일명/폴더명 패턴)
DOMAIN_SIGNALS = {
    "게임 개발": ["game", "player", "enemy", "scene", "inventory", "combat",
                  "sprite", "level", "quest", "npc", "dungeon", "weapon",
                  "gamemanager", "playercontroller", "spawn"],
    "웹 프론트엔드": ["component", "page", "layout", "header", "footer",
                      "navbar", "sidebar", "modal", "hook", "store"],
    "서버/백엔드": ["controller", "service", "repository", "middleware",
                    "router", "handler", "migration", "schema", "endpoint"],
    "ML/AI": ["model", "train", "dataset", "inference", "predict",
              "embedding", "tokenizer", "epoch", "checkpoint"],
    "모바일 앱": ["activity", "fragment", "viewmodel", "storyboard",
                  "appdelegate", "widget", "screen"],
    "DevOps/인프라": ["terraform", "ansible", "helm", "k8s", "pipeline",
                      "deploy", "monitoring", "grafana"],
}

def detect_domain_from_tree(tree_data: dict) -> list[str]:
    """파일명/폴더명에서 도메인 시그널 감지. 최소 2개 이상 매칭 시 시그널로 인정."""
    all_paths = [item["path"].lower() for item in tree_data.get("tree", [])]

    domain_hits = {}
    for domain, keywords in DOMAIN_SIGNALS.items():
        hits = sum(1 for p in all_paths for kw in keywords if kw in p)
        if hits >= 2:
            domain_hits[domain] = hits

    return sorted(domain_hits, key=domain_hits.get, reverse=True)
```

**시그널 우선순위:**
도메인 감지 결과가 있으면 언어 통계보다 우선하여 `build_profile_text()`에 반영한다.

| 시그널 | 신뢰도 | 역할 |
|---|---|---|
| 파일명/폴더명 도메인 감지 | 높음 | 도메인 결정의 1차 시그널 |
| README 텍스트 키워드 | 높음 | 도메인 보강 + 프로젝트 설명 |
| 의존성 파일 | 중간 | 프레임워크 특정 |
| 언어 통계 | 낮음 (다의적) | 도메인 감지 실패 시 폴백 |

**build_profile_text() 반영:**

도메인 감지 없을 때: `"C# 기반 개발 경험"` → SW/솔루션 공고로 매칭 (오분류)
도메인 감지 있을 때: `"C# 기반 게임 개발 경험"` → 게임 클라이언트 공고로 매칭 (정분류)

```python
def build_profile_text(extracted_data: dict) -> str:
    parts = []

    # 도메인 감지 결과 우선 적용
    domains = extracted_data.get("detected_domains", [])
    langs = extracted_data.get("top_languages", "")

    if domains:
        parts.append(f"{langs} 기반 {domains[0]} 경험")
    elif langs:
        parts.append(f"{langs} 기반 개발 경험")

    # 프레임워크
    if extracted_data.get("frameworks"):
        parts.append(f"{', '.join(extracted_data['frameworks'])} 활용 경험")

    # CI/CD
    if extracted_data.get("has_cicd"):
        parts.append("CI/CD 파이프라인 구축 경험 (GitHub Actions 또는 Docker)")

    # 테스트
    if extracted_data.get("has_tests"):
        parts.append("테스트 코드 작성 경험 보유")

    # 배포
    if extracted_data.get("has_deployment"):
        parts.append("배포 환경 구성 경험")

    # README 요약 (정제 후 200자 이상인 경우만 포함)
    if extracted_data.get("readme_summary") and len(extracted_data["readme_summary"]) >= 200:
        parts.append(extracted_data["readme_summary"][:500])

    return ". ".join(parts) + "."
```

---

## 4. 파이프라인 B: 포트폴리오 진단

### 4-1. 진단 항목 (체크리스트 형태)

기존 github_score의 contribution/quality/consistency 3축을 **사용자 친화적 진단 항목**으로 재구성.
종합 점수 하나로 뭉개지 않고, 항목별로 개별 피드백 제공.

| 진단 항목 | 판별 방법 | 데이터 소스 |
|---|---|---|
| README 품질 | 정제 후 텍스트 길이, 스크린샷/GIF 포함 여부 | readme_data |
| 프로젝트 구조 | 디렉토리 모듈화, .gitignore 존재, 파일당 평균 LOC | tree_data |
| 테스트 작성 | test 파일 비율 (기존 로직 재활용) | tree_data |
| CI/CD 구성 | GitHub Actions / Dockerfile 존재 + 실질성 (기존 로직) | tree_data |
| 커밋 습관 | 커밋 메시지 평균 길이, 무의미 메시지 비율 | commits API |
| 배포 경험 | Dockerfile, docker-compose, Vercel/Netlify 설정 존재 | tree_data |
| 협업 경험 | 팀 프로젝트 레포에서 PR/이슈 참여 패턴 | commits API |
| 성장 궤적 | 시간순 코드 품질 변화 (초기 vs 최근 커밋 비교) | stratified samples |

### 4-2. 출력 형태

```json
{
  "portfolio_diagnosis": {
    "readme_quality": {
      "status": "양호",
      "detail": "평균 680자, 2개 레포에 스크린샷 포함",
      "action": null
    },
    "test_coverage": {
      "status": "미흡",
      "detail": "3개 레포 중 테스트 파일 존재 0개",
      "action": "주력 프로젝트에 pytest/Jest 테스트를 추가하세요. 테스트 커버리지는 채용 시 중요한 차별화 요소입니다."
    },
    "cicd": {
      "status": "양호",
      "detail": "GitHub Actions 워크플로우 감지 (1개 레포)",
      "action": null
    },
    "commit_quality": {
      "status": "개선 필요",
      "detail": "커밋 메시지 중 42%가 'fix', 'update' 등 무의미 메시지",
      "action": "Conventional Commits 형식(feat:, fix:, refactor:)을 적용해보세요."
    },
    "deployment": {
      "status": "미경험",
      "detail": "배포 관련 설정 파일 미감지",
      "action": "Dockerfile 또는 Vercel 배포를 추가하면 실무 경험으로 어필할 수 있습니다."
    }
  }
}
```

### 4-3. 기대 수준 가이드 (회사 티어 대체)

특정 회사를 이름으로 분류하지 않고, 포트폴리오 완성도 기준으로 시장 기대 수준을 제시:

| 레벨 | 충족 조건 | 설명 |
|---|---|---|
| Entry | README 존재, 프로젝트 1~2개 | 중소/중견 SI, 일반 스타트업 지원 가능 수준 |
| Competitive | + 테스트 코드 + CI/CD + 배포 경험 | 시리즈B+ 스타트업, IT 서비스 기업 경쟁력 있는 수준 |
| Top | + 오픈소스 기여 + 기술 블로그 + 복수 완성 프로젝트 | 대형 테크 기업 서류 통과 가능 수준 |

판별 기준은 진단 항목의 충족 개수로 결정 (룰 베이스).

### 4-4. 파일당 평균 LOC (Plan2 F1 유지)

Plan2의 Feature 1은 그대로 유지. 추가 API 호출 없이 구현 가능.

```
avg_loc_per_file = valid_loc / source_file_count

- avg_loc < 20       → 파편화 의심
- 20 ≤ avg_loc ≤ 300 → 정상 범위
- avg_loc > 300      → 모놀리식 의심
```

포트폴리오 진단의 "프로젝트 구조" 항목에 포함.

---

## 5. 파이프라인 C: 시장 연봉 밴드 (독립 제공)

### 5-1. 변경 핵심

**삭제하는 것:**
- `multiplier = 0.80 + (github_score / 100.0) * 0.45` — 근거 없는 공식
- `code_quality_factor`, `resume_factor` — LLM 기반 보정 계수 전체
- `recommended_salary` — 단일 추천 연봉 숫자
- `percentile_estimate` — github_score를 그대로 치환한 가짜 백분위

**유지하는 것:**
- 점핏/원티드 교차검증된 시장 연봉 데이터 (3,400개 공고 기반)
- 직무별 연차별 중앙값 조회 기능
- `route_job_category()` 직무 카테고리 라우팅

### 5-2. 신입 한정 출력 형태

```json
{
  "market_salary_band": {
    "matched_category": "서버/백엔드",
    "experience_level": "신입 (0~3년)",
    "salary_range": {
      "jumpit_median": 36498644,
      "wanted_median": 38354225,
      "combined_range": "3,500만 ~ 3,800만원"
    },
    "source": "점핏·원티드 2025 채용공고 기반",
    "note": "동일 직무 내에서 회사 규모, 지역, 협상력에 따라 차이가 있을 수 있습니다."
  },
  "category_comparison": [
    {"category": "인공지능/머신러닝", "junior_range": "3,900만 ~ 4,100만원"},
    {"category": "서버/백엔드", "junior_range": "3,500만 ~ 3,800만원"},
    {"category": "프론트엔드", "junior_range": "3,400만 ~ 3,500만원"},
    {"category": "QA 엔지니어", "junior_range": "3,100만 ~ 3,300만원"}
  ]
}
```

깃허브 점수로 밴드 안에서 위치를 "정밀하게" 찍지 않음.
대신 직무 간 비교 정보를 제공하여 직무 선택에 참고가 되도록 함.

---

## 6. 삭제된 Plan2 기능 목록 및 사유

| Plan2 기능 | 삭제 사유 |
|---|---|
| F2: LLM 코드 리뷰 레이어 | 외부 API 의존 제거. 비용 대비 효과 불확실. 데모 안정성 리스크 |
| F2-B: resume LLM 평가 | 룰베이스 변환 레이어로 대체. README 정보 밀도가 낮아 LLM 평가 신뢰도 부족 |
| F3: resume_depth_score 휴리스틱 | F2-B 폴백 용도였으나, F2-B 자체가 삭제되어 불필요 |
| code_quality_factor (±5%) | multiplier 구조 자체 삭제 |
| resume_factor (±3%) | multiplier 구조 자체 삭제 |
| recommended_salary 단일 숫자 | 근거 없는 가짜 정밀도. 밴드 범위 제공으로 대체 |
| percentile_estimate | github_score = percentile 동어반복. 삭제 |

---

## 7. LLM 사용 전략 (단계적 전환)

외부 API를 기본값으로 쓰지 않음. 필요 시 로컬 모델로 단계적 전환.

```
우선순위 1: 룰베이스 템플릿 (build_profile_text)
    ↓ 매칭 품질 테스트 후 부족하면
우선순위 2: 로컬 Qwen2-7B (RTX 4090에서 구동)
    ↓ 그래도 부족하면
우선순위 3: 외부 API (최후 수단, 여기까지 올 가능성 낮음)
```

**로컬 모델이 외부 API보다 나은 이유 (캡스톤 맥락):**
- 네트워크 의존 없음 → 데모 당일 API 장애 리스크 0
- 비용 0
- "오픈소스 모델을 로컬 배포해서 파이프라인에 통합" → 심사위원에게 시스템 설계 역량 어필
- "외부 의존성 없이 전체 파이프라인이 로컬 동작" → 종합설계 취지에 부합

---

## 8. README 활용 전략

### 8-1. README 잔량 기반 분기

```
_clean_markdown() 후 텍스트 길이
    ↓
[200자 이상] → 정제 텍스트 + 구조화 데이터로 프로필 생성 (LLM 불필요)
    ↓
[50~200자]  → 구조화 데이터(언어, 의존성 파일) 기반 템플릿 프로필
    ↓
[50자 미만] → 의존성 파일 파싱 시도
              ├─ 의존성 파일 있음 → 기술 스택 프로필 생성
              └─ 의존성 파일도 없음 → 매칭 입력에서 가중치 최소화
```

### 8-2. 원칙
- LLM은 "없는 정보를 만들어내는 마법사"가 아니라 "있는 걸 정리하는 편집자"
- README가 비어 있는데 프로젝트 목적을 "추론"하면 할루시네이션 리스크
- 정보가 없으면 "해당 프로젝트에 대한 상세 설명 없음"으로 정직하게 처리

---

## 9. 전체 파이프라인 (최종)

```
GitHub Username + 레포 URL 리스트
        ↓
GitHubExtractor (github_extractor.py)
  - API 수집 (커밋, 트리, README, 메타)
  - 균등 샘플링 + SHA dedup
  - 점수 산출 (contribution / quality / consistency)
  - 의존성 파일 파싱 (신규)
  - 파일명/폴더명 도메인 감지 (신규)
        ↓
github_score + score_breakdown + extracted_data + detected_domains
        ↓
[변환 레이어] build_profile_text() — 룰베이스 템플릿
  - 추출 데이터를 공고 문체 텍스트로 변환
  - README 잔량 기반 분기 처리
        ↓
FAISS 벡터 매칭 (jhgan/ko-sroberta-multitask)
  - 변환된 프로필 텍스트 → 임베딩
  - 3,400개 공고 인덱스에서 상위 5개 매칭
        ↓
[리포트 모듈 A] 직무 매칭 결과 + 매칭 공고 패턴 분석
[리포트 모듈 B] 포트폴리오 진단 체크리스트 + 개선 가이드 + 기대 수준
[리포트 모듈 C] 매칭 직무의 시장 연봉 밴드 (독립 조회)
        ↓
최종 통합 리포트 출력
```

---

## 10. 구현 우선순위

| 순위 | 작업 | 난이도 | 예상 공수 | 비고 |
|---|---|---|---|---|
| 1 | build_profile_text() 변환 레이어 구현 | 낮음 | 2~3시간 | 핵심 개선. 매칭 품질 직접 영향 |
| 2 | 의존성 파일 파싱 모듈 추가 | 낮음 | 2~3시간 | tree_data 재활용, API 불필요 |
| 3 | 파일명/폴더명 도메인 감지 모듈 | 낮음 | 2~3시간 | tree_data 재활용, 도메인 오분류 방지 핵심 |
| 4 | 포트폴리오 진단 체크리스트 모듈 | 중간 | 반나절 | 기존 지표 재구성 + 개선 가이드 템플릿 |
| 5 | valuation_engine.py 리팩토링 | 낮음 | 1~2시간 | multiplier 제거, 밴드 독립 제공으로 전환 |
| 6 | 기대 수준 가이드 (Entry/Competitive/Top) | 낮음 | 1~2시간 | 진단 항목 충족 개수 기반 룰 |
| 7 | 매칭 공고 패턴 분석 | 중간 | 반나절 | 상위 5개 공고 메타데이터 집계 |
| 8 | 파일당 평균 LOC (Plan2 F1) | 낮음 | 1~2시간 | tree_data 재활용, API 불필요 |
| 9 | 최종 리포트 출력 포맷 통합 | 중간 | 반나절 | 3개 모듈 병합 출력 |
| 10 | 매칭 품질 검증 + 필요시 로컬 Qwen 도입 | 높음 | 1~2일 | 룰베이스 결과 불충분 시에만 |

**권장 순서:** 1 → 2 → 3 → 5 → 4 → 6 → 7 → 8 → 9 → 10

---

## 11. 캡스톤 디자인 부합성

### 충족 항목
| 캡스톤 요구사항 | 충족 방법 |
|---|---|
| 현장문제 해결 | "신입 개발자가 자기 포트폴리오의 시장 경쟁력을 파악할 수 없다" — 실재하는 문제 |
| 기획→제작 전 과정 | 데이터 수집 → 분석 엔진 → 매칭 시스템 → 리포트 출력 전 과정 직접 수행 |
| 팀워크/종합설계 | 팀 프로젝트로 진행 |

### 보완 필요 항목
| 항목 | 현재 상태 | 보완 방법 |
|---|---|---|
| 산업체 연계 | ❌ 부족 | 현직 채용담당자/개발자 인터뷰 1~2건 확보 |
| 사용자 검증 | ❌ 없음 | 취준생 5~10명 대상 실사용 테스트 + 피드백 수집 |

### 산업체 연계 구체 방안
1. **현직자 인터뷰 (최소 요건):** IT 기업 채용담당자 또는 개발 팀장에게 "신입 채용 시 깃허브를 어떤 기준으로 보는지" + "진단 기준 검토" 요청
2. **부트캠프 연계 (이상적):** 패스트캠퍼스/코드스테이츠 수강생 대상 무료 진단 제공 → 피드백 수집
3. **학교 취업지원센터:** CS 학생 포트폴리오 경쟁력 진단 도구로 활용 제안

### 발표 프레이밍
```
1. 문제 정의: "신입 개발자가 자기 포트폴리오의 시장 경쟁력을 모른다"
2. 현장 검증: 현직 채용담당자 인터뷰를 통해 문제 실재 확인
3. 해결 방안: 기술 아키텍처 (FAISS, 임베딩, 비동기 크롤링 등)
4. 산업 연계: 현직자 피드백 반영 / 취준생 N명 실사용 테스트
5. 결과 및 확장성
```

---

## 12. 향후 확장 (발표에서 "1슬라이드" 언급용)

| 확장 방향 | 설명 |
|---|---|
| B2B 전환 | 동일 분석 엔진을 채용담당자 대상 스크리닝 도구로 제공 |
| 실시간 공고 연동 | 채용 플랫폼 API 연동으로 공고 DB 실시간 갱신 |
| 경력직 확장 | LinkedIn/이력서 데이터 결합 시 경력직 분석 가능 |
| LOC 기준값 상대화 | 지원자 데이터 누적 후 백분위 기반 상대 평가 전환 |

이 확장은 현재 구현 범위 밖이며, 캡스톤 발표에서 "사업 확장성"으로만 언급.

---

## 13. 리스크 및 보완

| 리스크 | 가능성 | 보완책 |
|---|---|---|
| 룰베이스 변환이 매칭 품질에 부족 | 중간 | 로컬 Qwen2-7B로 단계적 전환 |
| README 부실 레포가 다수 | 높음 | 의존성 파일 파싱 + "분석 불가" 정직한 표시 |
| 공고 데이터 노후화 | 낮음 (캡스톤 범위) | 수집 시점 명시, 실서비스 시 갱신 파이프라인 필요 |
| 진단 항목이 실제 채용 기준과 불일치 | 중간 | 현직자 인터뷰로 검증 (캡스톤 보완 항목과 겸용) |
| 신입 타겟이 너무 좁음 | 낮음 | 타겟이 좁을수록 문제 정의가 명확 — 캡스톤에서는 장점 |

---

*Git2Value Upgrade Plan v3 — Phase 4.0 — 2026.04.06*
