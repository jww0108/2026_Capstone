"""
실험 1 평가 스크립트: 키워드 매칭 vs AI 임베딩 매칭.

평가 목적
- 동일한 GitHub profile_for_matching과 동일한 채용공고 metadata를 사용한다.
- keyword_matcher.py: 기술 키워드 중복 기반 Top-k 추천
- embedding_matcher.py: SentenceTransformer + FAISS 기반 Top-k 추천
- 각 방식의 Top-1 / Top-3 / Top-5 Accuracy를 계산한다.

입력
- experiments/cache/eval_profiles.json
  collect_eval_profiles.py가 생성한 평가 레포 캐시

출력
- experiments/results/experiment1_result.csv
  레포별 상세 결과
- experiments/results/experiment1_summary.csv
  방식별 Top-k Accuracy 요약
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Sequence

# experiments/에서 실행해도 프로젝트 루트 모듈을 import할 수 있게 처리
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from experiments.keyword_matcher import load_metadata, match_jobs_by_keywords  # noqa: E402
from experiments.embedding_matcher import match_jobs_by_embedding  # noqa: E402

DEFAULT_PROFILES_PATH = PROJECT_ROOT / "experiments" / "cache" / "eval_profiles.json"
DEFAULT_META_PATH = PROJECT_ROOT / "vector" / "git2value_metadata.json"
DEFAULT_INDEX_PATH = PROJECT_ROOT / "vector" / "git2value_faiss.index"
DEFAULT_RESULT_PATH = PROJECT_ROOT / "experiments" / "results" / "ex1_result.csv"
DEFAULT_SUMMARY_PATH = PROJECT_ROOT / "experiments" / "results" / "ex1_summary.csv"

# 평가 CSV의 label이 조금 다르게 적혀도 원본 route_job_category 결과와 비교 가능하도록 정규화한다.
LABEL_ALIASES: Dict[str, str] = {
    # backend
    "backend": "서버/백엔드",
    "back-end": "서버/백엔드",
    "백엔드": "서버/백엔드",
    "서버": "서버/백엔드",
    "서버/백엔드": "서버/백엔드",
    # frontend
    "frontend": "프론트엔드",
    "front-end": "프론트엔드",
    "프론트": "프론트엔드",
    "프론트엔드": "프론트엔드",
    # ai/data
    "ai": "인공지능/머신러닝",
    "ml": "인공지능/머신러닝",
    "ai/ml": "인공지능/머신러닝",
    "ai_data": "인공지능/머신러닝",
    "ai/데이터": "인공지능/머신러닝",
    "머신러닝": "인공지능/머신러닝",
    "인공지능": "인공지능/머신러닝",
    "인공지능/머신러닝": "인공지능/머신러닝",
    # data engineering
    "빅데이터": "빅데이터 엔지니어",
    "데이터 엔지니어": "빅데이터 엔지니어",
    "빅데이터 엔지니어": "빅데이터 엔지니어",
    # devops
    "devops": "devops/시스템 엔지니어",
    "devops/infra": "devops/시스템 엔지니어",
    "인프라": "devops/시스템 엔지니어",
    "시스템": "devops/시스템 엔지니어",
    "클라우드": "devops/시스템 엔지니어",
    "devops/시스템 엔지니어": "devops/시스템 엔지니어",
    # mobile
    "android": "안드로이드",
    "안드로이드": "안드로이드",
    "ios": "iOS",
    "iOS": "iOS",
    "모바일": "모바일 앱",
    "모바일 앱": "모바일 앱",
    "크로스플랫폼": "크로스플랫폼 앱",
    "크로스플랫폼 앱": "크로스플랫폼 앱",
    # game
    "game": "게임 개발",
    "게임": "게임 개발",
    "게임 개발": "게임 개발",
    "게임 클라이언트": "게임 클라이언트",
    "게임 서버": "게임 서버",
    # etc
    "임베디드": "HW/임베디드",
    "hw/임베디드": "HW/임베디드",
    "블록체인": "블록체인",
}

# 사람이 붙인 큰 라벨과 원본 채용공고 category가 일치하는지 판단하기 위한 그룹.
# 예: 평가 label이 "게임 개발"이면 "게임 클라이언트", "게임 서버" 모두 성공으로 처리.
LABEL_GROUPS: Dict[str, set[str]] = {
    "모바일 앱": {"안드로이드", "iOS", "크로스플랫폼 앱"},
    "게임 개발": {"게임 클라이언트", "게임 서버", "VR/AR/3D"},
    "ML/AI": {"인공지능/머신러닝", "빅데이터 엔지니어"},
    "인공지능/머신러닝": {"인공지능/머신러닝", "빅데이터 엔지니어"},
    "웹 개발": {"서버/백엔드", "프론트엔드", "웹 풀스택", "웹퍼블리셔"},
    "풀스택": {"웹 풀스택", "서버/백엔드", "프론트엔드"},
}


def normalize_label(label: str) -> str:
    raw = (label or "").strip()
    key = raw.lower().replace(" ", "")

    # 공백 제거 버전도 지원
    compact_aliases = {k.lower().replace(" ", ""): v for k, v in LABEL_ALIASES.items()}
    if key in compact_aliases:
        return compact_aliases[key]
    return raw


def label_matches(true_label: str, predicted_category: str) -> bool:
    true_norm = normalize_label(true_label)
    pred_norm = normalize_label(predicted_category)

    if true_norm == pred_norm:
        return True

    # 큰 라벨 그룹 처리
    if true_norm in LABEL_GROUPS and pred_norm in LABEL_GROUPS[true_norm]:
        return True

    # 모바일 label을 크게 준 경우 처리
    if true_norm == "모바일 앱" and pred_norm in {"안드로이드", "iOS", "크로스플랫폼 앱"}:
        return True

    return False


def topk_hit(true_label: str, categories: Sequence[str], k: int) -> int:
    return int(any(label_matches(true_label, c) for c in categories[:k]))


def load_profiles(path: Path | str = DEFAULT_PROFILES_PATH) -> List[Dict[str, Any]]:
    with Path(path).open("r", encoding="utf-8") as f:
        data = json.load(f)
    if isinstance(data, dict):
        data = list(data.values())
    if not isinstance(data, list):
        raise ValueError("eval_profiles.json은 list 또는 dict 형식이어야 합니다.")
    return data


def _positions(matches: Sequence[Dict[str, Any]]) -> str:
    return " | ".join(str(m.get("meta", {}).get("position") or "") for m in matches)


def _categories(matches: Sequence[Dict[str, Any]]) -> List[str]:
    return [str(m.get("category") or "") for m in matches]


def _scores(matches: Sequence[Dict[str, Any]]) -> str:
    return " | ".join(f"{float(m.get('similarity', 0.0)):.4f}" for m in matches)


def evaluate(
    profiles_path: Path,
    result_path: Path,
    summary_path: Path,
    meta_path: Path,
    index_path: Path,
    top_k: int = 5,
) -> Dict[str, Dict[str, float]]:
    profiles = load_profiles(profiles_path)
    metadata = load_metadata(meta_path)

    result_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.parent.mkdir(parents=True, exist_ok=True)

    detail_rows: List[Dict[str, Any]] = []
    counters: Dict[str, Dict[str, int]] = defaultdict(lambda: {"n": 0, "top1": 0, "top3": 0, "top5": 0})

    valid_profiles = [
        p for p in profiles
        if (p.get("profile_for_matching") or "").strip() and not p.get("error")
    ]

    for idx, profile in enumerate(valid_profiles, start=1):
        repo_key = profile.get("repo_key") or f"{profile.get('username')}/{profile.get('repo')}"
        true_label = str(profile.get("label") or "")
        profile_text = str(profile.get("profile_for_matching") or "")

        print(f"[{idx}/{len(valid_profiles)}] 평가 중: {repo_key} ({true_label})")

        method_matches = {
            "keyword": match_jobs_by_keywords(profile_text, metadata=metadata, top_k=top_k),
            "embedding": match_jobs_by_embedding(
                profile_text,
                top_k=top_k,
                index_path=index_path,
                meta_path=meta_path,
            ),
        }

        for method, matches in method_matches.items():
            cats = _categories(matches)
            hit1 = topk_hit(true_label, cats, 1)
            hit3 = topk_hit(true_label, cats, min(3, top_k))
            hit5 = topk_hit(true_label, cats, min(5, top_k))

            counters[method]["n"] += 1
            counters[method]["top1"] += hit1
            counters[method]["top3"] += hit3
            counters[method]["top5"] += hit5

            detail_rows.append(
                {
                    "repo_key": repo_key,
                    "repo_url": profile.get("repo_url", ""),
                    "true_label": true_label,
                    "true_label_normalized": normalize_label(true_label),
                    "method": method,
                    "top1_hit": hit1,
                    "top3_hit": hit3,
                    "top5_hit": hit5,
                    "pred_top1_category": cats[0] if cats else "",
                    "pred_categories_top5": " | ".join(cats),
                    "scores_top5": _scores(matches),
                    "positions_top5": _positions(matches),
                }
            )

    # 상세 결과 저장
    fieldnames = [
        "repo_key", "repo_url", "true_label", "true_label_normalized", "method",
        "top1_hit", "top3_hit", "top5_hit", "pred_top1_category",
        "pred_categories_top5", "scores_top5", "positions_top5",
    ]
    with result_path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(detail_rows)

    # 요약 결과 저장
    summary_rows: List[Dict[str, Any]] = []
    summary: Dict[str, Dict[str, float]] = {}
    for method in ["keyword", "embedding"]:
        n = counters[method]["n"]
        if n == 0:
            vals = {"n": 0, "top1_accuracy": 0.0, "top3_accuracy": 0.0, "top5_accuracy": 0.0}
        else:
            vals = {
                "n": n,
                "top1_accuracy": counters[method]["top1"] / n,
                "top3_accuracy": counters[method]["top3"] / n,
                "top5_accuracy": counters[method]["top5"] / n,
            }
        summary[method] = vals
        summary_rows.append({"method": method, **vals})

    with summary_path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["method", "n", "top1_accuracy", "top3_accuracy", "top5_accuracy"])
        writer.writeheader()
        writer.writerows(summary_rows)

    print("\n[실험 1 요약]")
    for row in summary_rows:
        print(
            f"- {row['method']}: "
            f"Top-1={row['top1_accuracy']:.4f}, "
            f"Top-3={row['top3_accuracy']:.4f}, "
            f"Top-5={row['top5_accuracy']:.4f} "
            f"(n={row['n']})"
        )
    print(f"\n상세 결과: {result_path}")
    print(f"요약 결과: {summary_path}")
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description="실험 1: 키워드 매칭 vs AI 임베딩 매칭 평가")
    parser.add_argument("--profiles", default=str(DEFAULT_PROFILES_PATH), help="experiments/cache/eval_profiles_3.json 경로")
    parser.add_argument("--meta", default=str(DEFAULT_META_PATH), help="vector/git2value_metadata.json 경로")
    parser.add_argument("--index", default=str(DEFAULT_INDEX_PATH), help="vector/git2value_faiss.index 경로")
    parser.add_argument("--result", default=str(DEFAULT_RESULT_PATH), help="상세 결과 CSV 저장 경로")
    parser.add_argument("--summary", default=str(DEFAULT_SUMMARY_PATH), help="요약 결과 CSV 저장 경로")
    parser.add_argument("--top-k", type=int, default=5)
    args = parser.parse_args()

    evaluate(
        profiles_path=Path(args.profiles),
        result_path=Path(args.result),
        summary_path=Path(args.summary),
        meta_path=Path(args.meta),
        index_path=Path(args.index),
        top_k=args.top_k,
    )


if __name__ == "__main__":
    main()
