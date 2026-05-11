"""
실험 1 AI 방식: SentenceTransformer + FAISS 기반 채용공고 매칭.

목적
- run_git2value.py의 원본 임베딩/FAISS 매칭 로직을 실험용 함수로 분리한다.
- keyword_matcher.py와 같은 metadata(vector/git2value_metadata.json)를 사용한다.
- profile_for_matching 텍스트를 입력받아 Top-k 채용공고를 반환한다.

반환 형식은 keyword_matcher.py와 최대한 맞춘다.
    {
        "meta": 채용공고 metadata,
        "similarity": FAISS 유사도 점수,
        "category": route_job_category(meta["position"]),
        "index": FAISS metadata index
    }
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List

# experiments/에서 실행해도 프로젝트 루트 모듈을 import할 수 있게 처리
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# 원본 코드와 동일하게 로컬 캐시 우선 사용
os.environ.setdefault("HF_HUB_OFFLINE", "1")

import faiss  # noqa: E402
from sentence_transformers import SentenceTransformer  # noqa: E402

# 원본 코드의 직무 라우팅 함수를 그대로 재사용
from run_git2value import route_job_category  # noqa: E402

DEFAULT_INDEX_PATH = PROJECT_ROOT / "vector" / "git2value_faiss.index"
DEFAULT_META_PATH = PROJECT_ROOT / "vector" / "git2value_metadata.json"
DEFAULT_MODEL_NAME = "jhgan/ko-sroberta-multitask"


_MODEL_CACHE: Dict[str, SentenceTransformer] = {}
_INDEX_CACHE: Dict[str, Any] = {}
_META_CACHE: Dict[str, List[Dict[str, Any]]] = {}


def load_metadata(meta_path: Path | str = DEFAULT_META_PATH) -> List[Dict[str, Any]]:
    """원본 vector/git2value_metadata.json 로드."""
    path = str(Path(meta_path))
    if path not in _META_CACHE:
        with Path(meta_path).open("r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, list):
            raise ValueError("metadata JSON은 list 형식이어야 합니다.")
        _META_CACHE[path] = data
    return _META_CACHE[path]


def load_faiss_index(index_path: Path | str = DEFAULT_INDEX_PATH):
    """원본 FAISS index 로드."""
    path = str(Path(index_path))
    if path not in _INDEX_CACHE:
        _INDEX_CACHE[path] = faiss.read_index(path)
    return _INDEX_CACHE[path]


def load_embedding_model(model_name: str = DEFAULT_MODEL_NAME) -> SentenceTransformer:
    """원본 run_git2value.py와 동일한 SentenceTransformer 모델 로드."""
    if model_name not in _MODEL_CACHE:
        _MODEL_CACHE[model_name] = SentenceTransformer(model_name)
    return _MODEL_CACHE[model_name]


def match_jobs_by_embedding(
    profile_text: str,
    top_k: int = 5,
    index_path: Path | str = DEFAULT_INDEX_PATH,
    meta_path: Path | str = DEFAULT_META_PATH,
    model_name: str = DEFAULT_MODEL_NAME,
) -> List[Dict[str, Any]]:
    """
    GitHub profile_for_matching 텍스트를 임베딩하고 FAISS로 유사 채용공고 Top-k 반환.

    run_git2value.py의 핵심 로직과 동일하게:
        query_vector = model.encode([match_text], normalize_embeddings=True)
        distances, indices = index.search(query_vector, top_k)
    를 사용한다.
    """
    profile_text = (profile_text or "").strip()
    if not profile_text:
        return []

    metadata = load_metadata(meta_path)
    index = load_faiss_index(index_path)
    model = load_embedding_model(model_name)

    query_vector = model.encode([profile_text], normalize_embeddings=True)
    distances, indices = index.search(query_vector, top_k)

    results: List[Dict[str, Any]] = []
    for rank, idx in enumerate(indices[0], start=1):
        idx_int = int(idx)
        if idx_int < 0 or idx_int >= len(metadata):
            continue
        meta = metadata[idx_int]
        position = str(meta.get("position") or "")
        results.append(
            {
                "rank": rank,
                "index": idx_int,
                "meta": meta,
                "similarity": float(distances[0][rank - 1]),
                "category": route_job_category(position),
            }
        )
    return results


def _demo(profile_text: str, top_k: int, index_path: Path, meta_path: Path, model_name: str) -> None:
    matches = match_jobs_by_embedding(
        profile_text=profile_text,
        top_k=top_k,
        index_path=index_path,
        meta_path=meta_path,
        model_name=model_name,
    )
    for rank, m in enumerate(matches, start=1):
        meta = m["meta"]
        print(f"#{rank} similarity={m['similarity']:.4f} category={m['category']}")
        print(f"  position: {meta.get('position')}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Git2Value AI 임베딩 기반 채용공고 매칭")
    parser.add_argument("--profile-text", default="", help="직접 입력할 profile_for_matching 텍스트")
    parser.add_argument("--profile-file", default="", help="profile_for_matching 텍스트 파일")
    parser.add_argument("--index", default=str(DEFAULT_INDEX_PATH), help="vector/git2value_faiss.index 경로")
    parser.add_argument("--meta", default=str(DEFAULT_META_PATH), help="vector/git2value_metadata.json 경로")
    parser.add_argument("--model", default=DEFAULT_MODEL_NAME, help="SentenceTransformer 모델명")
    parser.add_argument("--top-k", type=int, default=5)
    args = parser.parse_args()

    if args.profile_file:
        profile_text = Path(args.profile_file).read_text(encoding="utf-8")
    else:
        profile_text = args.profile_text

    if not profile_text.strip():
        raise SystemExit("--profile-text 또는 --profile-file을 입력하세요.")

    _demo(profile_text, args.top_k, Path(args.index), Path(args.meta), args.model)


if __name__ == "__main__":
    main()
