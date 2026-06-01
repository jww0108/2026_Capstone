# Git2Value — 다중 도메인 리랭킹 억제 및 키워드 커버리지 보강 계획

> 작성일: 2026.04.09 | 대상 버전: v5.3 → v5.3.1
> 발견 계기: AI CCTV 풀스택 프로젝트(DeepSentinel)에서 도메인 리랭킹 퇴행 발생

---

## 1. 문제 정의

### 1-1. 다중 도메인 프로젝트에서 리랭킹이 오작동한다

DeepSentinel은 AI 영상 분석 + Django 백엔드 + Next.js/React 프론트엔드가 하나의 레포에 있는 풀스택 프로젝트.

도메인 감지 결과: **"웹 프론트엔드"** (1순위)

이유: React 컴포넌트는 파일 하나당 하나씩 쪼개는 관행이 있어서 `component/`, `page/`, `layout/`, `header/`, `modal/` 등 프론트엔드 키워드 히트가 ML/AI나 백엔드보다 파일 수에서 압도적으로 많음.

결과: 리랭킹이 프론트엔드 공고에 +0.05를 부여 → FAISS 원본에서 4순위였던 프론트엔드 공고가 1순위로 올라옴 → **이전 버전(v5.2)에서 백엔드/AI로 잘 잡히던 매칭이 프론트엔드로 퇴행.**

### 1-2. README 키워드 사전의 ML/AI 영어 커버리지가 부족하다

DeepSentinel의 README:
```
🦅 DeepSentinel
AI-powered CCTV Video Analysis Platform for Unmanned Stores
"Replace expensive sensors with AI..."
```

현재 `README_KEYWORDS["ML/AI"]` 사전:
```python
["학습", "training", "모델", "추론", "inference", "데이터셋", "dataset", "파인튜닝", "fine-tuning"]
```

"AI-powered", "CCTV", "Video Analysis", "Detection" 같은 영어 키워드가 없어서 ML/AI 키워드 추출이 실패.
대신 "deploy", "monitoring"만 잡혀서 인프라 도메인으로 분류됨.

프로필 텍스트에 AI 관련 시그널이 빠지면서 FAISS 매칭도 AI/백엔드 공고에서 멀어짐.

### 1-3. 겸직 공고 제목의 라우팅 문제 (낮은 심각도)

"프론트·백엔드 개발자"라는 공고 제목에서 `route_job_category()`가 "백엔드"를 먼저 매칭하여 "서버/백엔드"로 분류.
결과적으로 이 공고가 "웹 프론트엔드" 도메인 부스트를 받지 못하고 순위가 밀림.

이건 풀스택/겸직 공고의 본질적 모호성이라 완전 해결은 어려움. 낮은 우선순위.

---

## 2. 해결 방향

| 항목 | 방향 | 심각도 |
|---|---|---|
| 다중 도메인 리랭킹 오작동 | 히트 비율 기반 리랭킹 억제 | 높음 |
| README ML/AI 키워드 부족 | 사전 보강 | 중간 |
| 도메인 히트 파일 수 편향 | 고유 키워드 종류 수로 전환 | 중간 |
| Conventional Commits 오탐 | 정규식 수정 (콜론 뒤 설명 허용) | 낮음 |
| 겸직 공고 라우팅 | 검토만, 구현은 선택 | 낮음 |

---

## 3. 수정 1: 다중 도메인 리랭킹 억제

### 원칙

단일 도메인이 압도적일 때만 리랭킹을 적용한다.
여러 도메인이 경합하는 풀스택/혼합 프로젝트에서는 FAISS 원본 순서를 유지한다.

### 판정 기준

도메인 감지에서 2개 이상 도메인이 잡혔을 때, 1순위 히트 수가 2순위의 **2배 미만**이면 "혼합 프로젝트"로 판단하고 리랭킹을 건너뜀.

```
예시 A — TCG 게임 레포:
  게임 개발: 12히트
  다른 도메인: 0히트
  → 단일 도메인 압도 → 리랭킹 적용 ✅

예시 B — DeepSentinel:
  웹 프론트엔드: 8히트
  ML/AI: 5히트
  DevOps/인프라: 3히트
  → 1순위(8) < 2순위(5) × 2 = 10 → 혼합 프로젝트 → 리랭킹 억제 ✅
```

### 구현

`rerank_by_domain()`에 `domain_hits` 파라미터를 추가하고 경합 체크 로직 삽입:

```python
DOMAIN_BOOST = 0.05

def rerank_by_domain(
    top_matches: list[dict],
    detected_domains: list[str],
    domain_hits: dict[str, int] | None = None,
) -> tuple[list[dict], str]:
    """
    Returns (reranked_matches, rerank_note).
    rerank_note: 리포트 하단에 표시할 리랭킹 상태 설명.
    """
    if not detected_domains:
        return top_matches, "도메인 감지 없음 — FAISS 유사도 순서 그대로 적용."

    primary_domain = detected_domains[0]
    expected_categories = DOMAIN_TO_CATEGORIES.get(primary_domain, [])
    if not expected_categories:
        return top_matches, "도메인 감지 없음 — FAISS 유사도 순서 그대로 적용."

    # 다중 도메인 경합 감지
    if domain_hits and len(detected_domains) >= 2:
        hits_sorted = sorted(domain_hits.values(), reverse=True)
        if len(hits_sorted) >= 2:
            top_hits = hits_sorted[0]
            second_hits = hits_sorted[1]
            if top_hits < second_hits * 2:
                note = (
                    f"다중 도메인 감지: {', '.join(detected_domains[:3])} "
                    f"(히트 비율 근접) — 혼합 프로젝트로 판단, "
                    f"리랭킹 미적용. FAISS 유사도 순서 유지."
                )
                return top_matches, note

    # 상위 N개 중 도메인 일치 공고가 하나도 없으면 리랭킹 불필요
    has_any_match = any(m["category"] in expected_categories for m in top_matches)
    if not has_any_match:
        note = (
            f"도메인 감지: '{primary_domain}' — "
            f"상위 공고에 일치 직무 없어 리랭킹 미적용."
        )
        return top_matches, note

    # 단일 도메인 압도 → 리랭킹 적용
    boosted = []
    for m in top_matches:
        effective = m["similarity"]
        domain_matched = m["category"] in expected_categories
        if domain_matched:
            effective += DOMAIN_BOOST
        boosted.append({
            **m,
            "effective_score": round(effective, 4),
            "domain_boosted": domain_matched,
        })
    boosted.sort(key=lambda x: x["effective_score"], reverse=True)

    note = (
        f"도메인 감지: '{primary_domain}' → "
        f"기대 직무와 일치하는 공고에 +{DOMAIN_BOOST} 가산 후 "
        f"유효 점수로 재정렬했습니다."
    )
    return boosted, note
```

### 호출부 변경

```python
# run_git2value.py
# domain_hits를 per_repo에서 병합하여 전달
merged_domain_hits: dict[str, int] = {}
for r in profile.get("per_repo") or []:
    for d in r.get("detected_domains") or []:
        # detected_domains는 이름 리스트이므로 domain_hits 원본이 필요
        pass

# → github_extractor에서 domain_hits를 per_repo에 포함시키거나,
#   profile 레벨에서 병합된 domain_hits를 별도 필드로 제공
```

**주의:** 현재 `per_repo`에 `detected_domains`(리스트)는 있지만 `domain_hits`(딕셔너리)는 없음.
`extract_applicant_profile()`에서 병합된 `merged_domain_hits` 딕셔너리를 profile에 추가로 반환하거나,
`run_git2value.py`에서 `profile_builder.merge_domain_hits()`의 원본 딕셔너리 버전을 사용해야 함.

가장 간단한 방법: `extract_applicant_profile()` 반환값에 `"domain_hits_merged"` 필드 추가.

```python
# github_extractor.py extract_applicant_profile() 끝부분
domain_hit_list = [res.get("domain_hits") or {} for res in valid_results]
merged_domain_hits_dict: Dict[str, int] = {}
for d in domain_hit_list:
    for k, v in d.items():
        merged_domain_hits_dict[k] = merged_domain_hits_dict.get(k, 0) + v

return {
    ...
    "domain_hits_merged": merged_domain_hits_dict,  # v5.3.1 추가
}
```

---

## 4. 수정 2: README_KEYWORDS ML/AI 영어 커버리지 보강

### 현재 사전

```python
"ML/AI": [
    "학습", "training", "모델", "추론", "inference",
    "데이터셋", "dataset", "파인튜닝", "fine-tuning",
],
```

### 보강 후

```python
"ML/AI": [
    # 기존 (한국어 + 기본 영어)
    "학습", "training", "모델", "추론", "inference",
    "데이터셋", "dataset", "파인튜닝", "fine-tuning",
    # v5.3.1 추가 (영어 커버리지)
    "ai", "artificial intelligence", "deep learning", "딥러닝",
    "machine learning", "머신러닝",
    "detection", "recognition", "classification",
    "yolo", "cnn", "transformer", "resnet",
    "computer vision", "영상 분석", "객체 탐지",
    "cctv", "video analysis", "image processing",
    "neural network", "신경망",
    "nlp", "자연어 처리", "natural language",
],
```

### 기대 효과

DeepSentinel README에서 "AI-powered", "Video Analysis", "CCTV", "Detection" 등이 매칭 → `extract_readme_keywords()`가 "ai, detection, cctv, video analysis 관련 프로젝트" 반환 → 프로필 텍스트에 AI 시그널이 포함됨 → FAISS가 AI/백엔드 공고 쪽으로 매칭.

### 다른 도메인 사전도 점검

게임과 웹은 이미 충분하지만, 서버/인프라 쪽도 영어 키워드를 보강하면 좋음:

```python
"서버": [
    # 기존
    "서버", "server", "API", "REST", "GraphQL",
    "데이터베이스", "database", "인증", "auth",
    # v5.3.1 추가
    "backend", "백엔드", "microservice", "마이크로서비스",
    "endpoint", "middleware", "orm",
],

"인프라": [
    # 기존
    "배포", "deploy", "컨테이너", "container",
    "쿠버네티스", "kubernetes", "모니터링", "monitoring",
    # v5.3.1 추가
    "docker", "ci/cd", "pipeline", "devops",
    "infrastructure", "terraform", "aws", "gcp", "azure",
],
```

---

## 5. 수정 3: 겸직 공고 라우팅 (낮은 우선순위, 선택)

### 문제

"프론트·백엔드 개발자" 제목 → `route_job_category()`가 "백엔드" 먼저 매칭 → "서버/백엔드"로 분류 → 프론트엔드 도메인 부스트 못 받음.

### 수정 방향

"풀스택"을 명시적으로 감지하는 패턴 추가:

```python
# route_job_category() — 풀스택 감지를 백엔드/프론트엔드보다 앞에 배치
if any(k in title_no_hyphen for k in ["풀스택", "fullstack"]):
    return "웹 풀스택"
# "프론트" + "백엔드" 동시 출현 → 풀스택으로 분류
if ("프론트" in title or "front" in title) and ("백엔드" in title or "backend" in title):
    return "웹 풀스택"
```

### 영향

"웹 풀스택"이 `DOMAIN_TO_CATEGORIES["웹 프론트엔드"]`에 이미 포함되어 있으므로, 프론트엔드 도메인 부스트를 받을 수 있게 됨.
다만 이건 다중 도메인 억제가 적용되면 부스트 자체가 안 걸리므로, DeepSentinel 케이스에서는 영향 없음.

**이 수정은 선택 사항. 다중 도메인 억제만으로 퇴행이 해결되면 스킵 가능.**

---

## 6. 수정 4: 도메인 히트 카운팅 — 파일 수 → 고유 키워드 종류 수

### 문제

현재 `detect_domain_hits()`가 "키워드가 포함된 파일 경로 수"를 센다.
React 프로젝트에서 `ComponentA.tsx`, `ComponentB.tsx`, `ComponentC.tsx`가 있으면 "component" 키워드가 3히트.
반면 ML 프로젝트에서 `model/`, `train/`, `inference/`가 있으면 각 1히트씩 3히트.

파일을 잘게 쪼개는 관행이 있는 프론트엔드가 파일 수에서 항상 우세하여, 풀스택 프로젝트에서 프론트엔드 도메인이 과대 평가됨.

### 해결

히트 수를 "매칭된 고유 키워드 종류 수"로 변경. 같은 키워드가 여러 파일에서 반복되어도 1히트.

```python
def detect_domain_hits(tree_data: Dict[str, Any]) -> Dict[str, int]:
    """도메인별 고유 키워드 종류 수. 최소 2종류 이상인 도메인만 포함."""
    blobs = _tree_blobs(tree_data)
    all_paths = [b["path"].lower().replace("\\", "/") for b in blobs]
    domain_hits: Dict[str, int] = {}
    for domain, keywords in DOMAIN_SIGNALS.items():
        # 파일 수가 아닌, 실제로 매칭된 키워드 종류 수를 카운트
        matched_keywords: set[str] = set()
        for p in all_paths:
            for kw in keywords:
                if kw in p:
                    matched_keywords.add(kw)
        if len(matched_keywords) >= 2:
            domain_hits[domain] = len(matched_keywords)
    return domain_hits
```

### 효과

```
변경 전 (파일 수 기반):
  웹 프론트엔드: component×30 + page×15 + layout×5 = 50히트
  ML/AI: model×2 + train×1 + inference×1 = 4히트
  → 프론트엔드 압도

변경 후 (고유 키워드 종류 수):
  웹 프론트엔드: component, page, layout, header, modal = 5종류
  ML/AI: model, train, inference, dataset = 4종류
  → 비율이 근접해져서 다중 도메인 억제가 정확하게 작동
```

이 변경은 다중 도메인 경합 판정(수정 1)과 시너지가 있음. 파일 수 편향이 제거되면 히트 비율이 실제 도메인 비중에 가까워져서, "2배 미만이면 혼합 프로젝트"라는 기준이 더 정확해짐.

### 영향 범위

`detect_domain_hits()`는 `profile_builder.py`에 있고, `github_extractor.py`의 `evaluate_repository()`에서 호출됨.
반환 타입(`Dict[str, int]`)이 동일하므로 호출부 변경 없음. 값의 의미만 "파일 수 → 키워드 종류 수"로 바뀜.

---

## 7. 수정 5: Conventional Commits 오탐 수정

### 문제

현재 정규식:
```python
MEANINGLESS_COMMIT_PATTERNS = re.compile(
    r"^(fix|update|wip|temp|test|merge|revert|chore|bump|initial commit)\b", re.I
)
```

"fix: 로그인 세션 만료 버그 해결" → "fix"로 시작 → 무의미로 분류됨.
실제로는 Conventional Commits 형식으로 의미 있는 메시지인데 오탐.

DeepSentinel 테스트에서 "커밋 메시지 개선 필요 (40% 무의미)"라고 나왔는데, 이 중 상당수가 "fix:", "chore:" 같은 Conventional Commits일 가능성이 높음.

### 해결

콜론 뒤에 설명이 있으면 Conventional Commits로 인정하고, 키워드만 단독으로 쓰인 경우만 무의미로 잡음:

```python
MEANINGLESS_COMMIT_PATTERNS = re.compile(
    r"^("
    r"(fix|update|wip|temp|test|merge|revert|chore|bump)\s*$"       # 단독 사용 (설명 없음)
    r"|initial\s+commit\s*$"                                         # "initial commit" 단독
    r"|(fix|update|wip|temp|test)\s+[^:\s]"                          # "fix something" (콜론 없이 바로 내용)
    r")",
    re.I,
)
```

매칭되는 것:
- `"fix"` → 무의미 ✅
- `"update"` → 무의미 ✅
- `"fix bug"` → 무의미 ✅ (콜론 없이 바로 내용)
- `"initial commit"` → 무의미 ✅

매칭 안 되는 것 (Conventional Commits로 인정):
- `"fix: 로그인 세션 만료 버그 해결"` → 유의미 ✅
- `"chore: 의존성 업데이트"` → 유의미 ✅
- `"feat: 사용자 인증 기능 추가"` → 유의미 ✅ (feat는 원래 패턴에 없음)

### 수정 위치

`portfolio_diagnosis.py` 상단의 `MEANINGLESS_COMMIT_PATTERNS` 상수.

---

## 8. 예상 결과

### DeepSentinel (AI CCTV 풀스택)

```
도메인 감지:
  웹 프론트엔드: 8히트
  ML/AI: 7히트 (키워드 보강 후 증가)
  DevOps/인프라: 3히트

1순위(8) < 2순위(7) × 2 = 14 → 혼합 프로젝트 → 리랭킹 억제

프로필 텍스트 (키워드 보강 후):
  "TypeScript (43%), Python (39%)... 기반 웹 프론트엔드 경험.
   React, Next.js, Django 활용 경험. CI/CD... 배포...
   ai, detection, cctv, video analysis 관련 프로젝트."

FAISS 원본 순서 유지 → 이전처럼 백엔드/AI 공고가 상위
리포트 하단: "다중 도메인 감지: 웹 프론트엔드, ML/AI, DevOps/인프라
             (히트 비율 근접) — 혼합 프로젝트로 판단, 리랭킹 미적용."
```

### TCG 게임 레포 (C# Unity)

```
도메인 감지:
  게임 개발: 12히트
  (다른 도메인 없음)

단일 도메인 압도 → 리랭킹 정상 적용
→ v5.3 결과 그대로 유지 (게임 개발자 1순위)
```

### Python 백엔드 단일 레포

```
도메인 감지:
  서버/백엔드: 10히트
  (다른 도메인 없거나 미미)

단일 도메인 압도 → 리랭킹 적용 → 백엔드 공고 강화
→ 기존 결과 유지 또는 개선
```

---

## 9. 구현 우선순위

| 순위 | 작업 | 난이도 | 예상 공수 |
|---|---|---|---|
| 1 | `detect_domain_hits()` 파일 수 → 고유 키워드 종류 수로 변경 | 낮음 | 30분 |
| 2 | `README_KEYWORDS` ML/AI + 서버 + 인프라 영어 키워드 보강 | 낮음 | 30분 |
| 3 | `MEANINGLESS_COMMIT_PATTERNS` Conventional Commits 오탐 수정 | 낮음 | 30분 |
| 4 | `extract_applicant_profile()`에 `domain_hits_merged` 필드 추가 | 낮음 | 15분 |
| 5 | `rerank_by_domain()`에 다중 도메인 경합 체크 + 리랭킹 억제 로직 | 낮음 | 1시간 |
| 6 | 리포트 출력에 리랭킹 상태 메시지 반영 | 낮음 | 30분 |
| 7 | DeepSentinel 레포로 테스트 (퇴행 해소 확인) | — | 30분 |
| 8 | TCG 게임 레포로 퇴행 테스트 (리랭킹 여전히 정상 작동 확인) | — | 15분 |
| 9 | (선택) 겸직 공고 라우팅 수정 | 낮음 | 30분 |

**권장 순서:** 1 → 2 → 3 → 4 → 5 → 6 → 7 → 8 → 9는 필요시

---

## 10. 리스크

| 리스크 | 가능성 | 대응 |
|---|---|---|
| 2배 기준이 너무 관대해서 리랭킹이 거의 안 걸림 | 낮음 | 단일 도메인 프로젝트에서는 경합 도메인이 없거나 미미하므로 정상 작동. 기준값은 테스트 후 조정 가능 |
| ML/AI 키워드 "ai"가 너무 범용적이라 오탐 | 중간 | "ai"는 1히트만 기여. 다른 ML 키워드와 함께 2종류 이상 매칭돼야 도메인으로 인정 |
| 키워드 보강 후 README 키워드 추출이 여러 도메인에서 동시 매칭 | 낮음 | `extract_readme_keywords()`는 히트 수 최다 도메인 1개만 선택 |
| domain_hits_merged 추가로 profile JSON 크기 증가 | 무시 | dict 하나 추가, 수십 바이트 수준 |
| 고유 키워드 방식에서 키워드가 짧아서 의도치 않은 매칭 | 낮음 | DOMAIN_SIGNALS 키워드가 대부분 4자 이상. "page" 같은 짧은 키워드는 다른 도메인 키워드와 함께 2종류 이상 매칭돼야 인정 |
| Conventional Commits 정규식이 일부 엣지 케이스를 놓침 | 낮음 | "fix something" 패턴은 잡되 "fix: something"은 허용. 완벽하지 않지만 현재보다 크게 개선 |

---

## 11. 알려진 한계 (이번에 해결 안 되는 것)

| 한계 | 이유 | 향후 방향 |
|---|---|---|
| ~~도메인 감지 자체가 파일 수에 편향됨~~ | ✅ v5.3.1 수정 6에서 고유 키워드 종류 수로 전환 | — |
| DOMAIN_SIGNALS에 없는 도메인 | 정보보안, 블록체인, 데이터 엔지니어링 등 미커버 | 해당 도메인 테스트 케이스 확보 시 사전 추가 |
| 단일 레포에 여러 서비스가 모노레포로 있는 경우 | 도메인 감지가 모든 서비스를 뒤섞어서 판단 | 디렉토리 깊이 기반 서브 프로젝트 분리 (장기 과제, 캡스톤 범위 밖) |

---

*Git2Value — 다중 도메인 리랭킹 억제 계획 v5.3.1 — 2026.04.09*
