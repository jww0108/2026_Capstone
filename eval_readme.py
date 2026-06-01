"""
단일 README LLM 채점 스크립트.

사용법:
    # 로컬 파일
    python eval_readme.py path/to/README.md

    # GitHub raw URL
    python eval_readme.py https://raw.githubusercontent.com/user/repo/main/README.md

    # meta 정보 직접 지정 (선택)
    python eval_readme.py README.md --domain 서버/백엔드 --langs "Python 80,TypeScript 20" --sigs "FastAPI,Docker" --repo-type team
"""
from __future__ import annotations

import argparse
import asyncio
import sys
import urllib.request
from typing import Any, Dict, List

from llm_readme_evaluator import ReadmeEvaluator

REASON_WRAP_WIDTH = 120


def _parse_langs(raw: str) -> Dict[str, int]:
    """'Python 80,TypeScript 20' → {"Python": 80, "TypeScript": 20}"""
    result: Dict[str, int] = {}
    if not raw:
        return result
    for part in raw.split(","):
        part = part.strip()
        tokens = part.rsplit(" ", 1)
        if len(tokens) == 2:
            try:
                result[tokens[0].strip()] = int(tokens[1])
            except ValueError:
                result[tokens[0].strip()] = 0
        elif tokens:
            result[tokens[0].strip()] = 0
    return result


def _load_readme(source: str) -> str:
    if source.startswith("http://") or source.startswith("https://"):
        try:
            with urllib.request.urlopen(source, timeout=10) as resp:
                return resp.read().decode("utf-8")
        except Exception as e:
            print(f"[오류] URL에서 README를 가져올 수 없습니다: {e}")
            sys.exit(1)
    else:
        try:
            with open(source, encoding="utf-8") as f:
                return f.read()
        except FileNotFoundError:
            print(f"[오류] 파일을 찾을 수 없습니다: {source}")
            sys.exit(1)


def _wrap_text(text: str, width: int = REASON_WRAP_WIDTH) -> List[str]:
    """긴 텍스트를 width자 단위 줄로 분할한다."""
    if not text:
        return []
    return [text[i : i + width] for i in range(0, len(text), width)]


def _bar(score: int) -> str:
    return "█" * score + "░" * (5 - score)


def _print_result(result: Dict[str, Any]) -> None:
    oq = result["overall_quality"]
    tier_icon = {"양호": "🟢", "보통": "🟡", "미흡": "🔴"}.get(oq["tier"], "⚪")

    print()
    print("=" * 60)
    print(f"  종합 평가: {tier_icon} {oq['tier']}  (score {oq['score']}/5)")
    print(f"  {oq['summary']}")
    print("-" * 60)

    dim_labels = [
        ("purpose_clarity", "목적 명확성"),
        ("tech_description", "기술 설명 "),
        ("setup_guide",      "실행 가이드"),
        ("visual_demo",      "시각 자료 "),
    ]
    for key, label in dim_labels:
        d = result.get(key, {})
        sc = d.get("score", 0)
        reason = d.get("reason", "")
        print(f"  {label}: {_bar(sc)} {sc}/5")
        if reason:
            print(f"            {reason}")

    print("-" * 60)
    print("  💡 개선 제안:")
    for suggestion in result.get("improvement_suggestions", []):
        print(f"    • {suggestion}")
    print("=" * 60)
    print()


async def main(args: argparse.Namespace) -> None:
    readme = _load_readme(args.source)

    meta: Dict[str, Any] = {
        "languages": _parse_langs(args.langs),
        "domain": args.domain,
        "signatures": [s.strip() for s in args.sigs.split(",") if s.strip()] if args.sigs else [],
        "repo_type": args.repo_type,
    }

    print(f"\n[정보] README 로드 완료 ({len(readme)} chars)")
    print(f"[정보] meta: domain={meta['domain']}, repo_type={meta['repo_type']}")
    if meta["languages"]:
        print(f"[정보]        languages={meta['languages']}")
    if meta["signatures"]:
        print(f"[정보]        signatures={meta['signatures']}")

    ev = ReadmeEvaluator()
    print("\n[정보] vLLM 서버 확인 중...")
    if not await ev.health_check():
        print("[오류] vLLM 서버에 연결할 수 없습니다.")
        print("  → 서버를 먼저 실행하세요:")
        print("    vllm serve Qwen/Qwen2.5-32B-Instruct-AWQ --gpu-memory-utilization 0.85 --max-model-len 4096")
        sys.exit(1)

    print("[정보] LLM 평가 중... (수 초 소요)\n")
    result = await ev.evaluate(readme, meta)

    if result is None:
        print("[실패] LLM 평가 결과를 가져오지 못했습니다.")
        print("  → README가 50자 미만이거나 서버 오류입니다.")
        sys.exit(1)

    _print_result(result)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="단일 README를 LLM으로 채점합니다.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "source",
        help="README 파일 경로 또는 GitHub raw URL",
    )
    parser.add_argument(
        "--domain",
        default="Unknown",
        help="프로젝트 도메인 (예: 서버/백엔드, 프론트엔드, 인공지능/머신러닝)",
    )
    parser.add_argument(
        "--langs",
        default="",
        help="언어 비중 (예: \"Python 80,TypeScript 20\")",
    )
    parser.add_argument(
        "--sigs",
        default="",
        help="주요 프레임워크/라이브러리 (예: \"FastAPI,Docker,React\")",
    )
    parser.add_argument(
        "--repo-type",
        default="personal",
        choices=["personal", "team"],
        help="레포지토리 유형 (personal 또는 team, 기본값: personal)",
    )

    asyncio.run(main(parser.parse_args()))
