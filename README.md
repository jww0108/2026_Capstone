# 2026_Capstone

# Git2Value — 프로젝트 개요서

> 최종 갱신: 2026.06.01 | 스펙 버전: v4.0 | 구현 버전: v7.2-upgrade.7
> 대상 독자: 팀원 전원 (기획·개발·발표 준비용)

日本人の方はこの[文書](https://github.com/jww0108/2026_Capstone/blob/tekyung/README_JAPAN.md)を開いてください
---

## 1. 한 줄 소개

> **신입 개발자를 위한 깃허브 포트폴리오 진단 & 취업 전략 리포트 서비스**

GitHub 레포지토리를 분석하여 취준생에게 세 가지를 알려줍니다:
1. 어떤 직무 공고와 매칭되는가
2. 포트폴리오의 강점·약점·개선 우선순위는 무엇인가
3. 해당 직무의 시장 연봉 범위는 얼마인가

---

## 2. 왜 신입 전용인가

| | 경력직 | 신입(취준생) |
|---|---|---|
| 깃허브의 의미 | 전체 역량의 극히 일부 | 사실상 유일한 코드 포트폴리오 |
| 연봉 결정 변수 | 회사 경력, 협상력, 스톡옵션 등 깃허브 밖 변수가 지배적 | 회사 티어별 밴드가 좁아 범위 제시가 현실적 |
| 레벨 추정 필요성 | 시니어/주니어 구별 필요 (깃허브로 불가능) | 불필요 — 모두 신입 |
| 사용자 니즈 | 약함 (이미 LinkedIn, 헤드헌터 존재) | **강함** (취준생은 피드백에 굶주려 있음) |

---

## 3. 서비스 전체 구조

```
GitHub Username + 레포 URL 리스트 (최대 3개)
        ↓
┌─────────────────────────────────────────────┐
│           GitHubExtractor                   │
│  - GitHub API 비동기 수집                    │
│  - 균등 커밋 샘플링 + SHA 중복 제거          │
│  - 점수 산출 (Contribution 60 / Quality 30 / Consistency 10) │
│  - 커밋 품질 계수 + Fork/기여 비율 보정       │
│  - 의존성 파일 파싱 + 트리 기반 도메인 감지    │
└─────────────────────────────────────────────┘
        ↓
┌─────────────────────────────────────────────┐
│           프로필 변환 레이어                   │
│  build_profile_text()                       │
│  - 추출 데이터를 채용 공고 문체로 변환         │
│  - 도메인 감지 → 언어+도메인 결합 표현        │
│  - README 잔량 기반 분기 처리                │
└─────────────────────────────────────────────┘
        ↓
┌─────────────────────────────────────────────┐
│           FAISS 벡터 매칭                    │
│  jhgan/ko-sroberta-multitask 임베딩          │
│  3,400개 실제 채용 공고 인덱스               │
│  (원티드 2,000 + 점핏 1,000 + 리멤버 400)   │
└─────────────────────────────────────────────┘
        ↓
┌────────────────┬────────────────┬────────────────┐
│  모듈 A        │  모듈 B        │  모듈 C        │
│  직무 매칭     │  포트폴리오 진단 │  시장 연봉 밴드 │
│  (상위 5개 공고)│  (레포별 카드)  │  (독립 조회)   │
└────────────────┴────────────────┴────────────────┘
        ↓
      최종 통합 리포트
```

**핵심 설계 원칙:** 세 모듈은 완전히 독립적입니다. GitHub 점수는 합격/불합격 판정이나 연봉 산식이 아니라, 공개 포트폴리오 신호를 해석하는 진단 지표입니다.

---

## 4. 모듈 A: 직무 매칭

### 하는 일
지원자의 깃허브 프로필을 채용 공고 벡터 인덱스와 비교하여, 경력 조건을 거른 뒤 가장 유사한 공고 상위 5개를 추천합니다.

### 기술 구성

**임베딩 모델:** `jhgan/ko-sroberta-multitask` (한국어 특화)
**벡터 DB:** FAISS (CPU)
**유사도:** 코사인 유사도

### 프로필 변환 레이어

깃허브에서 추출한 데이터를 채용 공고와 **같은 문체**의 텍스트로 변환합니다.
이 변환이 없으면 깃허브 텍스트("Python (45%), C# (30%)")와 공고 텍스트("3년 이상 Spring Boot 경험자 우대")의 문체가 달라서 의미 있는 유사도가 나오지 않습니다.

변환 시 다음 시그널을 우선순위에 따라 결합합니다:

| 우선순위 | 시그널 | 예시 |
|---|---|---|
| 1순위 | 파일명/폴더명 도메인 감지 | GameManager.cs, PlayerController.cs → "게임 개발" |
| 2순위 | README 텍스트 키워드 | "유니티 UI 연결 가이드" → 게임 도메인 보강 |
| 3순위 | 의존성 파일 (package.json 등) | React, FastAPI → 프레임워크 특정 |
| 4순위 | 언어 통계 | C# 60%, Python 25% → 폴백 |

**변환 예시:**
- 변환 전: `"주요 기술 스택: C# (92%)\n\n[repo 요약]: REST API 서버를 구축했습니다"`
- 변환 후: `"C# 기반 게임 개발 경험. Unity 연동 설계. 테스트 코드 작성 경험 보유."`

### 도메인 감지

언어만으로는 도메인을 오분류하는 케이스가 있습니다 (예: C# 게임 레포 → SW 개발로 오분류).
파일/폴더 이름 패턴으로 도메인을 감지하여 이를 방지합니다.

```python
DOMAIN_SIGNALS = {
    "게임 개발":    ["game", "player", "enemy", "scene", "inventory", "combat", "spawn", ...],
    "웹 프론트엔드": ["component", "page", "layout", "header", "navbar", "modal", ...],
    "서버/백엔드":   ["controller", "service", "repository", "middleware", "router", ...],
    "ML/AI":        ["model", "train", "dataset", "inference", "embedding", ...],
    "모바일 앱":     ["activity", "fragment", "viewmodel", "storyboard", ...],
    "DevOps/인프라": ["terraform", "ansible", "helm", "k8s", "pipeline", ...],
}
# 최소 2개 이상 매칭 시에만 해당 도메인으로 인정
```

### 매칭 공고 패턴 분석

상위 5개 매칭 공고의 공통점을 요약하여 제공합니다.
특정 회사를 "티어"로 분류하지 않으므로 논란 없이 시장 감각을 전달합니다.

```json
{
  "top_5_pattern": {
    "common_tech_stack": ["Python", "Docker", "AWS"],
    "company_types": ["시리즈B 스타트업 3곳", "중견 IT기업 2곳"],
    "common_requirements": "REST API 설계 경험, 협업 도구 사용 경험"
  }
}
```

---

## 5. 모듈 B: 포트폴리오 진단

### 하는 일
깃허브 레포를 분석하여 레포별 카드 진단, 개선 가이드, GitHub Portfolio Tier를 알려줍니다.

### 진단 항목

| 진단 항목 | 판별 방법 | 데이터 소스 |
|---|---|---|
| README 품질 | 길이, 목적/기술/실행/환경/시각화 근거, 선택적 로컬 LLM 평가 | readme_data |
| 프로젝트 구조 | 디렉토리 모듈화, .gitignore 존재, 파일당 평균 LOC | tree_data |
| 테스트 작성 | test 파일 / 전체 소스 파일 비율 | tree_data |
| CI/CD 구성 | GitHub Actions / Dockerfile 존재 + 파일 크기 > 200B | tree_data |
| 커밋 메시지 | 무의미 메시지("fix", "update") 비율, Conventional Commits 개선 힌트 | commits API |
| 배포 경험 | Dockerfile, docker-compose, Vercel/Netlify 설정 존재 | tree_data |
| 커밋 리듬 | 지원자 기준 활성 주, 주당 커밋 빈도 | commits API |
| 성장성/활동 지속성 | active_weeks, duration_days, total_commits, repo_active_weeks | commits API |

### 출력 예시

```json
{
  "core_items": {
    "readme_quality": {
      "status": "개선 필요",
      "detail": "길이는 충분하지만 실행 방법과 기술 설명 근거가 부족합니다.",
      "action": "README에 실행 커맨드, 환경 변수, 기술 스택 설명을 추가하세요."
    },
    "project_structure": {
      "status": "양호",
      "detail": "디렉터리 구성과 .gitignore 존재 여부가 적절합니다.",
      "action": null
    },
    "commit_quality": {
      "status": "보통",
      "detail": "일부 커밋 메시지가 추상적입니다.",
      "action": "변경 의도가 드러나도록 한 줄 설명을 덧붙이세요."
    }
  },
  "extra_items": {
    "growth_signal": {
      "status": "성장 신호",
      "detail": "활동 주와 커밋 수 기준 지속 성장 흐름이 보입니다.",
      "action": "주 단위 기록을 유지하세요."
    }
  }
}
```

### 기대 수준 가이드

공개 GitHub 포트폴리오 성숙도에 따라 어느 수준인지 안내합니다. 개발자 역량 전체 등급이 아니라, 분석된 GitHub 활동과 문서화/운영 신호 기준입니다.

| 레벨 | 충족 조건 | 설명 |
|---|---|---|
| **Entry** | 기본 README/구조 신호 일부 존재 | 공개 GitHub 포트폴리오가 아직 보강 필요한 상태 |
| **Competitive** | 팀 경험 또는 운영 신호 + 복수 프로젝트 | 지원 직무와 연결 가능한 포트폴리오 신호가 있는 상태 |
| **Top** | README/구조/운영/활동 신호가 고르게 충족 | 공개 포트폴리오 운영·협업 신호가 매우 충실한 상태 |

---

## 6. 모듈 C: 시장 연봉 밴드

### 하는 일
매칭된 직무의 신입 시장 연봉 범위를 **깃허브 점수와 무관하게** 독립적으로 제공합니다.

### 왜 깃허브 점수로 연봉을 계산하지 않는가

- 깃허브 점수 X인 사람이 실제 연봉 Y를 받는다는 데이터가 존재하지 않음
- 연봉은 기술력의 함수가 아님 — 같은 실력이라도 회사, 지역, 협상력에 따라 2~3배 차이
- 근거 없는 정밀한 숫자("추천 연봉 4,823만원")는 서비스 신뢰도를 깎아먹음

### 데이터 기반

점핏·원티드 2025년 채용 공고에서 추출한 직무별·연차별 연봉 중앙값을 사용합니다.
두 플랫폼의 교차검증 결과, 신입 구간은 오차율 ±5% 이내로 수렴합니다.

### 출력 예시

```json
{
  "salary_band": {
    "matched_category": "서버/백엔드",
    "experience_level": "신입 (0~3년)",
    "salary_range": {
      "jumpit_median": 36498644,
      "wanted_median": 38354225,
      "combined_range": "3,500만 ~ 3,800만원"
    },
    "realistic_range": {
      "p25": 35000000,
      "p75": 42000000
    },
    "source": "점핏·원티드 2025 채용공고 기반",
    "reference_categories": [
      {"category": "인공지능/머신러닝", "combined_range": "3,900만 ~ 4,100만원"},
      {"category": "프론트엔드", "combined_range": "3,400만 ~ 3,500만원"}
    ]
  },
  "note": "연봉 밴드는 GitHub 점수와 독립적인 시장 참고값입니다."
}
```

직무 간 비교 정보를 함께 제공하여 직무 선택에 참고가 되도록 합니다.

---

## 7. GitHub 분석 엔진 상세

### 점수 구조 (3축 분해)

| 축 | 배점 | 산출 방식 |
|---|---|---|
| contribution (개발 활동량) | 최대 60점 | LOC/evidence LOC + 커밋 활동 이력, 커밋 품질 계수, Fork 보정 |
| quality (프로젝트 운영도) | 최대 30점 | 팀/개인 레포 기준별 CI/CD, 테스트, 활성 주 |
| consistency (작업 일관성) | 최대 10점 | 커밋 간격 표준편차 기반 |

`score_detail`에는 축별 세부 항목의 현재 점수, 만점, 개선 여지, 원시값이 포함됩니다.
커밋 항목은 `commit_score_100`에 `commit_quality_factor`를 적용한 `adjusted_commit_score_100` 기준으로 계산됩니다.

### 안티 치팅

- **Fork 감지:** fork 레포는 지원자 기여 비율에 따라 contribution 축만 보정
- **작성자 분리 수집:** 지원자 author 커밋과 레포 전체 커밋을 분리해 팀/개인 판정
- **SHA 중복 제거:** 레포 간 동일 커밋 중복 집계 방지
- **보일러플레이트 제거:** CRA, 프레임워크 기본 텍스트 자동 필터링

### 커밋 샘플링

전체 커밋을 초기/중간/최근 3구간에서 각 최대 25개씩 균등 추출합니다.
최근 커밋만 보는 편향을 방지합니다.

### Rate Limit 대응

모든 GitHub API 호출에 `Retry-After` 헤더 파싱 + 지수 백오프(최대 3회) 적용.
3회 실패 시 해당 레포를 명시적으로 스킵하고 경고를 출력합니다.

---

## 8. README 활용 전략

```
_clean_markdown() 후 텍스트 길이
    ↓
[200자 이상] → 키워드 추출 성공 시 매칭용 프로필 보강
    ↓
[50~200자]  → 구조화 데이터(언어, 의존성, 도메인 감지) 기반 템플릿 프로필
    ↓
[50자 미만] → 의존성 파일 파싱 + 도메인 감지 시도
              ├─ 시그널 있음 → 최소 프로필 생성
              └─ 시그널 없음 → "상세 분석 불가"로 정직하게 표시
```

**원칙:** 없는 정보를 만들어내지 않습니다. 정보가 부족하면 부족하다고 표시합니다. README는 100점 점수축에 직접 배점되지 않고, 진단/Tier gate/매칭 보조/evidence LOC에 간접 반영됩니다.

---

## 9. 기술 스택

| 구분 | 기술 |
|---|---|
| 언어 | Python |
| GitHub 데이터 수집 | aiohttp + asyncio (비동기) |
| 임베딩 모델 | jhgan/ko-sroberta-multitask |
| 벡터 검색 | FAISS (CPU) |
| 채용 공고 데이터 | 원티드 2,000 + 점핏 1,000 + 리멤버 400건 |
| 연봉 데이터 | 점핏·원티드 2025 직무별 연차별 중앙값 |
| API 서버 | FastAPI (`main.py`) |
| README 선택 평가 | 로컬 vLLM + `ReadmeEvaluator` |
| 환경 | Windows, Docker, PyTorch |

### 외부 API 의존성

**외부 LLM API 없음.** 전체 분석·매칭·진단 파이프라인은 로컬에서 동작합니다.
GitHub API(데이터 수집)와 Hugging Face 모델 다운로드를 제외하면 외부 서비스 호출이 없습니다.

---

## 10. 파일 구조

```
basic/
├── github_extractor.py      # GitHub 분석 엔진 (핵심)
├── profile_builder.py       # 도메인·엔진 시그니처 감지, 매칭용 프로필 생성
├── portfolio_diagnosis.py   # 레포별 카드 진단 + Portfolio Tier
├── valuation_engine.py      # 시장 연봉 밴드 조회
├── experience_filter.py     # 경력 요건 필터링
├── run_git2value.py         # E2E 파이프라인 실행 + Git2ValuePipeline
├── main.py                  # FastAPI 분석/README 평가 API
├── llm_readme_evaluator.py  # 로컬 LLM README 평가
├── requirements.txt         # 의존성
├── .env                     # GitHub API 토큰 (버전 관리 제외)
│
├── vector/
│   ├── git2value_faiss.index   # FAISS 인덱스 (3,400개 공고)
│   ├── git2value_metadata.json # 공고 메타데이터
│   ├── unified_jd_corpus.jsonl # JD 원문 코퍼스
│   └── experience_cache.json   # 경력 필터 캐시
│
├── data/
│   ├── jumpit_data/          # 점핏 연봉 룩업 테이블
│   ├── wanted_data/          # 원티드 연봉 데이터
│   └── *.py                  # 데이터 수집/파싱 스크립트
│
├── tests/              # 도메인/회귀 테스트
├── response_sample/    # 프론트 응답 예시 JSON
├── ml/                 # AI 직무 분류 연구용 (프로덕션 도입 보류)
├── experiments/        # FAISS/룰/AI 리랭킹 비교 실험
└── md/                 # 보조 문서
```

---

## 11. 실행 방법

### 사전 준비
1. `.env` 파일에 `Github_api_token` 설정
2. `pip install -r requirements.txt`
3. `vector/` 폴더에 FAISS 인덱스 파일 존재 확인

### 실행
```bash
# E2E 파이프라인 (전체 흐름)
python run_git2value.py

# FastAPI 서버
python main.py

# GitHub 분석만 단독 실행
python github_extractor.py

# 연봉 밴드 조회만 단독 테스트
python valuation_engine.py
```

`run_git2value.py`의 `__main__` 블록에서 `TARGET_USERNAME`, `TARGET_REPOS`, `APPLICANT_YEARS`를 수정하여 분석 대상을 변경합니다.

---

## 12. 캡스톤 디자인 전략

### 발표 구조

```
1. 문제 정의
   "신입 개발자가 자기 포트폴리오의 시장 경쟁력을 파악할 수 없다"

2. 현장 검증
   현직 채용담당자 인터뷰를 통해 문제가 실재함을 확인
   (→ 팀에서 인터뷰 1~2건 확보 필요)

3. 해결 방안
   기술 아키텍처 설명 (FAISS, 임베딩, 비동기 크롤링 등)

4. 산업 연계
   현직자 피드백을 진단 기준에 반영
   취준생 5~10명 대상 실사용 테스트 결과

5. 결과 및 확장성
```

### 반드시 보완해야 할 항목

| 항목 | 방법 |
|---|---|
| **산업체 연계** | IT 기업 채용담당자 또는 개발 팀장 인터뷰 1~2건 |
| **사용자 검증** | 취준생 5~10명에게 실제 깃허브 분석 → 피드백 수집 |

### 향후 확장 (발표 1슬라이드용)

| 확장 방향 | 설명 |
|---|---|
| B2B 전환 | 채용담당자 대상 기능은 현재 로드맵으로 분리 |
| 실시간 공고 연동 | 채용 플랫폼 API 연동으로 공고 DB 실시간 갱신 |
| 경력직 확장 | LinkedIn/이력서 결합 시 경력직 분석 가능 |
| 직무별 독립 Tier | Backend/DevOps/AI/Data 등 직무별 포트폴리오 티어 분리 |

---

## 13. 알려진 한계

이 시스템이 **할 수 없는 것**을 명확히 인지하고 사용해야 합니다.

| 한계 | 이유 |
|---|---|
| 깃허브 없는 지원자 분석 불가 | 입력 데이터 자체가 없음 |
| 코드 전체 품질 판단 불가 | 샘플 기반 간접 평가의 본질적 한계 |
| 정확한 연봉 예측 불가 | 깃허브 점수와 연봉 사이 검증된 상관관계 부재 |
| 깃허브를 안 쓰는 개발자 커버 불가 | 신입 중에서도 깃허브를 적극 관리하는 비율은 일부 |
| 면접 합격 여부 예측 불가 | 컬쳐핏, 면접 퍼포먼스 등 깃허브 밖 변수 |
| 직무별 독립 티어 미지원 | 현재는 Primary Domain Portfolio Tier 중심 |

---

*Git2Value — 프로젝트 개요서 v4.0 / 구현 v7.2-upgrade.7 — 2026.06.01*
