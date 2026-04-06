"""
Git2Value v5.1 — 프로필 텍스트 변환 레이어 (룰베이스).
JD 임베딩과의 문체 정합을 위해 구조화 데이터를 공고형 문장으로 변환합니다.
v5.1: README는 키워드 압축(노이즈 완화) + 키워드 없을 때 짧은 원문 폴백.
"""
from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Optional, Set

# 파일명/폴더명 기반 도메인 시그널 (Plan3 §3-5)
DOMAIN_SIGNALS: Dict[str, List[str]] = {
    "게임 개발": [
        "game", "player", "enemy", "scene", "inventory", "combat",
        "sprite", "level", "quest", "npc", "dungeon", "weapon",
        "gamemanager", "playercontroller", "spawn",
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
    ],
}


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


def detect_domain_hits(tree_data: Dict[str, Any]) -> Dict[str, int]:
    """도메인별 히트 수. 최소 2히트 이상인 도메인만 포함."""
    blobs = _tree_blobs(tree_data)
    all_paths = [b["path"].lower().replace("\\", "/") for b in blobs]
    domain_hits: Dict[str, int] = {}
    for domain, keywords in DOMAIN_SIGNALS.items():
        hits = 0
        for p in all_paths:
            for kw in keywords:
                if kw in p:
                    hits += 1
        if hits >= 2:
            domain_hits[domain] = hits
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
    extracted_data 키: top_languages, detected_domains, frameworks,
    has_cicd, has_tests, has_deployment, readme_summary
    """
    parts: List[str] = []
    domains: List[str] = extracted_data.get("detected_domains") or []
    langs: str = (extracted_data.get("top_languages") or "").strip()

    if domains and langs and langs.upper() != "N/A":
        parts.append(f"{langs} 기반 {domains[0]} 경험")
    elif langs and langs.upper() != "N/A":
        parts.append(f"{langs} 기반 개발 경험")

    fw = extracted_data.get("frameworks") or []
    if fw:
        parts.append(f"{', '.join(fw)} 활용 경험")

    if extracted_data.get("has_cicd"):
        parts.append("CI/CD 파이프라인 구축 경험 (GitHub Actions 또는 Docker)")

    if extracted_data.get("has_tests"):
        parts.append("테스트 코드 작성 경험 보유")

    if extracted_data.get("has_deployment"):
        parts.append("배포 환경 구성 경험")

    readme_summary = extracted_data.get("readme_summary") or ""
    if readme_summary and len(readme_summary) >= 200:
        readme_keywords = extract_readme_keywords(readme_summary)
        if readme_keywords:
            parts.append(readme_keywords)
        else:
            parts.append(readme_summary[:300])

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
