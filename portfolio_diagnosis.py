"""
Git2Value v5.8 — 포트폴리오 진단 체크리스트 (룰베이스).
v5.4: Unity/Unreal/Godot 감지 시 테스트·CI/CD·배포 피드백을 게임 개발 맥락으로 조정.
v5.5: 기여 유형 안내(contribution_type_note), Competitive 등급 기준 조정, 테스트 항목 문구 완화.
v5.7: 모드/플러그인 플랫폼 맥락 메시지(mod_context_message), 설정 프로젝트 안내(config_repo_message),
      run_diagnosis() 반환에 repo_classifications 추가.
v5.8: 신규 도메인 맥락 메시지 추가 — blockchain_context_message, data_engineer_context_message,
      tool_dev_context_message (블록체인/데이터 엔지니어링/도구 개발 프로젝트 안내).
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


def contribution_type_note(valid_loc: int, evidence_loc: int) -> str:
    """코드 vs 설정·데이터 기여 비율 안내 (v5.5)."""
    total = valid_loc + evidence_loc
    if total == 0:
        return ""
    code_ratio = valid_loc / total
    if code_ratio >= 0.8:
        return (
            f"기여 유형: 소스 코드 중심 (코드 {valid_loc:,} LOC, 설정/데이터 {evidence_loc:,} LOC)"
        )
    if code_ratio >= 0.4:
        return (
            f"기여 유형: 코드·설정 병행 (코드 {valid_loc:,} LOC, 설정/데이터 {evidence_loc:,} LOC)"
        )
    return (
        f"기여 유형: 설정/데이터 중심 (코드 {valid_loc:,} LOC, 설정/데이터 {evidence_loc:,} LOC)\n"
        f"  → 이 레포에서는 데이터·인프라·문서 영역에 주로 기여한 것으로 보입니다. "
        f"순수 코딩 LOC 기반 점수가 낮게 나올 수 있으며, 이는 기여 유형의 차이이지 실력의 문제가 아닙니다."
    )


GAME_ENGINE_LABELS: Set[str] = {"Unity", "Unreal Engine", "Godot"}


def _collect_game_engines(per_repo: List[Dict[str, Any]]) -> Set[str]:
    """per_repo의 frameworks에서 게임 엔진 라벨만 수집."""
    out: Set[str] = set()
    for r in per_repo:
        for fw in r.get("frameworks") or []:
            if fw in GAME_ENGINE_LABELS:
                out.add(fw)
    return out


# ---------------------------------------------------------------------------
# v5.7: 모드/설정 프로젝트 분류 메시지
# ---------------------------------------------------------------------------

def mod_context_message(mod_platform: Dict[str, Any]) -> str:
    """모드/플러그인 플랫폼 프로젝트 안내 메시지."""
    name = mod_platform.get("name", "모드")
    if mod_platform.get("is_hobby"):
        return (
            f"{name} 프로젝트로 분류되었습니다. "
            f"직무 매칭에 활용되나, 채용 시장에서 직접 매칭되는 공고는 적습니다. "
            f"주력 프로젝트로는 게임 엔진 기반 자체 게임 개발을 권장합니다."
        )
    return (
        f"{name} 프로젝트로 분류되었습니다. "
        f"게임 분야에 대한 깊은 이해와 스크립팅 능력을 보여주는 포트폴리오입니다. "
        f"채용 시 게임 클라이언트 공고와 매칭되며, 엔진 기반 자체 게임 프로젝트를 "
        f"함께 보유하면 매칭 정확도가 더 올라갑니다."
    )


def config_repo_message(host_name: str) -> str:
    """설정/취미 프로젝트 안내 메시지."""
    return (
        f"{host_name} 프로젝트로 분류되었습니다. "
        f"에디터/도구 설정은 직무 매칭에 활용되지 않으며, 포트폴리오에서는 보조 역할입니다. "
        f"주력 프로젝트(웹/게임/AI 등)를 추가하시기 바랍니다."
    )


def blockchain_context_message(label: str) -> str:
    """블록체인/Web3 프로젝트 안내 메시지 (v5.8)."""
    return (
        f"{label} 프로젝트로 분류되었습니다. "
        f"스마트 컨트랙트 개발 역량을 보여주는 포트폴리오로, 블록체인 개발자 공고에 매칭됩니다. "
        f"채용 시장에서 블록체인 직군은 규모가 작지만 수요가 꾸준하므로, "
        f"서버/백엔드 역량을 함께 어필하면 범용 취업에 유리합니다."
    )


def data_engineer_context_message(label: str) -> str:
    """데이터 엔지니어링 프로젝트 안내 메시지 (v5.8)."""
    return (
        f"{label} 프로젝트로 분류되었습니다. "
        f"데이터 파이프라인 구축·ETL 역량을 보여주는 포트폴리오로, "
        f"빅데이터 엔지니어 및 데이터 분석 공고에 매칭됩니다. "
        f"순수 코드 LOC는 낮게 나올 수 있으나, 이는 데이터 엔지니어링 기여 특성이며 "
        f"Evidence LOC(YAML·SQL·설정 파일)로 기여도가 반영됩니다."
    )


def tool_dev_context_message(label: str) -> str:
    """도구 개발(VS Code 확장·브라우저 확장) 프로젝트 안내 메시지 (v5.8)."""
    return (
        f"{label} 프로젝트로 분류되었습니다. "
        f"개발자 도구에 대한 깊은 이해와 사용자 인터페이스 설계 능력을 보여줍니다. "
        f"채용 시장에서 직접 매칭되는 전용 공고는 적으나, "
        f"프론트엔드 또는 SW 개발 직무에 차별화 포트폴리오로 활용 가능합니다."
    )


def _build_repo_classifications(per_repo: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    per_repo 각 항목에 대해 분류(main/mod/config)와 안내 메시지를 생성.
    Returns: [{"repo_name", "type", "label", "message", "matching_included"}, ...]
    """
    classifications = []
    for r in per_repo:
        repo_name = r.get("repo_name", "")
        mod_platform = r.get("mod_platform")
        is_config = r.get("is_config_repo", False)
        sub_host = r.get("sub_language_host")
        matching = r.get("matching_included", True)

        if is_config and sub_host:
            host_name = sub_host.get("name") or sub_host.get("label") or "설정"
            classifications.append({
                "repo_name": repo_name,
                "type": "config",
                "label": sub_host.get("label", "설정 프로젝트"),
                "message": config_repo_message(host_name),
                "matching_included": matching,
            })
        elif mod_platform:
            classifications.append({
                "repo_name": repo_name,
                "type": "mod",
                "label": mod_platform.get("label", "모드 개발"),
                "message": mod_context_message(mod_platform),
                "matching_included": matching,
            })
        else:
            # v5.8: 엔진 시그너처 도메인 기반 맥락 메시지 (블록체인/데이터/도구 개발)
            detected_domains = r.get("detected_domains") or []
            frameworks = r.get("frameworks") or []
            special_msg = None
            special_label = None
            blockchain_labels = {"Hardhat (Solidity)", "Foundry (Solidity)"}
            data_eng_labels = {"dbt"}
            tool_dev_labels = {"VS Code 확장", "Browser Extension"}
            if "블록체인" in detected_domains or any(f in blockchain_labels for f in frameworks):
                fw_label = next((f for f in frameworks if f in blockchain_labels), "블록체인")
                special_label = fw_label
                special_msg = blockchain_context_message(fw_label)
            elif "빅데이터 엔지니어" in detected_domains or any(f in data_eng_labels for f in frameworks):
                fw_label = next((f for f in frameworks if f in data_eng_labels), "데이터 엔지니어링")
                special_label = fw_label
                special_msg = data_engineer_context_message(fw_label)
            elif "도구 개발" in detected_domains or any(f in tool_dev_labels for f in frameworks):
                fw_label = next((f for f in frameworks if f in tool_dev_labels), "도구 개발")
                special_label = fw_label
                special_msg = tool_dev_context_message(fw_label)
            classifications.append({
                "repo_name": repo_name,
                "type": "main",
                "label": special_label,
                "message": special_msg,
                "matching_included": matching,
            })
    return classifications


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
        action = (
            "테스트 코드는 Top 등급 차별화 요소입니다. "
            "핵심 비즈니스 로직부터 단위 테스트를 추가해보세요."
        )
        if ge:
            if "Unity" in ge:
                action = (
                    "테스트는 Top 등급 차별화 요소입니다. "
                    "Unity Test Framework 또는 PlayMode 테스트 추가를 검토해 보세요."
                )
            elif "Unreal Engine" in ge:
                action = (
                    "테스트는 Top 등급 차별화 요소입니다. "
                    "Unreal Automation Tests 또는 테스트 러너 추가를 검토해 보세요."
                )
            elif "Godot" in ge:
                action = (
                    "테스트는 Top 등급 차별화 요소입니다. "
                    "GUT 또는 WAT 등 Godot 테스트 도구 추가를 검토해 보세요."
                )
        return _item(
            "선택 가점",
            f"{len(per_repo)}개 레포 중 테스트 파일이 감지되지 않았습니다.",
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
    # v5.5: Competitive — 테스트 조건 제외, CI/CD 또는 배포 + 멀티 프로젝트
    if readme_ok and (has_cicd or has_deploy) and multi_proj and s >= 4:
        return {
            "level": "Competitive",
            "summary": "중견 IT·시리즈 B급 이상 스타트업에 맞설 만한 포트폴리오 완성도로 볼 수 있습니다.",
        }
    return {
        "level": "Entry",
        "summary": (
            "중소·SI·일반 스타트업 지원에 맞는 기본 단계입니다. "
            "CI/CD·배포·멀티 프로젝트를 보강하면 체감이 커집니다."
        ),
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

    ms = profile.get("metrics_summary") or {}
    vl = int(ms.get("total_valid_loc") or 0)
    el = int(ms.get("total_evidence_loc") or 0)

    return {
        "portfolio_diagnosis": diagnosis,
        "expected_level": expected_level(per_repo, diagnosis),
        "contribution_type": contribution_type_note(vl, el),
        "repo_classifications": _build_repo_classifications(per_repo),  # v5.7
    }
