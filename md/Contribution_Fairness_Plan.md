# Git2Value — 기여도 편향 해소 및 진단 기준 재조정 계획

> 작성일: 2026.04.15 | 대상 버전: v5.4 → v5.5
> 발견 계기: 실사용자 2차 피드백 — 협업 프로젝트 기여도 편향, 개인 프로젝트 커밋 부족, 테스트 현실성, 추가 스택 커버리지

---

## 1. 문제 정의

### 1-1. 협업 프로젝트의 기여도 편향

**사용자 피드백:** "부트캠프나 팀 프로젝트처럼 처음부터 협업으로 진행된 레포의 경우, 역할 분담 때문에 개인별 기여도 점수가 낮게 나온다. 특히 풀스택 레포일수록 역할별 차이가 두드러진다."

**재구성:**
현재 contribution 점수는 `valid_loc`(70%) + `analyzed_count`(30%)로 계산. 문제는 `valid_loc`이 "기여의 대리지표"로 부적절한 경우가 많다는 것.

| 역할 | LOC 반영 | 결과 |
|---|---|---|
| 프론트엔드 담당 | 컴포넌트 파일 다수 → LOC 큼 | 점수 높음 |
| 백엔드 담당 | 로직 집약 → LOC 중간 | 점수 중간 |
| 데이터셋/문서 담당 | json/md/txt → ignore_extensions로 제외 | 점수 거의 0 |
| DevOps/설정 담당 | yml/dockerfile → 제외 | 점수 거의 0 |

**특히 심각한 케이스:** 데이터셋 전담자, 설정/인프라 전담자 → 실제로는 중요한 기여를 했음에도 점수가 0에 수렴.

### 1-2. 개인 프로젝트의 커밋 부족

**사용자 피드백:** "커밋 횟수가 적은 개인 프로젝트에서 기여도 오류가 발생한다. 완성하고 한두 번에 푸시한 경우 점수가 낮게 나온다."

**재구성:**
`commit_score = min(100, log(analyzed_count / 5 + 1) / log(21) * 100)`에서 커밋이 5개 미만이면 점수가 급격히 떨어짐. LOC는 많은데 커밋이 3~5개면 contribution이 불합리하게 낮음.

### 1-3. 테스트 항목의 비현실성

**사용자 피드백:** "신입 레포에서 테스트 코드를 넣는 경우가 거의 없다. 반영해야 할지 논의 필요."

**재구성:**
- 현재 `has_tests`가 Competitive 등급의 필수 조건 중 하나 (`readme_ok and (has_tests or has_cicd)`)
- 실제로는 신입 포트폴리오의 90% 이상이 테스트 없음
- 결과적으로 Competitive 도달이 과도하게 어려움
- 대기업 통과 포트폴리오조차 Entry로 분류되는 원인 중 하나

전체 사용자의 대다수가 같은 피드백을 받는 항목은 변별력이 없음.

### 1-4. 게임 이외 추가 파악 기술 스택

**사용자 피드백:** "게임 분야 이외에 특별히 파악해야 할 기술 스택이 있을지?"

**현재 커버 중:**
- 엔진(v5.4): Unity, Unreal, Godot, Flutter
- 의존성 파싱: React, Next.js, Vue, Django, FastAPI, Spring Boot, Rails, Gin, Echo, Actix

**미커버 빈틈:**
- Jupyter/ML 실험 성격 프로젝트 (AI 연구직 매칭에 유용)
- Kubernetes/IaC 인프라 프로젝트 (DevOps 직무 매칭에 유용)

---

## 2. 해결 방향 요약

| 문제 | 해결 방향 | 심각도 |
|---|---|---|
| 1-1. 협업 기여도 편향 | ① 커밋 가중치 상향 ② Evidence LOC 보조 점수 ③ 기여 유형 안내 | 높음 |
| 1-2. 개인 프로젝트 커밋 부족 | 커밋 수 기반 동적 가중치 | 높음 |
| 1-3. 테스트 비현실성 | Competitive 조건에서 제외, Top 전용으로 유지 | 높음 |
| 1-4. 추가 기술 스택 | Jupyter/ML, Kubernetes/IaC 시그니처 추가 | 중간 |

---

## 3. 수정 1: Contribution 가중치 재조정

### 3-1. 커밋 수에 따른 동적 가중치

```python
# 현재 (고정 7:3)
blend_100 = loc_score * 0.7 + commit_score * 0.3

# v5.5 (커밋 수에 따라 동적 조정)
if analyzed_count < 5:
    # 커밋이 너무 적음 → LOC 위주로 판단 (개인 프로젝트 일괄 푸시 케이스)
    loc_weight, commit_weight = 0.9, 0.1
elif analyzed_count < 15:
    # 일반적 범위
    loc_weight, commit_weight = 0.6, 0.4
else:
    # 꾸준한 커밋 → 커밋 가중치 상향 (협업 프로젝트에서 LOC 적은 역할도 보상)
    loc_weight, commit_weight = 0.5, 0.5

blend_100 = loc_score * loc_weight + commit_score * commit_weight
```

### 3-2. Evidence LOC 보조 점수

소스 코드로는 인정 안 하지만 "기여 증거"로는 카운트하는 확장자를 추가.

```python
# github_extractor.py
CONTRIBUTION_EVIDENCE_EXTENSIONS = {
    '.json', '.yml', '.yaml', '.md', '.txt', '.csv',
    '.tf', '.hcl',               # Terraform / IaC
    '.dockerfile',                # 확장자 없는 Dockerfile은 파일명으로 별도 처리
    '.proto',                     # gRPC 정의
    '.sql',                       # 마이그레이션/스키마
}

def _is_contribution_evidence(filename: str) -> bool:
    """LOC 계산에서는 제외되지만 기여 증거로는 인정되는 파일."""
    lower_name = filename.lower()
    if any(path in lower_name for path in self.ignore_paths):
        return False
    if lower_name.endswith('dockerfile'):
        return True
    ext = os.path.splitext(lower_name)[1]
    return ext in CONTRIBUTION_EVIDENCE_EXTENSIONS
```

`_analyze_sampled_commits()`에서 `evidence_loc`를 별도로 집계.

```python
evidence_loc = 0
for f in detail.get("files", []) or []:
    filename = f.get("filename", "")
    if self._is_valid_source_code(filename):
        valid_loc += f.get("additions", 0) or 0
    elif self._is_contribution_evidence(filename):
        evidence_loc += f.get("additions", 0) or 0
```

### 3-3. Evidence LOC를 contribution에 반영

```python
# v5.5 contribution 계산
loc_score_main = min(100, math.log(valid_loc / 100 + 1) / math.log(101) * 100)
loc_score_evidence = min(50, math.log(evidence_loc / 500 + 1) / math.log(101) * 50)
# evidence는 50점 만점 (가중치 절반)

loc_score_combined = min(100, loc_score_main + loc_score_evidence)
commit_score = min(100, math.log(analyzed_count / 5 + 1) / math.log(21) * 100)

blend_100 = loc_score_combined * loc_weight + commit_score * commit_weight
contribution_axis = round((blend_100 / 100) * 60, 1)
```

**효과:**
- 순수 코드 기여자: 변화 거의 없음 (loc_score_main이 이미 포화)
- 데이터셋/설정 전담자: evidence_loc로 +20~30점 수준 보정
- 풀스택 내 프론트 전담자: 기존과 유사

### 3-4. 기여 유형 안내 메시지

점수 변경으로도 해결 안 되는 케이스를 위해, 진단 리포트에 **기여 유형 설명**을 추가.

```python
# portfolio_diagnosis.py 또는 별도 출력 블록
def contribution_type_note(valid_loc: int, evidence_loc: int) -> str:
    total = valid_loc + evidence_loc
    if total == 0:
        return ""
    code_ratio = valid_loc / total
    
    if code_ratio >= 0.8:
        return f"기여 유형: 소스 코드 중심 (코드 {valid_loc:,} LOC, 설정/데이터 {evidence_loc:,} LOC)"
    elif code_ratio >= 0.4:
        return f"기여 유형: 코드·설정 병행 (코드 {valid_loc:,} LOC, 설정/데이터 {evidence_loc:,} LOC)"
    else:
        return (
            f"기여 유형: 설정/데이터 중심 "
            f"(코드 {valid_loc:,} LOC, 설정/데이터 {evidence_loc:,} LOC)\n"
            f"  → 이 레포에서는 데이터·인프라·문서 영역에 주로 기여한 것으로 보입니다. "
            f"순수 코딩 LOC 기반 점수가 낮게 나올 수 있으며, 이는 기여 유형의 차이이지 실력의 문제가 아닙니다."
        )
```

모듈 A 또는 지원자 요약 블록에 추가.

---

## 4. 수정 2: 테스트 항목 재배치

### 4-1. 현재 문제

```python
# 현재 expected_level()
if readme_ok and multi_proj and has_tests and has_cicd and has_deploy and s >= 6:
    return "Top"
if readme_ok and (has_tests or has_cicd) and s >= 4:
    return "Competitive"
return "Entry"
```

`has_tests`가 Competitive 조건에 OR로 들어가 있지만, `has_cicd`도 신입 레포에 드물어서 사실상 Competitive 진입 장벽이 높음.

### 4-2. 변경안

**Competitive:** 테스트 조건 제거. CI/CD 또는 배포 중 하나만 있어도 진입 가능.
**Top:** 테스트 유지. 상위권 차별화 요소로 활용.

```python
def expected_level(per_repo, diagnosis):
    s = _count_checks(per_repo, diagnosis)
    readme_ok = diagnosis["readme_quality"]["status"] in ("양호", "보통")
    has_tests = diagnosis["test_coverage"]["status"] == "양호"
    has_cicd = diagnosis["cicd"]["status"] == "양호"
    has_deploy = diagnosis["deployment"]["status"] == "양호"
    multi_proj = len(per_repo) >= 2
    
    # Top: 테스트 + CI/CD + 배포 + 멀티 프로젝트 모두 충족 (차별화 유지)
    if readme_ok and multi_proj and has_tests and has_cicd and has_deploy and s >= 6:
        return {"level": "Top", ...}
    
    # Competitive: 테스트 조건 제거, CI/CD 또는 배포 중 하나만 있어도 진입
    if readme_ok and (has_cicd or has_deploy) and multi_proj and s >= 4:
        return {"level": "Competitive", ...}
    
    return {"level": "Entry", ...}
```

### 4-3. 진단 리포트의 테스트 항목 문구 조정

```python
# portfolio_diagnosis.py _test_diagnosis()
if with_tests == 0:
    return _item(
        "선택 가점",  # "미흡" → "선택 가점"으로 완화
        f"{len(per_repo)}개 레포 중 테스트 파일이 감지되지 않았습니다.",
        "테스트 코드는 Top 등급 차별화 요소입니다. "
        "핵심 비즈니스 로직부터 단위 테스트를 추가해보세요.",
    )
```

사용자가 "테스트 미흡 = 나쁜 포트폴리오"로 받아들이지 않도록 문구 조정. 신입 단계에서 테스트가 없는 게 "결격"이 아니라 "가점 포인트 미획득" 정도로 표현.

### 4-4. 등급 판정 기준 테이블 업데이트

| 레벨 | 현재 조건 (v5.4) | 변경 조건 (v5.5) |
|---|---|---|
| Entry | 기본 | 기본 |
| Competitive | README + (테스트 or CI/CD) + 체크 4+ | README + (CI/CD or 배포) + 멀티 프로젝트 + 체크 4+ |
| Top | README + 테스트 + CI/CD + 배포 + 멀티 프로젝트 + 체크 6+ | 동일 |

핵심 변화: Competitive에서 테스트 제거, 대신 "멀티 프로젝트" 조건 추가로 Entry와의 차별화 유지.

---

## 5. 수정 3: 추가 엔진/프레임워크 시그니처

v5.4의 `ENGINE_SIGNATURES`에 2개 추가.

```python
ENGINE_SIGNATURES = {
    # 기존 (v5.4): Unity, Unreal Engine, Godot, Flutter
    
    # v5.5 추가
    "Jupyter/ML 실험": {
        "required_any": [],
        "supporting_files": [".ipynb"],
        "supporting_dirs": ["notebooks/", "experiments/"],
        "min_supporting": 2,  # .ipynb 2개 이상 또는 (파일 1개 + 디렉토리 1개)
    },
    "Kubernetes/IaC": {
        "required_any": [],
        "supporting_files": [".tf", ".hcl"],
        "supporting_dirs": ["kubernetes/", "k8s/", "helm/", "terraform/"],
        "min_supporting": 2,
    },
}
```

### 5-1. Jupyter/ML 감지의 가치

현재 ML/AI 도메인은 DOMAIN_SIGNALS의 키워드("model", "train" 등)로 감지.
`.ipynb` 다수 존재는 **ML 중에서도 실험/연구 성격**을 구분함.

```
일반 ML 서비스 프로젝트: inference.py, model_server.py → 기존 감지 OK
실험/연구 프로젝트: experiments/eda.ipynb, notebooks/training_v3.ipynb → Jupyter 감지 추가
```

→ "데이터 사이언티스트" vs "머신러닝 엔지니어" 공고 매칭에서 차이 발생 가능.

### 5-2. Kubernetes/IaC 감지의 가치

DevOps/시스템 엔지니어 직무와의 매칭 정확도 향상. 기존에는 `docker-compose`나 `.github/workflows`만 감지해서 인프라 전문성을 특정하기 어려움.

---

## 6. 예상 결과

### 6-1. 협업 부트캠프 프로젝트 (데이터셋 전담자)

```
현재 (v5.4):
  valid_loc: 200 (README, 문서 외에는 거의 없음)
  contribution: 15.3점
  사용자: "나도 기여했는데 점수가 왜 이렇게 낮지?"

v5.5 적용 후:
  valid_loc: 200
  evidence_loc: 5,200 (json 데이터셋, yml 설정, md 문서)
  contribution: 38.5점 (evidence 반영 + 커밋 가중치 조정)
  
  기여 유형 안내:
    "기여 유형: 설정/데이터 중심 (코드 200 LOC, 설정/데이터 5,200 LOC)
     → 이 레포에서는 데이터·인프라·문서 영역에 주로 기여한 것으로 보입니다."
```

### 6-2. 일괄 푸시 개인 프로젝트

```
현재 (v5.4):
  valid_loc: 4,500
  analyzed_count: 3
  loc_score=99.8, commit_score=30.1
  blend = 99.8*0.7 + 30.1*0.3 = 78.8
  contribution: 47.3점

v5.5 적용 후 (커밋 5 미만 → 0.9:0.1):
  blend = 99.8*0.9 + 30.1*0.1 = 92.8
  contribution: 55.7점
  → 일괄 푸시여도 LOC 기반으로 공정 평가
```

### 6-3. 대기업 통과 Unity 포트폴리오

```
현재 (v5.4):
  테스트 미흡, CI/CD 미경험, 배포 미경험 → Entry
  
v5.5 적용 후:
  Unity 감지됨, 커밋 가중치 조정으로 점수 상승
  has_cicd=False, has_deploy=False라면 여전히 Entry
  → 등급 기준 완화만으로는 한계. 도메인별 등급 분기 필요 (별도 계획)
```

**한계 인지:** 게임 포트폴리오의 등급 편향은 v5.5로 완전 해결되지 않음. 테스트 조건 완화는 도움이 되지만, CI/CD/배포가 여전히 웹 관행 기준.

### 6-4. Jupyter 기반 AI 연구 프로젝트

```
v5.4: ML/AI 도메인 감지됨
v5.5: ML/AI + "Jupyter/ML 실험" frameworks 추가
      프로필: "Python (100%) 기반 ML/AI 경험. Jupyter/ML 실험 활용 경험..."
      → 데이터 사이언티스트 공고와의 매칭 강화
```

---

## 7. 구현 우선순위

| 순위 | 작업 | 난이도 | 예상 공수 |
|---|---|---|---|
| 1 | Contribution 커밋 수 기반 동적 가중치 (3-1) | 낮음 | 30분 |
| 2 | Evidence LOC 보조 점수 도입 (3-2, 3-3) | 낮음 | 1시간 |
| 3 | 기여 유형 안내 메시지 (3-4) | 낮음 | 1시간 |
| 4 | 테스트 항목 Competitive 조건에서 제거 (4-2) | 낮음 | 30분 |
| 5 | 테스트 항목 문구 "선택 가점"으로 조정 (4-3) | 낮음 | 15분 |
| 6 | Jupyter/ML, Kubernetes/IaC 시그니처 추가 (5) | 낮음 | 30분 |
| 7 | 기존 테스트 레포들 퇴행 테스트 (TCG, DeepSentinel, AI 서버, Unity 대기업) | — | 45분 |

**권장 순서:** 1 → 2 → 3 → 4 → 5 → 6 → 7

총 공수: 약 4시간.

---

## 8. 리스크

| 리스크 | 가능성 | 대응 |
|---|---|---|
| Evidence LOC가 과하게 부풀려져서 코드 기여 없는 레포가 높은 점수 받음 | 중간 | Evidence는 50점 만점으로 제한. main + evidence 합산도 100점 캡 |
| 커밋 5개 미만에서 LOC 0.9 가중치가 "커밋 안 쪼개기" 조장 | 낮음 | 점수는 보정하되 진단에서 "작은 단위 커밋 권장"은 유지 |
| Competitive 등급이 너무 쉬워져서 변별력 저하 | 낮음 | "멀티 프로젝트" 조건 추가로 Entry와 차별화 유지 |
| "선택 가점" 문구로 사용자가 테스트를 경시 | 낮음 | Top 등급 조건에는 여전히 필수. 상위 지향 사용자에게는 시그널 작동 |
| Jupyter 시그니처가 일반 데이터 분석 레포에도 걸림 | 낮음 | 최소 2개 이상 .ipynb 또는 노트북 전용 디렉토리 요구 |
| 변경사항이 많아서 기존 테스트 레포에서 예상 못한 퇴행 | 중간 | 7번 퇴행 테스트 필수. TCG, DeepSentinel, AI 서버, Unity 4개 모두 확인 |

---

## 9. 남겨둔 한계 (v5.5 범위 밖)

| 항목 | 이유 | 향후 방향 |
|---|---|---|
| 도메인별 등급 분기 | 설계 변경 규모가 큼 | 최종 발표 전 별도 작업 |
| 게임 포트폴리오 완전 공정 평가 | 위 항목 해결 필요 | 동일 |
| `distinct_author_count` 협업 감지 불가 | author 필터로 단일 작성자만 수집됨 | 추가 API 호출 필요, 현재 우선순위 낮음 |

---

*Git2Value — 기여도 편향 해소 및 진단 기준 재조정 계획 v5.5 — 2026.04.15*
