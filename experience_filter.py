"""
Git2Value v6.3 — 경력 요건 필터링 모듈.

공고 position + text에서 경력 요건을 정규식으로 추출하고,
신입/취준생(특히 0년차) 기준으로 명백한 경력직 공고를 추천 후보에서 분리한다.
사이드카 캐시(vector/experience_cache.json)로 재실행 비용을 줄인다.
"""
from __future__ import annotations

import json
import os
import re
from typing import Any, Tuple

# 패턴 변경 시 이 값을 증가시키면 캐시 전체 재구축
CACHE_VERSION = 2

# 경력 요건 추출 패턴 (position + text 합산 대상, 우선순위 순)
EXPERIENCE_PATTERNS: list[tuple[str, str]] = [
    # 1. 경력무관/신입+경력 (최우선) — v6.3: "신입 가능" 추가
    (r"경력\s*무관|경력무관|신입\s*/\s*경력|신입\s*및\s*경력|신입\s*또는\s*경력|신입\s*가능", "open_to_all"),
    # 2. 신입/주니어
    (r"신입|주니어|junior|entry\s*level", "junior_only"),
    # 3. 시니어/경력직 — v6.3: "경력 개발자", "경력직", "experienced" 추가
    (r"시니어|senior|리드|lead|경력\s*개발자|경력직|experienced", "senior_only"),
    # 4. 한글 연차 범위 — v6.3: "경력" prefix 없이도 매칭 (년 suffix로 구분)
    (r"(\d+)\s*[~\-]\s*(\d+)\s*년", "range_years"),
    # 5. 한글 "N년 이상"
    (r"(\d+)\s*년\s*이상", "min_years_exp"),
    # 6. 영문 "N+ years" / "N years experience" — v6.3 신규
    (r"(\d+)\+?\s*years?\s*(?:of\s+)?(?:experience|exp)?", "min_years_exp"),
    # 7. 한글 "N년차"
    (r"(\d+)\s*년차", "specific_years"),
]


def extract_experience_requirement(position: str, text: str = "") -> dict[str, Any]:
    """
    공고 제목 + 본문에서 경력 요건을 추출.
    Returns: {min_years, is_junior_friendly, raw_label, requirement_type}
    """
    combined = (position + " " + text).lower()
    result: dict[str, Any] = {
        "min_years": 0,
        "is_junior_friendly": True,
        "raw_label": None,
        "requirement_type": "unspecified",
    }

    for pattern, kind in EXPERIENCE_PATTERNS:
        m = re.search(pattern, combined)
        if not m:
            continue
        if kind == "open_to_all":
            result.update({
                "is_junior_friendly": True,
                "raw_label": "경력무관",
                "requirement_type": "open_to_all",
            })
            return result
        if kind == "junior_only":
            result.update({
                "is_junior_friendly": True,
                "raw_label": "신입/주니어",
                "requirement_type": "junior",
            })
            return result
        if kind == "senior_only":
            result.update({
                "is_junior_friendly": False,
                "min_years": 5,
                "raw_label": "경력(시니어)",
                "requirement_type": "senior",
            })
            return result
        if kind == "range_years":
            years = int(m.group(1))
            result.update({
                "min_years": years,
                "is_junior_friendly": years <= 1,
                "raw_label": f"{years}년 이상",
                "requirement_type": "min_years",
            })
            return result
        if kind == "min_years_exp":
            years = int(m.group(1))
            result.update({
                "min_years": years,
                "is_junior_friendly": years <= 1,
                "raw_label": f"{years}년 이상",
                "requirement_type": "min_years",
            })
            return result
        if kind == "specific_years":
            years = int(m.group(1))
            result.update({
                "min_years": years,
                "is_junior_friendly": years <= 3,
                "raw_label": f"{years}년차",
                "requirement_type": "specific_years",
            })
            return result

    return result  # 경력 명시 없으면 신입도 지원 가능한 공고로 판단


def is_applicant_eligible(exp_req: dict[str, Any], applicant_years: int) -> bool:
    """
    추천 후보 포함 여부.
    - 0년차: 신입/주니어/경력무관/경력 미기재만 허용, '1년 이상'도 추천에서는 제외
    - 1~3년차: 명시 최소 연차가 실제 연차 이하인 경우만 허용
    - 4년차 이상: 명시 최소 연차가 실제 연차 이하인 경우 허용
    """
    min_years = int(exp_req.get("min_years") or 0)
    req_type = exp_req.get("requirement_type") or "unspecified"

    if applicant_years <= 0:
        return req_type in {"unspecified", "open_to_all", "junior"} and min_years <= 0
    return min_years <= applicant_years


def load_or_build_cache(metadata: list[dict], cache_path: str) -> dict[str, Any]:
    """
    사이드카 캐시 로드/빌드.
    캐시 형식: {str(job_id): {min_years, is_junior_friendly, raw_label, requirement_type}}
    - 캐시 파일이 없거나 누락 항목이 있으면 추출 후 저장.
    - 파일 I/O 오류는 조용히 무시 (캐시 없이도 런타임 추출로 동작).
    - v6.3: __version__ 불일치 시 캐시 전체 재구축.
    """
    cache: dict[str, Any] = {}

    if os.path.exists(cache_path):
        try:
            with open(cache_path, "r", encoding="utf-8") as f:
                raw = json.load(f)
            if raw.get("__version__") != CACHE_VERSION:
                cache = {}
            else:
                cache = raw
        except (OSError, json.JSONDecodeError):
            cache = {}

    updated = False
    for entry in metadata:
        job_id = str(entry.get("job_id") or entry.get("id") or "")
        cached = cache.get(job_id)
        if job_id and (not cached or "requirement_type" not in cached):
            req = extract_experience_requirement(
                position=entry.get("position", ""),
                text=entry.get("text", ""),
            )
            cache[job_id] = req
            updated = True

    if updated:
        try:
            os.makedirs(os.path.dirname(cache_path) or ".", exist_ok=True)
            cache["__version__"] = CACHE_VERSION
            with open(cache_path, "w", encoding="utf-8") as f:
                json.dump(cache, f, ensure_ascii=False, indent=2)
        except OSError:
            pass

    return cache


def _with_exp_info(match: dict, exp_req: dict[str, Any]) -> dict:
    out = dict(match)
    out["experience_requirement"] = exp_req
    return out


def split_by_experience(
    top_matches: list[dict],
    applicant_years: int,
    cache: dict[str, Any],
) -> Tuple[list[dict], list[dict]]:
    """
    신입/지원자 연차 기준으로 추천 가능 공고와 제외 공고를 분리한다.
    제외 공고는 정보 보존용으로 experience_warning을 붙인다.
    """
    if applicant_years > 30:  # 비정상 입력 방어
        applicant_years = 30

    eligible: list[dict] = []
    flagged: list[dict] = []

    for m in top_matches:
        job_id = str(m["meta"].get("job_id") or m["meta"].get("id") or "")
        exp_req = cache.get(job_id) or extract_experience_requirement(
            position=m["meta"].get("position", ""),
            text=m["meta"].get("text", ""),
        )

        if is_applicant_eligible(exp_req, applicant_years):
            eligible.append(_with_exp_info(m, exp_req))
        else:
            flagged_match = _with_exp_info(m, exp_req)
            flagged_match["experience_warning"] = exp_req.get("raw_label", "경력직")
            flagged.append(flagged_match)

    return eligible, flagged


def filter_by_experience(
    top_matches: list[dict],
    applicant_years: int,
    cache: dict[str, Any],
) -> list[dict]:
    """
    하위 호환용 래퍼.
    기존 동작처럼 추천 가능 공고를 앞에 두고, 제외 공고는 뒤에 보존한다.
    신규 파이프라인에서는 split_by_experience()를 사용한다.
    """
    eligible, flagged = split_by_experience(top_matches, applicant_years, cache)
    return eligible + flagged


def _self_test() -> bool:
    """v6.3: 경력 요건 정규식 패턴 검증용 단위 테스트 (25개 케이스)."""
    cases = [
        # (position, applicant_years, expected_eligible, label_hint)
        # 신입/경력무관
        ("프론트엔드 개발자 신입", 0, True, "신입/주니어"),
        ("백엔드 개발자 (경력 무관)", 0, True, "경력무관"),
        ("개발자 신입/경력", 0, True, "경력무관"),
        ("주니어 백엔드 개발자", 0, True, "신입/주니어"),
        ("Junior Software Engineer", 0, True, "신입/주니어"),
        # 경력직 - 신입 0년차에게 부적합
        ("백엔드 개발자 (경력 3년 이상)", 0, False, "3년 이상"),
        ("시니어 풀스택 개발자", 0, False, "경력(시니어)"),
        ("Senior Backend Engineer", 0, False, "경력(시니어)"),
        ("개발자 5년차", 0, False, "5년차"),
        ("백엔드 개발자 (경력 3~5년)", 0, False, "3년 이상"),
        ("개발자 1년 이상", 0, False, "1년 이상"),
        # 경력자에게 적합
        ("개발자 5년차", 5, True, None),
        ("백엔드 개발자 (경력 3~5년)", 4, True, None),
        ("개발자 1년 이상", 2, True, None),
        # 경력 미명시 - 모두 통과
        ("백엔드 개발자", 0, True, None),
        ("Software Engineer", 2, True, None),
        # v6.3 신규: 경력직 표현 보강
        ("경력 개발자", 0, False, "경력(시니어)"),
        ("경력직 백엔드", 0, False, "경력(시니어)"),
        ("Experienced Engineer", 0, False, "경력(시니어)"),
        ("Backend Developer 3+ years", 0, False, "3년 이상"),
        ("5 years of experience required", 0, False, "5년 이상"),
        ("개발자 1~4년", 0, False, "1년 이상"),
        ("프론트엔드 2-5년", 0, False, "2년 이상"),
        ("신입 가능", 0, True, "경력무관"),
        ("Junior Developer 3+ years", 0, True, "신입/주니어"),  # junior가 먼저 매칭
    ]

    failed = []
    for position, years, expected, label_hint in cases:
        req = extract_experience_requirement(position, "")
        eligible = is_applicant_eligible(req, years)
        if eligible != expected:
            failed.append({
                "position": position,
                "years": years,
                "expected": expected,
                "got": eligible,
                "req": req,
            })

    if failed:
        print(f"FAIL {len(failed)}/{len(cases)} 테스트 실패:")
        for f in failed:
            print(f"  '{f['position']}' (경력 {f['years']}년): "
                  f"expected={f['expected']}, got={f['got']}, req={f['req']}")
        return False

    print(f"OK {len(cases)}/{len(cases)} 테스트 통과")
    return True


if __name__ == "__main__":
    _self_test()
