# Git2Value — 언어 분류 체계 및 호스트 환경 추론 계획

> 작성일: 2026.04.27 | 대상 버전: v5.5 → v5.6
> 발견 계기: Lua 등 서브 언어 처리 피드백 — 단독으로 직무를 결정하지 않는 언어들의 표현 방식 부재

---

## 1. 문제 정의

### 1-1. 현재 언어 처리 방식

`top_languages`는 LOC 비율로만 산출되어 프로필 텍스트에 그대로 노출됨:

```
"Lua (80%), C++ (20%) 기반 게임 개발 경험"
```

이 표현은 잘못되었음. 사용자는 "Lua 개발자"가 아니라 **"Lua를 사용하는 게임 클라이언트 개발자"** 또는 특정 플랫폼 개발자임. 채용 시장에 "Lua 개발자" 공고는 거의 없음.

### 1-2. 동일 패턴이 적용되는 다른 서브 언어

| 서브 언어 | 직무 시장에서의 의미 |
|---|---|
| Lua | 게임/인프라/임베디드 (호스트 의존) |
| Shell/Bash | 자체 직무 없음, DevOps 보조 |
| CSS/HTML | 자체 직무는 웹퍼블리셔 한정 |
| GLSL/HLSL | 그래픽스 엔지니어 시그널 |
| Dockerfile | DevOps 시그널 |
| Makefile | 빌드 시스템 시그널 |
| Vim script | 직무 거의 없음 |

이런 언어들이 메인 언어와 동일한 "기반 ... 경험" 형식으로 표기되면, FAISS 임베딩이 잘못된 방향으로 끌려감.

### 1-3. Lua 단독 레포의 환경 모호성

Lua는 거의 항상 호스트 환경에 임베딩되는 스크립팅 언어임. 단순히 "Lua 비율이 높다"는 정보만으로는 이 사람이 게임 개발자인지 인프라 엔지니어인지 임베디드 개발자인지 알 수 없음.

---

## 2. 해결 방향

### 2-1. 언어를 메인/서브로 분류

언어를 **메인 언어**(자체 직무 카테고리를 가짐)와 **서브 언어**(보조 역할)로 분리하고, 프로필 텍스트에서 다르게 표기.

```
변경 전: "C++ (70%), Lua (25%) 기반 게임 개발 경험"
변경 후: "C++ (70%) 기반 게임 개발 경험. Lua 스크립팅 활용."
```

### 2-2. Lua 호스트 환경 추론

Lua가 감지되면 파일/디렉토리 시그너처로 호스트 환경(Roblox, Love2D, OpenResty 등)을 추론하여 직무 카테고리에 반영.

---

## 3. 구현 설계

### 3-1. 언어 분류 사전

```python
# profile_builder.py 또는 신규 lang_classifier.py

# 자체 직무를 가지는 메인 언어 (LOC 5% 이상이면 프로필 메인 라벨에 포함)
MAIN_LANGUAGES: set[str] = {
    "Python", "Java", "JavaScript", "TypeScript",
    "C#", "C++", "C", "Go", "Rust",
    "Kotlin", "Swift", "Ruby", "PHP", "Dart",
    "Scala", "Elixir",
}

# 서브 언어: 단독으로는 직무 시그널 약함, 메인 언어와 결합 시 보조 역할
SUB_LANGUAGE_SIGNALS: dict[str, dict] = {
    "Lua": {
        "framework_label": None,  # 환경 추론 결과로 별도 처리
        "alone_handler": "lua_host",  # 호스트 추론 시도
        "with_main_label": "Lua 스크립팅",
    },
    "Shell": {
        "framework_label": "셸 스크립팅",
        "alone_handler": "default_devops",
        "with_main_label": "셸 스크립팅",
    },
    "GLSL": {
        "framework_label": "셰이더 프로그래밍",
        "alone_handler": "default_graphics",
        "with_main_label": "셰이더 프로그래밍",
    },
    "HLSL": {
        "framework_label": "셰이더 프로그래밍",
        "alone_handler": "default_graphics",
        "with_main_label": "셰이더 프로그래밍",
    },
    "CSS": {
        "framework_label": None,  # 메인이 JS/TS이면 자연스럽게 묶임
        "alone_handler": "default_publisher",
        "with_main_label": None,  # 별도 표기 안 함
    },
    "HTML": {
        "framework_label": None,
        "alone_handler": "default_publisher",
        "with_main_label": None,
    },
    "Dockerfile": {
        "framework_label": "Docker",
        "alone_handler": None,
        "with_main_label": None,  # frameworks에서 별도 감지됨
    },
    "Makefile": {
        "framework_label": None,
        "alone_handler": None,
        "with_main_label": None,
    },
    "Vim Script": {
        "framework_label": None,
        "alone_handler": "default_hobby",
        "with_main_label": None,
    },
    "SQL": {
        "framework_label": None,
        "alone_handler": "default_dba",
        "with_main_label": "SQL/DB",
    },
}
```

### 3-2. 언어 카테고라이저 함수

```python
def categorize_languages(lang_stats: dict[str, int]) -> dict:
    """
    언어를 main / sub / trivial로 분류.
    LOC 비율 기준이 아닌 직무 시그널 강도 기준.
    """
    total = sum(lang_stats.values())
    if total == 0:
        return {"main": [], "sub": [], "trivial": []}

    main: list[tuple[str, float]] = []
    sub: list[tuple[str, float]] = []
    trivial: list[tuple[str, float]] = []

    for lang, loc in sorted(lang_stats.items(), key=lambda x: -x[1]):
        pct = loc / total * 100

        if lang in MAIN_LANGUAGES and pct >= 5:
            main.append((lang, pct))
        elif lang in SUB_LANGUAGE_SIGNALS:
            sub.append((lang, pct))
        elif pct >= 5:
            # 알려지지 않은 언어지만 비중 있음 → 메인 후보
            main.append((lang, pct))
        else:
            trivial.append((lang, pct))

    return {"main": main, "sub": sub, "trivial": trivial}
```

### 3-3. Lua 호스트 환경 시그너처

```python
# profile_builder.py
LUA_HOST_SIGNATURES: dict[str, dict] = {
    "Roblox": {
        "file_patterns_endswith": [".rbxl", ".rbxlx", ".rbxm", ".rbxmx"],
        "min_count": 1,
        "domain": "게임 개발",
        "label": "Roblox 플랫폼 개발",
    },
    "Love2D": {
        "required_files_root": ["main.lua", "conf.lua"],
        "domain": "게임 개발",
        "label": "Love2D 게임 개발",
    },
    "Defold": {
        "required_files": ["game.project"],
        "supporting_files_endswith": [".script", ".gui_script", ".collection"],
        "min_supporting": 1,
        "domain": "게임 개발",
        "label": "Defold 게임 개발",
    },
    "Solar2D/Corona": {
        "required_files_root": ["main.lua", "build.settings"],
        "domain": "모바일 앱",
        "label": "Solar2D 모바일 게임 개발",
    },
    "Cocos2d-x Lua": {
        "required_files_endswith": ["cocos.lua"],
        "supporting_files": ["project.json"],
        "min_supporting": 0,
        "domain": "게임 개발",
        "label": "Cocos2d-x Lua 게임 개발",
    },
    "OpenResty/Nginx-Lua": {
        "required_any_basename": ["nginx.conf", "openresty.conf"],
        "supporting_dirs": ["lua/"],
        "min_supporting": 0,
        "domain": "DevOps/인프라",
        "label": "OpenResty/Nginx 모듈 개발",
    },
    "NodeMCU/임베디드 Lua": {
        "required_files_basename": ["init.lua"],
        "supporting_files_basename": ["wifi.lua", "uart.lua", "spi.lua", "i2c.lua"],
        "min_supporting": 1,
        "domain": "HW/임베디드",
        "label": "NodeMCU/임베디드 Lua 개발",
    },
    "Neovim 설정": {
        "required_files_root": ["init.lua"],
        "supporting_dirs": ["lua/"],
        "min_supporting": 1,
        "domain": None,  # 직무 시그널 없음
        "label": "Neovim 에디터 설정",
        "is_config": True,  # v5.7에서 매칭 제외 처리
    },
}


def detect_lua_host(tree_data: dict) -> dict | None:
    """
    Lua 호스트 환경 감지. 첫 번째 매칭되는 환경 반환.
    Returns: {"name", "domain", "label", "is_config"} or None
    """
    if not tree_data or "tree" not in tree_data:
        return None

    paths = [item["path"].lower().replace("\\", "/") for item in tree_data["tree"]]
    basenames = [p.rsplit("/", 1)[-1] for p in paths]
    root_files = [p for p in paths if "/" not in p]

    for name, sig in LUA_HOST_SIGNATURES.items():
        if not _matches_lua_host_signature(sig, paths, basenames, root_files):
            continue
        return {
            "name": name,
            "domain": sig.get("domain"),
            "label": sig.get("label"),
            "is_config": sig.get("is_config", False),
        }
    return None


def _matches_lua_host_signature(sig, paths, basenames, root_files) -> bool:
    """단일 시그너처 매칭. 헬퍼 — 각 키 종류별 체크."""
    # required_files_root: 루트에 있어야 함
    if "required_files_root" in sig:
        for f in sig["required_files_root"]:
            if f.lower() not in root_files:
                return False

    # required_any_basename: basename 중 하나라도
    if "required_any_basename" in sig:
        if not any(b in sig["required_any_basename"] for b in basenames):
            return False

    # required_files_basename: basename에 모두 있어야
    if "required_files_basename" in sig:
        for f in sig["required_files_basename"]:
            if f.lower() not in basenames:
                return False

    # required_files: 경로 어디든 있어야
    if "required_files" in sig:
        for f in sig["required_files"]:
            if not any(f.lower() in p for p in paths):
                return False

    # required_files_endswith: 경로 끝
    if "required_files_endswith" in sig:
        for f in sig["required_files_endswith"]:
            if not any(p.endswith(f.lower()) for p in paths):
                return False

    # file_patterns_endswith + min_count
    if "file_patterns_endswith" in sig:
        cnt = sum(1 for p in paths
                  for pat in sig["file_patterns_endswith"]
                  if p.endswith(pat.lower()))
        if cnt < sig.get("min_count", 1):
            return False

    # supporting 카운트
    support_count = 0
    for f in sig.get("supporting_files", []):
        if any(f.lower() in p for p in paths):
            support_count += 1
    for f in sig.get("supporting_files_endswith", []):
        if any(p.endswith(f.lower()) for p in paths):
            support_count += 1
    for f in sig.get("supporting_files_basename", []):
        if f.lower() in basenames:
            support_count += 1
    for d in sig.get("supporting_dirs", []):
        if any(d.lower() in p for p in paths):
            support_count += 1

    if support_count < sig.get("min_supporting", 0):
        return False

    return True
```

### 3-4. 다른 서브 언어 단독 처리

Lua 외에도 단독 서브 언어 레포가 있을 때의 기본 분류:

```python
DEFAULT_ALONE_DOMAINS: dict[str, str] = {
    "default_devops": "DevOps/인프라",   # Shell 단독
    "default_graphics": "그래픽스",       # GLSL 단독 (드물지만)
    "default_publisher": "웹 프론트엔드",  # CSS/HTML 단독
    "default_dba": "DBA/데이터",          # SQL 단독
    "default_hobby": None,                 # Vim Script 등 직무 시그널 없음
}


def resolve_sub_language_alone(lang: str, tree_data: dict | None = None) -> dict | None:
    """
    서브 언어가 단독으로 있을 때의 환경/도메인 추론.
    Lua는 호스트 추론, 나머지는 기본 도메인.
    """
    sig = SUB_LANGUAGE_SIGNALS.get(lang)
    if not sig:
        return None

    handler = sig.get("alone_handler")
    if handler == "lua_host" and tree_data:
        return detect_lua_host(tree_data)
    if handler in DEFAULT_ALONE_DOMAINS:
        domain = DEFAULT_ALONE_DOMAINS[handler]
        return {
            "name": f"{lang} 단독",
            "domain": domain,
            "label": f"{lang} 기반 프로젝트",
            "is_config": handler == "default_hobby",
        }
    return None
```

---

## 4. build_profile_text() 재구성

```python
def build_profile_text(extracted_data: dict) -> str:
    parts: list[str] = []

    lang_cat = extracted_data.get("language_category") or {}
    main_langs = lang_cat.get("main", [])
    sub_langs = lang_cat.get("sub", [])
    sub_host = extracted_data.get("sub_language_host")  # Lua 호스트 등

    domains = extracted_data.get("detected_domains") or []
    primary_domain = domains[0] if domains else None

    # 1. 메인 언어 + 도메인 처리
    if main_langs:
        main_str = ", ".join(f"{l} ({pct:.0f}%)" for l, pct in main_langs[:3])
        if primary_domain:
            parts.append(f"{main_str} 기반 {primary_domain} 경험")
        else:
            parts.append(f"{main_str} 기반 개발 경험")
    elif sub_host and sub_host.get("domain"):
        # 메인 언어 없이 서브 언어 단독: 호스트 기반 기술
        parts.append(f"{sub_host['label']}")

    # 2. 프레임워크
    fw = extracted_data.get("frameworks") or []
    if fw:
        parts.append(f"{', '.join(fw)} 활용 경험")

    # 3. 서브 언어 (메인이 있을 때 보조 역할 표기)
    if main_langs and sub_langs:
        sub_descriptions: list[str] = []
        for lang, pct in sub_langs:
            sig = SUB_LANGUAGE_SIGNALS.get(lang) or {}
            label = sig.get("with_main_label")
            if label:
                sub_descriptions.append(label)
        if sub_descriptions:
            parts.append(f"{', '.join(sub_descriptions)} 활용")

    # 4. 호스트 환경 (Lua 단독이고 환경 감지된 경우, 메인이 있어도 추가)
    if sub_host and sub_host.get("label") and main_langs:
        # 메인이 있을 때는 환경 보조 정보로
        parts.append(f"{sub_host['label']} 환경")

    # 5. CI/CD, 테스트, 배포
    if extracted_data.get("has_cicd"):
        parts.append("CI/CD 파이프라인 구축 경험")
    if extracted_data.get("has_tests"):
        parts.append("테스트 코드 작성 경험")
    if extracted_data.get("has_deployment"):
        parts.append("배포 환경 구성 경험")

    # 6. README 키워드 (기존 v5.3 로직 유지)
    readme_summary = extracted_data.get("readme_summary") or ""
    if readme_summary and len(readme_summary) >= 200:
        readme_kw = extract_readme_keywords(readme_summary)
        if readme_kw:
            parts.append(readme_kw)

    if not parts:
        return "GitHub 저장소 기반 개발 경험 (상세 메타데이터 부족)."
    return ". ".join(parts) + "."
```

---

## 5. 데이터 흐름 변경

`github_extractor.evaluate_repository()`에서 호출 추가:

```python
# 언어 분류
lang_category = profile_builder.categorize_languages(lang_stats)

# 서브 언어 호스트 추론 (Lua 단독 또는 메인+Lua)
sub_host = None
if any(l == "Lua" for l, _ in lang_category["sub"]):
    sub_host = profile_builder.detect_lua_host(tree_data)

# 기존 결과 dict에 추가
return {
    ...
    "language_category": lang_category,
    "sub_language_host": sub_host,
}
```

`extract_applicant_profile()`에서 병합:

```python
# 레포별 lang_category를 합산하여 전체 카테고리 산출
# (단순화: 첫 번째 valid 결과의 sub_host를 사용하거나, 모든 결과 중 하나라도 있으면 채택)
profile_for_matching = profile_builder.build_profile_text({
    ...
    "language_category": merged_lang_category,
    "sub_language_host": first_detected_sub_host,
})
```

---

## 6. 도메인 분기: detected_domains 보강

`detect_lua_host()` 결과의 `domain`이 있으면, `merged_detected_domains`에 우선 합산:

```python
# extract_applicant_profile()
if sub_host and sub_host.get("domain"):
    # 호스트 기반 도메인을 기존 도메인 감지 결과보다 앞에 배치
    merged_domains.insert(0, sub_host["domain"])
    merged_domains = list(dict.fromkeys(merged_domains))  # dedup
```

이러면 Roblox 단독 레포가 "게임 개발"로 잡혀 리랭킹에도 정상 적용됨.

---

## 7. 예상 결과

### 7-1. C++ Unreal 게임 + Lua 스크립팅

```
입력: C++ 70%, Lua 25%, others 5%
lang_category: main=[C++], sub=[Lua]
sub_host: None (Unreal은 ENGINE_SIGNATURES에서 별도 감지)

프로필:
"C++ (70%) 기반 게임 개발 경험. Unreal Engine 활용 경험.
 Lua 스크립팅 활용. CI/CD 파이프라인 구축 경험."
```

### 7-2. Roblox 단독 (Lua 95%)

```
입력: Lua 95%, others 5%
lang_category: main=[], sub=[Lua]
sub_host: {"name": "Roblox", "domain": "게임 개발", "label": "Roblox 플랫폼 개발"}

프로필:
"Roblox 플랫폼 개발. 게임, 캐릭터 관련 프로젝트."

도메인 감지: "게임 개발" → 리랭킹 정상 적용 → 게임 클라이언트 공고 매칭
```

### 7-3. NodeMCU 임베디드 Lua

```
입력: Lua 100%
sub_host: {"name": "NodeMCU/임베디드 Lua", "domain": "HW/임베디드", ...}

프로필:
"NodeMCU/임베디드 Lua 개발."

도메인: "HW/임베디드" → 임베디드 공고 매칭
```

### 7-4. Python 백엔드 + Shell 보조

```
입력: Python 90%, Shell 10%
lang_category: main=[Python], sub=[Shell]

프로필:
"Python (90%) 기반 서버/백엔드 경험. FastAPI 활용 경험.
 셸 스크립팅 활용. CI/CD 파이프라인 구축 경험."
```

### 7-5. CSS/HTML 단독 (정적 사이트)

```
입력: CSS 60%, HTML 40%
lang_category: main=[], sub=[CSS, HTML]
sub_host: {"name": "CSS 단독", "domain": "웹 프론트엔드", ...}
(handler="default_publisher")

프로필:
"CSS 기반 프로젝트."
도메인: "웹 프론트엔드" → 웹퍼블리셔 공고 매칭
```

---

## 8. 구현 우선순위

| 순위 | 작업 | 공수 |
|---|---|---|
| 1 | `MAIN_LANGUAGES` / `SUB_LANGUAGE_SIGNALS` 사전 정의 | 30분 |
| 2 | `categorize_languages()` 구현 | 30분 |
| 3 | `LUA_HOST_SIGNATURES` 정의 + `detect_lua_host()` 구현 | 1시간 |
| 4 | `resolve_sub_language_alone()` 및 기본 도메인 처리 | 30분 |
| 5 | `build_profile_text()` 재구성 (메인/서브 분리) | 1시간 |
| 6 | `evaluate_repository()` 및 `extract_applicant_profile()` 통합 | 30분 |
| 7 | 테스트: Roblox 또는 Lua 임베딩 레포 1개 | 30분 |
| 8 | 퇴행 테스트: 기존 메인 언어 레포 (TCG, DeepSentinel, AI 서버, Unity 대기업) | 45분 |

총 약 5시간. 메인/서브 분리 자체가 다른 서브 언어(Shell, GLSL 등)도 자동으로 정리하기 때문에 넓은 효과가 있음.

---

## 9. 리스크

| 리스크 | 가능성 | 대응 |
|---|---|---|
| Lua 호스트 시그너처 오탐 (init.lua만 있는 일반 Lua가 Neovim으로 잡힘) | 중간 | `lua/` 디렉토리 동시 요구로 구분. min_supporting 활용 |
| 메인 언어 5% 임계값이 부적절한 케이스 | 낮음 | 값은 후속 튜닝 가능. 초기엔 5% 유지 |
| 다중 레포에서 lang_category 병합 로직 단순화로 인한 부정확 | 중간 | 첫 번째 sub_host 채택 방식. 향후 다중 호스트 처리 필요 시 개선 |
| 메인 없이 서브만 있는 레포의 프로필이 너무 짧아짐 | 낮음 | sub_host의 label이 "Roblox 플랫폼 개발" 같이 충분한 정보 제공 |
| CSS/HTML 단독을 웹퍼블리셔로 매칭하지만 공고 수 적음 | 수용 | 매칭 자체는 시도하되 결과가 빈약할 수 있음을 인지 |

---

## 10. v5.7로 미루는 항목

다음 항목들은 별도 계획(`Mod_Platform_Plan.md`)에서 처리:

- 모드 플랫폼 감지 (EDOPro, Garry's Mod, Factorio 등)
- 파일명 정규식 패턴 매칭 (`c\d{8}.lua` 등)
- 모드 개발 / 설정 프로젝트별 진단 메시지
- `is_config: True` 레포의 매칭 입력 제외 처리

v5.6은 **언어 처리의 구조적 변경**에 집중하고, v5.7은 **특수 카테고리 추가**에 집중하는 분할.

---

*Git2Value — 언어 분류 체계 및 호스트 환경 추론 계획 v5.6 — 2026.04.27*
