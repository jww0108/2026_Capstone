"""
학습된 직무 분류 모델로 GitHub 레포의 직무 확률을 예측하는 스크립트.

입력:
- experiments/cache/eval_profiles.json 또는 train_profiles.json
- ml/models/job_classifier.pkl

출력:
- 각 repo별 직무별 확률
- 선택적으로 CSV 저장

실행 예시:
python ml/job_classifier.py ^
  --input experiments/cache/eval_profiles.json ^
  --model ml/models/job_classifier.pkl ^
  --output experiments/results/job_classifier_predictions.csv
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path
from typing import Any, Dict, List

import joblib
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]

# 프로젝트 루트 import 가능하게 처리
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from ml.feature_extractor import extract_numeric_features, load_profiles  # noqa: E402


DEFAULT_INPUT_PATH = PROJECT_ROOT / "experiments" / "cache" / "eval_profiles.json"
DEFAULT_MODEL_PATH = PROJECT_ROOT / "ml" / "models" / "job_classifier.pkl"
DEFAULT_OUTPUT_PATH = PROJECT_ROOT / "experiments" / "results" / "job_classifier_predictions.csv"


def load_model_bundle(model_path: Path) -> Dict[str, Any]:
    """학습된 모델 번들 로드."""
    if not model_path.exists():
        raise FileNotFoundError(f"모델 파일이 없습니다: {model_path}")

    bundle = joblib.load(model_path)

    if not isinstance(bundle, dict):
        raise ValueError("모델 파일 형식이 올바르지 않습니다. dict bundle이어야 합니다.")

    required_keys = {"model", "feature_columns", "labels"}
    missing = required_keys - set(bundle.keys())
    if missing:
        raise ValueError(f"모델 번들에 필요한 키가 없습니다: {missing}")

    return bundle


def profile_to_model_input(
    profile: Dict[str, Any],
    feature_columns: List[str],
    include_domain_hits: bool = False,
) -> pd.DataFrame:
    """
    profile JSON 1개를 모델 입력 X 1행으로 변환.

    학습 때 저장된 feature_columns 순서에 맞춰야 하므로,
    없는 컬럼은 0으로 채우고, 불필요한 컬럼은 제거한다.
    """
    features = extract_numeric_features(
        profile,
        include_domain_hits=include_domain_hits,
    )

    row: Dict[str, Any] = {}
    for col in feature_columns:
        value = features.get(col, 0.0)
        row[col] = value

    X = pd.DataFrame([row])

    for col in X.columns:
        X[col] = pd.to_numeric(X[col], errors="coerce").fillna(0.0)

    return X


def predict_profile(
    profile: Dict[str, Any],
    bundle: Dict[str, Any],
    include_domain_hits: bool = False,
) -> Dict[str, Any]:
    """
    레포 하나에 대해 직무별 확률 예측.
    """
    model = bundle["model"]
    feature_columns = list(bundle["feature_columns"])

    X = profile_to_model_input(
        profile=profile,
        feature_columns=feature_columns,
        include_domain_hits=include_domain_hits,
    )

    pred_label = str(model.predict(X)[0])

    # RandomForestClassifier는 predict_proba 지원
    if hasattr(model, "predict_proba"):
        probs = model.predict_proba(X)[0]
        classes = list(model.classes_)

        prob_map = {
            str(label): float(prob)
            for label, prob in zip(classes, probs)
        }
    else:
        prob_map = {pred_label: 1.0}

    return {
        "repo_key": profile.get("repo_key", ""),
        "repo_url": profile.get("repo_url", ""),
        "true_label": profile.get("label", ""),
        "pred_label": pred_label,
        "probabilities": prob_map,
    }


def predict_profiles(
    profiles: List[Dict[str, Any]],
    bundle: Dict[str, Any],
    include_domain_hits: bool = False,
) -> List[Dict[str, Any]]:
    """
    여러 레포에 대해 예측 수행.
    """
    results: List[Dict[str, Any]] = []

    valid_profiles = [
        p for p in profiles
        if not p.get("error") and str(p.get("profile_for_matching") or "").strip()
    ]

    for idx, profile in enumerate(valid_profiles, start=1):
        repo_key = profile.get("repo_key") or f"{profile.get('username')}/{profile.get('repo')}"
        print(f"[{idx}/{len(valid_profiles)}] 직무 확률 예측 중: {repo_key}")

        result = predict_profile(
            profile=profile,
            bundle=bundle,
            include_domain_hits=include_domain_hits,
        )
        results.append(result)

    return results


def flatten_prediction_row(result: Dict[str, Any], label_order: List[str]) -> Dict[str, Any]:
    """
    CSV 저장용으로 probabilities dict를 펼침.

    예:
    probabilities = {"서버/백엔드": 0.7, "프론트엔드": 0.2}

    CSV:
    prob_서버_백엔드 = 0.7
    prob_프론트엔드 = 0.2
    """
    row: Dict[str, Any] = {
        "repo_key": result.get("repo_key", ""),
        "repo_url": result.get("repo_url", ""),
        "true_label": result.get("true_label", ""),
        "pred_label": result.get("pred_label", ""),
    }

    probs = result.get("probabilities") or {}

    for label in label_order:
        safe_label = (
            str(label)
            .replace("/", "_")
            .replace(" ", "_")
            .replace("\\", "_")
        )
        row[f"prob_{safe_label}"] = float(probs.get(label, 0.0))

    return row


def save_predictions_csv(
    results: List[Dict[str, Any]],
    output_path: Path,
    label_order: List[str],
) -> None:
    """예측 결과 CSV 저장."""
    output_path.parent.mkdir(parents=True, exist_ok=True)

    rows = [
        flatten_prediction_row(result, label_order=label_order)
        for result in results
    ]

    if not rows:
        raise ValueError("저장할 예측 결과가 없습니다.")

    fieldnames: List[str] = []
    for row in rows:
        for key in row.keys():
            if key not in fieldnames:
                fieldnames.append(key)

    with output_path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"\n예측 결과 저장 완료: {output_path}")


def print_prediction_summary(results: List[Dict[str, Any]], top_n: int = 3) -> None:
    """콘솔에 예측 결과 요약 출력."""
    print("\n[직무 분류 예측 요약]")

    for result in results:
        repo_key = result.get("repo_key", "")
        true_label = result.get("true_label", "")
        pred_label = result.get("pred_label", "")
        probs = result.get("probabilities") or {}

        top_probs = sorted(
            probs.items(),
            key=lambda x: x[1],
            reverse=True,
        )[:top_n]

        top_text = " | ".join(
            f"{label}: {prob:.3f}"
            for label, prob in top_probs
        )

        print(f"- {repo_key}")
        print(f"  true={true_label}, pred={pred_label}")
        print(f"  top{top_n}: {top_text}")


def main() -> None:
    parser = argparse.ArgumentParser(description="학습된 GitHub 직무 분류 모델로 직무 확률 예측")
    parser.add_argument(
        "--input",
        default=str(DEFAULT_INPUT_PATH),
        help="예측할 profile JSON 경로",
    )
    parser.add_argument(
        "--model",
        default=str(DEFAULT_MODEL_PATH),
        help="학습된 job_classifier.pkl 경로",
    )
    parser.add_argument(
        "--output",
        default=str(DEFAULT_OUTPUT_PATH),
        help="예측 결과 CSV 저장 경로",
    )
    parser.add_argument(
        "--include-domain-hits",
        action="store_true",
        help="feature_extractor.py에서 domain_hits_merged 특징을 포함해 학습한 모델일 때 사용",
    )
    parser.add_argument(
        "--no-save",
        action="store_true",
        help="CSV 저장 없이 콘솔 출력만 수행",
    )
    args = parser.parse_args()

    input_path = Path(args.input)
    model_path = Path(args.model)
    output_path = Path(args.output)

    bundle = load_model_bundle(model_path)
    profiles = load_profiles(input_path)

    results = predict_profiles(
        profiles=profiles,
        bundle=bundle,
        include_domain_hits=args.include_domain_hits,
    )

    label_order = list(bundle.get("labels") or getattr(bundle["model"], "classes_", []))

    print_prediction_summary(results, top_n=3)

    if not args.no_save:
        save_predictions_csv(
            results=results,
            output_path=output_path,
            label_order=label_order,
        )


if __name__ == "__main__":
    main()