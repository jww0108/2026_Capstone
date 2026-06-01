# Git2Value — v6.4 README 진단 정상화 + 지배적 기여자 판정 계획

> 작성일: 2026.05.13 | 대상 버전: v6.3 → v6.4
> 발견 계기: (1) README 평가가 대부분 "미흡" 반환하는 구조적 버그 발견 + (2) 사실상 1인 프로젝트가 팀으로 오분류되는 피드백

---

## 1. 개요

본 계획은 두 가지 독립적 결함을 수정한다:

**(가) README 진단 정상화** — `_clean_markdown()`이 평가 증거를 삭제한 뒤 평가 함수에 전달하는 구조적 버그 수정 + 패턴 커버리지 보강
**(나) 지배적 기여자 판정** — 작성자 2명 이상이라도 한 사람이 커밋의 85% 이상을 차지하면 "personal"로 판정

| 구분 | 문제 | v6.4 반영 항목 |
|---|---|---|
| 테스트 발견 | README 3차원 평가가 거의 항상 실패 | → **§3. README 원본 전환** |
| 테스트 발견 | 패턴이 흔한 헤딩 표현을 누락 | → **§4. README 패턴 커버리지 보강** |
| 사용자 피드백 | 기여 1~3커밋 팀원 때문에 팀 판정 | → **§5. 지배적 기여자 판정** |

**총 공수: 약 1시간 30분.** §3~§4는 진단 정확도, §5는 점수에 직접 영향.

---

## 2. 작업 항목 우선순위

| 순위 | 항목 | 근거 | 공수 |
|---|---|---|---|
| 🔴 1 | README 원본 마크다운 기준 전환 | 진단 3차원 모두 불능 상태 | 15분 |
| 🔴 2 | 지배적 기여자 판정 (85% 임계값) | 팀/개인 오분류 → Quality 배점 + 등급 연쇄 오류 | 30분 |
| 🟡 3 | README 패턴 커버리지 보강 | 원본 전환 후에도 흔한 표현 누락 | 30분 |
| — | 회귀 테스트 | — | 15분 |

---

## 3. README 원본 마크다운 기준 전환

### 3-1. 문제

`evaluate_readme_quality()`가 정제본(`_clean_markdown()` 출력)을 입력받는데, 정제 과정에서 평가에 필요한 마크업이 전부 삭제된다.

```
GitHub API → readme_raw_text (원본)
                  │
                  └─ _clean_markdown()
                       ├─ 이미지 마크다운 삭제:  !\[.*?\]\(.*?\)
                       ├─ HTML 태그 삭제:       <img src=...>
                       ├─ 헤딩 마크업 삭제:     ## 기술 스택 → 기술 스택
                       └─ 줄바꿈 제거:          전체 한 줄로 병합
                            │
                            ↓
                      readme_content (정제본) ← 현재 여기서 평가 (❌)
```

3개 차원이 모두 깨지는 이유:

| 차원 | 매칭 대상 | 정제 후 상태 | 매칭 |
|---|---|---|---|
| 프로젝트 목적 | `##\s*(소개\|introduction)` | `#` 마크업 삭제됨 | ❌ |
| 기술 스택 | `##\s*(기술\s*스택\|tech\s*stack)` | 동일 | ❌ |
| 결과물 시각화 | `!\[.*?\]\(.*?\)`, `<img\s+src=` | 이미지·HTML 명시적 삭제 | ❌ |

### 3-2. 연쇄 영향

README 진단이 거의 항상 "미흡"/"개선 필요"를 반환하므로:

| 영향 받는 로직 | 현재 상태 | 정상화 후 |
|---|---|---|
| `expected_level()` — `readme_st ∈ (양호, 보통)` → `score += 1` | 거의 발동 안 됨 | 정상 발동 |
| Top/Competitive 진입 조건 `readme_ok = True` | 차단됨 | 정상 개방 |
| `generate_summary_block()` 강점 리스트 | README 포함 안 됨 | 정상 포함 |
| Quick Wins 풀 | README 항목 항상 출력 | 실제 미흡한 경우만 출력 |

### 3-3. 해결: `readme_raw` 필드 추가

`_clean_markdown()`은 FAISS 임베딩용이므로 변경하지 않는다. README 원본을 별도 필드로 전달.

**`github_extractor.py` — `evaluate_repository()` 반환 dict:**

```python
return {
    ...
    "readme": readme_content,               # 기존 유지: FAISS 임베딩 / 출력용
    "readme_raw": readme_raw_text[:5000],    # v6.4 추가: 품질 평가용 원본
    "readme_has_image": readme_has_image,
    ...
}
```

**`github_extractor.py` — `extract_applicant_profile()` 내 `per_repo`:**

```python
per_repo.append(
    {
        ...
        "readme": rm,
        "readme_raw": res.get("readme_raw") or rm,   # v6.4 추가
        "readme_has_image": bool(res.get("readme_has_image")),
        "readme_tier": profile_builder.readme_length_tier(rm),
        ...
    }
)
```

**`portfolio_diagnosis.py` — `_readme_diagnosis_single()` 수정:**

```python
def _readme_diagnosis_single(repo: Dict[str, Any]) -> Dict[str, Any]:
    # v6.4: 품질 평가는 원본 마크다운, 길이는 정제본 기준
    readme_raw = (repo.get("readme_raw") or repo.get("readme") or "").strip()
    readme_clean = (repo.get("readme") or "").strip()
    has_image = bool(repo.get("readme_has_image"))
    n = len(readme_clean)

    if n < 50:
        return _item(
            "미흡",
            "README가 거의 비어 있거나 매우 짧습니다.",
            "채용 담당자가 처음 보는 문서가 README입니다. 구조화된 설명을 추가하세요.",
        )

    quality = evaluate_readme_quality(readme_raw)  # v6.4: 원본으로 평가
    missing_dims = [k for k, v in quality["indicators"].items() if not v]
    missing_hint = f" (부족: {', '.join(missing_dims)})" if missing_dims else ""

    if n >= 200:
        if quality["status"] == "양호":
            img_hint = " · 이미지 포함" if has_image else ""
            return _item(
                "양호",
                f"길이 {n:,}자{img_hint}. 목적·기술스택·시각화 항목이 충실합니다.",
                None,
            )
        return _item(
            "개선 필요",
            f"길이는 충분({n:,}자)하지만 구성이 아쉽습니다{missing_hint}.",
            f"README에 {', '.join(missing_dims) if missing_dims else '목적·기술 스택·스크린샷'}을 추가하면 완성도가 높아집니다.",
        )

    return _item(
        "개선 필요",
        f"README가 짧습니다 ({n:,}자){missing_hint}.",
        "프로젝트 목적, 기술 스택, 실행 방법, 데모 GIF/스크린샷을 README에 정리하세요.",
    )
```

### 3-4. 변경하지 않는 것

| 항목 | 이유 |
|---|---|
| `_clean_markdown()` | FAISS 임베딩용 정제 로직으로 목적이 다름 |
| `evaluate_readme_quality()` 함수 시그니처 | 입력만 원본으로 바꾸면 됨 |
| `readme_has_image` | 이미 원본 기준 판정이므로 정확 |
| `readme_length_tier()` | 정제본 기준 길이 tier가 맞음 (보일러플레이트 제외 후 실질 길이) |

---

## 4. README 패턴 커버리지 보강

### 4-1. 문제

§3으로 원본 전환하면 기존 패턴이 정상 작동하지만, 흔한 README 작성 관행 중 현재 패턴이 누락하는 표현이 다수 존재한다.

### 4-2. 현재 패턴 vs 누락 케이스

**차원 1 — 프로젝트 목적 명시:**

```python
# 현재
r"^#\s*[가-힣\w].{5,}",
r"##\s*(소개|introduction|overview|개요)",
r"##\s*(프로젝트\s*목적|purpose|goal)",
```

| 누락 표현 | 빈도 |
|---|---|
| `## About` / `## About this project` | 높음 |
| `## Description` | 높음 |
| `## 프로젝트 설명` / `## 프로젝트 소개` | 높음 |
| `## What is this` / `## What is [프로젝트명]` | 중간 |
| `## Summary` | 중간 |

**차원 2 — 기술 스택 설명:**

```python
# 현재
r"##\s*(기술\s*스택|tech\s*stack|technologies|사용\s*기술|stack)",
r"\|\s*(언어|language|framework|기술)\s*\|",
```

| 누락 표현 | 빈도 |
|---|---|
| `## Built with` / `## Built With` | 높음 |
| `## Requirements` / `## 개발 환경` | 높음 |
| `## Dependencies` / `## 의존성` | 중간 |
| `## Installation` 내 기술 스택 열거 | 중간 |
| `## 기술 구성` / `## 사용 기술 스택` | 중간 |

**차원 3 — 결과물 시각화:**

```python
# 현재
r"!\[.*?\]\(.*?\)",
r"<img\s+src=",
r"https?://[^\s)]+\.(gif|png|jpg|jpeg|mp4|webm)",
```

| 누락 표현 | 빈도 |
|---|---|
| `<video` 태그 | 낮음 |
| YouTube/Vimeo 링크 | 중간 |
| `## Demo` / `## 데모` / `## Screenshots` 섹션 존재 자체 | 중간 |

### 4-3. 보강 패턴

```python
README_QUALITY_INDICATORS: Dict[str, List[str]] = {
    "프로젝트 목적 명시": [
        r"^#\s*[가-힣\w].{5,}",
        r"##\s*(소개|introduction|overview|개요)",
        r"##\s*(프로젝트\s*목적|purpose|goal)",
        # v6.4 추가
        r"##\s*(about|description|summary)",
        r"##\s*프로젝트\s*(설명|소개)",
        r"##\s*what\s+is",
    ],
    "기술 스택 설명": [
        r"##\s*(기술\s*스택|tech\s*stack|technologies|사용\s*기술|stack)",
        r"\|\s*(언어|language|framework|기술)\s*\|",
        # v6.4 추가
        r"##\s*(built\s*with|requirements|dependencies)",
        r"##\s*(개발\s*환경|의존성|기술\s*구성|사용\s*기술)",
    ],
    "결과물 시각화": [
        r"!\[.*?\]\(.*?\)",
        r"<img\s+src=",
        r"https?://[^\s)]+\.(gif|png|jpg|jpeg|mp4|webm)",
        # v6.4 추가
        r"<video\s",
        r"https?://(www\.)?(youtube\.com|youtu\.be|vimeo\.com)/",
        r"##\s*(demo|데모|screenshots?|스크린샷|preview|미리\s*보기)",
    ],
}
```

### 4-4. 보강 효과 예상

| README 구성 | v6.2 | v6.3 (원본만) | v6.4 (원본+패턴) |
|---|---|---|---|
| `## About` + `## Built With` + `![img](...)` | 0개 매칭 → 미흡 | 1개 매칭(이미지만) → 보통 | **3개 매칭 → 양호** |
| `## Description` + 기술 나열 (헤딩 없음) | 0개 → 미흡 | 0개 → 미흡 | **1개 매칭 → 보통** |
| `## 소개` + `## 기술 스택` + YouTube 링크 | 0개 → 미흡 | 2개 매칭 → 양호 | **3개 매칭 → 양호** |
| `# Title` + 본문만 (헤딩 1개) | 0개 → 미흡 | 1개 매칭 → 보통 | 1개 매칭 → 보통 |

### 4-5. 리스크

| 리스크 | 가능성 | 대응 |
|---|---|---|
| `## Demo` 섹션이 있지만 빈 경우 | 낮음 | 섹션 존재만으로 "시각화 있음" 판정은 약간 관대하지만, 빈 Demo 섹션은 극소. "개선 필요"보다 "양호"로 판정되는 편이 사용자 경험에 유리 |
| `## Requirements`가 시스템 요구사항(Python 3.9+ 등)만 열거 | 중간 | 이 경우에도 "기술 스택 설명이 있다"로 판정하는 것은 합리적. 시스템 요구사항 자체가 기술 스택의 일부 |
| YouTube 링크가 관련 없는 영상 | 낮음 | README에 YouTube 링크를 넣는 경우 대부분 데모 영상. 관련 없는 영상은 극소 |

---

## 5. 지배적 기여자 판정

### 5-1. 문제

현재 팀/개인 판정은 `distinct_author_count >= 2`라는 이진 조건이다. 다음 케이스가 모두 "team"으로 분류된다:

```
케이스 A: 지원자 200 + 팀원 B 180 + C 150  → team ✅ 정확
케이스 B: 지원자 290 + 팀원 B 3커밋         → team ❌ 부당
케이스 C: 지원자 195 + 교수 5커밋           → team ❌ 부당
```

팀 오분류 시 연쇄 영향:

| 영향 | 설명 |
|---|---|
| Quality 배점 | 개인(활성 주 20 + CI/CD 5 + 테스트 5) → 팀(각 10점 균등). CI/CD 없는 개인 프로젝트가 더 불리 |
| "Competitive (개인)" 경로 | `team_repo_count == 0` 조건 차단 |
| 출력 표시 | "팀 프로젝트"로 표시되어 사용자 혼란 |

### 5-2. 해결: 지배 비율 기반 보정

`distinct_author_count` 산출 후, 최다 기여자의 커밋 비율이 85% 이상이면 "personal"로 재판정한다.

### 5-3. 85% 임계값 근거

| 시나리오 | 최다 기여자 비율 | 판정 | 근거 |
|---|---|---|---|
| 2명, 290:3 | 99% | personal | B의 3커밋은 오타/설정 수준 |
| 2명, 195:5 | 97.5% | personal | 교수 초기 템플릿 수준 |
| 3명, 170:20:10 | 85% | personal | 나머지 합 15%, 보조적 참여 |
| 3명, 150:30:20 | 75% | team | B(15%), C(10%)가 의미 있는 기여 |
| 5명 균등 | 20% | team | 정상적 팀 프로젝트 |

85%는 "나머지 전원을 합쳐도 15% 미만"이라는 뜻이다. 이 수준의 소수 커밋은 오타 수정, 초기 설정, 리뷰 코멘트 반영 정도로 볼 수 있다.

### 5-4. 구현

```python
# github_extractor.py — evaluate_repository() 내부

# 기존 봇/미연결 필터링 루프에 작성자별 커밋 수 집계 추가
repo_author_keys: Set[str] = set()
repo_author_labels: List[str] = []
seen_label_keys: Set[str] = set()
author_commit_counts: Dict[str, int] = {}           # v6.4 추가
bot_count = 0
unlinked_count = 0
human_commit_count = 0

for c in all_repo_commits:
    if self._is_bot_author(c):
        bot_count += 1
        continue

    human_commit_count += 1

    gh_author = c.get("author")
    if gh_author is None:
        unlinked_count += 1
        continue

    key = self._commit_author_key(c)
    if key:
        repo_author_keys.add(key)
        author_commit_counts[key] = author_commit_counts.get(key, 0) + 1  # v6.4
        label = self._commit_author_label(c)
        if label and key not in seen_label_keys:
            repo_author_labels.append(str(label))
            seen_label_keys.add(key)

# ... bot/unlinked 경고 ...

distinct_author_count = len(repo_author_keys) if repo_author_keys else 1

# v6.4: 지배적 기여자 판정 — 한 사람이 85% 이상이면 사실상 개인 프로젝트
dominance_ratio = 0.0
is_dominance_override = False

if distinct_author_count >= 2 and author_commit_counts:
    max_commits = max(author_commit_counts.values())
    total_authored = sum(author_commit_counts.values())
    dominance_ratio = max_commits / total_authored if total_authored > 0 else 0

    if dominance_ratio >= 0.85:
        repo_type = "personal"
        is_dominance_override = True
        repo_warnings.append(
            f"작성자 {distinct_author_count}명이나 최다 기여자가 "
            f"커밋의 {dominance_ratio:.0%}를 차지하여 개인 프로젝트로 판정"
        )
    else:
        repo_type = "team"
else:
    repo_type = "team" if distinct_author_count >= 2 else "personal"
```

### 5-5. 반환 dict에 판정 근거 추가

```python
return {
    ...
    "repo_type": repo_type,
    "distinct_author_count": distinct_author_count,
    # v6.4 추가
    "dominance_ratio": round(dominance_ratio, 3) if dominance_ratio > 0 else None,
    "is_dominance_override": is_dominance_override,
    ...
}
```

### 5-6. 출력 반영 (`run_git2value.py` — `_print_repo_card()`)

```python
# 레포 유형 출력 라인에 지배적 기여자 판정 표시
if repo.get("is_dominance_override"):
    type_label = (
        f"개인 (작성자 {repo['distinct_author_count']}명이나 "
        f"본인 기여 {repo['dominance_ratio']:.0%}로 개인 판정)"
    )
elif repo_type == "team":
    type_label = f"팀 ({repo['distinct_author_count']}명)"
else:
    type_label = "개인"
```

### 5-7. Quality 배점 연동

`repo_type`이 "personal"로 재판정되므로, 기존 `evaluate_repository()`의 Quality 분기가 자동으로 개인 배점을 적용한다:

```python
if repo_type == "team":
    # CI/CD(10) + 테스트(10) + 활성 주(10)
    ...
else:
    # 활성 주(20) + CI/CD 가산(5) + 테스트 가산(5)
    ...
```

추가 코드 변경 없이 `repo_type` 변경만으로 연쇄 적용된다.

### 5-8. `expected_level()` 연동

`team_repo_count`는 `per_repo_diags`에서 `repo_type == "team"`인 레포를 카운팅하므로, 지배적 기여자로 "personal" 재판정된 레포는 자동으로 `team_repo_count`에서 빠진다. "Competitive (개인)" 경로 진입도 자동 정상화.

### 5-9. 검증 시나리오

| 시나리오 | 커밋 분포 | 지배 비율 | v6.3 | v6.4 |
|---|---|---|---|---|
| 2명, 지원자 290 + B 3 | 99% | team | **personal** ✅ |
| 2명, 지원자 195 + 교수 5 | 97.5% | team | **personal** ✅ |
| 3명, 170:20:10 | 85% | team | **personal** ✅ |
| 3명, 150:30:20 | 75% | team | team ✅ |
| 5명 균등 각 40 | 20% | team | team ✅ |
| 1명 단독 | 100% | personal | personal ✅ |
| 2명 균등 50:50 | 50% | team | team ✅ |

---

## 6. 적용 순서

```
1. github_extractor.py  ★ 점수/진단 영향
   ├─ evaluate_repository():
   │   ├─ author_commit_counts 집계 추가            (§5)
   │   ├─ 지배적 기여자 판정 (dominance_ratio)      (§5)
   │   ├─ 반환 dict에 dominance_ratio 등 추가       (§5)
   │   └─ readme_raw 필드 추가                      (§3)
   └─ extract_applicant_profile():
       └─ per_repo에 readme_raw 전달                (§3)

2. portfolio_diagnosis.py
   ├─ README_QUALITY_INDICATORS 패턴 보강            (§4)
   └─ _readme_diagnosis_single() 원본 기준 평가      (§3)

3. run_git2value.py
   └─ _print_repo_card() 지배적 기여자 출력 표시     (§5)

4. 검증
   ├─ README 충실 레포 ("## About" + "## Built With" + 이미지):
   │   "양호" 확인                                    (§3, §4)
   ├─ README 보일러플레이트 레포: "미흡" 유지          (§3)
   ├─ 2명(지원자 95% + B 5%): personal 판정           (§5)
   ├─ 3명(75%:15%:10%): team 유지                     (§5)
   └─ 지배적 개인 판정 레포: Quality 개인 배점 확인    (§5)
```

---

## 7. 검증 매트릭스

| 테스트 | 검증 항목 | 예상 결과 |
|---|---|---|
| README `## About` + `## Built With` + `![img](...)` | 패턴 매칭 | 3개 매칭 → "양호" |
| README `## Description` + 기술 나열 (헤딩 없음) | 패턴 매칭 | 1개 매칭 → "보통" |
| README `## 소개` + `## 기술 스택` + YouTube 링크 | 패턴 매칭 | 3개 매칭 → "양호" |
| README `## Demo` 섹션 + 텍스트만 | 시각화 차원 | 1개 매칭 (Demo 섹션) |
| CRA 보일러플레이트 README | 정제 후 길이 | "미흡" 유지 |
| README 없는 레포 | 길이 0 | "미흡" |
| 2명, 지원자 290커밋 + B 3커밋 | 지배적 기여자 | `personal`, dominance 99% |
| 2명, 지원자 195커밋 + 교수 5커밋 | 지배적 기여자 | `personal`, dominance 97.5% |
| 3명, 170:20:10 | 지배적 기여자 | `personal`, dominance 85% |
| 3명, 150:30:20 | 지배적 기여자 | `team`, dominance 75% |
| 지배적 개인 판정 레포 + CI/CD 없음 | Quality 배점 | 개인 기준: 활성 주 20 + 가산 → 팀 기준 10보다 유리 |
| 지배적 개인 판정만 있는 사용자 | expected_level | "Competitive (개인)" 경로 접근 가능 |

---

## 8. 영향 범위

### 영향 있는 파일

| 파일 | 변경 규모 | 내용 |
|---|---|---|
| `github_extractor.py` | 중간 | `readme_raw` 추가 + `author_commit_counts` 집계 + 지배적 기여자 판정 |
| `portfolio_diagnosis.py` | 소규모 | README 패턴 보강 + 원본 기준 평가 전환 |
| `run_git2value.py` | 소규모 | 지배적 기여자 출력 표시 |

### 영향 없는 파일

| 파일 | 이유 |
|---|---|
| `profile_builder.py` | README 키워드 압축은 정제본 사용 — 변경 없음 |
| `experience_filter.py` | 변경 없음 |
| `valuation_engine.py` | 변경 없음 |

### 점수/진단 변동

| 변경 | 영향 |
|---|---|
| README 원본 전환 + 패턴 보강 (§3, §4) | 대부분의 레포에서 README 진단 상향 → `expected_level` score +1 가능 → 등급 상향 가능. 점수 자체(github_score)는 불변 (진단은 모듈 B, 점수는 독립) |
| 지배적 기여자 판정 (§5) | 해당 레포의 Quality 배점이 팀→개인으로 전환. CI/CD 없는 프로젝트에서 점수 상승 가능. `expected_level`에서 `team_repo_count` 감소 → "Competitive (개인)" 경로 진입 가능 |

---

## 9. 발표/논문 영향

| 항목 | 영향 |
|---|---|
| README 원본 전환 | 논문 §3: "README 품질 평가를 원본 마크다운 기준으로 전환하여 진단 정확도 향상" |
| README 패턴 보강 | 논문 §3: "3차원 평가 패턴을 영문·한글 주요 헤딩 표현으로 확장" |
| 지배적 기여자 판정 | 논문 §4: "최다 기여자 커밋 비율 85% 이상 시 개인 프로젝트로 재판정하여 팀/개인 오분류 해소" |

---

## 10. 리스크

| 리스크 | 가능성 | 대응 |
|---|---|---|
| README `[:5000]` 상한으로 긴 README 뒷부분 평가 누락 | 낮음 | 품질 패턴(소개, 기술 스택, 이미지)은 README 상단에 위치 |
| README 진단 상향으로 Quick Wins "README" 항목 감소 | 의도됨 | 잘 작성된 README에 "미흡" 피드백을 주는 것이 더 문제 |
| `## Demo` 섹션이 있지만 빈 경우 | 낮음 | 빈 Demo 섹션은 극소. 관대한 판정이 사용자 경험에 유리 |
| `## Requirements`가 시스템 요구사항만 열거 | 중간 | 시스템 요구사항도 기술 스택의 일부로 볼 수 있음 |
| 지배적 기여자 85% 임계값이 실제 팀을 개인으로 오분류 | 낮음 | 85%는 "나머지 전원 합 15% 미만". 이 수준의 소수 커밋은 오타·설정 수준 |
| 커밋 수 기준만으로 판정 (LOC 미반영) | 낮음 | "커밋 1개에 LOC 5000"은 드문 엣지 케이스. v7에서 LOC 기반 보강 검토 |
| 지배적 기여자 판정으로 기존 테스트 결과 변동 | 확실 | 회귀 테스트 기대값을 v6.4 기준으로 갱신 |

---

## 11. v7 이후 검토 항목 (본 계획에서 미포함)

| 항목 | 사유 | 비고 |
|---|---|---|
| 지배적 기여자 LOC 기반 보강 | 커밋별 diff API 추가 호출 필요 | v7에서 API 비용 대비 효과 분석 |
| README 내용 품질 평가 (로컬 LLM) | 룰베이스 한계 | Qwen2.5-32B-AWQ로 README 설명 품질·완성도 평가 |
| 보일러플레이트 패턴 확장 | CRA 외 Vue CLI, Next.js, Vite 등 | 현재는 정제본 길이가 길어지는 정도로 영향 미미 |
| 지배적 기여자 팀 레포 출력 개선 | "사실상 개인이지만 팀원 존재" 시 출력 문구 정교화 | 현재는 경고 메시지로 충분 |

---

*Git2Value v6.4 README 진단 정상화 + 지배적 기여자 판정 계획 — 2026.05.13*
