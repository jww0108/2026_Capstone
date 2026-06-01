# Git2Value — 엔진/프레임워크 구조 감지 계획

> 작성일: 2026.04.13 | 대상 버전: v5.3.1 → v5.4
> 발견 계기: NC/Nexon 통과 Unity 포트폴리오에서 Unity 감지 실패 (README 없음, 의존성 파일 없음)

---

## 1. 문제 정의

### 현재 프레임워크/엔진 감지 방식과 한계

| 감지 방식 | 커버하는 것 | 놓치는 것 |
|---|---|---|
| DOMAIN_SIGNALS (파일명 키워드) | "게임 개발" 도메인 (game, player, enemy 등) | "Unity인지 Unreal인지" 특정 불가 |
| 의존성 파일 파싱 | React, Django, FastAPI, Spring Boot 등 | Unity, Unreal, Godot, Flutter (의존성 파일 형식이 다름) |
| README 키워드 추출 | "unity", "unreal" 등 텍스트 언급 | README가 없으면 감지 불가 |

실제 실패 사례: NC/Nexon 통과 Unity 게임 레포
- README 없음 → README 키워드 추출 실패
- .csproj는 ignore_extensions → 의존성 파싱 불가
- DOMAIN_SIGNALS로 "게임 개발" 도메인은 잡았지만 "Unity"는 특정 못 함
- 프로필 텍스트에 "Unity"가 빠져서 Unity 특화 공고와의 매칭 약화

### 핵심 인사이트

Unity, Unreal, Flutter 같은 도구들은 **고유한 디렉토리/파일 구조**를 갖고 있어서, 의존성 파일이나 README가 없어도 tree 구조만으로 100% 확정할 수 있다. 이 시그니처는 수년간 변하지 않는 안정적 패턴이다.

---

## 2. 해결 방향

### LLM vs 하드코딩 검토 결과

| 방식 | 장점 | 단점 | 결론 |
|---|---|---|---|
| LLM에 트리 전달 | 새 프레임워크 자동 대응 | 응답 불일관, 레이턴시 +2~5초, 설계 원칙 위반 | ❌ |
| 하드코딩 시그니처 | 100% 일관성, 0 레이턴시, 외부 의존 없음 | 새 프레임워크 수동 추가 필요 | ✅ |

파일 구조 시그니처는 프레임워크마다 고정되어 있고 변하지 않는다 (Unity의 Assets/ + .meta는 10년째 동일). 패턴이 명확한 문제에 LLM은 과잉.

---

## 3. 구현 설계

### 3-1. 시그니처 사전

```python
ENGINE_SIGNATURES: dict[str, dict] = {
    "Unity": {
        "required_any": ["assets/"],
        "supporting_files": [".meta", ".unity", ".prefab", ".asset"],
        "supporting_dirs": ["projectsettings/", "packages/"],
        "min_supporting": 1,
    },
    "Unreal Engine": {
        "required_any": ["source/"],
        "supporting_files": [".uproject", ".uasset", ".umap"],
        "supporting_dirs": ["content/", "config/", "plugins/"],
        "min_supporting": 1,
    },
    "Godot": {
        "required_any": [],
        "supporting_files": [".godot", ".tscn", ".tres", ".gd", ".gdshader"],
        "supporting_dirs": [],
        "min_supporting": 2,
    },
    "Flutter": {
        "required_any": ["pubspec.yaml"],
        "supporting_files": [],
        "supporting_dirs": ["lib/", "android/", "ios/"],
        "min_supporting": 1,
    },
}
```

### 3-2. 감지 함수

```python
def detect_engine_signatures(tree_data: dict) -> list[str]:
    """
    파일 트리에서 엔진/프레임워크 시그니처를 감지.
    DOMAIN_SIGNALS(키워드 기반), 의존성 파싱과 독립적으로 동작.
    tree_data를 이미 갖고 있으므로 추가 API 호출 불필요.
    """
    if not tree_data or "tree" not in tree_data:
        return []

    all_paths = [item["path"].lower().replace("\\", "/") for item in tree_data["tree"]]

    detected: list[str] = []

    for name, sig in ENGINE_SIGNATURES.items():
        # required_any 체크: 하나라도 있으면 통과
        has_required = False
        if not sig["required_any"]:
            has_required = True
        else:
            for req in sig["required_any"]:
                if any(req in p for p in all_paths):
                    has_required = True
                    break

        if not has_required:
            continue

        # supporting 카운트
        support_count = 0
        for sf in sig.get("supporting_files", []):
            if any(p.endswith(sf) for p in all_paths):
                support_count += 1
        for sd in sig.get("supporting_dirs", []):
            if any(sd in p for p in all_paths):
                support_count += 1

        if support_count >= sig.get("min_supporting", 1):
            detected.append(name)

    return detected
```

### 3-3. 기존 시스템과의 통합

감지 결과를 `frameworks` 리스트에 합산. 기존 `build_profile_text()`가 자동으로 처리.

```python
# github_extractor.py evaluate_repository() 내
# 기존
frameworks = profile_builder.parse_dependency_contents(dep_contents)

# 추가
engine_detected = profile_builder.detect_engine_signatures(tree_data)
frameworks = engine_detected + frameworks  # 엔진을 앞에 배치
```

### 3-4. 프로필 텍스트 반영 예시

```
변경 전 (Unity 미감지):
  "C# (100%) 기반 게임 개발 경험. 게임, game 관련 프로젝트."

변경 후 (Unity 감지):
  "C# (100%) 기반 게임 개발 경험. Unity 활용 경험. 게임, game 관련 프로젝트."
```

"Unity 활용 경험"이 프로필에 들어가면 Unity 특화 게임 공고와의 FAISS 유사도가 올라감.

---

## 4. .meta 파일 처리 정책

### 현재 상태

`.meta`가 `ignore_extensions`에 포함 → LOC 계산에서 제외 + 소스 코드로 인정 안 함.

### 변경 방침

**LOC 계산에서는 계속 제외하되, 존재 여부 감지에는 사용.**

`detect_engine_signatures()`는 tree_data의 전체 경로를 스캔하므로 `ignore_extensions`와 무관하게 `.meta` 파일을 감지할 수 있음. `_is_valid_source_code()`와 별도 경로이므로 충돌 없음.

즉 코드 변경 없이 현재 구조에서 바로 동작.

---

## 5. 게임 등급 기준 편향 문제 (연관 이슈)

### 발견

NC/Nexon 통과 포트폴리오가 Entry로 분류됨. 원인은 `expected_level()`의 Competitive/Top 조건이 웹 개발 관행에 편향되어 있기 때문:

- 테스트: Unity Test Framework은 현재 감지 안 됨 → 미흡
- CI/CD: Unity Cloud Build는 GitHub Actions가 아님 → 미경험
- 배포: 스토어 배포는 Docker가 아님 → 미경험
- README: 게임은 플레이 영상이 README 역할 → 부실 판정

### 대응 방향

이번(v5.4)에서는 엔진 감지까지만 구현하고, 도메인별 등급 분기는 최종 발표 전까지 별도 계획으로 진행.

단, 엔진이 감지되면 진단 리포트에 컨텍스트 안내를 추가할 수 있음:

```python
# portfolio_diagnosis.py
if "Unity" in detected_engines or "Unreal Engine" in detected_engines:
    # 테스트/CI/CD/배포 항목에 게임 개발 맥락 추가
    test_action = "Unity Test Framework 또는 PlayMode 테스트 추가를 권장합니다."
    cicd_action = "Unity Cloud Build 또는 GameCI GitHub Action을 검토해보세요."
    deploy_action = "빌드 결과물(APK/EXE) 또는 itch.io 배포 경험을 README에 명시하세요."
```

이렇게 하면 등급 기준을 바꾸지 않아도 **피드백이 게임 개발 맥락에 맞게 조정**됨.

---

## 6. 커버리지 판단

### 이번에 넣는 것 (의존성 파싱이 커버 못 하는 빈틈)

| 엔진/프레임워크 | 시그니처 고유성 | 의존성 파싱 커버 여부 | 넣을까? |
|---|---|---|---|
| Unity | ⭐⭐⭐⭐⭐ (Assets/ + .meta) | ❌ 불가 | ✅ |
| Unreal Engine | ⭐⭐⭐⭐⭐ (Source/ + .uproject) | ❌ 불가 | ✅ |
| Godot | ⭐⭐⭐⭐ (.tscn + .gd) | ❌ 불가 | ✅ |
| Flutter | ⭐⭐⭐⭐ (pubspec.yaml + lib/) | ❌ pubspec.yaml 미지원 | ✅ |

### 넣지 않는 것 (이미 의존성 파싱으로 커버 중)

| 프레임워크 | 의존성 파싱에서 감지 | 구조 감지 추가 필요? |
|---|---|---|
| React / Next.js | ✅ package.json | ❌ 중복 |
| Django / FastAPI / Flask | ✅ requirements.txt | ❌ 중복 |
| Spring Boot | ✅ build.gradle / pom.xml | ❌ 중복 |
| Ruby on Rails | ✅ Gemfile | ❌ 중복 |

### 향후 추가 고려 (필요시)

| 대상 | 시그니처 | 우선순위 |
|---|---|---|
| Jupyter/ML 실험 | .ipynb 파일 존재 | 낮음 (AI 도메인은 README 키워드로 커버) |
| Terraform IaC | .tf 파일 + modules/ | 낮음 (인프라 도메인 공고 소수) |
| Docker Compose 멀티 서비스 | docker-compose.yml | 낮음 (배포 감지에서 이미 커버) |

---

## 7. 예상 결과

### NC/Nexon 통과 Unity 레포 (README 없음)

```
현재 (v5.3.1):
  프로필: "C# (100%) 기반 게임 개발 경험."
  → Unity 언급 없음

v5.4 적용 후:
  detect_engine_signatures() → ["Unity"]
  frameworks: ["Unity"]
  프로필: "C# (100%) 기반 게임 개발 경험. Unity 활용 경험."
  → Unity 특화 게임 공고와의 유사도 상승
  
  진단 피드백:
    테스트 권장: "Unity Test Framework 또는 PlayMode 테스트 추가를 권장합니다."
    CI/CD 권장: "Unity Cloud Build 또는 GameCI GitHub Action을 검토해보세요."
```

### Flutter 모바일 앱 레포

```
현재: pubspec.yaml이 의존성 파싱에 없어서 프레임워크 감지 실패
v5.4: detect_engine_signatures() → ["Flutter"]
프로필: "Dart (80%) 기반 모바일 앱 경험. Flutter 활용 경험."
```

### 일반 웹 레포 (React + Django)

```
detect_engine_signatures() → [] (해당 시그니처 없음)
기존 의존성 파싱이 React, Django를 감지 → 변화 없음. 퇴행 없음.
```

---

## 8. 구현 우선순위

| 순위 | 작업 | 난이도 | 예상 공수 |
|---|---|---|---|
| 1 | `ENGINE_SIGNATURES` 사전 + `detect_engine_signatures()` 함수 구현 | 낮음 | 1시간 |
| 2 | `evaluate_repository()`에서 호출 + frameworks에 합산 | 낮음 | 15분 |
| 3 | 게임 엔진 감지 시 진단 피드백 맥락 조정 | 낮음 | 30분 |
| 4 | NC/Nexon Unity 레포로 테스트 | — | 30분 |
| 5 | 기존 테스트 레포(TCG, DeepSentinel, AI 서버) 퇴행 테스트 | — | 30분 |

**권장 순서:** 1 → 2 → 4 → 5 → 3

---

## 9. 리스크

| 리스크 | 가능성 | 대응 |
|---|---|---|
| Assets/ 디렉토리가 Unity가 아닌 일반 에셋 폴더일 수 있음 | 낮음 | .meta 또는 .unity 파일 동시 존재를 요구 (min_supporting: 1) |
| Flutter의 pubspec.yaml이 Dart 일반 프로젝트에도 존재 | 중간 | lib/ + (android/ 또는 ios/) 동시 존재로 Flutter 특정 |
| 감지된 엔진이 frameworks에 중복 추가될 수 있음 | 낮음 | 의존성 파싱과 엔진 감지 결과를 합칠 때 dedup 처리 |
| 등급 기준 웹 편향은 이번에 해결 안 됨 | 인지 | 진단 피드백 맥락 조정으로 부분 완화. 등급 분기는 별도 계획 |

---

*Git2Value — 엔진/프레임워크 구조 감지 계획 v5.4 — 2026.04.13*
