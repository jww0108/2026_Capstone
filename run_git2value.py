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
    if any(k in title_no_hyphen for k in ["크로스플랫폼", "플러터", "flutter", "reactnative"]):
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


# profile_builder.detected_domains[0]과 FAISS 라우팅 직무 정합 (v5.1)
DOMAIN_TO_CATEGORIES: dict[str, list[str]] = {
    "게임 개발": ["게임 클라이언트", "게임 서버", "VR/AR/3D"],
    "웹 프론트엔드": ["프론트엔드", "웹 풀스택", "웹퍼블리셔"],
    "서버/백엔드": ["서버/백엔드", "웹 풀스택"],
    "ML/AI": ["인공지능/머신러닝", "빅데이터 엔지니어"],
    "모바일 앱": ["안드로이드", "iOS", "크로스플랫폼 앱"],
    "DevOps/인프라": ["devops/시스템 엔지니어"],
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


def similarity_label(score: float, top5_scores: list[float]) -> str:
    """
    상위 5개 점수를 기준으로 한 상대적 레이블 (v5.2 간이 방식, v5.3은 유효 점수 기준).
    spread < 0.02 처럼 점수가 몰려 있을 때는 전체 수준(max_s)으로 판단.
    """
    max_s = max(top5_scores)
    min_s = min(top5_scores)
    spread = max_s - min_s
    if spread < 0.02:
        return "높음" if max_s >= 0.70 else "보통"
    if score >= max_s - spread * 0.1:
        return "높음"
    if score >= max_s - spread * 0.4:
        return "보통"
    return "낮음"


TECH_KEYWORDS_FOR_PATTERN = [
    "Python", "Java", "JavaScript", "TypeScript", "React", "Vue", "Spring", "Spring Boot",
    "Docker", "Kubernetes", "AWS", "GCP", "Azure", "Go", "Rust", "C++", "Django", "FastAPI",
    "Node.js", "Kotlin", "Swift", "Flutter", "PyTorch", "TensorFlow", "Redis", "PostgreSQL",
    "MySQL", "MongoDB", "GraphQL", "REST API", "Terraform",
]


DIAG_LABELS_KO = {
    "readme_quality": "README 품질",
    "project_structure": "프로젝트 구조",
    "test_coverage": "테스트",
    "cicd": "CI/CD",
    "commit_quality": "커밋 메시지",
    "commit_pattern": "커밋 리듬",
    "deployment": "배포",
    "collaboration": "협업",
    "growth_trajectory": "성장 궤적",
}


def analyze_tech_match(
    applicant_languages: str,
    applicant_frameworks: list[str],
    top_matches: list[dict],
) -> dict:
    """
    지원자 보유 기술(언어 + 프레임워크)과 공고 요구 기술을 교차 분석 (v5.2).
    기존 '공통 기술 키워드' 단순 나열을 보유/미보유 분리로 교체.
    공고 분류 태그(company_types)는 유지.
    """
    # 지원자 보유 기술 세트 구성 (언어 통계 파싱 + 프레임워크)
    applicant_techs: set[str] = set()
    for token in applicant_languages.replace(",", " ").split():
        clean = token.strip("()%0123456789").strip()
        if clean and len(clean) >= 2:
            applicant_techs.add(clean)
    for fw in applicant_frameworks:
        applicant_techs.add(fw)

    # 공고 요구 기술 추출
    combined_lower = "\n".join(
        (m["meta"].get("position") or "") + "\n" + (m["meta"].get("text") or "")
        for m in top_matches
    ).lower()
    required_techs = [kw for kw in TECH_KEYWORDS_FOR_PATTERN if kw.lower() in combined_lower]

    # 교차 분석
    applicant_lower = {t.lower() for t in applicant_techs}
    matched = [kw for kw in required_techs if kw.lower() in applicant_lower]
    missing = [kw for kw in required_techs if kw.lower() not in applicant_lower]

    # 공고 분류 태그 (기존 company_types 유지)
    categories = [m["meta"].get("category") for m in top_matches if m["meta"].get("category")]
    company_types = [
        f"{name} 유사 공고 {cnt}건"
        for name, cnt in Counter(categories).most_common(4)
    ]
    return {
        "matched": matched,
        "missing": missing[:6],  # 최대 6개 — 너무 길면 압도적
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

    # ── 1. 인프라 로딩 ──────────────────────────────────────────
    print("\n[Step 1] 벡터 DB 및 연봉 엔진 로딩 중...")
    index = faiss.read_index(index_path)
    with open(meta_path, "r", encoding="utf-8") as f:
        metadata = json.load(f)
    model = SentenceTransformer("jhgan/ko-sroberta-multitask")
    val_engine = Git2ValueEngine()
    print("  완료.")

    # ── 2. GitHub 실시간 스캔 ───────────────────────────────────
    print(f"\n[Step 2] GitHub 스캔 시작 — {target_username}")
    print(f"  대상 레포 ({len(target_repos)}개): {', '.join(target_repos)}")
    extractor = GitHubExtractor()
    profile = await extractor.extract_applicant_profile(target_username, target_repos)

    # 스캔 결과 전체 출력
    print_applicant_profile(profile, target_username)

    applicant_github_score = profile["github_score"]
    applicant_score_breakdown = profile["score_breakdown"]
    applicant_warnings = profile.get("warnings", [])
    match_text = (profile.get("profile_for_matching") or "").strip() or (
        profile.get("applicant_resume") or ""
    )

    # ── 3. FAISS JD 매칭 ────────────────────────────────────────
    print("\n[Step 3] AI 직무 매칭 중 (Top 5 추출)...")
    query_vector = model.encode([match_text], normalize_embeddings=True)
    distances, indices = index.search(query_vector, 5)

    # 상위 5개 결과를 리스트에 저장
    top_matches = []
    for i in range(5):
        idx = indices[0][i]
        dist = distances[0][i]
        meta = metadata[idx]
        top_matches.append({
            "meta": meta,
            "similarity": float(dist),
            "category": route_job_category(meta["position"])
        })

    detected_domains_merged = merged_detected_domains_from_profile(profile)
    domain_hits_merged = profile.get("domain_hits_merged") or {}
    top_matches, rerank_note = rerank_by_domain(
        top_matches, detected_domains_merged, domain_hits_merged
    )
    jumpit_category = top_matches[0]["category"]
    domain_check = check_domain_match_consistency(detected_domains_merged, top_matches)

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
    tech_result = analyze_tech_match(
        applicant_languages=ms.get("top_languages", ""),
        applicant_frameworks=all_frameworks,
        top_matches=top_matches,
    )

    # ── 6. 최종 리포트 (3개 독립 모듈) ───────────────────────────
    print("\n" + "=" * 60)
    print("[Git2Value v5.3] 최종 리포트 — 모듈 A / B / C")
    print("=" * 60)

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
    print(f"  분석 레포 수    : {ms.get('scanned_repos', 0)}개")
    print(f"  분석 커밋 수    : {ms.get('total_commits_analyzed', 0)}개")
    print(f"  유효 LOC        : {ms.get('total_valid_loc', 0):,} lines")
    print(f"  기술 스택       : {ms.get('top_languages', 'N/A')}")
    if applicant_warnings:
        print("  경고:")
        for w in applicant_warnings:
            print(f"    - {w}")

    print("\n" + "-" * 60)
    print("[모듈 A] 직무 매칭 (FAISS + 도메인 리랭킹)")
    print("-" * 60)
    top5_effective = [float(m["effective_score"]) for m in top_matches]
    for i, match in enumerate(top_matches):
        m = match["meta"]
        rank_label = "1순위" if i == 0 else f"{i + 1}순위"
        sim = float(match["similarity"])
        eff = float(match["effective_score"])
        boosted = bool(match.get("domain_boosted"))
        label = similarity_label(eff, top5_effective)
        print(f"  [{rank_label}] [{m['company_name']}] {m['position']}")
        if boosted:
            print(
                f"          (FAISS: {sim:.4f} + 도메인 일치: +{DOMAIN_BOOST} "
                f"→ 유효: {eff:.4f} · {label})"
            )
        else:
            print(f"          (FAISS: {sim:.4f} · {label})")
    print(f"\n  {rerank_note}")
    if not domain_check["consistent"]:
        print(f"\n  ⚠️ 도메인 불일치 감지:")
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

    print("\n" + "-" * 60)
    print("[모듈 B] 포트폴리오 진단 + 기대 수준")
    print("-" * 60)
    exp = diag_bundle.get("expected_level") or {}
    print(f"  기대 수준: {exp.get('level', '?')} — {exp.get('summary', '')}")
    for key, block in (diag_bundle.get("portfolio_diagnosis") or {}).items():
        label = DIAG_LABELS_KO.get(key, key)
        print(f"\n  · {label}")
        print(f"      상태: {block.get('status')}")
        print(f"      내용: {block.get('detail')}")
        act = block.get("action")
        if act:
            print(f"      권장: {act}")

    print("\n" + "-" * 60)
    print("[모듈 C] 시장 연봉 밴드 (신입~3년 구간, GitHub 점수 미반영)")
    print("-" * 60)
    msb = band_report["market_salary_band"]
    sr = msb["salary_range"]
    print(f"  매칭 직무       : {msb['matched_category']}")
    print(f"  구간            : {msb['experience_level']}")
    print(f"  점핏 중앙값     : {sr['jumpit_median']:,}원")
    wm = sr.get("wanted_median")
    if wm is not None:
        print(f"  원티드(신입~3년 평균): {wm:,}원")
    else:
        print("  원티드(신입~3년 평균): 해당 직무 JSON 매핑 없음")
    print(f"  참고 범위       : {sr['combined_range']}")
    print(f"  출처·주의      : {msb['source']} / {msb['note']}")
    if not domain_check["consistent"] and domain_check.get("suggested_category"):
        sc = domain_check["suggested_category"]
        print(f"\n  (참고: 도메인 감지 기반 '{sc}' 직무 연봉 밴드)")
        try:
            alt_band = val_engine.get_market_band(
                job_category=sc,
                years_max=3 if applicant_years <= 3 else applicant_years,
            )
            alt_sr = alt_band["market_salary_band"]["salary_range"]
            print(f"    참고 범위: {alt_sr['combined_range']}")
        except ValueError:
            print("    해당 직무의 연봉 데이터가 없습니다.")
    print("\n  (직무 간 비교 — 점핏 junior 구간)")
    for row in (band_report.get("category_comparison") or [])[:6]:
        print(f"    - {row['category']}: {row['junior_range']}")
    print("=" * 60)


if __name__ == "__main__":
    if platform.system() == "Windows":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    # ================================================================
    # [입력] 분석할 지원자 정보를 여기서 수정하세요
    TARGET_USERNAME = "tekyung" #"siheon012" # 
    TARGET_REPOS = [
        #"tekyung/2025-2_java_team_project/",
        #"tekyung/Ttakji_lab-mobile_development_dep/tree/gabriel",
        "tekyung/Ttakji_lab-mobile_development_dep/tree/M1_milestone",
        #"tekyung/kyonggi-university_network-system-laboratory_webpage",
        #"siheon012/Deepsentinel",
        #"Virtual-Company-Mal-Geum/ai-server/tree/tekyung"
    ]
    APPLICANT_YEARS = 0
    # ================================================================

    asyncio.run(run_e2e_pipeline(TARGET_USERNAME, TARGET_REPOS, APPLICANT_YEARS))
