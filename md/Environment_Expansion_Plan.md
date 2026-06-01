# Git2Value — 신규 환경 카테고리 확장 및 manifest 내용 검증 계획

> 작성일: 2026.04.27 | 대상 버전: v5.7 → v5.8
> 발견 계기: Lua 외 비-게임 영역에도 동일한 "언어로는 직무 결정 불가, 파일 조합으로 추론 가능" 패턴이 다수 존재함을 확인

---

## 1. 문제 정의

### 1-1. 현재 시스템이 놓치는 카테고리들

기존 시스템은 메인 언어 + 의존성 파싱 + 게임 엔진/Lua 호스트/모드 플랫폼만 처리. 다음 영역은 GitHub Linguist가 분류하는 언어와 실제 직무가 일치하지 않아 매칭이 부정확:

| 영역 | 사례 | 현재 분류 (잘못됨) | 실제 직무 |
|---|---|---|---|
| 모바일 | React Native | "JavaScript 웹" | 모바일 개발자 |
| 데이터 엔지니어링 | dbt | "SQL 학습" | 데이터/분석 엔지니어 |
| 인프라 | Helm Chart | "YAML 설정" | DevOps/SRE |
| Web3 | Hardhat 프로젝트 | "JavaScript" | 블록체인 개발자 |
| IDE/브라우저 확장 | VS Code/Chrome 확장 | "TypeScript 웹" | 도구 개발자 |
| ML 데모 | Streamlit | "일반 Python" | ML 엔지니어 |

이들은 모두 **고유한 설정 파일 또는 디렉토리 구조**를 가져서 시그너처 매칭으로 정확히 식별 가능.

### 1-2. manifest.json 충돌 문제

이번 점검에서 **`manifest.json`을 사용하는 환경이 최소 5개**임을 확인:

1. Unity Package Manager (`Packages/manifest.json` — npm 형식)
2. Stardew Valley SMAPI 모드
3. Chrome/Firefox 브라우저 확장
4. Obsidian 플러그인
5. Web App Manifest (PWA)

각 환경의 manifest.json은 **포함하는 키가 다름**:

| 환경 | 고유 키 |
|---|---|
| Stardew Valley | `UniqueID`, `MinimumApiVersion`, `EntryDll` |
| 브라우저 확장 | `manifest_version`, `permissions`, `content_scripts` |
| Obsidian 플러그인 | `id`, `minAppVersion`, `isDesktopOnly` |
| Web App Manifest | `start_url`, `display`, `theme_color` |
| Unity Packages | `dependencies` (npm 형식, scopedRegistries 필드) |

루트 위치 한정만으로는 (Chrome ext, Obsidian, PWA가 모두 루트) 구분 불가. **manifest 내용 기반 분기**가 필수.

---

## 2. 해결 방향

### 2-1. manifest 내용 검증 메커니즘 정식 도입

`Signature_Audit_Plan.md`에서 보류했던 `manifest_signature_keywords` 키를 정식 기능으로 도입. tree 스캔 후 manifest 후보가 발견되면 비동기로 내용을 fetch하여 키 존재 여부로 환경을 확정.

### 2-2. 신규 카테고리 7개 추가

중요도 중간 이상의 7개 카테고리만 우선 도입. 좁은 시장(Anchor, Hugo 등)은 향후 확장으로 보류.

---

## 3. manifest 내용 검증 메커니즘

### 3-1. 새 시그너처 키

```python
# 기존 시그너처 키 + 신규
"manifest_signature_keywords": ["UniqueID", "MinimumApiVersion"]
# manifest.json 등 특정 파일의 내용에 이 키워드들이 모두 포함되어야 매칭
```

### 3-2. 감지 함수 비동기화

기존 `detect_engine_signatures()` 등은 동기 함수. manifest 내용 검증을 위해 비동기 변형 추가:

```python
async def detect_signatures_with_content(
    tree_data: dict,
    fetch_text_fn,        # GitHubExtractor._fetch_repo_text_files
    repo_url: str,
    branch: str,
    signatures: dict,
) -> list[dict]:
    """
    manifest 내용 검증이 필요한 시그너처를 위한 비동기 감지.

    1단계: tree 스캔으로 후보 추출 (기존 동기 로직 재사용)
    2단계: manifest_signature_keywords가 정의된 후보만 내용 fetch
    3단계: 키워드 매칭으로 환경 확정
    """
    # 1단계: 트리 기반 후보 추출
    candidates: list[tuple[str, dict]] = []
    for name, sig in signatures.items():
        if _matches_basic_signature(sig, tree_data):
            candidates.append((name, sig))

    # 2단계: 내용 검증이 필요한 후보들의 manifest 경로 수집
    paths_to_fetch: list[str] = []
    candidate_paths: dict[str, str] = {}  # name -> manifest_path

    for name, sig in candidates:
        if "manifest_signature_keywords" not in sig:
            continue
        manifest_path = _find_manifest_path(tree_data, sig)
        if manifest_path:
            paths_to_fetch.append(manifest_path)
            candidate_paths[name] = manifest_path

    # 3단계: 일괄 fetch
    if paths_to_fetch:
        contents = await fetch_text_fn(repo_url, branch, paths_to_fetch)
    else:
        contents = {}

    # 결과 확정
    detected = []
    for name, sig in candidates:
        if "manifest_signature_keywords" not in sig:
            # 내용 검증 불필요한 시그너처
            detected.append({"name": name, **_extract_meta(sig)})
            continue

        manifest_path = candidate_paths.get(name)
        if not manifest_path:
            continue
        manifest_text = contents.get(manifest_path, "")
        keywords = sig["manifest_signature_keywords"]
        if all(kw in manifest_text for kw in keywords):
            detected.append({"name": name, **_extract_meta(sig)})

    return detected
```

### 3-3. 우선순위 처리

여러 manifest 시그너처가 같은 파일에 매칭될 경우(예: 같은 `manifest.json`에 Chrome ext 키와 Obsidian 키가 동시에 있는 경우), **사전 정의 순서대로 첫 매칭 채택**. 일반적으로 동시 매칭은 발생하지 않지만, 안전장치로 명시.

```python
# MOD_PLATFORM_SIGNATURES 등의 순서 보장 (Python 3.7+ dict 순서)
# 더 구체적인 시그너처를 앞에 배치
```

---

## 4. 신규 카테고리 시그너처

각 시그너처는 기존 사전 구조(`ENGINE_SIGNATURES`, `MOD_PLATFORM_SIGNATURES`)와 동일 형식으로 추가. 분류상 적합한 사전에 배치.

### 4-1. React Native / Expo (모바일)

```python
ENGINE_SIGNATURES = {
    # 기존 (Unity, Unreal, Godot, Flutter, Jupyter/ML, Kubernetes/IaC) ...

    "Expo": {
        # Expo는 RN 기반이지만 더 단순한 구조 → RN보다 먼저 평가
        "required_files_root": ["app.json"],
        "manifest_signature_keywords": ["expo"],  # app.json 내용에 "expo" 키 필수
        "supporting_files_basename": ["package.json"],
        "min_supporting": 1,
        "domain": "모바일 앱",
        "label": "Expo (React Native) 모바일 앱 개발",
    },
    "React Native": {
        "required_files_basename": ["package.json"],
        "required_any_dirs": ["android/", "ios/"],
        "exclude_if_basename_exists": ["pubspec.yaml"],  # Flutter 배제
        "supporting_files_basename": ["metro.config.js", "App.js", "App.tsx"],
        "min_supporting": 1,
        "domain": "모바일 앱",
        "label": "React Native 모바일 앱 개발",
    },
}
```

**판별 핵심:**
- Flutter와 모바일 디렉토리 구조가 같음 → `pubspec.yaml` 부재로 배제
- Expo는 `app.json` 내용에 `"expo"` 키 존재 필수 (일반 React 앱의 `app.json`과 구분)

### 4-2. dbt (데이터 엔지니어링)

```python
ENGINE_SIGNATURES["dbt"] = {
    "required_files_basename": ["dbt_project.yml"],
    "supporting_dirs": ["models/", "seeds/", "macros/", "snapshots/"],
    "min_supporting": 1,
    "domain": "빅데이터 엔지니어",
    "label": "dbt 데이터 모델링",
}
```

`dbt_project.yml`은 dbt 외엔 안 쓰임. 매우 안전.

### 4-3. Helm Chart (인프라)

```python
ENGINE_SIGNATURES["Helm Chart"] = {
    "required_files_basename": ["Chart.yaml"],
    "supporting_dirs": ["templates/"],
    "supporting_files_basename": ["values.yaml"],
    "min_supporting": 1,
    "domain": "DevOps/인프라",
    "label": "Helm Chart 개발",
}
```

`Chart.yaml`은 Helm 외엔 안 쓰임. 매우 안전.

### 4-4. Hardhat (블록체인)

```python
ENGINE_SIGNATURES["Hardhat (Solidity)"] = {
    "required_files_basename": ["hardhat.config.js", "hardhat.config.ts"],
    "supporting_dirs": ["contracts/", "scripts/", "test/"],
    "supporting_files_endswith": [".sol"],
    "min_supporting": 1,
    "domain": "블록체인",
    "label": "Hardhat 기반 Solidity 개발",
}
```

`hardhat.config.{js,ts}`는 Hardhat 외엔 안 쓰임.

### 4-5. Foundry (블록체인, Solidity 신규 표준)

```python
ENGINE_SIGNATURES["Foundry (Solidity)"] = {
    "required_files_basename": ["foundry.toml"],
    "supporting_dirs": ["src/", "test/", "script/", "lib/"],
    "supporting_files_endswith": [".sol"],
    "min_supporting": 2,  # 디렉토리 + .sol 필수
    "domain": "블록체인",
    "label": "Foundry 기반 Solidity 개발",
}
```

`foundry.toml`은 Foundry 외엔 안 쓰임. 단 Foundry의 `lib/` 디렉토리는 일반 라이브러리 폴더와 이름 겹치므로 보조 시그너처는 `.sol` 파일 동반으로 강화.

### 4-6. VS Code 확장 (도구 개발자)

```python
# package.json 의존성 기반이지만, 시그너처 사전에 함께 두는 것이 일관성에 좋음
ENGINE_SIGNATURES["VS Code 확장"] = {
    "required_files_root": ["package.json"],
    "manifest_signature_keywords": ["vscode", "contributes"],
    # package.json 내용에 vscode 의존성 + contributes 필드 동시 존재
    "supporting_files_basename": [".vscodeignore"],
    "min_supporting": 0,
    "domain": "도구 개발",  # 기존 카테고리 없으면 추가 필요
    "label": "VS Code 확장 개발",
}
```

`package.json` 내용 검증으로 일반 Node.js 프로젝트와 구분.

### 4-7. 브라우저 확장 (Chrome/Firefox)

```python
ENGINE_SIGNATURES["Browser Extension"] = {
    "required_files_root": ["manifest.json"],
    "manifest_signature_keywords": ["manifest_version", "permissions"],
    "supporting_files_endswith": [".js", ".html"],
    "min_supporting": 1,
    "domain": "도구 개발",
    "label": "브라우저 확장 개발",
}
```

`manifest_version` + `permissions` 조합은 브라우저 확장 manifest의 명확한 시그너처. Stardew Valley(`UniqueID`/`MinimumApiVersion`)와 Obsidian(`id`/`minAppVersion`/`isDesktopOnly`)과 키 자체가 달라 명확히 구분됨.

---

## 5. "도구 개발" 도메인 신설

VS Code 확장과 브라우저 확장은 기존 6개 도메인(게임 개발, 웹 프론트엔드, 서버/백엔드, ML/AI, 모바일 앱, DevOps/인프라) 중 어디에도 정확히 맞지 않음.

### 5-1. 신규 도메인 추가

```python
# DOMAIN_SIGNALS 에 추가
DOMAIN_SIGNALS = {
    # 기존 6개 ...
    "도구 개발": [
        # 트리 기반 키워드 시그널이 명확하지 않음
        # 시그너처 매칭으로만 감지 (DOMAIN_SIGNALS는 비워두거나 최소 키워드만)
        "extension", "plugin", "addon",
    ],
}

# DOMAIN_TO_CATEGORIES 추가
DOMAIN_TO_CATEGORIES = {
    # 기존 ...
    "도구 개발": ["프론트엔드", "SW/솔루션"],  # 점핏 카테고리에 맞춤
}
```

### 5-2. 직무 매칭 처리

"도구 개발"은 점핏의 "프론트엔드" 또는 "SW/솔루션" 카테고리로 매칭. 채용 공고에 "VS Code 확장 개발자" 같은 직무는 거의 없으므로, 일반 프론트엔드/소프트웨어 직무로 라우팅하되 진단에 맥락 추가.

### 5-3. 진단 안내

```python
def tool_dev_context_message(label: str) -> str:
    return (
        f"{label} 프로젝트로 분류되었습니다. "
        f"채용 시장에 직접 매칭되는 공고는 적으나, "
        f"개발자 도구에 대한 깊은 이해와 사용자 인터페이스 설계 능력을 보여줍니다. "
        f"일반 웹 프론트엔드 또는 SW 개발 직무에 활용 가능합니다."
    )
```

---

## 6. 의존성 파싱 확장 (시그너처 사전과 별도)

다음 도구들은 단일 의존성 추가만으로 명확히 식별되므로, 시그너처 사전 대신 `parse_dependency_contents()` 확장이 적합:

```python
# profile_builder.py _parse_package_json() 등에 추가

PACKAGE_JSON_SIGNALS = {
    # 기존: react, next, vue, ...
    "@expo/cli": "Expo",
    "react-native": "React Native",
    "hardhat": "Hardhat",
    "@nomicfoundation/hardhat-toolbox": "Hardhat",
    "discord.js": "Discord 봇",
    "telegraf": "Telegram 봇",
    "@vscode/vsce": "VS Code 확장",
}

REQUIREMENTS_TXT_SIGNALS = {
    # 기존: fastapi, django, flask, ...
    "streamlit": "Streamlit",
    "gradio": "Gradio",
    "apache-airflow": "Airflow",
    "dbt-core": "dbt",
    "discord.py": "Discord 봇",
    "python-telegram-bot": "Telegram 봇",
    "transformers": "Hugging Face Transformers",
}
```

이러면 시그너처 사전이 비대해지지 않으면서 추가 환경을 커버.

---

## 7. 처리 우선순위 (감지 순서)

여러 시그너처가 동시 매칭될 경우 처리 순서:

1. **모드 플랫폼** (가장 구체적 카테고리)
2. **게임 엔진** (Unity, Unreal, Godot, Defold)
3. **모바일** (Expo → React Native → Flutter)
4. **블록체인** (Foundry → Hardhat)
5. **인프라** (Helm Chart, Kubernetes/IaC)
6. **데이터/AI** (dbt, Jupyter/ML)
7. **도구 개발** (VS Code 확장, 브라우저 확장)
8. **Lua 호스트** (v5.6)

이유: 더 구체적인 환경이 먼저 매칭되어야, 덜 구체적인 환경(예: 일반 모바일 앱)이 잘못 우선순위를 가져가지 않음. Python 3.7+ dict는 입력 순서를 보존하므로 사전 정의 순서가 평가 순서가 됨.

---

## 8. 예상 결과

### 8-1. React Native 앱 레포

```
입력: TypeScript 60% + JavaScript 30% + Java/Kotlin 10%
       package.json + android/ + ios/ + App.tsx + metro.config.js

기존 (v5.7):
  도메인: 웹 프론트엔드 (오감지)
  프로필: "TS/JS 기반 웹 프론트엔드 경험"
  → 모바일 공고 매칭 실패

v5.8:
  ENGINE_SIGNATURES["React Native"] 매칭 (pubspec.yaml 부재 확인)
  도메인: 모바일 앱
  프로필: "TypeScript (60%) 기반 모바일 앱 경험. React Native 모바일 앱 개발."
  → 모바일 공고 매칭
```

### 8-2. dbt 프로젝트

```
입력: SQL 95% + YAML 5%

기존:
  메인 언어 SQL → "SQL 단독" → DBA 카테고리 매칭
  → 데이터 엔지니어 공고 매칭 실패

v5.8:
  dbt_project.yml 발견 → ENGINE_SIGNATURES["dbt"] 매칭
  도메인: 빅데이터 엔지니어
  프로필: "SQL 기반 빅데이터 엔지니어 경험. dbt 데이터 모델링."
  → 데이터 엔지니어 공고 매칭
```

### 8-3. Hardhat 블록체인 프로젝트

```
입력: JavaScript 50% + Solidity 50%

기존:
  도메인: 웹 프론트엔드 또는 서버/백엔드 (혼합)
  → 블록체인 공고 매칭 실패

v5.8:
  hardhat.config.js 발견 → Hardhat 매칭
  도메인: 블록체인
  프로필: "JavaScript (50%), Solidity (50%) 기반 블록체인 경험. Hardhat 기반 Solidity 개발."
  → 블록체인 공고 매칭
```

### 8-4. Chrome 브라우저 확장 vs Stardew Valley 모드

```
공통: 둘 다 루트에 manifest.json + 메인 언어 코드 다수

v5.8 — manifest 내용 검증:
  Chrome ext의 manifest.json: { "manifest_version": 3, "permissions": [...] }
    → "manifest_version" + "permissions" 키 매칭 → 브라우저 확장 확정
  Stardew의 manifest.json: { "UniqueID": "...", "MinimumApiVersion": "3.0" }
    → "UniqueID" + "MinimumApiVersion" 키 매칭 → Stardew Valley 확정
  Unity의 Packages/manifest.json: 루트 아님 → 후보 자체에서 제외
```

내용 검증으로 세 환경이 명확히 구분됨.

### 8-5. Streamlit ML 데모

```
입력: Python 100% + requirements.txt에 streamlit

v5.8 — 의존성 파싱 확장:
  parse_dependency_contents() → frameworks에 "Streamlit" 추가
  프로필: "Python (100%) 기반 ML/AI 경험. Streamlit 활용 경험."
  → ML 데모 시그널이 ML/AI 공고 매칭에 기여
```

---

## 9. 구현 우선순위

| 순위 | 작업 | 공수 |
|---|---|---|
| 1 | manifest 내용 검증 메커니즘 도입 (`detect_signatures_with_content` 비동기 함수) | 2시간 |
| 2 | `evaluate_repository()` 흐름에 비동기 시그너처 감지 통합 | 1시간 |
| 3 | "도구 개발" 도메인 신설 (DOMAIN_SIGNALS, DOMAIN_TO_CATEGORIES, 라우팅) | 30분 |
| 4 | React Native / Expo 시그너처 추가 + Flutter 배제 조건 | 30분 |
| 5 | dbt / Helm Chart 시그너처 추가 | 30분 |
| 6 | Hardhat / Foundry 시그너처 추가 | 30분 |
| 7 | VS Code 확장 / 브라우저 확장 시그너처 + manifest 키 검증 | 1시간 |
| 8 | 의존성 파싱 확장 (Streamlit, Gradio, Airflow, Discord 봇 등) | 1시간 |
| 9 | 도구 개발 / 블록체인 / 데이터 엔지니어링 진단 안내 메시지 | 1시간 |
| 10 | 테스트: RN, dbt, Hardhat, VS Code 확장, Chrome 확장 각 1개씩 | 1시간 |
| 11 | 퇴행 테스트: 기존 모든 카테고리 (Unity, Lua, EDOPro, 일반 웹) | 1시간 |

총 약 10시간. manifest 내용 검증(1번) 도입이 다른 신규 카테고리의 전제이므로 우선 처리.

---

## 10. 리스크

| 리스크 | 가능성 | 대응 |
|---|---|---|
| 비동기 시그너처 감지 통합으로 기존 동기 흐름 깨짐 | 중간 | 동기 부분(트리 스캔)과 비동기 부분(content fetch) 명확히 분리. 단계적 통합 |
| manifest fetch가 추가 API 호출로 rate limit 부담 | 낮음 | 후보 단계에서 필터링하여 실제 fetch는 1~2개 manifest로 제한 |
| "도구 개발" 도메인 신설로 기존 매칭 결과 오염 | 낮음 | DOMAIN_TO_CATEGORIES에 보수적 매핑(프론트엔드/SW). 기존 도메인은 영향 없음 |
| Foundry의 `lib/` 폴더가 일반 라이브러리 폴더와 충돌 | 낮음 | `.sol` 파일 동반 요구로 구분 |
| Expo가 `app.json`에 `expo` 키만 있고 다른 곳에는 없는 경우 | 낮음 | manifest_signature_keywords로 검증 |
| 의존성 파싱 확장이 `package.json` 너무 큰 경우 | 낮음 | 기존과 동일하게 80KB 제한 |
| 시그너처 사전 비대화 | 중간 | 좁은 시장(Anchor, Hugo 등)은 향후 확장으로 보류 |
| 신규 도메인 매칭 결과 검증 불충분 | 중간 | 11번 퇴행 테스트로 기존 카테고리 영향 확인 |

---

## 11. 본 계획에서 제외한 항목 (향후 확장)

**낮은 시장 점유 (좁은 사용자 풀):**
- Anchor (Solana) — Solidity가 더 큰 시장
- Hugo / Jekyll / Docusaurus — 직무 시그널보다 매칭 제외에 가까움
- Awesome 리스트 — 매칭 제외 처리만 필요
- Obsidian 플러그인 — 사용자 풀 좁음

**의존성 파싱으로 대체 가능 (시그너처 불필요):**
- p5.js / Three.js — `three`, `p5` 의존성 추가만으로 식별
- 강화학습 (gymnasium, stable-baselines3) — 의존성 파싱 확장으로 처리
- Discord/Telegram 봇 — 의존성 파싱 확장으로 처리

**복잡도 대비 가치 낮음:**
- 미니앱 (위챗/카카오 등) — 한국 사용자 풀 작음
- iOS/Android 네이티브 시그너처 강화 — 의존성 파싱이 일정 수준 커버 중

이들은 실제 사용자 피드백에서 빈도가 높아지면 그때 추가.

---

## 12. 시그너처 사전 정의 책임

본 계획 적용 후 시그너처 정의는 다음과 같이 분산됨:

- **`Engine_Detection_Plan.md`** (v5.4): Unity, Unreal, Godot, Flutter, Jupyter/ML, Kubernetes/IaC + 본 계획 신규 추가 (RN, Expo, dbt, Helm Chart, Hardhat, Foundry, VS Code 확장, 브라우저 확장)
- **`Language_Categorization_Plan.md`** (v5.6): Lua 호스트 환경 (Roblox, Love2D 등)
- **`Mod_Platform_Plan.md`** (v5.7): 모드/플러그인 (EDOPro, Garry's Mod, Stardew Valley 등)
- **`Signature_Audit_Plan.md`**: 시그너처 강화 권한 있는 출처
- **`profile_builder.parse_dependency_contents()`**: 단일 의존성으로 식별 가능한 도구

향후 신규 시그너처 추가 시 `Signature_Audit_Plan.md` §7의 체크리스트 적용.

---

*Git2Value — 신규 환경 카테고리 확장 및 manifest 내용 검증 계획 v5.8 — 2026.04.27*
