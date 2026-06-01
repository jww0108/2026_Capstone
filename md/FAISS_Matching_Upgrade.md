# Git2Value — FAISS 매칭 품질 개선 계획

> 작성일: 2026.04.06 | 대상 버전: v5.0 → v5.1
> 발견 계기: C# Unity TCG 게임 레포가 프론트엔드 공고로 오매칭된 실제 테스트 결과

---

## 1. 문제 정의

### 발생 현상

C# 100% Unity 게임 코어 로직 레포를 분석한 결과:
- 도메인 감지: **"게임 개발" 정상 감지** ✅
- 프로필 텍스트: `"C# (100%) 기반 게임 개발 경험"` 정상 생성 ✅
- FAISS 매칭 결과: **React 웹 인터랙티브, 프론트엔드, Mobile Client** ❌

게임 관련 공고가 상위 5개에 하나도 없음.

### 원인 분석

`build_profile_text()`가 README 원문을 최대 500자까지 프로필에 그대로 붙이고 있음.
해당 레포의 README에는 "이벤트 기반 아키텍처", "EventManager", "구독(Subscribe)", "UI 팀", "애니메이션", "이펙트" 같은 단어가 다량 포함되어 있었음.

임베딩 모델 입장에서 이 키워드들은 **프론트엔드/UI 개발 공고의 어휘와 유사**함.
"C# 기반 게임 개발 경험"이라는 한 문장(약 20자)보다 README 원문(500자)의 임베딩 가중치가 훨씬 크게 작용하여, 프로필 벡터가 프론트엔드 공고 쪽으로 끌려감.

```
프로필 텍스트 구성:
  "C# (100%) 기반 게임 개발 경험"     ← 20자 (게임 시그널)
  + README 원문 500자                 ← "이벤트, UI, 구독, 애니메이션..." (프론트엔드 노이즈)

→ 임베딩 벡터가 프론트엔드 쪽으로 편향
```

---

## 2. 개선 방향 (2가지 동시 적용)

### 방향 A: README 원문 → 키워드 압축 (노이즈 제거)

README를 통째로 붙이지 않고, 도메인/기술 관련 키워드만 추출하여 짧은 문장으로 압축.

### 방향 B: 도메인 감지 기반 FAISS 후처리 (불일치 감지 + 안내)

FAISS 매칭 결과와 `detected_domains`를 비교하여, 불일치 시 경고 및 보정.

---

## 3. 방향 A 상세: README 키워드 압축

### 현재 동작

```python
# build_profile_text() 내부
readme_summary = extracted_data.get("readme_summary") or ""
if readme_summary and len(readme_summary) >= 200:
    parts.append(readme_summary[:500])  # 원문 그대로 붙임
```

### 변경 후 동작

README 원문 대신 **도메인·기술 키워드를 추출**하여 한 문장으로 압축.

```python
# README에서 도메인/기술 키워드를 추출하는 사전
README_KEYWORDS: dict[str, list[str]] = {
    "게임": [
        "게임", "game", "unity", "유니티", "unreal", "언리얼",
        "tcg", "rpg", "mmo", "fps", "moba",
        "캐릭터", "던전", "퀘스트", "인벤토리",
        "sprite", "tilemap", "physics",
    ],
    "웹": [
        "웹", "web", "브라우저", "SPA", "SEO", "SSR",
        "반응형", "responsive", "landing",
    ],
    "서버": [
        "서버", "server", "API", "REST", "GraphQL",
        "데이터베이스", "database", "인증", "auth",
    ],
    "ML/AI": [
        "학습", "training", "모델", "추론", "inference",
        "데이터셋", "dataset", "파인튜닝", "fine-tuning",
    ],
    "모바일": [
        "앱", "app", "모바일", "mobile", "iOS", "안드로이드", "android",
    ],
    "인프라": [
        "배포", "deploy", "컨테이너", "container",
        "쿠버네티스", "kubernetes", "모니터링", "monitoring",
    ],
}


def extract_readme_keywords(readme_text: str) -> str:
    """
    README에서 도메인/기술 키워드를 추출하여 압축 문장 생성.
    원문을 그대로 붙이지 않고, 매칭에 유의미한 시그널만 남김.
    """
    if not readme_text or len(readme_text.strip()) < 30:
        return ""

    text_lower = readme_text.lower()
    hit_domains: dict[str, int] = {}

    for domain, keywords in README_KEYWORDS.items():
        hits = sum(1 for kw in keywords if kw.lower() in text_lower)
        if hits >= 1:
            hit_domains[domain] = hits

    if not hit_domains:
        return ""

    # 히트 수 기준 상위 도메인 추출
    sorted_domains = sorted(hit_domains, key=hit_domains.get, reverse=True)
    top_domain = sorted_domains[0]

    # 매칭된 키워드 중 실제 등장한 것들을 나열
    matched_keywords = []
    for kw in README_KEYWORDS[top_domain]:
        if kw.lower() in text_lower and kw not in matched_keywords:
            matched_keywords.append(kw)

    if matched_keywords:
        return f"{', '.join(matched_keywords[:6])} 관련 프로젝트"
    return ""
```

### build_profile_text() 변경

```python
# 변경 전
if readme_summary and len(readme_summary) >= 200:
    parts.append(readme_summary[:500])

# 변경 후
readme_keywords = extract_readme_keywords(readme_summary)
if readme_keywords:
    parts.append(readme_keywords)
```

### 기대 효과

변경 전 프로필:
```
C# (100%) 기반 게임 개발 경험. C환경 테스트 (ConsoleRunner.cs 를 실행할 경우)
_ VS code 기준 ... 이벤트 기반 아키텍처 ... UI 팀은 게임의 상태를 직접
수정해서는 안 되며, 오직 EventManager가 쏘아주는 방송(Event)을 구독(Subscribe)
하여 애니메이션과 이펙트를 재생하는 역할만 담당합니다...
```

변경 후 프로필:
```
C# (100%) 기반 게임 개발 경험. 게임, unity, 유니티, TCG 관련 프로젝트.
```

"이벤트", "UI", "구독", "애니메이션" 같은 프론트엔드 노이즈가 제거되고,
게임 도메인 시그널만 남아서 임베딩 벡터가 게임 공고 쪽으로 향하게 됨.

---

## 4. 방향 B 상세: 도메인 감지 기반 FAISS 후처리

### 목적

도메인 감지와 FAISS 매칭 결과가 불일치할 때 이를 감지하고 사용자에게 안내.
완전한 리랭킹이 아니라 **투명한 경고 + 보조 정보 제공** 방식.

### 구현 위치

`run_git2value.py`의 모듈 A 출력 직전.

### 로직

```python
def check_domain_match_consistency(
    detected_domains: list[str],
    top_matches: list[dict],
) -> dict:
    """
    도메인 감지 결과와 FAISS 매칭 공고의 카테고리를 비교.
    불일치 시 경고 + 권장 직무를 반환.
    """
    if not detected_domains:
        return {"consistent": True, "warning": None, "suggested_category": None}

    primary_domain = detected_domains[0]

    # 도메인 → 점핏 카테고리 매핑
    DOMAIN_TO_CATEGORIES: dict[str, list[str]] = {
        "게임 개발":    ["게임 클라이언트", "게임 서버", "VR/AR/3D"],
        "웹 프론트엔드": ["프론트엔드", "웹 풀스택", "웹퍼블리셔"],
        "서버/백엔드":   ["서버/백엔드", "웹 풀스택"],
        "ML/AI":        ["인공지능/머신러닝", "빅데이터 엔지니어"],
        "모바일 앱":     ["안드로이드", "iOS", "크로스플랫폼 앱"],
        "DevOps/인프라": ["devops/시스템 엔지니어"],
    }

    expected_categories = DOMAIN_TO_CATEGORIES.get(primary_domain, [])
    if not expected_categories:
        return {"consistent": True, "warning": None, "suggested_category": None}

    # 상위 5개 매칭 공고의 카테고리 확인
    matched_categories = [m["category"] for m in top_matches]
    overlap = [c for c in matched_categories if c in expected_categories]

    if overlap:
        # 1개라도 일치하면 정상
        return {"consistent": True, "warning": None, "suggested_category": None}

    # 완전 불일치
    suggested = expected_categories[0]
    return {
        "consistent": False,
        "warning": (
            f"도메인 감지 결과는 '{primary_domain}'이지만, "
            f"상위 매칭 공고는 모두 다른 직무({', '.join(set(matched_categories))})입니다. "
            f"공고 DB에 '{primary_domain}' 관련 공고가 부족하거나, "
            f"프로필 텍스트가 다른 직무 키워드에 가까울 수 있습니다."
        ),
        "suggested_category": suggested,
    }
```

### 모듈 A 출력에 반영

```python
# run_git2value.py 모듈 A 출력부
domain_check = check_domain_match_consistency(
    profile.get("per_repo", [{}])[0].get("detected_domains", [])
    if profile.get("per_repo") else [],
    top_matches,
)

if not domain_check["consistent"]:
    print(f"\n  ⚠️ 도메인 불일치 감지:")
    print(f"     {domain_check['warning']}")
    if domain_check["suggested_category"]:
        print(f"     권장: '{domain_check['suggested_category']}' 직무로 직접 검색을 권장합니다.")
```

### 모듈 C 연봉 밴드에도 반영

도메인 불일치 시, 연봉 밴드를 FAISS 1순위 카테고리가 아니라 **도메인 감지 기반 카테고리**로도 조회:

```python
if not domain_check["consistent"] and domain_check["suggested_category"]:
    print(f"\n  (참고: 도메인 감지 기반 '{domain_check['suggested_category']}' 직무 연봉 밴드)")
    try:
        alt_band = val_engine.get_market_band(domain_check["suggested_category"])
        alt_sr = alt_band["market_salary_band"]["salary_range"]
        print(f"    참고 범위: {alt_sr['combined_range']}")
    except ValueError:
        print(f"    해당 직무의 연봉 데이터가 없습니다.")
```

### 기대 효과

TCG 게임 레포 테스트 시 출력 예시:

```
[모듈 A] 직무 매칭 (FAISS) + 상위 공고 패턴
  [1순위] [이스트나인] React 기반 웹 인터랙티브 이벤트 엔진 개발 리드 (유사도: 0.7813)
  ...

  ⚠️ 도메인 불일치 감지:
     도메인 감지 결과는 '게임 개발'이지만, 상위 매칭 공고는 모두 다른 직무(프론트엔드)입니다.
     공고 DB에 '게임 개발' 관련 공고가 부족하거나, 프로필 텍스트가 다른 직무 키워드에 가까울 수 있습니다.
     권장: '게임 클라이언트' 직무로 직접 검색을 권장합니다.

[모듈 C] 시장 연봉 밴드
  매칭 직무: 프론트엔드
  ...
  (참고: 도메인 감지 기반 '게임 클라이언트' 직무 연봉 밴드)
    참고 범위: 3,500만 ~ 3,800만원
```

---

## 5. 추가 확인 사항: 공고 DB 커버리지

방향 A+B를 구현해도, **공고 DB에 게임 공고가 극소수면 매칭 자체가 불가능**.
구현 전 확인 필요:

```python
# 공고 DB에서 게임 관련 공고 수 확인
game_keywords = ["게임", "game", "unity", "unreal", "클라이언트"]
game_count = sum(
    1 for m in metadata
    if any(kw in (m.get("position") or "").lower() for kw in game_keywords)
)
print(f"전체 공고 {len(metadata)}개 중 게임 관련: {game_count}개")
```

게임 공고가 10개 미만이면 방향 B(불일치 경고)가 더 중요해짐.
충분하다면 방향 A만으로도 매칭이 개선될 가능성이 높음.

---

## 6. 구현 우선순위

| 순위 | 작업 | 난이도 | 예상 공수 |
|---|---|---|---|
| 0 | 공고 DB 게임 공고 수 확인 | 매우 낮음 | 10분 |
| 1 | `extract_readme_keywords()` 함수 구현 | 낮음 | 1~2시간 |
| 2 | `build_profile_text()` README 붙이기 방식 변경 | 낮음 | 30분 |
| 3 | `check_domain_match_consistency()` 함수 구현 | 낮음 | 1시간 |
| 4 | 모듈 A 출력에 불일치 경고 추가 | 낮음 | 30분 |
| 5 | 모듈 C에 도메인 기반 대안 연봉 밴드 추가 | 낮음 | 30분 |
| 6 | TCG 레포로 재테스트 | — | 30분 |

**권장 순서:** 0 → 1 → 2 → 6(중간 검증) → 3 → 4 → 5 → 6(최종 검증)

---

## 7. 리스크

| 리스크 | 가능성 | 대응 |
|---|---|---|
| README 키워드 추출이 너무 적어서 프로필이 빈약해짐 | 중간 | 키워드 0개면 기존 방식(원문 300자) 폴백 |
| 게임 공고 자체가 DB에 없음 | 중간 | 방향 B 경고로 사용자에게 안내 |
| 키워드 사전에 없는 도메인의 README | 낮음 | 사전에 없으면 기존 방식 유지 (퇴행 없음) |
| 도메인 불일치 경고가 너무 자주 뜸 | 낮음 | 상위 5개 중 1개라도 일치하면 경고 안 뜸 |

---

*Git2Value — FAISS 매칭 품질 개선 계획 v5.1 — 2026.04.06*
