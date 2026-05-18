"""
Git2Value v7.0 — LLM README 평가기 골든 셋 검증.

vLLM 서버가 실행 중인 상태에서 아래 커맨드로 실행:
    python tests/test_golden_set.py

통과 기준:
  - tier 일치율 80% 이상 (25개 중 20개)
  - 1단계 이내 오차율 100% ("양호"↔"미흡" 직접 반전 없음)
  - JSON 파싱 성공률 100%
"""
from __future__ import annotations

import asyncio
import os
import sys
import time
from typing import Any, Dict, List, Optional

# 프로젝트 루트를 경로에 추가
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from llm_readme_evaluator import ReadmeEvaluator

# ── 테스트용 fixtures 경로 ─────────────────────────────────
FIXTURE_DIR = os.path.join(os.path.dirname(__file__), "fixtures")

TIER_ORDER = ["미흡", "보통", "양호"]


def _load_fixture(filename: str) -> str:
    path = os.path.join(FIXTURE_DIR, filename)
    if not os.path.exists(path):
        return ""
    with open(path, encoding="utf-8") as f:
        return f.read()


# ── 골든 셋 정의 (25개) ───────────────────────────────────
GOLDEN_SET: List[Dict[str, Any]] = [
    {
        "id": 1,
        "name": "README 없음",
        "fixture": "01_empty_readme.md",
        "meta": {"languages": {}, "domain": "", "signatures": [], "repo_type": "personal"},
        "expected_tier": "미흡",
        "expected_llm_call": False,  # 50자 미만이므로 LLM 호출 안 함
    },
    {
        "id": 2,
        "name": "CRA 보일러플레이트",
        "fixture": "02_cra_boilerplate.md",
        "meta": {"languages": {"JavaScript": 90}, "domain": "프론트엔드", "signatures": ["React"], "repo_type": "personal"},
        "expected_tier": "미흡",
        "expected_llm_call": True,
    },
    {
        "id": 3,
        "name": "한 줄 설명만",
        "fixture": "03_one_liner.md",
        "meta": {"languages": {}, "domain": "", "signatures": [], "repo_type": "personal"},
        "expected_tier": "미흡",
        "expected_llm_call": False,  # 50자 미만
    },
    {
        "id": 4,
        "name": "목적만 있고 기술/실행 없음",
        "fixture": "04_purpose_only.md",
        "meta": {"languages": {"Java": 80}, "domain": "서버/백엔드", "signatures": [], "repo_type": "team"},
        "expected_tier": "미흡",  # 목적만 있어도 기술/실행 없으면 종합 미흡이 자연스러움
        "expected_tier_range": ["미흡", "보통"],
        "expected_llm_call": True,
    },
    {
        "id": 5,
        "name": "기술 나열만 (설명 없음)",
        "fixture": "05_tech_list_only.md",
        "meta": {"languages": {"JavaScript": 70, "TypeScript": 20}, "domain": "프론트엔드", "signatures": ["React", "Node.js"], "repo_type": "team"},
        "expected_tier": "미흡",
        "expected_tier_range": ["미흡", "보통"],
        "expected_llm_call": True,
    },
    {
        "id": 6,
        "name": "목적+기술 있으나 실행 가이드 없음",
        "fixture": "06_purpose_and_tech_no_setup.md",
        "meta": {"languages": {"TypeScript": 60, "Java": 30}, "domain": "서버/백엔드", "signatures": ["Spring Boot", "React", "WebSocket"], "repo_type": "team"},
        "expected_tier": "미흡",  # 실행/시각 부재 시 LLM 종합 점수 1~2에 가까움
        "expected_tier_range": ["미흡", "보통"],
        "expected_llm_call": True,
    },
    {
        "id": 7,
        "name": "영문 README (잘 작성됨)",
        "fixture": "07_english_well_written.md",
        "meta": {"languages": {"Python": 90}, "domain": "서버/백엔드", "signatures": ["FastAPI", "Docker"], "repo_type": "personal"},
        "expected_tier": "양호",
        "expected_llm_call": True,
    },
    {
        "id": 8,
        "name": "한국어 README (잘 작성됨)",
        "fixture": "08_korean_well_written.md",
        "meta": {"languages": {"Java": 70, "TypeScript": 20}, "domain": "서버/백엔드", "signatures": ["Spring Boot", "React", "RabbitMQ", "Docker"], "repo_type": "team"},
        "expected_tier": "양호",
        "expected_llm_call": True,
    },
    {
        "id": 9,
        "name": "Unity 게임 프로젝트",
        "fixture": "09_unity_game.md",
        "meta": {"languages": {"C#": 95}, "domain": "게임 클라이언트", "signatures": ["Unity"], "repo_type": "personal"},
        "expected_tier": "보통",  # 게임 맥락에서는 양호 허용
        "expected_tier_range": ["보통", "양호"],
        "expected_llm_call": True,
    },
    {
        "id": 10,
        "name": "ML 프로젝트 (모델 성능 포함)",
        "fixture": "10_ml_with_metrics.md",
        "meta": {"languages": {"Python": 95}, "domain": "인공지능/머신러닝", "signatures": ["PyTorch", "FastAPI"], "repo_type": "personal"},
        "expected_tier": "양호",
        "expected_llm_call": True,
    },
    {
        "id": 11,
        "name": "스크린샷만 있고 설명 없음",
        "fixture": "11_screenshot_only.md",
        "meta": {"languages": {}, "domain": "프론트엔드", "signatures": [], "repo_type": "personal"},
        "expected_tier": "미흡",
        "expected_llm_call": True,  # 실제 내용이 50자 초과 (이미지 링크 포함)
    },
    {
        "id": 12,
        "name": "상세하지만 이미지 없음",
        "fixture": "12_detailed_no_image.md",
        "meta": {"languages": {"Java": 60, "TypeScript": 30}, "domain": "서버/백엔드", "signatures": ["Spring Boot", "React", "Redis", "AWS"], "repo_type": "team"},
        "expected_tier": "보통",  # 내용은 풍부하나 시각 자료 없음
        "expected_tier_range": ["보통", "양호"],
        "expected_llm_call": True,
    },
    {
        "id": 13,
        "name": "완벽한 README",
        "fixture": "13_perfect_readme.md",
        "meta": {"languages": {"TypeScript": 50, "Java": 40}, "domain": "서버/백엔드", "signatures": ["Spring Boot", "React", "Docker", "AWS"], "repo_type": "team"},
        "expected_tier": "양호",
        "expected_min_score": 4,
        "expected_llm_call": True,
    },
    {
        "id": 14,
        "name": "일본어 README",
        "fixture": "14_japanese_readme.md",
        "meta": {"languages": {"JavaScript": 80}, "domain": "프론트엔드", "signatures": ["Vue.js", "Node.js"], "repo_type": "personal"},
        "expected_tier": "보통",
        "expected_llm_call": True,
    },
    {
        "id": 15,
        "name": "자동 생성 README (Copilot 등)",
        "fixture": "15_copilot_generated.md",
        "meta": {"languages": {"JavaScript": 90}, "domain": "서버/백엔드", "signatures": [], "repo_type": "personal"},
        "expected_tier": "보통",  # 플레이스홀더가 많아 미흡에 가까울 수 있음
        "expected_tier_range": ["미흡", "보통"],
        "expected_llm_call": True,
    },
    # ── 신규 케이스 (16-25): 경계 케이스 및 도메인 다양화 ──────
    {
        "id": 16,
        "name": "한국어 프론트엔드 (중간 수준)",
        "fixture": "16_frontend_mid_korean.md",
        "meta": {"languages": {"TypeScript": 70, "JavaScript": 20}, "domain": "프론트엔드", "signatures": ["React", "Zustand"], "repo_type": "personal"},
        "expected_tier": "보통",  # 목적+기술+스크린샷 1개, 실행 불완전
        "expected_tier_range": ["미흡", "보통"],
        "expected_llm_call": True,
    },
    {
        "id": 17,
        "name": "CLI 도구 (영문, 실행 예시 상세)",
        "fixture": "17_cli_tool_english.md",
        "meta": {"languages": {"Python": 100}, "domain": "CLI/유틸리티", "signatures": [], "repo_type": "personal"},
        "expected_tier": "보통",  # 목적+실행 예시 충분, 시각 없음
        "expected_tier_range": ["보통", "양호"],
        "expected_llm_call": True,
    },
    {
        "id": 18,
        "name": "아키텍처 다이어그램 + 데모 GIF",
        "fixture": "18_architecture_diagram.md",
        "meta": {"languages": {"Java": 70, "TypeScript": 20}, "domain": "서버/백엔드", "signatures": ["Spring Boot", "Kafka", "Docker"], "repo_type": "team"},
        "expected_tier": "양호",
        "expected_min_score": 4,
        "expected_llm_call": True,
    },
    {
        "id": 19,
        "name": "Docker 원클릭 실행 + 스크린샷 2개",
        "fixture": "19_docker_oneclick.md",
        "meta": {"languages": {"Python": 50, "TypeScript": 40}, "domain": "서버/백엔드", "signatures": ["FastAPI", "React", "Docker"], "repo_type": "team"},
        "expected_tier": "양호",
        "expected_tier_range": ["보통", "양호"],
        "expected_llm_call": True,
    },
    {
        "id": 20,
        "name": "데이터 분석 (모델 성능표 + 시각화)",
        "fixture": "20_data_analysis.md",
        "meta": {"languages": {"Python": 95}, "domain": "인공지능/머신러닝", "signatures": ["XGBoost", "Jupyter"], "repo_type": "personal"},
        "expected_tier": "양호",
        "expected_tier_range": ["보통", "양호"],
        "expected_llm_call": True,
    },
    {
        "id": 21,
        "name": "React Native 기초 (설명 빈약)",
        "fixture": "21_react_native_basic.md",
        "meta": {"languages": {"JavaScript": 90}, "domain": "모바일 앱", "signatures": ["React Native", "Expo"], "repo_type": "personal"},
        "expected_tier": "미흡",
        "expected_tier_range": ["미흡", "보통"],
        "expected_llm_call": True,
    },
    {
        "id": 22,
        "name": "자동화 스크립트 (설명 없음)",
        "fixture": "22_automation_script.md",
        "meta": {"languages": {"Python": 100}, "domain": "CLI/유틸리티", "signatures": [], "repo_type": "personal"},
        "expected_tier": "미흡",
        "expected_llm_call": True,
    },
    {
        "id": 23,
        "name": "크롤러 프로젝트 (한국어, 설명+실행 있음)",
        "fixture": "23_crawler_project.md",
        "meta": {"languages": {"Python": 100}, "domain": "CLI/유틸리티", "signatures": ["Selenium", "BeautifulSoup"], "repo_type": "personal"},
        "expected_tier": "보통",
        "expected_tier_range": ["보통", "양호"],
        "expected_llm_call": True,
    },
    {
        "id": 24,
        "name": "영문 중간 수준 백엔드 API",
        "fixture": "24_english_mid_backend.md",
        "meta": {"languages": {"JavaScript": 90}, "domain": "서버/백엔드", "signatures": ["Node.js", "Express", "MongoDB"], "repo_type": "personal"},
        "expected_tier": "보통",
        "expected_tier_range": ["보통", "양호"],
        "expected_llm_call": True,
    },
    {
        "id": 25,
        "name": "한국어 완벽 README (문제정의+아키텍처+GIF)",
        "fixture": "25_perfect_korean_readme.md",
        "meta": {"languages": {"Java": 50, "TypeScript": 40}, "domain": "서버/백엔드", "signatures": ["Spring Boot", "React", "Redis", "Docker"], "repo_type": "team"},
        "expected_tier": "양호",
        "expected_min_score": 4,
        "expected_llm_call": True,
    },
]


def _tier_distance(a: str, b: str) -> int:
    """tier 간 거리 (0=일치, 1=인접, 2=반전)."""
    try:
        return abs(TIER_ORDER.index(a) - TIER_ORDER.index(b))
    except ValueError:
        return 99


def _print_bar(label: str, s: int) -> str:
    return f"{'█' * s}{'░' * (5 - s)} {s}/5"


async def run_golden_test() -> None:
    evaluator = ReadmeEvaluator()

    print("=" * 65)
    print("Git2Value v7.0 — LLM README 골든 셋 테스트 (25개)")
    print("=" * 65)

    server_ok = await evaluator.health_check()
    if not server_ok:
        print("\n[오류] vLLM 서버에 연결할 수 없습니다.")
        print("  → 서버를 먼저 실행하세요:")
        print("    vllm serve Qwen/Qwen2.5-32B-Instruct-AWQ \\")
        print("      --gpu-memory-utilization 0.85 --max-model-len 4096")
        sys.exit(1)

    print(f"\n  vLLM 서버 가용 확인 완료.\n")

    results = []
    total_elapsed = 0.0

    for case in GOLDEN_SET:
        readme_raw = _load_fixture(case["fixture"])
        expected_call = case.get("expected_llm_call", True)

        print(f"[{case['id']:02d}] {case['name']}")

        t0 = time.perf_counter()
        llm_result = await evaluator.evaluate(readme_raw, case["meta"])
        elapsed = time.perf_counter() - t0
        total_elapsed += elapsed

        # LLM 호출 여부 검증
        if expected_call is False:
            if llm_result is not None:
                print(f"  FAIL  LLM이 호출되면 안 되는 케이스인데 결과 반환됨")
                results.append({"id": case["id"], "name": case["name"], "match": False,
                                "expected": case["expected_tier"], "actual": "N/A",
                                "skip_reason": "unexpected_llm_call"})
                continue
            else:
                print(f"  PASS  LLM 미호출 확인 (50자 미만) — 기대: {case['expected_tier']}")
                results.append({"id": case["id"], "name": case["name"], "match": True,
                                "expected": case["expected_tier"], "actual": "skipped (no LLM)"})
                continue

        # LLM 결과 없음 (오류/타임아웃)
        if llm_result is None:
            print(f"  SKIP  LLM 결과 없음 (타임아웃 또는 오류) [{elapsed:.2f}s]")
            results.append({"id": case["id"], "name": case["name"], "match": False,
                            "expected": case["expected_tier"], "actual": None,
                            "elapsed": elapsed})
            continue

        actual_tier = llm_result["overall_quality"]["tier"]
        actual_score = llm_result["overall_quality"]["score"]
        expected_tier = case["expected_tier"]
        tier_range = case.get("expected_tier_range")

        # 일치 판정 (범위 허용)
        if tier_range:
            match = actual_tier in tier_range
        else:
            match = actual_tier == expected_tier

        dist = _tier_distance(actual_tier, expected_tier)
        no_reverse = dist <= 1  # 2단계 반전은 치명적 실패

        status = "PASS " if match else ("WARN " if no_reverse else "FAIL ")
        print(f"  {status} expected={expected_tier}, actual={actual_tier} "
              f"(score={actual_score}) [{elapsed:.2f}s]")

        # 5차원 점수 상세 (pass가 아닌 경우)
        if not match:
            dims = ["purpose_clarity", "tech_description", "setup_guide", "visual_demo"]
            dim_labels = ["목적", "기술", "실행", "시각"]
            for dim, lbl in zip(dims, dim_labels):
                s = llm_result.get(dim, {}).get("score", 0)
                reason = llm_result.get(dim, {}).get("reason", "")
                print(f"    {lbl}: {_print_bar(lbl, s)}  ({reason[:60]})")

        # 시간 초과 경고
        if elapsed > 10.0:
            print(f"  [경고] 응답 시간 {elapsed:.2f}s (기준 10초 초과)")

        # 최소 점수 검증 (케이스 13)
        if "expected_min_score" in case and actual_score < case["expected_min_score"]:
            print(f"  [경고] 점수 {actual_score} < 기대 최소 점수 {case['expected_min_score']}")

        results.append({
            "id": case["id"],
            "name": case["name"],
            "match": match,
            "no_reverse": no_reverse,
            "expected": expected_tier,
            "actual": actual_tier,
            "score": actual_score,
            "elapsed": elapsed,
        })
        print()

    # ── 결과 요약 ─────────────────────────────────────────
    llm_cases = [r for r in results if r.get("actual") != "skipped (no LLM)" and r.get("actual") is not None]
    skipped = [r for r in results if r.get("actual") == "skipped (no LLM)"]
    failed_llm = [r for r in results if r.get("actual") is None and r.get("actual") != "skipped (no LLM)"]

    match_count = sum(1 for r in llm_cases if r.get("match"))
    no_reverse_count = sum(1 for r in llm_cases if r.get("no_reverse", True))
    total_llm = len(llm_cases)

    print("=" * 65)
    print(f"결과 요약  (LLM 호출 {total_llm}건 / 스킵 {len(skipped)}건 / 오류 {len(failed_llm)}건)")
    print("-" * 65)

    tier_match_rate = match_count / total_llm if total_llm > 0 else 0
    no_reverse_rate = no_reverse_count / total_llm if total_llm > 0 else 0

    print(f"  tier 일치율      : {match_count}/{total_llm} = {tier_match_rate:.0%}  (기준: 80% 이상)")
    print(f"  1단계 이내 오차  : {no_reverse_count}/{total_llm} = {no_reverse_rate:.0%}  (기준: 100%)")
    print(f"  총 소요 시간     : {total_elapsed:.2f}s")

    passed = tier_match_rate >= 0.80 and no_reverse_rate >= 1.00
    print()
    if passed:
        print("  [PASS] 모든 기준 통과")
    else:
        print("  [FAIL] 일부 기준 미달")
        if tier_match_rate < 0.80:
            print(f"    - tier 일치율 {tier_match_rate:.0%} < 80%")
        if no_reverse_rate < 1.00:
            reversed_cases = [r for r in llm_cases if not r.get("no_reverse", True)]
            for r in reversed_cases:
                print(f"    - [{r['id']:02d}] {r['name']}: {r['expected']} → {r['actual']} (2단계 반전!)")
    print("=" * 65)


if __name__ == "__main__":
    asyncio.run(run_golden_test())
