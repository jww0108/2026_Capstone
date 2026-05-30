from __future__ import annotations

import json
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import profile_builder
from run_git2value import (
    DOMAIN_TO_CATEGORIES,
    recommend_multi_domain,
    rerank_by_domain,
    route_job_category,
)


FIXTURE_TREES_DIR = os.path.join(os.path.dirname(__file__), "fixtures", "trees")


def _load_tree_fixture(filename: str) -> dict:
    path = os.path.join(FIXTURE_TREES_DIR, filename)
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def test_merge_readme_domain_hits_adds_frontend_aux_signal() -> None:
    merged = profile_builder.merge_readme_domain_hits({}, "React SPA 기반 웹 프로젝트")
    assert merged.get("웹 프론트엔드") == 1


def test_merge_readme_domain_hits_keeps_backend_primary_when_tree_strong() -> None:
    base_hits = {"서버/백엔드": 5}
    merged = profile_builder.merge_readme_domain_hits(base_hits, "React SPA 웹")
    assert merged["서버/백엔드"] == 5
    assert merged["웹 프론트엔드"] == 1

    ordered = sorted(merged.keys(), key=lambda d: merged[d], reverse=True)
    assert ordered[0] == "서버/백엔드"


def test_extract_readme_keywords_returns_summary_without_nameerror() -> None:
    summary = profile_builder.extract_readme_keywords(
        "이 프로젝트는 React 기반 웹 SPA이며 SEO와 반응형 UI를 제공합니다."
    )
    assert summary
    assert "관련 프로젝트" in summary


def test_detect_domain_hits_on_mini_tree_fixture() -> None:
    tree_data = _load_tree_fixture("frontend_mini_tree.json")
    hits = profile_builder.detect_domain_hits(tree_data)
    assert hits.get("웹 프론트엔드", 0) >= 2


def test_detect_domain_hits_avoids_tool_domain_on_generic_manifest_noise() -> None:
    tree_data = _load_tree_fixture("frontend_manifest_noise_tree.json")
    hits = profile_builder.detect_domain_hits(tree_data)
    assert "도구 개발" not in hits


def test_detect_domain_hits_keeps_tool_domain_on_browser_extension_fixture() -> None:
    tree_data = _load_tree_fixture("browser_extension_tree.json")
    hits = profile_builder.detect_domain_hits(tree_data)
    assert hits.get("도구 개발", 0) >= 2


def test_detect_domain_hits_suppresses_mobile_game_without_strong_evidence() -> None:
    tree_data = _load_tree_fixture("ai_backend_noise_tree.json")
    hits = profile_builder.detect_domain_hits(tree_data)
    assert hits.get("서버/백엔드", 0) >= 2
    assert hits.get("ML/AI", 0) >= 2
    assert "모바일 앱" not in hits
    assert "게임 개발" not in hits


def test_detect_domain_hits_keeps_mobile_with_strong_evidence() -> None:
    tree_data = _load_tree_fixture("mobile_react_native_tree.json")
    hits = profile_builder.detect_domain_hits(tree_data)
    assert hits.get("모바일 앱", 0) >= 2


def test_detect_domain_hits_keeps_game_with_strong_evidence() -> None:
    tree_data = _load_tree_fixture("game_engine_tree.json")
    hits = profile_builder.detect_domain_hits(tree_data)
    assert hits.get("게임 개발", 0) >= 2


@pytest.mark.parametrize(
    "title,expected",
    [
        ("웹 개발자", "웹 풀스택"),
        ("Frontend 웹 개발", "프론트엔드"),
        ("자바 웹 개발", "서버/백엔드"),
        ("JAVA 웹 개발", "서버/백엔드"),
        ("Node 웹 개발자", "서버/백엔드"),
    ],
)
def test_route_job_category_webdev_cases(title: str, expected: str) -> None:
    assert route_job_category(title) == expected


def test_domain_to_categories_has_extended_mappings() -> None:
    for key in ("HW/임베디드", "DBA/데이터", "그래픽스"):
        assert DOMAIN_TO_CATEGORIES.get(key)


def test_rerank_by_domain_boosts_frontend_category_only() -> None:
    top_matches = [
        {"category": "서버/백엔드", "similarity": 0.83, "meta": {"position": "백엔드 개발자"}},
        {"category": "프론트엔드", "similarity": 0.82, "meta": {"position": "프론트엔드 개발자"}},
    ]
    reranked, note = rerank_by_domain(
        top_matches,
        detected_domains=["웹 프론트엔드"],
        domain_hits={"웹 프론트엔드": 4},
    )
    assert "재정렬" in note
    boosted = [m for m in reranked if m["category"] == "프론트엔드"][0]
    non_boosted = [m for m in reranked if m["category"] == "서버/백엔드"][0]
    assert boosted["domain_boosted"] is True
    assert non_boosted["domain_boosted"] is False
    assert reranked[0]["category"] == "프론트엔드"


def test_rerank_by_domain_skips_when_multi_domain_hits_are_close() -> None:
    top_matches = [
        {"category": "서버/백엔드", "similarity": 0.84, "meta": {"position": "백엔드 개발자"}},
        {"category": "프론트엔드", "similarity": 0.83, "meta": {"position": "프론트엔드 개발자"}},
    ]
    reranked, note = rerank_by_domain(
        top_matches,
        detected_domains=["서버/백엔드", "웹 프론트엔드"],
        domain_hits={"서버/백엔드": 4, "웹 프론트엔드": 3},
    )
    assert "다중 도메인 감지" in note
    assert all(m["domain_boosted"] is False for m in reranked)


def test_rerank_by_domain_does_not_trigger_mixed_for_weak_tool_domain() -> None:
    top_matches = [
        {"category": "프론트엔드", "similarity": 0.84, "meta": {"position": "프론트엔드 개발자"}},
        {"category": "서버/백엔드", "similarity": 0.83, "meta": {"position": "백엔드 개발자"}},
    ]
    reranked, note = rerank_by_domain(
        top_matches,
        detected_domains=["웹 프론트엔드", "도구 개발"],
        domain_hits={"웹 프론트엔드": 5, "도구 개발": 3},
    )
    assert "다중 도메인 감지" not in note
    assert reranked[0]["category"] == "프론트엔드"


def test_recommend_multi_domain_skips_when_tool_domain_is_weak() -> None:
    picks = recommend_multi_domain(
        top_matches_extended=[
            {"category": "프론트엔드", "similarity": 0.84, "meta": {"position": "프론트엔드 개발자"}},
            {"category": "서버/백엔드", "similarity": 0.83, "meta": {"position": "백엔드 개발자"}},
        ],
        detected_domains=["웹 프론트엔드", "도구 개발"],
        domain_hits={"웹 프론트엔드": 5, "도구 개발": 3},
    )
    assert picks is None

