# Git2Value — 도메인 기반 하이브리드 리랭킹 계획

> 작성일: 2026.04.09 | 대상 버전: v5.2 → v5.3
> 발견 계기: 프로필 텍스트 튜닝만으로는 공고 DB 분포 불균형을 극복할 수 없음

---

## 1. 문제 요약

### 프로필 텍스트 튜닝의 한계에 도달

| 버전 | 프로필 전략 | 게임 공고 순위 | 1순위와의 유사도 차이 |
|---|---|---|---|
| v5.1 | 키워드 압축만 (60자) | **1순위** (0.6539) | — |
| v5.2 | + 맥락 문장 추가 (180자) | 2순위 (0.7158) | 0.0148 |
| v5.2 수정 | + 어휘 특화 + LOC 제거 | 2순위 (0.6834) | 0.0038 |

프로필 정보량을 늘리면 유사도 절대값은 올라가지만, 프론트엔드 공고와의 유사도도 같이 올라감.
프론트엔드/SW 공고가 DB에서 압도적으로 많기 때문에, 확률적으로 항상 하나가 게임 공고보다 미세하게 가까운 위치에 존재함.

**결론: 임베딩 유사도 단일 시그널만으로는 공고 DB 분포 불균형을 극복할 수 없음.**

---

## 2. 해결 방향: 하이브리드 리랭킹

두 개의 독립적인 시그널을 결합:

```
시그널 1: FAISS 임베딩 유사도 (텍스트 의미 유사성)
시그널 2: 파일명/폴더명 도메인 감지 (구조적 메타데이터)
```

FAISS가 상위 N개를 뽑은 후, 도메인 감지 결과와 일치하는 공고에 가산점을 부여하여 재정렬.
FAISS 원본 유사도는 변경하지 않으며, 보정 과정을 리포트에 투명하게 표시.

이 방식은 정보 검색에서 표준적인 하이브리드 랭킹이며, 단일 시그널보다 정확도가 높음.

---

## 3. 프로필 텍스트 전략 변경

### v5.2 맥락 문장을 제거하고 v5.1 방식으로 복원

v5.1에서 게임이 1순위였고, v5.2에서 맥락 문장을 추가하면서 오히려 밀렸으므로:

```
v5.3 프로필 = v5.1 방식 유지
  - 도메인 + 언어 결합 ("C# 기반 게임 개발 경험")
  - README 키워드 압축 ("게임, unity, 유니티, tcg 관련 프로젝트")
  - 프레임워크, CI/CD, 테스트, 배포 (해당 시)
  - DOMAIN_CONTEXT 맥락 문장: 제거
  - LOC 규모 문장: 제거
```

매칭 순서는 리랭킹이 담당하고, 프로필 텍스트는 깔끔하게 유지.

### build_profile_text() 변경

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

    # 4. README 키워드 압축 (v5.1)
    readme_summary = extracted_data.get("readme_summary", "")
    if readme_summary and len(readme_summary) >= 200:
        readme_kw = extract_readme_keywords(readme_summary)
        if readme_kw:
            parts.append(readme_kw)
        # 키워드 없으면 아무것도 추가하지 않음 (원문 폴백 제거)

    # DOMAIN_CONTEXT 맥락 문장: 삭제
    # LOC 규모 문장: 삭제
    # → 이 정보는 모듈 B 진단에서 제공

    if not parts:
        return "GitHub 저장소 기반 개발 경험 (상세 메타데이터 부족)."
    return ". ".join(parts) + "."
```

---

## 4. 리랭킹 함수 구현

### 핵심 함수

```python
DOMAIN_BOOST = 0.05  # 도메인 일치 시 유사도에 가산

def rerank_by_domain(
    top_matches: list[dict],
    detected_domains: list[str],
) -> list[dict]:
    """
    FAISS 상위 N개 결과를 도메인 감지 결과로 리랭킹.
    FAISS 원본 유사도(similarity)는 보존하고, effective_score를 별도 추가.
    """
    if not detected_domains:
        return top_matches

    primary_domain = detected_domains[0]
    expected_categories = DOMAIN_TO_CATEGORIES.get(primary_domain, [])
    if not expected_categories:
        return top_matches

    # 상위 N개 중 도메인 일치 공고가 하나도 없으면 리랭킹 불필요
    has_any_match = any(m["category"] in expected_categories for m in top_matches)
    if not has_any_match:
        return top_matches

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
    return boosted
```

### 파이프라인 적용 위치

```python
# run_git2value.py — FAISS 검색 직후, 리포트 출력 전
top_matches = [...]  # FAISS 상위 5개 (기존)
detected_domains_merged = merged_detected_domains_from_profile(profile)

# 리랭킹 적용
top_matches = rerank_by_domain(top_matches, detected_domains_merged)

# 리랭킹 후 1순위로 라우팅
jumpit_category = top_matches[0]["category"]
```

---

## 5. 리포트 출력 변경

### 리랭킹 과정을 투명하게 표시

```
------------------------------------------------------------
[모듈 A] 직무 매칭 (FAISS + 도메인 리랭킹)
------------------------------------------------------------
  [1순위] [에스피코리아] 게임 개발자(1~3년)
          (FAISS: 0.6834 + 도메인 일치: +0.05 → 유효: 0.7334 · 높음)
  [2순위] [메타익스체인지] 프론트 개발 3-5년차
          (FAISS: 0.6872 · 보통)
  [3순위] [슈퍼센트] 게임 백엔드 개발자(5년 이상)
          (FAISS: 0.6663 + 도메인 일치: +0.05 → 유효: 0.7163 · 보통)
  ...

  도메인 감지: '게임 개발' → 게임 관련 공고에 +0.05 가산 적용
```

### 도메인 감지가 없는 경우

리랭킹을 적용하지 않고 기존 FAISS 순서 그대로 출력.
"도메인 감지: 없음 (FAISS 유사도 순서 그대로 적용)" 표시.

---

## 6. 예상 결과

### TCG 게임 레포 (C# 100%, Unity)

```
프로필 텍스트 (v5.1 복원):
  "C# (100%) 기반 게임 개발 경험. 게임, game, unity, 유니티, tcg 관련 프로젝트."

도메인 감지: "게임 개발"

FAISS 원본 순서 (v5.1 기준):
  1. 에스피코리아 게임 개발자      0.6539
  2. 메타익스체인지 프론트 개발      0.6407
  3. 슈퍼센트 게임 백엔드           0.6284
  4. 펫박스 프론트엔드              0.6214
  5. 카를로 C#/DB                  0.6176

리랭킹 후 (도메인 일치 +0.05):
  1. 에스피코리아 게임 개발자      0.6539 + 0.05 = 0.7039 ★
  2. 슈퍼센트 게임 백엔드          0.6284 + 0.05 = 0.6784 ★
  3. 메타익스체인지 프론트 개발     0.6407
  4. 펫박스 프론트엔드             0.6214
  5. 카를로 C#/DB                 0.6176

→ 게임 공고가 1, 2순위를 확보. 프론트엔드는 3순위 이하로 밀림.
→ 라우팅 직무: "게임 클라이언트" → 연봉 밴드도 게임 직무로 정상 연결.
```

### Python 백엔드 레포 (도메인 감지: 서버/백엔드)

```
FAISS 원본에서 이미 백엔드 공고가 상위 → 리랭킹 해도 순서 변동 없음.
도메인 일치 가산이 기존 1순위에 붙으므로 순서가 더 강화될 뿐.
```

### 도메인 감지 실패 레포 (범용 파일명만 있는 경우)

```
detected_domains = []
→ rerank_by_domain()이 원본 그대로 반환.
→ 기존 FAISS 순서 유지. 퇴행 없음.
```

---

## 7. DOMAIN_BOOST 값 설정 근거

### 왜 0.05인가

v5.2 수정 테스트에서 게임 공고(0.6834)와 프론트엔드(0.6872)의 차이가 0.0038이었음.
0.05는 이 차이의 약 13배로, 도메인이 일치하면 확실히 추월하지만 FAISS 유사도가 현저히 낮은 공고까지 끌어올리지는 않는 수준.

예: FAISS 유사도 0.50인 게임 공고가 있어도 0.55로 올라가는데, 프론트엔드 0.68을 추월하지는 못함.

### 조정 가능성

| DOMAIN_BOOST | 효과 | 리스크 |
|---|---|---|
| 0.03 | 보수적. 미세한 차이만 보정 | 0.02 이상 차이 시 여전히 밀림 |
| **0.05** | **균형. 대부분의 근접 케이스 보정** | **낮은 유사도 공고가 무리하게 올라오진 않음** |
| 0.10 | 공격적. 도메인 일치면 거의 무조건 상위 | FAISS 유사도를 사실상 무시하게 됨 |

0.05를 기본값으로 시작하고, 다양한 레포로 테스트 후 필요시 조정.

---

## 8. 정리: v5.3 전체 변경 사항

| 항목 | v5.2 | v5.3 |
|---|---|---|
| 프로필 텍스트 | 키워드 + 맥락 문장 + LOC 규모 (~180자) | **키워드만 (v5.1 복원, ~60자)** |
| DOMAIN_CONTEXT | 사용 | **매칭용 프로필에서 제거** |
| LOC 규모 문장 | 사용 | **매칭용 프로필에서 제거** |
| README 원문 폴백 | 300자 폴백 있음 | **폴백 제거** |
| FAISS 후처리 | 없음 | **도메인 리랭킹 추가** |
| 리포트 출력 | FAISS 유사도만 표시 | **FAISS + 도메인 보정 투명 표시** |

---

## 9. 구현 우선순위

| 순위 | 작업 | 난이도 | 예상 공수 |
|---|---|---|---|
| 1 | `rerank_by_domain()` 함수 구현 | 낮음 | 30분 |
| 2 | `run_git2value.py`에 리랭킹 적용 + 출력 변경 | 낮음 | 1시간 |
| 3 | `build_profile_text()`에서 DOMAIN_CONTEXT·LOC 문장·원문 폴백 제거 | 낮음 | 30분 |
| 4 | HandOff.md에 외부 API 0 원칙 명시 | 매우 낮음 | 10분 |
| 5 | HandOff.md에 README 분기 로직 문서화 | 매우 낮음 | 10분 |
| 6 | TCG 레포로 테스트 | — | 30분 |
| 7 | 다른 도메인 레포(백엔드, 프론트엔드)로 퇴행 테스트 | — | 30분 |

**권장 순서:** 3 → 1 → 2 → 4 → 5 → 6 → 7

---

## 10. 리스크

| 리스크 | 가능성 | 대응 |
|---|---|---|
| DOMAIN_BOOST가 너무 커서 낮은 유사도 공고가 상위로 | 낮음 | 0.05면 FAISS 0.50 공고가 0.68을 추월 불가 |
| 도메인 감지 오탐 시 잘못된 리랭킹 | 낮음 | 도메인 감지 임계값이 히트 2개 이상. 오탐률 낮음 |
| 프로필 텍스트가 짧아서(60자) 유사도 절대값 낮음 | 수용 | 유사도 레이블로 보완. 매칭 순서가 정확하면 절대값은 부차적 |
| 도메인 감지 안 되는 레포에서는 효과 없음 | 해당 없음 | 리랭킹 미적용, 기존 FAISS 순서 유지. 퇴행 없음 |

---

## 11. 병행 수정: 기존 취약점 3건

리랭킹과 함께 v5.3에서 병행 처리할 항목.

### 11-1. README 원문 300자 폴백 제거

**현재 문제:**

`build_profile_text()`에서 README 키워드 추출 실패 시 원문 300자를 폴백으로 붙이고 있음.

```python
# 현재 (v5.2)
if readme_summary and len(readme_summary) >= 200:
    readme_keywords = extract_readme_keywords(readme_summary)
    if readme_keywords:
        parts.append(readme_keywords)
    else:
        parts.append(readme_summary[:300])  # ← 이게 노이즈 재유입 경로
```

이 폴백이 발동하면 v5.1 이전과 동일한 노이즈 문제가 재발함.
"이벤트", "UI", "구독" 같은 범용 키워드가 프로필에 유입되어 오매칭 유발.

**수정:**

```python
# v5.3
if readme_summary and len(readme_summary) >= 200:
    readme_keywords = extract_readme_keywords(readme_summary)
    if readme_keywords:
        parts.append(readme_keywords)
    # else: 아무것도 추가하지 않음.
    # 키워드 사전에 없는 도메인이면 프로필에 README를 넣지 않는 게 안전.
    # 도메인/언어/프레임워크/CI/테스트 정보만으로 매칭.
```

**영향:** 키워드 사전(`README_KEYWORDS`)에 없는 도메인의 레포에서 프로필이 약간 짧아질 수 있지만, 노이즈 유입보다 나음. 필요시 `README_KEYWORDS`에 도메인을 추가하여 커버리지 확대.

---

### 11-2. 외부 API 0 원칙 HandOff 명시

**현재 문제:**

프로젝트 핵심 설계 원칙인 "외부 LLM API 의존 없이 전체 파이프라인 로컬 동작"이 HandOff 문서 어디에도 명시되지 않음.
의존성 주의사항에 GitHub API 토큰만 언급되어 있어, 새 개발자가 이어받을 때 이 원칙을 인지하지 못할 수 있음.

**수정:**

HandOff.md 1절(프로젝트 개요) 끝에 다음을 추가:

```markdown
### 설계 원칙: 외부 API 의존 0

Git2Value는 GitHub API(데이터 수집)를 제외하면 외부 서비스 호출이 없습니다.
ChatGPT, Claude 등 외부 LLM API를 사용하지 않으며, 전체 분석·매칭·진단 파이프라인이
로컬에서 동작합니다.

이 원칙의 이유:
- 비용 0 (API 과금 없음)
- 네트워크 장애 시에도 정상 동작 (데모 안정성)
- 캡스톤 종합설계 취지에 부합 (자체 엔진 구축)

프로필 변환이 부족할 경우의 단계적 전환 경로:
1순위: 룰베이스 템플릿 (현재 build_profile_text)
2순위: 로컬 오픈소스 모델 (Qwen2-7B, RTX 4090에서 구동 가능)
3순위: 외부 API (최후 수단, 여기까지 올 가능성 낮음)
```

HandOff.md 8절(의존성 주의사항)에도 한 줄 추가:

```markdown
- **외부 LLM API 의존 없음** — 전체 파이프라인 로컬 동작 (설계 원칙)
```

---

### 11-3. README 분기 로직 HandOff 문서화

**현재 문제:**

`readme_length_tier()`와 `build_profile_text()`의 README 잔량 기반 분기가 코드에는 있지만 HandOff에 설명되지 않음.
새 개발자가 "README를 언제, 어떻게 프로필에 포함하는가"를 코드를 읽지 않으면 알 수 없음.

**수정:**

HandOff.md 3절(`profile_builder.py` 설명) 또는 별도 항목으로 다음을 추가:

```markdown
### README 활용 분기 로직

_clean_markdown() 정제 후 텍스트 길이로 분기:

| 잔량 | 티어 | 프로필 반영 방식 |
|---|---|---|
| 200자 이상 | long | extract_readme_keywords()로 도메인 키워드 압축 후 프로필에 추가 |
| 50~199자 | medium | 프로필에 추가하지 않음. 도메인/언어/프레임워크 데이터만 사용 |
| 49자 이하 | short | 프로필에 추가하지 않음. 의존성 파일 + 도메인 감지에 의존 |

원칙: README가 부실하면 프로필에 넣지 않는다. 없는 정보를 만들어내지 않는다.
키워드 추출 실패 시에도 원문을 폴백으로 넣지 않는다 (v5.3에서 폴백 제거).
```

---

### 11절 구현 요약

| 항목 | 수정 위치 | 공수 |
|---|---|---|
| README 원문 폴백 제거 | `profile_builder.py` `build_profile_text()` | 5분 |
| 외부 API 0 원칙 명시 | `HandOff.md` 1절 + 8절 | 10분 |
| README 분기 로직 문서화 | `HandOff.md` 3절 | 10분 |

세 항목 모두 코드 변경은 최소(폴백 else 삭제 1건)이고 나머지는 문서 보강.

---

*Git2Value — 도메인 기반 하이브리드 리랭킹 계획 v5.3 — 2026.04.09*
