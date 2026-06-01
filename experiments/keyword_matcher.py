"""
실험 1 비교 기준선: 키워드 기반 채용공고 매칭.

목적
- embedding_matcher.py가 사용하는 것과 동일한 채용공고 metadata를 사용한다.
- 단, SentenceTransformer/FAISS는 사용하지 않는다.
- GitHub profile_for_matching 텍스트와 채용공고 text 사이의 기술 키워드 중복 정도로 Top-k를 반환한다.

반환 형식은 run_git2value.py의 FAISS top_matches와 최대한 맞춘다.
    {
        "meta": 채용공고 metadata,
        "similarity": 키워드 점수,
        "category": route_job_category(meta["position"]),
        "matched_keywords": [...]
    }
"""

from __future__ import annotations

import argparse
import json
import math
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any, Dict, Iterable, List, Sequence, Set

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# 원본 코드의 채용공고 직무 라우팅 함수를 그대로 사용한다.
from run_git2value import route_job_category  # noqa: E402

DEFAULT_META_PATH = PROJECT_ROOT / "vector" / "git2value_metadata.json"

# 실험용 기술 키워드 사전.
# 원본 profile_for_matching이 언어/프레임워크/도메인/CI/CD/테스트 정보를 문장으로 만들기 때문에
# 해당 정보가 잘 잡히도록 한국어/영어/프레임워크명을 함께 둔다.
TECH_KEYWORDS: Sequence[str] = [
    # language
    "python", "java", "javascript", "typescript", "node", "node.js", "php", "ruby",
    "go", "golang", "kotlin", "swift", "c", "c++", "c#", "rust", "scala",
    "html", "css", "sass", "lua", "r", "matlab",
    # backend
    "spring", "spring boot", "jpa", "hibernate", "fastapi", "django", "flask",
    "express", "nestjs", "nodejs", "rest", "rest api", "graphql", "api", "server",
    "backend", "백엔드", "서버", "controller", "service", "repository", "middleware",
    # frontend
    "react", "next", "next.js", "vue", "nuxt", "angular", "svelte", "frontend",
    "프론트엔드", "프론트", "component", "ui", "ux", "redux", "zustand", "tailwind",
    # db/data
    "mysql", "postgresql", "postgres", "mariadb", "mongodb", "redis", "sqlite",
    "oracle", "database", "db", "sql", "nosql", "etl", "spark", "hadoop", "kafka",
    "airflow", "bigquery", "snowflake", "데이터", "빅데이터",
    # ai/ml
    "ai", "ml", "machine learning", "머신러닝", "인공지능", "deep learning", "딥러닝",
    "pytorch", "tensorflow", "keras", "scikit", "sklearn", "opencv", "yolo", "llm",
    "nlp", "computer vision", "vision", "cv", "embedding", "faiss", "model", "train",
    "inference", "dataset", "데이터셋", "예측", "분류", "객체탐지",
    # devops/cloud
    "docker", "dockerfile", "docker compose", "kubernetes", "k8s", "helm", "terraform",
    "ansible", "aws", "gcp", "azure", "cloud", "클라우드", "devops", "데브옵스",
    "ci/cd", "cicd", "github actions", "jenkins", "pipeline", "deploy", "deployment",
    "배포", "nginx", "linux", "monitoring", "grafana", "prometheus",
    # mobile/game/embedded
    "android", "안드로이드", "ios", "flutter", "react native", "expo", "mobile", "모바일",
    "unity", "unreal", "godot", "game", "게임", "vr", "ar", "3d",
    "embedded", "임베디드", "firmware", "펌웨어", "hardware", "하드웨어", "arduino",
    "raspberry", "stm32", "iot",
    # quality/portfolio terms from profile_builder
    "test", "testing", "테스트", "pytest", "junit", "jest", "vitest", "coverage",
    "readme", "문서", "문서화", "license", "authentication", "auth", "jwt", "oauth",
]

# 동의어를 대표 키워드로 정규화한다. 키워드 중복 비교가 과도하게 불리해지지 않게 하기 위함.
ALIASES: Dict[str, str] = {
    "node.js": "node",
    "nodejs": "node",
    "next.js": "next",
    "spring boot": "spring",
    "postgres": "postgresql",
    "rest api": "api",
    "rest": "api",
    "ci/cd": "cicd",
    "github actions": "cicd",
    "deployment": "deploy",
    "배포": "deploy",
    "machine learning": "ml",
    "머신러닝": "ml",
    "인공지능": "ai",
    "deep learning": "deep_learning",
    "딥러닝": "deep_learning",
    "computer vision": "vision",
    "객체탐지": "detection",
    "데이터셋": "dataset",
    "백엔드": "backend",
    "서버": "backend",
    "프론트엔드": "frontend",
    "프론트": "frontend",
    "데브옵스": "devops",
    "클라우드": "cloud",
    "안드로이드": "android",
    "모바일": "mobile",
    "게임": "game",
    "임베디드": "embedded",
    "펌웨어": "firmware",
    "하드웨어": "hardware",
    "테스트": "test",
    "문서화": "docs",
    "문서": "docs",
}


def normalize_text(text: str) -> str:
    text = (text or "").lower()
    # c++, c#, node.js 같은 표현을 보존하면서 비교하기 위해 기본 정규화만 수행
    text = text.replace("_", " ").replace("-", " ")
    return re.sub(r"\s+", " ", text).strip()


def _keyword_pattern(keyword: str) -> re.Pattern[str]:
    """영문 키워드는 단어 경계를 두고, 한글 키워드는 부분 문자열 매칭을 허용."""
    k = re.escape(keyword.lower())
    if re.search(r"[가-힣]", keyword):
        return re.compile(k)
    # c++, c#처럼 \b가 잘 안 맞는 표현은 주변 영숫자만 제한
    return re.compile(rf"(?<![a-z0-9]){k}(?![a-z0-9])")


_KEYWORD_PATTERNS = [(kw, _keyword_pattern(kw)) for kw in sorted(TECH_KEYWORDS, key=len, reverse=True)]


def canonical_keyword(keyword: str) -> str:
    return ALIASES.get(keyword.lower(), keyword.lower())


def extract_keywords(text: str) -> Set[str]:
    """텍스트에서 기술 키워드를 추출하고 대표 키워드로 정규화."""
    norm = normalize_text(text)
    found: Set[str] = set()
    for kw, pattern in _KEYWORD_PATTERNS:
        if pattern.search(norm):
            found.add(canonical_keyword(kw))
    return found


def keyword_score(query_keywords: Set[str], doc_keywords: Set[str]) -> float:
    """
    키워드 매칭 점수.
    - query 기준 recall: GitHub 프로필 키워드 중 공고와 겹친 비율
    - doc 기준 precision: 공고 키워드 중 GitHub와 겹친 비율
    두 값을 F1 형태로 결합해 긴 공고가 무조건 유리해지는 현상을 완화한다.
    """
    if not query_keywords or not doc_keywords:
        return 0.0
    overlap = query_keywords & doc_keywords
    if not overlap:
        return 0.0
    recall = len(overlap) / len(query_keywords)
    precision = len(overlap) / len(doc_keywords)
    return 2 * precision * recall / (precision + recall)


def load_metadata(meta_path: Path | str = DEFAULT_META_PATH) -> List[Dict[str, Any]]:
    with Path(meta_path).open("r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, list):
        raise ValueError("metadata JSON은 list 형식이어야 합니다.")
    return data


def _metadata_text(meta: Dict[str, Any]) -> str:
    """원본 FAISS 인덱스가 만들어진 metadata의 text를 최우선으로 사용."""
    parts = [
        str(meta.get("position") or ""),
        str(meta.get("category") or ""),
        str(meta.get("text") or ""),
    ]
    return "\n".join(p for p in parts if p)


def match_jobs_by_keywords(
    profile_text: str,
    metadata: List[Dict[str, Any]] | None = None,
    top_k: int = 5,
    meta_path: Path | str = DEFAULT_META_PATH,
) -> List[Dict[str, Any]]:
    """GitHub profile_for_matching 텍스트와 채용공고 metadata를 키워드 중복으로 매칭."""
    if metadata is None:
        metadata = load_metadata(meta_path)

    query_keywords = extract_keywords(profile_text)
    scored: List[Dict[str, Any]] = []

    for meta in metadata:
        doc_text = _metadata_text(meta)
        doc_keywords = extract_keywords(doc_text)
        overlap = sorted(query_keywords & doc_keywords)
        score = keyword_score(query_keywords, doc_keywords)

        # 동점 처리용: 겹친 키워드 개수와 공고 제목 내 직접 매칭 개수도 함께 둔다.
        title_keywords = extract_keywords(str(meta.get("position") or ""))
        title_overlap_count = len(query_keywords & title_keywords)

        scored.append(
            {
                "meta": meta,
                "similarity": float(score),
                "category": route_job_category(str(meta.get("position") or "")),
                "matched_keywords": overlap,
                "query_keywords": sorted(query_keywords),
                "doc_keyword_count": len(doc_keywords),
                "title_overlap_count": title_overlap_count,
            }
        )

    scored.sort(
        key=lambda x: (
            x["similarity"],
            len(x["matched_keywords"]),
            x["title_overlap_count"],
        ),
        reverse=True,
    )
    return scored[:top_k]


def _demo(profile_text: str, top_k: int, meta_path: Path) -> None:
    metadata = load_metadata(meta_path)
    matches = match_jobs_by_keywords(profile_text, metadata=metadata, top_k=top_k)
    print("[Query keywords]", ", ".join(extract_keywords(profile_text)) or "없음")
    print()
    for rank, m in enumerate(matches, start=1):
        meta = m["meta"]
        print(f"#{rank} score={m['similarity']:.4f} category={m['category']}")
        print(f"  position: {meta.get('position')}")
        print(f"  matched: {', '.join(m['matched_keywords']) or '-'}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Git2Value 키워드 기반 채용공고 매칭")
    parser.add_argument("--profile-text", default="", help="직접 입력할 profile_for_matching 텍스트")
    parser.add_argument("--profile-file", default="", help="profile_for_matching 텍스트 파일")
    parser.add_argument("--meta", default=str(DEFAULT_META_PATH), help="vector/git2value_metadata.json 경로")
    parser.add_argument("--top-k", type=int, default=5)
    args = parser.parse_args()

    if args.profile_file:
        profile_text = Path(args.profile_file).read_text(encoding="utf-8")
    else:
        profile_text = args.profile_text

    if not profile_text.strip():
        raise SystemExit("--profile-text 또는 --profile-file을 입력하세요.")

    _demo(profile_text, args.top_k, Path(args.meta))


if __name__ == "__main__":
    main()
