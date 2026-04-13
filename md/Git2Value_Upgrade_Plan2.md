# Git2Value — 다음 업그레이드 계획
**Phase 3.1 설계 문서**
> 작성일: 2026.04.01 | 전제: 외부 API 사용 부분 허용 (목적 한정)
> v3.0 → v3.1 변경: Gemini 크로스 리뷰 반영 — LLM 코드 리뷰 조건부 실행 추가, resume 텍스트 영향 범위 설계 의도 명확화

---

## 1. 이 계획의 전제

### 외부 API 사용 원칙
API는 **두 곳에만** 사용한다.

1. **코드 품질 평가** — "이 사람이 어떤 수준의 문제를 풀었는가" (지원자 상위 20%에만 조건부 실행)
2. **resume 기술 깊이 평가** — applicant_resume 텍스트의 기술적 깊이 정량화 (전체 실행)

정적으로 계산 가능한 지표(LOC, 파일 구조 등)에는 API를 쓰지 않는다.

> **resume 텍스트 API 평가에 대한 주의사항**
> applicant_resume는 README 마크다운을 정제한 최대 1500자 텍스트다.
> 대부분 프로젝트 설명, 기술 스택, 실행 방법이 담겨 있어 정보 밀도가 낮을 수 있다.
> 이 때문에 resume LLM 평가의 연봉 영향 범위를 **±3%로 의도적으로 제한**한다.
> README를 잘 쓰는 사람이 코딩을 잘 한다는 보장이 없으므로, 보조 신호로만 활용한다.

### 업그레이드 방향
현재 시스템의 가장 큰 공백은 두 가지다.

1. **applicant_resume 텍스트가 연봉 계산에 전혀 반영 안 됨** — 지금은 직무 매칭에만 쓰이고 버려진다
2. **코드가 얼마나 있는지만 알고, 코드가 어떤 수준인지는 모름** — LOC만 보고 품질은 모른다

이 두 가지를 해결하는 것이 이번 업그레이드의 전부다.

---

## 2. 추가할 기능 목록

### Feature 1. 파일당 평균 LOC 지표 (즉시 구현 가능)
**목적:** 코드 파편화 또는 모놀리식 구조를 간접적으로 감지

현재 `tree_data`에서 파일 목록을 이미 갖고 있고, LOC도 이미 계산하고 있다.
추가 API 호출 없이 함수 하나로 구현 가능하다.

**판단 기준:**
```
avg_loc_per_file = valid_loc / source_file_count

- avg_loc < 20       → 파편화 의심 (지나치게 잘게 쪼개진 파일들)
- 20 ≤ avg_loc ≤ 300 → 정상 범위
- avg_loc > 300      → 모놀리식 의심 (파일 하나에 로직이 집중)
```

**점수 반영 방식:**
`contribution_axis`에 보정 계수로 적용 (최대 ±5점 수준으로 제한).
코드 스타일 차이(언어마다 관습이 다름)를 감안해 패널티보다 정보 제공 위주로 설계한다.

**추가 출력 필드:**
```json
"code_structure": {
  "avg_loc_per_file": 87,
  "source_file_count": 34,
  "structure_signal": "정상"   // "파편화 의심" | "정상" | "모놀리식 의심"
}
```

---

### Feature 2. LLM 코드 품질 평가 레이어 (핵심 추가 기능)
**목적:** "이 사람이 어떤 수준의 문제를 풀었는가"를 정성적으로 평가

#### 2-0. 조건부 실행 ★ v3.0 대비 추가

모든 지원자에게 LLM 코드 리뷰를 돌리지 않는다.
**github_score 기준 상위 20% (80점 이상)인 경우에만** 실행한다.

```python
SENIOR_THRESHOLD = 80.0  # 이 점수 이상일 때만 LLM 코드 리뷰 실행

if github_score >= SENIOR_THRESHOLD:
    code_quality_result = await run_llm_code_review(snippet)
else:
    code_quality_result = None  # code_quality_factor = 1.0 (중립) 처리
```

**이유:**
- 하위권 지원자의 코드를 심층 리뷰하는 건 비용 대비 정보 가치가 낮다
- 연봉 산출의 차별화 효과가 가장 큰 구간(시니어 경계)에 API를 집중한다
- 트래픽이 늘어도 비용이 선형으로 증가하지 않고 상위 20%에만 한정된다

#### 2-1. 무엇을 LLM에게 보내는가 (스니펫 선택 전략)

가장 어려운 부분이다. "응집도 높은 파일"은 정적 계산이 어려우므로
아래 기준으로 파일을 선택한다.

**선택 기준 (우선순위 순):**
```
1. 해당 지원자가 직접 수정한 커밋이 가장 많은 파일 (author 커밋 집계)
2. 소스 파일 중 LOC 기준 상위 20% (단, test 파일 제외)
3. 파일명/경로에 'main', 'core', 'engine', 'service', 'manager' 포함 파일 우선
```

위 기준으로 최대 **3개 파일, 합산 최대 500줄**만 추출한다.
500줄 초과 시 각 파일의 앞부분 위주로 트리밍한다.

선택된 파일 목록은 output에 포함시켜 사용자가 확인 가능하게 한다.

#### 2-2. LLM에게 무엇을 물어보는가

LLM 리뷰의 목적은 **연봉 보정 계수**를 만드는 것이다.
"좋다/나쁘다" 판단이 아니라, 구체적인 수치를 뽑아야 한다.

**System Prompt 설계:**
```
당신은 시니어 개발자입니다. 아래 코드를 보고 JSON만 반환하세요.
다른 텍스트, 마크다운 코드블록, 설명은 절대 포함하지 마세요.

평가 항목:
- design_score (0~10): 함수/클래스 분리, 책임 단일화, 확장성
- readability_score (0~10): 변수명, 주석, 코드 흐름의 명확성
- problem_complexity (0~10): 이 코드가 해결하는 문제의 난이도
- one_line_summary: 이 코드의 핵심을 한 문장으로 (한국어)

반환 형식:
{"design_score": 7, "readability_score": 8, "problem_complexity": 6, "one_line_summary": "..."}
```

**사용 모델:** `claude-sonnet-4-20250514` (Anthropic API)

#### 2-3. LLM 점수를 연봉에 반영하는 방법

LLM 점수를 직접 연봉 계산식에 넣지 않는다.
`valuation_engine.py`의 multiplier 계산에 **보정 계수**로 반영한다.

```python
# 비정상 응답 처리: 파싱 실패 또는 점수 범위 이탈 시 중립값 반환
def parse_llm_review(raw: str) -> dict:
    try:
        result = json.loads(raw)
        assert all(0 <= result[k] <= 10 for k in ["design_score", "readability_score", "problem_complexity"])
        return result
    except Exception:
        return {"design_score": 5, "readability_score": 5, "problem_complexity": 5,
                "one_line_summary": "(평가 불가)"}  # → code_quality_factor = 1.0 (중립)

# multiplier 보정
code_quality_avg = (design_score + readability_score + problem_complexity) / 3  # 0~10
code_quality_factor = 0.95 + (code_quality_avg / 10.0) * 0.10  # 범위: 0.95 ~ 1.05

multiplier = (0.80 + (github_score / 100.0) * 0.45) * code_quality_factor
```

**설계 의도:**
- LLM 점수가 연봉에 미치는 영향을 **±5% 이내로 제한**한다
- 환각이나 주관적 편향이 과도하게 반영되지 않도록 안전장치를 둔다
- github_score(정량)가 메인 신호이고, LLM 리뷰(정성)는 보정 역할이다

#### 2-4. 비용 예측

파일 3개, 최대 500줄 기준:
- 입력 토큰: 약 2,000~4,000 tokens
- 출력 토큰: 약 100 tokens
- Claude Sonnet 기준: 지원자 1인당 약 **$0.01~0.02** 수준
- **조건부 실행(상위 20%만)으로 실제 평균 비용: 전체의 20% 수준**

대규모 트래픽 시 지원자당 1회만 호출하고 결과를 캐싱한다.

---

### Feature 2-B. resume 기술 깊이 LLM 평가 ★ v3.0 대비 추가
**목적:** applicant_resume 텍스트를 LLM으로 정량화하여 연봉에 반영

휴리스틱(F3)으로 먼저 처리하되, 휴리스틱의 한계(오탐, 문맥 오해)를 LLM으로 보완한다.
**모든 지원자에게 실행** (코드 리뷰와 달리 텍스트만 전송하므로 비용이 매우 낮음).

```
System Prompt:
아래는 개발자의 GitHub 프로젝트 설명입니다. JSON만 반환하세요.
다른 텍스트, 마크다운 코드블록, 설명은 절대 포함하지 마세요.

- tech_depth_score (0~10): 기술 스택의 깊이와 난이도
- architecture_score (0~10): 시스템 설계 이해도 (MSA, 이벤트 기반 등)
- achievement_score (0~10): 구체적 성과 서술 여부 (수치, 최적화 결과 등)

반환 형식: {"tech_depth_score": 6, "architecture_score": 4, "achievement_score": 7}
```

**연봉 반영:**
```python
resume_avg = (tech_depth_score + architecture_score + achievement_score) / 3  # 0~10
resume_factor = 0.97 + (resume_avg / 10.0) * 0.06  # 범위: 0.97 ~ 1.03

multiplier = multiplier * resume_factor
```

> **영향 범위를 ±3%로 제한하는 이유:**
> applicant_resume는 README 정제 텍스트 최대 1500자로, 정보 밀도가 낮다.
> LLM이 이 텍스트만 보고 시니어/주니어를 정확히 구분하는 데는 한계가 있다.
> 코드를 직접 보는 F2(±5%)보다 신뢰도가 낮으므로 영향 범위를 더 좁게 설정한다.

---

### Feature 3. resume_depth_score (휴리스틱 — F2-B의 폴백)
**목적:** API 호출 실패 시 또는 텍스트가 너무 짧을 때의 폴백 처리

F2-B LLM 평가가 정상 작동하면 이 함수는 호출하지 않는다.
API 오류, 타임아웃, 텍스트 100자 미만 등 예외 상황에서만 사용한다.

```python
def score_resume_depth_heuristic(resume_text: str) -> float:
    """폴백용 휴리스틱. F2-B 실패 시에만 호출."""
    score = 0.0

    # 수치 포함 문장 (성과 구체화의 지표)
    if re.search(r'\d+[%배x배]|\d+ms|\d+초', resume_text):
        score += 0.3

    # 고급 기술 키워드
    advanced_keywords = [
        'msa', '마이크로서비스', 'event-driven', '이벤트 기반', 'cqrs', 'ddd',
        '최적화', 'optimization', '병목', 'bottleneck', '지연시간', 'latency',
        '분산', 'distributed', '동시성', 'concurrency', '트랜잭션',
        '파인튜닝', 'fine-tuning', 'qlora', '추론', 'inference', '양자화', 'quantization',
    ]
    hit_count = sum(1 for kw in advanced_keywords if kw in resume_text.lower())
    score += min(0.4, hit_count * 0.08)

    # 트러블슈팅 서술 패턴
    if re.search(r'(해결|문제|이슈|개선|리팩토링|원인|분석)', resume_text):
        score += 0.2

    # 텍스트 분량
    if len(resume_text) > 300:
        score += 0.1

    return min(1.0, score)
```

---

## 3. 전체 업그레이드 후 파이프라인

```
GitHub Extractor
    ↓
    ├── (기존) LOC, 커밋 수, CI/CD, 테스트 비율, 일관성
    └── (신규 F1) 파일당 평균 LOC → code_structure 신호
    ↓
github_score + score_breakdown + code_structure
    ↓
    ├── (신규 F2-B) resume LLM 평가 → resume_factor (±3%) [전체 실행]
    │       └── 실패 시 F3 휴리스틱으로 폴백
    ↓
FAISS 벡터 매칭 → 직무 카테고리
    ↓
    ├── (기존) github_score 기반 multiplier
    ├── (신규 F2) LLM 코드 리뷰 → code_quality_factor (±5%) [상위 20%만]
    └── resume_factor 적용
    ↓
최종 적정 연봉 산출
```

---

## 4. 구현 우선순위 및 일정

| 순위 | 기능 | 난이도 | 예상 공수 | 비고 |
|---|---|---|---|---|
| 1 | 파일당 평균 LOC (F1) | 낮음 | 1~2시간 | tree_data 재활용, API 불필요 |
| 2 | resume LLM 평가 (F2-B) | 낮음 | 2~3시간 | API 연동, 폴백 로직 포함 |
| 3 | valuation_engine.py resume_factor 반영 | 낮음 | 1시간 | F2-B 결과 연결 |
| 4 | 스니펫 선택 알고리즘 | 중간 | 반나절 | F2의 전제 조건 |
| 5 | LLM 코드 리뷰 레이어 (F2) | 중간 | 반나절~1일 | 조건부 실행 포함 |
| 6 | valuation_engine.py code_quality_factor 반영 | 낮음 | 1시간 | F2 결과 연결 |

**권장 순서:** 1 → 2 → 3 (LLM 없는 구조 먼저 완성 후 resume API 붙이기) → 4 → 5 → 6

---

## 5. 리스크 및 보완책

| 리스크 | 가능성 | 보완책 |
|---|---|---|
| LLM 환각으로 잘못된 코드 평가 | 중간 | 영향 범위를 ±5%로 제한. 비정상 응답 시 code_quality_factor = 1.0 (중립) 처리 |
| resume LLM이 README 정보 부족으로 오평가 | 중간 | 영향 범위를 ±3%로 제한. 텍스트 100자 미만이면 F3 휴리스틱 폴백 |
| 스니펫 선택 알고리즘이 대표성 없는 파일 선택 | 중간 | 선택된 파일 목록을 output에 포함시켜 사용자가 확인 가능하게 함 |
| 언어별 avg_loc 관습 차이 | 낮음 | structure_signal은 정보 제공만, 점수 패널티는 최소화 |
| 상위 20% 기준(80점)의 적절성 | 낮음 | 지원자 데이터 누적 후 실제 분포 보고 임계값 조정 예정 |

---

## 6. 전체 보정 계수 구조 (최종 multiplier)

```python
# valuation_engine.py 최종 multiplier 구조
base_multiplier    = 0.80 + (github_score / 100.0) * 0.45   # 메인 신호 (범위: 0.80~1.25)
code_quality_factor = 0.95 ~ 1.05                            # F2: 코드 리뷰 (상위 20%만, ±5%)
resume_factor       = 0.97 ~ 1.03                            # F2-B: resume 깊이 (전체, ±3%)

final_multiplier = base_multiplier * code_quality_factor * resume_factor
# 최대 영향 범위: base ±8% (두 보정 계수 최대 조합 시)
```

신호 간 영향력 비율: **github_score 85% : 코드 품질 10% : resume 깊이 5%**

---

## 7. 이번 업그레이드 후 시스템이 알 수 있는 것

| 항목 | 업그레이드 전 | 업그레이드 후 |
|---|---|---|
| 얼마나 많은 코드를 썼는가 | ✅ | ✅ |
| 얼마나 꾸준히 썼는가 | ✅ | ✅ |
| 코드가 어떤 구조로 구성됐는가 | ❌ | ✅ (F1) |
| README가 기술 깊이를 담고 있는가 | ❌ | ✅ (F2-B) |
| 코드의 설계 품질은 어떤가 | ❌ | ✅ (F2, 상위 20%만, 간접적) |
| 어떤 난이도의 문제를 풀었는가 | ❌ | ✅ (F2, problem_complexity) |
| 코드 전체가 얼마나 좋은가 | ❌ | ❌ (여전히 한계. 샘플 기반이므로) |

마지막 항목은 이번에도 해결 안 된다.
전체 코드를 다 읽지 않는 한 불가능한 문제이고, 그건 이 시스템의 설계 범위 밖이다.
**샘플 기반 간접 평가라는 한계를 인지하고 쓰는 것이 이 시스템의 올바른 사용법이다.**

---

*Git2Value Upgrade Plan — Phase 3.1 — 2026.04.01*
