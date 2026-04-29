"""
Git2Value v5.8 — 프로필 텍스트 변환 레이어 (룰베이스).
JD 임베딩과의 문체 정합을 위해 구조화 데이터를 공고형 문장으로 변환합니다.
v5.3: README는 키워드 압축만(노이즈 완화), 키워드 없을 때 원문 폴백 없음.
      도메인·LOC 맥락 문장은 매칭용 프로필에서 제거 — 순서 보정은 run_git2value 도메인 리랭킹.
v5.4: tree 시그니처 기반 엔진 감지(detect_engine_signatures) — Unity 등 의존성 파일 없이 특정.
v5.5: Jupyter/ML 실험, Kubernetes/IaC 시그너처 추가.
v5.6: 언어 메인/서브 분류(categorize_languages), Lua 호스트 환경 추론(detect_lua_host),
      서브 언어 단독 처리(resolve_sub_language_alone), build_profile_text 재구성.
v5.7: 모드/플러그인 플랫폼 감지(MOD_PLATFORM_SIGNATURES, detect_mod_platform) —
      EDOPro·Garry's Mod·Factorio·Minecraft·Stardew Valley·WoW 애드온.
      정규식 파일명 패턴 매칭(_matches_mod_signature) 지원.
v5.8: 시그너처 오탐 강화 — 새 키 5종(required_any_dirs, file_count_endswith,
      exclude_if_basename_exists, supporting_path_contains, required_files_root) 추가.
      Flutter: required_any_dirs(android/·ios/). Jupyter/ML: file_count_endswith(.ipynb>=3).
      Solar2D/Love2D: 사전 순서 조정 + Love2D exclude_if_basename_exists(build.settings).
      OpenResty: min_supporting 1. Minecraft: supporting_path_contains(Bukkit/Paper/Bungee 경로).
      Stardew Valley: required_files_root로 루트 한정(Unity Packages/ 충돌 해소).
      Neovim: min_supporting 2, lazy-lock.json/packer_compiled.lua 보조 시그너처 추가.
v5.8 (환경 카테고리 확장): ENGINE_SIGNATURES에 신규 8개 카테고리 추가 —
      Expo·React Native(모바일), Hardhat·Foundry(블록체인), Helm Chart(인프라),
      dbt(데이터 엔지니어링), VS Code 확장·Browser Extension(도구 개발).
      manifest 내용 검증 메커니즘(detect_signatures_with_content) 비동기 함수 도입 —
      Expo app.json, VS Code 확장 package.json, 브라우저 확장 manifest.json 내용 키 검증.
      의존성 파싱 확장: package.json(react-native, @expo/cli, hardhat 등),
      requirements.txt(streamlit, gradio, apache-airflow, dbt-core, transformers 등).
      DOMAIN_SIGNALS·DOMAIN_CONTEXT·README_KEYWORDS에 블록체인·빅데이터 엔지니어·도구 개발 추가.
"""
from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Optional, Set, Tuple

# ---------------------------------------------------------------------------
# v5.6: 언어 분류 사전 (메인 / 서브 / 기본 도메인)
# ---------------------------------------------------------------------------

# 자체 직무 카테고리를 가지는 메인 언어 (LOC 5% 이상이면 메인 라벨에 포함)
MAIN_LANGUAGES: Set[str] = {
    "Python", "Java", "JavaScript", "TypeScript",
    "C#", "C++", "C", "Go", "Rust",
    "Kotlin", "Swift", "Ruby", "PHP", "Dart",
    "Scala", "Elixir",
}

# 서브 언어: 단독으로는 직무 시그널 약함, 메인과 결합 시 보조 역할
SUB_LANGUAGE_SIGNALS: Dict[str, Dict] = {
    "Lua": {
        "alone_handler": "lua_host",
        "with_main_label": "Lua 스크립팅",
    },
    "Shell": {
        "alone_handler": "default_devops",
        "with_main_label": "셸 스크립팅",
    },
    "GLSL": {
        "alone_handler": "default_graphics",
        "with_main_label": "셰이더 프로그래밍",
    },
    "HLSL": {
        "alone_handler": "default_graphics",
        "with_main_label": "셰이더 프로그래밍",
    },
    "CSS": {
        "alone_handler": "default_publisher",
        "with_main_label": None,
    },
    "HTML": {
        "alone_handler": "default_publisher",
        "with_main_label": None,
    },
    "Dockerfile": {
        "alone_handler": None,
        "with_main_label": None,
    },
    "Makefile": {
        "alone_handler": None,
        "with_main_label": None,
    },
    "Vim Script": {
        "alone_handler": "default_hobby",
        "with_main_label": None,
    },
    "SQL": {
        "alone_handler": "default_dba",
        "with_main_label": "SQL/DB",
    },
}

# Lua 서브 언어 단독 레포에서 호스트 환경 추론 시그너처 (9종)
LUA_HOST_SIGNATURES: Dict[str, Dict] = {
    "Roblox": {
        "file_patterns_endswith": [".rbxl", ".rbxlx", ".rbxm", ".rbxmx"],
        "min_count": 1,
        "domain": "게임 개발",
        "label": "Roblox 플랫폼 개발",
    },
    "Solar2D/Corona": {
        "required_files_root": ["main.lua", "build.settings"],
        "domain": "모바일 앱",
        "label": "Solar2D 모바일 게임 개발",
    },
    "Love2D": {
        "required_files_root": ["main.lua", "conf.lua"],
        "exclude_if_basename_exists": ["build.settings"],
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
        "supporting_files_endswith": [".lua"],
        "min_supporting": 1,
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
        "supporting_dirs": ["lua/", "plugin/", "after/"],
        "supporting_files_basename": ["lazy-lock.json", "packer_compiled.lua"],
        "min_supporting": 2,
        "domain": None,
        "label": "Neovim 에디터 설정",
        "is_config": True,
    },
}

# 서브 언어 단독 처리 시 기본 도메인 (Lua 외 언어용)
DEFAULT_ALONE_DOMAINS: Dict[str, Optional[str]] = {
    "default_devops":    "DevOps/인프라",
    "default_graphics":  "그래픽스",
    "default_publisher": "웹 프론트엔드",
    "default_dba":       "DBA/데이터",
    "default_hobby":     None,
}

# ---------------------------------------------------------------------------
# v5.7: 모드/플러그인 플랫폼 시그너처 사전
# ---------------------------------------------------------------------------
# 게임 엔진을 직접 만드는 것이 아니라 기존 게임/플랫폼의 모드·플러그인을 개발하는 프로젝트.
# 게임 도메인 시그널로 분류하되, 진단에서 "모드 개발" 맥락을 별도 안내한다.
MOD_PLATFORM_SIGNATURES: Dict[str, Dict] = {
    "EDOPro 카드 스크립트": {
        "regex_patterns": [r"^c\d{8}\.lua$"],
        "min_pattern_count": 5,
        "supporting_dirs": ["script/", "scripts/"],
        "min_supporting": 0,
        "domain": "게임 개발",
        "label": "EDOPro 카드 스크립팅",
        "mod_context": True,
        "is_hobby": False,
    },
    "Garry's Mod": {
        "required_dirs": ["gamemodes/"],
        "supporting_dirs": ["entities/", "lua/"],
        "min_supporting": 1,
        "domain": "게임 개발",
        "label": "Garry's Mod 게임모드 개발",
        "mod_context": True,
        "is_hobby": False,
    },
    "Factorio 모드": {
        "required_files_basename": ["info.json"],
        "supporting_files_basename": ["control.lua", "data.lua", "data-final-fixes.lua"],
        "min_supporting": 1,
        "domain": "게임 개발",
        "label": "Factorio 모드 개발",
        "mod_context": True,
        "is_hobby": False,
    },
    "Minecraft 플러그인": {
        "required_files_basename": ["plugin.yml"],
        "supporting_files_basename": ["paper-plugin.yml", "bungee.yml"],
        "supporting_path_contains": ["org/bukkit/", "io/papermc/", "net/md_5/bungee/"],
        "min_supporting": 1,
        "domain": "게임 개발",
        "label": "Minecraft 플러그인 개발",
        "mod_context": True,
        "is_hobby": False,
    },
    "Stardew Valley (SMAPI)": {
        "required_files_root": ["manifest.json"],
        "supporting_files_endswith": [".cs"],
        "min_supporting": 1,
        "domain": "게임 개발",
        "label": "Stardew Valley 모드 개발",
        "mod_context": True,
        "is_hobby": False,
    },
    "WoW 애드온": {
        "regex_patterns": [r"\.toc$"],
        "min_pattern_count": 1,
        "supporting_files_endswith": [".lua"],
        "min_supporting": 1,
        "domain": "게임 개발",
        "label": "WoW 애드온 개발",
        "mod_context": True,
        "is_hobby": True,
    },
}

# 파일명/폴더명 기반 도메인 시그널 (Plan3 §3-5)
DOMAIN_SIGNALS: Dict[str, List[str]] = {
    "게임 개발": [
        "game", "player", "enemy", "scene", "inventory", "combat",
        "sprite", "level", "quest", "npc", "dungeon", "weapon",
        "gamemanager", "playercontroller", "spawn", "Lua"
    ],
    "웹 프론트엔드": [
        "component", "page", "layout", "header", "footer",
        "navbar", "sidebar", "modal", "hook", "store",
    ],
    "서버/백엔드": [
        "controller", "service", "repository", "middleware",
        "router", "handler", "migration", "schema", "endpoint",
    ],
    "ML/AI": [
        "model", "train", "dataset", "inference", "predict",
        "embedding", "tokenizer", "epoch", "checkpoint",
    ],
    "모바일 앱": [
        "activity", "fragment", "viewmodel", "storyboard",
        "appdelegate", "widget", "screen",
    ],
    "DevOps/인프라": [
        "terraform", "ansible", "helm", "k8s", "pipeline",
        "deploy", "monitoring", "grafana",
    ],
    # v5.8: 신규 도메인 (시그너처 감지 보완용 트리 키워드)
    "블록체인": [
        "contract", "solidity", "hardhat", "foundry", "web3",
        "abi", "bytecode", "truffle", "ethers",
    ],
    "빅데이터 엔지니어": [
        "pipeline", "airflow", "dbt", "etl", "warehouse",
        "spark", "kafka", "datalake", "batch",
    ],
    "도구 개발": [
        "extension", "plugin", "addon", "vscode",
        "manifest", "contributes",
    ],
}

DEPENDENCY_FILENAMES: Set[str] = {
    "package.json",
    "requirements.txt",
    "pyproject.toml",
    "build.gradle",
    "build.gradle.kts",
    "pom.xml",
    "gemfile",
    "go.mod",
    "cargo.toml",
}

# GitHub tree 경로만으로 특정 가능한 엔진/프레임워크 (의존성 파싱이 커버하지 못하는 경우)
ENGINE_SIGNATURES: Dict[str, Dict[str, Any]] = {
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
        "required_any_dirs": ["android/", "ios/"],
        "supporting_files": [],
        "supporting_dirs": ["lib/"],
        "min_supporting": 1,
    },
    "Jupyter/ML 실험": {
        "required_any": [],
        "file_count_endswith": {".ipynb": 3},
        "supporting_files": [],
        "supporting_dirs": ["notebooks/", "experiments/"],
        "min_supporting": 1,
    },
    "Kubernetes/IaC": {
        "required_any": [],
        "supporting_files": [".tf", ".hcl"],
        "supporting_dirs": ["kubernetes/", "k8s/", "helm/", "terraform/"],
        "min_supporting": 2,
    },
    # --- 모바일 ---
    "Expo": {
        # required_files_root + manifest_signature_keywords: app.json 내용에 "expo" 키 필수
        # → detect_signatures_with_content()에서 비동기 처리 (detect_engine_signatures 건너뜀)
        "required_any": [],
        "required_files_root": ["app.json"],
        "manifest_signature_keywords": ["\"expo\""],
        "supporting_files": ["package.json"],
        "supporting_dirs": [],
        "min_supporting": 1,
        "domain": "모바일 앱",
        "label": "Expo (React Native) 모바일 앱 개발",
    },
    "React Native": {
        # android/ 또는 ios/ 디렉토리 존재 + pubspec.yaml 부재(Flutter 배제)
        "required_any": ["package.json"],
        "required_any_dirs": ["android/", "ios/"],
        "exclude_if_basename_exists": ["pubspec.yaml"],
        "supporting_files": ["metro.config.js", "app.js", "app.tsx"],
        "supporting_dirs": [],
        "min_supporting": 1,
        "domain": "모바일 앱",
        "label": "React Native 모바일 앱 개발",
    },
    # --- 블록체인 ---
    "Hardhat (Solidity)": {
        # hardhat.config.js 또는 .ts 존재 (required_any partial match로 처리)
        "required_any": ["hardhat.config"],
        "supporting_dirs": ["contracts/"],
        "supporting_files": [],
        "supporting_files_endswith": [".sol"],
        "min_supporting": 1,
        "domain": "블록체인",
        "label": "Hardhat 기반 Solidity 개발",
    },
    "Foundry (Solidity)": {
        "required_any": ["foundry.toml"],
        "supporting_dirs": ["src/", "test/", "lib/"],
        "supporting_files": [],
        "supporting_files_endswith": [".sol"],
        "min_supporting": 2,
        "domain": "블록체인",
        "label": "Foundry 기반 Solidity 개발",
    },
    # --- 인프라 (Kubernetes/IaC 보완) ---
    "Helm Chart": {
        "required_any": ["chart.yaml"],
        "supporting_dirs": ["templates/"],
        "supporting_files": ["values.yaml"],
        "min_supporting": 1,
        "domain": "DevOps/인프라",
        "label": "Helm Chart 개발",
    },
    # --- 데이터 엔지니어링 ---
    "dbt": {
        "required_any": ["dbt_project.yml"],
        "supporting_dirs": ["models/", "seeds/", "macros/"],
        "supporting_files": [],
        "min_supporting": 1,
        "domain": "빅데이터 엔지니어",
        "label": "dbt 데이터 모델링",
    },
    # --- 도구 개발 (manifest 내용 검증 필요 → detect_signatures_with_content 처리) ---
    "VS Code 확장": {
        "required_any": [],
        "required_files_root": ["package.json"],
        "manifest_signature_keywords": ["vscode", "contributes"],
        "supporting_files": [".vscodeignore"],
        "supporting_dirs": [],
        "min_supporting": 0,
        "domain": "도구 개발",
        "label": "VS Code 확장 개발",
    },
    "Browser Extension": {
        "required_any": [],
        "required_files_root": ["manifest.json"],
        "manifest_signature_keywords": ["manifest_version", "permissions"],
        "supporting_files_endswith": [".js", ".html"],
        "supporting_dirs": [],
        "min_supporting": 1,
        "domain": "도구 개발",
        "label": "브라우저 확장 개발",
    },
}

DEPLOYMENT_PATH_MARKERS: List[str] = [
    "docker-compose",
    "vercel.json",
    "netlify.toml",
    "fly.toml",
    "render.yaml",
    "kubernetes",
    "k8s",
    ".github/workflows",
]

# 도메인별 공고 어휘 템플릿 (참고용; v5.3부터 build_profile_text에는 미삽입)
DOMAIN_CONTEXT: Dict[str, str] = {
    "게임 개발":       "Unity C# 게임 개발, 게임 콘텐츠 구현, 게임 시스템 설계, 게임 밸런싱",
    "웹 프론트엔드":    "웹 프론트엔드 개발, 사용자 인터페이스 구현, 반응형 웹, 웹 서버 개발",
    "서버/백엔드":      "서버 개발, API 설계, 데이터베이스 설계, 데이터베이스 운영",
    "ML/AI":           "머신러닝 모델 개발, 데이터 분석, 모델 학습 및 추론, 데이터 수집",
    "모바일 앱":        "모바일 앱 개발, 네이티브 앱, 크로스플랫폼 개발, 모바일 서버 개발",
    "DevOps/인프라":    "인프라 구축, 배포 자동화, 컨테이너 운영, 인프라 운영",
    # v5.8: 신규 도메인
    "블록체인":         "스마트 컨트랙트 개발, Solidity, 블록체인 DApp, 탈중앙화 프로토콜",
    "빅데이터 엔지니어": "데이터 파이프라인 구축, ETL, 데이터 웨어하우스, 배치 처리",
    "도구 개발":        "개발자 도구 개발, VS Code 확장, 브라우저 확장, 플러그인 개발",
}

# README 원문 전체를 임베딩에 넣을 때 노이즈가 되는 경우를 줄이기 위해 도메인별 키워드만 압축 (v5.1)
README_KEYWORDS: Dict[str, List[str]] = {
    "게임": [
        "게임",
        "game",
        "unity",
        "유니티",
        "unreal",
        "언리얼",
        "tcg",
        "rpg",
        "mmo",
        "fps",
        "moba",
        "캐릭터",
        "던전",
        "퀘스트",
        "인벤토리",
        "sprite",
        "tilemap",
        "physics",
    ],
    "웹": [
        "웹",
        "web",
        "브라우저",
        "SPA",
        "SEO",
        "SSR",
        "반응형",
        "responsive",
        "landing",
    ],
    "서버": [
        "서버",
        "server",
        "API",
        "REST",
        "GraphQL",
        "데이터베이스",
        "database",
        "인증",
        "auth",
        "backend",
        "백엔드",
        "microservice",
        "마이크로서비스",
        "endpoint",
        "middleware",
        "orm",
    ],
    "ML/AI": [
        "학습",
        "training",
        "모델",
        "추론",
        "inference",
        "데이터셋",
        "dataset",
        "파인튜닝",
        "fine-tuning",
        "ai",
        "artificial intelligence",
        "deep learning",
        "딥러닝",
        "machine learning",
        "머신러닝",
        "detection",
        "recognition",
        "classification",
        "yolo",
        "cnn",
        "transformer",
        "resnet",
        "computer vision",
        "영상 분석",
        "객체 탐지",
        "cctv",
        "video analysis",
        "image processing",
        "neural network",
        "신경망",
        "nlp",
        "자연어 처리",
        "natural language",
    ],
    "모바일": [
        "앱",
        "app",
        "모바일",
        "mobile",
        "iOS",
        "안드로이드",
        "android",
    ],
    "인프라": [
        "배포",
        "deploy",
        "컨테이너",
        "container",
        "쿠버네티스",
        "kubernetes",
        "모니터링",
        "monitoring",
        "docker",
        "ci/cd",
        "pipeline",
        "devops",
        "infrastructure",
        "terraform",
        "aws",
        "gcp",
        "azure",
    ],
    # v5.8: 신규 도메인
    "블록체인": [
        "blockchain",
        "블록체인",
        "solidity",
        "smart contract",
        "스마트 컨트랙트",
        "web3",
        "defi",
        "nft",
        "ethereum",
        "evm",
        "hardhat",
        "foundry",
        "truffle",
        "dapp",
        "탈중앙화",
        "decentralized",
    ],
    "데이터": [
        "dbt",
        "airflow",
        "etl",
        "data warehouse",
        "데이터 웨어하우스",
        "data pipeline",
        "데이터 파이프라인",
        "spark",
        "kafka",
        "data lake",
        "배치 처리",
        "batch",
        "analytics",
        "분석",
        "bigquery",
        "snowflake",
        "redshift",
    ],
    "도구개발": [
        "extension",
        "확장",
        "plugin",
        "플러그인",
        "addon",
        "vscode",
        "browser extension",
        "브라우저 확장",
        "devtools",
        "개발 도구",
        "developer tool",
    ],
}


# ---------------------------------------------------------------------------
# v5.6: 언어 분류 함수
# ---------------------------------------------------------------------------

def categorize_languages(lang_stats: Dict[str, int]) -> Dict[str, List[Tuple[str, float]]]:
    """
    언어를 main / sub / trivial로 분류.
    LOC 비율 기준이 아닌 직무 시그널 강도 기준.
    Returns: {"main": [(lang, pct), ...], "sub": [...], "trivial": [...]}
    """
    total = sum(lang_stats.values())
    if total == 0:
        return {"main": [], "sub": [], "trivial": []}

    main: List[Tuple[str, float]] = []
    sub: List[Tuple[str, float]] = []
    trivial: List[Tuple[str, float]] = []

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


def _matches_lua_host_signature(
    sig: Dict,
    paths: List[str],
    basenames: List[str],
    root_files: List[str],
) -> bool:
    """단일 Lua 호스트 시그너처 매칭. 헬퍼 — 각 키 종류별 체크."""
    # exclude_if_basename_exists: 이 basename이 있으면 매칭 제외 (부정 조건)
    for f in sig.get("exclude_if_basename_exists", []):
        if f.lower() in basenames:
            return False

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
        cnt = sum(
            1 for p in paths
            for pat in sig["file_patterns_endswith"]
            if p.endswith(pat.lower())
        )
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


def detect_lua_host(tree_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Lua 호스트 환경 감지. 첫 번째 매칭되는 환경 반환.
    Returns: {"name", "domain", "label", "is_config"} or None
    """
    if not tree_data or "tree" not in tree_data:
        return None

    paths = [
        item["path"].lower().replace("\\", "/")
        for item in tree_data["tree"]
        if item.get("path")
    ]
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


def resolve_sub_language_alone(
    lang: str,
    tree_data: Optional[Dict[str, Any]] = None,
) -> Optional[Dict[str, Any]]:
    """
    서브 언어가 단독으로 있을 때의 환경/도메인 추론.
    Lua는 호스트 추론, 나머지는 DEFAULT_ALONE_DOMAINS 기본값.
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


# ---------------------------------------------------------------------------
# v5.7: 모드/플러그인 플랫폼 감지
# ---------------------------------------------------------------------------

def _matches_mod_signature(
    sig: Dict,
    paths: List[str],
    basenames: List[str],
    root_files: Optional[List[str]] = None,
) -> bool:
    """
    모드 플랫폼 시그너처 매칭 헬퍼.
    required_dirs / required_files_basename / required_files_root /
    regex_patterns(basename 대상) + supporting_dirs / supporting_files_basename /
    supporting_files_endswith / supporting_path_contains 지원.
    exclude_if_basename_exists: 부정 조건 (basename 존재 시 매칭 제외).
    """
    # exclude_if_basename_exists: 이 basename이 있으면 매칭 제외 (부정 조건)
    for f in sig.get("exclude_if_basename_exists", []):
        if f.lower() in basenames:
            return False

    # required_dirs: 하나라도 경로에 포함되면 OK
    for d in sig.get("required_dirs", []):
        if not any(d.lower() in p for p in paths):
            return False

    # required_files_basename: basename에 해당 파일이 있어야 함
    for f in sig.get("required_files_basename", []):
        if f.lower() not in basenames:
            return False

    # required_files_root: 루트(깊이 0) 파일에 해당 파일이 있어야 함
    if "required_files_root" in sig:
        rf = root_files if root_files is not None else [p for p in paths if "/" not in p]
        for f in sig["required_files_root"]:
            if f.lower() not in rf:
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

    # supporting 조건 집계
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
    for s in sig.get("supporting_path_contains", []):
        if any(s.lower() in p for p in paths):
            support_count += 1

    if support_count < sig.get("min_supporting", 0):
        return False

    return True


def detect_mod_platform(tree_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    모드/플러그인 플랫폼 감지. 첫 번째 매칭 환경 반환.
    Returns: {"name", "domain", "label", "mod_context", "is_hobby"} or None
    """
    if not tree_data or "tree" not in tree_data:
        return None

    paths = [
        item["path"].lower().replace("\\", "/")
        for item in tree_data["tree"]
        if item.get("path")
    ]
    basenames = [p.rsplit("/", 1)[-1] for p in paths]
    root_files = [p for p in paths if "/" not in p]

    for name, sig in MOD_PLATFORM_SIGNATURES.items():
        if not _matches_mod_signature(sig, paths, basenames, root_files):
            continue
        return {
            "name": name,
            "domain": sig.get("domain"),
            "label": sig.get("label"),
            "mod_context": sig.get("mod_context", True),
            "is_hobby": sig.get("is_hobby", False),
        }
    return None


def extract_readme_keywords(readme_text: str) -> str:
    """
    README에서 도메인/기술 키워드를 추출해 짧은 문장으로 압축.
    원문을 그대로 붙이지 않고 FAISS 매칭에 유의미한 시그널만 남김 (v5.1).
    """
    if not readme_text or len(readme_text.strip()) < 30:
        return ""

    text_lower = readme_text.lower()
    hit_domains: Dict[str, int] = {}

    for domain, keywords in README_KEYWORDS.items():
        hits = sum(1 for kw in keywords if kw.lower() in text_lower)
        if hits >= 1:
            hit_domains[domain] = hits

    if not hit_domains:
        return ""

    sorted_domains = sorted(hit_domains, key=hit_domains.get, reverse=True)
    top_domain = sorted_domains[0]

    matched_keywords: List[str] = []
    for kw in README_KEYWORDS[top_domain]:
        if kw.lower() in text_lower and kw not in matched_keywords:
            matched_keywords.append(kw)

    if matched_keywords:
        return f"{', '.join(matched_keywords[:6])} 관련 프로젝트"
    return ""


def _tree_blobs(tree_data: Dict[str, Any]) -> List[Dict[str, Any]]:
    if not tree_data or "tree" not in tree_data:
        return []
    return [i for i in tree_data["tree"] if i.get("type") == "blob" and i.get("path")]


def _tree_all_paths_lower(tree_data: Dict[str, Any]) -> List[str]:
    """blob·tree 항목 모두 포함 — 디렉터리 경로(예: Assets/) 감지용."""
    if not tree_data or "tree" not in tree_data:
        return []
    out: List[str] = []
    for item in tree_data["tree"]:
        p = item.get("path")
        if p:
            out.append(p.lower().replace("\\", "/"))
    return out


def detect_engine_signatures(tree_data: Dict[str, Any]) -> List[str]:
    """
    파일 트리에서 엔진/프레임워크 시그니처를 감지합니다.
    DOMAIN_SIGNALS·의존성 파싱과 독립적이며, 추가 API 호출이 없습니다.

    지원 키:
      required_any: 경로에 하나라도 포함 (OR, 빈 리스트면 pass)
      required_any_dirs: OR 조건 디렉토리 (하나라도 있어야)
      required_files_root: 루트 레벨 파일 (AND — 모두 있어야)
      exclude_if_basename_exists: 부정 조건 basename (하나라도 있으면 제외)
      file_count_endswith: 확장자별 최소 파일 수 {ext: min_count}
      supporting_files: endswith 보조 파일
      supporting_dirs: 경로 부분 매칭 보조 디렉토리
      supporting_files_endswith: 확장자 endswith 보조 (supporting_files와 동일 방식)
      min_supporting: 보조 조건 최소 충족 수
    manifest_signature_keywords가 있는 시그너처는 detect_signatures_with_content()에서
    비동기로 처리하므로 이 함수에서는 건너뜁니다.
    """
    if not tree_data or "tree" not in tree_data:
        return []

    all_paths = _tree_all_paths_lower(tree_data)
    basenames = [p.rsplit("/", 1)[-1] for p in all_paths]
    root_files = [p for p in all_paths if "/" not in p]
    detected: List[str] = []

    for name, sig in ENGINE_SIGNATURES.items():
        # manifest_signature_keywords가 있으면 비동기 함수로 처리 → 건너뜀
        if "manifest_signature_keywords" in sig:
            continue

        # exclude_if_basename_exists: 이 basename이 있으면 제외 (부정 조건)
        excluded = False
        for f in sig.get("exclude_if_basename_exists", []):
            if f.lower() in basenames:
                excluded = True
                break
        if excluded:
            continue

        # required_any: 경로에 문자열이 하나라도 포함되어야 (OR)
        has_required = False
        req_any = sig.get("required_any") or []
        if not req_any:
            has_required = True
        else:
            for req in req_any:
                if any(req in p for p in all_paths):
                    has_required = True
                    break

        if not has_required:
            continue

        # required_files_root: 루트 레벨에 해당 파일이 모두 있어야 (AND)
        root_ok = True
        for f in sig.get("required_files_root", []):
            if f.lower() not in root_files:
                root_ok = False
                break
        if not root_ok:
            continue

        # required_any_dirs: OR 조건 — 디렉토리 중 하나라도 트리에 있어야
        req_any_dirs = sig.get("required_any_dirs") or []
        if req_any_dirs:
            if not any(any(d.lower() in p for p in all_paths) for d in req_any_dirs):
                continue

        # file_count_endswith: 확장자별 최소 파일 수
        file_count_ok = True
        for ext, min_count in sig.get("file_count_endswith", {}).items():
            cnt = sum(1 for p in all_paths if p.endswith(ext.lower()))
            if cnt < min_count:
                file_count_ok = False
                break
        if not file_count_ok:
            continue

        support_count = 0
        for sf in sig.get("supporting_files", []):
            if any(p.endswith(sf) for p in all_paths):
                support_count += 1
        for sd in sig.get("supporting_dirs", []):
            if any(sd in p for p in all_paths):
                support_count += 1
        # supporting_files_endswith: supporting_files와 동일한 endswith 방식
        for sf in sig.get("supporting_files_endswith", []):
            if any(p.endswith(sf.lower()) for p in all_paths):
                support_count += 1

        if support_count >= int(sig.get("min_supporting", 1)):
            detected.append(name)

    return detected


async def detect_signatures_with_content(
    tree_data: Dict[str, Any],
    fetch_text_fn,
    repo_url: str,
    ref: str,
) -> List[str]:
    """
    manifest_signature_keywords가 있는 ENGINE_SIGNATURES 항목을 비동기로 검증.

    fetch_text_fn: async (repo_url, ref, paths) -> Dict[str, str]
      — GitHubExtractor._fetch_repo_text_files의 (session 바인딩된) 래퍼를 전달.

    처리 흐름:
      1단계: 트리 경로 기반 사전 필터 (required_files_root, required_any_dirs,
             exclude_if_basename_exists 동기 체크)
      2단계: 후보의 manifest 파일 경로 수집 후 일괄 fetch
      3단계: manifest_signature_keywords 키워드 매칭으로 환경 확정
    """
    if not tree_data or "tree" not in tree_data:
        return []

    all_paths = _tree_all_paths_lower(tree_data)
    basenames = [p.rsplit("/", 1)[-1] for p in all_paths]
    root_files = [p for p in all_paths if "/" not in p]

    # manifest_signature_keywords를 가진 시그너처만 처리
    candidates: List[tuple] = []
    for name, sig in ENGINE_SIGNATURES.items():
        if "manifest_signature_keywords" not in sig:
            continue

        # exclude_if_basename_exists 사전 필터
        excluded = any(f.lower() in basenames for f in sig.get("exclude_if_basename_exists", []))
        if excluded:
            continue

        # required_files_root: 루트에 해당 파일이 모두 있어야
        root_ok = all(f.lower() in root_files for f in sig.get("required_files_root", []))
        if not root_ok:
            continue

        # required_any_dirs: OR 조건
        req_any_dirs = sig.get("required_any_dirs") or []
        if req_any_dirs:
            if not any(any(d.lower() in p for p in all_paths) for d in req_any_dirs):
                continue

        # required_any: 경로 부분 매칭 OR 조건
        req_any = sig.get("required_any") or []
        if req_any:
            if not any(any(req in p for p in all_paths) for req in req_any):
                continue

        candidates.append((name, sig))

    if not candidates:
        return []

    # 각 후보의 manifest 파일 실제 경로를 트리에서 탐색
    paths_to_fetch: List[str] = []
    candidate_manifest_paths: Dict[str, str] = {}  # name → 실제 파일 경로

    for name, sig in candidates:
        root_targets = sig.get("required_files_root", [])
        if not root_targets:
            continue
        target_lower = root_targets[0].lower()
        # 트리에서 대소문자 원본 경로 찾기 (root_files는 소문자이므로 tree를 재순회)
        for item in tree_data["tree"]:
            item_path = item.get("path", "").replace("\\", "/")
            if item_path.lower() == target_lower and "/" not in item_path:
                if item_path not in paths_to_fetch:
                    paths_to_fetch.append(item_path)
                candidate_manifest_paths[name] = item_path
                break

    if not paths_to_fetch:
        return []

    # 일괄 fetch (실제 호출 수는 후보 manifest 수 = 최대 2~3개로 제한)
    contents: Dict[str, str] = await fetch_text_fn(repo_url, ref, paths_to_fetch)

    # 키워드 매칭으로 최종 확정
    detected: List[str] = []
    for name, sig in candidates:
        manifest_path = candidate_manifest_paths.get(name)
        if not manifest_path:
            continue
        manifest_text = contents.get(manifest_path, "")
        if not manifest_text:
            continue
        keywords = sig["manifest_signature_keywords"]
        if all(kw in manifest_text for kw in keywords):
            detected.append(name)

    return detected


def detect_domain_hits(tree_data: Dict[str, Any]) -> Dict[str, int]:
    """도메인별 고유 키워드 종류 수. 최소 2종류 이상인 도메인만 포함."""
    blobs = _tree_blobs(tree_data)
    all_paths = [b["path"].lower().replace("\\", "/") for b in blobs]
    domain_hits: Dict[str, int] = {}
    for domain, keywords in DOMAIN_SIGNALS.items():
        matched_keywords: Set[str] = set()
        for p in all_paths:
            for kw in keywords:
                if kw in p:
                    matched_keywords.add(kw)
        if len(matched_keywords) >= 2:
            domain_hits[domain] = len(matched_keywords)
    return domain_hits


def merge_domain_hits(per_repo_hits: List[Dict[str, int]]) -> List[str]:
    merged: Dict[str, int] = {}
    for d in per_repo_hits:
        for k, v in d.items():
            merged[k] = merged.get(k, 0) + v
    return sorted(merged.keys(), key=lambda x: merged[x], reverse=True)


def find_dependency_paths(tree_data: Dict[str, Any], max_files: int = 8) -> List[str]:
    """tree에서 의존성 파일 경로만 수집 (얕은 경로 우선)."""
    blobs = _tree_blobs(tree_data)
    found: List[str] = []
    seen: Set[str] = set()
    # 짧은 경로(루트 근처) 우선
    candidates = []
    for b in blobs:
        path = b["path"]
        name = path.rsplit("/", 1)[-1].lower()
        if name in DEPENDENCY_FILENAMES or name == "gemfile":
            depth = path.count("/")
            candidates.append((depth, len(path), path))
    candidates.sort(key=lambda x: (x[0], x[1]))
    for _, _, path in candidates:
        if path in seen:
            continue
        seen.add(path)
        found.append(path)
        if len(found) >= max_files:
            break
    return found


def has_deployment_signals(tree_data: Dict[str, Any]) -> bool:
    blobs = _tree_blobs(tree_data)
    for b in blobs:
        pl = b["path"].lower().replace("\\", "/")
        for marker in DEPLOYMENT_PATH_MARKERS:
            if marker in pl:
                return True
    return False


def _parse_package_json(text: str) -> List[str]:
    out: List[str] = []
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return out
    deps = {}
    for key in ("dependencies", "devDependencies", "peerDependencies"):
        block = data.get(key)
        if isinstance(block, dict):
            deps.update(block)
    interesting = {
        "react": "React",
        "next": "Next.js",
        "vue": "Vue.js",
        "express": "Express",
        "nestjs": "NestJS",
        "@nestjs/core": "NestJS",
        "nuxt": "Nuxt",
        "svelte": "Svelte",
        "angular": "Angular",
        "electron": "Electron",
        # v5.8: 신규 환경 카테고리
        "react-native": "React Native",
        "@expo/cli": "Expo",
        "expo": "Expo",
        "hardhat": "Hardhat",
        "@nomicfoundation/hardhat-toolbox": "Hardhat",
        "discord.js": "Discord 봇",
        "telegraf": "Telegram 봇",
        "@vscode/vsce": "VS Code 확장",
    }
    for pkg, label in interesting.items():
        if pkg in deps:
            out.append(label)
    return list(dict.fromkeys(out))


def _parse_requirements_txt(text: str) -> List[str]:
    names = []
    for line in text.splitlines():
        line = line.strip().split("#", 1)[0].strip()
        if not line or line.startswith("-"):
            continue
        m = re.match(r"^([a-zA-Z0-9_.-]+)", line)
        if m:
            names.append(m.group(1).lower().replace("_", "-"))
    interesting = {
        "fastapi": "FastAPI",
        "django": "Django",
        "flask": "Flask",
        "torch": "PyTorch",
        "tensorflow": "TensorFlow",
        "uvicorn": "Uvicorn",
        # v5.8: 신규 환경 카테고리
        "streamlit": "Streamlit",
        "gradio": "Gradio",
        "apache-airflow": "Airflow",
        "dbt-core": "dbt",
        "discord.py": "Discord 봇",
        "python-telegram-bot": "Telegram 봇",
        "transformers": "Hugging Face Transformers",
    }
    out: List[str] = []
    for n in names:
        for k, label in interesting.items():
            if k == n or n.startswith(k + "["):
                out.append(label)
    return list(dict.fromkeys(out))


def _parse_go_mod(text: str) -> List[str]:
    out: List[str] = []
    for line in text.splitlines():
        line = line.strip()
        if line.startswith("module "):
            continue
        if "github.com/gin-gonic/gin" in line:
            out.append("Gin")
        if "github.com/labstack/echo" in line:
            out.append("Echo")
    return list(dict.fromkeys(out))


def _parse_cargo_toml(text: str) -> List[str]:
    out: List[str] = []
    if re.search(r"\bactix-web\b", text):
        out.append("Actix Web")
    if re.search(r"\brocket\b", text, re.I):
        out.append("Rocket")
    if re.search(r"\baxum\b", text):
        out.append("Axum")
    return out


def _parse_gemfile(text: str) -> List[str]:
    out: List[str] = []
    if re.search(r"gem\s+['\"]rails['\"]", text, re.I):
        out.append("Ruby on Rails")
    if re.search(r"gem\s+['\"]sinatra['\"]", text, re.I):
        out.append("Sinatra")
    return out


def _parse_pom_or_gradle(text: str) -> List[str]:
    out: List[str] = []
    if "spring-boot" in text.lower() or "springframework" in text.lower():
        out.append("Spring Boot")
    return out


def parse_dependency_contents(path_to_content: Dict[str, str]) -> List[str]:
    """경로→원문 맵에서 프레임워크 라벨 목록 추출."""
    acc: List[str] = []
    for path, content in path_to_content.items():
        name = path.rsplit("/", 1)[-1].lower()
        if name == "package.json":
            acc.extend(_parse_package_json(content))
        elif name == "requirements.txt":
            acc.extend(_parse_requirements_txt(content))
        elif name in ("build.gradle", "build.gradle.kts", "pom.xml"):
            acc.extend(_parse_pom_or_gradle(content))
        elif name == "gemfile":
            acc.extend(_parse_gemfile(content))
        elif name == "go.mod":
            acc.extend(_parse_go_mod(content))
        elif name == "cargo.toml":
            acc.extend(_parse_cargo_toml(content))
        elif name == "pyproject.toml":
            acc.extend(_parse_pom_or_gradle(content))
            acc.extend(_parse_requirements_txt(content))
    return list(dict.fromkeys(acc))


def compute_tree_structure_stats(
    tree_data: Dict[str, Any],
    valid_loc: int,
    is_valid_source_code_fn,
) -> Dict[str, Any]:
    """파일당 평균 LOC, .gitignore, 소스 파일 수."""
    blobs = _tree_blobs(tree_data)
    source_files = [
        b for b in blobs
        if is_valid_source_code_fn(b["path"])
    ]
    n_src = len(source_files)
    avg_loc = (valid_loc / n_src) if n_src > 0 else 0.0
    paths_lower = [b["path"].lower().replace("\\", "/") for b in blobs]
    has_gitignore = any(p.endswith("/.gitignore") or p == ".gitignore" for p in paths_lower)
    return {
        "source_file_count": n_src,
        "avg_loc_per_file": round(avg_loc, 1),
        "has_gitignore": has_gitignore,
    }


def build_profile_text(extracted_data: Dict[str, Any]) -> str:
    """
    공고 문체에 가까운 단일 문자열 생성.
    v5.6: language_category(main/sub) + sub_language_host 기반 분기.
          top_languages 키는 후방 호환용으로 폴백에만 사용.
          README 키워드/CI/CD/테스트/배포 라인은 v5.3 정책 그대로 유지.
    extracted_data 키: language_category, sub_language_host,
                       top_languages(fallback), detected_domains, frameworks,
                       has_cicd, has_tests, has_deployment, readme_summary
    """
    parts: List[str] = []

    lang_cat = extracted_data.get("language_category") or {}
    main_langs: List[Tuple[str, float]] = lang_cat.get("main") or []
    sub_langs: List[Tuple[str, float]] = lang_cat.get("sub") or []
    sub_host: Optional[Dict[str, Any]] = extracted_data.get("sub_language_host")

    domains: List[str] = extracted_data.get("detected_domains") or []
    primary_domain = domains[0] if domains else None

    # 1. 메인 언어 + 도메인
    if main_langs:
        main_str = ", ".join(f"{l} ({pct:.0f}%)" for l, pct in main_langs[:3])
        if primary_domain:
            parts.append(f"{main_str} 기반 {primary_domain} 경험")
        else:
            parts.append(f"{main_str} 기반 개발 경험")
    elif sub_host and sub_host.get("label"):
        # 메인 언어 없이 서브 언어 단독: 호스트/기본 도메인 기반 라벨
        parts.append(sub_host["label"])
    else:
        # v5.6 이전 방식 폴백 (language_category가 없는 경우)
        langs: str = (extracted_data.get("top_languages") or "").strip()
        if primary_domain and langs and langs.upper() != "N/A":
            parts.append(f"{langs} 기반 {primary_domain} 경험")
        elif langs and langs.upper() != "N/A":
            parts.append(f"{langs} 기반 개발 경험")

    # 2. 프레임워크
    fw = extracted_data.get("frameworks") or []
    if fw:
        parts.append(f"{', '.join(fw)} 활용 경험")

    # 3. 서브 언어 보조 역할 표기 (메인이 있을 때)
    if main_langs and sub_langs:
        sub_descriptions: List[str] = []
        for lang, _ in sub_langs:
            sig = SUB_LANGUAGE_SIGNALS.get(lang) or {}
            label = sig.get("with_main_label")
            if label:
                sub_descriptions.append(label)
        if sub_descriptions:
            parts.append(f"{', '.join(sub_descriptions)} 활용")

    # 4. Lua 호스트 환경 (메인이 있어도 보조 정보로 추가)
    if sub_host and sub_host.get("label") and main_langs:
        parts.append(f"{sub_host['label']} 환경")

    # 5. CI/CD, 테스트, 배포 (v5.3 정책 유지)
    if extracted_data.get("has_cicd"):
        parts.append("CI/CD 파이프라인 구축 경험 (GitHub Actions 또는 Docker)")

    if extracted_data.get("has_tests"):
        parts.append("테스트 코드 작성 경험 보유")

    if extracted_data.get("has_deployment"):
        parts.append("배포 환경 구성 경험")

    # 6. README 키워드 (v5.3 정책 유지: 200자 이상 + 키워드 추출 성공 시만)
    readme_summary = extracted_data.get("readme_summary") or ""
    if readme_summary and len(readme_summary) >= 200:
        readme_keywords = extract_readme_keywords(readme_summary)
        if readme_keywords:
            parts.append(readme_keywords)

    if not parts:
        return "GitHub 저장소 기반 개발 경험 (상세 메타데이터 부족)."
    return ". ".join(parts) + "."


def readme_length_tier(clean_readme: str) -> str:
    n = len(clean_readme.strip())
    if n >= 200:
        return "long"
    if n >= 50:
        return "medium"
    return "short"
