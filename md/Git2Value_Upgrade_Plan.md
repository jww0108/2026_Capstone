# Git2Value — 다음 업그레이드 계획
**Phase 3.0 설계 문서**
> 작성일: 2026.04.01 | 전제: 외부 API 사용 부분 허용 (목적 한정)

---

## 1. 이 계획의 전제

### 외부 API 사용 원칙
API는 **"이 사람이 어떤 수준의 문제를 풀었는가"를 판단하는 단 한 곳에만** 집중 사용한다.
정적으로 계산 가능한 지표(LOC, 파일 구조, 복잡도 등)에는 API를 쓰지 않는다.

이유: API 비용은 호출 수에 비례하므로, 로컬 연산으로 해결 가능한 지표에 쓰는 건 낭비다.
그리고 정량 지표를 API로 대체하면 비용만 늘고 신뢰도 개선은 없다.

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

- avg_loc < 20      → 파편화 의심 (지나치게 잘게 쪼개진 파일들)
- 20 ≤ avg_loc ≤ 300 → 정상 범위
- avg_loc > 300     → 모놀리식 의심 (파일 하나에 로직이 집중)
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

#### 2-1. 무엇을 LLM에게 보내는가 (스니펫 선택 전략)

가장 어려운 부분이다. Gemini가 "응집도 높은 파일 3개"라고 했는데, 응집도는 정적 계산이 어렵다.
대신 아래 기준으로 파일을 선택한다.

**선택 기준 (우선순위 순):**
```
1. 해당 지원자가 직접 수정한 커밋이 가장 많은 파일 (author 커밋 집계)
2. 소스 파일 중 LOC 기준 상위 20% (단, test 파일 제외)
3. 파일명/경로에 'main', 'core', 'engine', 'service', 'manager' 포함 파일 우선
```

위 기준으로 최대 **3개 파일, 합산 최대 500줄**만 추출한다.
500줄 초과 시 각 파일의 앞부분 위주로 트리밍한다.

**이유:** LLM에 코드 전체를 넣는 건 비용 낭비이고 효과도 낮다.
"이 사람이 가장 공들인 파일"을 정확히 고르는 것이 리뷰 품질을 결정한다.

#### 2-2. LLM에게 무엇을 물어보는가

LLM 리뷰의 목적은 **연봉 보정 계수** 를 만드는 것이다.
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
외부 API 사용을 허용한 만큼, 코드 이해 품질이 가장 높은 모델을 사용한다.

#### 2-3. LLM 점수를 연봉에 반영하는 방법

LLM 점수를 직접 연봉 계산식에 넣지 않는다.
대신 `valuation_engine.py`의 multiplier 계산에 **보정 계수**로 반영한다.

```python
# 현재
multiplier = 0.80 + (github_score / 100.0) * 0.45

# 업그레이드 후
code_quality_avg = (design_score + readability_score + problem_complexity) / 3  # 0~10
code_quality_factor = 0.95 + (code_quality_avg / 10.0) * 0.10  # 범위: 0.95 ~ 1.05

multiplier = (0.80 + (github_score / 100.0) * 0.45) * code_quality_factor
```

**설계 의도:**
- LLM 점수가 연봉에 미치는 영향을 ±5% 이내로 제한한다
- LLM 환각이나 주관적 편향이 최종 결과에 과도하게 반영되지 않도록 안전장치를 둔다
- github_score(정량)가 여전히 메인 신호이고, LLM 리뷰(정성)는 보정 역할이다

#### 2-4. 비용 예측

파일 3개, 최대 500줄 기준:
- 입력 토큰: 약 2,000~4,000 tokens
- 출력 토큰: 약 100 tokens
- Claude Sonnet 기준: 지원자 1인당 약 **$0.01~0.02** 수준

대규모 트래픽 시 비용 통제가 필요하면 지원자당 1회만 호출하고 결과를 캐싱한다.

---

### Feature 3. resume_depth_score (무료 구현, 즉시 적용 가능)
**목적:** applicant_resume 텍스트를 연봉 계산에 반영하는 가장 빠른 방법

LLM 없이 휴리스틱으로 구현한다.

```python
def score_resume_depth(resume_text: str) -> float:
    """
    README에서 추출된 텍스트의 기술적 깊이를 0~1 사이 값으로 반환.
    """
    score = 0.0
    
    # 1. 수치 포함 문장 (성과 구체화의 지표)
    #    예: "응답 시간 50% 단축", "처리량 3배 향상"
    if re.search(r'\d+[%배x배]|\d+ms|\d+초', resume_text):
        score += 0.3
    
    # 2. 고급 기술 키워드 (레이어별 가중치)
    advanced_keywords = [
        # 아키텍처/설계
        'msa', '마이크로서비스', 'event-driven', '이벤트 기반', 'cqrs', 'ddd',
        # 성능/최적화
        '최적화', 'optimization', '병목', 'bottleneck', '지연시간', 'latency',
        # 분산 시스템
        '분산', 'distributed', '동시성', 'concurrency', '트랜잭션',
        # AI/ML 심화
        '파인튜닝', 'fine-tuning', 'qlora', '추론', 'inference', '양자화', 'quantization',
    ]
    hit_count = sum(1 for kw in advanced_keywords if kw in resume_text.lower())
    score += min(0.4, hit_count * 0.08)
    
    # 3. 트러블슈팅 서술 패턴
    if re.search(r'(해결|문제|이슈|개선|리팩토링|원인|분석)', resume_text):
        score += 0.2
    
    # 4. 텍스트 분량 (최소한의 내용이 있어야 함)
    if len(resume_text) > 300:
        score += 0.1
    
    return min(1.0, score)
```

**연봉 반영:**
```python
# valuation_engine.py 보정
resume_factor = 0.97 + score_resume_depth(applicant_resume) * 0.06  # 범위: 0.97 ~ 1.03
multiplier = multiplier * resume_factor
```

---

## 3. 전체 업그레이드 후 파이프라인

```
GitHub Extractor
    ↓
    ├── (기존) LOC, 커밋 수, CI/CD, 테스트 비율, 일관성
    ├── (신규 F1) 파일당 평균 LOC → code_structure 신호
    └── (신규 F3) resume_depth_score (휴리스틱)
    ↓
github_score + score_breakdown + code_structure
    ↓
FAISS 벡터 매칭 → 직무 카테고리
    ↓
    ├── (기존) github_score 기반 multiplier
    ├── (신규 F2) LLM 코드 리뷰 → code_quality_factor (±5%)
    └── (신규 F3) resume_depth_score → resume_factor (±3%)
    ↓
최종 적정 연봉 산출
```

---

## 4. 구현 우선순위 및 일정

| 순위 | 기능 | 난이도 | 예상 공수 | 비고 |
|---|---|---|---|---|
| 1 | resume_depth_score (F3) | 낮음 | 1~2시간 | API 불필요, 즉시 구현 |
| 2 | 파일당 평균 LOC (F1) | 낮음 | 1~2시간 | tree_data 재활용 |
| 3 | 스니펫 선택 알고리즘 | 중간 | 반나절 | F2의 전제 조건 |
| 4 | LLM 코드 리뷰 레이어 (F2) | 중간 | 반나절~1일 | Anthropic API 연동 |
| 5 | valuation_engine.py 보정 | 낮음 | 1시간 | F2, F3 결과 반영 |

**권장 순서:** 1 → 2 → 5 (LLM 없이 먼저 완성) → 3 → 4 → 5 재조정

---

## 5. 리스크 및 보완책

| 리스크 | 가능성 | 보완책 |
|---|---|---|
| LLM 환각으로 잘못된 코드 평가 | 중간 | 영향 범위를 ±5%로 제한. 비정상 응답 시 code_quality_factor = 1.0 (중립) 처리 |
| 스니펫 선택 알고리즘이 대표성 없는 파일 선택 | 중간 | 선택된 파일 목록을 output에 포함시켜 사용자가 확인 가능하게 함 |
| 언어별 avg_loc 관습 차이 | 낮음 | structure_signal은 정보 제공만, 점수 패널티는 최소화 |
| resume_depth 키워드가 복붙된 글에서 오탐 | 낮음 | LLM 리뷰(F2)가 실제 코드를 보기 때문에 최종 단계에서 상쇄됨 |

---

## 6. 이번 업그레이드 후 시스템이 알 수 있는 것

| 항목 | 업그레이드 전 | 업그레이드 후 |
|---|---|---|
| 얼마나 많은 코드를 썼는가 | ✅ | ✅ |
| 얼마나 꾸준히 썼는가 | ✅ | ✅ |
| 코드가 어떤 구조로 구성됐는가 | ❌ | ✅ (F1) |
| README가 기술 깊이를 담고 있는가 | ❌ | ✅ (F3) |
| 코드의 설계 품질은 어떤가 | ❌ | ✅ (F2, 간접적) |
| 어떤 난이도의 문제를 풀었는가 | ❌ | ✅ (F2, problem_complexity) |
| 코드 전체가 얼마나 좋은가 | ❌ | ❌ (여전히 한계. 샘플 기반이므로) |

마지막 항목은 이번에도 해결 안 된다.
전체 코드를 다 읽지 않는 한 불가능한 문제이고, 그건 이 시스템의 설계 범위 밖이다.
**샘플 기반 간접 평가라는 한계를 인지하고 쓰는 것이 이 시스템의 올바른 사용법이다.**

---

*Git2Value Upgrade Plan — Phase 3.0 — 2026.04.01*
