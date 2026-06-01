# Git2Value — v6.3 UX 용어 정리 + 경력 필터 강화 + 봇/Fork 보강 계획

> 작성일: 2026.05.12 | 대상 버전: v6.2 → v6.3
> 발견 계기: (1) 팀원 3차 개선안 (3차_개선안.pdf) 검토 + (2) 추가 피드백 2건 (Fork 면제 조건, Streamlit 봇 오인식)

---

## 1. 개요

본 계획은 두 갈래의 작업을 통합한다:

**(가) 3차 개선안 반영** — 즉시 반영 가능하고 리스크가 낮은 4개 항목
**(나) 추가 피드백 반영** — Fork 감점 면제 조건 추가 + 봇 패턴 확장 및 커밋 카운트 정정 3건

3차 개선안의 전체 항목 중 v6.2에서 이미 해결된 Fork 패널티(문제 1~3)와 설계적으로 부적절한 세부 점수 가중 평균 통일(문제 4)을 제외하고, 나머지 타당한 제안 + 운영 중 발견된 봇 오인식 결함을 v6.3으로 정리한다.

| 구분 | 원문 | v6.3 반영 항목 |
|---|---|---|
| 3차 문제 1~3 | Fork 패널티 고도화 | ✅ v6.2 완료 — 추가 작업 없음 |
| 3차 문제 4 | 종합/세부 점수 기준 통일 | 🔴 반영 불필요 — 현 구현이 정확 |
| 3차 문제 2 | "기여도" 용어 오해 | → **§3. 출력 용어 정리** |
| 3차 문제 5 | "성숙도/안정성" 용어 부적합 | → **§3. 출력 용어 정리** |
| 3차 문제 6 | 게임 프로젝트 Quick Wins 부적합 | → **§4. Quick Wins 게임 맥락 분기** |
| 3차 문제 7 | 경력직 공고 필터 누락 | → **§5. 경력 필터 패턴 보강** |
| 3차 문제 8 | 캐시 버전 미관리 | → **§6. 캐시 버전 관리 도입** |
| 피드백 1 | Fork 감점 완전 면제 조건 | → **§7. Fork 감점 면제 조건 추가** |
| 피드백 2 | Streamlit 등 봇 오인식 + 커밋 카운트 오염 | → **§8. 봇 패턴 확장 + 커밋 카운트 정정** |

**총 공수: 약 2시간 30분.** §7~§8이 점수 로직에 영향을 주지만, 변경 범위가 `_calc_fork_penalty()` + `evaluate_repository()` 내부로 한정되어 리스크가 통제 가능하다.

---

## 2. 작업 항목 우선순위

| 순위 | 항목 | 근거 | 공수 |
|---|---|---|---|
| 🔴 1 | 봇 패턴 확장 + `total_repo_commit_count` 봇 제외 | 피드백 2 (점수 정확성) | 30분 |
| 🔴 2 | Fork 감점 면제 조건 (기여 80% + 커밋 20개 이상) | 피드백 1 (점수 공정성) | 15분 |
| 🟡 3 | 출력 용어 정리 ("기여도" → "개발 활동량", "성숙도" → "프로젝트 운영도") | 3차 문제 2, 5 | 30분 |
| 🟡 4 | Quick Wins 게임 엔진 맥락 분기 | 3차 문제 6 | 30분 |
| 🟡 5 | 경력 필터 정규식 패턴 보강 | 3차 문제 7 | 30분 |
| 🟢 6 | 경력 필터 캐시 버전 관리 | 3차 문제 8 | 15분 |
| — | 회귀 테스트 (봇 + Fork + 경력 필터 + 출력 확인) | — | 별도 |

---

## 3. 출력 용어 정리

### 3-1. 변경 이유 (3차 개선안 문제 2, 5)

**"기여도" 문제:**
현재 contribution 축은 유효 LOC + 커밋 수의 동적 가중 혼합이다. "기여도"라는 표현은 팀 내 참여율(팀 기여 비율)로 오해될 수 있다. 특히 개인 레포에서 "기여도가 낮다"는 출력이 "내가 기여를 안 했다는 건가?"라는 오해를 유발한다.

**"성숙도" 문제:**
현재 quality 축은 CI/CD + 테스트 + 활성 주(팀) 또는 활성 주 중심 + CI/CD·테스트 가산(개인)이다. "성숙도"는 코드 품질이나 아키텍처 수준을 연상시키지만, 실제 로직은 프로젝트 운영 체계(CI/CD, 테스트, 지속 개발)를 평가한다.

### 3-2. 용어 매핑

| 내부 key (변경 없음) | v6.2 출력 용어 | v6.3 출력 용어 | 이유 |
|---|---|---|---|
| `contribution` | 기여도 | **개발 활동량** | LOC + 커밋 수 기반임을 명확히 |
| `quality` | 성숙도 | **프로젝트 운영도** | CI/CD·테스트·활성 주 평가임을 명확히 |
| `consistency` | 일관성 | **작업 일관성** | 기존과 동일, "작업" prefix 추가로 맥락 보강 |

> **"프로젝트 관리도"(3차 개선안 원안) 대신 "프로젝트 운영도"를 채택한 이유:**
> 개인 레포에서 활성 주(20점)가 주 배점인데, "관리"는 조직적 관리를 연상시킨다. "운영"은 CI/CD·테스트("운영 체계") + 활성 주("지속적 운영") 양쪽을 포괄한다.

### 3-3. 변경 대상 파일 및 위치

**`portfolio_diagnosis.py` — `generate_summary_block()`:**

```python
# v6.2 (현재)
f"    (기여도 {contrib} / 성숙도 {quality} / 일관성 {consistency}) — 최고 레포 기준",

# v6.3 변경
f"    (개발 활동량 {contrib} / 프로젝트 운영도 {quality} / 작업 일관성 {consistency}) — 최고 레포 기준",
```

레포별 점수 표시도 동일 패턴 변경:

```python
# v6.2
f"(기여도 {bd.get('contribution', 0)} / "
f"성숙도 {bd.get('quality', 0)} / "
f"일관성 {bd.get('consistency', 0)})"

# v6.3
f"(개발 활동량 {bd.get('contribution', 0)} / "
f"프로젝트 운영도 {bd.get('quality', 0)} / "
f"작업 일관성 {bd.get('consistency', 0)})"
```

**`run_git2value.py` — `_print_repo_card()` 내 breakdown 출력:**

팀 레포 커밋 리듬 하단의 점수 표시에도 동일 용어 적용.

### 3-4. 변경하지 않는 것

- `score_breakdown` dict의 **key** (`"contribution"`, `"quality"`, `"consistency"`)는 하위 호환을 위해 유지
- 내부 변수명 (`contribution_axis`, `quality_axis`, `consistency_axis`)은 유지
- 논문·HandOff 문서는 v6.3 적용 후 일괄 갱신

---

## 4. Quick Wins 게임 엔진 맥락 분기

### 4-1. 문제 (3차 개선안 문제 6)

Unity/Unreal/Godot 프로젝트에서 `_aggregate_quick_wins()`가 정적 `_QUICK_WINS_POOL`을 참조하므로, 게임 프로젝트에도 "GitHub Actions 워크플로우 1개 추가 (Python: pytest, Node: jest)" 같은 웹 중심 피드백이 출력된다.

> 참고: 레포별 개별 진단(`_cicd_diagnosis_single`, `_test_diagnosis_single`, `_deployment_diagnosis_single`)은 이미 `game_engines` 파라미터로 게임 맥락 분기가 구현되어 있다. 문제는 **종합 Quick Wins만 분기가 없는 것**이다.

### 4-2. 현재 코드

```python
# portfolio_diagnosis.py

_QUICK_WINS_POOL: List[tuple] = [
    ("readme_quality", "README에 프로젝트 목적 + 기술 스택 + 스크린샷 1장 추가 (1시간 이내)"),
    ("commit_quality", "Conventional Commits 적용 (feat:/fix:/refactor:)"),
    ("cicd", "GitHub Actions 워크플로우 1개 추가 (Python: pytest, Node: jest)"),
    ("deployment", "Dockerfile + docker-compose.yml로 로컬 실행 가능하게 구성"),
    ("test_coverage", "핵심 비즈니스 로직 1~2개에 단위 테스트 추가"),
]
```

### 4-3. 개선: 게임 엔진별 Quick Wins 풀 추가

```python
# portfolio_diagnosis.py

_QUICK_WINS_POOL_DEFAULT: List[tuple] = [
    ("readme_quality", "README에 프로젝트 목적 + 기술 스택 + 스크린샷 1장 추가 (1시간 이내)"),
    ("commit_quality", "Conventional Commits 적용 (feat:/fix:/refactor:)"),
    ("cicd", "GitHub Actions 워크플로우 1개 추가 (Python: pytest, Node: jest)"),
    ("deployment", "Dockerfile + docker-compose.yml로 로컬 실행 가능하게 구성"),
    ("test_coverage", "핵심 비즈니스 로직 1~2개에 단위 테스트 추가"),
]

_QUICK_WINS_POOL_GAME: List[tuple] = [
    ("readme_quality", "README에 프로젝트 목적 + 기술 스택 + 스크린샷/GIF 1장 추가 (1시간 이내)"),
    ("commit_quality", "Conventional Commits 적용 (feat:/fix:/refactor:)"),
    ("cicd", "GameCI GitHub Action 또는 엔진 빌드 자동화 파이프라인 추가"),
    ("deployment", "빌드 결과물(APK/EXE) 또는 itch.io/스토어 배포 링크를 README에 명시"),
    ("test_coverage", "Unity Test Framework / Unreal Automation Tests 등 엔진 테스트 도구 추가"),
]
```

### 4-4. `_aggregate_quick_wins()` 수정

```python
def _aggregate_quick_wins(
    per_repo_diags: List[Dict[str, Any]],
    game_engines: Optional[Set[str]] = None,       # v6.3 추가
) -> List[str]:
    """미흡 항목 빈도순 Quick wins 추출. 게임 엔진 감지 시 게임 맥락 풀 사용."""
    bad_counter: Counter = Counter()
    for d in per_repo_diags:
        for key, item in d["core_items"].items():
            if item["status"] in _BAD_STATUSES:
                bad_counter[key] += 1
        if d.get("repo_type") == "team":
            for key in ("test_coverage", "cicd", "deployment"):
                if d["extra_items"][key]["status"] in _BAD_STATUSES:
                    bad_counter[key] += 1

    # v6.3: 게임 프로젝트면 게임 맥락 Quick Wins 풀 사용
    pool = _QUICK_WINS_POOL_GAME if game_engines else _QUICK_WINS_POOL_DEFAULT

    out: List[str] = []
    used = set()
    for key, action in pool:
        if key in bad_counter and key not in used:
            out.append(action)
            used.add(key)
        if len(out) >= 3:
            break
    return out
```

### 4-5. `generate_summary_block()` 호출 변경

```python
# generate_summary_block() 내부

def generate_summary_block(
    per_repo_diags, level_dict, github_score, score_breakdown,
    primary_domain, per_repo_scores=None,
    game_engines=None,                              # v6.3 추가
):
    ...
    quick_wins = _aggregate_quick_wins(per_repo_diags, game_engines=game_engines)
    ...
```

### 4-6. `run_diagnosis()` 호출 변경

```python
# run_diagnosis() 내부

def run_diagnosis(profile: Dict[str, Any]) -> Dict[str, Any]:
    per_repo = list(profile.get("per_repo") or [])
    game_engines = _collect_game_engines(per_repo)       # 기존 함수 활용

    ...
    summary_block = generate_summary_block(
        per_repo_diags, level_dict, github_score, score_breakdown,
        primary_domain, per_repo_scores=per_repo_scores,
        game_engines=game_engines,                       # v6.3 추가
    )
    ...
```

### 4-7. 검증 시나리오

| 시나리오 | Quick Wins cicd 항목 | Quick Wins deployment 항목 |
|---|---|---|
| 웹 백엔드 프로젝트 (CI/CD 없음) | "GitHub Actions 워크플로우 ... pytest, jest" | "Dockerfile + docker-compose.yml ..." |
| Unity 게임 프로젝트 (CI/CD 없음) | "GameCI GitHub Action ..." | "빌드 결과물(APK/EXE) 또는 itch.io ..." |
| 혼합 (웹 + 게임) | 게임 엔진이 1개라도 있으면 게임 풀 적용 | 동일 |

---

## 5. 경력 필터 정규식 패턴 보강

### 5-1. 문제 (3차 개선안 문제 7)

현재 `EXPERIENCE_PATTERNS`가 누락하는 공고 표현:

| 표현 | 현재 매칭 | 문제 |
|---|---|---|
| `"경력 개발자"` | ❌ | senior_only에 해당하나 패턴 없음 |
| `"경력직"` | ❌ | 동일 |
| `"Experienced Engineer"` | ❌ | 영문 경력 표현 누락 |
| `"3+ years"` / `"5+ years experience"` | ❌ | 영문 연차 패턴 누락 |
| `"1~4년"` (경력 prefix 없이) | ❌ | `range_years` 패턴에 "경력" prefix 필수 |

### 5-2. 패턴 보강

```python
# experience_filter.py

EXPERIENCE_PATTERNS: list[tuple[str, str]] = [
    # 1. 경력무관/신입+경력 (최우선)
    (r"경력\s*무관|경력무관|신입\s*/\s*경력|신입\s*및\s*경력|신입\s*또는\s*경력|신입\s*가능",
     "open_to_all"),

    # 2. 신입/주니어
    (r"신입|주니어|junior|entry\s*level",
     "junior_only"),

    # 3. 시니어/경력직 (v6.3: "경력 개발자", "경력직", "experienced" 추가)
    (r"시니어|senior|리드|lead|경력\s*개발자|경력직|experienced",
     "senior_only"),

    # 4. 한글 연차 범위 (v6.3: "경력" prefix 없이도 매칭)
    (r"(\d+)\s*[~\-]\s*(\d+)\s*년",
     "range_years"),

    # 5. 한글 "N년 이상"
    (r"(\d+)\s*년\s*이상",
     "min_years_exp"),

    # 6. 영문 "N+ years" / "N years" (v6.3 신규)
    (r"(\d+)\+?\s*years?\s*(?:of\s+)?(?:experience|exp)?",
     "min_years_exp"),

    # 7. 한글 "N년차"
    (r"(\d+)\s*년차",
     "specific_years"),
]
```

### 5-3. "신입 가능" 패턴 추가 이유

3차 개선안 개선 9번: "경력무관, 신입/경력, 신입 가능 등은 예외적으로 통과시키고, 단순히 무관이라는 단어만으로 경력무관으로 오판하지 않도록 개선"

현재 `open_to_all` 패턴에 "신입 가능"을 추가한다. 단순 "무관"은 기존과 동일하게 매칭하지 않는다 (이미 "경력무관"으로만 매칭).

### 5-4. 영문 패턴 주의사항

`"(\d+)\+?\s*years?"` 패턴은 "2 years of experience", "3+ years", "5 years exp" 등을 커버한다. 단, "10 years warranty" 같은 비경력 표현에 오매칭될 수 있으므로, `(?:experience|exp)?` suffix를 추가하되 optional로 두어 "3 years" 단독도 잡는다.

이 패턴이 `open_to_all`/`junior_only`/`senior_only` **이후**에 위치하므로, "Junior 3+ years" 같은 표현은 먼저 `junior_only`로 매칭되어 오판하지 않는다.

### 5-5. `extract_experience_requirement()` 수정

영문 연차 패턴이 `min_years_exp`로 매칭되므로 기존 `min_years_exp` 처리 로직을 그대로 재사용한다. 추가 코드 변경 없음.

### 5-6. 단위 테스트 케이스 보강

기존 16개에 다음 케이스 추가:

```python
# experience_filter.py _self_test() 내 cases 리스트에 추가

# v6.3 신규 케이스
("경력 개발자", 0, False, "경력(시니어)"),
("경력직 백엔드", 0, False, "경력(시니어)"),
("Experienced Engineer", 0, False, "경력(시니어)"),
("Backend Developer 3+ years", 0, False, "3년 이상"),
("5 years of experience required", 0, False, "5년 이상"),
("개발자 1~4년", 0, False, "1년 이상"),
("프론트엔드 2-5년", 0, False, "2년 이상"),
("신입 가능", 0, True, "경력무관"),
# 기존 패턴 우선순위 확인
("Junior Developer 3+ years", 0, True, "신입/주니어"),  # junior가 먼저 매칭
```

---

## 6. 경력 필터 캐시 버전 관리

### 6-1. 문제 (3차 개선안 문제 8)

`load_or_build_cache()`는 `requirement_type` 필드 유무만 확인한다:

```python
if job_id and (not cached or "requirement_type" not in cached):
```

정규식을 보강해도 기존 캐시에 `requirement_type`이 이미 있으면 재추출하지 않는다. 예: v6.2에서 "경력 개발자"를 `unspecified`로 캐시 → v6.3에서 패턴 추가해도 캐시 히트로 여전히 `unspecified` 반환.

### 6-2. 개선: `CACHE_VERSION` 도입

```python
# experience_filter.py 상단

# 패턴 변경 시 이 값을 증가시키면 캐시 전체 재구축
CACHE_VERSION = 2


def load_or_build_cache(metadata: list[dict], cache_path: str) -> dict[str, Any]:
    cache: dict[str, Any] = {}

    if os.path.exists(cache_path):
        try:
            with open(cache_path, "r", encoding="utf-8") as f:
                raw = json.load(f)
            # v6.3: 캐시 버전 불일치 시 전체 재구축
            if raw.get("__version__") != CACHE_VERSION:
                cache = {}
            else:
                cache = raw
        except (OSError, json.JSONDecodeError):
            cache = {}

    updated = False
    for entry in metadata:
        job_id = str(entry.get("job_id") or entry.get("id") or "")
        cached = cache.get(job_id)
        if job_id and (not cached or "requirement_type" not in cached):
            req = extract_experience_requirement(
                position=entry.get("position", ""),
                text=entry.get("text", ""),
            )
            cache[job_id] = req
            updated = True

    if updated:
        try:
            os.makedirs(os.path.dirname(cache_path) or ".", exist_ok=True)
            cache["__version__"] = CACHE_VERSION
            with open(cache_path, "w", encoding="utf-8") as f:
                json.dump(cache, f, ensure_ascii=False, indent=2)
        except OSError:
            pass

    return cache
```

### 6-3. `__version__` key 충돌 방지

`__version__`은 `__` prefix이므로 job_id와 충돌하지 않는다. `split_by_experience()`에서 `cache.get(job_id)`로 조회할 때 `__version__` key는 무시된다 (job_id가 `__version__`일 수 없음).

### 6-4. 버전 증가 규칙

| 변경 | 버전 증가 |
|---|---|
| 패턴 추가/수정 | ✅ 필수 |
| `is_applicant_eligible()` 로직 변경 | ❌ (캐시는 추출 결과만 저장, 적격 판정은 런타임) |
| 출력 문구 변경 | ❌ |

---

## 7. Fork 감점 면제 조건 추가

### 7-1. 문제 (피드백 1)

현재 `_calc_fork_penalty()`의 최대 완화가 **0.7(30% 감산)**이다. 기여 비율이 공정 기준 이상이어도 Fork라는 이유만으로 반드시 30%는 깎인다.

실제 문제 시나리오:

```
템플릿 Fork → 본인이 전체 커밋의 90% 작성, 사실상 유일한 기여자
→ 현재: contribution * 0.7 (30% 손실)
→ 실질: 이 사람이 프로젝트의 주인이므로 패널티가 부당
```

### 7-2. 면제 조건 설계

무조건 면제하면 Fork 원본의 초기 코드(보일러플레이트)가 LOC에 반영되어 점수가 부풀려질 위험이 있다. 따라서 **이중 게이트**를 적용한다:

| 조건 | 이유 |
|---|---|
| `contribution_ratio >= 0.8` | 커밋의 80% 이상이 본인 → 사실상 단독 저작 |
| `target_commit_count >= 20` | 충분한 양의 작업을 실제로 수행한 증거 |

두 조건 모두 만족해야 면제. `contribution_ratio >= 0.8` 단독으로는 부족하다 — 총 커밋 5개인 레포에서 4개만 본인이면 80%이지만, Fork 원본 위에 약간 수정한 것일 수 있다.

### 7-3. 구현

```python
# github_extractor.py — _calc_fork_penalty()

@staticmethod
def _calc_fork_penalty(
    is_fork: bool,
    target_commit_count: int,
    total_repo_commits: int,
    distinct_author_count: int,
) -> Tuple[float, str]:
    if not is_fork:
        return 1.0, ""

    if total_repo_commits <= 0 or distinct_author_count <= 0:
        return 0.3, "Fork: 커밋 데이터 부족 → 기본 패널티 0.3"

    contribution_ratio = target_commit_count / total_repo_commits
    fair_share = 1.0 / distinct_author_count

    # v6.3: 사실상 단독 저자 Fork → 면제
    if contribution_ratio >= 0.8 and target_commit_count >= 20:
        return 1.0, (
            f"Fork 감점 면제: 기여 비율 {contribution_ratio:.1%}, "
            f"본인 커밋 {target_commit_count}개 — 사실상 단독 저작"
        )

    if contribution_ratio >= fair_share:
        return 0.7, (
            f"Fork 패널티 완화: 기여 비율 {contribution_ratio:.1%} "
            f">= 공정 기준 {fair_share:.1%} ({distinct_author_count}명) → 계수 0.7"
        )
    if contribution_ratio >= fair_share * 0.5:
        return 0.5, (
            f"Fork 패널티 중간: 기여 비율 {contribution_ratio:.1%} "
            f">= 공정 기준의 50% ({fair_share * 0.5:.1%}) → 계수 0.5"
        )
    return 0.3, (
        f"Fork 소극적 기여: 기여 비율 {contribution_ratio:.1%} "
        f"< 공정 기준의 50% → 기본 패널티 0.3"
    )
```

### 7-4. 검증 시나리오

| 시나리오 | 본인 커밋 / 전체 | 비율 | 커밋 수 | 패널티 |
|---|---|---|---|---|
| 템플릿 Fork 후 전부 본인 작성 | 280 / 300 | 93% | 280 | **1.0 (면제)** |
| Fork + 비율 높지만 커밋 소량 | 4 / 5 | 80% | 4 | 0.7 (커밋 수 미달) |
| 캡스톤 팀 Fork (5명, 본인 20%) | 100 / 500 | 20% | 100 | 0.7 (완화) |
| 오픈소스 PR 1회 | 2 / 500 | 0.4% | 2 | 0.3 (유지) |

---

## 8. 봇 패턴 확장 + 커밋 카운트 정정

### 8-1. 문제 (피드백 2)

Streamlit Cloud 배포 시 자동 생성되는 커밋이 `streamlit` 사용자로 기록되어:
1. `distinct_author_count`가 2가 되어 **개인 레포가 팀 레포로 오분류**
2. 봇 커밋이 `total_repo_commit_count`에 포함되어 **지원자 커밋 비율 희석**

Streamlit 외에도 Vercel, Netlify, Heroku, Snyk 등 배포/의존성 서비스가 동일 문제를 일으킬 수 있다.

### 8-2. 두 가지 결함

**결함 A: 봇 패턴 부족**

현재 `_BOT_LOGIN_PATTERN`에 Streamlit, Vercel, Netlify 등이 없다.

**결함 B: `total_repo_commit_count`에 봇 커밋 포함**

v6.2에서 봇을 `distinct_author_count`에서 제외했지만, `total_repo_commit_count`는 `len(all_repo_commits)`로 봇 포함 카운팅이다.

```python
# 현재 코드 — 문제 지점
distinct_author_count = len(repo_author_keys) if repo_author_keys else 1  # ✅ 봇 제외
total_repo_commit_count = len(all_repo_commits)                           # ❌ 봇 포함!
```

이로 인해 Fork 패널티의 `contribution_ratio = target / total`에서 분모가 부풀려져, 실제로는 팀 내 최다 기여자인 지원자가 과도한 패널티를 받는다.

**예시:**

```
팀 Fork 레포, 총 커밋 200개
  지원자: 50개 / 팀원 A: 40개 / 팀원 B: 30개 / 봇 3종: 80개

현재 (봇 포함):  contribution_ratio = 50/200 = 25%, fair_share = 33% → 계수 0.5
정확 (봇 제외):  contribution_ratio = 50/120 = 41.7%, fair_share = 33% → 계수 0.7
```

### 8-3. 개선 A: `_BOT_LOGIN_PATTERN` 확장

```python
# github_extractor.py — 클래스 상수

_BOT_LOGIN_PATTERN = re.compile(
    # 기존 패턴
    r"\[bot\]$"
    r"|^dependabot$"
    r"|^github-actions$"
    r"|^renovate-bot$"
    r"|^pre-commit-ci$"
    r"|^codecov-commenter$"
    r"|^stale\b"
    # v6.3: 배포/호스팅 서비스 봇
    r"|^streamlit"              # streamlit, streamlit-bot
    r"|^vercel"                 # vercel, vercel[bot]
    r"|^netlify"
    r"|^heroku"
    r"|^railway"
    # v6.3: 의존성/보안 봇
    r"|^snyk"
    r"|^depfu"
    r"|^greenkeeper"
    r"|^imgbot$"
    r"|^allcontributors"
    r"|^whitesource"
    r"|^mend-bolt"
    # v6.3: 릴리스 봇
    r"|^semantic-release"
    r"|^release-drafter"
    r"|^changeset-bot",
    re.IGNORECASE,
)
```

### 8-4. 개선 B: `author.type == "Bot"` 범용 체크 추가

개별 서비스를 일일이 추가하는 것은 한계가 있다. GitHub API의 커밋 응답에서 `author` 객체에 `type` 필드가 포함되며, Bot 계정은 `"type": "Bot"`으로 반환된다. 이를 체크하면 패턴 목록에 없는 미래의 봇도 자동으로 잡힌다.

```python
@classmethod
def _is_bot_author(cls, commit_obj: Dict[str, Any]) -> bool:
    gh_author = commit_obj.get("author") or {}
    login = str(gh_author.get("login") or "")

    # 1차: 명시적 봇 패턴 매칭
    if login and cls._BOT_LOGIN_PATTERN.search(login):
        return True

    # v6.3 2차: GitHub author type이 "Bot"이면 봇 확정
    if str(gh_author.get("type") or "").lower() == "bot":
        return True

    # 3차: 이메일 기반 판별
    raw = (commit_obj.get("commit") or {}).get("author") or {}
    email = str(raw.get("email") or "").lower()
    if any(hint in email for hint in cls._BOT_EMAIL_HINTS):
        if "users.noreply.github.com" in email:
            return False
        return True

    return False
```

### 8-5. 개선 C: `total_repo_commit_count` 봇 제외

```python
# evaluate_repository() 내부 — 봇 필터링 루프 수정

repo_author_keys: Set[str] = set()
repo_author_labels: List[str] = []
seen_label_keys: Set[str] = set()
bot_count = 0
human_commit_count = 0                              # v6.3 추가

for c in all_repo_commits:
    if self._is_bot_author(c):
        bot_count += 1
        continue
    human_commit_count += 1                          # v6.3 추가
    key = self._commit_author_key(c)
    if key:
        repo_author_keys.add(key)
        label = self._commit_author_label(c)
        if label and key not in seen_label_keys:
            repo_author_labels.append(str(label))
            seen_label_keys.add(key)

if bot_count >= 5:
    repo_warnings.append(
        f"repo '{repo}' 봇 작성자 커밋 {bot_count}개 제외 (팀/개인 판정에 미반영)"
    )

distinct_author_count = len(repo_author_keys) if repo_author_keys else 1
repo_type = "team" if distinct_author_count >= 2 else "personal"
target_commit_count = len(all_author_commits)
total_repo_commit_count = human_commit_count         # v6.3 변경: 봇 제외
```

### 8-6. 영향 범위

이 변경으로 다음 지표들이 모두 정확해진다:

| 지표 | v6.2 | v6.3 |
|---|---|---|
| `distinct_author_count` | ✅ 봇 제외 | ✅ 유지 |
| `target_commit_count` | ✅ author 필터 | ✅ 유지 |
| `total_repo_commit_count` | ❌ 봇 포함 | ✅ **봇 제외** |
| `target_commit_ratio` | ❌ 분모 부풀림 | ✅ **정확** |
| Fork 패널티 `contribution_ratio` | ❌ 과소 평가 | ✅ **정확** |
| 출력 "전체 커밋 N개 중 지원자 M개 (X%)" | ❌ 비율 왜곡 | ✅ **정확** |

### 8-7. 봇 확인 방법 (팀원 안내용)

Streamlit이 사용된 레포에서 봇 커밋의 author 구조를 확인:

```bash
curl -H "Authorization: token $TOKEN" \
  "https://api.github.com/repos/{owner}/{repo}/commits?per_page=10" \
  | jq '.[].author | {login, type}'
```

이 결과에서 `login`과 `type` 값을 확인하여 패턴이 정확히 매칭되는지 검증한다.

---

## 9. 적용 순서

```
1. github_extractor.py  ★ 점수 영향 있는 파일 — 먼저 적용
   ├─ _BOT_LOGIN_PATTERN 확장                     (§8)
   ├─ _is_bot_author() author.type 체크 추가       (§8)
   ├─ evaluate_repository():
   │   ├─ human_commit_count 도입                  (§8)
   │   └─ total_repo_commit_count 봇 제외          (§8)
   └─ _calc_fork_penalty() 면제 조건 추가          (§7)

2. experience_filter.py
   ├─ CACHE_VERSION = 2 추가                     (§6)
   ├─ EXPERIENCE_PATTERNS 패턴 보강              (§5)
   ├─ load_or_build_cache() 버전 체크 추가       (§6)
   └─ _self_test() 케이스 9개 추가               (§5)

3. portfolio_diagnosis.py
   ├─ _QUICK_WINS_POOL_DEFAULT / _QUICK_WINS_POOL_GAME 분리  (§4)
   ├─ _aggregate_quick_wins() game_engines 파라미터 추가      (§4)
   ├─ generate_summary_block() 용어 변경 + game_engines 전달  (§3, §4)
   └─ run_diagnosis() game_engines 전달                      (§4)

4. run_git2value.py
   └─ _print_repo_card() 등 출력 문구 용어 변경              (§3)

5. 검증
   ├─ Streamlit 사용 레포: repo_type=personal 확인            (§8)
   ├─ 봇 활성 팀 Fork 레포: target_commit_ratio 봇 제외 확인  (§8)
   ├─ 템플릿 Fork (본인 90%+, 커밋 20+): 면제(1.0) 확인      (§7)
   ├─ experience_filter _self_test(): 25개 케이스 전체 통과    (§5)
   ├─ 캐시 삭제 후 재실행: 재구축 확인                         (§6)
   └─ Unity 레포 분석: Quick Wins 게임 맥락 출력 확인          (§4)
```

---

## 10. 검증 매트릭스

| 테스트 | 검증 항목 | 예상 결과 |
|---|---|---|
| Streamlit 사용 개인 레포 | 봇 필터링 | `repo_type=personal` 유지, `distinct_author_count=1` |
| Vercel 배포 개인 레포 | 봇 필터링 | 동일 |
| 봇 커밋 80개 포함 팀 Fork (본인 50/120) | 커밋 카운트 정정 | `total_repo_commit_count=120`, `ratio=41.7%`, 계수 0.7 |
| 템플릿 Fork (본인 280/300, 커밋 280개) | Fork 면제 | 계수 **1.0**, 로그 "사실상 단독 저작" |
| Fork + 비율 높지만 커밋 4개 | Fork 면제 불가 | 계수 0.7 (커밋 수 게이트 미달) |
| "경력 개발자" 공고 | 경력 필터 | `senior_only`, 0년차 제외 |
| "Experienced Engineer" 공고 | 경력 필터 | `senior_only`, 0년차 제외 |
| "Backend Developer 3+ years" 공고 | 경력 필터 | `min_years_exp(3)`, 0년차 제외 |
| "1~4년" 공고 (경력 prefix 없음) | 경력 필터 | `range_years(1)`, 0년차 제외 |
| "신입 가능" 공고 | 경력 필터 | `open_to_all`, 0년차 통과 |
| "Junior Developer 3+ years" 공고 | 패턴 우선순위 | `junior_only` (junior 먼저 매칭), 0년차 통과 |
| 캐시 삭제 후 재실행 | 캐시 재구축 | `__version__: 2` 포함 확인 |
| 기존 캐시(버전 없음) 존재 시 | 버전 불일치 | 전체 재구축 |
| Unity 레포 (CI/CD 없음) | Quick Wins | "GameCI GitHub Action ..." 출력 |
| 웹 백엔드 레포 (CI/CD 없음) | Quick Wins | "GitHub Actions ... pytest, jest" 출력 |
| 종합 분석 블록 | 용어 변경 | "개발 활동량 / 프로젝트 운영도 / 작업 일관성" |

---

## 11. 영향 범위

### 영향 있는 파일

| 파일 | 변경 규모 | 내용 |
|---|---|---|
| `github_extractor.py` | **중간** | 봇 패턴 확장 + author.type 체크 + 커밋 카운트 정정 + Fork 면제 |
| `experience_filter.py` | 중간 | 패턴 보강 + 캐시 버전 + 테스트 케이스 |
| `portfolio_diagnosis.py` | 소규모 | Quick Wins 분기 + 용어 변경 |
| `run_git2value.py` | 소규모 | 출력 문구 용어 변경 |

### 영향 없는 파일

| 파일 | 이유 |
|---|---|
| `profile_builder.py` | 변경 없음 |
| `valuation_engine.py` | 변경 없음 |

### 점수 변동

**§7~§8에 의한 점수 변동 있음.** 단, 정확성 향상 방향이므로 의도된 변동이다:

| 변경 | 점수 영향 |
|---|---|
| `total_repo_commit_count` 봇 제외 (§8) | 봇 커밋이 많은 레포에서 `target_commit_ratio` 상승 → Fork 패널티 완화 가능 |
| Fork 면제 조건 추가 (§7) | 기여 80%+ AND 커밋 20개+ Fork 레포에서 패널티 제거 → contribution 점수 상승 |
| 출력 용어/경력 필터/Quick Wins (§3~§6) | 점수 변동 없음 |

---

## 12. 발표/논문 영향

| 항목 | 영향 |
|---|---|
| 용어 변경 | 논문 §4 점수 구조 표: "기여도/성숙도/일관성" → "개발 활동량/프로젝트 운영도/작업 일관성" |
| Quick Wins 게임 분기 | 논문 §3 포트폴리오 진단: "도메인 맥락 대응 피드백" 1줄 추가 |
| 경력 필터 강화 | 논문 §5 직무 매칭: "경력 필터 정규식 패턴 보강(영문 포함)" 1줄 추가 |
| Fork 면제 | 논문 §6(허위 이력 방지): "기여 비율 80%+ 시 Fork 패널티 면제" 추가 |
| 봇 패턴 확장 | 논문 §4: "배포·의존성 서비스 봇 자동 제외(Streamlit, Vercel 등)" 1줄 추가 |
| 캐시 버전 | 논문 영향 없음 (구현 세부사항) |

---

## 13. 리스크

| 리스크 | 가능성 | 대응 |
|---|---|---|
| 봇 패턴 과잉 매칭 (사용자명이 "streamlit-fan" 등) | 낮음 | `^streamlit`은 prefix 매칭이므로 "streamlit-fan"도 잡힘. 실제 사용자가 이런 이름을 쓸 확률은 극소. 오탐 발생 시 정규식을 `^streamlit-?bot$\|^streamlit$`로 좁힐 수 있음 |
| Fork 면제 악용 (빈 커밋 20개 + 비율 80%) | 낮음 | contribution_axis 자체가 LOC + 커밋 수 혼합이므로 빈 커밋은 LOC=0 → 점수 낮음. 면제는 패널티 계수만 1.0으로 올리고 점수 자체를 높이지 않음 |
| `author.type` 필드가 모든 커밋에 존재하지 않을 수 있음 | 중간 | `str(gh_author.get("type") or "")` — 필드 없으면 빈 문자열로 처리, 기존 패턴 매칭으로 폴백 |
| 영문 연차 패턴 오매칭 ("2 years warranty") | 낮음 | 공고 텍스트에 warranty 등 비경력 표현은 극소 |
| `range_years` "경력" prefix 제거로 비경력 숫자 매칭 | 낮음 | "년" suffix 필수이므로 일반 숫자와 구분됨 |
| 게임 Quick Wins 풀이 특정 엔진에 부적합 | 낮음 | "GameCI GitHub Action **또는** 엔진 빌드 자동화"로 범용 표현 |
| 캐시 전체 재구축 시 최초 실행 시간 증가 | 확실 | 3,400개 공고 × 정규식 7패턴 = 수초 이내 |
| 커밋 카운트 정정으로 기존 테스트 결과와 비율 변동 | 확실 | 회귀 테스트 기대값을 v6.3 기준으로 갱신 |

---

## 14. v7 이후 검토 항목 (본 계획에서 미포함)

| 항목 | 사유 | 비고 |
|---|---|---|
| 개인 Fork LOC+커밋 수 기반 상한 적용 | 임계값 근거 데이터 필요 | v7에서 실제 Fork 레포 분포 분석 후 결정 |
| 점수 3축 전면 재정의 (50/30/20) | 연쇄 파급 범위 과다 | 팀원 개편안을 v7 로드맵 기초 자료로 보존 |
| 세부 점수 가중 평균 통일 | 설계적으로 부적절 | 현재 "최고 레포 기준" 표시가 정확 |
| 협업 신호 점수화 | v6.0에서 의도적 제거 | PR/이슈 API 없이 신뢰성 확보 불가 |

---

*Git2Value v6.3 UX 용어 정리 + 경력 필터 강화 + 봇/Fork 보강 계획 — 2026.05.12*
