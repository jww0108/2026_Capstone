# Git2Value — 시그너처 오탐 점검 및 강화 계획

> 작성일: 2026.04.27 | 적용 대상: v5.4 / v5.6 / v5.7 시그너처 전반
> 발견 계기: Stardew Valley 시그너처가 Unity 프로젝트를 오탐. 이 외 시그너처들도 일괄 점검 필요

---

## 1. 점검 범위

세 계획 파일에 정의된 모든 시그너처를 오탐 위험 관점에서 점검:

- **v5.4 ENGINE_SIGNATURES**: Unity, Unreal Engine, Godot, Flutter, Jupyter/ML, Kubernetes/IaC
- **v5.6 LUA_HOST_SIGNATURES**: Roblox, Love2D, Defold, Solar2D/Corona, Cocos2d-x, OpenResty, NodeMCU, Neovim
- **v5.7 MOD_PLATFORM_SIGNATURES**: EDOPro, Garry's Mod, Factorio, Minecraft 플러그인, Stardew Valley, WoW 애드온

---

## 2. 점검 결과 요약

| 시그너처 | 오탐 위험 | 충돌 대상 | 조치 필요 |
|---|---|---|---|
| Unity | 안전 | — | — |
| Unreal Engine | 안전 | — | — |
| Godot | 안전 | — | — |
| **Flutter** | 중간 | 순수 Dart 라이브러리/서버 | ✅ 강화 |
| **Jupyter/ML 실험** | 낮음 | 노트북 디렉토리 가진 Python 프로젝트 | ✅ 강화 |
| Kubernetes/IaC | 안전 | — | — |
| Roblox | 안전 | — | — |
| **Love2D** | 중간 | Solar2D/Corona (사전 순서 문제) | ✅ 강화 |
| Defold | 안전 | — | — |
| Solar2D/Corona | 안전 | — | — |
| Cocos2d-x Lua | 안전 | — | — |
| **OpenResty/Nginx-Lua** | 중간 | 일반 Nginx 설정 레포 | ✅ 강화 |
| NodeMCU/임베디드 Lua | 안전 | — | — |
| **Neovim 설정** | 낮음 | 우연히 같은 구조의 Lua 프로젝트 | ✅ 강화 (선택) |
| EDOPro 카드 스크립트 | 안전 | — | — |
| Garry's Mod | 안전 | — | — |
| Factorio 모드 | 안전 | — | — |
| **Minecraft 플러그인** | 낮음 | Jenkins 플러그인 | ✅ 강화 |
| **Stardew Valley (SMAPI)** | 높음 | **Unity 프로젝트 (실제 발견됨)** | ✅ 강화 (즉시) |
| WoW 애드온 | 안전 | — | — |

총 7개 시그너처 강화 필요. Stardew Valley가 가장 시급함.

---

## 3. 시그너처별 강화 방안

### 3-1. Stardew Valley (SMAPI) — 최우선

**문제:** `manifest.json`이 Unity의 `Packages/manifest.json`과 충돌. `.cs` 파일 동반 조건도 Unity가 자동 통과.

**원인:**
- `manifest.json`은 Chrome Extension, PWA, Unity Package Manager, npm 등에서 광범위하게 사용
- Unity는 C#이라 `.cs` 보조 조건도 무력화

**강화안:**
```python
"Stardew Valley (SMAPI)": {
    "required_files_root": ["manifest.json"],   # 루트 한정 (Unity Packages/ 제외)
    "manifest_signature_keywords": [             # 추가 검증: SMAPI 고유 키
        "UniqueID", "MinimumApiVersion",
    ],
    "supporting_files_endswith": [".cs"],
    "min_supporting": 1,
    "domain": "게임 개발",
    "label": "Stardew Valley 모드 개발",
    "mod_context": True,
}
```

**효과:**
- Unity의 `Packages/manifest.json`은 루트 아니므로 1차 차단
- Chrome Extension/PWA의 manifest.json은 SMAPI 키워드 없으므로 2차 차단
- 정상 SMAPI 모드만 통과

**구현 비용:** manifest 내용을 fetch해야 하므로 감지 함수 비동기화 필요. 비용은 작지만 시그너처 매칭이 단순 트리 스캔에서 벗어남.

**대안 (단순 버전):** manifest 내용 검증 없이 루트 한정만 적용해도 Unity 오탐은 즉시 해소. Chrome Extension/PWA 오탐은 잔존하지만 `.cs` 동반 조건으로 자연스럽게 걸러짐. **이걸 우선 적용하고, 실제 Chrome Extension 오탐이 발견되면 manifest 내용 검증 추가.**

```python
# 단순 강화안 (1단계)
"Stardew Valley (SMAPI)": {
    "required_files_root": ["manifest.json"],
    "supporting_files_endswith": [".cs"],
    "min_supporting": 1,
    ...
}
```

---

### 3-2. Flutter

**문제:** `pubspec.yaml` + `lib/` 만으로도 통과. 순수 Dart 라이브러리/서버 프로젝트(Flutter 아님)도 동일 구조를 가질 수 있음.

**강화안:** `android/` 또는 `ios/` 중 **하나라도 반드시** 있도록 변경.

```python
"Flutter": {
    "required_any": ["pubspec.yaml"],
    "required_any_dirs": ["android/", "ios/"],   # 둘 중 하나는 필수
    "supporting_dirs": ["lib/"],
    "min_supporting": 1,
    ...
}
```

`android/`나 `ios/` 디렉토리는 Flutter가 모바일 빌드 환경을 자동 생성한 결과물이므로, 이게 없으면 Flutter가 아님.

**구현 비용:** 감지 함수에 `required_any_dirs` 같은 새 키 추가. 한 줄 변경 수준.

**대안:** 새 키 도입 없이 기존 `required_any`에 모바일 디렉토리를 OR 조건으로 묶어도 됨. 다만 `pubspec.yaml`도 필수라는 의미가 흐려져서 새 키가 의미상 명확함.

---

### 3-3. Jupyter/ML 실험

**문제:** `.ipynb` 1개 + `notebooks/` 디렉토리만으로 매칭. README 시각화용 노트북 1개 가진 일반 Python 백엔드 프로젝트도 잡힘.

**강화안:** `.ipynb` 파일 수 임계 상향.

```python
"Jupyter/ML 실험": {
    "required_any": [],
    "supporting_files": [".ipynb"],
    "supporting_dirs": ["notebooks/", "experiments/"],
    "min_supporting": 3,   # 기존 2 → 3 (또는 .ipynb 카운트 별도)
    ...
}
```

또는 더 정확히: `.ipynb` 파일 수가 **3개 이상**일 때만 매칭.

```python
"Jupyter/ML 실험": {
    "file_count_endswith": {".ipynb": 3},   # 새 키: 확장자별 최소 카운트
    "supporting_dirs": ["notebooks/", "experiments/"],
    "min_supporting": 0,
    ...
}
```

이러면 README 시각화용 `demo.ipynb` 1~2개 가진 백엔드 프로젝트는 매칭에서 빠짐.

---

### 3-4. Love2D

**문제:** `main.lua` + `conf.lua`(둘 다 루트)만으로 매칭. 그런데 **Solar2D/Corona도 동일하게 `main.lua`를 사용**하고, `conf.lua`도 사용 가능. 사전 순서상 Love2D가 먼저 평가되면 Solar2D 프로젝트가 Love2D로 오인됨.

**강화안:** Solar2D를 먼저 평가하도록 사전 순서 조정 + Love2D에 부정 조건(Solar2D 시그너처 부재 확인) 추가.

```python
LUA_HOST_SIGNATURES = {
    "Solar2D/Corona": {   # Love2D보다 먼저 배치
        "required_files_root": ["main.lua", "build.settings"],
        ...
    },
    "Love2D": {
        "required_files_root": ["main.lua", "conf.lua"],
        "exclude_if_basename_exists": ["build.settings"],   # Solar2D 표지 부재 확인
        ...
    },
    ...
}
```

`exclude_if_basename_exists` 같은 부정 조건을 도입하면 안전. 다만 사전 순서만으로도 (Solar2D가 먼저 매칭되어 반환되면 Love2D 평가 자체가 안 됨) 충분히 해결됨. **사전 순서 조정만으로 충분.**

---

### 3-5. OpenResty/Nginx-Lua

**문제:** `nginx.conf` 또는 `openresty.conf`만 있으면 매칭. 일반 Nginx 설정 레포(Lua 모듈 없는 단순 reverse proxy 설정)도 잡힘.

**강화안:** `lua/` 디렉토리 또는 `.lua` 파일 다수를 필수 조건으로.

```python
"OpenResty/Nginx-Lua": {
    "required_any_basename": ["nginx.conf", "openresty.conf"],
    "supporting_dirs": ["lua/"],
    "supporting_files_endswith": [".lua"],
    "min_supporting": 1,   # 기존 0 → 1 (lua/ 또는 .lua 파일 필수)
    ...
}
```

또는 더 명확히: Lua 코드가 실제로 있는지 확인. `min_supporting: 1`로만 바꿔도 일반 Nginx 설정과 OpenResty가 구분됨.

---

### 3-6. Minecraft 플러그인

**문제:** `plugin.yml`은 Jenkins 플러그인도 사용. Minecraft Bukkit/Spigot/Paper와 Jenkins는 둘 다 Java 기반이라 자연스럽게 구분되지 않음.

**강화안:** Minecraft 고유 디렉토리/패키지 패턴 동반 요구.

```python
"Minecraft 플러그인": {
    "required_files_basename": ["plugin.yml"],
    "supporting_files_basename": ["paper-plugin.yml", "bungee.yml"],
    "supporting_path_contains": [
        "org/bukkit/", "io/papermc/", "net/md_5/bungee/",
    ],   # 새 키: 경로에 특정 문자열 포함
    "min_supporting": 1,
    ...
}
```

Bukkit/Paper/BungeeCord는 자바 패키지 구조에서 이 경로들이 등장. Jenkins는 `io/jenkins/` 또는 `hudson/`을 쓰므로 명확히 구분됨.

**대안 (단순 버전):** `plugin.yml` 내용에서 `main:` 필드 또는 `api-version:` 필드를 검증. 다만 manifest 내용 검증과 동일하게 비동기 fetch 필요. 우선 경로 패턴 매칭만 적용하고, 실제 Jenkins 오탐이 발견되면 내용 검증 추가.

---

### 3-7. Neovim 설정

**문제:** `init.lua` + `lua/` 폴더는 우연히 일반 Lua 프로젝트도 가질 수 있음. 다만 실제 케이스가 드물어서 우선순위 낮음.

**강화안 (선택):** Neovim 설정 특유 파일을 보조 시그너처로 추가.

```python
"Neovim 설정": {
    "required_files_root": ["init.lua"],
    "supporting_dirs": ["lua/", "plugin/", "after/"],
    "supporting_files_basename": [
        "lazy-lock.json",      # lazy.nvim 패키지 매니저
        "packer_compiled.lua", # packer.nvim
    ],
    "min_supporting": 2,   # 기존 1 → 2 (Neovim 표지 둘 이상 요구)
    ...
}
```

`lazy-lock.json`이나 `packer_compiled.lua`가 있으면 거의 확실히 Neovim 설정. 일반 Lua 프로젝트가 이런 파일을 가질 일은 없음.

**우선순위:** 낮음. 실제 오탐 발견 시 적용.

---

## 4. 새로 도입할 시그너처 키

위 강화안에서 등장한 새 시그너처 키들을 정리하면:

| 키 | 설명 | 사용처 |
|---|---|---|
| `required_any_dirs` | 디렉토리 OR 조건 (하나라도 있어야) | Flutter |
| `file_count_endswith` | 확장자별 최소 파일 수 | Jupyter/ML |
| `exclude_if_basename_exists` | 부정 조건: 이 basename이 있으면 매칭 제외 | Love2D |
| `supporting_path_contains` | 경로 부분 문자열 포함 | Minecraft 플러그인 |
| `manifest_signature_keywords` | 특정 파일 내용에 키워드 포함 (비동기 fetch 필요) | Stardew Valley (선택) |

각 키를 감지 함수가 처리하도록 확장 필요:

```python
def _matches_signature(sig, paths, basenames, root_files) -> bool:
    # 기존 검사들 ...

    # required_any_dirs
    if "required_any_dirs" in sig:
        if not any(any(d.lower() in p for p in paths) for d in sig["required_any_dirs"]):
            return False

    # file_count_endswith
    if "file_count_endswith" in sig:
        for ext, min_count in sig["file_count_endswith"].items():
            cnt = sum(1 for p in paths if p.endswith(ext.lower()))
            if cnt < min_count:
                return False

    # exclude_if_basename_exists
    if "exclude_if_basename_exists" in sig:
        if any(b in sig["exclude_if_basename_exists"] for b in basenames):
            return False

    # supporting_path_contains (별도 카운팅)
    for s in sig.get("supporting_path_contains", []):
        if any(s.lower() in p for p in paths):
            support_count += 1

    # 기존 supporting 검사 ...
```

이건 v5.4/v5.6/v5.7의 `_matches_signature()` 헬퍼에 일괄 적용.

---

## 5. 우선순위 및 적용 순서

| 순위 | 항목 | 시급도 | 공수 |
|---|---|---|---|
| 1 | Stardew Valley 루트 한정 | 즉시 (실제 오탐 발견됨) | 5분 |
| 2 | 새 시그너처 키 5종을 감지 함수에 추가 | 새 기능들의 전제 | 1시간 |
| 3 | Flutter `required_any_dirs` 적용 | 중간 | 5분 |
| 4 | Jupyter/ML `file_count_endswith` 적용 | 낮음 | 5분 |
| 5 | Love2D 사전 순서 조정 + 부정 조건 | 중간 | 10분 |
| 6 | OpenResty `min_supporting: 1`로 조정 | 중간 | 5분 |
| 7 | Minecraft `supporting_path_contains` 적용 | 낮음 | 10분 |
| 8 | Neovim 보조 시그너처 추가 | 낮음 (선택) | 10분 |
| 9 | Stardew Valley manifest 내용 검증 (실제 Chrome ext 오탐 시) | 보류 | 1시간 |
| 10 | 점검 통과 테스트: Unity, 일반 Dart, 일반 Python (노트북 1개), 일반 Nginx, Jenkins 플러그인 | 검증 | 30분 |

총 약 2시간 30분. 새 시그너처 키 확장(2번)이 다른 모든 변경의 전제이므로 먼저 처리.

---

## 6. 적용 후 각 계획 파일 갱신

본 점검 결과는 다음 계획 파일들에 반영:

- **Engine_Detection_Plan.md (v5.4)**: Flutter, Jupyter/ML 시그너처 강화
- **Language_Categorization_Plan.md (v5.6)**: Love2D, OpenResty, Neovim 시그너처 강화
- **Mod_Platform_Plan.md (v5.7)**: Stardew Valley, Minecraft 플러그인 시그너처 강화
- **각 계획의 _matches_signature() 헬퍼**: 새 시그너처 키 5종 처리 로직 추가

각 파일은 본 점검 보고서를 참조하는 형태로 갱신하되, 시그너처 정의 자체는 본 보고서를 권위 있는 출처(source of truth)로 삼음.

---

## 7. 향후 방침

새 시그너처를 추가할 때마다 다음 체크리스트를 적용:

1. 시그너처의 키 파일/디렉토리가 다른 환경에서도 사용되는지 확인
2. 사용된다면 보조 시그너처로 명확히 구분 가능한지 확인
3. 명확히 구분 불가능하면:
   - 부정 조건(`exclude_if_*`) 사용
   - 또는 파일 내용 검증 도입
   - 또는 사전 순서로 더 구체적인 시그너처를 먼저 평가
4. 추가 후 다른 시그너처와의 충돌 가능성 재점검

이 체크리스트를 본 보고서에 명시하여 향후 신규 시그너처 추가 시 일관된 검증 절차로 활용.

---

*Git2Value — 시그너처 오탐 점검 및 강화 계획 — 2026.04.27*
