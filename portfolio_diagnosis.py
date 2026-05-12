"""
Git2Value v6.1 — 포트폴리오 진단 체크리스트 (룰베이스).
v5.4: Unity/Unreal/Godot 감지 시 테스트·CI/CD·배포 피드백을 게임 개발 맥락으로 조정.
v5.5: 기여 유형 안내(contribution_type_note), Competitive 등급 기준 조정, 테스트 항목 문구 완화.
v5.7: 모드/플러그인 플랫폼 맥락 메시지(mod_context_message), 설정 프로젝트 안내(config_repo_message),
      run_diagnosis() 반환에 repo_classifications 추가.
v5.8: 신규 도메인 맥락 메시지 추가 — blockchain/data_engineer/tool_dev context messages.
v6.0: 진단 항목 9→7 (commit_pattern·growth_trajectory·collaboration 제거). README 룰베이스 강화.
      COMMIT_REWRITE_HINTS + get_rewrite_hint(). generate_summary_block() 종합 분석 추가.
v6.1: 레포별 카드 진단으로 전환. classify_repo_type(), diagnose_single_repo() 도입.
      개인 레포: 테스트·CI/CD·배포·커밋 리듬을 가산점 항목으로 한 줄 안내.
      팀 레포: 4개 항목 모두 필수 점검 항목.
      generate_summary_block()에 GitHub 점수 분해, 레포 구성 요약 추가.
"""
from __future__ import annotations

import re
from collections import Counter
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
    out: Set[str] = set()
    for r in per_repo:
        for fw in r.get("frameworks") or []:
            if fw in GAME_ENGINE_LABELS:
                out.add(fw)
    return out


def _repo_game_engines(repo: Dict[str, Any]) -> Set[str]:
    return {fw for fw in (repo.get("frameworks") or []) if fw in GAME_ENGINE_LABELS}


# ---------------------------------------------------------------------------
# v6.1: 개인/팀 레포 분류
# ---------------------------------------------------------------------------

def classify_repo_type(repo: Dict[str, Any]) -> str:
    """
    레포를 'personal' / 'team'으로 분류.

    핵심 원칙:
    - fork 여부는 소유/복제 상태일 뿐, 개인/팀 판정 기준이 아니다.
    - author=username 커밋이 아니라 레포 전체 커밋 작성자 수를 기준으로 한다.
    - github_extractor가 repo_type을 내려주면 그 값을 우선 사용한다.
    """
    explicit = repo.get("repo_type")
    if explicit in {"personal", "team"}:
        return explicit
    distinct = int(repo.get("distinct_author_count") or 1)
    return "team" if distinct >= 2 else "personal"


# ---------------------------------------------------------------------------
# v5.7: 모드/설정 프로젝트 분류 메시지
# ---------------------------------------------------------------------------

def mod_context_message(mod_platform: Dict[str, Any]) -> str:
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
    return (
        f"{host_name} 프로젝트로 분류되었습니다. "
        f"에디터/도구 설정은 직무 매칭에 활용되지 않으며, 포트폴리오에서는 보조 역할입니다. "
        f"주력 프로젝트(웹/게임/AI 등)를 추가하시기 바랍니다."
    )


def blockchain_context_message(label: str) -> str:
    return (
        f"{label} 프로젝트로 분류되었습니다. "
        f"스마트 컨트랙트 개발 역량을 보여주는 포트폴리오로, 블록체인 개발자 공고에 매칭됩니다. "
        f"채용 시장에서 블록체인 직군은 규모가 작지만 수요가 꾸준하므로, "
        f"서버/백엔드 역량을 함께 어필하면 범용 취업에 유리합니다."
    )


def data_engineer_context_message(label: str) -> str:
    return (
        f"{label} 프로젝트로 분류되었습니다. "
        f"데이터 파이프라인 구축·ETL 역량을 보여주는 포트폴리오로, "
        f"빅데이터 엔지니어 및 데이터 분석 공고에 매칭됩니다. "
        f"순수 코드 LOC는 낮게 나올 수 있으나, 이는 데이터 엔지니어링 기여 특성이며 "
        f"Evidence LOC(YAML·SQL·설정 파일)로 기여도가 반영됩니다."
    )


def tool_dev_context_message(label: str) -> str:
    return (
        f"{label} 프로젝트로 분류되었습니다. "
        f"개발자 도구에 대한 깊은 이해와 사용자 인터페이스 설계 능력을 보여줍니다. "
        f"채용 시장에서 직접 매칭되는 전용 공고는 적으나, "
        f"프론트엔드 또는 SW 개발 직무에 차별화 포트폴리오로 활용 가능합니다."
    )


def repo_classification_note(repo: Dict[str, Any]) -> str:
    distinct = int(repo.get("distinct_author_count") or 1)
    repo_name = repo.get("repo_name", "레포")
    if distinct >= 2:
        return f"{repo_name}: {distinct}명이 함께 작업한 팀 프로젝트"
    return f"{repo_name}: 단독 작업 레포"


def _build_repo_classifications(per_repo: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    classifications = []
    for r in per_repo:
        repo_name = r.get("repo_name", "")
        mod_platform = r.get("mod_platform")
        is_config = r.get("is_config_repo", False)
        sub_host = r.get("sub_language_host")
        matching = r.get("matching_included", True)

        collab_note = repo_classification_note(r)
        if is_config and sub_host:
            host_name = sub_host.get("name") or sub_host.get("label") or "설정"
            classifications.append({
                "repo_name": repo_name,
                "type": "config",
                "label": sub_host.get("label", "설정 프로젝트"),
                "message": config_repo_message(host_name),
                "matching_included": matching,
                "collab_note": collab_note,
            })
        elif mod_platform:
            classifications.append({
                "repo_name": repo_name,
                "type": "mod",
                "label": mod_platform.get("label", "모드 개발"),
                "message": mod_context_message(mod_platform),
                "matching_included": matching,
                "collab_note": collab_note,
            })
        else:
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
                "collab_note": collab_note,
            })
    return classifications


# ---------------------------------------------------------------------------
# v6.0: README 룰베이스 3차원 평가
# ---------------------------------------------------------------------------

README_QUALITY_INDICATORS: Dict[str, List[str]] = {
    "프로젝트 목적 명시": [
        r"^#\s*[가-힣\w].{5,}",
        r"##\s*(소개|introduction|overview|개요)",
        r"##\s*(프로젝트\s*목적|purpose|goal)",
    ],
    "기술 스택 설명": [
        r"##\s*(기술\s*스택|tech\s*stack|technologies|사용\s*기술|stack)",
        r"\|\s*(언어|language|framework|기술)\s*\|",
    ],
    "결과물 시각화": [
        r"!\[.*?\]\(.*?\)",
        r"<img\s+src=",
        r"https?://[^\s)]+\.(gif|png|jpg|jpeg|mp4|webm)",
    ],
}


def evaluate_readme_quality(readme_text: str) -> Dict[str, Any]:
    indicators: Dict[str, bool] = {}
    for name, patterns in README_QUALITY_INDICATORS.items():
        found = any(re.search(p, readme_text, re.I | re.M) for p in patterns)
        indicators[name] = found
    found_count = sum(indicators.values())
    if found_count >= 2:
        return {"status": "양호", "indicators": indicators, "found_count": found_count}
    if found_count == 1:
        return {"status": "보통", "indicators": indicators, "found_count": found_count}
    return {"status": "미흡", "indicators": indicators, "found_count": found_count}


# ---------------------------------------------------------------------------
# v6.1: 레포별 단건 진단 함수들 (per-repo)
# ---------------------------------------------------------------------------

def _readme_diagnosis_single(repo: Dict[str, Any]) -> Dict[str, Any]:
    # v6.3: 품질 평가는 원본 기준, 길이 판단은 정제본 기준
    readme_raw = (repo.get("readme_raw") or repo.get("readme") or "").strip()
    readme_clean = (repo.get("readme") or "").strip()
    has_image = bool(repo.get("readme_has_image"))
    n = len(readme_clean)   # 길이: 정제본 (보일러플레이트 제외 후 실질 내용)

    if n < 50:
        return _item(
            "미흡",
            "README가 거의 비어 있거나 매우 짧습니다.",
            "채용 담당자가 처음 보는 문서가 README입니다. 구조화된 설명을 추가하세요.",
        )

    quality = evaluate_readme_quality(readme_raw)       # v6.3: 원본으로 평가
    missing_dims = [k for k, v in quality["indicators"].items() if not v]
    missing_hint = f" (부족: {', '.join(missing_dims)})" if missing_dims else ""

    if n >= 200:
        if quality["status"] == "양호":
            img_hint = " · 이미지 포함" if has_image else ""
            return _item(
                "양호",
                f"길이 {n:,}자{img_hint}. 목적·기술스택·시각화 항목이 충실합니다.",
                None,
            )
        return _item(
            "개선 필요",
            f"길이는 충분({n:,}자)하지만 구성이 아쉽습니다{missing_hint}.",
            f"README에 {', '.join(missing_dims) if missing_dims else '목적·기술 스택·스크린샷'}을 추가하면 완성도가 높아집니다.",
        )

    return _item(
        "개선 필요",
        f"README가 짧습니다 ({n:,}자){missing_hint}.",
        "프로젝트 목적, 기술 스택, 실행 방법, 데모 GIF/스크린샷을 README에 정리하세요.",
    )


def _structure_diagnosis_single(repo: Dict[str, Any]) -> Dict[str, Any]:
    ts = repo.get("tree_stats") or {}
    avg_loc = float(ts.get("avg_loc_per_file") or 0)
    has_gitignore = bool(ts.get("has_gitignore"))

    issues: List[str] = []
    if avg_loc > 0 and avg_loc < 20:
        issues.append(f"파일당 평균 LOC {avg_loc} (파편화 의심)")
    elif avg_loc > 300:
        issues.append(f"파일당 평균 LOC {avg_loc} (모놀리식 의심)")
    if not has_gitignore:
        issues.append(".gitignore 없음")

    if not issues:
        return _item(
            "양호",
            "디렉터리 구성과 .gitignore 존재 여부가 적절합니다.",
            None,
        )
    return _item(
        "개선 필요",
        "; ".join(issues),
        "모듈 단위로 파일을 나누고, 불필요한 산출물은 .gitignore로 제외하세요.",
    )


COMMIT_REWRITE_HINTS: Dict[str, str] = {
    r"^fix\s*$":               "fix: [무엇을] 수정",
    r"^update\s*$":            "refactor: [무엇을] 개선",
    r"^wip\s*$":               "feat: [기능명] 구현 중",
    r"^temp\s*$":              "wip: [작업명] 임시 저장",
    r"^test\s*$":              "test: [대상] 단위 테스트 추가",
    r"^initial\s+commit\s*$":  "chore: 프로젝트 초기 설정",
    r"^merge.*":               "merge: [브랜치명] 병합",
    r"^chore\s*$":             "chore: [작업] 정리",
    r"^bump\s*$":              "chore: 버전 업데이트",
    r"^revert\s*$":            "revert: [대상] 되돌리기",
}


def get_rewrite_hint(msg: str) -> str:
    for pattern, hint in COMMIT_REWRITE_HINTS.items():
        if re.search(pattern, msg.strip(), re.I):
            return hint
    return "feat/fix/refactor: 변경 내용 구체적으로 기술"


def _commit_quality_diagnosis_single(repo: Dict[str, Any]) -> Dict[str, Any]:
    msgs = repo.get("commit_messages") or []
    if not msgs:
        return _item(
            "알 수 없음",
            "커밋 메시지 샘플이 없습니다.",
            None,
        )
    bad = sum(1 for m in msgs if MEANINGLESS_COMMIT_PATTERNS.search(m.strip()))
    ratio = bad / len(msgs)
    if ratio >= 0.35:
        bad_samples = [m for m in msgs if MEANINGLESS_COMMIT_PATTERNS.search(m.strip())][:1]
        hint = get_rewrite_hint(bad_samples[0]) if bad_samples else "feat/fix/refactor: 변경 내용 구체적으로 기술"
        example = f"\n      예) '{bad_samples[0]}' → 권장: '{hint}'" if bad_samples else ""
        return _item(
            "개선 필요",
            f"샘플 커밋 중 약 {int(ratio * 100)}%가 무의미한 메시지입니다.{example}",
            "기존 커밋은 그대로 두고, Conventional Commits(feat:, fix:, refactor:) 형식을 적용해 보세요.",
        )
    if ratio >= 0.15:
        return _item(
            "보통",
            "일부 커밋 메시지가 추상적입니다.",
            "변경 의도가 드러나도록 한 줄 설명을 덧붙이세요.",
        )
    return _item("양호", "커밋 메시지가 비교적 구체적으로 보입니다.", None)


def _test_diagnosis_single(repo: Dict[str, Any], game_engines: Set[str]) -> Dict[str, Any]:
    has_tests = bool(repo.get("has_tests"))
    test_ratio = float(repo.get("test_ratio") or 0)
    if has_tests:
        return _item(
            "양호",
            f"테스트 파일이 감지되었습니다 (소스 대비 약 {int(test_ratio * 100)}%).",
            None,
        )
    action = "핵심 비즈니스 로직부터 단위 테스트를 추가하면 차별화 요소가 됩니다."
    if game_engines:
        if "Unity" in game_engines:
            action = "Unity Test Framework 또는 PlayMode 테스트 추가를 검토해 보세요."
        elif "Unreal Engine" in game_engines:
            action = "Unreal Automation Tests 또는 테스트 러너 추가를 검토해 보세요."
        elif "Godot" in game_engines:
            action = "GUT 또는 WAT 등 Godot 테스트 도구 추가를 검토해 보세요."
    return _item(
        "없음",
        "테스트 파일이 감지되지 않았습니다.",
        action,
    )


def _cicd_diagnosis_single(repo: Dict[str, Any], game_engines: Set[str]) -> Dict[str, Any]:
    has_cicd = bool(repo.get("has_cicd"))
    if has_cicd:
        return _item("양호", "CI/CD 신호(GitHub Actions 또는 Dockerfile)가 감지되었습니다.", None)
    action = "간단한 lint/test 워크플로우라도 추가해 보세요."
    if game_engines:
        if "Unity" in game_engines:
            action = "Unity Cloud Build 또는 GameCI GitHub Action을 검토해보세요."
        elif "Unreal Engine" in game_engines:
            action = "UBT·빌드 그래프 기반 CI 또는 팀 표준 빌드 파이프라인을 검토해보세요."
        elif "Godot" in game_engines:
            action = "Godot export·헤드리스 빌드를 자동화하는 CI 스크립트를 검토해보세요."
    return _item("없음", "GitHub Actions 또는 실질적인 Dockerfile 기반 CI/CD가 감지되지 않았습니다.", action)


def _deployment_diagnosis_single(repo: Dict[str, Any], game_engines: Set[str]) -> Dict[str, Any]:
    has_deploy = bool(repo.get("has_deployment"))
    if has_deploy:
        return _item("양호", "배포/인프라 관련 파일이 감지되었습니다.", None)
    action = "Vercel, Netlify, Railway 등 간단한 배포부터 시도해 보세요."
    if game_engines:
        if "Unity" in game_engines or "Unreal Engine" in game_engines:
            action = "빌드 결과물(APK/EXE) 또는 itch.io 배포 경험을 README에 명시하세요."
        elif "Godot" in game_engines:
            action = "내보내기 빌드(HTML5·데스크톱 등) 또는 스토어 배포 경험을 README에 명시하세요."
    return _item("없음", "배포 관련 설정(docker-compose, Vercel 등)이 감지되지 않았습니다.", action)


def _commit_pattern_diagnosis_single(repo: Dict[str, Any]) -> Dict[str, Any]:
    """지원자 본인의 커밋 리듬을 평가한다.

    팀 레포에서도 레포 전체 커밋 수가 아니라, 입력받은 GitHub 사용자명의
    커밋 수/활성 주 기준으로 산출한다. 개인 레포에서는 참고 항목으로만 쓰이고,
    팀 레포에서는 필수 점검 항목으로 승격된다.
    """
    active_weeks = int(repo.get("active_weeks") or 0)
    target_commits = int(repo.get("target_commit_count") or repo.get("total_commits") or 0)

    if active_weeks <= 0 or target_commits == 0:
        return _item("알 수 없음", "지원자 기준 커밋 활성 주를 산출할 수 없습니다.", None)

    avg = round(target_commits / active_weeks, 1)
    if avg >= 5.0:
        return _item("규칙적", f"지원자 기준 활성 주당 평균 약 {avg}회 — 꾸준한 커밋 패턴입니다.", None)
    if avg >= 2.0:
        return _item("보통", f"지원자 기준 활성 주당 평균 약 {avg}회 — 큰 단위 커밋 위주입니다.", None)
    return _item(
        "불규칙",
        f"지원자 기준 활성 주당 평균 약 {avg}회 — 간헐적 패턴입니다.",
        "팀 협업에서는 작은 단위로 자주 커밋하는 편이 리뷰·통합에 유리합니다.",
    )


def _team_required_items(extra_items: Dict[str, Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    """팀 레포에서는 4개 운영/협업 항목을 필수 점검 항목으로 승격한다."""
    out: Dict[str, Dict[str, Any]] = {}
    for key, item in extra_items.items():
        item = dict(item)
        status = item.get("status")
        if key in {"test_coverage", "cicd", "deployment"} and status in {"없음", "미흡", "미경험", "선택 가점"}:
            item["status"] = "필수 미흡"
        elif key == "commit_pattern":
            if status == "불규칙":
                item["status"] = "개선 필요"
            elif status == "알 수 없음":
                item["status"] = "확인 필요"
        out[key] = item
    return out


def diagnose_single_repo(repo: Dict[str, Any]) -> Dict[str, Any]:
    """
    레포 1개에 대한 진단 결과.
    - core_items 3개는 개인/팀 공통 평가
    - extra_items 4개는 팀 레포에서 필수 점검, 개인 레포에서는 참고 항목
    """
    game_engines = _repo_game_engines(repo)
    repo_type = classify_repo_type(repo)
    distinct = int(repo.get("distinct_author_count") or 1)

    context_label = None
    if game_engines:
        context_label = " / ".join(sorted(game_engines))
    elif repo.get("frameworks"):
        fw_top = (repo.get("frameworks") or [])[:2]
        if fw_top:
            context_label = " / ".join(fw_top)

    extra_items = {
        "test_coverage": _test_diagnosis_single(repo, game_engines),
        "cicd": _cicd_diagnosis_single(repo, game_engines),
        "deployment": _deployment_diagnosis_single(repo, game_engines),
        "commit_pattern": _commit_pattern_diagnosis_single(repo),
    }
    if repo_type == "team":
        extra_items = _team_required_items(extra_items)

    return {
        "repo_name": repo.get("repo_name", "repo"),
        "repo_type": repo_type,
        "distinct_author_count": distinct,
        "repo_author_names": repo.get("repo_author_names") or [],
        "target_commit_count": int(repo.get("target_commit_count") or repo.get("total_commits") or 0),
        "total_repo_commits": int(repo.get("total_repo_commits") or repo.get("total_commits") or 0),
        "target_commit_ratio": float(repo.get("target_commit_ratio") or 0.0),
        "is_fork": bool(repo.get("is_fork")),
        "context_label": context_label,
        # v6.2: 활동 기간 비율 표시용 필드
        "active_weeks": int(repo.get("active_weeks") or 0),
        "repo_active_weeks": int(repo.get("repo_active_weeks") or 0),
        "core_items": {
            "readme_quality": _readme_diagnosis_single(repo),
            "project_structure": _structure_diagnosis_single(repo),
            "commit_quality": _commit_quality_diagnosis_single(repo),
        },
        "extra_items": extra_items,
    }


# ---------------------------------------------------------------------------
# 등급 판정 (전체 레포 종합)
# ---------------------------------------------------------------------------

def expected_level(
    per_repo_diags: List[Dict[str, Any]],
    team_repo_count: int,
) -> Dict[str, Any]:
    """
    레포별 진단 결과를 종합해 Entry/Competitive/Top 등급 판정.
    팀 레포의 가산점 4개 항목은 점수 가중치 ↑ (실무 신호이므로).
    """
    n_repos = len(per_repo_diags)
    if n_repos == 0:
        return {"level": "Entry", "summary": "분석된 레포가 없습니다."}

    def _agg_status(item_key: str, group: str) -> str:
        statuses: List[str] = []
        for d in per_repo_diags:
            items = d.get(group, {})
            s = items.get(item_key, {}).get("status")
            if s:
                statuses.append(s)
        if not statuses:
            return "알 수 없음"
        good = sum(1 for s in statuses if s in ("양호", "규칙적"))
        if good >= max(1, len(statuses) // 2):
            return "양호"
        if any(s in ("보통",) for s in statuses):
            return "보통"
        return "개선 필요"

    readme_st = _agg_status("readme_quality", "core_items")
    struct_st = _agg_status("project_structure", "core_items")
    commit_st = _agg_status("commit_quality", "core_items")

    team_diags = [d for d in per_repo_diags if d.get("repo_type") == "team"]
    team_test_yes = sum(
        1 for d in team_diags
        if d["extra_items"]["test_coverage"]["status"] == "양호"
    )
    team_cicd_yes = sum(
        1 for d in team_diags
        if d["extra_items"]["cicd"]["status"] == "양호"
    )
    team_deploy_yes = sum(
        1 for d in team_diags
        if d["extra_items"]["deployment"]["status"] == "양호"
    )

    team_extra_yes = 0
    for d in team_diags:
        for k in ("test_coverage", "cicd", "deployment", "commit_pattern"):
            if d["extra_items"][k]["status"] in ("양호", "규칙적"):
                team_extra_yes += 1

    score = 0
    if readme_st in ("양호", "보통"):
        score += 1
    if struct_st == "양호":
        score += 1
    if commit_st in ("양호", "보통"):
        score += 1
    if n_repos >= 2:
        score += 1
    if team_repo_count >= 1:
        score += 1
    # 테스트/CI/CD/배포/커밋 리듬은 팀 레포에서만 강한 평가 신호로 반영한다.
    if team_test_yes >= 1:
        score += 1
    if team_cicd_yes >= 1:
        score += 1
    if team_deploy_yes >= 1:
        score += 1
    score += min(team_extra_yes, 2)

    multi_proj = n_repos >= 2
    has_test = team_test_yes >= 1
    has_cicd = team_cicd_yes >= 1
    has_deploy = team_deploy_yes >= 1
    readme_ok = readme_st in ("양호", "보통")

    if readme_ok and multi_proj and team_repo_count >= 1 and has_test and has_cicd and has_deploy and score >= 8:
        return {
            "level": "Top",
            "summary": "대형 테크·우수 스타트업 서류에서 경쟁력을 기대할 수 있는 완성도(참고 기준)입니다.",
        }
    if readme_ok and team_repo_count >= 1 and (has_cicd or has_deploy) and multi_proj and score >= 5:
        return {
            "level": "Competitive",
            "summary": "중견 IT·시리즈 B급 이상 스타트업에 맞설 만한 포트폴리오 완성도로 볼 수 있습니다.",
        }
    # v6.2: 개인 레포 전용 Competitive 경로
    if team_repo_count == 0 and n_repos >= 2:
        all_core_good = all(
            _agg_status(k, "core_items") in ("양호", "보통")
            for k in ("readme_quality", "project_structure", "commit_quality")
        )
        personal_extras = sum(
            1
            for d in per_repo_diags
            for k in ("test_coverage", "cicd", "deployment")
            if d["extra_items"][k]["status"] in ("양호", "규칙적")
        )
        if all_core_good and personal_extras >= 2 and score >= 5:
            return {
                "level": "Competitive (개인)",
                "summary": (
                    "팀 프로젝트 경험은 감지되지 않았으나, 개인 프로젝트의 완성도가 "
                    "Competitive 수준입니다. 팀 프로젝트 추가 시 더 강한 어필이 가능합니다."
                ),
            }
        return {
            "level": "Entry",
            "summary": (
                "Entry 수준 — 중견·중소 SI 또는 일반 스타트업 지원 가능 수준. "
                "현재 팀 프로젝트 경험이 감지되지 않아 Competitive 이상 등급에는 도달하지 않습니다. "
                "팀 프로젝트 1개 이상 확보 시 더 높은 등급에 도전할 수 있습니다."
            ),
        }
    return {
        "level": "Entry",
        "summary": "Entry 수준 — 중견·중소 SI 또는 일반 스타트업 지원 가능 수준입니다.",
    }


# ---------------------------------------------------------------------------
# v6.1: 종합 분석 블록 (GitHub 점수 + 레포 구성 + 강점 + Quick wins)
# ---------------------------------------------------------------------------

_DIAG_LABELS_FOR_SUMMARY: Dict[str, str] = {
    "readme_quality": "README 품질",
    "project_structure": "프로젝트 구조",
    "commit_quality": "커밋 메시지",
    "test_coverage": "테스트",
    "cicd": "CI/CD",
    "deployment": "배포",
}

_QUICK_WINS_POOL_DEFAULT: List[tuple] = [
    ("readme_quality", "README에 프로젝트 목적 + 기술 스택 + 스크린샷 1장 추가 (1시간 이내)"),
    ("commit_quality", "Conventional Commits 적용 (feat:/fix:/refactor:)"),
    ("cicd", "GitHub Actions 워크플로우 1개 추가 (Python: pytest, Node: jest)"),
    ("deployment", "Dockerfile + docker-compose.yml로 로컬 실행 가능하게 구성"),
    ("test_coverage", "핵심 비즈니스 로직 1~2개에 단위 테스트 추가"),
]

_QUICK_WINS_POOL_GAME: List[tuple] = [
    ("readme_quality", "README에 프로젝트 목적 + 기술 스택 + 스크린샷/GIF 1장 추가 (1시간 이내)"),
    ("commit_quality", "Conventional Commits 적용 (feat:/fix:/refactor:)"),
    ("cicd", "GameCI GitHub Action 또는 엔진 빌드 자동화 파이프라인 추가"),
    ("deployment", "빌드 결과물(APK/EXE) 또는 itch.io/스토어 배포 링크를 README에 명시"),
    ("test_coverage", "Unity Test Framework / Unreal Automation Tests 등 엔진 테스트 도구 추가"),
]

_BAD_STATUSES = {"미흡", "개선 필요", "미경험", "선택 가점", "없음", "필수 미흡", "확인 필요"}


def _primary_domain_from_profile(profile: Dict[str, Any]) -> Optional[str]:
    c: Counter = Counter()
    for r in profile.get("per_repo") or []:
        for d in r.get("detected_domains") or []:
            c[d] += 1
    if c:
        return c.most_common(1)[0][0]
    return None


def _portfolio_composition_lines(
    per_repo_diags: List[Dict[str, Any]],
    primary_domain: Optional[str],
) -> List[str]:
    n = len(per_repo_diags)
    if n == 0:
        return ["    · 분석된 레포 없음"]

    personal_n = sum(1 for d in per_repo_diags if d["repo_type"] == "personal")
    team_n = sum(1 for d in per_repo_diags if d["repo_type"] == "team")

    composition: List[str] = []
    parts = []
    if personal_n:
        parts.append(f"개인 {personal_n}개")
    if team_n:
        parts.append(f"팀 {team_n}개")
    if parts:
        composition.append(f"    · 레포 구성: {' + '.join(parts)} (총 {n}개)")

    if primary_domain:
        composition.append(f"    · 주요 도메인: {primary_domain}")

    if team_n == 0 and n >= 2:
        composition.append("    · 팀 프로젝트 1개 추가 시 협업 경험 어필에 유리합니다.")
    elif team_n >= 1 and personal_n == 0:
        composition.append("    · 개인 사이드 프로젝트 추가로 독립 완성 능력도 어필해 보세요.")

    return composition


def _aggregate_strengths(per_repo_diags: List[Dict[str, Any]]) -> List[str]:
    counters: Counter = Counter()
    for d in per_repo_diags:
        for key, item in d["core_items"].items():
            if item["status"] == "양호":
                counters[key] += 1
        if d.get("repo_type") == "team":
            for key in ("test_coverage", "cicd", "deployment"):
                if d["extra_items"][key]["status"] == "양호":
                    counters[key] += 1
    out: List[str] = []
    for key, _ in counters.most_common():
        out.append(_DIAG_LABELS_FOR_SUMMARY.get(key, key))
        if len(out) >= 2:
            break
    return out


def _aggregate_quick_wins(
    per_repo_diags: List[Dict[str, Any]],
    game_engines: Optional[Set[str]] = None,
) -> List[str]:
    """미흡 항목 빈도순 Quick wins 추출. 게임 엔진 감지 시 게임 맥락 풀 사용."""
    bad_counter: Counter = Counter()
    for d in per_repo_diags:
        for key, item in d["core_items"].items():
            if item["status"] in _BAD_STATUSES:
                bad_counter[key] += 1
        if d.get("repo_type") == "team":
            for key in ("test_coverage", "cicd", "deployment"):
                if d["extra_items"][key]["status"] in _BAD_STATUSES:
                    bad_counter[key] += 1

    # v6.3: 게임 프로젝트면 게임 맥락 Quick Wins 풀 사용
    pool = _QUICK_WINS_POOL_GAME if game_engines else _QUICK_WINS_POOL_DEFAULT

    out: List[str] = []
    used = set()
    for key, action in pool:
        if key in bad_counter and key not in used:
            out.append(action)
            used.add(key)
        if len(out) >= 3:
            break
    return out


def generate_summary_block(
    per_repo_diags: List[Dict[str, Any]],
    level_dict: Dict[str, Any],
    github_score: float,
    score_breakdown: Dict[str, Any],
    primary_domain: Optional[str],
    per_repo_scores: Optional[List[Dict[str, Any]]] = None,   # v6.2
    game_engines: Optional[Set[str]] = None,                   # v6.3
) -> str:
    """
    종합 분석 블록 — GitHub 점수 + 레포 구성 + 강점 + Quick wins.
    v6.2: per_repo_scores 추가 시 레포별 점수 표시.
    v6.3: game_engines 전달 시 게임 맥락 Quick Wins 사용.
    """
    level = level_dict.get("level", "Entry")
    pd_str = primary_domain or "개발"

    # v6.2: 팀 레포 부재 + Competitive(개인) 경우 포지셔닝 문구 강화
    team_count = sum(1 for d in per_repo_diags if d.get("repo_type") == "team")
    if level == "Top":
        pos_suffix = "대형 테크·우수 스타트업까지 도전 가능한 완성도입니다."
    elif level == "Competitive":
        pos_suffix = "주요 항목 보강 시 상위 직군 도전이 가능한 수준입니다."
    elif level == "Competitive (개인)":
        pos_suffix = "개인 프로젝트 완성도가 우수합니다. 팀 프로젝트 추가 시 더 강한 어필이 가능합니다."
    elif team_count == 0:
        pos_suffix = "경쟁력 있는 지원을 위해 팀 프로젝트 경험 확보가 권장됩니다."
    else:
        pos_suffix = "경쟁력 있는 지원을 위해 보강이 필요한 단계입니다."

    positioning = f"{pd_str} {level} 수준 포트폴리오 — {pos_suffix}"

    contrib = score_breakdown.get("contribution", 0)
    quality = score_breakdown.get("quality", 0)
    consistency = score_breakdown.get("consistency", 0)

    strengths = _aggregate_strengths(per_repo_diags)
    quick_wins = _aggregate_quick_wins(per_repo_diags, game_engines=game_engines)
    composition_lines = _portfolio_composition_lines(per_repo_diags, primary_domain)

    lines = [
        "─" * 60,
        "[종합 분석]",
        "─" * 60,
        f"  GitHub 종합 점수: {github_score}점 / 100점",
        f"    산출 기준: 대표 프로젝트(최고점) 70% + 전체 평균 30%",
        f"    (개발 활동량 {contrib} / 프로젝트 운영도 {quality} / 작업 일관성 {consistency}) — 최고 레포 기준",
        "",
    ]

    # v6.2: 레포별 점수 표시
    if per_repo_scores:
        lines.append("  레포별 점수:")
        for i, rps in enumerate(per_repo_scores, 1):
            name = rps.get("repo_name", f"레포 {i}")
            rtype = rps.get("repo_type", "")
            total = rps.get("repo_total_score", 0)
            bd = rps.get("score_breakdown") or {}
            type_label = "팀" if rtype == "team" else "개인"
            lines.append(
                f"    {i}. {name} ({type_label}): {total}점"
                f"  (개발 활동량 {bd.get('contribution', 0)} / "
                f"프로젝트 운영도 {bd.get('quality', 0)} / "
                f"작업 일관성 {bd.get('consistency', 0)})"
            )
        lines.append("")

    lines += [
        f"  포지셔닝     : {positioning}",
        "",
        "  포트폴리오 구성:",
    ]
    lines.extend(composition_lines)
    lines.append("")
    lines.append("  강점:")
    if strengths:
        for s in strengths:
            lines.append(f"    · {s}")
    else:
        lines.append("    · (주요 항목 보강 후 재확인 권장)")
    lines.append("")
    lines.append("  실행 가능한 개선 (Quick Wins):")
    if quick_wins:
        for i, qw in enumerate(quick_wins, 1):
            lines.append(f"    {i}. {qw}")
    else:
        lines.append("    (모든 주요 항목이 양호합니다)")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# 진입점
# ---------------------------------------------------------------------------

def run_diagnosis(profile: Dict[str, Any]) -> Dict[str, Any]:
    """
    extract_applicant_profile() 반환 프로필을 입력으로 진단 JSON을 생성.
    v6.1: 레포별 카드 진단(per_repo_diagnoses) + 종합 분석 블록.
    """
    per_repo: List[Dict[str, Any]] = list(profile.get("per_repo") or [])

    per_repo_diags: List[Dict[str, Any]] = [diagnose_single_repo(r) for r in per_repo]

    ms = profile.get("metrics_summary") or {}
    vl = int(ms.get("total_valid_loc") or 0)
    el = int(ms.get("total_evidence_loc") or 0)

    team_repo_count = sum(1 for d in per_repo_diags if d["repo_type"] == "team")
    level_dict = expected_level(per_repo_diags, team_repo_count)

    primary_domain = _primary_domain_from_profile(profile)
    github_score = float(profile.get("github_score") or 0)
    score_breakdown = profile.get("score_breakdown") or {}

    # v6.2: per_repo에서 레포별 점수 정보 추출하여 summary_block에 전달
    per_repo_scores = [
        {
            "repo_name": r.get("repo_name", ""),
            "repo_type": r.get("repo_type", "personal"),
            "repo_total_score": r.get("repo_total_score", 0),
            "score_breakdown": r.get("score_breakdown") or {},
        }
        for r in per_repo
        if r.get("repo_total_score") is not None or r.get("score_breakdown")
    ] or None

    game_engines = _collect_game_engines(per_repo)   # v6.3: 게임 맥락 Quick Wins 분기용

    summary_block = generate_summary_block(
        per_repo_diags, level_dict, github_score, score_breakdown, primary_domain,
        per_repo_scores=per_repo_scores,
        game_engines=game_engines or None,
    )

    return {
        "per_repo_diagnoses": per_repo_diags,
        "expected_level": level_dict,
        "contribution_type": contribution_type_note(vl, el),
        "repo_classifications": _build_repo_classifications(per_repo),
        "summary_block": summary_block,
    }
