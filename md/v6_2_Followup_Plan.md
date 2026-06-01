# Git2Value — v6.2 후속 패치 계획

> 작성일: 2026.05.04 | 대상 버전: v6.1 → v6.2
> 발견 계기: v6.1 코드 검증 중 발견된 필수 패치 1건 + 권장 보강 4건 + 사소한 정리 1건

---

## 1. 배경

v6.1 (팀원 2차 개선안 반영)은 전반적으로 우수한 변경이지만, 검증 과정에서 다음 사항이 발견되었다:

- **필수 패치 1건**: 봇 작성자 필터링 누락 → 팀/개인 분류 로직의 근본 신뢰도 위협
- **권장 보강 3건**: 사용자 경험 일관성 향상
- **정리 1건**: dead code 제거 또는 활용

본 계획은 모두 v6.1 코드 위에서 점진 추가하는 형태로, 큰 구조 변경은 없다. 발표 임박 시점에 안정성·완성도를 한 단계 끌어올리는 마무리 작업이다.

---

## 2. 작업 항목 우선순위

| 우선순위 | 항목 | 시급도 | 공수 |
|---|---|---|---|
| 🔴 1 | 봇 작성자 필터링 추가 | 매우 시급 | 30분 |
| 🟡 2 | `similarity_label`에 "보통" 라벨 복원 | 권장 | 15분 |
| 🟡 3 | `_print_extra_one_liner` 활용 또는 제거 | 권장 | 30분 |
| 🟢 4 | 개인 레포만 있는 사용자 등급 안내 강화 | 권장 | 15분 |
| 🟢 5 | `experience_filter` 단위 테스트 추가 | 보강 | 30분 |
| 🟢 6 | `repo_active_weeks` 활용 정의 | 정리 | 15분 |

총 약 2시간 15분. 1번만 처리해도 안정성이 크게 향상됨.

---

## 3. 항목별 상세 설계

### 3-1. 🔴 봇 작성자 필터링 추가 (필수)

**문제:**
v6.1의 `evaluate_repository()`에서 `repo_author_keys`에 모든 작성자를 카운트한다. 그러나 실제 GitHub 레포에는 다음과 같은 봇 작성자가 흔히 존재한다:

- `dependabot[bot]` — 의존성 자동 업데이트 PR
- `github-actions[bot]` — GitHub Actions 자동 커밋
- `renovate[bot]` — Renovate 의존성 봇
- `pre-commit-ci[bot]` — pre-commit 자동 수정

**영향:**
- Dependabot 활성화된 개인 토이 프로젝트 → `distinct_author_count = 2` → **개인 레포가 팀 레포로 잘못 분류**
- 잘못된 분류는 모듈 B 진단 전체에 연쇄 영향:
  - `_team_required_items()` 적용 → "테스트 미흡 (필수)"이 부당하게 표시
  - `expected_level()`에서 팀 레포 카운트로 잘못 가산 → Competitive 등급 오인정
  - 모듈 A 출력에서 "[팀 레포 · 2명 협업]" 잘못된 표시

이건 v6.1 핵심 변경(팀/개인 분리)의 신뢰도를 무력화하는 결함이다.

**구현:**

```python
# github_extractor.py 클래스 상수에 추가
import re

class GitHubExtractor:
    # ... 기존 클래스 상수 ...
    
    # v6.2: 봇 작성자 식별 패턴
    _BOT_LOGIN_PATTERN = re.compile(
        r"\[bot\]$|^dependabot$|^github-actions$|^renovate-bot$"
        r"|^pre-commit-ci$|^codecov-commenter$|^stale\b",
        re.IGNORECASE,
    )
    _BOT_EMAIL_HINTS = (
        "[bot]@",
        "noreply@github.com",  # GitHub Actions 기본 이메일
    )
    
    @classmethod
    def _is_bot_author(cls, commit_obj: Dict[str, Any]) -> bool:
        """
        커밋 작성자가 자동화 봇인지 판별.
        - GitHub login에 [bot] suffix 또는 알려진 봇 이름 매칭
        - 이메일이 noreply 또는 [bot]@ 패턴
        """
        gh_author = commit_obj.get("author") or {}
        login = str(gh_author.get("login") or "")
        if login and cls._BOT_LOGIN_PATTERN.search(login):
            return True
        
        raw = (commit_obj.get("commit") or {}).get("author") or {}
        email = str(raw.get("email") or "").lower()
        if any(hint in email for hint in cls._BOT_EMAIL_HINTS):
            # 단, 일반 사용자의 users.noreply.github.com은 제외
            if "users.noreply.github.com" in email:
                return False
            return True
        
        return False
```

```python
# evaluate_repository() 내 distinct_author_count 산출 부분 수정
repo_author_keys: Set[str] = set()
repo_author_labels: List[str] = []
seen_label_keys: Set[str] = set()
bot_count = 0

for c in all_repo_commits:
    # v6.2: 봇 작성자 제외
    if self._is_bot_author(c):
        bot_count += 1
        continue
    
    key = self._commit_author_key(c)
    if key:
        repo_author_keys.add(key)
        label = self._commit_author_label(c)
        if label and key not in seen_label_keys:
            repo_author_labels.append(str(label))
            seen_label_keys.add(key)

distinct_author_count = len(repo_author_keys) if repo_author_keys else 1
repo_type = "team" if distinct_author_count >= 2 else "personal"

# (선택) bot_count를 warnings에 추가 (디버깅용)
if bot_count >= 5:
    repo_warnings.append(
        f"repo '{repo}' 봇 작성자 커밋 {bot_count}개 제외 (팀/개인 판정에 미반영)"
    )
```

**검증:**

봇 필터링 단위 테스트 (test 데이터):

```python
# 테스트 케이스
test_commits = [
    # 봇 - 매칭되어야 함
    {"author": {"login": "dependabot[bot]"}, "commit": {"author": {"name": "dependabot[bot]", "email": "49699333+dependabot[bot]@users.noreply.github.com"}}},
    {"author": {"login": "github-actions[bot]"}, "commit": {"author": {"name": "GitHub Actions", "email": "noreply@github.com"}}},
    {"author": {"login": "renovate[bot]"}, "commit": {"author": {"name": "renovate[bot]", "email": "renovate-bot@users.noreply.github.com"}}},
    
    # 일반 사용자 - 매칭되지 않아야 함
    {"author": {"login": "alice"}, "commit": {"author": {"name": "Alice", "email": "alice@example.com"}}},
    {"author": {"login": "bob123"}, "commit": {"author": {"name": "Bob", "email": "12345+bob123@users.noreply.github.com"}}},
]

assert GitHubExtractor._is_bot_author(test_commits[0]) == True
assert GitHubExtractor._is_bot_author(test_commits[1]) == True
assert GitHubExtractor._is_bot_author(test_commits[2]) == True
assert GitHubExtractor._is_bot_author(test_commits[3]) == False
assert GitHubExtractor._is_bot_author(test_commits[4]) == False  # 일반 noreply 제외하면 안 됨
```

**리스크:**
- 봇 패턴 누락 시 잘못된 팀 분류는 잔존 (점진적 보강)
- 일반 사용자가 우연히 봇 같은 닉네임을 가진 경우 (가능성 매우 낮음)

---

### 3-2. 🟡 `similarity_label`에 "보통" 라벨 복원 (권장)

**문제:**
v6.1의 `similarity_label()`은 일반 spread 분포에서 "강함" / "약함" 두 라벨만 반환한다.

```python
# 현재 (v6.1)
if max_s < 0.70:
    return "약함", note
# spread < 0.02 분기 — "보통" 반환됨

# 일반 spread 분포
if score >= 0.85:
    return "강함", None
if score >= 0.75 or score >= max_s - spread * 0.4:
    return "강함", None
return "약함", None
```

`0.65 <= score < 0.75` 범위가 모두 "약함"으로 분류된다. 0.74와 0.55가 같은 라벨이 되어 사용자가 결과 강도를 세밀하게 이해하기 어렵다.

**구현:**

```python
def similarity_label(score: float, top5_scores: list[float]) -> tuple[str, str | None]:
    if not top5_scores:
        return "보통", None
    
    max_s = max(top5_scores)
    min_s = min(top5_scores)
    spread = max_s - min_s
    avg = sum(top5_scores) / len(top5_scores)
    
    # 절대값 기준 우선 검사 — 전반적으로 약한 매칭
    if max_s < 0.70:
        note = (
            "상위 5개 공고 모두 유사도가 낮습니다. "
            "프로필 텍스트가 어떤 직무와도 강하게 매칭되지 않습니다. "
            "README 보강 또는 기술 스택 명확화가 필요합니다."
        )
        return "약함", note
    
    # spread 좁음 (몰림) 분기 — 기존 로직 유지
    if spread < 0.02:
        if avg < 0.75:
            note = (
                "상위 5개 공고가 모두 비슷한 보통 수준의 유사도에 몰려 있습니다. "
                "프로필 색깔이 뚜렷하지 않은 상태일 수 있습니다."
            )
        else:
            note = (
                "상위 5개 공고가 모두 비슷한 유사도에 몰려 있습니다. "
                "여러 직무가 일정 수준 매칭되는 다재다능한 프로필입니다."
            )
        return "보통", note
    
    # 일반 spread 분포 — 절대 + 상대 혼합
    if score >= 0.85:
        return "강함", None
    if score >= 0.75 or score >= max_s - spread * 0.4:
        return "강함", None
    if score >= 0.65:                       # ← v6.2 추가
        return "보통", None                  # ← v6.2 추가
    return "약함", None
```

**효과:**

| score | v6.1 라벨 | v6.2 라벨 |
|---|---|---|
| 0.90 | 강함 | 강함 |
| 0.78 | 강함 | 강함 |
| 0.70 | 약함 | **보통** |
| 0.66 | 약함 | **보통** |
| 0.60 | 약함 | 약함 |

3단계 분류가 복원되어 사용자가 결과 강도를 보다 세밀하게 이해할 수 있다.

---

### 3-3. 🟡 `_print_extra_one_liner` 활용 또는 제거 (권장)

**문제:**
v6.1의 `run_git2value.py`에는 `_print_extra_one_liner` 함수가 정의되어 있으나 호출되지 않는다 (dead code).

```python
def _print_extra_one_liner(label: str, item: dict, indent: str = "    ") -> None:
    """개인 레포의 운영/협업 항목은 필수 평가가 아니라 참고로만 표시."""
    # ...
```

`_print_repo_card`에서 개인 레포는 운영 항목을 표시하지 않고 즉시 return한다:

```python
def _print_repo_card(diag: dict, idx: int) -> None:
    # ... 핵심 평가 항목 출력 ...
    if repo_type == "personal":
        return    # ← 운영 항목 완전 비표시
    # 팀 레포만 운영 항목 표시
```

**선택지:**

**A안. 개인 레포에서도 양호 항목만 한 줄 요약 표시**

개인 레포에 CI/CD를 잘 세팅한 사용자의 노력이 출력에서 사라지는 게 아쉬움. 양호 항목만 강점으로 표시:

```python
def _print_repo_card(diag: dict, idx: int) -> None:
    # ... 핵심 평가 항목 출력 ...
    
    if repo_type == "personal":
        # v6.2: 개인 레포에서도 양호한 운영 항목만 한 줄 요약
        good_extras = [
            (key, item) for key, item in diag["extra_items"].items()
            if item.get("status") in ("양호", "규칙적")
        ]
        if good_extras:
            print("\n  ─ 추가 강점 (참고) ─")
            for key, item in good_extras:
                label = EXTRA_LABELS.get(key, key)
                _print_extra_one_liner(label, item, indent="    ")
        return
    
    # 팀 레포 운영 항목 출력 (기존 로직)
    print("\n  ─ 필수 점검 항목 (팀 레포 기준) ─")
    # ...
```

**B안. 함수 자체 제거**

개인 레포는 운영 항목을 완전히 비표시하는 게 의도였다면 dead code 정리:

```python
# _print_extra_one_liner 함수 제거
# _print_repo_card의 개인 레포 분기는 그대로 유지
```

**권장:** A안. 개인 레포에서 CI/CD나 테스트를 잘 세팅한 사용자의 노력을 인정하는 게 사용자 경험에 더 좋다. 함수 자체는 이미 만들어져 있으므로 호출만 추가하면 됨.

**구현 (A안):**

```python
# run_git2value.py _print_repo_card() 내부

def _print_repo_card(diag: dict, idx: int) -> None:
    # ... 헤더 출력 ...
    # ... 핵심 평가 항목 (3개) ...
    
    if repo_type == "personal":
        # v6.2: 양호한 운영 항목만 표시 (가산점)
        good_extras = [
            (key, EXTRA_LABELS[key], item)
            for key, item in diag["extra_items"].items()
            if item.get("status") in ("양호", "규칙적") and key in EXTRA_LABELS
        ]
        if good_extras:
            print("\n  ─ 추가 강점 (참고) ─")
            for _, label, item in good_extras:
                _print_extra_one_liner(label, item, indent="    ")
        return
    
    # 팀 레포: 4개 운영 항목 모두 필수 점검
    print("\n  ─ 필수 점검 항목 (팀 레포 기준) ─")
    for key, label in EXTRA_LABELS.items():
        item = diag["extra_items"].get(key, {})
        _print_diag_item(label, item, indent="    ")
        if key == "commit_pattern":
            total_commits = int(diag.get("total_repo_commits") or 0)
            my_commits = int(diag.get("target_commit_count") or 0)
            if total_commits > 0:
                ratio = round((my_commits / total_commits) * 100, 1)
                print(
                    f"        협업 신호: 전체 커밋 {total_commits}개 중 "
                    f"지원자 커밋 {my_commits}개 ({ratio}%)"
                )
```

---

### 3-4. 🟢 개인 레포만 있는 사용자 등급 안내 강화 (권장)

**문제:**
v6.1의 `expected_level()`에서 `team_repo_count >= 1` 조건이 Competitive와 Top의 필수 조건이다. 개인 레포만 있는 사용자는 Entry 등급으로만 결정되는데, 그 이유가 출력에 명시되지 않는다.

사용자 입장에서는 README도 양호하고 CI/CD도 잘 세팅되어 있는데 Entry로 분류되는 이유를 알 수 없다.

**구현:**

```python
# portfolio_diagnosis.py expected_level() 마지막 fallback 부분

def expected_level(per_repo_diags, team_repo_count):
    # ... 기존 점수 계산 ...
    
    # Top 등급
    if readme_ok and multi_proj and team_repo_count >= 1 and has_test and has_cicd and has_deploy and score >= 8:
        return {
            "level": "Top",
            "summary": "대형 테크·우수 스타트업 서류에서 경쟁력을 기대할 수 있는 완성도(참고 기준)입니다.",
        }
    
    # Competitive 등급
    if readme_ok and team_repo_count >= 1 and (has_cicd or has_deploy) and multi_proj and score >= 5:
        return {
            "level": "Competitive",
            "summary": "중견 IT·시리즈 B급 이상 스타트업에 맞설 만한 포트폴리오 완성도로 볼 수 있습니다.",
        }
    
    # v6.2: Entry — 팀 레포 부재 시 명시적 안내
    if team_repo_count == 0 and n_repos >= 2:
        return {
            "level": "Entry",
            "summary": (
                "Entry 수준 — 중견·중소 SI 또는 일반 스타트업 지원 가능 수준. "
                "현재 팀 프로젝트 경험이 감지되지 않아 Competitive 이상 등급에는 도달하지 않습니다. "
                "팀 프로젝트 1개 이상 확보 시 더 높은 등급에 도전할 수 있습니다."
            ),
        }
    
    # 기본 Entry
    return {
        "level": "Entry",
        "summary": "Entry 수준 — 중견·중소 SI 또는 일반 스타트업 지원 가능 수준입니다.",
    }
```

**추가 출력 안내 (run_git2value.py 모듈 B 마지막):**

`generate_summary_block()`의 포지셔닝 부분도 함께 갱신해서 일관성 있게:

```python
# portfolio_diagnosis.py generate_summary_block() 내부
def generate_summary_block(per_repo_diags, level_dict, github_score, score_breakdown, primary_domain):
    level = level_dict.get("level", "Entry")
    pd_str = primary_domain or "개발"
    
    # v6.2: 팀 레포 부재 시 포지셔닝 메시지 강화
    team_count = sum(1 for d in per_repo_diags if d.get("repo_type") == "team")
    
    if level == "Top":
        pos_suffix = "상위 회사·서류 통과 가능성 높은 완성도입니다."
    elif level == "Competitive":
        pos_suffix = "주요 항목 보강 시 상위 도전이 가능합니다."
    elif team_count == 0:
        pos_suffix = "경쟁력 있는 지원을 위해 팀 프로젝트 경험 확보가 권장됩니다."
    else:
        pos_suffix = "경쟁력 있는 지원을 위해 보강이 필요합니다."
    
    positioning = f"{pd_str} {level} 수준 포트폴리오 — {pos_suffix}"
    # ...
```

---

### 3-5. 🟢 `experience_filter` 단위 테스트 추가 (보강)

**문제:**
v6.1의 `extract_experience_requirement()`는 정규식 기반이라 패턴 누락이 잠재 위험이다. 다양한 공고 표현에서 정상 동작하는지 검증할 단위 테스트가 없다.

**구현:**

```python
# experience_filter.py 하단에 테스트 함수 추가

def _self_test():
    """v6.2: 정규식 패턴 검증용 단위 테스트."""
    cases = [
        # (position, applicant_years, expected_eligible, label_hint)
        # 신입/경력무관
        ("프론트엔드 개발자 신입", 0, True, "신입/주니어"),
        ("백엔드 개발자 (경력 무관)", 0, True, "경력무관"),
        ("개발자 신입/경력", 0, True, "경력무관"),
        ("주니어 백엔드 개발자", 0, True, "신입/주니어"),
        ("Junior Software Engineer", 0, True, "신입/주니어"),
        
        # 경력직 - 신입 0년차에게 부적합
        ("백엔드 개발자 (경력 3년 이상)", 0, False, "3년 이상"),
        ("시니어 풀스택 개발자", 0, False, "경력(시니어)"),
        ("Senior Backend Engineer", 0, False, "경력(시니어)"),
        ("개발자 5년차", 0, False, "5년차"),
        ("백엔드 개발자 (경력 3~5년)", 0, False, "3년 이상"),
        ("개발자 1년 이상", 0, False, "1년 이상"),  # 0년차 제외
        
        # 경력자에게 적합
        ("개발자 5년차", 5, True, None),
        ("백엔드 개발자 (경력 3~5년)", 4, True, None),
        ("개발자 1년 이상", 2, True, None),
        
        # 경력 미명시 - 모두 통과
        ("백엔드 개발자", 0, True, None),
        ("Software Engineer", 2, True, None),
    ]
    
    failed = []
    for position, years, expected, label_hint in cases:
        req = extract_experience_requirement(position, "")
        eligible = is_applicant_eligible(req, years)
        if eligible != expected:
            failed.append({
                "position": position,
                "years": years,
                "expected": expected,
                "got": eligible,
                "req": req,
            })
    
    if failed:
        print(f"❌ {len(failed)}/{len(cases)} 테스트 실패:")
        for f in failed:
            print(f"  '{f['position']}' (경력 {f['years']}년): "
                  f"expected={f['expected']}, got={f['got']}, req={f['req']}")
        return False
    
    print(f"✅ {len(cases)}/{len(cases)} 테스트 통과")
    return True


if __name__ == "__main__":
    _self_test()
```

**실행:**

```bash
python experience_filter.py
# ✅ 16/16 테스트 통과 (또는 실패 케이스 명시)
```

CI에 통합할 수도 있고, 패턴 변경 시 회귀 검증으로 사용 가능.

---

### 3-6. 🟢 `repo_active_weeks` 활용 정의 (정리)

**문제:**
v6.1에서 `repo_active_weeks`(레포 전체 커밋 기준 활성 주) 필드가 추가되었으나 실제 사용처가 없다. `active_weeks`(지원자 기준)는 Quality 점수와 진단에 사용되지만, `repo_active_weeks`는 어디에도 쓰이지 않는다.

**선택지:**

**A안. 협업 신호 표시에 활용**
팀 레포에서 "지원자 활동 18주 / 레포 전체 활동 24주" 같이 비율 표시:

```python
# run_git2value.py _print_repo_card() 팀 레포 분기
if key == "commit_pattern":
    target_weeks = int(diag.get("active_weeks") or 0)  # 지원자 기준 (extractor에서)
    repo_weeks = int(diag.get("repo_active_weeks") or 0)
    if target_weeks > 0 and repo_weeks > 0:
        coverage = round(target_weeks / repo_weeks * 100, 1)
        print(f"        활동 기간: 지원자 {target_weeks}주 / 레포 전체 {repo_weeks}주 ({coverage}%)")
```

**B안. 필드 제거**
사용처가 명확하지 않다면 출력 JSON에서 제거.

**권장:** A안. 팀 레포에서 지원자가 얼마나 오래 참여했는지 보여주는 보조 지표로 의미가 있다. 프로젝트 후반부에만 합류한 경우 vs 처음부터 끝까지 참여한 경우를 구분 가능.

**구현 (A안):**

```python
# portfolio_diagnosis.py diagnose_single_repo() 반환에 추가
return {
    # ... 기존 필드 ...
    "active_weeks": int(repo.get("active_weeks") or 0),
    "repo_active_weeks": int(repo.get("repo_active_weeks") or 0),
    # ...
}
```

```python
# run_git2value.py _print_repo_card() 팀 레포 분기
if key == "commit_pattern":
    total_commits = int(diag.get("total_repo_commits") or 0)
    my_commits = int(diag.get("target_commit_count") or 0)
    if total_commits > 0:
        ratio = round((my_commits / total_commits) * 100, 1)
        print(f"        협업 신호: 전체 커밋 {total_commits}개 중 "
              f"지원자 커밋 {my_commits}개 ({ratio}%)")
    
    # v6.2: 활동 기간 비율 표시
    target_weeks = int(diag.get("active_weeks") or 0)
    repo_weeks = int(diag.get("repo_active_weeks") or 0)
    if target_weeks > 0 and repo_weeks > 0 and repo_weeks >= target_weeks:
        coverage = round(target_weeks / repo_weeks * 100, 1)
        print(f"        활동 기간: 지원자 {target_weeks}주 / 레포 {repo_weeks}주 ({coverage}%)")
```

---

## 4. 출력 예시 (v6.1 vs v6.2 비교)

### 4-1. 봇 필터링 적용 후

```
[Before — v6.1]
▼ 레포 1: my-toy-project  [팀 레포 · 2명 협업]
  ─ 핵심 평가 항목 ─
    · README 품질
    ...
  ─ 필수 점검 항목 (팀 레포 기준) ─       ← 잘못된 분류
    · 테스트
        상태: 필수 미흡                    ← 부당한 격하
    ...

[After — v6.2]
▼ 레포 1: my-toy-project  [개인 레포]    ← 정확한 분류
  ─ 핵심 평가 항목 ─
    · README 품질
    ...
  ─ 추가 강점 (참고) ─                    ← 양호 항목 표시
    · CI/CD (참고)  : ✓ GitHub Actions 신호 감지
```

### 4-2. similarity_label 3단계 복원 후

```
[Before — v6.1]
[1순위] [회사A] 백엔드 개발자  (0.7234 · 강함)
[2순위] [회사B] 백엔드 개발자  (0.6847 · 약함)   ← 0.68인데도 약함
[3순위] [회사C] 풀스택         (0.6612 · 약함)

[After — v6.2]
[1순위] [회사A] 백엔드 개발자  (0.7234 · 강함)
[2순위] [회사B] 백엔드 개발자  (0.6847 · 보통)   ← 자연스러운 중간 단계
[3순위] [회사C] 풀스택         (0.6612 · 보통)
```

### 4-3. 등급 안내 강화 후

```
[Before — v6.1]
포지셔닝: 서버/백엔드 Entry 수준 포트폴리오 — 경쟁력 있는 지원을 위해 보강이 필요합니다.

[After — v6.2]
포지셔닝: 서버/백엔드 Entry 수준 포트폴리오 — 경쟁력 있는 지원을 위해 팀 프로젝트 경험 확보가 권장됩니다.

[등급 상세]
Entry 수준 — 중견·중소 SI 또는 일반 스타트업 지원 가능 수준.
현재 팀 프로젝트 경험이 감지되지 않아 Competitive 이상 등급에는 도달하지 않습니다.
팀 프로젝트 1개 이상 확보 시 더 높은 등급에 도전할 수 있습니다.
```

---

## 5. 검증 계획

각 항목 적용 후 회귀 테스트:

| 테스트 | 검증 항목 | 예상 결과 |
|---|---|---|
| Dependabot 활성화된 개인 레포 | 봇 필터링 | `repo_type=personal` 유지 |
| 5명 협업 팀 레포 (봇 1개) | 봇 필터링 | `distinct_author_count=5` (봇 제외) |
| 매칭 유사도 0.66 결과 | similarity_label | 라벨 "보통" |
| 매칭 유사도 0.55 결과 | similarity_label | 라벨 "약함" |
| 개인 레포에 CI/CD 양호 | extra_one_liner | "추가 강점 (참고)" 블록 표시 |
| 팀 레포 0개 | 등급 안내 | summary에 팀 프로젝트 권장 메시지 |
| `extract_experience_requirement` | 단위 테스트 | 16/16 통과 |
| 기존 4종 회귀 (TCG/DeepSentinel/AI 서버/Unity) | 전체 | 모듈 A/B/C 정상 출력 |

---

## 6. 적용 순서

1. **봇 필터링 추가** (`github_extractor.py`) — 30분
2. **봇 필터링 단위 테스트** (`test_*.py` 또는 `if __name__`) — 15분
3. **`similarity_label` "보통" 라벨 복원** (`run_git2value.py`) — 15분
4. **`_print_extra_one_liner` 활용** (`run_git2value.py`) — 30분
5. **등급 안내 강화** (`portfolio_diagnosis.py`) — 15분
6. **`experience_filter` 단위 테스트** (`experience_filter.py`) — 30분
7. **`repo_active_weeks` 활용** (`portfolio_diagnosis.py` + `run_git2value.py`) — 15분
8. **회귀 테스트 4종 + 봇 케이스 1종** — 1시간

총 약 4시간. 1~3번이 가장 시급하고, 4~7번은 완성도 보강이다.

---

## 7. 외부 문서 동기 갱신

v6.2 적용 후:

| 문서 | 갱신 내용 |
|---|---|
| `HandOff.md` | §6 v6.2 항목 추가, §7에서 31~34, 37번 ✅로 변경 |
| `Git2Value_Spec_v3.md` | Phase 1-3 anti-cheating에 봇 필터링 한 줄 추가 |
| 발표 슬라이드 | 큰 변경 없음 (사소한 개선이라 설명 슬라이드에 반영 불필요) |

---

## 8. 리스크 관리

| 리스크 | 대응 |
|---|---|
| 봇 패턴 누락으로 일부 봇이 통과 | 점진적 보강. `_BOT_LOGIN_PATTERN` 정규식 확장 |
| 일반 사용자가 봇과 비슷한 닉네임 | 매우 드문 케이스. 발견 시 화이트리스트 추가 |
| 회귀 테스트 통과 못한 케이스 발견 | 해당 변경 롤백 후 재설계 |
| `_print_extra_one_liner` 활용이 출력 길이 늘림 | 양호 항목 최대 4개 제한, 한 줄 표시로 길이 통제 |
| 단위 테스트 실패 발견 시 | 해당 패턴 정규식 보강 |

---

## 9. v6.2 이후 (v7 검토 항목)

본 계획에서 다루지 않지만 추후 검토:

- **차등 가산점** (시그너처 vs 휴리스틱): 데이터 측정 후 결정
- **로컬 LLM 도입** (README 평가): RTX 4090 환경 별도 계획 파일
- **리멤버 400개 처리 결정**: 분포 분석 후 결정
- **신규 도메인 매핑** (HW/임베디드, DBA/데이터, 그래픽스)
- **공고 임베딩 재구성** (직무명+요구기술 추출)

---

*Git2Value v6.2 후속 패치 계획 — 2026.05.04*
