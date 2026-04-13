# Git2Value — 유사도 표현 및 기술 키워드 매칭 개선 계획

> 작성일: 2026.04.09 | 대상 버전: v5.1 → v5.2
> 발견 계기: README 키워드 압축 적용 후 유사도 절대값 하락 + 공통 기술 키워드가 지원자와 무관한 문제

---

## 1. 문제 정의

### 문제 1: 유사도 수치가 사용자에게 의미 없다

README 원문을 키워드로 압축한 후 매칭 정확도는 올라갔지만, 유사도 절대값이 하락했다 (0.78 → 0.65).

현재 출력:
```
[1순위] [에스피코리아] 게임 개발자(1~3년) (유사도: 0.6539)
```

사용자 입장에서 "0.6539"가 좋은 건지 나쁜 건지 판단할 수 없다.
코사인 유사도의 절대값은 프로필 텍스트 길이, 공고 텍스트 스타일 등에 따라 크게 변동하기 때문에 수치 자체에 의미를 부여하기 어렵다.

### 문제 2: 공통 기술 키워드가 지원자와 무관하다

현재 출력:
```
공통 기술 키워드: Python, Java, JavaScript, React, Vue, Docker, AWS...
```

이건 **매칭된 공고들이 요구하는 기술**이지, 지원자가 보유한 기술이 아니다.
C# 100% 게임 개발자에게 "Python, React, Vue"를 보여주면 혼란을 준다.
사용자가 알고 싶은 건 "내가 가진 것 중 뭐가 맞고, 뭐가 부족한가"이다.

### 문제 3: 유사도 절대값 자체가 낮다 (근본 원인)

레이블링은 "낮은 유사도를 잘 포장하는 것"이지 근본 해결이 아니다.
README 원문 500자 → 키워드 압축 60자로 줄이면서 임베딩 입력의 정보량이 크게 감소했다.
공고 텍스트는 200~500자인데 프로필이 60자면 벡터 공간에서 정보가 희박하여 유사도 상한 자체가 낮아진다.

핵심 과제: **노이즈를 제거하면서도 정보량을 유지하는 것.**

---

## 2. 개선 방향

### 방향 A: 유사도 → 상대적 레이블 변환 (표현 개선)
### 방향 B: 공고 요구 기술 → 지원자 보유/미보유 교차 분석 (정보 개선)
### 방향 C: 프로필 텍스트 정보량 확대 (유사도 근본 개선)

---

## 3. 방향 A 상세: 유사도 레이블링

### 접근 방식: 분포 기반 백분위 레이블

전체 공고 3,400개에 대한 유사도 분포를 미리 계산해두고, 현재 매칭 유사도가 그 분포에서 어디에 위치하는지로 레이블을 부여한다.

### 구현

**1단계: 오프라인 — 유사도 분포 기준점 계산 (1회)**

프로필 텍스트 유형별로 분포가 다를 수 있으므로, 대표 프로필 여러 개로 기준점을 산출한다.
또는 간단하게 현재 쿼리의 상위 N개 유사도를 기준으로 상대 판단한다.

```python
def compute_similarity_thresholds(index, model, metadata, sample_queries: list[str], k=100):
    """
    샘플 쿼리들로 유사도 분포를 수집하여 레이블 기준점 산출.
    빌드 타임에 1회 실행, 결과를 JSON으로 저장.
    """
    all_scores = []
    for query in sample_queries:
        vec = model.encode([query], normalize_embeddings=True)
        distances, _ = index.search(vec, k)
        all_scores.extend(distances[0].tolist())

    all_scores.sort()
    n = len(all_scores)
    return {
        "p25": all_scores[int(n * 0.25)],
        "p50": all_scores[int(n * 0.50)],
        "p75": all_scores[int(n * 0.75)],
        "p90": all_scores[int(n * 0.90)],
    }

# 결과 예시 (가상):
# {"p25": 0.45, "p50": 0.55, "p75": 0.65, "p90": 0.75}
```

**2단계: 런타임 — 유사도를 레이블로 변환**

```python
def similarity_label(score: float, thresholds: dict) -> str:
    """유사도 점수를 사용자 친화적 레이블로 변환."""
    if score >= thresholds["p90"]:
        return "매우 높음"
    if score >= thresholds["p75"]:
        return "높음"
    if score >= thresholds["p50"]:
        return "보통"
    if score >= thresholds["p25"]:
        return "낮음"
    return "매우 낮음"
```

**3단계: 출력 변경**

```
변경 전:
  [1순위] [에스피코리아] 게임 개발자(1~3년) (유사도: 0.6539)

변경 후:
  [1순위] [에스피코리아] 게임 개발자(1~3년) (유사도: 0.6539 · 높음)
```

### 레이블별 의미 가이드 (리포트 하단에 표시)

```
매우 높음: 프로필과 매우 유사한 공고입니다
높음:     기술 스택이 상당 부분 겹칩니다
보통:     부분적으로 관련 있는 공고입니다
낮음:     관련성이 약합니다. 공고 DB 커버리지 부족일 수 있습니다
매우 낮음: 유사한 공고를 찾기 어렵습니다
```

### 간이 방식 (분포 사전 계산 없이)

분포 계산이 번거로우면, 현재 쿼리의 상위 5개 유사도만으로 상대 판단하는 간이 방식도 가능하다:

```python
def similarity_label_simple(score: float, top5_scores: list[float]) -> str:
    """상위 5개 유사도의 범위를 기준으로 레이블링."""
    max_s = max(top5_scores)
    min_s = min(top5_scores)
    spread = max_s - min_s

    if spread < 0.02:
        # 상위 5개가 비슷 → 전체적으로 낮은 유사도면 "보통", 높으면 "높음"
        return "높음" if max_s >= 0.70 else "보통"

    # 1순위 기준 상대 위치
    if score >= max_s - spread * 0.1:
        return "높음"
    if score >= max_s - spread * 0.4:
        return "보통"
    return "낮음"
```

이 방식은 추가 인프라 없이 바로 적용 가능하다.

---

## 4. 방향 B 상세: 기술 키워드 교차 분석

### 현재 동작

```python
# run_git2value.py — analyze_top_matches_pattern()
# 상위 공고 텍스트에서 기술 키워드를 추출 → 그대로 출력
found = [kw for kw in TECH_KEYWORDS_FOR_PATTERN if kw.lower() in combined_lower]
```

공고 쪽 키워드만 추출하고, 지원자 보유 기술과의 대조가 없다.

### 변경 후 동작

지원자가 보유한 기술과 공고가 요구하는 기술을 대조하여 **보유/미보유를 분리** 표시.

```python
def analyze_tech_match(
    applicant_languages: str,
    applicant_frameworks: list[str],
    top_matches: list[dict],
) -> dict:
    """지원자 보유 기술과 공고 요구 기술의 교차 분석."""

    # 지원자 보유 기술 세트 구성
    applicant_techs: set[str] = set()

    # 언어 통계에서 추출 ("C# (100%)" → "C#")
    for token in applicant_languages.replace(",", " ").split():
        clean = token.strip("()%0123456789").strip()
        if clean and len(clean) >= 2:
            applicant_techs.add(clean)

    # 프레임워크 추가
    for fw in applicant_frameworks:
        applicant_techs.add(fw)

    # 공고 요구 기술 추출 (기존 로직)
    blobs = []
    for m in top_matches:
        meta = m["meta"]
        blobs.append((meta.get("position") or "") + "\n" + (meta.get("text") or ""))
    combined_lower = "\n".join(blobs).lower()

    required_techs: list[str] = []
    for kw in TECH_KEYWORDS_FOR_PATTERN:
        if kw.lower() in combined_lower:
            required_techs.append(kw)

    # 교차 분석
    applicant_lower = {t.lower() for t in applicant_techs}
    matched = [kw for kw in required_techs if kw.lower() in applicant_lower]
    missing = [kw for kw in required_techs if kw.lower() not in applicant_lower]

    return {
        "applicant_techs": sorted(applicant_techs),
        "required_by_jobs": required_techs,
        "matched": matched,
        "missing": missing,
    }
```

### 출력 변경

```
변경 전:
  공통 기술 키워드: Python, Java, JavaScript, React, Vue, Docker, AWS...

변경 후:
  기술 매칭 분석:
    보유 & 공고 일치: C#
    공고 요구 중 미보유: Unity 경력 명시, Docker, AWS, Python
    → 공고에서 자주 요구하지만 포트폴리오에 드러나지 않는 기술입니다.
      해당 기술 경험이 있다면 README에 명시하세요.
```

### 포트폴리오 진단과의 연결

미보유 기술 목록은 모듈 B(포트폴리오 진단)의 개선 가이드와 자연스럽게 연결된다:

```
[모듈 A] 기술 매칭 분석:
  공고 요구 중 미보유: Docker, AWS

[모듈 B] 배포 진단:
  상태: 미경험
  권장: Docker 또는 클라우드 배포 경험을 추가하면 매칭 공고와의 기술 일치도가 올라갑니다.
```

---

## 5. 방향 C 상세: 프로필 텍스트 정보량 확대 (유사도 근본 개선)

### 원인

v5.1에서 README 노이즈 제거 후 프로필 텍스트가 약 60자로 줄었다.
공고 텍스트(200~500자)와 길이 차이가 크면 임베딩 벡터의 정보 밀도가 불균형해져 유사도 상한이 낮아진다.

### 해결: 노이즈 없이 정보량 늘리기

README 원문을 다시 넣는 게 아니라, **구조화 데이터에서 자동 생성한 문장**과 **도메인별 공고 어휘 템플릿**을 추가한다.

### 추가할 정보 3가지

**5-1. 프로젝트 규모 서술**

이미 가지고 있는 LOC, 레포 수 데이터를 문장으로 변환:

```python
loc = extracted_data.get("total_valid_loc", 0)
repos = extracted_data.get("scanned_repos", 0)
if loc > 5000:
    parts.append(f"총 {loc:,}줄 규모의 프로젝트 개발 경험")
if repos >= 2:
    parts.append(f"{repos}개 프로젝트 포트폴리오 보유")
```

**5-2. 도메인 맥락 문장 템플릿**

도메인이 감지되면 해당 도메인의 채용 공고에서 자주 쓰이는 표현을 추가한다.
이 문장들은 **실제 공고 어휘에서 추출한 것**이므로 임베딩 공간에서 해당 직무 공고와 가까워진다.

```python
DOMAIN_CONTEXT: dict[str, str] = {
    "게임 개발":     "게임 클라이언트 개발, 게임 로직 설계, 게임 엔진 활용",
    "웹 프론트엔드":  "웹 프론트엔드 개발, 사용자 인터페이스 구현, 반응형 웹",
    "서버/백엔드":    "서버 개발, API 설계, 데이터베이스 설계",
    "ML/AI":         "머신러닝 모델 개발, 데이터 분석, 모델 학습 및 추론",
    "모바일 앱":      "모바일 앱 개발, 네이티브 앱, 크로스플랫폼 개발",
    "DevOps/인프라":  "인프라 구축, 배포 자동화, 컨테이너 운영",
}

domains = extracted_data.get("detected_domains", [])
if domains and domains[0] in DOMAIN_CONTEXT:
    parts.append(DOMAIN_CONTEXT[domains[0]])
```

**5-3. README 도메인 키워드 (v5.1 방식 유지)**

`extract_readme_keywords()`는 그대로 유지. 노이즈 없는 키워드만 추가.

### 변경 전후 프로필 비교

```
v5.1 (약 60자):
  "C# (100%) 기반 게임 개발 경험. 게임, game, unity, 유니티, tcg 관련 프로젝트."

v5.2 (약 180자):
  "C# (100%) 기반 게임 개발 경험. 게임, game, unity, 유니티, tcg 관련 프로젝트.
   총 15,375줄 규모의 프로젝트 개발 경험.
   게임 클라이언트 개발, 게임 로직 설계, 게임 엔진 활용."
```

추가된 문장은 전부 **구조화 데이터에서 자동 생성**이거나 **공고 어휘 템플릿**이라서 README 노이즈가 재유입되지 않는다.

### 기대 효과

- 프로필 길이가 공고 텍스트 길이와 비슷한 수준(150~200자)으로 올라감
- "게임 클라이언트 개발, 게임 로직 설계" 같은 공고 어휘가 직접 포함되어 게임 공고와의 유사도가 상승
- README 원문 의존 없이 정보량 확보 → 노이즈 재유입 리스크 0

### build_profile_text() 최종 구조

```python
def build_profile_text(extracted_data: dict) -> str:
    parts = []

    # 1. 도메인 + 언어
    domains = extracted_data.get("detected_domains", [])
    langs = extracted_data.get("top_languages", "")
    if domains and langs and langs.upper() != "N/A":
        parts.append(f"{langs} 기반 {domains[0]} 경험")
    elif langs and langs.upper() != "N/A":
        parts.append(f"{langs} 기반 개발 경험")

    # 2. 프레임워크
    fw = extracted_data.get("frameworks", [])
    if fw:
        parts.append(f"{', '.join(fw)} 활용 경험")

    # 3. CI/CD, 테스트, 배포
    if extracted_data.get("has_cicd"):
        parts.append("CI/CD 파이프라인 구축 경험")
    if extracted_data.get("has_tests"):
        parts.append("테스트 코드 작성 경험")
    if extracted_data.get("has_deployment"):
        parts.append("배포 환경 구성 경험")

    # 4. README 도메인 키워드 (v5.1)
    readme_summary = extracted_data.get("readme_summary", "")
    readme_kw = extract_readme_keywords(readme_summary)
    if readme_kw:
        parts.append(readme_kw)

    # 5. 프로젝트 규모 (v5.2 신규)
    loc = extracted_data.get("total_valid_loc", 0)
    repos = extracted_data.get("scanned_repos", 0)
    if loc > 5000:
        parts.append(f"총 {loc:,}줄 규모의 프로젝트 개발 경험")
    if repos >= 2:
        parts.append(f"{repos}개 프로젝트 포트폴리오 보유")

    # 6. 도메인 맥락 문장 (v5.2 신규)
    if domains and domains[0] in DOMAIN_CONTEXT:
        parts.append(DOMAIN_CONTEXT[domains[0]])

    if not parts:
        return "GitHub 저장소 기반 개발 경험 (상세 메타데이터 부족)."
    return ". ".join(parts) + "."
```

### 추가 개선 (선택): 공고 쪽 임베딩 재구성

프로필 쪽만 개선해도 효과가 있지만, 공고 쪽도 정리하면 양쪽 모두 깔끔해진다.
현재 공고 임베딩에 회사 소개, 복지 정보 등 직무와 무관한 텍스트가 포함되어 있을 수 있다.
"직무명 + 요구 기술 + 자격 요건"만 추출하여 재임베딩하면 유사도가 추가 상승한다.

다만 3,400개 공고 재처리가 필요하므로 공수가 크다. 방향 C 적용 후 유사도가 충분히 올라가면 스킵 가능.

---

## 6. 출력 예시 (방향 A+B+C 전체 적용 후)

```
------------------------------------------------------------
[모듈 A] 직무 매칭 (FAISS) + 기술 매칭 분석
------------------------------------------------------------
  [1순위] [에스피코리아] 게임 개발자(1~3년) (유사도: 0.6539 · 높음)
  [2순위] [메타익스체인지] 프론트 개발 3-5년차 (유사도: 0.6407 · 보통)
  [3순위] [슈퍼센트] 게임 백엔드 개발자(5년 이상) (유사도: 0.6284 · 보통)
  [4순위] [펫박스] 프론트엔드 개발자_1~4년 (유사도: 0.6214 · 보통)
  [5순위] [카를로] C#, DB 관련 개발자 (유사도: 0.6176 · 보통)

  기술 매칭 분석:
    보유 기술: C#
    보유 & 공고 일치: C#
    공고 요구 중 미보유: Python, Java, JavaScript, React, Docker, AWS, Unity 명시
    → 포트폴리오에 드러나지 않는 기술입니다. 경험이 있다면 README에 명시하세요.
```

---

## 7. 구현 우선순위

| 순위 | 작업 | 난이도 | 예상 공수 | 비고 |
|---|---|---|---|---|
| 1 | 프로필 텍스트 정보량 확대: 프로젝트 규모 문장 추가 | 낮음 | 30분 | 방향 C. 기존 데이터 활용, 즉시 가능 |
| 2 | 프로필 텍스트 정보량 확대: 도메인 맥락 문장 템플릿 | 낮음 | 1시간 | 방향 C. 유사도 근본 개선의 핵심 |
| 3 | 간이 유사도 레이블 함수 구현 | 낮음 | 30분 | 방향 A. 분포 사전 계산 불필요 |
| 4 | 모듈 A 출력에 레이블 추가 | 낮음 | 30분 | 방향 A. 출력 포맷만 변경 |
| 5 | `analyze_tech_match()` 함수 구현 | 낮음 | 1~2시간 | 방향 B. 지원자 스택 파싱 + 교차 분석 |
| 6 | 모듈 A 출력에 기술 매칭 분석 추가 | 낮음 | 30분 | 방향 B. 출력 포맷 변경 |
| 7 | TCG 레포로 유사도 재테스트 | — | 30분 | 방향 C 적용 후 유사도 상승 확인 |
| 8 | (선택) 분포 기반 레이블 기준점 산출 | 중간 | 2~3시간 | 간이 방식으로 충분하면 스킵 |
| 9 | (선택) 공고 임베딩 재구성 | 높음 | 반나절~1일 | 방향 C로 충분하면 스킵 |

**권장 순서:** 1 → 2 → 7(중간 검증) → 3 → 4 → 5 → 6 → (테스트) → 8, 9는 필요시

---

## 8. 리스크

| 리스크 | 가능성 | 대응 |
|---|---|---|
| 도메인 맥락 문장이 공고와 너무 유사하여 과적합 | 낮음 | 템플릿이 6개 도메인 × 1문장으로 제한, 다양성 유지 |
| 도메인 감지 실패 시 맥락 문장 미추가 → 유사도 개선 없음 | 중간 | 도메인 미감지 시 언어 기반 범용 문장 폴백 |
| 프로필 길이 증가로 다른 도메인 공고와도 유사도 상승 | 낮음 | 도메인 특화 어휘만 사용하여 타 도메인 오매칭 방지 |
| 간이 레이블이 프로필 유형마다 편향 | 중간 | 분포 기반 방식으로 전환 가능 (순위 8) |
| 지원자 기술 파싱에서 노이즈 | 낮음 | 언어 통계 + 프레임워크만 사용, 범위 한정 |
| 미보유 기술 목록이 너무 길어서 압도적 | 중간 | 상위 5~6개만 표시, 나머지 생략 |
| "미보유"로 표시된 기술을 실제로는 알고 있을 수 있음 | 높음 | "포트폴리오에 드러나지 않는"이라는 표현 사용 |

---

*Git2Value — 유사도 표현 및 기술 키워드 개선 계획 v5.2 (방향 C 추가) — 2026.04.09*
