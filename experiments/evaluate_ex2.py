"""
실험 2 평가 스크립트.

비교 대상:
1. FAISS only
   - SentenceTransformer + FAISS 검색 결과를 그대로 사용

2. FAISS + 도메인 리랭킹
   - 기존 run_git2value.py 방식과 동일한 구조
   - detected_domains와 채용공고 category가 맞으면 DOMAIN_BOOST만큼 가산
   - final_score = faiss_similarity + 0.05

3. FAISS + AI 분류모델 리랭킹
   - 학습된 job_classifier.pkl이 예측한 직무별 확률을 사용
   - final_score = faiss_similarity + alpha * job_probability

입력:
- experiments/cache/eval_profiles.json
- vector/git2value_metadata.json
- vector/git2value_faiss.index
- ml/models/job_classifier.pkl

출력:
- experiments/results/experiment2_result.csv
- experiments/results/experiment2_summary.csv
"""

from __future__ import annotations

import argparse
import csv
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Sequence

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from experiments.embedding_matcher import match_jobs_by_embedding  # noqa: E402
from experiments.evaluate_ex1 import (  # noqa: E402
    load_profiles,
    normalize_label,
    label_matches,
    topk_hit,
)
from ml.job_classifier import load_model_bundle, predict_profile  # noqa: E402


DEFAULT_PROFILES_PATH = PROJECT_ROOT / "experiments" / "cache" / "eval_profiles.json"
DEFAULT_META_PATH = PROJECT_ROOT / "vector" / "git2value_metadata.json"
DEFAULT_INDEX_PATH = PROJECT_ROOT / "vector" / "git2value_faiss.index"
DEFAULT_MODEL_PATH = PROJECT_ROOT / "ml" / "models" / "job_classifier.pkl"
DEFAULT_RESULT_PATH = PROJECT_ROOT / "experiments" / "results" / "ex2_result.csv"
DEFAULT_SUMMARY_PATH = PROJECT_ROOT / "experiments" / "results" / "ex2_summary.csv"


# 기존 도메인 리랭킹과 동일하게 고정 보너스 사용
DOMAIN_BOOST = 0.05

# AI 분류모델 확률 보정 계수
DEFAULT_AI_ALPHA = 0.10


DOMAIN_TO_CATEGORY_ALIAS = {
    "웹 프론트엔드": "프론트엔드",
    "프론트엔드": "프론트엔드",
    "서버/백엔드": "서버/백엔드",
    "백엔드": "서버/백엔드",
    "ML/AI": "인공지능/머신러닝",
    "인공지능/머신러닝": "인공지능/머신러닝",
    "DevOps/인프라": "devops/시스템 엔지니어",
    "DevOps/시스템 엔지니어": "devops/시스템 엔지니어",
    "devops/시스템 엔지니어": "devops/시스템 엔지니어",
    "모바일 앱": "모바일 앱",
    "게임 개발": "게임 개발",
    "블록체인": "블록체인",
    "빅데이터 엔지니어": "빅데이터 엔지니어",
}


def normalize_domain_name(domain: str) -> str:
    """
    GitHubExtractor가 만든 detected_domains 값을
    채용공고 category와 비교 가능한 이름으로 변환.
    """
    raw = str(domain or "").strip()
    return DOMAIN_TO_CATEGORY_ALIAS.get(raw, raw)


def categories_from_matches(matches: Sequence[Dict[str, Any]]) -> List[str]:
    return [str(m.get("category") or "") for m in matches]


def positions_from_matches(matches: Sequence[Dict[str, Any]]) -> str:
    return " | ".join(str(m.get("meta", {}).get("position") or "") for m in matches)


def scores_from_matches(matches: Sequence[Dict[str, Any]], score_key: str = "similarity") -> str:
    values = []
    for m in matches:
        score = float(m.get(score_key, m.get("similarity", 0.0)) or 0.0)
        values.append(f"{score:.4f}")
    return " | ".join(values)


def domain_matches_job_category(job_category: str, detected_domains: Sequence[str]) -> bool:
    """
    기존 도메인 리랭킹의 핵심 비교.

    detected_domains에 들어 있는 GitHub 도메인과
    채용공고 category가 같은 직무군이면 True.
    """
    for domain in detected_domains:
        domain_category = normalize_domain_name(domain)
        if label_matches(domain_category, job_category):
            return True
    return False


def rerank_by_domain(
    matches: Sequence[Dict[str, Any]],
    profile: Dict[str, Any],
    domain_boost: float = DOMAIN_BOOST,
) -> List[Dict[str, Any]]:
    """
    FAISS 결과에 기존 도메인 리랭킹 적용.

    원래 방식:
    - GitHub에서 감지된 도메인과 채용공고 category가 일치하면 +0.05
    - final_score = faiss_similarity + DOMAIN_BOOST
    """
    detected_domains = profile.get("detected_domains") or []

    reranked: List[Dict[str, Any]] = []

    for rank, match in enumerate(matches, start=1):
        job_category = str(match.get("category") or "")
        sim = float(match.get("similarity", 0.0) or 0.0)

        is_domain_match = domain_matches_job_category(job_category, detected_domains)
        domain_bonus = domain_boost if is_domain_match else 0.0
        effective_score = sim + domain_bonus

        reranked.append(
            {
                **match,
                "original_rank": rank,
                "domain_matched": int(is_domain_match),
                "domain_bonus": domain_bonus,
                "effective_score": effective_score,
            }
        )

    reranked.sort(key=lambda x: float(x.get("effective_score", 0.0)), reverse=True)
    return reranked


def get_probability_for_category(
    job_category: str,
    probabilities: Dict[str, float],
) -> float:
    """
    AI 분류모델의 직무별 확률 중,
    채용공고 category에 해당하는 확률을 찾는다.

    예:
    job_category = "서버/백엔드"
    probabilities = {"서버/백엔드": 0.82, "프론트엔드": 0.12}
    → 0.82
    """
    if not probabilities:
        return 0.0

    # 1. 정규화 이름이 완전히 같은 경우
    job_norm = normalize_label(job_category)
    for label, prob in probabilities.items():
        if normalize_label(label) == job_norm:
            return float(prob)

    # 2. 그룹 매칭까지 허용
    for label, prob in probabilities.items():
        if label_matches(label, job_category):
            return float(prob)

    return 0.0


def rerank_by_ai_classifier(
    matches: Sequence[Dict[str, Any]],
    probabilities: Dict[str, float],
    alpha: float = DEFAULT_AI_ALPHA,
) -> List[Dict[str, Any]]:
    """
    FAISS 결과에 AI 분류모델 확률 기반 리랭킹 적용.

    final_score = faiss_similarity + alpha * job_probability
    """
    reranked: List[Dict[str, Any]] = []

    for rank, match in enumerate(matches, start=1):
        job_category = str(match.get("category") or "")
        sim = float(match.get("similarity", 0.0) or 0.0)

        job_prob = get_probability_for_category(job_category, probabilities)
        ai_bonus = alpha * job_prob
        effective_score = sim + ai_bonus

        reranked.append(
            {
                **match,
                "original_rank": rank,
                "ai_probability": job_prob,
                "ai_bonus": ai_bonus,
                "effective_score": effective_score,
            }
        )

    reranked.sort(key=lambda x: float(x.get("effective_score", 0.0)), reverse=True)
    return reranked


def evaluate_method_result(
    repo_key: str,
    repo_url: str,
    true_label: str,
    method: str,
    matches: Sequence[Dict[str, Any]],
    top_k: int,
    extra_info: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    cats = categories_from_matches(matches)

    row: Dict[str, Any] = {
        "repo_key": repo_key,
        "repo_url": repo_url,
        "true_label": true_label,
        "true_label_normalized": normalize_label(true_label),
        "method": method,
        "top1_hit": topk_hit(true_label, cats, 1),
        "top3_hit": topk_hit(true_label, cats, min(3, top_k)),
        "top5_hit": topk_hit(true_label, cats, min(5, top_k)),
        "pred_top1_category": cats[0] if cats else "",
        "pred_categories_top5": " | ".join(cats[:5]),
        "similarities_top5": scores_from_matches(matches[:5], score_key="similarity"),
        "effective_scores_top5": scores_from_matches(matches[:5], score_key="effective_score"),
        "positions_top5": positions_from_matches(matches[:5]),
    }

    if extra_info:
        row.update(extra_info)

    return row


def update_counters(
    counters: Dict[str, Dict[str, int]],
    method: str,
    row: Dict[str, Any],
) -> None:
    counters[method]["n"] += 1
    counters[method]["top1"] += int(row["top1_hit"])
    counters[method]["top3"] += int(row["top3_hit"])
    counters[method]["top5"] += int(row["top5_hit"])


def save_detail_results(rows: List[Dict[str, Any]], result_path: Path) -> None:
    result_path.parent.mkdir(parents=True, exist_ok=True)

    fieldnames: List[str] = []
    for row in rows:
        for key in row.keys():
            if key not in fieldnames:
                fieldnames.append(key)

    with result_path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def save_summary(
    counters: Dict[str, Dict[str, int]],
    summary_path: Path,
) -> List[Dict[str, Any]]:
    summary_path.parent.mkdir(parents=True, exist_ok=True)

    methods = ["faiss_only", "domain_rerank", "ai_classifier_rerank"]

    rows: List[Dict[str, Any]] = []
    for method in methods:
        n = counters[method]["n"]
        if n == 0:
            row = {
                "method": method,
                "n": 0,
                "top1_accuracy": 0.0,
                "top3_accuracy": 0.0,
                "top5_accuracy": 0.0,
            }
        else:
            row = {
                "method": method,
                "n": n,
                "top1_accuracy": counters[method]["top1"] / n,
                "top3_accuracy": counters[method]["top3"] / n,
                "top5_accuracy": counters[method]["top5"] / n,
            }

        rows.append(row)

    with summary_path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=["method", "n", "top1_accuracy", "top3_accuracy", "top5_accuracy"],
        )
        writer.writeheader()
        writer.writerows(rows)

    return rows


def evaluate(
    profiles_path: Path,
    meta_path: Path,
    index_path: Path,
    model_path: Path,
    result_path: Path,
    summary_path: Path,
    top_k: int = 5,
    candidate_k: int = 5,
    domain_boost: float = DOMAIN_BOOST,
    ai_alpha: float = DEFAULT_AI_ALPHA,
    include_domain_hits_for_model: bool = False,
) -> Dict[str, Dict[str, float]]:
    profiles = load_profiles(profiles_path)
    model_bundle = load_model_bundle(model_path)

    valid_profiles = [
        p for p in profiles
        if not p.get("error") and str(p.get("profile_for_matching") or "").strip()
    ]

    detail_rows: List[Dict[str, Any]] = []
    counters: Dict[str, Dict[str, int]] = defaultdict(
        lambda: {"n": 0, "top1": 0, "top3": 0, "top5": 0}
    )

    for idx, profile in enumerate(valid_profiles, start=1):
        repo_key = profile.get("repo_key") or f"{profile.get('username')}/{profile.get('repo')}"
        repo_url = str(profile.get("repo_url") or "")
        true_label = str(profile.get("label") or "")
        profile_text = str(profile.get("profile_for_matching") or "")

        print(f"[{idx}/{len(valid_profiles)}] 실험 2 평가 중: {repo_key} ({true_label})")

        # 1. FAISS 검색
        # candidate_k를 top_k보다 크게 주면 더 넓은 후보군에서 리랭킹 가능.
        # 원래 코드와 동일하게 Top5 내에서만 리랭킹하려면 candidate_k=5 사용.
        faiss_candidates = match_jobs_by_embedding(
            profile_text,
            top_k=candidate_k,
            index_path=index_path,
            meta_path=meta_path,
        )

        # 2. FAISS only
        faiss_only = list(faiss_candidates[:top_k])
        faiss_only = [
            {**m, "effective_score": float(m.get("similarity", 0.0) or 0.0)}
            for m in faiss_only
        ]

        # 3. 도메인 리랭킹
        domain_reranked = rerank_by_domain(
            faiss_candidates,
            profile=profile,
            domain_boost=domain_boost,
        )[:top_k]

        # 4. AI 분류모델 리랭킹
        pred = predict_profile(
            profile=profile,
            bundle=model_bundle,
            include_domain_hits=include_domain_hits_for_model,
        )
        probabilities = pred.get("probabilities") or {}
        ai_pred_label = pred.get("pred_label", "")

        ai_reranked = rerank_by_ai_classifier(
            faiss_candidates,
            probabilities=probabilities,
            alpha=ai_alpha,
        )[:top_k]

        method_results = {
            "faiss_only": faiss_only,
            "domain_rerank": domain_reranked,
            "ai_classifier_rerank": ai_reranked,
        }

        for method, matches in method_results.items():
            extra_info: Dict[str, Any] = {}

            if method == "domain_rerank":
                extra_info["detected_domains"] = " | ".join(
                    str(x) for x in profile.get("detected_domains", [])
                )
                extra_info["domain_boost"] = domain_boost

            if method == "ai_classifier_rerank":
                top_probs = sorted(
                    probabilities.items(),
                    key=lambda x: x[1],
                    reverse=True,
                )[:5]
                extra_info["ai_pred_label"] = ai_pred_label
                extra_info["ai_top_probs"] = " | ".join(
                    f"{label}:{prob:.4f}" for label, prob in top_probs
                )
                extra_info["ai_alpha"] = ai_alpha

            row = evaluate_method_result(
                repo_key=repo_key,
                repo_url=repo_url,
                true_label=true_label,
                method=method,
                matches=matches,
                top_k=top_k,
                extra_info=extra_info,
            )

            detail_rows.append(row)
            update_counters(counters, method, row)

    save_detail_results(detail_rows, result_path)
    summary_rows = save_summary(counters, summary_path)

    print("\n[실험 2 요약]")
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

    return {
        row["method"]: {
            "n": row["n"],
            "top1_accuracy": row["top1_accuracy"],
            "top3_accuracy": row["top3_accuracy"],
            "top5_accuracy": row["top5_accuracy"],
        }
        for row in summary_rows
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="실험 2: FAISS only vs 도메인 리랭킹 vs AI 분류모델 리랭킹")
    parser.add_argument("--profiles", default=str(DEFAULT_PROFILES_PATH), help="평가용 profile JSON 경로")
    parser.add_argument("--meta", default=str(DEFAULT_META_PATH), help="채용공고 metadata JSON 경로")
    parser.add_argument("--index", default=str(DEFAULT_INDEX_PATH), help="FAISS index 경로")
    parser.add_argument("--model", default=str(DEFAULT_MODEL_PATH), help="학습된 job_classifier.pkl 경로")
    parser.add_argument("--result", default=str(DEFAULT_RESULT_PATH), help="상세 결과 CSV 저장 경로")
    parser.add_argument("--summary", default=str(DEFAULT_SUMMARY_PATH), help="요약 결과 CSV 저장 경로")
    parser.add_argument("--top-k", type=int, default=5, help="최종 평가 Top-k")
    parser.add_argument(
        "--candidate-k",
        type=int,
        default=5,
        help="FAISS에서 처음 가져올 후보 수. 원래 Top5 리랭킹이면 5, 후보군 확장 실험이면 10~20",
    )
    parser.add_argument("--domain-boost", type=float, default=DOMAIN_BOOST, help="도메인 리랭킹 보너스")
    parser.add_argument("--ai-alpha", type=float, default=DEFAULT_AI_ALPHA, help="AI 분류모델 확률 보정 계수")
    parser.add_argument(
        "--include-domain-hits-for-model",
        action="store_true",
        help="domain_hits_merged를 포함해서 학습한 모델일 경우 사용",
    )

    args = parser.parse_args()

    if args.candidate_k < args.top_k:
        raise ValueError("--candidate-k는 --top-k보다 크거나 같아야 합니다.")

    evaluate(
        profiles_path=Path(args.profiles),
        meta_path=Path(args.meta),
        index_path=Path(args.index),
        model_path=Path(args.model),
        result_path=Path(args.result),
        summary_path=Path(args.summary),
        top_k=args.top_k,
        candidate_k=args.candidate_k,
        domain_boost=args.domain_boost,
        ai_alpha=args.ai_alpha,
        include_domain_hits_for_model=args.include_domain_hits_for_model,
    )


if __name__ == "__main__":
    main()