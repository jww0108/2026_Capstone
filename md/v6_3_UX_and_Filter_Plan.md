# Git2Value — v6.3 UX 용어 정리 + 경력 필터 강화 계획

> 작성일: 2026.05.11 | 대상 버전: v6.2 → v6.3
> 발견 계기: 팀원 3차 개선안 (3차_개선안.pdf) 검토 + 설계 세션 판정

---

## 1. 개요

본 계획은 팀원 3차 개선안에서 **즉시 반영 가능하고 리스크가 낮은 4개 항목**을 추출한 것이다.

3차 개선안의 전체 항목 중 v6.2에서 이미 해결된 Fork 패널티(문제 1~3)와 설계적으로 부적절한 세부 점수 가중 평균 통일(문제 4)을 제외하고, 나머지 타당한 제안을 v6.3으로 정리한다.

| 구분 | 3차 개선안 원문 | v6.3 반영 항목 |
|---|---|---|
| 문제 1~3 | Fork 패널티 고도화 | ✅ v6.2 완료 — 추가 작업 없음 |
| 문제 4 | 종합/세부 점수 기준 통일 | 🔴 반영 불필요 — 현 구현이 정확 |
| 문제 2 | "기여도" 용어 오해 | → **§3. 출력 용어 정리** |
| 문제 5 | "성숙도/안정성" 용어 부적합 | → **§3. 출력 용어 정리** |
| 문제 6 | 게임 프로젝트 Quick Wins 부적합 | → **§4. Quick Wins 게임 맥락 분기** |
| 문제 7 | 경력직 공고 필터 누락 | → **§5. 경력 필터 패턴 보강** |
| 문제 8 | 캐시 버전 미관리 | → **§6. 캐시 버전 관리 도입** |

**총 공수: 약 1시간 45분.** 코드 변경 범위가 좁고 기존 점수 로직에 영향 없음.

---

## 2. 작업 항목 우선순위

| 순위 | 항목 | 3차 개선안 근거 | 공수 |
|---|---|---|---|
| 🟡 1 | 출력 용어 정리 ("기여도" → "개발 활동량", "성숙도" → "프로젝트 운영도") | 문제 2, 5 | 30분 |
| 🟡 2 | Quick Wins 게임 엔진 맥락 분기 | 문제 6 | 30분 |
| 🟡 3 | 경력 필터 정규식 패턴 보강 | 문제 7 | 30분 |
| 🟢 4 | 경력 필터 캐시 버전 관리 | 문제 8 | 15분 |
| — | 회귀 테스트 (경력 필터 단위 테스트 보강 + 출력 확인) | — | 별도 |

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

## 7. 적용 순서

```
1. experience_filter.py
   ├─ CACHE_VERSION = 2 추가                     (§6)
   ├─ EXPERIENCE_PATTERNS 패턴 보강              (§5)
   ├─ load_or_build_cache() 버전 체크 추가       (§6)
   └─ _self_test() 케이스 9개 추가               (§5)

2. portfolio_diagnosis.py
   ├─ _QUICK_WINS_POOL_DEFAULT / _QUICK_WINS_POOL_GAME 분리  (§4)
   ├─ _aggregate_quick_wins() game_engines 파라미터 추가      (§4)
   ├─ generate_summary_block() 용어 변경 + game_engines 전달  (§3, §4)
   └─ run_diagnosis() game_engines 전달                      (§4)

3. run_git2value.py
   └─ _print_repo_card() 등 출력 문구 용어 변경              (§3)

4. 검증
   ├─ experience_filter _self_test(): 25개 케이스 전체 통과
   ├─ 캐시 삭제 후 재실행: 재구축 확인
   └─ Unity 레포 분석: Quick Wins 게임 맥락 출력 확인
```

---

## 8. 검증 매트릭스

| 테스트 | 검증 항목 | 예상 결과 |
|---|---|---|
| "경력 개발자" 공고 | 경력 필터 | `senior_only`, 0년차 제외 |
| "Experienced Engineer" 공고 | 경력 필터 | `senior_only`, 0년차 제외 |
| "Backend Developer 3+ years" 공고 | 경력 필터 | `min_years_exp(3)`, 0년차 제외 |
| "1~4년" 공고 (경력 prefix 없음) | 경력 필터 | `range_years(1)`, 0년차 제외 |
| "신입 가능" 공고 | 경력 필터 | `open_to_all`, 0년차 통과 |
| "Junior Developer 3+ years" 공고 | 패턴 우선순위 | `junior_only` (junior가 먼저 매칭), 0년차 통과 |
| 캐시 삭제 후 재실행 | 캐시 재구축 | `__version__: 2` 포함 확인 |
| 기존 캐시(버전 없음) 존재 시 | 버전 불일치 | 전체 재구축 |
| Unity 레포 (CI/CD 없음) | Quick Wins | "GameCI GitHub Action ..." 출력 |
| 웹 백엔드 레포 (CI/CD 없음) | Quick Wins | "GitHub Actions ... pytest, jest" 출력 |
| 종합 분석 블록 | 용어 변경 | "개발 활동량 / 프로젝트 운영도 / 작업 일관성" |

---

## 9. 영향 범위

### 영향 있는 파일

| 파일 | 변경 규모 | 내용 |
|---|---|---|
| `experience_filter.py` | 중간 | 패턴 보강 + 캐시 버전 + 테스트 케이스 |
| `portfolio_diagnosis.py` | 소규모 | Quick Wins 분기 + 용어 변경 |
| `run_git2value.py` | 소규모 | 출력 문구 용어 변경 |

### 영향 없는 파일

| 파일 | 이유 |
|---|---|
| `github_extractor.py` | 점수 산출 로직 변경 없음 |
| `profile_builder.py` | 변경 없음 |
| `valuation_engine.py` | 변경 없음 |

### 점수 변동

**없음.** 이번 변경은 출력 용어 + 경력 필터 + Quick Wins 문구만 대상이다. `contribution_axis`, `quality_axis`, `consistency_axis`, `_calc_fork_penalty()` 등 점수 산출 로직은 일절 변경하지 않는다.

---

## 10. 발표/논문 영향

| 항목 | 영향 |
|---|---|
| 용어 변경 | 논문 §4 점수 구조 표: "기여도/성숙도/일관성" → "개발 활동량/프로젝트 운영도/작업 일관성" |
| Quick Wins 게임 분기 | 논문 §3 포트폴리오 진단: "도메인 맥락 대응 피드백" 1줄 추가 |
| 경력 필터 강화 | 논문 §5 직무 매칭: "경력 필터 정규식 패턴 보강(영문 포함)" 1줄 추가 |
| 캐시 버전 | 논문 영향 없음 (구현 세부사항) |

---

## 11. 리스크

| 리스크 | 가능성 | 대응 |
|---|---|---|
| 영문 연차 패턴 오매칭 ("2 years warranty") | 낮음 | 공고 텍스트에 warranty 등 비경력 표현은 극소; position + text 합산 대상이므로 경력 문맥에서 사용됨 |
| `range_years` "경력" prefix 제거로 비경력 숫자 매칭 | 낮음 | `(\d+)\s*[~\-]\s*(\d+)\s*년` — "년" suffix 필수이므로 일반 숫자와 구분됨 |
| 게임 Quick Wins 풀이 특정 엔진에 부적합 | 낮음 | GameCI는 Unity 전용이지만, 문구가 "GameCI GitHub Action **또는** 엔진 빌드 자동화"로 범용 표현 |
| 캐시 전체 재구축 시 최초 실행 시간 증가 | 확실 | 3,400개 공고 × 정규식 6패턴 = 수초 이내. 이후 캐시 히트 |
| 용어 변경으로 기존 출력과 비교 시 혼란 | 낮음 | HandOff.md + 논문 동기 갱신으로 해소 |

---

## 12. v7 이후 검토 항목 (본 계획에서 미포함)

3차 개선안에서 제안되었으나 v6.3에서 다루지 않는 항목:

| 항목 | 사유 | 비고 |
|---|---|---|
| 개인 Fork LOC+커밋 수 기반 상한 적용 | 임계값 근거 데이터 필요 | v7에서 실제 Fork 레포 분포 분석 후 결정 |
| 점수 3축 전면 재정의 (50/30/20) | 연쇄 파급 범위 과다 | 팀원 개편안을 v7 로드맵 기초 자료로 보존 |
| 세부 점수 가중 평균 통일 | 설계적으로 부적절 | 현재 "최고 레포 기준" 표시가 정확 |
| 협업 신호 점수화 | v6.0에서 의도적 제거 | PR/이슈 API 없이 신뢰성 확보 불가 |

---

*Git2Value v6.3 UX 용어 정리 + 경력 필터 강화 계획 — 2026.05.11*
