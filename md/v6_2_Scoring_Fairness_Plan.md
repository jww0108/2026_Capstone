# Git2Value — v6.2 점수 공정성 + 후속 패치 통합 계획

> 작성일: 2026.05.04 | 대상 버전: v6.1 → v6.2
> 발견 계기: (1) v6.1 코드 검증에서 발견된 필수/권장 패치 6건 + (2) 추가 피드백 3건 (점수 산출 공정성)

---

## 1. 개요

본 계획은 두 갈래의 작업을 통합한다:

**(가) 코드 검증 후속 패치** — v6.1 코드 검증에서 발견된 안정성·완성도 항목 6건  
**(나) 점수 공정성 피드백** — 다중 레포 총점 산출 / 개인·팀 평가 기준 분리 / Fork 패널티 완화 3건

두 갈래를 v6.2로 통합하는 이유: (나)의 세 항목이 모두 `github_extractor.py`의 `evaluate_repository()` + `extract_applicant_profile()`에 집중되며, (가)의 봇 필터링도 같은 파일이므로 한 번에 적용하는 것이 회귀 리스크를 줄인다.

---

## 2. 작업 항목 우선순위

| 순위 | 항목 | 갈래 | 시급도 | 공수 |
|---|---|---|---|---|
| 🔴 1 | 봇 작성자 필터링 추가 | (가) | 매우 시급 | 30분 |
| 🔴 2 | Fork 패널티 단계적 완화 | (나)-3 | 시급 | 1시간 |
| 🔴 3 | 총점 산출 방식 변경 (레포별 점수 + 대표 프로젝트 중심) | (나)-1 | 시급 | 1시간 |
| 🟡 4 | Quality 점수 개인/팀 분리 | (나)-2 | 중요 | 2시간 |
| 🟡 5 | 등급 판정 개인 전용 경로 | (나)-2 연장 | 중요 | 30분 |
| 🟡 6 | `similarity_label`에 "보통" 라벨 복원 | (가) | 권장 | 15분 |
| 🟡 7 | `_print_extra_one_liner` 활용 (개인 레포 양호 항목 표시) | (가) | 권장 | 30분 |
| 🟢 8 | 개인 레포만 있는 사용자 등급 안내 강화 | (가) | 보강 | 15분 |
| 🟢 9 | `experience_filter` 단위 테스트 | (가) | 보강 | 30분 |
| 🟢 10 | `repo_active_weeks` 활용 정의 | (가) | 정리 | 15분 |
| — | 회귀 테스트 (기존 4종 + 봇·Fork·개인 케이스) | — | 필수 | 1시간 |

총 약 7시간 30분. 1~5번(약 5시간)이 핵심, 6~10번(약 1시간 45분)은 완성도 보강.

---

## 3. (나)-3: Fork 패널티 단계적 완화

### 3-1. 현재 방식

```python
if is_fork:
    contribution_axis *= 0.3   # 일괄 70% 감산
```

기여도와 무관하게 일괄 감산. 팀 프로젝트를 Fork한 핵심 기여자도 동일 패널티.

### 3-2. 문제

- 캡스톤/팀 프로젝트에서 조직 레포를 Fork하는 건 매우 흔함
- 본인 커밋 비율이 20~60%인 핵심 기여자도 70% 감산은 부당
- 오픈소스 PR 1회만 보낸 소극적 기여자와 동일 취급

### 3-3. 개선: 기여 비율 기반 3단계 패널티

```python
# github_extractor.py

def _calc_fork_penalty(
    is_fork: bool,
    target_commit_count: int,
    total_repo_commits: int,
    distinct_author_count: int,
) -> tuple[float, str]:
    """
    Fork 레포의 contribution 패널티 계수.

    기여 비율이 공정 기준(100% / 참여 인원 수) 이상이면 패널티를 완화한다.

    Returns: (패널티 계수, 로그 메시지)
        - 1.0: Fork가 아닌 레포
        - 0.7: Fork이지만 공정 기준 이상 기여 (30% 감산)
        - 0.5: Fork, 공정 기준의 50% 이상 기여 (50% 감산)
        - 0.3: Fork, 소극적 기여 (70% 감산, 기존값)
    """
    if not is_fork:
        return 1.0, ""

    if total_repo_commits <= 0 or distinct_author_count <= 0:
        return 0.3, "Fork: 커밋 데이터 부족 → 기본 패널티 0.3"

    contribution_ratio = target_commit_count / total_repo_commits
    fair_share = 1.0 / distinct_author_count

    if contribution_ratio >= fair_share:
        return 0.7, (
            f"Fork 패널티 완화: 기여 비율 {contribution_ratio:.1%} "
            f"≥ 공정 기준 {fair_share:.1%} ({distinct_author_count}명) → 계수 0.7"
        )
    if contribution_ratio >= fair_share * 0.5:
        return 0.5, (
            f"Fork 패널티 중간: 기여 비율 {contribution_ratio:.1%} "
            f"≥ 공정 기준의 50% ({fair_share * 0.5:.1%}) → 계수 0.5"
        )
    return 0.3, (
        f"Fork 소극적 기여: 기여 비율 {contribution_ratio:.1%} "
        f"< 공정 기준의 50% → 기본 패널티 0.3"
    )
```

### 3-4. 적용 위치

```python
# evaluate_repository() 내부 — 기존 Fork 패널티 코드 교체

# 기존
if is_fork:
    contribution_axis *= 0.3

# v6.2 변경
fork_penalty, fork_log = self._calc_fork_penalty(
    is_fork=is_fork,
    target_commit_count=target_commit_count,
    total_repo_commits=total_repo_commit_count,
    distinct_author_count=distinct_author_count,
)
if is_fork:
    contribution_axis *= fork_penalty
    if fork_log:
        repo_warnings.append(fork_log)
```

### 3-5. 결과에 패널티 정보 노출

```python
# evaluate_repository() 반환 dict에 추가
return {
    ...
    "fork_penalty": fork_penalty,       # v6.2
    "fork_penalty_log": fork_log,       # v6.2 (디버깅용)
    ...
}
```

### 3-6. 검증 시나리오

| 시나리오 | 참여자 | 본인 커밋 / 전체 | 비율 | 패널티 |
|---|---|---|---|---|
| 오픈소스 PR 1회 | 50명 | 2 / 500 | 0.4% (< 1%) | 0.3 (유지) |
| 캡스톤 팀 Fork | 5명 | 100 / 500 | 20% (= 20%) | **0.7** (완화) |
| 2인 팀 Fork | 2명 | 300 / 500 | 60% (> 50%) | **0.7** (완화) |
| Fork + 커밋 0 | 1명 | 0 / 300 | 0% | 0.3 (유지) |
| 템플릿 Fork 후 전부 본인 작성 | 1명 | 280 / 300 | 93% (≥ 100%) | **0.7** (완화) |
| Fork + 절반 미만 기여 | 4명 | 30 / 400 | 7.5% (< 12.5%) | **0.5** (중간) |

---

## 4. (나)-1: 총점 산출 방식 변경

### 4-1. 현재 방식

```python
# extract_applicant_profile() 내부
total_weight = sum(valid_loc for each repo)
github_score = sum(repo_score * valid_loc) / total_weight
```

LOC 가중 평균. LOC가 큰 레포가 총점을 지배하며, v6.1의 레포별 카드 진단과 불일치.

### 4-2. 개선: 대표 프로젝트 중심 + 레포별 점수 주 출력

**총점 산출 방식 변경:**

```python
# extract_applicant_profile() 내부 — github_score 산출 부분 교체

repo_scores = []
for r in valid_results:
    bd = r.get("score_breakdown", {})
    total = bd.get("contribution", 0) + bd.get("quality", 0) + bd.get("consistency", 0)
    repo_scores.append(total)

if repo_scores:
    best_score = max(repo_scores)
    avg_score = sum(repo_scores) / len(repo_scores)
    # 대표 프로젝트 70% + 전체 평균 30%
    github_score = round(best_score * 0.7 + avg_score * 0.3, 1)
else:
    github_score = 0.0
```

**레포별 점수를 per_repo에 명시:**

```python
# per_repo 각 항목에 이미 score_breakdown이 있으므로
# repo_total_score 필드를 추가해서 출력 편의 제공
for r in per_repo_list:
    bd = r.get("score_breakdown", {})
    r["repo_total_score"] = round(
        bd.get("contribution", 0) + bd.get("quality", 0) + bd.get("consistency", 0),
        1,
    )
```

### 4-3. 출력 변경

**종합 분석 블록 내부:**

```
[종합 분석]
  GitHub 종합 점수: 79.0점 / 100점
    산출 기준: 대표 프로젝트(최고점) 70% + 전체 평균 30%
    (기여도 42 / 성숙도 28 / 일관성 9) — 최고 레포 기준

  레포별 점수:
    1. my-backend (팀): 85.0점  (기여도 48 / 성숙도 28 / 일관성 9)
    2. my-sideproject (개인): 60.0점  (기여도 35 / 성숙도 20 / 일관성 5)
    3. toy-app (개인): 40.0점  (기여도 22 / 성숙도 10 / 일관성 8)
```

### 4-4. generate_summary_block() 갱신

```python
# portfolio_diagnosis.py generate_summary_block() 내부

def generate_summary_block(
    per_repo_diags, level_dict, github_score, score_breakdown,
    primary_domain, per_repo_scores=None,   # v6.2 추가
):
    ...
    lines = [
        "─" * 60,
        "[종합 분석]",
        "─" * 60,
        f"  GitHub 종합 점수: {github_score}점 / 100점",
        f"    산출 기준: 대표 프로젝트(최고점) 70% + 전체 평균 30%",
        f"    (기여도 {contrib} / 성숙도 {quality} / 일관성 {consistency})",
        "",
    ]

    # v6.2: 레포별 점수 표시
    if per_repo_scores:
        lines.append("  레포별 점수:")
        for i, rps in enumerate(per_repo_scores, 1):
            name = rps.get("repo_name", f"레포 {i}")
            rtype = rps.get("repo_type", "")
            total = rps.get("repo_total_score", 0)
            bd = rps.get("score_breakdown", {})
            type_label = f"{'팀' if rtype == 'team' else '개인'}"
            lines.append(
                f"    {i}. {name} ({type_label}): {total}점  "
                f"(기여도 {bd.get('contribution',0)} / "
                f"성숙도 {bd.get('quality',0)} / "
                f"일관성 {bd.get('consistency',0)})"
            )
        lines.append("")
    ...
```

### 4-5. 주의

- 총점 산출 방식 변경은 **이전 테스트 결과와 점수가 달라짐**. 회귀 테스트 시 "점수가 변동했다"는 것 자체는 예상 범위.
- 다만 **등급 판정(`expected_level`)에는 총점을 직접 사용하지 않으므로** 등급에는 영향 없음.
- 논문에서 총점을 언급한 부분이 있다면 갱신 필요.

---

## 5. (나)-2: Quality 점수 개인/팀 분리

### 5-1. 현재 방식

```python
# evaluate_repository() 내부
quality_axis = cicd_pts + test_pts + duration_pts
# 30점 만점: CI/CD 10 + 테스트 10 + 활성 주 10
# 개인/팀 무관하게 동일 수식
```

### 5-2. 문제

- 진단(모듈 B)에서는 개인 레포의 CI/CD·테스트를 "참고"로 격하했는데, **점수에서는 그대로 반영**하는 모순
- 개인 레포에 CI/CD와 테스트가 없으면 Quality 0~10점 → 총점 낮아짐
- "개인 레포에서는 필수가 아닙니다"(진단)와 "하지만 점수는 깎습니다"(점수)가 충돌

### 5-3. 개선: 레포 유형별 Quality 배점

```python
# evaluate_repository() 내부 — quality_axis 산출 부분 교체

if repo_type == "team":
    # 팀 레포: 기존 그대로 (CI/CD + 테스트 + 활성 주 균등 배점)
    quality_axis = cicd_pts + test_pts + duration_pts
    # cicd_pts: 10 또는 0
    # test_pts: 0 / 5 / 10
    # duration_pts: 0 / 5 / 10
else:
    # 개인 레포: 활성 주 중심 + CI/CD·테스트는 가산점
    # 활성 주(최대 20점): 꾸준히 작업한 증거가 개인 프로젝트의 핵심 Quality
    if active_weeks >= 8:
        duration_personal = 20.0
    elif active_weeks >= 4:
        duration_personal = 12.0
    elif active_weeks >= 2:
        duration_personal = 6.0
    else:
        duration_personal = 2.0

    # CI/CD 가산점(최대 5점): 있으면 보너스, 없어도 감점 아님
    cicd_bonus = 5.0 if has_cicd else 0.0

    # 테스트 가산점(최대 5점): 있으면 보너스, 없어도 감점 아님
    if test_ratio >= 0.10:
        test_bonus = 5.0
    elif test_ratio >= 0.05:
        test_bonus = 3.0
    else:
        test_bonus = 0.0

    quality_axis = duration_personal + cicd_bonus + test_bonus
    # 최대 30점 (20 + 5 + 5)
```

### 5-4. 효과 비교

**개인 레포, CI/CD 없음, 테스트 없음, 활성 8주:**

| | v6.1 | v6.2 |
|---|---|---|
| CI/CD | 0 | 0 |
| 테스트 | 0 | 0 |
| 활성 주 | 10 | **20** |
| Quality 합계 | **10** / 30 | **20** / 30 |

**개인 레포, CI/CD 있음, 테스트 있음, 활성 8주:**

| | v6.1 | v6.2 |
|---|---|---|
| CI/CD | 10 | **5** (가산) |
| 테스트 | 10 | **5** (가산) |
| 활성 주 | 10 | **20** |
| Quality 합계 | **30** / 30 | **30** / 30 |

개인 레포에서 CI/CD·테스트가 없어도 Quality가 20/30으로 합리적이 됨. 있으면 30/30으로 동일.

**팀 레포는 완전히 기존과 동일** (변경 없음).

### 5-5. score_breakdown에 레포 유형 명시

```python
# evaluate_repository() 반환
return {
    ...
    "score_breakdown": {
        "contribution": contribution_axis,
        "quality": round(quality_axis, 1),
        "consistency": consistency_axis,
        "quality_mode": repo_type,    # v6.2: "team" 또는 "personal"
    },
    ...
}
```

---

## 6. (나)-2 연장: 등급 판정 개인 전용 경로

### 6-1. 현재 방식

```python
# 팀 레포 0개면 Competitive 이상 도달 불가
if team_repo_count >= 1 and ...:
    return "Competitive"
```

### 6-2. 개선: 개인 프로젝트 경로 추가

```python
# portfolio_diagnosis.py expected_level() 내부

def expected_level(per_repo_diags, team_repo_count):
    ...

    # ── 기존 Top / Competitive 판정 (팀 레포 필수) ──
    if readme_ok and multi_proj and team_repo_count >= 1 \
       and has_test and has_cicd and has_deploy and score >= 8:
        return {"level": "Top", "summary": "..."}

    if readme_ok and team_repo_count >= 1 \
       and (has_cicd or has_deploy) and multi_proj and score >= 5:
        return {"level": "Competitive", "summary": "..."}

    # ── v6.2: 개인 프로젝트 전용 Competitive 경로 ──
    if team_repo_count == 0 and n_repos >= 2:
        all_core_good = all(
            _agg_status(k, "core_items") in ("양호", "보통")
            for k in ("readme_quality", "project_structure", "commit_quality")
        )
        # 개인 레포라도 운영 항목 양호가 2개 이상이면 인정
        personal_extras = sum(
            1 for d in per_repo_diags
            for k in ("test_coverage", "cicd", "deployment")
            if d["extra_items"][k]["status"] in ("양호", "규칙적")
        )

        if all_core_good and personal_extras >= 2 and score >= 5:
            return {
                "level": "Competitive (개인)",
                "summary": (
                    "팀 프로젝트 경험은 감지되지 않았으나, 개인 프로젝트의 완성도가 "
                    "Competitive 수준입니다. 팀 프로젝트 추가 시 더 강한 어필이 가능합니다."
                ),
            }

    # ── 기본 Entry ──
    if team_repo_count == 0 and n_repos >= 1:
        return {
            "level": "Entry",
            "summary": (
                "Entry 수준 — 중견·중소 SI 또는 일반 스타트업 지원 가능 수준. "
                "팀 프로젝트 1개 이상 확보 시 Competitive 등급에 도전할 수 있습니다."
            ),
        }

    return {
        "level": "Entry",
        "summary": "Entry 수준 — 중견·중소 SI 또는 일반 스타트업 지원 가능 수준입니다.",
    }
```

### 6-3. "Competitive (개인)" 조건 정리

| 조건 | 이유 |
|---|---|
| 개인 레포 2개 이상 | 다수 완성 프로젝트 증거 |
| core 3개 모두 양호/보통 | README·구조·커밋 메시지 기본기 충족 |
| 운영 항목(CI/CD·테스트·배포) 양호 2개 이상 | **개인이라도 품질 의식** 증거 |
| score >= 5 | 최소 기준 |

이 조건은 충분히 까다로워서 "아무거나 올려도 통과"하지 않음. 개인 프로젝트 2개에 CI/CD + 배포까지 세팅한 사용자는 실제로도 신입 중 상위 수준이야.

### 6-4. generate_summary_block() 포지셔닝 갱신

```python
# generate_summary_block() 내부

team_count = sum(1 for d in per_repo_diags if d.get("repo_type") == "team")

if level == "Top":
    pos_suffix = "상위 회사·서류 통과 가능성 높은 완성도입니다."
elif level == "Competitive":
    pos_suffix = "주요 항목 보강 시 상위 도전이 가능합니다."
elif level == "Competitive (개인)":
    pos_suffix = "개인 프로젝트 완성도가 우수합니다. 팀 프로젝트 추가 시 더 강한 어필이 가능합니다."
elif team_count == 0:
    pos_suffix = "경쟁력 있는 지원을 위해 팀 프로젝트 경험 확보가 권장됩니다."
else:
    pos_suffix = "경쟁력 있는 지원을 위해 보강이 필요합니다."
```

---

## 7. (가)-1: 봇 작성자 필터링 추가

### 7-1. 구현

```python
# github_extractor.py — 클래스 상수

class GitHubExtractor:
    _BOT_LOGIN_PATTERN = re.compile(
        r"\[bot\]$|^dependabot$|^github-actions$|^renovate-bot$"
        r"|^pre-commit-ci$|^codecov-commenter$|^stale\b",
        re.IGNORECASE,
    )

    @classmethod
    def _is_bot_author(cls, commit_obj: Dict[str, Any]) -> bool:
        gh_author = commit_obj.get("author") or {}
        login = str(gh_author.get("login") or "")
        if login and cls._BOT_LOGIN_PATTERN.search(login):
            return True
        raw = (commit_obj.get("commit") or {}).get("author") or {}
        email = str(raw.get("email") or "").lower()
        if "[bot]@" in email:
            return True
        if email == "noreply@github.com":
            return True
        # 일반 사용자의 users.noreply.github.com은 정상
        return False
```

### 7-2. evaluate_repository() 적용

```python
# distinct_author_count 산출 부분
for c in all_repo_commits:
    if self._is_bot_author(c):
        continue
    key = self._commit_author_key(c)
    if key:
        repo_author_keys.add(key)
        label = self._commit_author_label(c)
        if label and key not in seen_label_keys:
            repo_author_labels.append(str(label))
            seen_label_keys.add(key)
```

---

## 8. (가)-2: similarity_label "보통" 라벨 복원

```python
# run_git2value.py similarity_label() 내부

# 일반 spread 분포 — 절대 + 상대 혼합
if score >= 0.85:
    return "강함", None
if score >= 0.75 or score >= max_s - spread * 0.4:
    return "강함", None
if score >= 0.65:                       # v6.2 추가
    return "보통", None                  # v6.2 추가
return "약함", None
```

---

## 9. (가)-3: _print_extra_one_liner 활용

개인 레포에서 양호한 운영 항목만 "추가 강점 (참고)"로 한 줄 표시:

```python
# run_git2value.py _print_repo_card() 내부

if repo_type == "personal":
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

# 팀 레포: 기존 로직 유지
```

---

## 10. (가)-4: 등급 안내 강화

항목 6(§6)에서 이미 처리됨. `expected_level`의 Entry fallback에 팀 프로젝트 부재 시 안내 메시지 포함.

---

## 11. (가)-5: experience_filter 단위 테스트

```python
# experience_filter.py 하단

def _self_test():
    cases = [
        ("프론트엔드 개발자 신입", 0, True),
        ("백엔드 개발자 (경력 무관)", 0, True),
        ("개발자 신입/경력", 0, True),
        ("주니어 백엔드 개발자", 0, True),
        ("Junior Software Engineer", 0, True),
        ("백엔드 개발자 (경력 3년 이상)", 0, False),
        ("시니어 풀스택 개발자", 0, False),
        ("Senior Backend Engineer", 0, False),
        ("개발자 5년차", 0, False),
        ("백엔드 개발자 (경력 3~5년)", 0, False),
        ("개발자 1년 이상", 0, False),
        ("개발자 5년차", 5, True),
        ("백엔드 개발자 (경력 3~5년)", 4, True),
        ("개발자 1년 이상", 2, True),
        ("백엔드 개발자", 0, True),
        ("Software Engineer", 2, True),
    ]

    failed = []
    for position, years, expected in cases:
        req = extract_experience_requirement(position, "")
        eligible = is_applicant_eligible(req, years)
        if eligible != expected:
            failed.append((position, years, expected, eligible, req))

    if failed:
        print(f"❌ {len(failed)}/{len(cases)} 테스트 실패:")
        for p, y, exp, got, req in failed:
            print(f"  '{p}' (경력 {y}년): expected={exp}, got={got}, req={req}")
        return False

    print(f"✅ {len(cases)}/{len(cases)} 테스트 통과")
    return True

if __name__ == "__main__":
    _self_test()
```

---

## 12. (가)-6: repo_active_weeks 활용

팀 레포 커밋 리듬 하단에 활동 기간 비율 표시:

```python
# run_git2value.py _print_repo_card() 팀 레포 커밋 리듬 이후

if key == "commit_pattern":
    # ... 기존 협업 신호 ...
    target_weeks = int(diag.get("active_weeks") or 0)
    repo_weeks = int(diag.get("repo_active_weeks") or 0)
    if target_weeks > 0 and repo_weeks > 0 and repo_weeks >= target_weeks:
        coverage = round(target_weeks / repo_weeks * 100, 1)
        print(f"        활동 기간: 지원자 {target_weeks}주 / 레포 {repo_weeks}주 ({coverage}%)")
```

---

## 13. 적용 순서

```
1. github_extractor.py
   ├─ _is_bot_author() 추가                    (§7)
   ├─ _calc_fork_penalty() 추가                (§3)
   ├─ evaluate_repository():
   │   ├─ 봇 필터링 적용                        (§7)
   │   ├─ Fork 패널티 교체                      (§3)
   │   ├─ Quality 개인/팀 분리                  (§5)
   │   └─ repo_total_score 추가                (§4)
   └─ extract_applicant_profile():
       └─ 총점 산출 방식 변경                    (§4)

2. portfolio_diagnosis.py
   ├─ expected_level(): 개인 전용 경로 추가      (§6)
   ├─ generate_summary_block(): 레포별 점수 표시 (§4) + 포지셔닝 갱신 (§6)
   └─ diagnose_single_repo(): active_weeks/repo_active_weeks 전달 (§12)

3. run_git2value.py
   ├─ similarity_label(): "보통" 라벨 복원       (§8)
   ├─ _print_repo_card(): 개인 양호 extra 표시   (§9) + repo_active_weeks (§12)
   └─ 모듈 B 출력: 레포별 점수 + 총점 산출 기준 표시 (§4)

4. experience_filter.py
   └─ _self_test() 추가                         (§11)

5. 회귀 테스트
   ├─ 기존 4종 레포 (TCG, DeepSentinel, AI 서버, Unity)
   ├─ Dependabot 활성화 개인 레포 1종
   ├─ 팀 Fork 레포 1종 (기여 비율 > 공정 기준)
   └─ 개인 레포만 2개 (CI/CD + 배포 양호)
```

---

## 14. 검증 매트릭스

| 테스트 | 검증 항목 | 예상 결과 |
|---|---|---|
| Dependabot 개인 레포 | 봇 필터링 | `repo_type=personal` 유지 |
| 5명 팀 Fork (본인 20%) | Fork 패널티 | 계수 0.7, 경고 로그에 완화 메시지 |
| 오픈소스 Fork (본인 0.5%) | Fork 패널티 | 계수 0.3, 기존 동일 |
| 개인 레포 2개 (CI/CD+배포 양호) | Quality + 등급 | Quality ~25/30, "Competitive (개인)" |
| 개인 레포 2개 (CI/CD 없음) | Quality + 등급 | Quality ~20/30, "Entry" + 팀 권장 안내 |
| 팀 레포 1개 (CI/CD·테스트 양호) | Quality + 등급 | Quality 30/30, "Competitive" |
| 유사도 0.70 | similarity_label | 라벨 "보통" (v6.1에서는 "약함") |
| 개인 레포 + CI/CD 양호 | extra_one_liner | "추가 강점 (참고): ✓ CI/CD" 표시 |
| 레포 3개 (85점, 60점, 40점) | 총점 산출 | 85×0.7 + 61.7×0.3 = **78.0** (기존 LOC 가중: 79.0과 다름) |
| experience_filter 단위 테스트 | 정규식 | 16/16 통과 |

---

## 15. 발표/논문 영향

| 항목 | 영향 |
|---|---|
| 총점 산출 방식 변경 | 논문 §4(점수 구조) 갱신: "LOC 가중 평균" → "대표 프로젝트 70% + 전체 평균 30%" |
| Quality 개인/팀 분리 | 논문 §4(Quality 배점 표) 갱신: 개인 레포 배점 표 별도 추가 |
| Fork 패널티 완화 | 논문 §6(허위 이력 방지) 갱신: "기여 비율에 따른 3단계 패널티" 명시 |
| "Competitive (개인)" 등급 | 논문 §3(포트폴리오 진단) 갱신: 등급 표에 개인 경로 추가 |
| 발표 슬라이드 | 점수 산출 구조 슬라이드 갱신 (팀/개인 분리 시각화) |

**발표 어필 포인트:**
- "다양한 사용자 상황(개인/팀/Fork/다중 레포)에서 점수가 공정하게 나오도록 4단계에 걸쳐 개선"
- "Fork 패널티를 기여도에 비례하여 조정하는 공정성 메커니즘"
- "개인 프로젝트만으로도 뛰어난 사용자를 인정하는 등급 체계"

---

## 16. 리스크

| 리스크 | 가능성 | 대응 |
|---|---|---|
| 총점 변동으로 기존 테스트 결과와 비교 불가 | 확실 | 회귀 테스트 기대값을 v6.2 기준으로 갱신 |
| Quality 개인/팀 분리로 개인 레포 점수 상승 | 의도적 | 등급 판정의 Competitive 조건이 까다로우므로 오남용 방지 |
| Fork 패널티 완화가 허위 이력에 악용 | 낮음 | 커밋 내용이 아닌 커밋 수 기준이라 양치기에는 이미 SHA dedup 적용 |
| "Competitive (개인)" 등급이 사용자를 안주하게 함 | 낮음 | summary에 "팀 프로젝트 추가 시 더 강한 어필 가능" 명시 |
| 봇 패턴 누락으로 일부 봇 통과 | 중간 | 정규식 점진적 보강 |

---

## 17. v6.2 이후 (v7 검토 항목)

본 계획에서 다루지 않는 항목:

- **차등 가산점** (시그너처 vs 휴리스틱): 데이터 측정 후 결정
- **로컬 LLM 도입** (README 평가): RTX 4090 환경 별도 계획 파일
- **리멤버 400개 처리 결정**: 분포 분석 후 결정
- **Consistency 0.5 계수 데이터 기반 튜닝**: 지수 감쇠 전환 검토
- **공고 임베딩 재구성**: 직무명+요구기술 추출 재임베딩

---

*Git2Value v6.2 점수 공정성 + 후속 패치 통합 계획 — 2026.05.04*
