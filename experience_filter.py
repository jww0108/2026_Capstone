"""
Git2Value v6.4 — 경력 요건 필터링 모듈.

공고 position + text에서 경력 요건을 정규식으로 추출하고,
신입/취준생(특히 0년차) 기준으로 명백한 경력직 공고를 추천 후보에서 분리한다.
사이드카 캐시(vector/experience_cache.json)로 재실행 비용을 줄인다.

v6.4 변경점
- '1~4년', '1-4년', '1년 이상 4년 이하', '3+ years', 'minimum 2 years' 등 연차 패턴 강화
- '경력 개발자', '경력직', 'experienced engineer', 'mid-level', '선임/책임' 등 숫자 없는 경력직 표현 강화
- 기존의 너무 넓은 '무관' 판정을 제거하고 '경력무관'/'신입·경력' 등 명시 표현만 허용
- position/title을 우선 판정하여 제목에 적힌 경력 요건이 본문 일반 문구에 묻히지 않도록 개선
"""
from __future__ import annotations

import json
import os
import re
from typing import Any, Tuple

# 정규식이 바뀌면 기존 캐시를 그대로 쓰지 않도록 버전 관리한다.
CACHE_VERSION = "v6.4-exp-filter-strict"

# ---------------------------------------------------------------------------
# 정규식 정의
# ---------------------------------------------------------------------------

OPEN_TO_ALL_PATTERNS = [
    r"경력\s*무관|경력무관",
    r"신입\s*(?:(?:/|·|,|및|또는|or|&|\+)|\s+)\s*경력",
    r"경력\s*(?:(?:/|·|,|및|또는|or|&|\+)|\s+)\s*신입",
    r"신입\s*가능|신입\s*지원\s*가능|신입\s*환영",
    r"무경력\s*가능|경력\s*없어도\s*가능",
    r"no\s+experience\s+required|no\s+prior\s+experience\s+required",
]

JUNIOR_PATTERNS = [
    r"신입",
    r"주니어",
    r"junior",
    r"entry\s*level|entry-level",
    r"new\s*grad|new\s*graduate|graduate\s*program",
    r"인턴|internship|intern\b",
]

SENIOR_PATTERNS = [
    r"시니어|senior",
    r"리드|lead\b|tech\s*lead",
    r"principal|staff\s+engineer",
    r"수석|책임|선임",
    r"미들급|중급|middle|mid[-\s]?level",
]

# 숫자 기반 경력 요건. named group 'min', 'max' 사용.
RANGE_PATTERNS = [
    # 1~4년, 1 - 4년, 1 to 4 years, 1~4 yrs
    r"(?P<min>\d{1,2})\s*(?:년|년차|years?|yrs?)?\s*(?:~|-|–|—|to)\s*(?P<max>\d{1,2})\s*(?:년|년차|years?|yrs?)",
    # 1년 ~ 4년, 1 year to 4 years
    r"(?P<min>\d{1,2})\s*(?:년|년차|years?|yrs?)\s*(?:~|-|–|—|to)\s*(?P<max>\d{1,2})\s*(?:년|년차|years?|yrs?)",
    # 1년 이상 4년 이하, 3년 이상 5년 미만
    r"(?P<min>\d{1,2})\s*(?:년|년차|years?|yrs?)\s*(?:이상|부터|or\s*more|plus)\s*(?P<max>\d{1,2})\s*(?:년|년차|years?|yrs?)\s*(?:이하|미만|까지)?",
    # 경력 1~4년, experience 2-5 years
    r"(?:경력|경험|experience|experienced).*?(?P<min>\d{1,2})\s*(?:년|년차|years?|yrs?)?\s*(?:~|-|–|—|to)\s*(?P<max>\d{1,2})\s*(?:년|년차|years?|yrs?)",
]

MIN_YEAR_PATTERNS = [
    # 3년 이상, 3 years or more, 3 yrs plus
    r"(?P<min>\d{1,2})\s*(?:년|년차|years?|yrs?)\s*(?:이상|이상의|부터|\+|or\s*more|plus|over)",
    # 3+ years, 3+ yrs
    r"(?P<min>\d{1,2})\s*\+\s*(?:년|년차|years?|yrs?)?",
    # 최소 2년, minimum 2 years, at least 2 years
    r"(?:최소|minimum|min\.?|at\s+least)\s*(?P<min>\d{1,2})\s*(?:년|년차|years?|yrs?)",
    # 경력 3년, experience 3 years, professional experience 2 years
    r"(?:경력|실무\s*경험|업무\s*경험|관련\s*경험|experience|experienced|professional\s*experience).*?(?P<min>\d{1,2})\s*(?:년|년차|years?|yrs?)",
]

SPECIFIC_YEAR_PATTERNS = [
    r"(?P<min>\d{1,2})\s*년차",
]

CAREER_ONLY_PATTERNS = [
    r"경력\s*개발자|경력직|경력자|경력\s*채용|경력\s*모집",
    r"경력\s*포지션|경력\s*사원|경력\s*직원",
    r"실무\s*경험\s*(?:보유|필수|있으신|있는)",
    r"상용\s*서비스\s*경험|운영\s*경험\s*(?:보유|필수)",
    r"experienced\b.*?(?:developer|engineer|programmer)",
    r"professional\s+experience",
    r"hands[-\s]?on\s+experience",
]

# 구버전 호환용: 외부에서 EXPERIENCE_PATTERNS를 참조할 가능성을 위해 남긴다.
EXPERIENCE_PATTERNS: list[tuple[str, str]] = (
    [(p, "open_to_all") for p in OPEN_TO_ALL_PATTERNS]
    + [(p, "junior_only") for p in JUNIOR_PATTERNS]
    + [(p, "senior_only") for p in SENIOR_PATTERNS]
    + [(p, "range_years") for p in RANGE_PATTERNS]
    + [(p, "min_years_exp") for p in MIN_YEAR_PATTERNS]
    + [(p, "specific_years") for p in SPECIFIC_YEAR_PATTERNS]
    + [(p, "career_only") for p in CAREER_ONLY_PATTERNS]
)


def _normalize(text: str) -> str:
    """검색 안정성을 위해 공백/구분자를 정리한다."""
    text = (text or "").lower()
    text = text.replace("～", "~").replace("−", "-").replace("–", "-").replace("—", "-")
    text = re.sub(r"[\[\]{}()<>]", " ", text)
    text = re.sub(r"[_/|·•,;:]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _has_any(text: str, patterns: list[str]) -> bool:
    return any(re.search(p, text, re.I) for p in patterns)


def _make_req(
    min_years: int,
    is_junior_friendly: bool,
    raw_label: str | None,
    requirement_type: str,
    source: str,
) -> dict[str, Any]:
    return {
        "min_years": int(min_years or 0),
        "is_junior_friendly": bool(is_junior_friendly),
        "raw_label": raw_label,
        "requirement_type": requirement_type,
        "source": source,
    }


def _extract_numeric_requirement(text: str, source: str) -> dict[str, Any] | None:
    """숫자 기반 경력 요건을 추출한다. 발견 즉시 0년차 추천에서는 제외된다."""
    for pattern in RANGE_PATTERNS:
        m = re.search(pattern, text, re.I)
        if m:
            years = int(m.group("min"))
            upper = m.groupdict().get("max")
            raw = f"{years}~{upper}년" if upper else f"{years}년 이상"
            return _make_req(years, years <= 0, raw, "range_years", source)

    for pattern in MIN_YEAR_PATTERNS:
        m = re.search(pattern, text, re.I)
        if m:
            years = int(m.group("min"))
            return _make_req(years, years <= 0, f"{years}년 이상", "min_years", source)

    for pattern in SPECIFIC_YEAR_PATTERNS:
        m = re.search(pattern, text, re.I)
        if m:
            years = int(m.group("min"))
            return _make_req(years, years <= 0, f"{years}년차", "specific_years", source)

    return None


def _extract_career_keyword(text: str, source: str) -> dict[str, Any] | None:
    if _has_any(text, SENIOR_PATTERNS):
        return _make_req(5, False, "경력(시니어/중급 이상)", "senior", source)
    if _has_any(text, CAREER_ONLY_PATTERNS):
        return _make_req(1, False, "경력직", "career_only", source)
    return None


def _extract_open_or_junior(text: str, source: str) -> dict[str, Any] | None:
    if _has_any(text, OPEN_TO_ALL_PATTERNS):
        return _make_req(0, True, "경력무관", "open_to_all", source)
    if _has_any(text, JUNIOR_PATTERNS):
        return _make_req(0, True, "신입/주니어", "junior", source)
    return None


def extract_experience_requirement(position: str, text: str = "") -> dict[str, Any]:
    """
    공고 제목 + 본문에서 경력 요건을 추출.

    판정 원칙:
    1. 제목(position)의 명시 조건을 최우선으로 본다.
       - '신입/경력', '경력무관'처럼 명시적으로 신입 허용이면 통과
       - '1~4년', '경력 개발자', '시니어'처럼 제목에 경력 신호가 있으면 제외
    2. 제목이 애매하면 본문(text)까지 합쳐서 판정한다.
    3. 일반적인 '무관' 단어는 경력무관으로 보지 않는다. 학력/성별 무관과 혼동되기 때문이다.

    Returns: {min_years, is_junior_friendly, raw_label, requirement_type, source}
    """
    title = _normalize(position)
    body = _normalize(text)
    combined = _normalize(f"{position} {text}")

    default = _make_req(0, True, None, "unspecified", "none")

    # 1) 제목에 명시적으로 신입 가능/경력무관이 있으면 우선 허용한다.
    title_open = _extract_open_or_junior(title, "position")
    if title_open and title_open["requirement_type"] == "open_to_all":
        return title_open

    # 2) 제목에 숫자/시니어/경력직 신호가 있으면 우선 제외한다.
    title_numeric = _extract_numeric_requirement(title, "position")
    if title_numeric:
        return title_numeric

    title_career = _extract_career_keyword(title, "position")
    if title_career:
        return title_career

    # 3) 제목이 junior/new grad 정도면 통과. 단 숫자 조건이 같이 있으면 위에서 이미 걸린다.
    if title_open:
        return title_open

    # 4) 본문/전체 문구에서 명시적으로 신입 가능이면 허용한다.
    combined_open = _extract_open_or_junior(combined, "combined")
    if combined_open and combined_open["requirement_type"] == "open_to_all":
        return combined_open

    # 5) 숫자 기반 경력 요건은 가장 강한 제외 신호다.
    combined_numeric = _extract_numeric_requirement(combined, "combined")
    if combined_numeric:
        return combined_numeric

    # 6) 숫자는 없지만 경력직/시니어/실무 경험 필수 신호가 있으면 제외한다.
    combined_career = _extract_career_keyword(combined, "combined")
    if combined_career:
        return combined_career

    # 7) junior/new grad는 숫자 경력 조건이 없을 때 통과.
    if combined_open:
        return combined_open

    return default  # 경력 명시 없으면 신입도 지원 가능한 공고로 판단


def is_applicant_eligible(exp_req: dict[str, Any], applicant_years: int) -> bool:
    """
    추천 후보 포함 여부.
    - 0년차: 신입/주니어/경력무관/경력 미기재만 허용, '1년 이상'도 추천에서는 제외
    - 1년차 이상: 명시 최소 연차가 실제 연차 이하인 경우만 허용
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
    - 정규식 버전이 바뀌면 기존 캐시를 폐기하고 재생성한다.
    - 파일 I/O 오류는 조용히 무시 (캐시 없이도 런타임 추출로 동작).
    """
    cache: dict[str, Any] = {}

    if os.path.exists(cache_path):
        try:
            with open(cache_path, "r", encoding="utf-8") as f:
                cache = json.load(f)
        except (OSError, json.JSONDecodeError):
            cache = {}

    if cache.get("_cache_version") != CACHE_VERSION:
        cache = {"_cache_version": CACHE_VERSION}

    updated = False
    for entry in metadata:
        job_id = str(entry.get("job_id") or entry.get("id") or "")
        cached = cache.get(job_id)
        if job_id and (not cached or "requirement_type" not in cached or "source" not in cached):
            req = extract_experience_requirement(
                position=entry.get("position", ""),
                text=entry.get("text", ""),
            )
            cache[job_id] = req
            updated = True

    if updated or cache.get("_cache_version") != CACHE_VERSION:
        cache["_cache_version"] = CACHE_VERSION
        try:
            os.makedirs(os.path.dirname(cache_path) or ".", exist_ok=True)
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
    include_flagged: bool = False,
) -> list[dict]:
    """
    하위 호환용 래퍼.
    기본값은 추천 가능 공고만 반환한다. 경력직 공고를 뒤에 붙여 출력하던 구버전 동작이
    필요하면 include_flagged=True를 명시한다.
    """
    eligible, flagged = split_by_experience(top_matches, applicant_years, cache)
    return eligible + flagged if include_flagged else eligible


def _self_test() -> bool:
    """v6.4: 경력 요건 정규식 패턴 검증용 단위 테스트."""
    cases = [
        # (position, applicant_years, expected_eligible, label_hint)
        # 신입/경력무관
        ("프론트엔드 개발자 신입", 0, True, "신입/주니어"),
        ("백엔드 개발자 (경력 무관)", 0, True, "경력무관"),
        ("개발자 신입/경력", 0, True, "경력무관"),
        ("신입 및 경력 서버 개발자", 0, True, "경력무관"),
        ("주니어 백엔드 개발자", 0, True, "신입/주니어"),
        ("Junior Software Engineer", 0, True, "신입/주니어"),
        ("Entry-level Frontend Engineer", 0, True, "신입/주니어"),
        ("New Grad Software Engineer", 0, True, "신입/주니어"),
        # 일반 무관은 경력무관으로 오판하지 않음
        ("백엔드 개발자", 0, True, None),
        ("백엔드 개발자", 0, True, None),
        # 경력직 - 신입 0년차에게 부적합
        ("백엔드 개발자 (경력 3년 이상)", 0, False, "3년 이상"),
        ("시니어 풀스택 개발자", 0, False, "경력(시니어"),
        ("Senior Backend Engineer", 0, False, "경력(시니어"),
        ("선임 백엔드 개발자", 0, False, "경력(시니어"),
        ("개발자 5년차", 0, False, "5년"),
        ("백엔드 개발자 (경력 3~5년)", 0, False, "3~5년"),
        ("프론트엔드 개발자_1~4년", 0, False, "1~4년"),
        ("백엔드 개발자 1-4년", 0, False, "1~4년"),
        ("개발자 1년 이상 4년 이하", 0, False, "1~4년"),
        ("Backend Engineer 2-5 years", 0, False, "2~5년"),
        ("Backend Engineer 3+ years", 0, False, "3년 이상"),
        ("Backend Engineer at least 2 years", 0, False, "2년 이상"),
        ("경력 개발자(백엔드) 채용", 0, False, "경력직"),
        ("Experienced Backend Engineer", 0, False, "경력직"),
        ("Mid-level Frontend Engineer", 0, False, "경력(시니어"),
        ("개발자 1년 이상", 0, False, "1년 이상"),
        # 본문 경력 조건
        ("백엔드 개발자", 0, False, "2년 이상", "지원자격: 관련 업무 경험 2년 이상"),
        ("프론트엔드 개발자", 0, False, "경력직", "자격요건: 실무 경험 보유자"),
        ("게임 클라이언트 개발자", 0, True, None, "학력 무관, 성별 무관"),
        # 경력자에게 적합
        ("개발자 5년차", 5, True, None),
        ("백엔드 개발자 (경력 3~5년)", 4, True, None),
        ("개발자 1년 이상", 2, True, None),
        # 경력 미명시 - 통과
        ("Software Engineer", 0, True, None),
        ("Software Engineer", 2, True, None),
    ]

    failed = []
    for case in cases:
        if len(case) == 4:
            position, years, expected, label_hint = case
            text = ""
        else:
            position, years, expected, label_hint, text = case
        req = extract_experience_requirement(position, text)
        eligible = is_applicant_eligible(req, years)
        if eligible != expected:
            failed.append({
                "position": position,
                "text": text,
                "years": years,
                "expected": expected,
                "got": eligible,
                "req": req,
            })
        if label_hint and label_hint not in str(req.get("raw_label")):
            failed.append({
                "position": position,
                "text": text,
                "years": years,
                "expected": f"label contains {label_hint}",
                "got": req.get("raw_label"),
                "req": req,
            })

    if failed:
        print(f"FAIL {len(failed)}/{len(cases)} 테스트 실패:")
        for f in failed:
            print(f"  '{f['position']}' text='{f.get('text','')}' (경력 {f['years']}년): "
                  f"expected={f['expected']}, got={f['got']}, req={f['req']}")
        return False

    print(f"OK {len(cases)}/{len(cases)} 테스트 통과")
    return True


if __name__ == "__main__":
    _self_test()
