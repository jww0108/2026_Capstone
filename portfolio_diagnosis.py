"""
Git2Value v5.4 — 포트폴리오 진단 체크리스트 (룰베이스).
v5.4: Unity/Unreal/Godot 감지 시 테스트·CI/CD·배포 피드백을 게임 개발 맥락으로 조정.
"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Set

MEANINGLESS_COMMIT_PATTERNS = re.compile(
    r"^("
    r"(fix|update|wip|temp|test|merge|revert|chore|bump)\s*$"
    r"|initial\s+commit\s*$"
    r"|(fix|update|wip|temp|test)\s+[^:\s]"
    r")",
    re.I,
)


def _item(status: str, detail: str, action: Optional[str] = None) -> Dict[str, Any]:
    return {"status": status, "detail": detail, "action": action}


GAME_ENGINE_LABELS: Set[str] = {"Unity", "Unreal Engine", "Godot"}


def _collect_game_engines(per_repo: List[Dict[str, Any]]) -> Set[str]:
    """per_repo의 frameworks에서 게임 엔진 라벨만 수집."""
    out: Set[str] = set()
    for r in per_repo:
        for fw in r.get("frameworks") or []:
            if fw in GAME_ENGINE_LABELS:
                out.add(fw)
    return out


def _readme_diagnosis(per_repo: List[Dict[str, Any]]) -> Dict[str, Any]:
    if not per_repo:
        return _item("미흡", "분석된 레포가 없습니다.", "대표 프로젝트 레포 URL을 추가하세요.")
    long_count = sum(1 for r in per_repo if (r.get("readme_tier") == "long"))
    img_count = sum(1 for r in per_repo if r.get("readme_has_image"))
    avg_len = 0
    n = 0
    for r in per_repo:
        L = len((r.get("readme") or "").strip())
        if L:
            avg_len += L
            n += 1
    avg = (avg_len // n) if n else 0
    if long_count >= max(1, len(per_repo) // 2) and avg >= 200:
        return _item(
            "양호",
            f"평균 약 {avg}자, {img_count}개 레포에 이미지(스크린샷 등) 포함 추정",
            None,
        )
    if avg >= 50:
        return _item(
            "개선 필요",
            f"README가 짧거나 일부 레포만 충실합니다 (평균 약 {avg}자).",
            "프로젝트 목적, 기술 스택, 실행 방법, 데모 GIF/스크린샷을 README에 정리하세요.",
        )
    return _item(
        "미흡",
        "README가 거의 비어 있거나 매우 짧습니다.",
        "채용 담당자가 처음 보는 문서가 README입니다. 구조화된 설명을 추가하세요.",
    )


def _structure_diagnosis(per_repo: List[Dict[str, Any]]) -> Dict[str, Any]:
    if not per_repo:
        return _item("미흡", "레포 데이터 없음", None)
    issues: List[str] = []
    for r in per_repo:
        name = r.get("repo_name", "repo")
        ts = r.get("tree_stats") or {}
        avg_loc = float(ts.get("avg_loc_per_file") or 0)
        if avg_loc > 0 and avg_loc < 20:
            issues.append(f"{name}: 파일당 평균 LOC {avg_loc} (파편화 의심)")
        elif avg_loc > 300:
            issues.append(f"{name}: 파일당 평균 LOC {avg_loc} (모놀리식 의심)")
        if not ts.get("has_gitignore"):
            issues.append(f"{name}: .gitignore 없음")
    if not issues:
        return _item(
            "양호",
            "디렉터리 구성과 .gitignore 존재 여부가 대체로 적절합니다.",
            None,
        )
    return _item(
        "개선 필요",
        "; ".join(issues[:4]) + (" …" if len(issues) > 4 else ""),
        "모듈 단위로 파일을 나누고, 불필요한 산출물은 .gitignore로 제외하세요.",
    )


def _test_diagnosis(
    per_repo: List[Dict[str, Any]],
    game_engines: Optional[Set[str]] = None,
) -> Dict[str, Any]:
    if not per_repo:
        return _item("미흡", "레포 데이터 없음", None)
    ge = game_engines or set()
    with_tests = sum(1 for r in per_repo if r.get("has_tests"))
    if with_tests == 0:
        action = "주력 프로젝트에 pytest/Jest 등 테스트를 추가하면 신뢰도가 올라갑니다."
        if ge:
            if "Unity" in ge:
                action = "Unity Test Framework 또는 PlayMode 테스트 추가를 권장합니다."
            elif "Unreal Engine" in ge:
                action = "Unreal Automation Tests 또는 테스트 러너 추가를 권장합니다."
            elif "Godot" in ge:
                action = "GUT 또는 WAT 등 Godot 테스트 도구 추가를 권장합니다."
        return _item(
            "미흡",
            f"{len(per_repo)}개 레포 중 테스트 파일 비율이 낮거나 감지되지 않았습니다.",
            action,
        )
    if with_tests >= len(per_repo) // 2 or with_tests >= 2:
        return _item("양호", f"{with_tests}개 레포에서 테스트 코드 신호가 감지되었습니다.", None)
    return _item(
        "개선 필요",
        f"일부 레포({with_tests}개)만 테스트 신호가 있습니다.",
        "핵심 비즈니스 로직에 단위 테스트를 우선 추가하세요.",
    )


def _cicd_diagnosis(
    per_repo: List[Dict[str, Any]],
    game_engines: Optional[Set[str]] = None,
) -> Dict[str, Any]:
    ge = game_engines or set()
    n = sum(1 for r in per_repo if r.get("has_cicd"))
    if n == 0:
        action = "간단한 lint/test 워크플로우라도 추가해 보세요."
        if ge:
            if "Unity" in ge:
                action = "Unity Cloud Build 또는 GameCI GitHub Action을 검토해보세요."
            elif "Unreal Engine" in ge:
                action = "UBT·빌드 그래프 기반 CI 또는 팀 표준 빌드 파이프라인을 검토해보세요."
            elif "Godot" in ge:
                action = "Godot export·헤드리스 빌드를 자동화하는 CI 스크립트를 검토해보세요."
        return _item(
            "미경험",
            "GitHub Actions 또는 실질적인 Dockerfile 기반 CI/CD가 감지되지 않았습니다.",
            action,
        )
    return _item("양호", f"CI/CD 신호가 {n}개 레포에서 감지되었습니다.", None)


def _commit_quality_diagnosis(per_repo: List[Dict[str, Any]]) -> Dict[str, Any]:
    msgs: List[str] = []
    for r in per_repo:
        msgs.extend(r.get("commit_messages") or [])
    if not msgs:
        return _item(
            "알 수 없음",
            "커밋 메시지 샘플이 없습니다.",
            "의미 있는 커밋 메시지로 변경 이력을 남기세요.",
        )
    bad = sum(1 for m in msgs if MEANINGLESS_COMMIT_PATTERNS.search(m.strip()))
    ratio = bad / len(msgs)
    if ratio >= 0.35:
        return _item(
            "개선 필요",
            f"샘플 커밋 중 약 {int(ratio * 100)}%가 fix/update 등 다소 무의미한 메시지입니다.",
            "Conventional Commits(feat:, fix:, refactor:) 형식을 권장합니다.",
        )
    if ratio >= 0.15:
        return _item(
            "보통",
            "일부 커밋 메시지가 추상적입니다.",
            "변경 의도가 드러나도록 한 줄 설명을 덧붙이세요.",
        )
    return _item("양호", "커밋 메시지가 비교적 구체적으로 보입니다.", None)


def _commit_pattern_diagnosis(per_repo: List[Dict[str, Any]]) -> Dict[str, Any]:
    """활성 주·커밋 수 기반 커밋 리듬(Scoring_Review 권고: 진단 항목)."""
    if not per_repo:
        return _item("알 수 없음", "레포 데이터가 없습니다.", None)
    total_weeks = sum(int(r.get("active_weeks") or 0) for r in per_repo)
    total_commits = sum(int(r.get("total_commits") or 0) for r in per_repo)
    if total_weeks <= 0:
        return _item(
            "알 수 없음",
            "커밋이 있는 ISO 주를 산출할 수 없습니다.",
            None,
        )
    avg_per_week = round(total_commits / total_weeks, 1)
    if avg_per_week >= 5.0:
        return _item(
            "규칙적",
            f"수집된 커밋 목록 기준, 활성 주당 평균 약 {avg_per_week}회 커밋으로 보입니다.",
            None,
        )
    if avg_per_week >= 2.0:
        return _item(
            "보통",
            f"활성 주당 평균 약 {avg_per_week}회 커밋입니다.",
            "가능하면 작은 단위로 자주 커밋해 변경 이력을 남기면 좋습니다.",
        )
    return _item(
        "불규칙",
        f"활성 주당 평균 약 {avg_per_week}회 커밋으로, 간헐적 패턴에 가깝습니다.",
        "스프린트 몰아쓰기보다 꾸준한 소량 커밋이 협업·리뷰에 유리합니다.",
    )


def _deployment_diagnosis(
    per_repo: List[Dict[str, Any]],
    game_engines: Optional[Set[str]] = None,
) -> Dict[str, Any]:
    ge = game_engines or set()
    n = sum(1 for r in per_repo if r.get("has_deployment"))
    if n == 0:
        action = "배포 경험은 실무 역량 어필에 도움이 됩니다."
        if ge:
            if "Unity" in ge or "Unreal Engine" in ge:
                action = "빌드 결과물(APK/EXE) 또는 itch.io 배포 경험을 README에 명시하세요."
            elif "Godot" in ge:
                action = "내보내기 빌드(HTML5·데스크톱 등) 또는 스토어 배포 경험을 README에 명시하세요."
        return _item(
            "미경험",
            "배포 관련 설정(docker-compose, Vercel 등)이 감지되지 않았습니다.",
            action,
        )
    return _item("양호", f"{n}개 레포에서 배포/인프라 관련 파일이 감지되었습니다.", None)


def _collaboration_diagnosis(per_repo: List[Dict[str, Any]]) -> Dict[str, Any]:
    multi = [r for r in per_repo if int(r.get("distinct_author_count") or 1) >= 2 and not r.get("is_fork")]
    if multi:
        return _item(
            "양호",
            f"{len(multi)}개 레포에서 다수 기여자(협업) 패턴이 보입니다.",
            None,
        )
    return _item(
        "보통",
        "단일 작성자 커밋 패턴이 주를 이룹니다.",
        "팀 프로젝트, PR 리뷰, 이슈 트래킹 경험을 README에 명시하면 좋습니다.",
    )


def _growth_diagnosis(per_repo: List[Dict[str, Any]]) -> Dict[str, Any]:
    """초기 vs 최근 커밋 메시지 길이(샘플 기반) 휴리스틱."""
    lens_early: List[int] = []
    lens_late: List[int] = []
    for r in per_repo:
        msgs = r.get("commit_messages") or []
        if len(msgs) < 4:
            continue
        early = msgs[: max(1, len(msgs) // 3)]
        late = msgs[-max(1, len(msgs) // 3) :]
        lens_early.extend(len(m) for m in early)
        lens_late.extend(len(m) for m in late)
    if not lens_early or not lens_late:
        return _item(
            "알 수 없음",
            "성장 궤적을 판단할 커밋 샘플이 부족합니다.",
            None,
        )
    a_e = sum(lens_early) / len(lens_early)
    a_l = sum(lens_late) / len(lens_late)
    if a_l >= a_e * 1.15:
        return _item(
            "양호",
            f"최근 커밋 메시지가 초기 대비 평균 길이가 약 {a_l / max(a_e, 1):.2f}배로 개선된 흐름이 보입니다.",
            None,
        )
    if a_l < a_e * 0.85:
        return _item(
            "개선 필요",
            "최근 커밋 설명이 초기보다 짧아지는 경향이 있습니다.",
            "리팩터링·이슈 링크 등 맥락을 남기도록 습관을 들이세요.",
        )
    return _item("보통", "초기·최근 커밋 메시지 길이에 큰 변화가 없습니다.", None)


def _count_checks(per_repo: List[Dict[str, Any]], diagnosis: Dict[str, Dict[str, Any]]) -> int:
    """Entry/Competitive/Top 룰용 충족 개수."""
    score = 0
    if diagnosis["readme_quality"]["status"] in ("양호", "보통"):
        score += 1
    if diagnosis["project_structure"]["status"] == "양호":
        score += 1
    if diagnosis["test_coverage"]["status"] == "양호":
        score += 1
    if diagnosis["cicd"]["status"] == "양호":
        score += 1
    if diagnosis["deployment"]["status"] == "양호":
        score += 1
    if diagnosis["commit_quality"]["status"] in ("양호", "보통"):
        score += 1
    if len(per_repo) >= 2:
        score += 1
    return score


def expected_level(per_repo: List[Dict[str, Any]], diagnosis: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
    s = _count_checks(per_repo, diagnosis)
    readme_ok = diagnosis["readme_quality"]["status"] in ("양호", "보통")
    has_tests = diagnosis["test_coverage"]["status"] == "양호"
    has_cicd = diagnosis["cicd"]["status"] == "양호"
    has_deploy = diagnosis["deployment"]["status"] == "양호"
    multi_proj = len(per_repo) >= 2

    if readme_ok and multi_proj and has_tests and has_cicd and has_deploy and s >= 6:
        return {
            "level": "Top",
            "summary": "대형 테크·우수 스타트업 서류에서 경쟁력을 기대할 수 있는 완성도(참고 기준)입니다.",
        }
    if readme_ok and (has_tests or has_cicd) and s >= 4:
        return {
            "level": "Competitive",
            "summary": "중견 IT·시리즈 B급 이상 스타트업에 맞설 만한 포트폴리오 완성도로 볼 수 있습니다.",
        }
    return {
        "level": "Entry",
        "summary": "중소·SI·일반 스타트업 지원에 맞는 기본 단계입니다. 테스트·CI/CD·배포를 보강하면 체감이 커집니다.",
    }


def run_diagnosis(profile: Dict[str, Any]) -> Dict[str, Any]:
    """
    extract_applicant_profile() 반환 프로필을 입력으로 진단 JSON을 생성합니다.
    """
    per_repo: List[Dict[str, Any]] = list(profile.get("per_repo") or [])
    game_engines = _collect_game_engines(per_repo)

    diagnosis = {
        "readme_quality": _readme_diagnosis(per_repo),
        "project_structure": _structure_diagnosis(per_repo),
        "test_coverage": _test_diagnosis(per_repo, game_engines),
        "cicd": _cicd_diagnosis(per_repo, game_engines),
        "commit_quality": _commit_quality_diagnosis(per_repo),
        "commit_pattern": _commit_pattern_diagnosis(per_repo),
        "deployment": _deployment_diagnosis(per_repo, game_engines),
        "collaboration": _collaboration_diagnosis(per_repo),
        "growth_trajectory": _growth_diagnosis(per_repo),
    }

    return {
        "portfolio_diagnosis": diagnosis,
        "expected_level": expected_level(per_repo, diagnosis),
    }
