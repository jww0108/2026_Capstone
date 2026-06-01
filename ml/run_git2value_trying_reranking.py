import os
import re
import asyncio
import platform
import warnings
from pathlib import Path #추가
from collections import Counter

import faiss
import json
from sentence_transformers import SentenceTransformer

from github_extractor import GitHubExtractor
from portfolio_diagnosis import run_diagnosis
from valuation_engine import Git2ValueEngine
from experience_filter import load_or_build_cache, filter_by_experience, split_by_experience
from ml.job_classifier import load_model_bundle, predict_profile #추가

warnings.filterwarnings("ignore")
os.environ["HF_HUB_OFFLINE"] = "1"

# 입력 가능한 레포 최대 개수 (메인 1 + 서브 2 권장)
MAX_REPO_COUNT = 3


def route_job_category(position_title: str) -> str:
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
    """route_job_category() 방어 래퍼."""
    result = route_job_category(position)
    if "," in result:
        return result.split(",")[0].strip()
    return result


DOMAIN_TO_CATEGORIES: dict[str, list[str]] = {
    "게임 개발": ["게임 클라이언트", "게임 서버", "VR/AR/3D"],
    "웹 프론트엔드": ["프론트엔드", "웹 풀스택", "웹퍼블리셔"],
    "서버/백엔드": ["서버/백엔드", "웹 풀스택"],
    "ML/AI": ["인공지능/머신러닝", "빅데이터 엔지니어"],
    "모바일 앱": ["안드로이드", "iOS", "크로스플랫폼 앱"],
    "DevOps/인프라": ["devops/시스템 엔지니어"],
    "블록체인": ["블록체인"],
    "빅데이터 엔지니어": ["빅데이터 엔지니어"],
    "도구 개발": ["프론트엔드", "SW/솔루션"],
}

DOMAIN_BOOST = 0.05

#---------------------추가----------------

# AI 분류모델 리랭킹 가중치
# experiments/evaluate_ex2.py의 DEFAULT_AI_ALPHA와 동일한 의미
CLASSIFIER_ALPHA = 0.10

# run_git2value.py의 세부 채용공고 category를
# ml/job_classifier.py가 예측하는 8개 도메인 라벨에 연결한다.
JOB_CATEGORY_TO_MODEL_LABELS: dict[str, list[str]] = {
    "서버/백엔드": ["서버/백엔드"],
    "웹 풀스택": ["서버/백엔드", "프론트엔드"],
    "프론트엔드": ["프론트엔드"],
    "웹퍼블리셔": ["프론트엔드"],

    "인공지능/머신러닝": ["인공지능/머신러닝"],
    "빅데이터 엔지니어": ["빅데이터 엔지니어", "인공지능/머신러닝"],

    "devops/시스템 엔지니어": ["DevOps/시스템 엔지니어"],
    "DevOps/시스템 엔지니어": ["DevOps/시스템 엔지니어"],

    "안드로이드": ["모바일 앱"],
    "iOS": ["모바일 앱"],
    "크로스플랫폼 앱": ["모바일 앱"],

    "게임 클라이언트": ["게임 개발"],
    "게임 서버": ["게임 개발", "서버/백엔드"],
    "VR/AR/3D": ["게임 개발"],

    "블록체인": ["블록체인"],
}


def _norm_label(label: str) -> str:
    return str(label or "").lower().replace(" ", "").replace("-", "").strip()


def get_classifier_probability_for_category(
    job_category: str,
    probabilities: dict[str, float],
) -> float:
    """
    채용공고 category에 대응되는 분류모델 확률을 반환한다.

    예:
    job_category = "안드로이드"
    probabilities = {"모바일 앱": 0.72, ...}
    → 0.72
    """
    if not probabilities:
        return 0.0

    target_labels = JOB_CATEGORY_TO_MODEL_LABELS.get(job_category, [job_category])
    prob_by_norm = {
        _norm_label(label): float(prob)
        for label, prob in probabilities.items()
    }

    matched_probs = [
        prob_by_norm.get(_norm_label(label), 0.0)
        for label in target_labels
    ]

    return max(matched_probs) if matched_probs else 0.0


def _matches_with_classifier_baseline(matches: list[dict]) -> list[dict]:
    return [
        {
            **m,
            "effective_score": round(float(m["similarity"]), 4),
            "domain_boosted": False,
            "ai_classifier_used": False,
            "ai_probability": 0.0,
            "ai_bonus": 0.0,
        }
        for m in matches
    ]


def rerank_by_ai_classifier(
    candidate_matches: list[dict],
    profile: dict,
    classifier_bundle: dict | None,
    alpha: float = CLASSIFIER_ALPHA,
    include_domain_hits: bool = False,
) -> tuple[list[dict], str, dict | None]:
    """
    기존 고정 도메인 보너스 대신 ml/job_classifier.py의 분류 확률로 재정렬한다.

    final_score = faiss_similarity + alpha * classifier_probability
    """
    if not candidate_matches:
        return [], "상위 매칭 없음 — FAISS 결과가 비어 있습니다.", None

    if classifier_bundle is None:
        return _matches_with_classifier_baseline(candidate_matches), (
            "분류모델을 로드하지 못해 FAISS 유사도 순서 그대로 적용했습니다."
        ), None

    pred = predict_profile(
        profile=profile,
        bundle=classifier_bundle,
        include_domain_hits=include_domain_hits,
    )

    probabilities = pred.get("probabilities") or {}
    pred_label = pred.get("pred_label", "")

    reranked: list[dict] = []

    for rank, m in enumerate(candidate_matches, start=1):
        sim = float(m.get("similarity", 0.0) or 0.0)
        job_category = str(m.get("category") or "")

        job_prob = get_classifier_probability_for_category(
            job_category,
            probabilities,
        )

        ai_bonus = alpha * job_prob
        effective = sim + ai_bonus

        reranked.append(
            {
                **m,
                "original_rank": rank,
                "effective_score": round(effective, 4),
                "domain_boosted": False,
                "ai_classifier_used": True,
                "ai_probability": round(job_prob, 4),
                "ai_bonus": round(ai_bonus, 4),
            }
        )

    reranked.sort(key=lambda x: x["effective_score"], reverse=True)

    top_probs = sorted(
        probabilities.items(),
        key=lambda x: x[1],
        reverse=True,
    )[:3]

    top_prob_text = ", ".join(
        f"{label} {prob:.3f}"
        for label, prob in top_probs
    ) or "없음"

    note = (
        f"분류모델 예측: '{pred_label}' "
        f"(상위 확률: {top_prob_text}) — "
        f"FAISS 유사도 + {alpha}×분류모델 직무확률로 재정렬했습니다."
    )

    return reranked, note, pred
#---------------추가------------

def _matches_with_baseline_scores(matches: list[dict]) -> list[dict]:
    return [
        {**m, "effective_score": round(float(m["similarity"]), 4), "domain_boosted": False}
        for m in matches
    ]


def rerank_by_domain(
    top_matches: list[dict],
    detected_domains: list[str],
    domain_hits: dict[str, int] | None = None,
) -> tuple[list[dict], str]:
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
    c: Counter = Counter()
    for r in profile.get("per_repo") or []:
        for d in r.get("detected_domains") or []:
            c[d] += 1
    return [d for d, _ in c.most_common()]


def check_domain_match_consistency(
    detected_domains: list[str],
    top_matches: list[dict],
) -> dict:
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
    v6.1: 절대값 기준을 추가. spread가 좁고 동시에 평균 유사도가 낮으면
    '약한 매칭'으로 통일된 코멘트, 평균이 높으면 '여러 직무 매칭'으로 안내.
    """
    max_s = max(top5_scores)
    min_s = min(top5_scores)
    spread = max_s - min_s
    avg = sum(top5_scores) / len(top5_scores)

    # 절대값 기준 우선 검사
    if max_s < 0.70:
        # 전반적으로 약한 매칭 — 레이블 모두 '약함'
        note = (
            "상위 5개 공고 모두 유사도가 낮습니다. "
            "프로필 텍스트가 어떤 직무와도 강하게 매칭되지 않습니다. "
            "README 보강 또는 기술 스택 명확화가 필요합니다."
        )
        return "약함", note

    if spread < 0.02:
        if avg < 0.75:
            note = (
                "상위 5개 공고가 모두 비슷한 보통 수준의 유사도에 몰려 있습니다. "
                "프로필 색깔이 뚜렷하지 않은 상태일 수 있습니다."
            )
        else:
            note = (
                "상위 5개 공고의 유사도가 비슷한 수준입니다. "
                "여러 직무가 일정 수준 매칭되는 다재다능한 프로필입니다."
            )
        # spread 좁을 때는 일괄 '보통'으로 통일
        return "보통", note

    # 일반 spread 분포 — 절대 + 상대 혼합
    if score >= 0.85:
        return "강함", None
    if score >= max_s - spread * 0.1:
        return "강함", None
    if score >= 0.75 or score >= max_s - spread * 0.4:
        return "강함", None
    if score >= 0.65:
        return "보통", None
    return "약함", None


def diagnose_domain_mismatch(
    detected_domains: list[str],
    top_matches: list[dict],
    domain_hits: dict[str, int],
) -> dict:
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


# v6.1: 기술 키워드와 포함관계 매핑 (Spring Boot가 있으면 Spring 제거)
TECH_KEYWORDS_FOR_PATTERN = [
    "Python", "Java", "JavaScript", "TypeScript", "React", "Vue", "Spring", "Spring Boot",
    "Docker", "Kubernetes", "AWS", "GCP", "Azure", "Go", "Rust", "C++", "Django", "FastAPI",
    "Node.js", "Kotlin", "Swift", "Flutter", "PyTorch", "TensorFlow", "Redis", "PostgreSQL",
    "MySQL", "MongoDB", "GraphQL", "REST API", "Terraform", "Lua"
]

# 포함관계: key 기술이 있으면 value 기술들은 제외
TECH_INCLUSION_MAP: dict[str, list[str]] = {
    "Spring Boot": ["Spring"],
    "FastAPI": [],
    "Django": [],
    "Next.js": ["React"],
    "Nuxt": ["Vue"],
}

# 도메인별 관련성 낮은 기술 (필터링 대상)
DOMAIN_IRRELEVANT_TECHS: dict[str, set[str]] = {
    "서버/백엔드": {"React", "Vue", "Flutter", "Swift", "Kotlin"},
    "프론트엔드": {"Spring", "Spring Boot", "FastAPI", "Django", "Kubernetes", "Terraform"},
    "웹 풀스택": set(),
    "인공지능/머신러닝": {"React", "Vue", "Flutter", "Swift"},
    "안드로이드": {"React", "Vue", "Spring", "Spring Boot", "Django", "FastAPI"},
    "iOS": {"React", "Vue", "Spring", "Spring Boot", "Django", "FastAPI"},
    "게임 클라이언트": {"React", "Vue", "Spring", "Spring Boot", "Django", "FastAPI", "Kubernetes"},
    "게임 서버": {"React", "Vue", "Flutter"},
    "devops/시스템 엔지니어": {"React", "Vue", "Flutter"},
}


def filter_techs_by_inclusion(techs: list[str]) -> list[str]:
    """포함관계에 따라 상위 기술이 있으면 하위 기술 제거."""
    techs_set = set(techs)
    to_remove: set[str] = set()
    for parent, children in TECH_INCLUSION_MAP.items():
        if parent in techs_set:
            to_remove.update(children)
    return [t for t in techs if t not in to_remove]


def filter_techs_by_domain(techs: list[str], target_category: str | None) -> list[str]:
    """매칭된 직무 카테고리와 관련 없는 기술 제거."""
    if not target_category:
        return techs
    irrelevant = DOMAIN_IRRELEVANT_TECHS.get(target_category, set())
    return [t for t in techs if t not in irrelevant]


# v6.1: 카테고리별 학습 권장 기술 (실제 채용 시장 기준)
CATEGORY_TARGET_TECHS: dict[str, list[str]] = {
    "서버/백엔드": ["Spring Boot", "Docker", "AWS", "PostgreSQL", "Redis"],
    "프론트엔드": ["React", "TypeScript", "Next.js", "Tailwind CSS"],
    "웹 풀스택": ["React", "Spring Boot", "Docker", "PostgreSQL"],
    "인공지능/머신러닝": ["PyTorch", "TensorFlow", "Python", "Hugging Face Transformers"],
    "안드로이드": ["Kotlin", "Jetpack Compose", "Coroutine"],
    "iOS": ["Swift", "SwiftUI", "Combine"],
    "게임 클라이언트": ["Unity", "C#", "Shader"],
    "게임 서버": ["C++", "Java", "Network", "Database"],
    "devops/시스템 엔지니어": ["Kubernetes", "Terraform", "AWS", "Docker"],
    "블록체인": ["Solidity", "Hardhat", "Web3.js"],
    "빅데이터 엔지니어": ["Airflow", "Spark", "dbt", "Kafka"],
    "크로스플랫폼 앱": ["Flutter", "Dart", "React Native"],
    "HW/임베디드": ["C", "C++", "RTOS"],
    "QA 엔지니어": ["Selenium", "Cypress", "Jest"],
    "DBA": ["PostgreSQL", "MySQL", "Redis"],
}


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
    if len(detected_domains) < 2:
        return None

    hits_sorted = sorted(domain_hits.values(), reverse=True)
    if len(hits_sorted) < 2 or hits_sorted[0] >= hits_sorted[1] * 2:
        return None

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
# 기술 매칭 분석 (v6.1: 포함관계 + 도메인 필터 + 미보유 3개 제한 + 학습 권장)
# ---------------------------------------------------------------------------

def analyze_tech_match(
    applicant_languages: str,
    applicant_frameworks: list[str],
    top_matches: list[dict],
    detected_domains: list[str] | None = None,
    target_category: str | None = None,
) -> dict:
    """
    v6.1 변경:
    - missing 결과에 Spring Boot/Spring 등 포함관계 처리
    - 매칭 직무와 관련 없는 기술 필터링
    - missing 최대 3개로 제한
    - 학습 권장 기술 제안 (target_category 기반)
    """
    applicant_techs: set[str] = set()
    for token in applicant_languages.replace(",", " ").split():
        clean = token.strip("()%0123456789").strip()
        if clean and len(clean) >= 2:
            applicant_techs.add(clean)
    for fw in applicant_frameworks:
        applicant_techs.add(fw)

    # 도메인 일치 공고 필터
    relevant_matches = top_matches
    if detected_domains:
        primary = detected_domains[0]
        expected_cats = DOMAIN_TO_CATEGORIES.get(primary, [])
        domain_filtered = [m for m in top_matches if m.get("category") in expected_cats]
        if domain_filtered:
            relevant_matches = domain_filtered

    combined_lower = "\n".join(
        (m["meta"].get("position") or "") + "\n" + (m["meta"].get("text") or "")
        for m in relevant_matches
    ).lower()
    required_techs_raw = [kw for kw in TECH_KEYWORDS_FOR_PATTERN if kw.lower() in combined_lower]

    # 포함관계 처리
    required_techs = filter_techs_by_inclusion(required_techs_raw)

    applicant_lower = {t.lower() for t in applicant_techs}
    matched = [kw for kw in required_techs if kw.lower() in applicant_lower]
    missing = [kw for kw in required_techs if kw.lower() not in applicant_lower]

    # 보유 기술도 포함관계 처리
    matched = filter_techs_by_inclusion(matched)
    # 미보유 기술 도메인 필터
    missing = filter_techs_by_domain(missing, target_category)
    # 최대 3개로 제한
    missing = missing[:3]

    # 공고 분류 태그
    raw_categories: list[str] = []
    for m in top_matches:
        raw_cat = m["meta"].get("category") or ""
        for part in re.split(r"[,，]", raw_cat):
            part = part.strip()
            if part:
                raw_categories.append(part)
    clean_cats = [c for c in raw_categories if "," not in c]
    company_types = [
        f"{name} 유사 공고 {cnt}건"
        for name, cnt in Counter(clean_cats).most_common(4)
    ]

    # 학습 권장 기술 (target_category가 있고 missing이 부족할 때 보강)
    target_techs = CATEGORY_TARGET_TECHS.get(target_category or "", [])
    learning_suggestions = [
        t for t in target_techs
        if t.lower() not in applicant_lower
    ][:3]

    return {
        "matched": matched,
        "missing": missing,
        "company_types": company_types,
        "applicant_techs": sorted(applicant_techs),
        "learning_suggestions": learning_suggestions,
    }


# ---------------------------------------------------------------------------
# v6.1: 모듈 A — 레포별 카드 출력 보조 함수
# ---------------------------------------------------------------------------

CORE_LABELS = {
    "readme_quality": "README 품질",
    "project_structure": "프로젝트 구조",
    "commit_quality": "커밋 메시지",
}

EXTRA_LABELS = {
    "test_coverage": "테스트",
    "cicd": "CI/CD",
    "deployment": "배포",
    "commit_pattern": "커밋 리듬",
}


def _print_diag_item(label: str, item: dict, indent: str = "    ") -> None:
    print(f"{indent}· {label}")
    print(f"{indent}    상태: {item.get('status', '?')}")
    print(f"{indent}    내용: {item.get('detail', '')}")
    act = item.get("action")
    if act:
        print(f"{indent}    권장: {act}")


def _print_extra_one_liner(label: str, item: dict, indent: str = "    ") -> None:
    """개인 레포의 운영/협업 항목은 필수 평가가 아니라 참고로만 표시."""
    status = item.get("status", "?")
    detail = item.get("detail", "")

    if status in ("양호", "규칙적"):
        print(f"{indent}· {label} (참고)  : ✓ {detail}")
    elif status in ("없음", "미경험", "선택 가점", "필수 미흡"):
        print(f"{indent}· {label} (참고)  : 개인 레포에서는 필수 감점 항목이 아닙니다")
    elif status == "보통":
        print(f"{indent}· {label} (참고)  : {detail}")
    elif status in ("불규칙", "개선 필요", "확인 필요"):
        print(f"{indent}· {label} (참고)  : {detail} (개인 작업에선 자연스러울 수 있음)")
    else:
        print(f"{indent}· {label} (참고)  : {detail}")


def _print_repo_card(diag: dict, idx: int) -> None:
    """레포 1개의 진단 카드 출력."""
    repo_name = diag.get("repo_name", "repo")
    repo_type = diag.get("repo_type", "personal")
    distinct = diag.get("distinct_author_count", 1)
    is_fork = diag.get("is_fork", False)
    context = diag.get("context_label")

    type_label_map = {
        "personal": "개인 레포",
        "team": f"팀 레포 · {distinct}명 협업",
    }
    type_label = type_label_map.get(repo_type, "레포")
    if is_fork:
        type_label += " · Fork"

    title = f"▼ 레포 {idx}: {repo_name}  [{type_label}]"
    if context:
        title += f"  ({context})"

    print(title)

    # 핵심 항목 (3개) — 모든 레포에서 공통
    print("  ─ 핵심 평가 항목 ─")
    for key, label in CORE_LABELS.items():
        item = diag["core_items"].get(key, {})
        _print_diag_item(label, item, indent="    ")

    # 운영/협업 항목 (4개) — 팀 레포에서만 필수 점검, 개인 레포는 양호 항목만 참고 표시
    if repo_type == "personal":
        # v6.2: 양호한 운영 항목만 "추가 강점 (참고)"으로 표시
        good_extras = [
            (key, EXTRA_LABELS[key], item)
            for key, item in diag["extra_items"].items()
            if item.get("status") in ("양호", "규칙적") and key in EXTRA_LABELS
        ]
        if good_extras:
            print("\n  ─ 추가 강점 (참고) ─")
            for _, label, item in good_extras:
                _print_extra_one_liner(label, item, indent="    ")
        return
    else:
        print("\n  ─ 필수 점검 항목 (팀 레포 기준) ─")
        for key, label in EXTRA_LABELS.items():
            item = diag["extra_items"].get(key, {})
            _print_diag_item(label, item, indent="    ")
            if key == "commit_pattern":
                total_commits = int(diag.get("total_repo_commits") or 0)
                my_commits = int(diag.get("target_commit_count") or 0)
                if total_commits > 0:
                    ratio = round((my_commits / total_commits) * 100, 1)
                    print(
                        f"        협업 신호: 전체 커밋 {total_commits}개 중 "
                        f"지원자 커밋 {my_commits}개 ({ratio}%)"
                    )
                # v6.2: 활동 기간 비율 표시
                target_weeks = int(diag.get("active_weeks") or 0)
                repo_weeks = int(diag.get("repo_active_weeks") or 0)
                if target_weeks > 0 and repo_weeks > 0 and repo_weeks >= target_weeks:
                    coverage = round(target_weeks / repo_weeks * 100, 1)
                    print(
                        f"        활동 기간: 지원자 {target_weeks}주 / "
                        f"레포 {repo_weeks}주 ({coverage}%)"
                    )


# ---------------------------------------------------------------------------
# v6.1: 지원자 요약 출력 (4개 항목만)
# ---------------------------------------------------------------------------

def _format_top_languages(top_languages: str) -> str:
    """'Java (76%), HTML (14%), JavaScript (9%)' → 'Java, HTML, JavaScript'"""
    if not top_languages or top_languages == "N/A":
        return "분석 데이터 없음"
    # 비율 제거: 괄호 안의 % 표기 삭제
    cleaned = re.sub(r"\s*\([^)]*\)", "", top_languages)
    # 콤마로 분리하고 빈 값 제거
    parts = [p.strip() for p in cleaned.split(",") if p.strip()]
    return ", ".join(parts) if parts else "분석 데이터 없음"


def _format_experience(years: int) -> str:
    if years <= 0:
        return "신입 (0년차)"
    return f"{years}년차"


def _print_applicant_summary(
    profile: dict,
    username: str,
    applicant_years: int,
    per_repo_diags: list[dict],
) -> None:
    """
    [지원자 요약] — 4개 항목만 출력.
      1. GitHub ID
      2. 경력
      3. 분석 레포 (이름 + 개인/팀)
      4. 기술 스택 (비율 제거)
    """
    print("\n[지원자 요약]")
    print(f"  GitHub ID    : {username}")
    print(f"  경력         : {_format_experience(applicant_years)}")

    n_repos = len(per_repo_diags)
    print(f"  분석 레포    : {n_repos}개")
    for d in per_repo_diags:
        nm = d.get("repo_name", "")
        rt = d.get("repo_type", "personal")
        distinct = d.get("distinct_author_count", 1)
        if rt == "team":
            type_str = f"[팀 · {distinct}명]"
        else:
            type_str = "[개인]"
        if d.get("is_fork"):
            type_str = type_str[:-1] + " · Fork]"
        print(f"    · {nm:<40} {type_str}")

    ms = profile.get("metrics_summary") or {}
    tech_str = _format_top_languages(ms.get("top_languages", ""))
    print(f"  기술 스택    : {tech_str}")

    # 경고는 유지 (오너십 의심 등 중요 신호)
    warns = profile.get("warnings") or []
    critical_warns = [w for w in warns if any(
        k in w for k in ["오너십", "rate limit", "Rate Limit"]
    )]
    if critical_warns:
        print("  경고:")
        for w in critical_warns:
            print(f"    - {w}")


# ---------------------------------------------------------------------------
# 메인 파이프라인
# ---------------------------------------------------------------------------

async def run_e2e_pipeline(
    target_username: str,
    target_repos: list[str],
    applicant_years: int,
) -> None:
    # v6.1: 입력 레포 개수 제한 (메인 1 + 서브 2 권장)
    if len(target_repos) > MAX_REPO_COUNT:
        print(
            f"\n⚠ 레포는 최대 {MAX_REPO_COUNT}개까지 분석 가능합니다. "
            "메인 프로젝트 1개 + 서브 프로젝트 2개를 선별해서 입력하세요."
        )
        print(f"   입력된 {len(target_repos)}개 중 앞 {MAX_REPO_COUNT}개만 사용합니다.")
        target_repos = target_repos[:MAX_REPO_COUNT]
    if not target_repos:
        print("\n⚠ 분석할 레포가 없습니다. TARGET_REPOS에 1~3개 입력하세요.")
        return

    current_dir = os.path.dirname(os.path.abspath(__file__))
    index_path = os.path.join(current_dir, "vector", "git2value_faiss.index")
    meta_path  = os.path.join(current_dir, "vector", "git2value_metadata.json")
    cache_path = os.path.join(current_dir, "vector", "experience_cache.json")

    # ── 1. 인프라 로딩 ──────────────────────────────────────────
    print("\n[Step 1] 벡터 DB 및 연봉 엔진 로딩 중...")
    index = faiss.read_index(index_path)
    with open(meta_path, "r", encoding="utf-8") as f:
        metadata = json.load(f)
    # model = SentenceTransformer("jhgan/ko-sroberta-multitask")
    # val_engine = Git2ValueEngine()
    # exp_cache = load_or_build_cache(metadata, cache_path)
    # print("  완료.")
    #추가------------------
    model = SentenceTransformer("jhgan/ko-sroberta-multitask")
    val_engine = Git2ValueEngine()
    exp_cache = load_or_build_cache(metadata, cache_path)

    classifier_model_path = Path(current_dir) / "ml" / "models" / "job_classifier.pkl"

    try:
        classifier_bundle = load_model_bundle(classifier_model_path)
        print(f"  분류모델 로드 완료: {classifier_model_path}")
    except Exception as e:
        classifier_bundle = None
        print(f"  ⚠ 분류모델 로드 실패: {e}")
    print("  완료.")
    
    # ── 2. GitHub 실시간 스캔 ───────────────────────────────────
    print(f"\n[Step 2] GitHub 스캔 시작 — {target_username}")
    print(f"  대상 레포 ({len(target_repos)}개): {', '.join(target_repos)}")
    extractor = GitHubExtractor()
    profile = await extractor.extract_applicant_profile(target_username, target_repos)

    match_text = (profile.get("profile_for_matching") or "").strip() or (
        profile.get("applicant_resume") or ""
    )

    # ── 3. FAISS JD 매칭 (k=100 → 0년차 기준 경력 필터) ─────────────
    SEARCH_K = min(100, len(metadata), getattr(index, "ntotal", len(metadata)))
    print(f"\n[Step 3] AI 직무 매칭 중 (Top {SEARCH_K} 추출 → 0년차/연차 필터링)...")
    query_vector = model.encode([match_text], normalize_embeddings=True)
    distances, indices = index.search(query_vector, SEARCH_K)

    raw_matches_extended: list[dict] = []
    for i in range(SEARCH_K):
        idx = indices[0][i]
        if idx < 0 or idx >= len(metadata):
            break
        dist = distances[0][i]
        meta = metadata[idx]
        raw_matches_extended.append({
            "meta": meta,
            "similarity": float(dist),
            "category": route_job_category_safe(meta["position"]),
        })

    entry_matches, excluded_exp_matches = split_by_experience(
        raw_matches_extended, applicant_years, exp_cache
    )

    if entry_matches:
        top_matches_extended = entry_matches
    else:
        # 데이터셋 상위권에 신입/경력무관 공고가 하나도 없을 때만 안전 폴백.
        # 이 경우 출력에서 경력 경고를 유지한다.
        top_matches_extended = excluded_exp_matches[:10]

    detected_domains_merged = merged_detected_domains_from_profile(profile)
    domain_hits_merged = profile.get("domain_hits_merged") or {}

    multi_domain_result = recommend_multi_domain(
        top_matches_extended, detected_domains_merged, domain_hits_merged
    )

    # reranked_matches, rerank_note = rerank_by_domain(
    #     top_matches_extended[:20], detected_domains_merged, domain_hits_merged
    # )
    # top_matches_5 = reranked_matches[:5]
    #추가-------------------
    reranked_matches, rerank_note, classifier_pred = rerank_by_ai_classifier(
        top_matches_extended[:20],
        profile=profile,
        classifier_bundle=classifier_bundle,
        alpha=CLASSIFIER_ALPHA,
        include_domain_hits=False,
    )
    top_matches_5 = reranked_matches[:5]

    jumpit_category = top_matches_5[0]["category"] if top_matches_5 else "SW/솔루션"
    domain_check = check_domain_match_consistency(detected_domains_merged, top_matches_5)
    mismatch_diag = diagnose_domain_mismatch(
        detected_domains_merged, top_matches_5, domain_hits_merged
    )

    print("\n[Step 4] 포트폴리오 진단 (룰베이스, 레포별)...")
    diag_bundle = run_diagnosis(profile)
    per_repo_diags = diag_bundle.get("per_repo_diagnoses") or []

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
        top_matches=top_matches_5,
        detected_domains=detected_domains_merged,
        target_category=jumpit_category,
    )

    # ── 6. 최종 리포트 (3개 독립 모듈) ───────────────────────────
    print("\n" + "=" * 60)
    print("[Git2Value v6.3] 최종 리포트 — 모듈 A / B / C")
    print("=" * 60)

    repo_classifications = diag_bundle.get("repo_classifications") or []
    has_mod_or_config = any(
        rc["type"] in ("mod", "config") for rc in repo_classifications
    )

    # ── 지원자 요약 (4개 항목만) ──────────────────────────────
    _print_applicant_summary(profile, target_username, applicant_years, per_repo_diags)

    # ── 모드/설정 프로젝트 분류 안내 (선택적) ─────────────────
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

    # ── 모듈 A: 포트폴리오 진단 (레포별 카드) ──────────────────
    print("\n" + "-" * 60)
    print(f"[모듈 A] 포트폴리오 진단 — 레포별 평가 ({len(per_repo_diags)}개)")
    print("-" * 60)

    if not per_repo_diags:
        print("  분석된 레포가 없습니다.")
    else:
        for i, diag in enumerate(per_repo_diags, 1):
            print()
            _print_repo_card(diag, i)

    # 종합 분석 (GitHub 점수 + 강점 + Quick wins)
    summary_block = diag_bundle.get("summary_block", "")
    if summary_block:
        print(f"\n{summary_block}")

    # ── 모듈 B: 직무 매칭 ──────────────────────────────────────
    print("\n" + "-" * 60)
    if multi_domain_result:
        print("[모듈 B] 직무 매칭 — 다중 도메인 프로젝트 (균형 추천)")
    else:
        print("[모듈 B] 직무 매칭 (FAISS + AI 분류모델 리랭킹)")
    print("-" * 60)

    if multi_domain_result:
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
        domain_list = list(multi_domain_result["domain_picks"].keys())
        top_domain = domain_list[0] if domain_list else "해당 도메인"
        top_picks = multi_domain_result["domain_picks"].get(top_domain, [])
        top_sim = float(top_picks[0]["similarity"]) if top_picks else 0
        print(f"  종합 분석:")
        print(f"    · 가장 강한 매칭은 {top_domain} 영역입니다 (유사도 {top_sim:.4f}).")
        print(f"    · 풀스택 경험을 어필하려면 README에 각 영역의 기여를 명시하세요.")
        print(f"  감지 도메인: {', '.join(detected_domains_merged[:4])}")
    else:
        # 단일 도메인
        top5_effective = [float(m["effective_score"]) for m in top_matches_5]
        system_note_printed = False
        for i, match in enumerate(top_matches_5):
            m = match["meta"]
            rank_label = "1순위" if i == 0 else f"{i + 1}순위"
            sim = float(match["similarity"])
            eff = float(match["effective_score"])
            # boosted = bool(match.get("domain_boosted"))
            # label, sys_note = similarity_label(eff, top5_effective)
            # exp_warn = match.get("experience_warning")
            # exp_str = f"  [⚠ {exp_warn} — 지원 가능 경력에 미달]" if exp_warn else ""
            # print(f"  [{rank_label}] [{m['company_name']}] {m['position']}{exp_str}")
            # if boosted:
            #     print(
            #         f"          (FAISS: {sim:.4f} + 도메인 일치: +{DOMAIN_BOOST} "
            #         f"→ 유효: {eff:.4f} · {label})"
            #     )
            # else:
            #     print(f"          (FAISS: {sim:.4f} · {label})")
            
            #추가
            boosted = bool(match.get("domain_boosted"))
            ai_used = bool(match.get("ai_classifier_used"))

            label, sys_note = similarity_label(eff, top5_effective)
            exp_warn = match.get("experience_warning")
            exp_str = f"  [⚠ {exp_warn} — 지원 가능 경력에 미달]" if exp_warn else ""

            print(f"  [{rank_label}] [{m['company_name']}] {m['position']}{exp_str}")

            if ai_used:
                ai_prob = float(match.get("ai_probability", 0.0) or 0.0)
                ai_bonus = float(match.get("ai_bonus", 0.0) or 0.0)

                print(
                    f"          (FAISS: {sim:.4f} + 분류모델: {ai_prob:.3f}×{CLASSIFIER_ALPHA}="
                    f"{ai_bonus:.4f} → 유효: {eff:.4f} · {label})"
                )

            elif boosted:
                print(
                    f"          (FAISS: {sim:.4f} + 도메인 일치: +{DOMAIN_BOOST} "
                    f"→ 유효: {eff:.4f} · {label})"
                )

            else:
                print(f"          (FAISS: {sim:.4f} · {label})")
            if sys_note and not system_note_printed:
                print(f"\n  ⚠ 매칭 분포 안내: {sys_note}")
                system_note_printed = True
        print(f"\n  {rerank_note}")

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
    print(f"    보유 & 공고 일치: {matched_str}")

    if tech_result.get("learning_suggestions"):
        sug_str = ", ".join(tech_result["learning_suggestions"])
        print(f"    {jumpit_category} 직무 학습 추천: {sug_str}")

    # ── 모듈 C: 시장 연봉 밴드 ─────────────────────────────────
    print("\n" + "-" * 60)
    print("[모듈 C] 시장 연봉 밴드 (신입~3년 구간, GitHub 점수 미반영)")
    print("-" * 60)
    msb = band_report["market_salary_band"]
    sr = msb["salary_range"]
    rr = msb.get("realistic_range", {})

    print(f"  매칭 직무       : {msb['matched_category']}")
    # 도메인 감지와 라우팅 직무가 다를 때 참고 직무 표시
    if detected_domains_merged and jumpit_category not in (
        DOMAIN_TO_CATEGORIES.get(detected_domains_merged[0], [])
    ):
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

    # 도메인 불일치 시 대안 밴드
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

    # ── [참고 직무] — 매칭 공고/감지 도메인 기준 ───────────────────
    # category_comparison은 상위 12개 고연봉 직무만 담기 때문에 여기서 쓰면
    # 프론트엔드처럼 데이터가 있어도 누락될 수 있다. 직무별로 직접 조회한다.
    matched_categories_seen: list[str] = []

    def _add_ref_category(cat: str | None) -> None:
        if cat and cat != jumpit_category and cat not in matched_categories_seen:
            matched_categories_seen.append(cat)

    if multi_domain_result:
        for _domain, picks in multi_domain_result["domain_picks"].items():
            for pick in picks:
                _add_ref_category(pick.get("category"))
    else:
        for m in top_matches_5[1:]:
            _add_ref_category(m.get("category"))

    # 공고 추천에는 경력 필터가 적용되지만, 연봉 참고선은 감지 도메인도 함께 보여준다.
    for domain in detected_domains_merged[:3]:
        for cat in DOMAIN_TO_CATEGORIES.get(domain, []):
            _add_ref_category(cat)

    if matched_categories_seen:
        print(f"\n  [참고 직무 — 매칭 공고/감지 도메인 기준]")
        ref_count = 0
        for cat in matched_categories_seen:
            try:
                ref_band = val_engine.get_market_band(
                    job_category=cat,
                    years_max=3 if applicant_years <= 3 else applicant_years,
                )
            except ValueError:
                continue
            ref_sr = ref_band["market_salary_band"]["salary_range"]
            print(f"    {cat}: {ref_sr['combined_range']}")
            ref_count += 1
            if ref_count >= 4:
                break
        if ref_count == 0:
            print("    (참고 직무의 연봉 데이터가 없습니다)")
        else:
            print("    → 참고용 수치입니다. 회사 규모·지역·협상에 따라 차이가 있습니다.")

    print("=" * 60)


if __name__ == "__main__":
    if platform.system() == "Windows":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    # ================================================================
    # [입력] 분석할 지원자 정보를 여기서 수정하세요
    # 레포는 최대 3개 (메인 1 + 서브 2 권장)
    TARGET_USERNAME =  "hojunnnnn"#"AstroJini"#"chjnett"#"honey766"#"tekyung"#"siheon012"#"jww0108"#"2026TUKCOMCD"#"Central-MakeUs"#"Project-Guideon"#"AstroJini"#
    TARGET_REPOS = [
        #"AstroJini/SmartFridge/tree/develop",
        #"AstroJini/SmartFridge-FE/tree/develop",
        #"tekyung/Ttakji_lab-mobile_development_dep/tree/M1_milestone", # unity, C# 게임 개발
        #"tekyung/kyonggi-university_network-system-laboratory_webpage", # 프론트엔드
        #"siheon012/Deepsentinel", # ai, 웹 풀스택
        #"Virtual-Company-Mal-Geum/ai-server/tree/tekyung", # ai 백엔드
        #"jww0108/2026_Cap stone/tree/tekyung" # 백엔드
        #"honey766/Paint", # unity, 게임 개발
        #"honey766/Balls-Run/tree/main", # unity, 게임 개발
        #"2026TUKCOMCD/SyncLab", # 웹 풀스택, 모바일
        #"Central-MakeUs/AZIT_Front/tree/develop", # 프론트엔드
        #"Project-Guideon/guideon-backend", # 백엔드
        #"AstroJini/MKX-BE/tree/develop", # 웹 풀스택
        "AstroJini/SmartFridge/tree/develop", # 웹 풀스택
        "chjnett/my-sports-ai/tree/main", # ai, 머신러닝
        "hojunnnnn/board/tree/master" #서버/백엔드
    ]
    APPLICANT_YEARS = 0
    # ================================================================

    asyncio.run(run_e2e_pipeline(TARGET_USERNAME, TARGET_REPOS, APPLICANT_YEARS))
