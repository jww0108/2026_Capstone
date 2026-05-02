import os
import re
import asyncio
import platform
import warnings
from collections import Counter

import faiss
import json
from sentence_transformers import SentenceTransformer

from github_extractor import GitHubExtractor
from portfolio_diagnosis import run_diagnosis
from valuation_engine import Git2ValueEngine
from experience_filter import load_or_build_cache, filter_by_experience

warnings.filterwarnings("ignore")
os.environ["HF_HUB_OFFLINE"] = "1"


def route_job_category(position_title: str) -> str:
    """
    [의도] 정규표현식(Regex)의 단어 경계(\b)를 활용하여 
    'software' 안의 'ar'이 매칭되는 참사를 막고, 오염된 문자열을 정규화하여 매핑합니다.
    """
    title = position_title.lower()
    title_no_hyphen = title.replace("-", "").replace(" ", "")

    if re.search(r'\b(ai|ml|vision|perception|cv)\b', title) or any(k in title for k in ["머신러닝", "인공지능", "딥러닝", "데이터 사이언스"]):
        return "인공지능/머신러닝"
    if "블록체인" in title or re.search(r'\bblockchain\b', title):
        return "블록체인"
    if re.search(r'\b(vr|ar|3d)\b', title) or any(k in title for k in ["메타버스", "그래픽스"]):
        return "VR/AR/3D"

    if any(k in title for k in ["빅데이터", "데이터 엔지니어"]):
        return "빅데이터 엔지니어"
    if re.search(r'\bdba\b', title) or "데이터베이스" in title:
        return "DBA"
    if any(k in title for k in ["devops", "데브옵스", "시스템", "인프라", "클라우드"]):
        return "devops/시스템 엔지니어"

    if "안드로이드" in title or re.search(r'\bandroid\b', title):
        return "안드로이드"
    if re.search(r'\bios\b', title) or any(k in title for k in ["아이폰", "애플"]):
        return "iOS"
    if any(k in title_no_hyphen for k in ["크로스플랫폼", "플러터", "flutter", "reactnative", "expo"]):
        return "크로스플랫폼 앱"

    # 게임 직무는 일반 서버/프론트 규칙보다 먼저 (v5.1)
    if (
        any(k in title for k in ["게임 클라이언트", "게임 서버"])
        or re.search(r"\b(unity|unreal|godot)\b", title)
        or "게임" in title
        or re.search(r"\bgame\s+(client|server)\b", title)
    ):
        if (
            "게임 서버" in title
            or re.search(r"\bgame\s+server\b", title)
            or (
                ("서버" in title or "server" in title or "backend" in title or "백엔드" in title)
                and ("게임" in title or re.search(r"\b(unity|unreal|godot)\b", title))
            )
        ):
            return "게임 서버"
        return "게임 클라이언트"

    # 겸직·풀스택 공고는 백엔드/프론트 단독 분류보다 앞서 처리 (MultiDomain Step 9)
    if any(k in title_no_hyphen for k in ["풀스택", "fullstack"]):
        return "웹 풀스택"
    if ("프론트" in title or "front" in title) and ("백엔드" in title or "backend" in title):
        return "웹 풀스택"

    if any(k in title for k in ["백엔드", "서버"]) or re.search(r'\b(backend|server|java|node\.?js|php|python|spring)\b', title):
        return "서버/백엔드"
    if any(k in title_no_hyphen for k in ["프론트엔드", "frontend", "프론트", "vue", "react"]):
        return "프론트엔드"
    if "퍼블리셔" in title:
        return "웹퍼블리셔"

    if any(k in title for k in ["임베디드", "하드웨어", "펌웨어"]) or re.search(r'\bhw\b', title):
        return "HW/임베디드"
    if any(k in title for k in ["테스트"]) or re.search(r'\bqa\b|\btest\b', title):
        return "QA 엔지니어"
    if any(k in title for k in ["기획", "매니저", "프로덕트"]) or re.search(r'\bpm\b', title):
        return "개발 PM"
    if "지원" in title:
        return "기술지원"

    return "SW/솔루션"


def route_job_category_safe(position: str) -> str:
    """
    route_job_category() 방어 래퍼 (Step 1 A-4).
    콤마나 슬래시가 섞인 결과가 나올 경우 첫 토큰만 반환.
    """
    result = route_job_category(position)
    if "," in result:
        return result.split(",")[0].strip()
    return result


# profile_builder.detected_domains[0]과 FAISS 라우팅 직무 정합 (v5.1)
DOMAIN_TO_CATEGORIES: dict[str, list[str]] = {
    "게임 개발": ["게임 클라이언트", "게임 서버", "VR/AR/3D"],
    "웹 프론트엔드": ["프론트엔드", "웹 풀스택", "웹퍼블리셔"],
    "서버/백엔드": ["서버/백엔드", "웹 풀스택"],
    "ML/AI": ["인공지능/머신러닝", "빅데이터 엔지니어"],
    "모바일 앱": ["안드로이드", "iOS", "크로스플랫폼 앱"],
    "DevOps/인프라": ["devops/시스템 엔지니어"],
    # v5.8: 신규 도메인 매핑
    "블록체인": ["블록체인"],
    "빅데이터 엔지니어": ["빅데이터 엔지니어"],
    "도구 개발": ["프론트엔드", "SW/솔루션"],
}

# 도메인 감지와 일치하는 공고에 FAISS 유사도 가산 (v5.3 하이브리드 리랭킹)
DOMAIN_BOOST = 0.05


def _matches_with_baseline_scores(matches: list[dict]) -> list[dict]:
    """FAISS 유사도만 유효 점수로 복사(가산 없음)."""
    return [
        {**m, "effective_score": round(float(m["similarity"]), 4), "domain_boosted": False}
        for m in matches
    ]


def rerank_by_domain(
    top_matches: list[dict],
    detected_domains: list[str],
    domain_hits: dict[str, int] | None = None,
) -> tuple[list[dict], str]:
    """
    FAISS 상위 N개를 도메인 감지 결과로 재정렬.
    similarity(FAISS 원본)는 보존하고 effective_score·domain_boosted를 추가.
    다중 도메인 경합 시(1순위 히트 < 2순위 히트×2) 리랭킹을 건너뜀.

    Returns:
        (재정렬·점수 부착된 목록, 모듈 A 하단용 상태 문자열)
    """
    if not top_matches:
        return [], "상위 매칭 없음 — FAISS 결과가 비어 있습니다."

    if not detected_domains:
        return _matches_with_baseline_scores(top_matches), (
            "도메인 감지: 없음 (FAISS 유사도 순서 그대로 적용)"
        )

    primary_domain = detected_domains[0]
    expected_categories = DOMAIN_TO_CATEGORIES.get(primary_domain, [])
    if not expected_categories:
        return _matches_with_baseline_scores(top_matches), (
            f"도메인 감지: '{primary_domain}' — 점핏 카테고리 매핑 없음. FAISS 순서 유지."
        )

    # 다중 도메인 경합: 히트 상위 2개가 2배 미만 차이면 혼합 프로젝트 → 리랭킹 억제
    if domain_hits and len(detected_domains) >= 2:
        hits_sorted = sorted(domain_hits.values(), reverse=True)
        if len(hits_sorted) >= 2:
            top_hits = hits_sorted[0]
            second_hits = hits_sorted[1]
            if top_hits < second_hits * 2:
                dom_preview = ", ".join(detected_domains[:3])
                if len(detected_domains) > 3:
                    dom_preview += ", …"
                note = (
                    f"다중 도메인 감지: {dom_preview} "
                    "(히트 비율 근접) — 혼합 프로젝트로 판단, 리랭킹 미적용. FAISS 유사도 순서 유지."
                )
                return _matches_with_baseline_scores(top_matches), note

    if not any(m["category"] in expected_categories for m in top_matches):
        return _matches_with_baseline_scores(top_matches), (
            f"도메인 감지: '{primary_domain}' — 상위 5개에 해당 직무 공고가 없어 "
            "가산·재정렬을 적용하지 않았습니다."
        )

    boosted: list[dict] = []
    for m in top_matches:
        sim = float(m["similarity"])
        domain_matched = m["category"] in expected_categories
        effective = sim + (DOMAIN_BOOST if domain_matched else 0.0)
        boosted.append(
            {
                **m,
                "effective_score": round(effective, 4),
                "domain_boosted": domain_matched,
            }
        )
    boosted.sort(key=lambda x: x["effective_score"], reverse=True)
    note = (
        f"도메인 감지: '{primary_domain}' → 기대 직무와 일치하는 공고에 "
        f"+{DOMAIN_BOOST} 가산 후 유효 점수로 재정렬했습니다."
    )
    return boosted, note


def merged_detected_domains_from_profile(profile: dict) -> list[str]:
    """per_repo의 detected_domains를 빈도순으로 병합."""
    c: Counter = Counter()
    for r in profile.get("per_repo") or []:
        for d in r.get("detected_domains") or []:
            c[d] += 1
    return [d for d, _ in c.most_common()]


def check_domain_match_consistency(
    detected_domains: list[str],
    top_matches: list[dict],
) -> dict:
    """
    도메인 감지 결과와 FAISS 상위 공고의 route_job_category 결과를 비교.
    불일치 시 경고·권장 점핏 직무(suggested_category) 반환.
    """
    if not detected_domains:
        return {"consistent": True, "warning": None, "suggested_category": None}

    primary_domain = detected_domains[0]
    expected_categories = DOMAIN_TO_CATEGORIES.get(primary_domain, [])
    if not expected_categories:
        return {"consistent": True, "warning": None, "suggested_category": None}

    matched_categories = [m["category"] for m in top_matches]
    overlap = [c for c in matched_categories if c in expected_categories]

    if overlap:
        return {"consistent": True, "warning": None, "suggested_category": None}

    suggested = expected_categories[0]
    uniq = sorted(set(matched_categories))
    return {
        "consistent": False,
        "warning": (
            f"도메인 감지 결과는 '{primary_domain}'이지만, "
            f"상위 매칭 공고는 모두 다른 직무({', '.join(uniq)})입니다. "
            f"공고 DB에 '{primary_domain}' 관련 공고가 부족하거나, "
            f"프로필 텍스트가 다른 직무 키워드에 가까울 수 있습니다."
        ),
        "suggested_category": suggested,
    }


def similarity_label(
    score: float, top5_scores: list[float]
) -> tuple[str, str | None]:
    """
    v6.0 Step 4: tuple[레이블, 시스템 안내] 반환.
    spread < 0.02 몰림 → 분포 분석 안내 포함.
    정상 분포 → (레이블, None).
    """
    max_s = max(top5_scores)
    min_s = min(top5_scores)
    spread = max_s - min_s
    avg = sum(top5_scores) / len(top5_scores)

    if spread < 0.02:
        if avg < 0.65:
            note = (
                "상위 5개 공고가 모두 비슷한 낮은 유사도에 몰려 있습니다. "
                "프로필이 특정 직무와 강하게 매칭되지 않는 신호로, "
                "README 보강 또는 기술 스택 명확화가 필요합니다."
            )
        else:
            note = (
                "상위 5개 공고의 유사도가 비슷한 수준입니다. "
                "여러 직무가 일정 수준 매칭되는 다재다능한 프로필이거나, "
                "직무 색깔이 뚜렷하지 않은 상태일 수 있습니다."
            )
        if score >= avg + 0.005:
            return "높음", note
        if score >= avg - 0.005:
            return "보통", note
        return "낮음", note

    if score >= max_s - spread * 0.1:
        return "높음", None
    if score >= max_s - spread * 0.4:
        return "보통", None
    return "낮음", None


def diagnose_domain_mismatch(
    detected_domains: list[str],
    top_matches: list[dict],
    domain_hits: dict[str, int],
) -> dict:
    """
    v6.0 Step 5: 도메인 불일치 원인을 4가지로 분기.
    db_coverage / weak_signal / consistent / ambiguous
    """
    if not detected_domains:
        return {"type": "no_signal", "message": None}

    primary = detected_domains[0]
    expected = DOMAIN_TO_CATEGORIES.get(primary, [])
    if not expected:
        return {"type": "no_mapping", "message": None}

    match_count = sum(1 for m in top_matches if m.get("category") in expected)
    primary_hits = domain_hits.get(primary, 0)

    if match_count > 0:
        return {"type": "consistent", "message": None}

    if primary_hits >= 5:
        return {
            "type": "db_coverage",
            "message": (
                f"'{primary}' 도메인이 명확히 감지되었으나 "
                f"채용 공고 DB에 해당 직무 공고가 적습니다. "
                f"실제 채용 시장에서 '{primary}' 공고를 별도로 검색하시기 바랍니다."
            ),
        }

    if primary_hits < 3:
        return {
            "type": "weak_signal",
            "message": (
                f"'{primary}' 도메인 신호가 약하게 감지되었습니다. "
                f"README에 해당 직무 키워드(기술 스택, 프로젝트 성격)를 "
                f"명시하면 매칭 정확도가 올라갑니다."
            ),
        }

    return {
        "type": "ambiguous",
        "message": (
            f"'{primary}' 도메인과 공고 DB 매칭이 모호합니다. "
            f"README 기술 스택 명확화를 권장합니다."
        ),
    }


TECH_KEYWORDS_FOR_PATTERN = [
    "Python", "Java", "JavaScript", "TypeScript", "React", "Vue", "Spring", "Spring Boot",
    "Docker", "Kubernetes", "AWS", "GCP", "Azure", "Go", "Rust", "C++", "Django", "FastAPI",
    "Node.js", "Kotlin", "Swift", "Flutter", "PyTorch", "TensorFlow", "Redis", "PostgreSQL",
    "MySQL", "MongoDB", "GraphQL", "REST API", "Terraform", "Lua"
]


# v6.0: 7개로 축소 (commit_pattern·growth_trajectory·collaboration 제거)
DIAG_LABELS_KO = {
    "readme_quality": "README 품질",
    "project_structure": "프로젝트 구조",
    "test_coverage": "테스트",
    "cicd": "CI/CD",
    "commit_quality": "커밋 메시지",
    "deployment": "배포",
}


# ---------------------------------------------------------------------------
# v6.0 Step 3: 다중 도메인 균형 추천
# ---------------------------------------------------------------------------

def recommend_multi_domain(
    top_matches_extended: list[dict],
    detected_domains: list[str],
    domain_hits: dict[str, int],
) -> dict | None:
    """
    다중 도메인 프로젝트에서 도메인별 균형 추천.
    단일 도메인이면 None 반환 (기존 +0.05 가산점 유지).
    v5.3.1과 같은 판정 기준: hits[0] < hits[1] * 2.
    """
    if len(detected_domains) < 2:
        return None

    hits_sorted = sorted(domain_hits.values(), reverse=True)
    if len(hits_sorted) < 2 or hits_sorted[0] >= hits_sorted[1] * 2:
        return None  # 단일 우세 도메인

    domain_to_picks: dict[str, list] = {}
    for domain in detected_domains[:3]:
        expected_cats = DOMAIN_TO_CATEGORIES.get(domain, [])
        if not expected_cats:
            continue
        picks = []
        for m in top_matches_extended:
            if m.get("category") in expected_cats:
                picks.append(m)
            if len(picks) >= 2:
                break
        if picks:
            domain_to_picks[domain] = picks

    if not domain_to_picks:
        return None

    return {
        "is_multi_domain": True,
        "domain_picks": domain_to_picks,
        "raw_top5": top_matches_extended[:5],
    }


# ---------------------------------------------------------------------------
# v6.0 Step 13: 직무 비교 그룹화 (DOMAIN_TO_CATEGORIES 역매핑)
# ---------------------------------------------------------------------------

# DOMAIN_TO_CATEGORIES 역방향 (한 번만 생성)
CATEGORY_TO_DOMAINS: dict[str, list[str]] = {}
for _domain, _cats in DOMAIN_TO_CATEGORIES.items():
    for _cat in _cats:
        CATEGORY_TO_DOMAINS.setdefault(_cat, []).append(_domain)


def find_adjacent_categories(my_category: str) -> list[str]:
    """현재 직무와 같은 도메인에 속하는 인접 직무 도출."""
    my_domains = CATEGORY_TO_DOMAINS.get(my_category, [])
    adjacent: set[str] = set()
    for domain in my_domains:
        for cat in DOMAIN_TO_CATEGORIES.get(domain, []):
            if cat != my_category:
                adjacent.add(cat)
    return sorted(adjacent)


def categorize_salary_comparison(
    my_category: str,
    comparison: list[dict],
) -> dict:
    """
    3그룹으로 재편: 내 직무 / 인접 직무 / 연봉 상위 직무.
    comparison: valuation_engine의 category_comparison 리스트.
    """
    adjacent = find_adjacent_categories(my_category)
    cat_map = {row["category"]: row for row in comparison}

    my_row = cat_map.get(my_category)
    similar: list[dict] = [
        {"name": cat, "range": cat_map[cat]["junior_range"]}
        for cat in adjacent
        if cat in cat_map
    ][:3]

    non_adjacent = [
        row for row in comparison
        if row["category"] != my_category and row["category"] not in adjacent
    ]
    higher = [
        {"name": row["category"], "range": row["junior_range"]}
        for row in non_adjacent[:2]
    ]

    return {
        "my_job": {"name": my_category, "range": my_row["junior_range"] if my_row else "N/A"},
        "similar": similar,
        "higher": higher,
    }


def analyze_tech_match(
    applicant_languages: str,
    applicant_frameworks: list[str],
    top_matches: list[dict],
    detected_domains: list[str] | None = None,
) -> dict:
    """
    v6.0 Step 6: detected_domains 인자 추가 → 도메인 일치 공고만 미보유 기술 추출.
    일치 공고 0이면 전체 사용 (퇴행 방지).
    Step 1 A-4: 메타 category 콤마 분리.
    """
    # 지원자 보유 기술 세트
    applicant_techs: set[str] = set()
    for token in applicant_languages.replace(",", " ").split():
        clean = token.strip("()%0123456789").strip()
        if clean and len(clean) >= 2:
            applicant_techs.add(clean)
    for fw in applicant_frameworks:
        applicant_techs.add(fw)

    # 도메인 일치 공고 필터 (A-5)
    relevant_matches = top_matches
    if detected_domains:
        primary = detected_domains[0]
        expected_cats = DOMAIN_TO_CATEGORIES.get(primary, [])
        domain_filtered = [m for m in top_matches if m.get("category") in expected_cats]
        if domain_filtered:
            relevant_matches = domain_filtered

    # 공고 요구 기술 추출 (도메인 일치 공고 기준)
    combined_lower = "\n".join(
        (m["meta"].get("position") or "") + "\n" + (m["meta"].get("text") or "")
        for m in relevant_matches
    ).lower()
    required_techs = [kw for kw in TECH_KEYWORDS_FOR_PATTERN if kw.lower() in combined_lower]

    # 교차 분석
    applicant_lower = {t.lower() for t in applicant_techs}
    matched = [kw for kw in required_techs if kw.lower() in applicant_lower]
    missing = [kw for kw in required_techs if kw.lower() not in applicant_lower]

    # 공고 분류 태그 — Step 1 A-4: 콤마 포함 raw category를 개별 항목으로 분리
    raw_categories: list[str] = []
    for m in top_matches:
        raw_cat = m["meta"].get("category") or ""
        for part in re.split(r"[,，]", raw_cat):
            part = part.strip()
            if part:
                raw_categories.append(part)
    # 콤마 포함 키 방어 필터
    clean_cats = [c for c in raw_categories if "," not in c]
    company_types = [
        f"{name} 유사 공고 {cnt}건"
        for name, cnt in Counter(clean_cats).most_common(4)
    ]
    return {
        "matched": matched,
        "missing": missing[:6],
        "company_types": company_types,
        "applicant_techs": sorted(applicant_techs),
    }


def print_applicant_profile(profile: dict, username: str) -> None:
    """GitHubExtractor.extract_applicant_profile() 결과를 터미널에 상세 출력합니다."""
    print("\n" + "=" * 60)
    print(f"[Git2Value] GitHub 스캔 결과 — {username}")
    print("=" * 60)

    print("\n[1] 종합 점수")
    print(f"  최종 GitHub 점수  : {profile['github_score']}점 / 100점")
    bd = profile.get("score_breakdown", {})
    print(f"  점수 분해")
    print(f"    - 기여도 (contribution) : {bd.get('contribution', 0)}점  (최대 60점)")
    print(f"    - 성숙도 (quality)       : {bd.get('quality', 0)}점  (최대 30점)")
    print(f"    - 일관성 (consistency)   : {bd.get('consistency', 0)}점  (최대 10점)")

    print("\n[2] 수집 지표 요약")
    ms = profile.get("metrics_summary", {})
    print(f"  스캔된 레포 수        : {ms.get('scanned_repos', 0)}개")
    print(f"  분석된 총 커밋 수     : {ms.get('total_commits_analyzed', 0)}개")
    print(f"  유효 코드 라인 (LOC)  : {ms.get('total_valid_loc', 0):,} lines")
    print(f"  기여 증거 LOC         : {ms.get('total_evidence_loc', 0):,} lines")
    print(f"  주요 기술 스택        : {ms.get('top_languages', 'N/A')}")

    warns = profile.get("warnings") or []
    if warns:
        print("\n[3] 경고 사항")
        for w in warns:
            print(f"  - {w}")
    else:
        print("\n[3] 경고 사항 : 없음")

    resume = profile.get("applicant_resume", "")
    pfm = profile.get("profile_for_matching") or ""
    print("\n[4] JD 매칭용 프로필 텍스트 (룰베이스 변환)")
    print("-" * 60)
    if pfm:
        prev = pfm if len(pfm) <= 500 else pfm[:500] + "\n  ... (이하 생략)"
        print(f"  {prev}")
    else:
        print("  (내용 없음)")
    print("\n[5] 레거시 Resume 미리보기 (참고)")
    print("-" * 60)
    if resume:
        preview = resume if len(resume) <= 400 else resume[:400] + "\n  ... (이하 생략)"
        print(f"  {preview}")
    else:
        print("  (내용 없음)")
    print("=" * 60)


async def run_e2e_pipeline(
    target_username: str,
    target_repos: list[str],
    applicant_years: int,
) -> None:
    current_dir = os.path.dirname(os.path.abspath(__file__))
    index_path = os.path.join(current_dir, "vector", "git2value_faiss.index")
    meta_path  = os.path.join(current_dir, "vector", "git2value_metadata.json")
    cache_path = os.path.join(current_dir, "vector", "experience_cache.json")

    # ── 1. 인프라 로딩 ──────────────────────────────────────────
    print("\n[Step 1] 벡터 DB 및 연봉 엔진 로딩 중...")
    index = faiss.read_index(index_path)
    with open(meta_path, "r", encoding="utf-8") as f:
        metadata = json.load(f)
    model = SentenceTransformer("jhgan/ko-sroberta-multitask")
    val_engine = Git2ValueEngine()
    # v6.0: 경력 필터 사이드카 캐시 로드/빌드
    exp_cache = load_or_build_cache(metadata, cache_path)
    print("  완료.")

    # ── 2. GitHub 실시간 스캔 ───────────────────────────────────
    print(f"\n[Step 2] GitHub 스캔 시작 — {target_username}")
    print(f"  대상 레포 ({len(target_repos)}개): {', '.join(target_repos)}")
    extractor = GitHubExtractor()
    profile = await extractor.extract_applicant_profile(target_username, target_repos)

    print_applicant_profile(profile, target_username)

    applicant_github_score = profile["github_score"]
    applicant_score_breakdown = profile["score_breakdown"]
    applicant_warnings = profile.get("warnings", [])
    match_text = (profile.get("profile_for_matching") or "").strip() or (
        profile.get("applicant_resume") or ""
    )

    # ── 3. FAISS JD 매칭 (k=20) ─────────────────────────────────
    print("\n[Step 3] AI 직무 매칭 중 (Top 20 추출 → 필터링)...")
    query_vector = model.encode([match_text], normalize_embeddings=True)
    # v6.0 Step 3: k=5 → 20 (다중 도메인 균형 추천 + 경력 필터 여유분)
    distances, indices = index.search(query_vector, 20)

    top_matches_extended: list[dict] = []
    for i in range(20):
        idx = indices[0][i]
        if idx < 0 or idx >= len(metadata):
            break
        dist = distances[0][i]
        meta = metadata[idx]
        top_matches_extended.append({
            "meta": meta,
            "similarity": float(dist),
            "category": route_job_category_safe(meta["position"]),  # Step 1: safe wrapper
        })

    # v6.0 Step 2: 경력 필터 적용 (신입 기준, 경력직 후순위)
    top_matches_extended = filter_by_experience(top_matches_extended, applicant_years, exp_cache)

    detected_domains_merged = merged_detected_domains_from_profile(profile)
    domain_hits_merged = profile.get("domain_hits_merged") or {}

    # v6.0 Step 3: 다중 도메인 균형 추천 판정
    multi_domain_result = recommend_multi_domain(
        top_matches_extended, detected_domains_merged, domain_hits_merged
    )

    # 단일 도메인: 상위 5개 기존 리랭킹 적용
    top_matches_5, rerank_note = rerank_by_domain(
        top_matches_extended[:5], detected_domains_merged, domain_hits_merged
    )

    jumpit_category = top_matches_5[0]["category"] if top_matches_5 else "SW/솔루션"
    domain_check = check_domain_match_consistency(detected_domains_merged, top_matches_5)
    # v6.0 Step 5: 원인 분기 진단
    mismatch_diag = diagnose_domain_mismatch(
        detected_domains_merged, top_matches_5, domain_hits_merged
    )

    print("\n[Step 4] 포트폴리오 진단 (룰베이스)...")
    diag_bundle = run_diagnosis(profile)

    print("\n[Step 5] 시장 연봉 밴드 조회 (GitHub 점수와 독립)...")
    try:
        band_report = val_engine.get_market_band(
            job_category=jumpit_category,
            years_max=3 if applicant_years <= 3 else applicant_years,
        )
    except ValueError as e:
        print(f"  연봉 밴드 조회 오류: {e}")
        return

    ms = profile.get("metrics_summary", {})
    all_frameworks = list({
        fw
        for r in profile.get("per_repo") or []
        for fw in (r.get("frameworks") or [])
    })
    # v6.0 Step 6: detected_domains 전달
    tech_result = analyze_tech_match(
        applicant_languages=ms.get("top_languages", ""),
        applicant_frameworks=all_frameworks,
        top_matches=top_matches_5,
        detected_domains=detected_domains_merged,
    )

    # ── 6. 최종 리포트 (3개 독립 모듈) ───────────────────────────
    print("\n" + "=" * 60)
    print("[Git2Value v6.0] 최종 리포트 — 모듈 A / B / C")
    print("=" * 60)

    repo_classifications = diag_bundle.get("repo_classifications") or []
    per_repo_data = profile.get("per_repo") or []
    matching_count = sum(1 for r in per_repo_data if r.get("matching_included", True))
    excluded_count = len(per_repo_data) - matching_count
    has_mod_or_config = any(
        rc["type"] in ("mod", "config") for rc in repo_classifications
    )

    print("\n[지원자 요약]")
    print(f"  GitHub ID       : {target_username}")
    print(f"  입력 경력       : {applicant_years}년차")
    print(f"  GitHub 점수     : {applicant_github_score}점 (진단 참고용, 연봉 밴드와 무관)")
    bd = applicant_score_breakdown
    print(
        f"  점수 분해       : contribution {bd.get('contribution', 0)} / "
        f"quality {bd.get('quality', 0)} / "
        f"consistency {bd.get('consistency', 0)}"
    )
    total_repos = ms.get("scanned_repos", 0)
    if excluded_count > 0:
        print(f"  분석 레포 수    : {total_repos}개 (매칭 사용: {matching_count}개, 설정/취미: {excluded_count}개)")
    else:
        print(f"  분석 레포 수    : {total_repos}개")
    for rc in repo_classifications:
        rtype = rc["type"]
        repo_nm = rc["repo_name"]
        # v6.0 Step 9: collab_note 표시
        collab = rc.get("collab_note", "")
        collab_str = f" · {collab}" if collab else ""
        if rtype == "config":
            print(f"    - {repo_nm} ({rc['label']}) — 매칭 제외됨{collab_str}")
        elif rtype == "mod":
            print(f"    - {repo_nm} ({rc['label']}) — 게임 도메인 (모드){collab_str}")
        else:
            print(f"    - {repo_nm} — 메인 프로젝트{collab_str}")
    print(f"  분석 커밋 수    : {ms.get('total_commits_analyzed', 0)}개")
    print(f"  유효 LOC        : {ms.get('total_valid_loc', 0):,} lines")
    print(f"  기여 증거 LOC   : {ms.get('total_evidence_loc', 0):,} lines (설정·데이터·IaC 등)")
    print(f"  기술 스택       : {ms.get('top_languages', 'N/A')}")
    if applicant_warnings:
        print("  경고:")
        for w in applicant_warnings:
            print(f"    - {w}")

    if has_mod_or_config:
        print("\n" + "-" * 60)
        print("[프로젝트 분류 안내]")
        print("-" * 60)
        for rc in repo_classifications:
            if rc["type"] in ("mod", "config") and rc.get("message"):
                print(f"  · {rc['repo_name']}: {rc['label']}")
                for line in rc["message"].split(". "):
                    line = line.strip()
                    if line:
                        print(f"      {line}.")
                if rc["type"] == "config":
                    print("      (직무 매칭 입력에서 제외됨)")

    # ── 모듈 A ───────────────────────────────────────────────────
    print("\n" + "-" * 60)
    if multi_domain_result:
        print("[모듈 A] 직무 매칭 — 다중 도메인 프로젝트 (균형 추천)")
    else:
        print("[모듈 A] 직무 매칭 (FAISS + 도메인 리랭킹)")
    print("-" * 60)

    if multi_domain_result:
        # v6.0 Step 3: 다중 도메인 균형 추천 출력
        print("  이 프로젝트는 여러 도메인이 혼합된 풀스택/혼합 프로젝트로 분류됩니다.")
        print("  도메인별로 균형 추천합니다.\n")
        for domain, picks in multi_domain_result["domain_picks"].items():
            print(f"  ▼ {domain} 매칭")
            for j, pick in enumerate(picks, 1):
                m = pick["meta"]
                sim = float(pick["similarity"])
                exp_warn = pick.get("experience_warning")
                exp_str = f" [⚠ {exp_warn}]" if exp_warn else ""
                print(f"    [{j}] [{m['company_name']}] {m['position']}{exp_str}")
                print(f"        (유사도: {sim:.4f})")
            print()
        # 종합 분석
        domain_list = list(multi_domain_result["domain_picks"].keys())
        top_domain = domain_list[0] if domain_list else "해당 도메인"
        top_picks = multi_domain_result["domain_picks"].get(top_domain, [])
        top_sim = float(top_picks[0]["similarity"]) if top_picks else 0
        print(f"  종합 분석:")
        print(f"    · 가장 강한 매칭은 {top_domain} 영역입니다 (유사도 {top_sim:.4f}).")
        print(f"    · 풀스택 경험을 어필하려면 README에 각 영역의 기여를 명시하세요.")
        print(f"  감지 도메인: {', '.join(detected_domains_merged[:4])}")
    else:
        # 단일 도메인: 기존 방식 (경력 필터 적용 포함)
        top5_effective = [float(m["effective_score"]) for m in top_matches_5]
        system_note_printed = False
        for i, match in enumerate(top_matches_5):
            m = match["meta"]
            rank_label = "1순위" if i == 0 else f"{i + 1}순위"
            sim = float(match["similarity"])
            eff = float(match["effective_score"])
            boosted = bool(match.get("domain_boosted"))
            label, sys_note = similarity_label(eff, top5_effective)  # Step 4: tuple
            exp_warn = match.get("experience_warning")
            exp_str = f"  [⚠ {exp_warn} — 지원 가능 경력에 미달]" if exp_warn else ""
            print(f"  [{rank_label}] [{m['company_name']}] {m['position']}{exp_str}")
            if boosted:
                print(
                    f"          (FAISS: {sim:.4f} + 도메인 일치: +{DOMAIN_BOOST} "
                    f"→ 유효: {eff:.4f} · {label})"
                )
            else:
                print(f"          (FAISS: {sim:.4f} · {label})")
            # 시스템 안내는 첫 번째 등장 시 한 번만 출력
            if sys_note and not system_note_printed:
                print(f"\n  ⚠ 매칭 분포 안내: {sys_note}")
                system_note_printed = True
        print(f"\n  {rerank_note}")

        # v6.0 Step 5: 원인 분기 불일치 진단
        if mismatch_diag["type"] not in ("consistent", "no_signal", "no_mapping"):
            print(f"\n  ⚠ 도메인 불일치: {mismatch_diag['message']}")
        elif not domain_check["consistent"]:
            print(f"\n  ⚠ 도메인 불일치 감지:")
            print(f"     {domain_check['warning']}")
            if domain_check.get("suggested_category"):
                print(
                    f"     권장: '{domain_check['suggested_category']}' 직무로 채용 공고를 직접 검색해 보세요."
                )

    print(f"\n  시장 밴드 라우팅 직무: '{jumpit_category}' (1순위 공고 제목 기준)")
    print(f"  공고 분류 태그: {', '.join(tech_result['company_types']) or '(없음)'}")
    print("\n  기술 매칭 분석:")
    matched_str = ", ".join(tech_result["matched"]) or "(없음)"
    missing_str = ", ".join(tech_result["missing"]) or "(없음)"
    print(f"    보유 & 공고 일치: {matched_str}")
    print(f"    공고 요구 중 미보유: {missing_str}")
    if tech_result["missing"]:
        print("    → 포트폴리오에 드러나지 않는 기술입니다. 경험이 있다면 README에 명시하세요.")

    # ── 모듈 B ───────────────────────────────────────────────────
    print("\n" + "-" * 60)
    print("[모듈 B] 포트폴리오 진단 + 기대 수준 (7개 항목)")
    print("-" * 60)
    exp = diag_bundle.get("expected_level") or {}
    print(f"  기대 수준: {exp.get('level', '?')} — {exp.get('summary', '')}")
    ct_note = (diag_bundle.get("contribution_type") or "").strip()
    if ct_note:
        print("  기여 유형 안내:")
        for line in ct_note.split("\n"):
            print(f"    {line}")
    for key, block in (diag_bundle.get("portfolio_diagnosis") or {}).items():
        label = DIAG_LABELS_KO.get(key, key)
        print(f"\n  · {label}")
        print(f"      상태: {block.get('status')}")
        print(f"      내용: {block.get('detail')}")
        act = block.get("action")
        if act:
            print(f"      권장: {act}")

    # v6.0 Step 11: 종합 분석 블록
    summary_block = diag_bundle.get("summary_block", "")
    if summary_block:
        print(f"\n{summary_block}")

    # ── 모듈 C ───────────────────────────────────────────────────
    print("\n" + "-" * 60)
    print("[모듈 C] 시장 연봉 밴드 (신입~3년 구간, GitHub 점수 미반영)")
    print("-" * 60)
    msb = band_report["market_salary_band"]
    sr = msb["salary_range"]
    rr = msb.get("realistic_range", {})

    # v6.0 Step 12: 실제 분포 우선 표시
    print(f"  매칭 직무       : {msb['matched_category']}")
    print(f"      → 채용공고 텍스트 유사도 기준 매칭 결과입니다.")
    if detected_domains_merged and jumpit_category not in (DOMAIN_TO_CATEGORIES.get(detected_domains_merged[0], [])):
        suggested = DOMAIN_TO_CATEGORIES.get(detected_domains_merged[0], [None])[0]
        if suggested:
            print(f"  참고 직무       : {suggested}")
            print(f"      → 레포지토리 파일 구조(도메인 감지) 기준입니다.")
            print(f"      → 두 직무 연봉이 다를 수 있으니 둘 다 확인하세요.")
    print(f"  구간            : {msb['experience_level']}")
    if rr:
        median_manwon = rr["median"] // 10000
        p25_manwon = rr["p25_estimate"] // 10000
        p75_manwon = rr["p75_estimate"] // 10000
        print(f"  시장 중앙값     : 약 {median_manwon:,}만원")
        print(f"  실제 분포       : {p25_manwon:,}만 ~ {p75_manwon:,}만원 (회사 규모·지역·협상에 따라)")
    print(f"  플랫폼 교차검증 (참고):")
    print(f"    점핏: {sr['jumpit_median'] // 10000:,}만원", end="")
    wm = sr.get("wanted_median")
    if wm is not None:
        print(f" / 원티드: {wm // 10000:,}만원")
    else:
        print(f" / 원티드: 해당 직무 매핑 없음")
    print(f"  출처·주의      : {msb['source']} / {msb['note']}")

    # v6.0 Step 13: 불일치 시 대안 밴드
    if not domain_check["consistent"] and domain_check.get("suggested_category"):
        sc = domain_check["suggested_category"]
        try:
            alt_band = val_engine.get_market_band(
                job_category=sc,
                years_max=3 if applicant_years <= 3 else applicant_years,
            )
            alt_rr = alt_band["market_salary_band"].get("realistic_range", {})
            if alt_rr:
                alt_m = alt_rr["median"] // 10000
                alt_p25 = alt_rr["p25_estimate"] // 10000
                alt_p75 = alt_rr["p75_estimate"] // 10000
                print(f"\n  (참고 — 도메인 감지 기반 '{sc}' 직무)")
                print(f"    중앙값: 약 {alt_m:,}만원 / 분포: {alt_p25:,}만 ~ {alt_p75:,}만원")
        except ValueError:
            pass

    # v6.0 Step 13: 직무 비교 3그룹
    sal_groups = categorize_salary_comparison(
        jumpit_category, band_report.get("category_comparison") or []
    )
    print(f"\n  [내 직무]")
    print(f"    {sal_groups['my_job']['name']}: {sal_groups['my_job']['range']}")
    if sal_groups["similar"]:
        print(f"\n  [인접 직무 — 현재 스택으로 지원 가능]")
        for row in sal_groups["similar"]:
            print(f"    {row['name']}: {row['range']}")
    if sal_groups["higher"]:
        print(f"\n  [참고 — 연봉 상위 직무]")
        for row in sal_groups["higher"]:
            print(f"    {row['name']}: {row['range']}")
        print("    → 이 직무들은 추가 학습이 필요할 수 있습니다.")
    print("=" * 60)


if __name__ == "__main__":
    if platform.system() == "Windows":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    # ================================================================
    # [입력] 분석할 지원자 정보를 여기서 수정하세요
    TARGET_USERNAME =  "mino0210"#"RWKHB"#"honey766"#"tekyung"#"bcnsrui"#"CloudChick"#"chjnett"#"devwooks"# #"seseoju" #"AstroJini"  #"HJIWO" #"yyuneu"# "tekyung" #"siheon012" 
    TARGET_REPOS = [
        #"tekyung/2025-2_java_team_project/tree/태경",
        #"tekyung/Ttakji_lab-mobile_development_dep/tree/gabriel",
        #"tekyung/Ttakji_lab-mobile_development_dep/tree/M1_milestone",
        #"tekyung/kyonggi-university_network-system-laboratory_webpage",
        #"siheon012/Deepsentinel",
        #"Virtual-Company-Mal-Geum/ai-server/tree/tekyung",
        #"jww0108/2026_Cap stone/tree/tekyung"
        #"honey766/Paint",
        #"honey766/Balls-Run/tree/main",
        #"2026TUKCOMCD/SyncLab",
        #"Central-MakeUs/AZIT_Front/tree/develop",
        #"Project-Guideon/guideon-backend",
        #"AstroJini/MKX-BE/tree/develop",
        #"AstroJini/SmartFridge/tree/develop",
        #"AstroJini/SmartFridge-FE/tree/develop",
        #"2026TUKCOMCD/SmartWalk/tree/main",
        #"chjnett/aws-jenkins/tree/main",
        #"chjnett/kmong_rich_deploy/tree/main",
        #"bcnsrui/KirafanTCG/tree/main",
        #"CloudChick/holoduel/tree/main",
        #"CloudChick/project_a4/tree/master",
        "mino0210/JuicyMatch/tree/main",
    ]
    APPLICANT_YEARS = 0
    # ================================================================

    asyncio.run(run_e2e_pipeline(TARGET_USERNAME, TARGET_REPOS, APPLICANT_YEARS))
