# Git2Value — 모드 플랫폼 감지 및 설정 프로젝트 처리 계획

> 작성일: 2026.04.27 | 대상 버전: v5.6 → v5.7
> 발견 계기: EDOPro 카드 스크립트 등 "기존 게임의 커스텀 모드" 프로젝트가 어떤 카테고리에도 맞지 않음

---

## 1. 문제 정의

### 1-1. 모드/플러그인 프로젝트의 카테고리 부재

EDOPro(유희왕 시뮬레이터)의 카드 스크립트 같은 프로젝트는 다음 어디에도 해당하지 않음:

- 게임 엔진 프로젝트가 아님 (엔진 자체를 만든 것 아님)
- 일반 Lua 라이브러리도 아님
- v5.6의 LUA_HOST_SIGNATURES에도 매칭되지 않음

**이건 "기존 게임/플랫폼의 모드/플러그인 개발"이라는 별도 카테고리.** 채용 시장에 "게임 모드 개발자" 공고는 거의 없지만, 게임 회사 신입 지원 시 **"게임을 깊게 이해하고 직접 만들어본 사람"이라는 시그널**로서 가치가 있음.

### 1-2. 동일 패턴이 적용되는 다른 모드/플러그인 플랫폼

| 모드/플러그인 대상 | 시그너처 | 주 사용 언어 |
|---|---|---|
| EDOPro (유희왕) | `c\d{8}.lua` 카드 스크립트 다수 | Lua |
| Garry's Mod | gamemodes/, entities/, lua/ | Lua |
| Factorio | info.json + control.lua + data.lua | Lua |
| Minecraft 플러그인 (Bukkit/Spigot/Paper) | plugin.yml | Java/Kotlin |
| Stardew Valley (SMAPI) | manifest.json | C# |
| Skyrim/Fallout (Papyrus) | .esp + .psc | Papyrus |
| WoW 애드온 | .toc 파일 | Lua |

이들은 공통적으로:
- 게임 도메인이지만 자체 엔진 개발이 아님
- 직무 매칭은 가능하되 진단에서 맥락 안내가 필요
- 일부(WoW 애드온 등)는 직무 시그널 없이 취미

### 1-3. 설정 프로젝트의 매칭 오염

v5.6에서 `is_config: True`로 분류한 레포(Neovim 설정 등)가 직무 매칭 입력에 포함되면 결과가 왜곡됨. Neovim 설정 레포로 직무 매칭을 수행하는 것은 의미가 없으며, 사용자에게도 혼란을 줌.

---

## 2. 해결 방향

### 2-1. 모드 플랫폼 시그너처 사전 도입

`MOD_PLATFORM_SIGNATURES`를 정의하여 게임 모드/플러그인 프로젝트를 감지하고, 게임 도메인으로 분류하되 진단에서 "모드 개발" 맥락을 표시.

### 2-2. 파일명 정규식 패턴 매칭 지원

EDOPro의 `c12345678.lua` 같은 정규식 기반 파일명 패턴을 시그너처에서 사용 가능하도록 감지 함수 확장.

### 2-3. 설정 프로젝트의 매칭 제외

v5.6에서 도입한 `is_config: True` 플래그를 활용하여:
- 다른 메인 레포가 있으면: 설정 레포를 매칭 입력에서 제외
- 설정 레포만 있으면: 매칭 결과에 안내 메시지 표시

---

## 3. 구현 설계

### 3-1. MOD_PLATFORM_SIGNATURES

```python
import re

# profile_builder.py
MOD_PLATFORM_SIGNATURES: dict[str, dict] = {
    "EDOPro 카드 스크립트": {
        "regex_patterns": [r"^c\d{8}\.lua$"],  # 파일 basename에 대해 정규식
        "min_pattern_count": 5,
        "supporting_dirs": ["script/", "scripts/"],
        "min_supporting": 0,
        "domain": "게임 개발",
        "label": "EDOPro 카드 스크립팅",
        "mod_context": True,
    },
    "Garry's Mod": {
        "required_dirs": ["gamemodes/"],
        "supporting_dirs": ["entities/", "lua/"],
        "min_supporting": 1,
        "domain": "게임 개발",
        "label": "Garry's Mod 게임모드 개발",
        "mod_context": True,
    },
    "Factorio 모드": {
        "required_files_basename": ["info.json"],
        "supporting_files_basename": ["control.lua", "data.lua", "data-final-fixes.lua"],
        "min_supporting": 1,
        "domain": "게임 개발",
        "label": "Factorio 모드 개발",
        "mod_context": True,
    },
    "Minecraft 플러그인": {
        "required_files_basename": ["plugin.yml"],
        "supporting_files_basename": ["paper-plugin.yml", "bungee.yml"],
        "min_supporting": 0,
        "domain": "게임 개발",
        "label": "Minecraft 플러그인 개발",
        "mod_context": True,
    },
    "Stardew Valley (SMAPI)": {
        "required_files_basename": ["manifest.json"],
        "supporting_files_endswith": [".cs"],
        "min_supporting": 1,
        "domain": "게임 개발",
        "label": "Stardew Valley 모드 개발",
        "mod_context": True,
    },
    "WoW 애드온": {
        "regex_patterns": [r"\.toc$"],
        "min_pattern_count": 1,
        "supporting_files_endswith": [".lua"],
        "min_supporting": 1,
        "domain": "게임 개발",
        "label": "WoW 애드온 개발",
        "mod_context": True,
        "is_hobby": True,  # 직무 시그널 약함
    },
}
```

### 3-2. 감지 함수 (정규식 패턴 지원)

```python
def detect_mod_platform(tree_data: dict) -> dict | None:
    """
    모드/플러그인 플랫폼 감지. 첫 번째 매칭 환경 반환.
    """
    if not tree_data or "tree" not in tree_data:
        return None

    paths = [item["path"].lower().replace("\\", "/") for item in tree_data["tree"]]
    basenames = [p.rsplit("/", 1)[-1] for p in paths]

    for name, sig in MOD_PLATFORM_SIGNATURES.items():
        if not _matches_mod_signature(sig, paths, basenames):
            continue
        return {
            "name": name,
            "domain": sig.get("domain"),
            "label": sig.get("label"),
            "mod_context": sig.get("mod_context", True),
            "is_hobby": sig.get("is_hobby", False),
        }
    return None


def _matches_mod_signature(sig, paths, basenames) -> bool:
    """모드 플랫폼 시그너처 매칭 (정규식 + 기존 키 지원)."""

    # required_dirs
    if "required_dirs" in sig:
        for d in sig["required_dirs"]:
            if not any(d.lower() in p for p in paths):
                return False

    # required_files_basename
    if "required_files_basename" in sig:
        for f in sig["required_files_basename"]:
            if f.lower() not in basenames:
                return False

    # regex_patterns: basename에 대해 정규식 매칭, min_pattern_count 이상
    if "regex_patterns" in sig:
        compiled = [re.compile(p) for p in sig["regex_patterns"]]
        match_count = sum(
            1 for b in basenames
            for cp in compiled
            if cp.search(b)
        )
        if match_count < sig.get("min_pattern_count", 1):
            return False

    # supporting_dirs / supporting_files_basename / supporting_files_endswith
    support_count = 0
    for d in sig.get("supporting_dirs", []):
        if any(d.lower() in p for p in paths):
            support_count += 1
    for f in sig.get("supporting_files_basename", []):
        if f.lower() in basenames:
            support_count += 1
    for f in sig.get("supporting_files_endswith", []):
        if any(p.endswith(f.lower()) for p in paths):
            support_count += 1

    if support_count < sig.get("min_supporting", 0):
        return False

    return True
```

### 3-3. 호출 순서 통합

`evaluate_repository()`에서 감지 우선순위:

```python
# 1. 게임 엔진 (Unity, Unreal, Godot, Flutter) — v5.4
engine = profile_builder.detect_engine_signatures(tree_data)

# 2. 모드 플랫폼 — v5.7 신규
mod_platform = profile_builder.detect_mod_platform(tree_data)

# 3. Lua 호스트 환경 — v5.6
sub_host = None
if any(l == "Lua" for l, _ in lang_category["sub"]):
    sub_host = profile_builder.detect_lua_host(tree_data)

# 우선순위: 엔진 > 모드 플랫폼 > Lua 호스트
# 단, 엔진이 감지되어도 모드 플랫폼이 동시 감지되면 둘 다 표기
```

엔진과 모드 플랫폼이 동시에 감지되는 경우는 드물지만, Stardew Valley 모드(C# + SMAPI)처럼 가능성이 있음. 이 경우 둘 다 표기하는 게 정확함.

---

## 4. 설정 프로젝트의 매칭 제외 처리

### 4-1. per-repo 플래그 전파

`evaluate_repository()`에서 호스트 추론 결과의 `is_config`를 결과 dict에 포함:

```python
return {
    ...
    "sub_language_host": sub_host,
    "is_config_repo": bool(sub_host and sub_host.get("is_config")),
}
```

### 4-2. 매칭 입력 필터링

`extract_applicant_profile()`에서 매칭용 프로필 생성 시:

```python
# is_config_repo가 True인 레포는 매칭 입력에서 제외
non_config_results = [r for r in valid_results if not r.get("is_config_repo")]

if non_config_results:
    # 일반 레포가 있으면 그 결과만으로 프로필 생성
    profile_for_matching = profile_builder.build_profile_text({
        "language_category": _merge_lang_categories(non_config_results),
        ...
    })
else:
    # 모든 레포가 설정 프로젝트인 경우: 매칭은 시도하되 결과 신뢰도 경고
    profile_for_matching = profile_builder.build_profile_text({
        "language_category": _merge_lang_categories(valid_results),
        ...
    })
    warnings.append(
        "분석된 레포지토리가 모두 에디터 설정/취미 프로젝트입니다. "
        "직무 매칭 결과의 신뢰도가 낮을 수 있습니다. "
        "주력 프로젝트(웹/게임/AI 등)를 추가하시기 바랍니다."
    )
```

### 4-3. per_repo 출력에 분류 표시

리포트의 지원자 요약에서 각 레포의 분류를 명시:

```
[지원자 요약]
  분석 레포 수: 3개
    - my-portfolio (메인): 게임 개발
    - my-website (메인): 웹 프론트엔드
    - nvim-config (설정/제외): Neovim 설정 — 매칭 입력 제외됨
```

사용자가 어떤 레포가 어떻게 처리됐는지 투명하게 볼 수 있도록.

---

## 5. 진단 메시지 추가

### 5-1. 모드 개발 프로젝트

```python
# portfolio_diagnosis.py 또는 run_git2value 출력 블록
def mod_context_message(mod_platform: dict) -> str:
    name = mod_platform["name"]
    is_hobby = mod_platform.get("is_hobby", False)

    if is_hobby:
        return (
            f"{name} 프로젝트로 분류되었습니다. "
            f"직무 매칭에 활용되나, 채용 시장에서 직접 매칭되는 공고는 적습니다. "
            f"주력 프로젝트로는 게임 엔진 기반 자체 게임 개발을 권장합니다."
        )

    return (
        f"{name} 프로젝트로 분류되었습니다. "
        f"게임 분야에 대한 깊은 이해와 스크립팅 능력을 보여주는 포트폴리오입니다. "
        f"채용 시 게임 클라이언트 공고와 매칭되며, 엔진 기반 자체 게임 프로젝트를 "
        f"함께 보유하면 매칭 정확도가 더 올라갑니다."
    )
```

### 5-2. 환경 미상 Lua 프로젝트 (v5.6에서 호스트 감지 실패)

```python
def lua_unknown_host_message() -> str:
    return (
        "Lua 프로젝트의 사용 환경(Roblox, Love2D, 게임 모드 등)이 감지되지 않았습니다. "
        "README에 사용 플랫폼을 명시하면 매칭 정확도가 올라갑니다."
    )
```

### 5-3. 설정 프로젝트

```python
def config_repo_message(host_name: str) -> str:
    return (
        f"{host_name} 프로젝트로 분류되었습니다. "
        f"에디터/도구 설정은 직무 매칭에 활용되지 않으며, 포트폴리오에서는 보조 역할입니다. "
        f"주력 프로젝트(웹/게임/AI 등)를 추가하시기 바랍니다."
    )
```

이 메시지들은 모듈 A 출력 직전에 별도 블록으로 표시:

```
------------------------------------------------------------
[프로젝트 분류 안내]
------------------------------------------------------------
  · my-edopro-cards: EDOPro 카드 스크립트
    {mod_context_message}

  · nvim-config: Neovim 설정 (매칭 제외)
    {config_repo_message}
```

---

## 6. 예상 결과

### 6-1. EDOPro 카드 스크립트 단독 레포

```
입력: Lua 100%, c12345678.lua, c87654321.lua... 다수
mod_platform: {"name": "EDOPro 카드 스크립트", "domain": "게임 개발", "label": "EDOPro 카드 스크립팅", "mod_context": True}
sub_host: None (모드 플랫폼이 우선)

프로필:
"EDOPro 카드 스크립팅."
도메인: "게임 개발" → 게임 클라이언트 공고 매칭

진단 안내:
"EDOPro 카드 스크립트 프로젝트로 분류되었습니다.
 게임 분야에 대한 깊은 이해와 스크립팅 능력을 보여주는 포트폴리오입니다.
 채용 시 게임 클라이언트 공고와 매칭되며..."
```

### 6-2. WoW 애드온 (취미)

```
mod_platform: {"is_hobby": True, ...}

진단 안내:
"WoW 애드온 프로젝트로 분류되었습니다.
 직무 매칭에 활용되나, 채용 시장에서 직접 매칭되는 공고는 적습니다.
 주력 프로젝트로는 게임 엔진 기반 자체 게임 개발을 권장합니다."
```

### 6-3. 메인 레포 + Neovim 설정 레포 동시 입력

```
레포 1: my-portfolio (Python + 백엔드) → 매칭에 포함
레포 2: nvim-config (is_config_repo=True) → 매칭에서 제외

프로필 (레포 1만 반영):
"Python (90%) 기반 서버/백엔드 경험. FastAPI 활용 경험..."

지원자 요약:
"분석 레포 수: 2개 (매칭 사용: 1개, 설정/취미: 1개)
   - my-portfolio: 서버/백엔드
   - nvim-config: Neovim 설정 (매칭 제외됨)"
```

### 6-4. Neovim 설정만 단독 입력

```
경고:
"분석된 레포지토리가 모두 에디터 설정/취미 프로젝트입니다.
 직무 매칭 결과의 신뢰도가 낮을 수 있습니다."

매칭은 일단 수행하되 결과에 신뢰도 경고 동반.
```

---

## 7. 구현 우선순위

| 순위 | 작업 | 공수 |
|---|---|---|
| 1 | `MOD_PLATFORM_SIGNATURES` 사전 정의 | 30분 |
| 2 | `detect_mod_platform()` + 정규식 패턴 매칭 지원 | 1시간 |
| 3 | `evaluate_repository()`에 모드 플랫폼 감지 통합 | 30분 |
| 4 | `is_config_repo` 플래그 전파 + 매칭 입력 필터링 | 1시간 |
| 5 | per_repo 분류 표시 + 신뢰도 경고 | 30분 |
| 6 | 모드/취미/설정 진단 메시지 출력 블록 | 1시간 |
| 7 | 테스트: EDOPro 또는 유사 모드 레포 | 30분 |
| 8 | 테스트: 메인 + 설정 레포 조합 | 30분 |
| 9 | 퇴행 테스트: 기존 4종 레포 | 30분 |

총 약 6시간.

---

## 8. 리스크

| 리스크 | 가능성 | 대응 |
|---|---|---|
| 정규식 매칭 비용 (대형 레포에서 수천 파일) | 낮음 | basename에 대해서만 매칭, 컴파일된 정규식 재사용 |
| Stardew Valley(C#)와 일반 .cs 프로젝트 혼동 | 낮음 | manifest.json 필수 요구로 구분 |
| EDOPro 외 다른 카드 게임 시뮬레이터의 비슷한 패턴 | 낮음 | 첫 매칭 후 종료, 다른 카드 게임은 추후 추가 |
| `is_config_repo` 플래그가 전파되지 않아 매칭 제외 누락 | 중간 | 단위 테스트로 sub_host와 is_config_repo의 매핑 검증 |
| 모든 레포가 설정인 경우 매칭이 무의미 | 수용 | 경고는 표시하되 매칭은 수행 (사용자 판단에 맡김) |
| mod_context와 일반 게임 개발의 매칭 결과 차이 미미 | 수용 | 진단 메시지로 사용자 인지 유도 |

---

## 9. v5.6과의 의존 관계

이 계획은 v5.6의 다음 항목에 의존:

- `LUA_HOST_SIGNATURES`의 `is_config: True` 플래그
- `language_category` (메인/서브 분리 결과)
- `sub_language_host` 필드

v5.6 적용 후 v5.7을 진행하는 순서가 자연스러움.

---

## 10. 향후 확장 여지

본 계획에서 처리하지 않지만 확장 가능한 항목:

| 항목 | 비고 |
|---|---|
| Skyrim/Fallout (Papyrus) | Papyrus 언어 자체가 GitHub Linguist에 미흡, 별도 처리 필요 |
| OBS 플러그인 | Lua/Python 모두 가능, 시그너처 모호 |
| VS Code 익스텐션 | package.json에 vscode 의존성 — 의존성 파싱으로 추후 추가 가능 |
| Discord 봇 | 직무 카테고리 모호 — 일반 백엔드로 처리하는 것이 적절할 수 있음 |
| 모드 플랫폼 진단 가산점 | mod_context가 있으면 게임 도메인 점수 보정 (현재는 미적용) |

---

*Git2Value — 모드 플랫폼 감지 및 설정 프로젝트 처리 계획 v5.7 — 2026.04.27*
