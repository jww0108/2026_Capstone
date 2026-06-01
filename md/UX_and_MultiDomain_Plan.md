# Git2Value — 사용자 경험 개선 및 다중 도메인 균형 추천 계획

> 작성일: 2026.04.28 | 대상 버전: v5.8 → v6.0
> 발견 계기: 팀원 1차 개선안 (모듈 A/B/C 전반) + 다중 도메인 출력 구조 재고

---

## 1. 배경 및 범위

### 1-1. 두 갈래의 피드백

본 계획은 두 갈래의 피드백을 통합한다:

(가) **팀원 1차 개선안**: 시스템 설계자 관점이 아닌 **사용자(취준생) 관점**에서의 출력 품질 점검. 진단/매칭 결과가 사용자에게 어떻게 읽히는지를 중심으로 한 개선 제안.

(나) **다중 도메인 환경 재고**: v5.6/v5.7에서 시그너처 기반 환경 식별 체계가 정착되면서, 다중 도메인 프로젝트의 출력 구조 자체를 재검토할 필요가 발생함.

### 1-2. 본 계획에서 다루지 않는 것

- LLM 도입 (외부 API 0 원칙과 충돌, 발표 후 v7 검토)
- 신뢰도별 차등 가산점 (데이터 기반 검증 후 v7 검토)
- 신규 시그너처 추가 (v5.8에서 처리)

---

## 2. 모듈 A 개선

### 2-1. 약한 매칭 신호 직접 알림 (팀원 A-1)

**현재 문제:**
- 5개 점수가 0.79~0.82(spread 0.03)에 몰리면 1순위만 "높음", 나머지 "낮음"
- 사용자는 "1순위만 맞고 나머지는 별로"로 오해
- 실제 의미는 "프로필이 어느 직무와도 강하게 매칭되지 않음"

**해결 방향:**

```python
def similarity_label(score: float, top5_scores: list[float]) -> tuple[str, str | None]:
    """
    Returns (label, system_note)
    - label: "높음"/"보통"/"낮음" (개별 공고용)
    - system_note: 5개 전체 분포 분석에 따른 시스템 안내 (없으면 None)
    """
    max_s = max(top5_scores)
    min_s = min(top5_scores)
    spread = max_s - min_s
    avg = sum(top5_scores) / len(top5_scores)

    # 분포 분석: 5개가 좁은 구간에 몰림 = 약한 매칭
    if spread < 0.02:
        if avg < 0.65:
            note = (
                "상위 5개 공고가 모두 비슷한 낮은 유사도에 몰려 있습니다. "
                "프로필이 특정 직무와 강하게 매칭되지 않는 신호로, "
                "README 보강 또는 프로필 텍스트 명확화가 필요합니다."
            )
        else:
            note = (
                "상위 5개 공고의 유사도가 비슷한 수준입니다. "
                "여러 직무가 모두 일정 수준 매칭되는 다재다능한 프로필이거나, "
                "직무 색깔이 뚜렷하지 않은 상태일 수 있습니다."
            )
        # 개별 레이블은 평균 기준
        if score >= avg + 0.005:
            return "높음", note
        if score >= avg - 0.005:
            return "보통", note
        return "낮음", note

    # 정상 분포: 기존 로직
    if score >= max_s - spread * 0.1:
        return "높음", None
    if score >= max_s - spread * 0.4:
        return "보통", None
    return "낮음", None
```

**출력 예시:**
```
[1순위] [회사A] 백엔드 개발자  (0.8244 · 보통)
[2순위] [회사B] 백엔드 개발자  (0.8175 · 보통)
[3순위] [회사C] 풀스택         (0.8089 · 보통)
[4순위] [회사D] SW 개발        (0.8075 · 보통)
[5순위] [회사E] 웹 개발        (0.8042 · 낮음)

⚠ 매칭 분포 안내: 상위 5개 공고가 모두 비슷한 유사도에 몰려 있습니다.
   여러 직무가 일정 수준 매칭되는 다재다능한 프로필이거나, 직무 색깔이
   뚜렷하지 않은 상태일 수 있습니다.
```

### 2-2. 경력직 공고 필터링 (팀원 A-2) ⭐ 최우선

**현재 문제:** "경력 3-5년차" 공고가 신입 1순위로 나옴. 지원 자체가 불가능한 결과.

**해결 방향:**

1단계: 공고 메타데이터에서 경력 요건 추출 (전처리)
```python
# vector/git2value_metadata.json 빌드 시 추가 필드
import re

EXPERIENCE_PATTERNS = [
    (r"경력\s*(\d+)\s*[년~\-]\s*(\d+)?\s*년", "min_years_exp"),
    (r"(\d+)\s*년\s*이상", "min_years_exp"),
    (r"(\d+)\s*년차", "specific_years"),
    (r"신입", "junior_only"),
    (r"주니어|junior", "junior_only"),
    (r"시니어|senior|lead|리드", "senior_only"),
]

def extract_experience_requirement(position: str, text: str = "") -> dict:
    """공고 제목 + 본문에서 경력 요건 추출."""
    combined = (position + " " + text).lower()
    result = {"min_years": 0, "is_junior_friendly": True, "raw_label": None}

    for pattern, kind in EXPERIENCE_PATTERNS:
        m = re.search(pattern, combined)
        if not m:
            continue
        if kind == "junior_only":
            result["is_junior_friendly"] = True
            result["raw_label"] = "신입"
            return result
        if kind == "senior_only":
            result["is_junior_friendly"] = False
            result["min_years"] = 5
            result["raw_label"] = "경력"
            return result
        if kind == "min_years_exp":
            years = int(m.group(1))
            result["min_years"] = years
            result["is_junior_friendly"] = years <= 1
            result["raw_label"] = f"{years}년 이상"
            return result
        if kind == "specific_years":
            years = int(m.group(1))
            result["min_years"] = years
            result["is_junior_friendly"] = years <= 3
            result["raw_label"] = f"{years}년차"
            return result

    return result  # 경력 명시 없으면 모두에게 열림
```

2단계: 매칭 시점에 필터링 또는 표시
```python
def filter_by_experience(top_matches: list[dict], applicant_years: int) -> list[dict]:
    """
    신입(0~3년) 지원자에게 명백한 경력직 공고는 후순위로.
    완전 제외가 아닌 표시 + 정렬 조정 (정보는 보존).
    """
    junior = applicant_years <= 3

    if not junior:
        return top_matches  # 경력 지원자는 필터링 불필요

    eligible = []
    flagged = []

    for m in top_matches:
        meta = m["meta"]
        exp_req = meta.get("experience_requirement", {})
        min_years = exp_req.get("min_years", 0)

        if min_years > applicant_years + 1:  # 1년 여유 허용
            m["experience_warning"] = exp_req.get("raw_label", "경력직")
            flagged.append(m)
        else:
            eligible.append(m)

    # 적합 공고 우선, 경력직은 뒤로 + 경고 표시
    return eligible + flagged
```

**출력 예시:**
```
[1순위] [회사A] 백엔드 개발자(신입~3년)         (0.7234 · 높음)
[2순위] [회사B] 백엔드 주니어                   (0.7102 · 보통)
[3순위] [회사C] 백엔드 개발자                   (0.6985 · 보통)
[4순위] [회사D] 백엔드 개발자(3년 이상) ⚠경력직  (0.7456 · 높음)
        → 지원 가능 경력에 미달합니다.
```

**구현 비용:** 메타데이터 한 번 갱신 + 필터 함수 추가. 약 2시간.

### 2-3. 도메인 불일치 원인 분기 (팀원 A-3)

**현재 문제:** 두 원인을 동시에 나열.

**해결 방향:**

```python
def diagnose_domain_mismatch(detected_domains, top_matches, domain_hits) -> dict:
    """불일치 원인을 명확히 분기."""
    if not detected_domains:
        return {"type": "no_signal", ...}

    primary = detected_domains[0]
    expected = DOMAIN_TO_CATEGORIES.get(primary, [])

    # 상위 5개 중 일치 카테고리 수
    match_count = sum(1 for m in top_matches if m["category"] in expected)

    # 도메인 감지 강도
    primary_hits = domain_hits.get(primary, 0)

    if match_count == 0 and primary_hits >= 5:
        # 도메인 감지는 강한데 일치 공고가 0개 → DB 커버리지 문제
        return {
            "type": "db_coverage",
            "message": (
                f"'{primary}' 도메인이 명확히 감지되었으나 "
                f"채용 공고 DB에 해당 직무 공고가 적습니다. "
                f"이는 시스템의 한계로, 실제 채용 시장에서 해당 직무 공고를 "
                f"별도로 검색하시기 바랍니다."
            ),
        }

    if match_count == 0 and primary_hits < 3:
        # 도메인 감지가 약함 → 프로필 보강 필요
        return {
            "type": "weak_signal",
            "message": (
                f"'{primary}' 도메인 신호가 약하게 감지되었습니다. "
                f"README에 해당 직무 키워드(기술 스택, 프로젝트 성격)를 "
                f"명시하면 매칭 정확도가 올라갑니다."
            ),
        }

    if match_count > 0:
        return {"type": "consistent", ...}

    # 그 외 모호한 경우
    return {"type": "ambiguous", "message": "..."}
```

### 2-4. 공고 분류 태그 버그 (팀원 A-4) ⭐ 즉시 수정

**현재 문제:** "SW/솔루션,devops/시스템 엔지니어,서버/백엔드 개발자 유사 공고 1건" — 한 태그에 카테고리 3개 결합.

**원인 추정:**
- 공고 메타데이터 `position` 필드에 콤마로 구분된 다중 직무 표기
- `route_job_category()`가 첫 매칭에서 멈추지 않고 모든 매칭을 콤마로 합침
- 또는 메타데이터 빌드 시 `category` 필드가 이미 콤마 결합된 상태

**해결 방향:**

```python
# 1. route_job_category 결과 검증
def route_job_category_safe(position: str) -> str:
    """반드시 단일 카테고리 반환. 콤마 포함 여부 검증."""
    result = route_job_category(position)
    if "," in result:
        # 버그 발견 시 첫 카테고리만 반환
        return result.split(",")[0].strip()
    return result

# 2. Counter 결합 시 키 검증
categories = [
    route_job_category_safe(m["meta"].get("position", ""))
    for m in top_matches
]
# 콤마 포함 키 필터링 (방어적)
categories = [c for c in categories if c and "," not in c]
```

근본 원인은 디버깅으로 코드 추적 후 정확히 짚어야 함. 위는 방어 코드.

### 2-5. 기술 미보유 리스트 도메인 필터링 (팀원 A-5)

**현재 문제:** 게임 개발자에게 Java/Spring/Vue 미보유 표시 → 직무 무관 노이즈.

**해결 방향:** `analyze_tech_match()`가 도메인 감지 결과와 일치하는 공고의 요구 기술만 추출.

```python
def analyze_tech_match(
    applicant_languages: str,
    applicant_frameworks: list[str],
    top_matches: list[dict],
    detected_domains: list[str],   # v6.0 추가
) -> dict:
    # 도메인 일치 공고만 필터링
    if detected_domains:
        primary = detected_domains[0]
        expected = DOMAIN_TO_CATEGORIES.get(primary, [])
        relevant_matches = [m for m in top_matches if m["category"] in expected]
        if not relevant_matches:
            # 일치 공고가 없으면 전체 사용 (퇴행 방지)
            relevant_matches = top_matches
    else:
        relevant_matches = top_matches

    # 이하 기존 로직 (relevant_matches 기준으로 추출)
    ...
```

**효과:** 게임 도메인 감지 시 게임 공고들이 요구하는 기술(Unity, C#, C++, Unreal 등)만 미보유 분석에 포함.

---

## 3. 다중 도메인 균형 추천 모드 (신규)

### 3-1. 배경

v5.3.1의 다중 도메인 억제는 "리랭킹을 안 함 → FAISS 원본 그대로"였음.
하지만 풀스택 프로젝트(예: DeepSentinel)에서 FAISS 원본은 우연히 프론트엔드 5개로 채워질 수 있어, 사용자에게 ML/AI 매칭 결과가 보이지 않음.

**사용자 가치 관점에서, 다중 도메인 프로젝트는 각 도메인별 추천이 더 의미 있음.**

### 3-2. 동작 설계

```python
def recommend_multi_domain(
    top_matches_extended: list[dict],   # 상위 5개가 아닌 15~20개
    detected_domains: list[str],
    domain_hits: dict[str, int],
) -> dict:
    """
    다중 도메인 시 도메인별 균형 추천.
    각 도메인 카테고리에서 상위 1~2개씩 추출.
    """
    if len(detected_domains) < 2:
        return None  # 단일 도메인은 기존 로직

    # 다중 도메인 판정 (v5.3.1과 동일 기준)
    hits = sorted(domain_hits.values(), reverse=True)
    if len(hits) < 2 or hits[0] >= hits[1] * 2:
        return None  # 단일 우세 도메인

    # 각 도메인의 기대 카테고리 수집
    domain_to_picks: dict[str, list] = {}
    for domain in detected_domains[:3]:  # 상위 3개 도메인까지
        expected_cats = DOMAIN_TO_CATEGORIES.get(domain, [])
        if not expected_cats:
            continue

        domain_picks = []
        for m in top_matches_extended:
            if m["category"] in expected_cats:
                domain_picks.append(m)
            if len(domain_picks) >= 2:
                break
        if domain_picks:
            domain_to_picks[domain] = domain_picks

    return {
        "is_multi_domain": True,
        "domain_picks": domain_to_picks,
        "raw_top5": top_matches_extended[:5],  # 참고용 원본
    }
```

### 3-3. FAISS 검색 범위 확장

다중 도메인 추천을 위해 상위 5개가 아닌 15~20개를 가져와야 함.

```python
# run_git2value.py
distances, indices = index.search(query_vector, 20)  # 5 → 20
top_matches_extended = build_match_list(distances, indices, metadata)

# 단일 도메인이면 상위 5개만 사용
# 다중 도메인이면 도메인별 분배에 활용
```

### 3-4. 출력 예시

**DeepSentinel (웹 프론트엔드 + ML/AI + DevOps):**
```
[모듈 A] 직무 매칭 — 다중 도메인 프로젝트

이 레포지토리는 풀스택/혼합 프로젝트로 분류되어, 각 도메인별로 균형 추천합니다.

▼ 웹 프론트엔드 매칭
  [1] [오투플러스] 프론트엔드 개발자        (0.8550)
  [2] [콘텐츠웨이브] 웹 프론트엔드          (0.8446)

▼ ML/AI 매칭
  [1] [코드러닝] AI 엔지니어                (0.8123)
  [2] [업스테이지] ML 엔지니어 신입         (0.7956)

▼ DevOps/인프라 매칭
  [1] [이수시스템] DevOps 엔지니어          (0.7654)

종합 분석:
  · 가장 강한 매칭은 웹 프론트엔드 영역입니다 (유사도 0.85+).
  · 풀스택 경험을 어필하려면 README에 각 영역의 기여를 명시하세요.
  · ML/AI 직무 지원 시 모델 학습/추론 부분 강조가 필요합니다.
```

### 3-5. 단일 도메인은 기존 방식 유지

```python
if multi_domain_result:
    # 다중 도메인 균형 추천
    print_multi_domain_matches(multi_domain_result)
else:
    # 단일 도메인: 기존 +0.05 가산점 적용 + 상위 5개 출력
    print_single_domain_matches(top_matches_extended[:5])
```

가산점 +0.05는 **단일 도메인에서만 작동**하므로 그대로 유지. 다중 도메인에서는 카테고리별 분배가 가산점 역할을 대체.

---

## 4. 모듈 B 개선

### 4-1. 항목 정리: 9개 → 7개

**제거 항목:**
- 커밋 리듬 (개인 레포에서 무의미, Consistency 점수와 중복)
- 성장 궤적 (커밋 메시지 길이 기반 판단의 신뢰도 낮음)

**유지 항목 (7개):** README 품질, 프로젝트 구조, 테스트, CI/CD, 커밋 메시지, 배포, 협업

이 변경은 **논문 표 1과도 일치**시킴. 9개 → 7개는 "의미 없는 항목을 빼는 정직한 시스템"으로 어필 가능.

### 4-2. 커밋 메시지 변환 힌트 (팀원 B-5)

```python
COMMIT_REWRITE_HINTS = {
    r"^fix\s*$":        "fix: [무엇을] 수정",
    r"^update\s*$":     "refactor: [무엇을] 개선",
    r"^wip\s*$":        "feat: [기능명] 구현 중",
    r"^test\s*$":       "test: [대상] 단위 테스트 추가",
    r"^initial\s+commit\s*$": "chore: 프로젝트 초기 설정",
    r"^merge.*":        "merge: [브랜치명] 병합",
    r"^chore\s*$":      "chore: [작업] 정리",
}

def get_rewrite_hint(msg: str) -> str:
    for pattern, hint in COMMIT_REWRITE_HINTS.items():
        if re.search(pattern, msg.strip(), re.I):
            return hint
    return "feat/fix/refactor: 변경 내용 구체적으로 기술"

# 진단 출력
bad_samples = [m for m in commit_messages
               if MEANINGLESS_COMMIT_PATTERNS.search(m.strip())][:2]

if bad_samples:
    hint = get_rewrite_hint(bad_samples[0])
    action_message = (
        f"실제 커밋 예시: '{bad_samples[0]}'\n"
        f"개선 방향: '{hint}'\n"
        f"Conventional Commits 형식 적용을 권장합니다."
    )
```

### 4-3. 협업 항목 재구성 (팀원 B-8)

**선택 B 채택:** 항목 제거 + 레포 분류 안내로 대체.

```python
# portfolio_diagnosis.py에서 협업 항목 제거
# 대신 per_repo 출력에 분류 표시
def repo_classification_note(repo: dict) -> str:
    distinct = repo.get("distinct_author_count", 1)
    if distinct >= 2:
        return f"{repo['repo_name']}: {distinct}명이 함께 작업한 팀 프로젝트"
    return f"{repo['repo_name']}: 단독 작업 레포"
```

**출력 위치:** [지원자 요약] 블록 또는 [프로젝트 분류 안내] 블록 (v5.7에서 도입한 위치).

### 4-4. README 품질: 룰베이스 유지 + LLM 도입 보류

팀원이 LLM 사용 제안했으나, 외부 API 0 원칙과 충돌. v6.0에서는 **룰베이스 유지**, v7에서 로컬 모델(Qwen2-7B) 검토.

**대신 룰베이스 강화:**

```python
README_QUALITY_INDICATORS = {
    "프로젝트 목적 명시": [
        r"^#\s*[가-힣\w].{5,}",   # H1 제목
        r"##\s*소개|introduction|overview|개요",
        r"##\s*프로젝트\s*목적|purpose|goal",
    ],
    "기술 스택 설명": [
        r"##\s*기술\s*스택|tech\s*stack|technologies",
        r"##\s*사용\s*기술|stack",
    ],
    "결과물 시각화": [
        r"!\[.*\]\(.*\)",   # 마크다운 이미지
        r"<img\s+src=",     # HTML 이미지
        r"https?://.*\.(gif|png|jpg|jpeg|mp4|webm)",
    ],
}

def evaluate_readme_quality(readme_text: str) -> dict:
    indicators = {}
    for name, patterns in README_QUALITY_INDICATORS.items():
        found = any(re.search(p, readme_text, re.I | re.M) for p in patterns)
        indicators[name] = found

    found_count = sum(indicators.values())
    if found_count >= 2:
        return {"status": "양호", "indicators": indicators}
    if found_count == 1:
        return {"status": "보통", "indicators": indicators}
    return {"status": "미흡", "indicators": indicators}
```

룰베이스로도 "프로젝트 목적 명시 / 기술 스택 설명 / 결과물 시각화" 3가지 차원 평가 가능. 글자수 단일 기준보다 훨씬 풍부함.

### 4-5. 종합 메시지 추가 (팀원 B-총합) ⭐ 매우 중요

진단 9개(축소 후 7개) 항목을 나열한 후, **사용자가 실제로 가져갈 수 있는 종합 메시지** 추가.

```python
def generate_summary_block(diagnosis: dict, expected_level: dict, github_score: float) -> str:
    """
    [한 줄 포지셔닝]
    [강점 1~2개]
    [이번 주 quick wins 1~3개]
    """
    # 1. 한 줄 포지셔닝
    level = expected_level["level"]
    primary_domain = ...  # 도메인 감지 결과
    positioning = (
        f"{primary_domain} {level} 수준 포트폴리오 — "
        f"{'경쟁력 있는 지원을 위해 보강 필요' if level == 'Entry' else '주요 항목 보강 시 상위 도전 가능'}"
    )

    # 2. 강점 추출 (양호 항목 중 상위 2개)
    strengths = []
    priority_items = ["readme_quality", "commit_quality", "project_structure", "test_coverage"]
    for key in priority_items:
        item = diagnosis.get(key, {})
        if item.get("status") == "양호":
            label = DIAG_LABELS_KO.get(key, key)
            strengths.append(label)
        if len(strengths) >= 2:
            break

    # 3. Quick wins (미흡/개선필요 항목 중 즉시 실행 가능한 것)
    quick_wins_pool = [
        ("cicd", "GitHub Actions 워크플로우 1개 추가 (Python: pytest, Node: jest)"),
        ("deployment", "Dockerfile 작성 + docker-compose.yml로 로컬 실행 가능하게 구성"),
        ("readme_quality", "README에 프로젝트 목적 + 기술 스택 + 스크린샷 1장 추가"),
        ("commit_quality", "다음 커밋부터 Conventional Commits 적용 (feat:/fix:/refactor:)"),
        ("test_coverage", "핵심 비즈니스 로직 1~2개에 단위 테스트 추가"),
    ]
    quick_wins = []
    for key, action in quick_wins_pool:
        item = diagnosis.get(key, {})
        if item.get("status") in ("미흡", "개선필요", "미경험"):
            quick_wins.append(action)
        if len(quick_wins) >= 3:
            break

    # 출력 조립
    output = [
        "─" * 60,
        "[종합 분석]",
        "─" * 60,
        f"  포지셔닝: {positioning}",
        "",
        f"  강점:",
    ]
    for s in strengths:
        output.append(f"    · {s}")
    output.append("")
    output.append("  이번 주 실행 가능한 개선 (Quick Wins):")
    for i, qw in enumerate(quick_wins, 1):
        output.append(f"    {i}. {qw}")

    return "\n".join(output)
```

**출력 예시:**
```
────────────────────────────────────────────────────────────
[종합 분석]
────────────────────────────────────────────────────────────
  포지셔닝: 서버/백엔드 Entry 수준 포트폴리오 — 경쟁력 있는 지원을 위해 보강 필요

  강점:
    · README 품질
    · 커밋 메시지

  이번 주 실행 가능한 개선 (Quick Wins):
    1. GitHub Actions 워크플로우 1개 추가 (Python: pytest, Node: jest)
    2. Dockerfile 작성 + docker-compose.yml로 로컬 실행 가능하게 구성
    3. 핵심 비즈니스 로직 1~2개에 단위 테스트 추가
```

**효과:** 사용자가 진단 결과 9개를 보고 "그래서 뭐 어쩌라고?" 되지 않게 실행 가능한 행동 안내 제공. 발표에서도 "이 시스템이 사용자에게 무엇을 주는가?"의 강한 답이 됨.

---

## 5. 모듈 C 개선

### 5-1. 연봉 범위를 현실적으로 확장 (팀원 C-1)

**현재 문제:** 점핏 3,724만 vs 원티드 3,677만 → 47만원 차이. "정밀하지만 좁은" 인상.

**해결 방향:**

```python
def realistic_salary_range(jumpit_median: int, wanted_median: int) -> dict:
    """
    실제 분포 감각을 주는 범위.
    중앙값 기준 ±15%/+20% 비대칭 (상위 분산이 더 큼).
    """
    median = (jumpit_median + wanted_median) // 2 if wanted_median else jumpit_median
    return {
        "median": median,
        "p25_estimate": int(median * 0.85),   # 하위 25%
        "p75_estimate": int(median * 1.20),   # 상위 75%
        "narrow_range": (
            min(jumpit_median, wanted_median) if wanted_median else jumpit_median,
            max(jumpit_median, wanted_median) if wanted_median else jumpit_median,
        ),  # 기존 좁은 범위 (참고용)
    }
```

**출력 예시:**
```
[모듈 C] 시장 연봉 밴드 — 신입(0~3년)

  매칭 직무: 서버/백엔드
  
  시장 중앙값: 약 3,700만원
  실제 분포:   3,145만 ~ 4,440만원 (회사 규모·지역·협상에 따라)
  
  플랫폼 교차검증 (좁은 범위, 참고):
    점핏: 3,724만 / 원티드: 3,677만 (오차 ±5% 이내 수렴)
```

좁은 범위(±5%)는 신뢰도 검증 자료로 별도 표기. 사용자에게 보여주는 "실제 분포"는 ±15%/+20%로 넓힘.

### 5-2. 직무 불일치 사용자 언어 설명 (팀원 C-2)

**현재 문제:**
```
매칭 직무: SW/솔루션
(참고: 게임 클라이언트)
```
왜 두 개 나오는지 설명 없음.

**해결 방향:**

```
매칭 직무: SW/솔루션
  → 채용공고 텍스트 유사도 기준 매칭 결과입니다.

참고 직무: 게임 클라이언트
  → 레포지토리 파일 구조(게임 도메인 감지) 기준입니다.
  → 두 직무의 연봉 범위가 다르므로 둘 다 확인하세요.

[불일치 시 행동 안내]
  두 직무가 일치하지 않는 이유: 레포지토리 코드와 공고 텍스트가
  서로 다른 직무 신호를 보냅니다.
  → 지원하려는 직무가 '게임 클라이언트'라면 README에 
    Unity/게임 개발 키워드를 명시하면 매칭 정확도가 올라갑니다.
```

### 5-3. 직무 비교 그룹화 (팀원 C-3) ⭐ 매우 가치 큼

**현재 문제:** 상위 6개 직무를 연봉 순으로 나열 → "그럼 나 블록체인 해야 하나?" 오해 유발.

**해결 방향:** `DOMAIN_TO_CATEGORIES` 역방향 활용으로 인접 직무 도출.

```python
# DOMAIN_TO_CATEGORIES 역매핑 (이미 정의된 것 활용)
CATEGORY_TO_DOMAINS = {}  # 역방향 자동 생성
for domain, cats in DOMAIN_TO_CATEGORIES.items():
    for cat in cats:
        CATEGORY_TO_DOMAINS.setdefault(cat, []).append(domain)

def find_adjacent_categories(my_category: str) -> list[str]:
    """현재 직무와 같은 도메인에 속하는 인접 직무 도출."""
    my_domains = CATEGORY_TO_DOMAINS.get(my_category, [])
    adjacent = set()
    for domain in my_domains:
        for cat in DOMAIN_TO_CATEGORIES.get(domain, []):
            if cat != my_category:
                adjacent.add(cat)
    return sorted(adjacent)

def categorize_salary_comparison(my_category: str, all_categories: dict) -> dict:
    """3개 그룹으로 재편: 내 직무 / 인접 직무 / 연봉 상위 직무."""
    my_band = all_categories.get(my_category)
    adjacent = find_adjacent_categories(my_category)

    similar = []
    for cat in adjacent:
        if cat in all_categories:
            similar.append({
                "name": cat,
                "range": all_categories[cat]["junior_range"],
            })

    # 연봉 상위 직무 (인접하지 않으면서 평균 높은 것)
    by_median = sorted(
        [(cat, info) for cat, info in all_categories.items()
         if cat != my_category and cat not in adjacent],
        key=lambda x: x[1].get("median", 0),
        reverse=True,
    )
    higher = [
        {"name": cat, "range": info["junior_range"]}
        for cat, info in by_median[:2]
    ]

    return {
        "my_job": {"name": my_category, "range": my_band["junior_range"]},
        "similar": similar[:3],
        "higher": higher,
    }
```

**출력 예시:**
```
[내 직무]
  서버/백엔드: 3,500 ~ 3,800만원 (실제 분포)

[인접 직무 — 현재 스택으로 지원 가능]
  웹 풀스택: 3,400 ~ 3,700만원
  DevOps/시스템 엔지니어: 3,800 ~ 4,200만원
  
[참고 — 연봉 상위 직무]
  인공지능/머신러닝: 3,958 ~ 3,977만원
  블록체인: 3,539 ~ 4,453만원
  → 이 직무들은 추가 학습이 필요할 수 있습니다.
```

**효과:** "내가 지금 갈 수 있는 곳"과 "장기 목표"를 분리하여 노이즈 제거. 사용자에게 의사결정 가치 제공.

---

## 6. 도메인 가산점 정책 (현황 정리)

### 6-1. 결정

**v6.0에서는 +0.05 단일값 유지.** 다음 이유로 차등 가산점은 보류:

- 시그너처 매칭(Unity 등) vs 키워드 휴리스틱의 정확도 차이를 정량화할 데이터 부족
- 발표 임박 시점에 복잡도 증가는 리스크
- 다중 도메인 균형 추천 모드 도입으로 가산점의 비중이 상대적으로 줄어듦

### 6-2. 작동 범위

| 상황 | 가산점 | 비고 |
|---|---|---|
| 단일 도메인 + 시그너처 매칭 | +0.05 | 현행 유지 |
| 단일 도메인 + 키워드 휴리스틱 | +0.05 | 현행 유지 |
| 다중 도메인 (히트 비율 < 2배) | 미적용 | 균형 추천 모드로 대체 |
| 도메인 감지 실패 | 미적용 | 현행 유지 |

### 6-3. v7 후속 검토

발표 후 v7에서 데이터 기반 차등화 검토:
- 시그너처 매칭 도메인의 매칭 정확도 측정
- 키워드 휴리스틱 도메인의 오감지 빈도 측정
- 두 값이 유의미하게 다르면 차등 가산점 도입

---

## 7. 구현 우선순위

| 순위 | 항목 | 시급도 | 공수 |
|---|---|---|---|
| 1 | A-2 경력직 공고 필터링 | 매우 시급 | 2시간 |
| 2 | A-4 공고 분류 태그 버그 수정 | 시급 (디버깅) | 1시간 |
| 3 | B-총합 종합 메시지 블록 | 발표 효과 큼 | 2시간 |
| 4 | C-2/C-3 연봉 모듈 출력 재편 | 발표 효과 큼 | 2시간 |
| 5 | A-1 약한 매칭 신호 안내 | 신뢰도 향상 | 1시간 |
| 6 | A-5 기술 미보유 도메인 필터링 | A-3 의존 | 1시간 |
| 7 | A-3 도메인 불일치 원인 분기 | 안내 정리 | 1시간 |
| 8 | B-항목 정리 (커밋 리듬, 성장 궤적 제거) | 단순화 | 30분 |
| 9 | B-5 커밋 메시지 변환 힌트 | 진단 품질 | 30분 |
| 10 | B-8 협업 항목 재구성 | 단순화 | 30분 |
| 11 | B-4 README 룰베이스 강화 | 진단 품질 | 1시간 |
| 12 | C-1 연봉 범위 확장 | 신뢰도 향상 | 30분 |
| 13 | 다중 도메인 균형 추천 모드 | 핵심 기능 | 4시간 |
| 14 | 퇴행 테스트: 기존 4종 레포 + 신규 시나리오 | 검증 | 2시간 |

총 약 19시간. 우선순위 1~5만 우선 처리해도 발표 가치가 크게 향상됨.

---

## 8. 발표/논문 영향

### 8-1. 논문 갱신 필요 항목

| 항목 | 논문 반영 |
|---|---|
| 진단 항목 9개 → 7개 | 표 1 갱신 |
| 종합 메시지 블록 | §3 또는 §6에 출력 예시 갱신 |
| 경력 필터링 | §2 직무 매칭에 한 문단 추가 (실용성 보강) |
| 다중 도메인 균형 추천 | §3 시그너처 섹션에 한 문단 추가 |
| 직무 비교 그룹화 | §5 연봉 모듈 갱신 |
| 도메인 가산점 +0.05 | 현행 유지 (변경 없음) |

### 8-2. 발표 어필 포인트

본 계획 적용 시 다음 메시지를 발표에서 강조 가능:

- **"사용자 관점 피드백을 반영하는 반복 개선"** — 팀원 1차 개선안 도입
- **"의미 없는 항목을 빼는 정직한 시스템"** — 9개 → 7개 정리
- **"실행 가능한 행동 안내"** — Quick wins 블록
- **"신입에게 적합한 공고만 추천"** — 경력 필터링
- **"다중 도메인 프로젝트의 다양한 진로 추천"** — 균형 추천 모드
- **"시장 분포를 정직하게 보여주는 연봉 정보"** — 범위 확장 + 비교 그룹화

### 8-3. 예상 질문 대응 강화

| 질문 | v6.0 대응 |
|---|---|
| "GitHub 통계와 뭐가 다른가?" | "Quick wins로 이번 주 실행 가능한 행동을 제시" |
| "신입에게 도움이 되는가?" | "경력직 공고 자동 필터링, 인접 직무 비교" |
| "결과 신뢰도는?" | "약한 매칭은 약하다고 명시, 정직한 분포 표시" |
| "사용자 피드백을 반영했나?" | "1차 개선안의 12개 항목 중 11개 반영, 1개(LLM)는 의도적 보류" |

---

## 9. 리스크

| 리스크 | 가능성 | 대응 |
|---|---|---|
| 경력 필터링 정규식 누락으로 일부 경력직 통과 | 중간 | 다양한 공고 제목 패턴으로 테스트, 점진적 보강 |
| 다중 도메인 균형 추천이 너무 출력 길어짐 | 중간 | 도메인당 2개로 제한, 종합 분석 한 줄로 마무리 |
| 종합 메시지의 강점 추출이 부정확 | 낮음 | 우선순위 항목 정의로 일관성 확보 |
| Quick wins 안내가 사용자 상황과 안 맞음 | 중간 | 항목별 미흡 상태에 매핑된 안내, 도메인 무관 일반론 |
| 룰베이스 README 강화가 여전히 한계 | 수용 | LLM 도입은 v7에서 재검토 |
| 연봉 ±15%/+20% 비율 근거 부족 | 낮음 | "업계 일반 분포 추정" 명시. 실 데이터 확보 시 갱신 |
| 다중 도메인 균형 추천이 단일 도메인에서 잘못 발동 | 중간 | v5.3.1 판정 기준 재사용으로 일관성 |

---

## 10. 본 계획 적용 후 시스템 정체성

v6.0 적용 후 Git2Value의 정체성은 다음과 같이 정리됨:

> "신입 개발자의 GitHub 포트폴리오를 분석하여 **실행 가능한 행동 안내**와 함께 직무 매칭, 진단, 시장 정보를 제공하는 시스템. 단일 도메인 프로젝트에서는 도메인 리랭킹으로 정확도를 높이고, 다중 도메인 프로젝트에서는 균형 추천으로 다양한 진로 가능성을 보여준다. 의미 없는 항목은 과감히 빼고, 신뢰할 수 없는 정보는 그렇다고 명시한다."

이 정체성이 발표에서 일관된 메시지로 전달되어야 함.

---

*Git2Value — 사용자 경험 개선 및 다중 도메인 균형 추천 계획 v6.0 — 2026.04.28*
