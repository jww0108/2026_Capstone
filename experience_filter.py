"""
Git2Value v6.0 — 경력 요건 필터링 모듈 (A-2).

공고 position + text에서 경력 요건을 정규식으로 추출하고,
신입(0~3년) 지원자에게 명백히 부적합한 공고를 후순위로 내린다.
사이드카 캐시(vector/experience_cache.json)로 재실행 비용을 0으로 줄인다.
"""
from __future__ import annotations

import json
import os
import re
from typing import Any

# 경력 요건 추출 패턴 (position + text 합산 대상, 우선순위 순)
EXPERIENCE_PATTERNS: list[tuple[str, str]] = [
    (r"신입|주니어|junior", "junior_only"),
    (r"시니어|senior|리드|lead", "senior_only"),
    (r"경력\s*(\d+)\s*[년~\-]\s*(\d+)?\s*년", "range_years"),
    (r"(\d+)\s*년\s*이상", "min_years_exp"),
    (r"(\d+)\s*년차", "specific_years"),
]


def extract_experience_requirement(position: str, text: str = "") -> dict[str, Any]:
    """
    공고 제목 + 본문에서 경력 요건을 추출.
    Returns: {"min_years": int, "is_junior_friendly": bool, "raw_label": str | None}
    """
    combined = (position + " " + text).lower()
    result: dict[str, Any] = {
        "min_years": 0,
        "is_junior_friendly": True,
        "raw_label": None,
    }

    for pattern, kind in EXPERIENCE_PATTERNS:
        m = re.search(pattern, combined)
        if not m:
            continue
        if kind == "junior_only":
            result["is_junior_friendly"] = True
            result["raw_label"] = "신입/주니어"
            return result
        if kind == "senior_only":
            result["is_junior_friendly"] = False
            result["min_years"] = 5
            result["raw_label"] = "경력(시니어)"
            return result
        if kind in ("range_years", "min_years_exp"):
            years = int(m.group(1))
            result["min_years"] = years
            result["is_junior_friendly"] = years <= 1
            result["raw_label"] = f"{years}년 이상"
            return result
        if kind == "specific_years":
            years = int(m.group(1))
            result["min_years"] = years
            result["is_junior_friendly"] = years <= 3
            result["raw_label"] = f"{years}년차"
            return result

    return result  # 경력 명시 없으면 모두에게 열린 공고로 판단


def load_or_build_cache(metadata: list[dict], cache_path: str) -> dict[str, Any]:
    """
    사이드카 캐시 로드/빌드.
    캐시 형식: {str(job_id): {min_years, is_junior_friendly, raw_label}}
    - 캐시 파일이 없거나 누락 항목이 있으면 추출 후 저장.
    - 파일 I/O 오류는 조용히 무시 (캐시 없이도 런타임 추출로 동작).
    """
    cache: dict[str, Any] = {}

    if os.path.exists(cache_path):
        try:
            with open(cache_path, "r", encoding="utf-8") as f:
                cache = json.load(f)
        except (OSError, json.JSONDecodeError):
            cache = {}

    updated = False
    for entry in metadata:
        job_id = str(entry.get("job_id") or entry.get("id") or "")
        if job_id and job_id not in cache:
            req = extract_experience_requirement(
                position=entry.get("position", ""),
                text=entry.get("text", ""),
            )
            cache[job_id] = req
            updated = True

    if updated:
        try:
            os.makedirs(os.path.dirname(cache_path) or ".", exist_ok=True)
            with open(cache_path, "w", encoding="utf-8") as f:
                json.dump(cache, f, ensure_ascii=False, indent=2)
        except OSError:
            pass  # 캐시 저장 실패는 무시하고 계속

    return cache


def filter_by_experience(
    top_matches: list[dict],
    applicant_years: int,
    cache: dict[str, Any],
) -> list[dict]:
    """
    신입(0~3년) 지원자에게 명백한 경력직 공고는 후순위로.
    완전 제외가 아닌 '표시 + 정렬 조정'(정보 보존).

    판정 기준: min_years > applicant_years + 1 (1년 여유 허용)
    경력 지원자(>3년)는 필터링 불필요.
    """
    if applicant_years > 3:
        return top_matches

    eligible: list[dict] = []
    flagged: list[dict] = []

    for m in top_matches:
        job_id = str(
            m["meta"].get("job_id") or m["meta"].get("id") or ""
        )
        exp_req = cache.get(job_id) or extract_experience_requirement(
            position=m["meta"].get("position", ""),
            text=m["meta"].get("text", ""),
        )
        min_years = exp_req.get("min_years", 0)

        if min_years > applicant_years + 1:
            flagged_match = dict(m)
            flagged_match["experience_warning"] = exp_req.get("raw_label", "경력직")
            flagged.append(flagged_match)
        else:
            eligible.append(m)

    return eligible + flagged
