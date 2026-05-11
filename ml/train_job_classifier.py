"""
직무 분류 모델 학습 스크립트.

입력:
- ml/dataset/job_training_data.csv
  feature_extractor.py가 생성한 숫자 특징값 CSV

출력:
- ml/models/job_classifier.pkl
  학습된 모델 + 특징 컬럼 + 라벨 정보 저장

실행 예시:
python ml/train_job_classifier.py

경로 직접 지정:
python ml/train_job_classifier.py ^
  --input ml/dataset/job_training_data.csv ^
  --output ml/models/job_classifier.pkl
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple

import joblib
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix
from sklearn.model_selection import train_test_split


PROJECT_ROOT = Path(__file__).resolve().parents[1]


DROP_COLUMNS = [
    "repo_key",
    "repo_url",
    "label",
]


def load_training_data(csv_path: Path) -> pd.DataFrame:
    """학습용 CSV 로드."""
    if not csv_path.exists():
        raise FileNotFoundError(f"학습 데이터가 없습니다: {csv_path}")

    df = pd.read_csv(csv_path, encoding="utf-8-sig")

    if "label" not in df.columns:
        raise ValueError("CSV에 label 컬럼이 필요합니다.")

    # label 없는 행 제거
    df = df[df["label"].notna()]
    df = df[df["label"].astype(str).str.strip() != ""]

    if len(df) == 0:
        raise ValueError("유효한 학습 데이터가 없습니다.")

    return df


def prepare_xy(df: pd.DataFrame) -> Tuple[pd.DataFrame, pd.Series, List[str]]:
    """
    X, y 분리.

    X = 숫자 특징값
    y = 정답 직무 라벨
    """
    y = df["label"].astype(str)

    feature_columns = [
        col for col in df.columns
        if col not in DROP_COLUMNS
    ]

    X = df[feature_columns].copy()

    # 혹시 숫자가 아닌 값이 섞이면 숫자로 변환, 실패하면 0 처리
    for col in X.columns:
        X[col] = pd.to_numeric(X[col], errors="coerce").fillna(0.0)

    return X, y, feature_columns


def can_stratify(y: pd.Series) -> bool:
    """
    stratify 가능 여부 확인.

    train_test_split에서 stratify를 쓰려면
    각 라벨이 최소 2개 이상 있어야 함.
    """
    counts = y.value_counts()
    return len(counts) >= 2 and counts.min() >= 2


def split_data(
    X: pd.DataFrame,
    y: pd.Series,
    test_size: float,
    random_state: int,
) -> Tuple[pd.DataFrame, pd.DataFrame, pd.Series, pd.Series]:
    """학습/검증 데이터 분리."""
    stratify = y if can_stratify(y) else None

    if stratify is None:
        print("[경고] 일부 라벨의 데이터가 1개뿐이라 stratify 없이 분리합니다.")

    return train_test_split(
        X,
        y,
        test_size=test_size,
        random_state=random_state,
        stratify=stratify,
    )


def train_model(
    X_train: pd.DataFrame,
    y_train: pd.Series,
    random_state: int,
) -> RandomForestClassifier:
    """RandomForest 기반 직무 분류 모델 학습."""
    model = RandomForestClassifier(
        n_estimators=300,
        max_depth=None,
        min_samples_split=2,
        min_samples_leaf=1,
        class_weight="balanced",
        random_state=random_state,
        n_jobs=-1,
    )

    model.fit(X_train, y_train)
    return model


def evaluate_model(
    model: RandomForestClassifier,
    X_test: pd.DataFrame,
    y_test: pd.Series,
) -> Dict[str, Any]:
    """검증 데이터로 성능 확인."""
    y_pred = model.predict(X_test)

    acc = accuracy_score(y_test, y_pred)
    labels = sorted(y_test.unique().tolist())

    print("\n[검증 결과]")
    print(f"Accuracy: {acc:.4f}")

    print("\n[Classification Report]")
    print(
        classification_report(
            y_test,
            y_pred,
            zero_division=0,
        )
    )

    print("[Confusion Matrix]")
    cm = confusion_matrix(y_test, y_pred, labels=labels)
    cm_df = pd.DataFrame(cm, index=[f"true:{x}" for x in labels], columns=[f"pred:{x}" for x in labels])
    print(cm_df)

    return {
        "accuracy": float(acc),
        "labels": labels,
        "confusion_matrix": cm.tolist(),
    }


def print_feature_importance(
    model: RandomForestClassifier,
    feature_columns: List[str],
    top_n: int = 20,
) -> List[Dict[str, Any]]:
    """중요 특징값 출력."""
    importances = model.feature_importances_

    pairs = sorted(
        zip(feature_columns, importances),
        key=lambda x: x[1],
        reverse=True,
    )

    print(f"\n[상위 {top_n}개 중요 특징]")
    result = []
    for name, score in pairs[:top_n]:
        print(f"{name}: {score:.4f}")
        result.append({"feature": name, "importance": float(score)})

    return result


def save_model_bundle(
    model: RandomForestClassifier,
    output_path: Path,
    feature_columns: List[str],
    label_list: List[str],
    metrics: Dict[str, Any],
    feature_importance: List[Dict[str, Any]],
) -> None:
    """
    모델 저장.

    단순 모델만 저장하지 않고,
    나중에 예측할 때 필요한 feature_columns도 같이 저장한다.
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)

    bundle = {
        "model": model,
        "feature_columns": feature_columns,
        "labels": label_list,
        "metrics": metrics,
        "feature_importance": feature_importance,
    }

    joblib.dump(bundle, output_path)
    print(f"\n모델 저장 완료: {output_path}")


def save_training_report(
    report_path: Path,
    label_counts: Dict[str, int],
    feature_columns: List[str],
    metrics: Dict[str, Any],
    feature_importance: List[Dict[str, Any]],
) -> None:
    """학습 리포트 JSON 저장."""
    report_path.parent.mkdir(parents=True, exist_ok=True)

    report = {
        "label_counts": label_counts,
        "num_features": len(feature_columns),
        "feature_columns": feature_columns,
        "metrics": metrics,
        "feature_importance": feature_importance,
    }

    with report_path.open("w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    print(f"학습 리포트 저장 완료: {report_path}")


def main() -> None:
    parser = argparse.ArgumentParser(description="GitHub 특징값 기반 직무 분류 모델 학습")
    parser.add_argument(
        "--input",
        default=str(PROJECT_ROOT / "ml" / "dataset" / "job_training_data.csv"),
        help="feature_extractor.py가 생성한 학습 CSV 경로",
    )
    parser.add_argument(
        "--output",
        default=str(PROJECT_ROOT / "ml" / "models" / "job_classifier.pkl"),
        help="학습된 모델 저장 경로",
    )
    parser.add_argument(
        "--report",
        default=str(PROJECT_ROOT / "ml" / "models" / "job_classifier_report.json"),
        help="학습 리포트 저장 경로",
    )
    parser.add_argument(
        "--test-size",
        type=float,
        default=0.25,
        help="검증 데이터 비율",
    )
    parser.add_argument(
        "--random-state",
        type=int,
        default=42,
        help="랜덤 시드",
    )
    args = parser.parse_args()

    csv_path = Path(args.input)
    output_path = Path(args.output)
    report_path = Path(args.report)

    df = load_training_data(csv_path)
    X, y, feature_columns = prepare_xy(df)

    label_counts = y.value_counts().to_dict()

    print("[학습 데이터 정보]")
    print(f"전체 데이터 수: {len(df)}")
    print(f"특징값 개수: {len(feature_columns)}")
    print("라벨 분포:")
    for label, count in label_counts.items():
        print(f"  - {label}: {count}")

    X_train, X_test, y_train, y_test = split_data(
        X,
        y,
        test_size=args.test_size,
        random_state=args.random_state,
    )

    print("\n[데이터 분리]")
    print(f"학습 데이터: {len(X_train)}개")
    print(f"검증 데이터: {len(X_test)}개")

    model = train_model(
        X_train=X_train,
        y_train=y_train,
        random_state=args.random_state,
    )

    metrics = evaluate_model(
        model=model,
        X_test=X_test,
        y_test=y_test,
    )

    feature_importance = print_feature_importance(
        model=model,
        feature_columns=feature_columns,
        top_n=20,
    )

    label_list = sorted(y.unique().tolist())

    save_model_bundle(
        model=model,
        output_path=output_path,
        feature_columns=feature_columns,
        label_list=label_list,
        metrics=metrics,
        feature_importance=feature_importance,
    )

    save_training_report(
        report_path=report_path,
        label_counts=label_counts,
        feature_columns=feature_columns,
        metrics=metrics,
        feature_importance=feature_importance,
    )


if __name__ == "__main__":
    main()