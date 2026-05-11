"""
GitHub profile JSON -> ML 학습용 숫자 특징 CSV 변환 스크립트.

입력:
- experiments/cache/eval_profiles.json
- collect_eval_profiles.py가 생성한 JSON

출력:
- ml/dataset/job_training_data.csv

기본 원칙:
- 비교 공정성을 위해 profile_for_matching 텍스트를 중심으로 특징값을 추출한다.
- domain_hits_merged는 기본적으로 사용하지 않는다.
- 필요하면 --include-domain-hits 옵션으로 추가 가능하다.

실행 예시:
python ml/feature_extractor.py ^
  --input experiments/cache/train_profiles.json ^
  --output ml/dataset/job_training_data.csv

domain_hits_merged까지 포함하고 싶을 때:
python ml/feature_extractor.py ^
  --input experiments/cache/train_profiles.json ^
  --output ml/dataset/job_training_data.csv ^
  --include-domain-hits
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, List


PROJECT_ROOT = Path(__file__).resolve().parents[1]


LANGUAGE_COLUMNS = [
    "python_ratio",
    "java_ratio",
    "javascript_ratio",
    "typescript_ratio",
    "kotlin_ratio",
    "dart_ratio",
    "swift_ratio",
    "csharp_ratio",
    "cpp_ratio",
    "html_ratio",
    "css_ratio",
    "go_ratio",
    "php_ratio",
    "ruby_ratio",
    "solidity_ratio",
]

LANGUAGE_ALIASES = {
    "python": "python_ratio",
    "java": "java_ratio",
    "javascript": "javascript_ratio",
    "typescript": "typescript_ratio",
    "kotlin": "kotlin_ratio",
    "dart": "dart_ratio",
    "swift": "swift_ratio",
    "c#": "csharp_ratio",
    "csharp": "csharp_ratio",
    "c++": "cpp_ratio",
    "cpp": "cpp_ratio",
    "html": "html_ratio",
    "css": "css_ratio",
    "go": "go_ratio",
    "golang": "go_ratio",
    "php": "php_ratio",
    "ruby": "ruby_ratio",
    "solidity": "solidity_ratio",
}

FRAMEWORK_KEYWORDS = {
    "has_spring": ["spring", "spring boot", "springboot"],
    "has_fastapi": ["fastapi"],
    "has_django": ["django"],
    "has_flask": ["flask"],
    "has_express": ["express"],
    "has_nestjs": ["nestjs", "nest.js"],
    "has_react": ["react"],
    "has_nextjs": ["next.js", "nextjs"],
    "has_vue": ["vue", "vue.js"],
    "has_flutter": ["flutter"],
    "has_react_native": ["react native"],
    "has_unity": ["unity"],
    "has_unreal": ["unreal"],
    "has_pytorch": ["pytorch", "torch"],
    "has_tensorflow": ["tensorflow", "keras"],
    "has_yolo": ["yolo"],
    "has_opencv": ["opencv"],
    "has_streamlit": ["streamlit"],
    "has_docker": ["docker", "dockerfile", "docker compose"],
    "has_kubernetes": ["kubernetes", "k8s"],
    "has_aws": ["aws", "ec2", "s3", "eks", "ecs"],
    "has_terraform": ["terraform"],
    "has_github_actions": ["github actions", "github action"],
    "has_jenkins": ["jenkins"],
    "has_solidity": ["solidity", "foundry", "hardhat", "smart contract", "스마트 컨트랙트"],
}

KEYWORD_FEATURES = {
    # backend
    "kw_backend": ["backend", "back-end", "백엔드", "서버"],
    "kw_api": ["api", "rest", "restful", "endpoint", "엔드포인트"],
    "kw_database": ["database", "db", "mysql", "postgresql", "mongodb", "redis", "데이터베이스"],
    "kw_auth": ["auth", "jwt", "oauth", "인증", "로그인"],
    "kw_orm": ["orm", "jpa", "hibernate", "prisma", "sqlmodel", "sequelize"],

    # frontend
    "kw_frontend": ["frontend", "front-end", "프론트엔드", "프론트", "web", "웹"],
    "kw_ui": ["ui", "ux", "component", "컴포넌트", "반응형", "responsive"],
    "kw_seo": ["seo"],

    # ai/data
    "kw_ai": ["ai", "인공지능", "머신러닝", "machine learning", "ml", "딥러닝", "deep learning"],
    "kw_model": ["model", "모델", "train", "학습", "classification", "regression", "분류", "회귀"],
    "kw_cv": ["opencv", "yolo", "detection", "segmentation", "computer vision", "객체", "영상", "이미지"],
    "kw_data": ["data", "데이터", "pandas", "numpy", "spark", "pyspark", "분석"],

    # devops
    "kw_devops": ["devops", "ci/cd", "cicd", "pipeline", "deploy", "배포"],
    "kw_container": ["docker", "container", "컨테이너"],
    "kw_cloud": ["aws", "cloud", "클라우드", "ec2", "s3", "eks"],
    "kw_monitoring": ["monitoring", "grafana", "prometheus", "모니터링"],

    # mobile
    "kw_mobile": ["mobile", "모바일", "app", "앱", "android", "ios", "안드로이드"],
    "kw_flutter": ["flutter", "dart"],
    "kw_kotlin": ["kotlin"],
    "kw_swift": ["swift"],

    # game
    "kw_game": ["game", "게임", "unity", "unreal", "fps", "캐릭터", "player"],

    # blockchain
    "kw_blockchain": ["blockchain", "블록체인", "solidity", "smart contract", "hyperledger", "fabric", "토큰"],
}

DOMAIN_COLUMNS = [
    "domain_backend_score",
    "domain_frontend_score",
    "domain_ai_score",
    "domain_devops_score",
    "domain_mobile_score",
    "domain_game_score",
    "domain_blockchain_score",
]

DOMAIN_NAME_TO_COLUMN = {
    "서버/백엔드": "domain_backend_score",
    "웹 프론트엔드": "domain_frontend_score",
    "프론트엔드": "domain_frontend_score",
    "ML/AI": "domain_ai_score",
    "인공지능/머신러닝": "domain_ai_score",
    "DevOps/인프라": "domain_devops_score",
    "devops/시스템 엔지니어": "domain_devops_score",
    "모바일 앱": "domain_mobile_score",
    "게임 개발": "domain_game_score",
    "블록체인": "domain_blockchain_score",
}


def load_profiles(path: Path) -> List[Dict[str, Any]]:
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    if isinstance(data, dict):
        data = list(data.values())

    if not isinstance(data, list):
        raise ValueError("입력 JSON은 list 또는 dict 형식이어야 합니다.")

    return data


def normalize_text(text: str) -> str:
    return (text or "").lower()


def contains_any(text: str, keywords: List[str]) -> int:
    lower = normalize_text(text)
    return int(any(k.lower() in lower for k in keywords))


def parse_language_ratios(profile: Dict[str, Any]) -> Dict[str, float]:
    """
    언어 비율 추출.

    1순위: per_repo[0].language_category
    2순위: metrics_summary.top_languages 문자열
    3순위: profile_for_matching 문자열
    """
    result = {col: 0.0 for col in LANGUAGE_COLUMNS}

    # 1. per_repo language_category에서 추출
    per_repo = profile.get("per_repo") or []
    if per_repo:
        lang_cat = per_repo[0].get("language_category") or {}
        for group in ["main", "sub", "trivial"]:
            for item in lang_cat.get(group, []) or []:
                if not isinstance(item, list) or len(item) < 2:
                    continue
                lang = str(item[0]).strip().lower()
                ratio = float(item[1]) / 100.0
                col = LANGUAGE_ALIASES.get(lang)
                if col:
                    result[col] = max(result[col], ratio)

    # 이미 값이 있으면 반환
    if any(v > 0 for v in result.values()):
        return result

    # 2. top_languages 문자열에서 추출
    top_languages = str((profile.get("metrics_summary") or {}).get("top_languages") or "")
    _parse_language_text_into_result(top_languages, result)

    if any(v > 0 for v in result.values()):
        return result

    # 3. profile_for_matching에서 추출
    profile_text = str(profile.get("profile_for_matching") or "")
    _parse_language_text_into_result(profile_text, result)

    return result


def _parse_language_text_into_result(text: str, result: Dict[str, float]) -> None:
    """
    예: 'Java (87%), JavaScript (11%)' 형태 파싱
    """
    pattern = re.compile(r"([A-Za-z+#]+)\s*\((\d+(?:\.\d+)?)%\)")
    for lang, pct in pattern.findall(text or ""):
        lang_key = lang.strip().lower()
        col = LANGUAGE_ALIASES.get(lang_key)
        if col:
            result[col] = max(result[col], float(pct) / 100.0)


def extract_numeric_features(
    profile: Dict[str, Any],
    include_domain_hits: bool = False,
) -> Dict[str, Any]:
    text = str(profile.get("profile_for_matching") or "")
    per_repo = profile.get("per_repo") or []
    repo0 = per_repo[0] if per_repo else {}

    features: Dict[str, Any] = {}

    # 기본 식별자
    features["repo_key"] = profile.get("repo_key", "")
    features["repo_url"] = profile.get("repo_url", "")

    # 1. 언어 비율
    features.update(parse_language_ratios(profile))

    # 2. 프레임워크/기술 키워드
    for col, keywords in FRAMEWORK_KEYWORDS.items():
        combined_text = text + " " + " ".join(repo0.get("frameworks") or [])
        features[col] = contains_any(combined_text, keywords)

    # 3. 일반 키워드 특징
    for col, keywords in KEYWORD_FEATURES.items():
        features[col] = contains_any(text, keywords)

    # 4. profile_for_matching 자체의 간단한 길이 특징
    features["profile_text_len"] = len(text)
    features["profile_token_count"] = len(text.split())
    features["profile_keyword_count"] = sum(
        features[col] for col in KEYWORD_FEATURES.keys()
    )

    # 5. 품질/활동 특징
    metrics = profile.get("metrics_summary") or {}

    features["github_score"] = float(profile.get("github_score") or 0.0)
    features["total_valid_loc"] = float(metrics.get("total_valid_loc") or 0.0)
    features["total_evidence_loc"] = float(metrics.get("total_evidence_loc") or 0.0)
    features["total_commits_analyzed"] = float(metrics.get("total_commits_analyzed") or 0.0)

    features["has_tests"] = int(bool(repo0.get("has_tests")))
    features["has_cicd"] = int(bool(repo0.get("has_cicd")))
    features["has_deployment"] = int(bool(repo0.get("has_deployment")))
    features["readme_has_image"] = int(bool(repo0.get("readme_has_image")))
    features["test_ratio"] = float(repo0.get("test_ratio") or 0.0)

    tree_stats = repo0.get("tree_stats") or {}
    features["source_file_count"] = float(tree_stats.get("source_file_count") or 0.0)
    features["avg_loc_per_file"] = float(tree_stats.get("avg_loc_per_file") or 0.0)

    readme = str(repo0.get("readme") or "")
    features["readme_len"] = len(readme)

    # 6. 도메인 히트 특징
    # 기본값은 사용하지 않음. AI 분류모델이 도메인 리랭킹을 그대로 복사하지 않도록 하기 위함.
    if include_domain_hits:
        domain_hits = profile.get("domain_hits_merged") or {}
        for col in DOMAIN_COLUMNS:
            features[col] = 0.0

        for domain_name, score in domain_hits.items():
            col = DOMAIN_NAME_TO_COLUMN.get(str(domain_name))
            if col:
                features[col] = float(score or 0.0)

    # 정답 라벨
    features["label"] = profile.get("label", "")

    return features


def build_dataset(
    profiles: List[Dict[str, Any]],
    include_domain_hits: bool = False,
) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []

    for profile in profiles:
        if profile.get("error"):
            continue

        if not str(profile.get("profile_for_matching") or "").strip():
            continue

        if not str(profile.get("label") or "").strip():
            continue

        rows.append(extract_numeric_features(profile, include_domain_hits=include_domain_hits))

    return rows


def save_csv(rows: List[Dict[str, Any]], output_path: Path) -> None:
    if not rows:
        raise ValueError("저장할 데이터가 없습니다.")

    output_path.parent.mkdir(parents=True, exist_ok=True)

    # 모든 row의 key 합집합을 컬럼으로 사용
    fieldnames: List[str] = []
    for row in rows:
        for key in row.keys():
            if key not in fieldnames:
                fieldnames.append(key)

    # label은 마지막으로 보내기
    if "label" in fieldnames:
        fieldnames.remove("label")
        fieldnames.append("label")

    with output_path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description="GitHub profile JSON을 ML 학습용 특징 CSV로 변환")
    parser.add_argument(
        "--input",
        default=str(PROJECT_ROOT / "experiments" / "cache" / "train_profiles.json"),
        help="collect_eval_profiles.py가 만든 profile JSON 경로",
    )
    parser.add_argument(
        "--output",
        default=str(PROJECT_ROOT / "ml" / "dataset" / "job_training_data.csv"),
        help="저장할 학습용 CSV 경로",
    )
    parser.add_argument(
        "--include-domain-hits",
        action="store_true",
        help="domain_hits_merged를 특징값으로 포함할지 여부",
    )
    args = parser.parse_args()

    profiles = load_profiles(Path(args.input))
    rows = build_dataset(profiles, include_domain_hits=args.include_domain_hits)
    save_csv(rows, Path(args.output))

    labels = {}
    for row in rows:
        labels[row["label"]] = labels.get(row["label"], 0) + 1

    print(f"입력 프로필 수: {len(profiles)}")
    print(f"변환된 학습 데이터 수: {len(rows)}")
    print(f"저장 위치: {args.output}")
    print("라벨 분포:")
    for label, count in sorted(labels.items()):
        print(f"  - {label}: {count}")


if __name__ == "__main__":
    main()