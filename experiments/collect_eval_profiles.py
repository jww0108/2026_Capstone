"""
실험용 GitHub 프로필 수집 스크립트.

목적
- eval_repos.csv에 적힌 평가 레포를 기존 GitHubExtractor로 분석한다.
- 원본 코드에서 생성하는 profile_for_matching, domain_hits_merged, per_repo 등을 그대로 캐시한다.
- 이후 keyword_matcher.py / embedding_matcher.py / evaluate_experiment1.py에서 같은 입력 조건으로 비교할 수 있게 한다.

기본 입력 CSV 형식
    username,repo,label
    jww0108,2026_Capstone,서버/백엔드

또는 repo_url 형식도 지원
    repo_url,label
    https://github.com/jww0108/2026_Capstone,서버/백엔드

실행 예시
    python experiments/collect_eval_profiles.py
    python experiments/collect_eval_profiles.py --input experiments/eval_repos.csv --output experiments/cache/eval_profiles.json
    python experiments/collect_eval_profiles.py --force
"""

from __future__ import annotations

import argparse
import asyncio
import csv
import json
import os
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple

# experiments/에서 실행해도 프로젝트 루트 모듈을 import할 수 있게 처리
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from github_extractor import GitHubExtractor  # noqa: E402


def _parse_repo_url(repo_url: str) -> Tuple[str, str]:
    """GitHub URL에서 (username, repo) 추출."""
    repo_url = (repo_url or "").strip()
    m = re.search(r"github\.com[:/](?P<owner>[^/]+)/(?P<repo>[^/#?]+)", repo_url)
    if not m:
        raise ValueError(f"repo_url 형식을 해석할 수 없습니다: {repo_url}")
    repo = m.group("repo").replace(".git", "")
    return m.group("owner"), repo


def _read_eval_rows(input_path: Path) -> List[Dict[str, str]]:
    """eval_repos.csv 로드. username/repo 방식과 repo_url 방식을 모두 지원."""
    if not input_path.exists():
        raise FileNotFoundError(
            f"평가 CSV가 없습니다: {input_path}\n"
            "먼저 experiments/eval_repos.csv를 만들어 주세요."
        )

    rows: List[Dict[str, str]] = []
    with input_path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        required_any = {"repo_url", "username"}
        if not reader.fieldnames or not (required_any & set(reader.fieldnames)):
            raise ValueError(
                "CSV에는 repo_url 또는 username/repo 컬럼이 필요합니다. "
                "권장 형식: username,repo,label"
            )

        for i, row in enumerate(reader, start=2):
            label = (row.get("label") or row.get("job_label") or "").strip()
            if not label:
                raise ValueError(f"{i}행에 label이 없습니다.")

            if row.get("repo_url"):
                username, repo = _parse_repo_url(row["repo_url"])
                repo_url = row["repo_url"].strip()
            else:
                username = (row.get("username") or row.get("owner") or "").strip()
                repo = (row.get("repo") or row.get("repository") or "").strip()
                if not username or not repo:
                    raise ValueError(f"{i}행에 username/repo 정보가 부족합니다.")
                repo_url = f"https://github.com/{username}/{repo}"

            rows.append(
                {
                    "username": username,
                    "repo": repo,
                    "repo_url": repo_url,
                    "label": label,
                }
            )
    return rows


def _load_existing_cache(output_path: Path) -> Dict[str, Dict[str, Any]]:
    if not output_path.exists():
        return {}
    with output_path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    if isinstance(data, list):
        return {item.get("repo_key", f"idx:{i}"): item for i, item in enumerate(data)}
    if isinstance(data, dict):
        return data
    return {}


def _profile_to_cache_item(row: Dict[str, str], profile: Dict[str, Any]) -> Dict[str, Any]:
    """원본 profile 중 실험에 필요한 필드를 보존."""
    repo_key = f"{row['username']}/{row['repo']}"
    return {
        "repo_key": repo_key,
        "username": row["username"],
        "repo": row["repo"],
        "repo_url": row["repo_url"],
        "label": row["label"],
        # 실험 1의 공통 입력: 원본 build_profile_text() 결과
        "profile_for_matching": profile.get("profile_for_matching", ""),
        # 실험 2 도메인 리랭킹용: 원본 도메인 감지 결과
        "domain_hits_merged": profile.get("domain_hits_merged") or {},
        "detected_domains": list((profile.get("domain_hits_merged") or {}).keys()),
        # 추후 분석/오류 검토용
        "github_score": profile.get("github_score"),
        "score_breakdown": profile.get("score_breakdown"),
        "metrics_summary": profile.get("metrics_summary"),
        "warnings": profile.get("warnings") or [],
        "per_repo": profile.get("per_repo") or [],
    }


async def collect_profiles(input_path: Path, output_path: Path, force: bool = False) -> List[Dict[str, Any]]:
    rows = _read_eval_rows(input_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    cache = _load_existing_cache(output_path)
    extractor = GitHubExtractor()

    for idx, row in enumerate(rows, start=1):
        repo_key = f"{row['username']}/{row['repo']}"
        if not force and repo_key in cache and cache[repo_key].get("profile_for_matching"):
            print(f"[{idx}/{len(rows)}] 캐시 사용: {repo_key}")
            continue

        print(f"[{idx}/{len(rows)}] GitHub 분석 중: {repo_key}")
        try:
            repo_full_name = f"{row['username']}/{row['repo']}"
            profile = await extractor.extract_applicant_profile(row["username"], [repo_full_name])
            cache[repo_key] = _profile_to_cache_item(row, profile)
        except Exception as e:  # 실험 전체가 멈추지 않도록 실패도 기록
            cache[repo_key] = {
                "repo_key": repo_key,
                "username": row["username"],
                "repo": row["repo"],
                "repo_url": row["repo_url"],
                "label": row["label"],
                "error": repr(e),
                "profile_for_matching": "",
                "domain_hits_merged": {},
                "detected_domains": [],
            }
            print(f"  실패: {repo_key} -> {e!r}")

        # 중간 저장: GitHub API 제한/중단 상황에서도 진행분 보존
        with output_path.open("w", encoding="utf-8") as f:
            json.dump(list(cache.values()), f, ensure_ascii=False, indent=2)

    result = [cache[f"{r['username']}/{r['repo']}"] for r in rows if f"{r['username']}/{r['repo']}" in cache]
    with output_path.open("w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="Git2Value 실험용 평가 프로필 캐시 생성")
    parser.add_argument("--input", default=str(PROJECT_ROOT / "experiments" / "eval_repos.csv"))
    parser.add_argument("--output", default=str(PROJECT_ROOT / "experiments" / "cache" / "eval_profiles.json"))
    parser.add_argument("--force", action="store_true", help="기존 캐시가 있어도 다시 수집")
    args = parser.parse_args()

    result = asyncio.run(collect_profiles(Path(args.input), Path(args.output), force=args.force))
    ok = sum(1 for x in result if x.get("profile_for_matching") and not x.get("error"))
    fail = len(result) - ok
    print(f"\n완료: 성공 {ok}개, 실패 {fail}개, 저장 위치: {args.output}")


if __name__ == "__main__":
    main()
