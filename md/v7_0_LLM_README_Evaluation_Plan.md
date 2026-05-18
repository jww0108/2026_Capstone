# Git2Value — 로컬 LLM README 평가 시스템 설계

> 작성일: 2026.05.13 | 대상 버전: v6.4 → v7.0 (README LLM 보강)
> 전제: 파인튜닝 없음 (Qwen2.5-32B-AWQ 베이스 성능), vLLM 상시 서빙, Docker 인프라는 별도 진행

---

## 1. 목표와 범위

### 1-1. 한 줄 목표

**룰베이스가 판정할 수 없는 "README 내용의 품질"을 로컬 LLM으로 평가하여, 포트폴리오 진단의 정확도와 개선 제안의 구체성을 높인다.**

### 1-2. 범위

| 포함 | 미포함 |
|---|---|
| README 내용 품질 5차원 평가 | 코드 품질 분석 |
| 도메인 맥락 맞춤 개선 제안 | 커밋 메시지 평가 |
| 룰베이스 폴백 보장 | FAISS 매칭 직접 활용 |
| 골든 셋 기반 정확도 검증 | 프로젝트 구조 평가 |
| 한국어/영문 README 대응 | 파인튜닝 |

### 1-3. 설계 원칙

| 원칙 | 구현 |
|---|---|
| **LLM은 Optional** | 서버 다운 시 룰베이스 단독 동작. 진단 결과에 "LLM 미사용" 표기 |
| **모듈 독립 유지** | LLM은 모듈 B(진단) 내부 보강. A(매칭)·C(연봉)·github_score에 영향 없음 |
| **일관성 > 창의성** | temperature=0.1, guided_json으로 구조화된 출력 강제 |
| **지연 시간 제한** | 레포당 LLM 응답 3초 이내. 초과 시 타임아웃 → 룰베이스 폴백 |
| **검증 가능성** | 골든 셋 15개 기준 tier 일치율 80% 이상 달성 후 적용 |

---

## 2. 아키텍처

### 2-1. 전체 흐름

```
                         ┌─────────────────┐
                         │  vLLM 서버      │
                         │  (상시 운영)     │
                         │  :8000           │
                         └────────┬────────┘
                                  │ HTTP (localhost)
                                  │
┌─────────────────────────────────┴──────────────────────────────────┐
│  run_git2value.py                                                  │
│                                                                    │
│  1. GitHub API 수집  ──→  github_extractor.py                      │
│     └─ readme_raw, 언어, 시그너처, 도메인 등                       │
│                                                                    │
│  2. LLM 평가 요청   ──→  llm_readme_evaluator.py  ──→  vLLM 서버  │
│     └─ readme_raw + 메타데이터 전송                                │
│     └─ 타임아웃/오류 시 None 반환                                  │
│                                                                    │
│  3. 진단 생성       ──→  portfolio_diagnosis.py                     │
│     └─ _readme_diagnosis_single(repo, llm_result)                  │
│         ├─ llm_result 있음: LLM 5차원 점수 + 제안 활용             │
│         └─ llm_result 없음: 룰베이스 단독 판정 (기존 v6.4)         │
│                                                                    │
│  4. 출력            ──→  LLM 사용 여부 표기                        │
└────────────────────────────────────────────────────────────────────┘
```

### 2-2. 호출 타이밍 — GitHub API와 병렬

```python
# run_git2value.py — E2E 파이프라인 내부

async def _evaluate_all_repos(repos, extractor, llm_evaluator):
    tasks = []
    for repo in repos:
        # 1단계: GitHub API 수집 (기존)
        repo_data = await extractor.evaluate_repository(repo)

        # 2단계: LLM 평가를 비동기 태스크로 즉시 시작
        llm_task = asyncio.create_task(
            llm_evaluator.evaluate(
                readme_raw=repo_data.get("readme_raw", ""),
                meta={
                    "languages": repo_data.get("languages", {}),
                    "domain": repo_data.get("detected_domain", ""),
                    "signatures": repo_data.get("engine_signatures", []),
                    "repo_type": repo_data.get("repo_type", "personal"),
                },
            )
        )
        tasks.append((repo_data, llm_task))

    # 3단계: 모든 LLM 결과 수집
    evaluated = []
    for repo_data, llm_task in tasks:
        try:
            llm_result = await asyncio.wait_for(llm_task, timeout=5.0)
        except (asyncio.TimeoutError, Exception):
            llm_result = None
        evaluated.append((repo_data, llm_result))

    return evaluated
```

레포 1의 LLM 평가가 진행되는 동안 레포 2의 GitHub API 호출이 시작되므로, 추가 지연이 최소화됩니다.

---

## 3. LLM 입력 설계

### 3-1. 입력 구성

```
[시스템 프롬프트] — 역할 + 평가 기준 + 출력 포맷
[사용자 메시지]  — README 원본 + 메타데이터 컨텍스트
```

### 3-2. 시스템 프롬프트

```
You are a senior hiring manager evaluating GitHub README files for junior developer (0-3 years) portfolios.

Evaluate the README on 5 dimensions, each scored 1-5:

1. PURPOSE CLARITY (목적 명확성)
   1: Cannot tell what this project does
   2: Vague description, unclear problem/solution
   3: Basic description present but lacks context
   4: Clear purpose with problem statement
   5: Compelling problem definition + solution approach

2. TECH DESCRIPTION (기술 설명)
   1: No technology mentioned
   2: Tech names listed without context
   3: Tech stack section exists with brief explanation
   4: Tech stack with selection rationale or architecture overview
   5: Detailed architecture + tech choices justified

3. SETUP GUIDE (실행 가이드)
   1: No setup instructions
   2: Partial commands, missing prerequisites
   3: Clone→install→run steps present but incomplete
   4: Complete reproducible setup guide
   5: One-command setup (Docker/script) with troubleshooting

4. VISUAL DEMO (시각 자료)
   1: No visuals at all
   2: One low-quality or irrelevant image
   3: Meaningful screenshot(s)
   4: Screenshots + GIF/video demo
   5: Rich visuals including architecture diagram + demo

5. OVERALL QUALITY (종합)
   Score = your holistic assessment (not necessarily the average)
   Also assign tier: "양호" (score>=4), "보통" (score 2.5-3.9), "미흡" (score<2.5)

CRITICAL RULES:
- Consider the project's DOMAIN context. A game project needs different things than a backend API.
- Be calibrated for JUNIOR developers (0-3 years). Don't expect enterprise-level docs.
- Provide exactly 2 actionable improvement suggestions, specific to this project's domain.
- Respond ONLY in the specified JSON format. No markdown, no preamble.
```

### 3-3. 사용자 메시지 템플릿

```python
USER_PROMPT_TEMPLATE = """
PROJECT CONTEXT:
- Primary languages: {languages}
- Detected domain: {domain}
- Detected signatures: {signatures}
- Repository type: {repo_type}

README CONTENT (first 3000 chars):
---
{readme_raw}
---

Evaluate this README and respond in JSON.
"""
```

### 3-4. 입력 전처리

```python
def _prepare_llm_input(readme_raw: str, meta: dict) -> str:
    # README 3000자 제한 (추론 시간 + 토큰 비용 제어)
    truncated = readme_raw[:3000]

    # 언어 정보 포맷팅 (상위 3개만)
    lang_stats = meta.get("languages", {})
    sorted_langs = sorted(lang_stats.items(), key=lambda x: x[1], reverse=True)[:3]
    lang_str = ", ".join(f"{k} {v}%" for k, v in sorted_langs) if sorted_langs else "Unknown"

    # 시그너처 포맷팅
    sigs = meta.get("signatures", [])
    sig_str = ", ".join(sigs[:5]) if sigs else "None detected"

    return USER_PROMPT_TEMPLATE.format(
        languages=lang_str,
        domain=meta.get("domain", "Unknown"),
        signatures=sig_str,
        repo_type=meta.get("repo_type", "personal"),
        readme_raw=truncated,
    )
```

---

## 4. LLM 출력 설계

### 4-1. JSON 스키마

```python
README_EVAL_SCHEMA = {
    "type": "object",
    "properties": {
        "purpose_clarity": {
            "type": "object",
            "properties": {
                "score": {"type": "integer", "minimum": 1, "maximum": 5},
                "reason": {"type": "string", "maxLength": 150}
            },
            "required": ["score", "reason"]
        },
        "tech_description": {
            "type": "object",
            "properties": {
                "score": {"type": "integer", "minimum": 1, "maximum": 5},
                "reason": {"type": "string", "maxLength": 150}
            },
            "required": ["score", "reason"]
        },
        "setup_guide": {
            "type": "object",
            "properties": {
                "score": {"type": "integer", "minimum": 1, "maximum": 5},
                "reason": {"type": "string", "maxLength": 150}
            },
            "required": ["score", "reason"]
        },
        "visual_demo": {
            "type": "object",
            "properties": {
                "score": {"type": "integer", "minimum": 1, "maximum": 5},
                "reason": {"type": "string", "maxLength": 150}
            },
            "required": ["score", "reason"]
        },
        "overall_quality": {
            "type": "object",
            "properties": {
                "score": {"type": "integer", "minimum": 1, "maximum": 5},
                "tier": {"type": "string", "enum": ["양호", "보통", "미흡"]},
                "summary": {"type": "string", "maxLength": 200}
            },
            "required": ["score", "tier", "summary"]
        },
        "improvement_suggestions": {
            "type": "array",
            "items": {"type": "string", "maxLength": 150},
            "minItems": 2,
            "maxItems": 2
        }
    },
    "required": [
        "purpose_clarity", "tech_description", "setup_guide",
        "visual_demo", "overall_quality", "improvement_suggestions"
    ]
}
```

### 4-2. 출력 예시

**입력:** FastAPI 백엔드 프로젝트, README에 `## 소개` + `## 기술 스택` 있으나 실행 방법 없음

```json
{
    "purpose_clarity": {
        "score": 4,
        "reason": "프로젝트 목적이 첫 문단에 명확히 기술. 해결하려는 문제도 언급됨"
    },
    "tech_description": {
        "score": 4,
        "reason": "FastAPI, PostgreSQL, Docker가 표로 정리되어 있고 역할 설명 포함"
    },
    "setup_guide": {
        "score": 1,
        "reason": "설치 및 실행 방법이 전혀 없음"
    },
    "visual_demo": {
        "score": 3,
        "reason": "API 응답 스크린샷 1장 포함. 아키텍처 다이어그램 없음"
    },
    "overall_quality": {
        "score": 3,
        "tier": "보통",
        "summary": "프로젝트 설명과 기술 스택은 잘 갖춰져 있으나, 실행 가이드가 완전히 빠져 있어 채용 담당자가 직접 확인하기 어렵습니다"
    },
    "improvement_suggestions": [
        "docker-compose up 한 줄로 실행 가능하도록 Docker 설정과 실행 가이드를 README에 추가하세요",
        "주요 API 엔드포인트 목록(경로, 메서드, 설명)을 표로 정리하면 백엔드 역량이 더 잘 드러납니다"
    ]
}
```

---

## 5. 통합 로직 — 룰베이스 + LLM 병합

### 5-1. 판정 우선순위

```
LLM 결과 있음:
  → LLM tier 채택 ("양호"/"보통"/"미흡")
  → LLM summary를 진단 설명으로 사용
  → LLM improvement_suggestions를 Quick Wins 최우선으로 사용
  → 출력에 "🤖 AI 분석" 표기

LLM 결과 없음 (타임아웃/서버 다운/파싱 실패):
  → 룰베이스 tier 채택 (기존 v6.4 로직 그대로)
  → 룰베이스 진단 설명 사용
  → 정적 Quick Wins 풀 사용
  → 출력에 "📋 룰베이스 분석 (AI 미사용)" 표기
```

### 5-2. `_readme_diagnosis_single()` 수정

```python
def _readme_diagnosis_single(
    repo: Dict[str, Any],
    llm_result: Optional[Dict[str, Any]] = None,       # v7.0 추가
) -> Dict[str, Any]:

    readme_raw = (repo.get("readme_raw") or repo.get("readme") or "").strip()
    readme_clean = (repo.get("readme") or "").strip()
    has_image = bool(repo.get("readme_has_image"))
    n = len(readme_clean)

    # 길이 0 → LLM 결과와 무관하게 즉시 미흡
    if n < 50:
        return _item(
            "미흡",
            "README가 거의 비어 있거나 매우 짧습니다.",
            "채용 담당자가 처음 보는 문서가 README입니다. 구조화된 설명을 추가하세요.",
            llm_used=False,
        )

    # LLM 결과가 유효하면 LLM 기반 판정
    if llm_result and _validate_llm_result(llm_result):
        overall = llm_result["overall_quality"]
        tier = overall["tier"]          # "양호"/"보통"/"미흡"
        summary = overall["summary"]
        suggestions = llm_result.get("improvement_suggestions", [])

        return _item(
            tier,
            summary,
            suggestions[0] if suggestions else None,
            llm_used=True,
            llm_scores={
                "purpose": llm_result["purpose_clarity"]["score"],
                "tech": llm_result["tech_description"]["score"],
                "setup": llm_result["setup_guide"]["score"],
                "visual": llm_result["visual_demo"]["score"],
                "overall": overall["score"],
            },
            llm_suggestions=suggestions,
        )

    # LLM 없으면 룰베이스 (기존 v6.4 로직)
    quality = evaluate_readme_quality(readme_raw)
    missing_dims = [k for k, v in quality["indicators"].items() if not v]
    missing_hint = f" (부족: {', '.join(missing_dims)})" if missing_dims else ""

    if n >= 200:
        if quality["status"] == "양호":
            img_hint = " · 이미지 포함" if has_image else ""
            return _item(
                "양호",
                f"길이 {n:,}자{img_hint}. 목적·기술스택·시각화 항목이 충실합니다.",
                None,
                llm_used=False,
            )
        return _item(
            "개선 필요",
            f"길이는 충분({n:,}자)하지만 구성이 아쉽습니다{missing_hint}.",
            f"README에 {', '.join(missing_dims) if missing_dims else '목적·기술 스택·스크린샷'}을 추가하면 완성도가 높아집니다.",
            llm_used=False,
        )

    return _item(
        "개선 필요",
        f"README가 짧습니다 ({n:,}자){missing_hint}.",
        "프로젝트 목적, 기술 스택, 실행 방법, 데모 GIF/스크린샷을 README에 정리하세요.",
        llm_used=False,
    )
```

### 5-3. `_item()` 확장

```python
def _item(
    status: str,
    detail: str,
    action: Optional[str],
    llm_used: bool = False,                                 # v7.0 추가
    llm_scores: Optional[Dict[str, int]] = None,            # v7.0 추가
    llm_suggestions: Optional[List[str]] = None,            # v7.0 추가
) -> Dict[str, Any]:
    result = {"status": status, "detail": detail, "action": action}
    result["llm_used"] = llm_used
    if llm_scores:
        result["llm_scores"] = llm_scores
    if llm_suggestions:
        result["llm_suggestions"] = llm_suggestions
    return result
```

### 5-4. LLM 결과 유효성 검증

```python
def _validate_llm_result(result: dict) -> bool:
    """LLM 출력이 스키마에 맞는지 최소 검증."""
    try:
        overall = result.get("overall_quality", {})
        if overall.get("tier") not in ("양호", "보통", "미흡"):
            return False
        if not (1 <= overall.get("score", 0) <= 5):
            return False
        for key in ("purpose_clarity", "tech_description", "setup_guide", "visual_demo"):
            dim = result.get(key, {})
            if not (1 <= dim.get("score", 0) <= 5):
                return False
        suggestions = result.get("improvement_suggestions", [])
        if not isinstance(suggestions, list) or len(suggestions) < 1:
            return False
        return True
    except Exception:
        return False
```

---

## 6. 신규 파일: `llm_readme_evaluator.py`

### 6-1. 모듈 구조

```python
"""
Git2Value v7.0 — 로컬 LLM 기반 README 품질 평가.

vLLM 서버(Qwen2.5-32B-AWQ)에 README + 메타데이터를 전송하여
5차원 품질 점수 + 도메인 맞춤 개선 제안을 반환한다.
서버 미가동 시 None 반환 → 룰베이스 폴백 보장.
"""
from __future__ import annotations

import asyncio
import json
import logging
from typing import Any, Dict, Optional

import aiohttp

logger = logging.getLogger(__name__)

# ── 설정 ──────────────────────────────────────────────────
LLM_BASE_URL = "http://localhost:8000/v1"
LLM_MODEL = "Qwen/Qwen2.5-32B-Instruct-AWQ"
LLM_TIMEOUT = 5.0         # 초
LLM_TEMPERATURE = 0.1     # 일관성 최대화
LLM_MAX_TOKENS = 600
README_MAX_CHARS = 3000


class ReadmeEvaluator:
    """vLLM 서버와 통신하는 README 평가기."""

    def __init__(
        self,
        base_url: str = LLM_BASE_URL,
        model: str = LLM_MODEL,
        timeout: float = LLM_TIMEOUT,
    ):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout = timeout
        self._available: Optional[bool] = None

    async def health_check(self) -> bool:
        """vLLM 서버 가용성 확인. 최초 1회만 실행, 결과 캐시."""
        if self._available is not None:
            return self._available
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.base_url}/models",
                    timeout=aiohttp.ClientTimeout(total=2.0),
                ) as resp:
                    self._available = resp.status == 200
        except Exception:
            self._available = False
        if not self._available:
            logger.warning("LLM 서버 미가용 — README 평가는 룰베이스로 폴백")
        return self._available

    async def evaluate(
        self,
        readme_raw: str,
        meta: Dict[str, Any],
    ) -> Optional[Dict[str, Any]]:
        """
        README 품질 평가 요청.
        성공 시 5차원 점수 dict, 실패 시 None.
        """
        if not await self.health_check():
            return None

        if not readme_raw or len(readme_raw.strip()) < 50:
            return None  # 너무 짧으면 LLM 호출 불필요

        prompt = self._build_prompt(readme_raw, meta)

        try:
            async with aiohttp.ClientSession() as session:
                payload = {
                    "model": self.model,
                    "messages": [
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": prompt},
                    ],
                    "temperature": LLM_TEMPERATURE,
                    "max_tokens": LLM_MAX_TOKENS,
                    "guided_json": README_EVAL_SCHEMA,
                }
                async with session.post(
                    f"{self.base_url}/chat/completions",
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=self.timeout),
                ) as resp:
                    if resp.status != 200:
                        logger.warning(f"LLM 응답 오류: HTTP {resp.status}")
                        return None
                    data = await resp.json()

            content = data["choices"][0]["message"]["content"]
            result = json.loads(content)

            if _validate_llm_result(result):
                return result
            else:
                logger.warning("LLM 출력 스키마 검증 실패")
                return None

        except asyncio.TimeoutError:
            logger.warning(f"LLM 타임아웃 ({self.timeout}초 초과)")
            return None
        except (json.JSONDecodeError, KeyError, IndexError) as e:
            logger.warning(f"LLM 응답 파싱 실패: {e}")
            return None
        except Exception as e:
            logger.warning(f"LLM 호출 예외: {e}")
            return None

    def _build_prompt(self, readme_raw: str, meta: dict) -> str:
        """사용자 메시지 조립."""
        truncated = readme_raw[:README_MAX_CHARS]

        lang_stats = meta.get("languages", {})
        sorted_langs = sorted(lang_stats.items(), key=lambda x: x[1], reverse=True)[:3]
        lang_str = ", ".join(f"{k} {v}%" for k, v in sorted_langs) if sorted_langs else "Unknown"

        sigs = meta.get("signatures", [])
        sig_str = ", ".join(sigs[:5]) if sigs else "None detected"

        return USER_PROMPT_TEMPLATE.format(
            languages=lang_str,
            domain=meta.get("domain", "Unknown"),
            signatures=sig_str,
            repo_type=meta.get("repo_type", "personal"),
            readme_raw=truncated,
        )
```

### 6-2. 에러 처리 정책

| 실패 유형 | 동작 | 로그 |
|---|---|---|
| 서버 미가동 (health_check 실패) | None → 룰베이스 | WARNING 1회 |
| HTTP 오류 (4xx/5xx) | None → 룰베이스 | WARNING + status code |
| 타임아웃 (5초 초과) | None → 룰베이스 | WARNING |
| JSON 파싱 실패 | None → 룰베이스 | WARNING + 오류 내용 |
| 스키마 검증 실패 | None → 룰베이스 | WARNING |
| README 50자 미만 | None (호출 안 함) | — |

모든 실패 경로가 `None`을 반환하여 룰베이스 폴백을 보장한다. 사용자에게는 오류 메시지 대신 "📋 룰베이스 분석" 표기로 대체.

---

## 7. Quick Wins 통합

### 7-1. LLM 제안 우선 사용

```python
def _aggregate_quick_wins(
    per_repo_diags: List[Dict[str, Any]],
    game_engines: Optional[Set[str]] = None,
) -> List[str]:
    # v7.0: LLM 개선 제안이 있으면 최우선 사용
    llm_suggestions = []
    for d in per_repo_diags:
        core_readme = d.get("core_items", {}).get("readme_quality", {})
        if core_readme.get("llm_suggestions"):
            llm_suggestions.extend(core_readme["llm_suggestions"])

    if llm_suggestions:
        # 중복 제거 + 최대 3개
        seen = set()
        unique = []
        for s in llm_suggestions:
            if s not in seen:
                seen.add(s)
                unique.append(s)
            if len(unique) >= 3:
                break
        return unique

    # LLM 미사용 시 기존 정적 풀 로직 (v6.4 그대로)
    ...
```

### 7-2. 제안 품질 차이 예시

| 상황 | 정적 풀 (기존) | LLM 제안 |
|---|---|---|
| FastAPI 프로젝트 | "GitHub Actions 워크플로우 1개 추가 (Python: pytest, Node: jest)" | "주요 API 엔드포인트 목록(경로, 메서드, 설명)을 표로 정리하면 백엔드 역량이 더 잘 드러납니다" |
| Unity 게임 | "Dockerfile + docker-compose.yml로 로컬 실행 가능하게 구성" | "빌드된 WebGL 또는 APK를 itch.io에 올리고 링크를 README에 추가하세요" |
| ML 프로젝트 | "핵심 비즈니스 로직 1~2개에 단위 테스트 추가" | "모델 성능 지표(정확도, F1 등)를 표로 정리하고 학습 곡선 그래프를 README에 추가하세요" |

---

## 8. 출력 표시

### 8-1. 레포 카드 내 README 진단

```
📄 README 품질: 보통
   🤖 AI 분석: 프로젝트 설명과 기술 스택은 잘 갖춰져 있으나,
   실행 가이드가 빠져 있어 채용 담당자가 직접 확인하기 어렵습니다
   ├─ 목적 명확성: ████░ 4/5
   ├─ 기술 설명:   ████░ 4/5
   ├─ 실행 가이드: █░░░░ 1/5
   ├─ 시각 자료:   ███░░ 3/5
   └─ 종합:        ███░░ 3/5

또는 (LLM 미사용 시):

📄 README 품질: 개선 필요
   📋 룰베이스 분석 (AI 미사용): 길이는 충분(823자)하지만
   구성이 아쉽습니다 (부족: 결과물 시각화)
```

### 8-2. `_print_repo_card()` 수정

```python
def _print_repo_card(repo_diag, ...):
    readme = repo_diag["core_items"]["readme_quality"]
    status = readme["status"]
    detail = readme["detail"]
    llm_used = readme.get("llm_used", False)

    label = "🤖 AI 분석" if llm_used else "📋 룰베이스 분석 (AI 미사용)"
    print(f"  📄 README 품질: {status}")
    print(f"     {label}: {detail}")

    # LLM 5차원 점수 바 (LLM 사용 시만)
    if llm_used and readme.get("llm_scores"):
        scores = readme["llm_scores"]
        dim_names = {
            "purpose": "목적 명확성",
            "tech": "기술 설명  ",
            "setup": "실행 가이드",
            "visual": "시각 자료  ",
            "overall": "종합      ",
        }
        for key, name in dim_names.items():
            s = scores.get(key, 0)
            bar = "█" * s + "░" * (5 - s)
            print(f"     ├─ {name}: {bar} {s}/5")
```

---

## 9. expected_level() 및 점수 체계 영향

### 9-1. 변경 없음

LLM 결과는 `_readme_diagnosis_single()`의 반환값을 통해 기존 진단 체계에 흘러간다:

```
_readme_diagnosis_single() → status = "양호"/"보통"/"미흡"/"개선 필요"
                                  ↓
diagnose_single_repo()  → core_items["readme_quality"]["status"]
                                  ↓
expected_level()        → readme_st = _agg_status("readme_quality")
                        → readme_st ∈ ("양호", "보통") → score += 1
```

LLM이 반환하는 tier("양호"/"보통"/"미흡")는 룰베이스의 status와 동일한 값 공간이므로 하위 호환 완벽. `expected_level()`, `generate_summary_block()`, `github_score` 모두 코드 변경 없음.

### 9-2. 유일한 차이

LLM 사용 시 README 진단 정확도가 올라가므로:
- 잘 작성된 README가 "양호"로 올바르게 판정됨 → `score += 1` 정상 발동
- Top/Competitive 진입 조건 `readme_ok = True` 정상 개방
- 이것은 v6.4 원본 전환에서 이미 개선된 방향과 동일, LLM이 더 정교할 뿐

---

## 10. 골든 셋 테스트

### 10-1. 구성 (15개 레포)

| # | 유형 | 기대 tier | 핵심 검증 포인트 |
|---|---|---|---|
| 1 | README 없음 | 미흡 | LLM 호출 안 함 (50자 미만) |
| 2 | CRA 보일러플레이트만 | 미흡 | 보일러플레이트를 "내용 있음"으로 오판하지 않는지 |
| 3 | 한 줄 설명만 | 미흡 | 짧지만 LLM이 과대평가하지 않는지 |
| 4 | 목적만 있고 기술/실행 없음 | 미흡~보통 | 목적 점수만 높고 나머지 낮은지 |
| 5 | 기술 나열만 (설명 없음) | 보통 | tech_description 2~3점인지 |
| 6 | 목적 + 기술 + 실행 없음 | 보통 | setup_guide 1점인지 |
| 7 | 영문 README (잘 작성됨) | 양호 | 영문 처리 정확도 |
| 8 | 한국어 README (잘 작성됨) | 양호 | 한국어 처리 정확도 |
| 9 | Unity 게임 프로젝트 | 보통~양호 | 도메인 맥락 인식 (Docker 대신 빌드/배포) |
| 10 | ML 프로젝트 (모델 성능 포함) | 양호 | 모델 지표를 시각 자료로 인정하는지 |
| 11 | 스크린샷만 있고 설명 없음 | 보통 | visual 높고 나머지 낮은 균형 |
| 12 | 상세하지만 이미지 없음 | 보통 | visual 낮고 나머지 높은 균형 |
| 13 | 완벽한 README | 양호 | 5점 만점 근처 |
| 14 | README가 중국어/일본어 | 보통 | 비영어/비한국어 처리 |
| 15 | 자동 생성 README (Copilot 등) | 보통 | 자동 생성 패턴을 과대평가하지 않는지 |

### 10-2. 검증 기준

| 지표 | 통과 기준 |
|---|---|
| **tier 일치율** | 15개 중 12개 이상 (80%) |
| **tier 1단계 이내 오차** | 15개 전체 (100%) — "양호"를 "미흡"으로 판정하면 실패 |
| **도메인 맥락 반영** | 게임/ML 레포의 개선 제안이 도메인에 맞는지 수동 확인 |
| **응답 시간** | 15개 전체 3초 이내 |
| **JSON 파싱 성공률** | 15개 전체 (100%) |

### 10-3. 실행 방법

```python
# tests/test_golden_set.py

import asyncio
import json

GOLDEN_SET = [
    {
        "repo_name": "empty-readme",
        "readme_raw": "",
        "meta": {"languages": {}, "domain": "", "signatures": [], "repo_type": "personal"},
        "expected_tier": "미흡",
        "expected_llm_call": False,  # 50자 미만이므로 호출 안 함
    },
    {
        "repo_name": "perfect-fastapi",
        "readme_raw": open("tests/fixtures/perfect_fastapi_readme.md").read(),
        "meta": {"languages": {"Python": 85}, "domain": "서버/백엔드", "signatures": ["FastAPI", "Docker"], "repo_type": "personal"},
        "expected_tier": "양호",
        "expected_min_score": 4,
    },
    ...
]

async def run_golden_test():
    evaluator = ReadmeEvaluator()
    results = []

    for case in GOLDEN_SET:
        llm_result = await evaluator.evaluate(case["readme_raw"], case["meta"])

        if case.get("expected_llm_call") is False:
            assert llm_result is None, f"{case['repo_name']}: LLM이 호출되면 안 됨"
            continue

        assert llm_result is not None, f"{case['repo_name']}: LLM 응답 없음"
        actual_tier = llm_result["overall_quality"]["tier"]
        actual_score = llm_result["overall_quality"]["score"]

        results.append({
            "repo": case["repo_name"],
            "expected": case["expected_tier"],
            "actual": actual_tier,
            "score": actual_score,
            "match": actual_tier == case["expected_tier"],
        })

    match_rate = sum(r["match"] for r in results) / len(results)
    print(f"Tier 일치율: {match_rate:.0%} ({sum(r['match'] for r in results)}/{len(results)})")
    for r in results:
        status = "✅" if r["match"] else "❌"
        print(f"  {status} {r['repo']}: expected={r['expected']}, actual={r['actual']} (score={r['score']})")
```

---

## 11. 파일 구조 변경

```
basic/
├─ github_extractor.py       # 변경 없음
├─ profile_builder.py         # 변경 없음
├─ portfolio_diagnosis.py     # _readme_diagnosis_single() LLM 통합
├─ valuation_engine.py        # 변경 없음
├─ experience_filter.py       # 변경 없음
├─ run_git2value.py           # LLM 초기화 + 병렬 호출 + 출력 표기
├─ llm_readme_evaluator.py    # ★ 신규: ReadmeEvaluator 클래스
├─ tests/
│   ├─ test_golden_set.py     # ★ 신규: 골든 셋 테스트
│   └─ fixtures/              # ★ 신규: 테스트용 README 파일 15개
└─ vector/
    └─ (기존 FAISS 파일들)
```

---

## 12. 적용 순서

```
Phase 1: 인프라 (별도 진행)
  └─ vLLM 서버 Docker 구성 + Qwen2.5-32B-AWQ 로드

Phase 2: 코드 구현
  1. llm_readme_evaluator.py 작성                     (§6)
  2. portfolio_diagnosis.py 수정
     ├─ _item() 확장 (llm_used, llm_scores 등)        (§5)
     └─ _readme_diagnosis_single() LLM 통합            (§5)
  3. run_git2value.py 수정
     ├─ ReadmeEvaluator 초기화 + health_check          (§2)
     ├─ 병렬 LLM 호출 조율                             (§2)
     └─ _print_repo_card() 출력 표기                   (§8)
  4. Quick Wins LLM 제안 우선 사용                     (§7)

Phase 3: 검증
  1. 골든 셋 README 15개 수집 + 수동 평가               (§10)
  2. test_golden_set.py 작성 + 실행                    (§10)
  3. tier 일치율 80% 확인
  4. LLM 서버 다운 시 룰베이스 폴백 확인
  5. 응답 시간 3초 이내 확인
```

---

## 13. 리스크

| 리스크 | 가능성 | 대응 |
|---|---|---|
| Qwen2.5-32B가 한국어 README를 과소/과대평가 | 중간 | 골든 셋에 한국어 케이스 3개 포함. 프롬프트에 "Korean or English" 명시 |
| 동일 README에 대해 다른 점수 반환 (비결정성) | 낮음 | temperature=0.1 + guided_json. 골든 셋 3회 반복 실행으로 분산 확인 |
| vLLM 서버 VRAM 부족으로 OOM | 낮음 | AWQ 4bit ≈ 18GB. RTX 4090 24GB에서 6GB 여유. `gpu-memory-utilization=0.85`로 제한 |
| LLM 응답 시간 3초 초과 | 중간 | `max_tokens=600`, `max-model-len=4096`으로 제한. 초과 시 타임아웃 → 룰베이스 |
| 보일러플레이트 README를 "양호"로 오판 | 낮음 | 시스템 프롬프트에 "boilerplate or auto-generated READMEs should score low" 명시 |
| `guided_json`이 vLLM 버전에 따라 미지원 | 중간 | vLLM 0.4.0+ 필요. 미지원 시 프롬프트에 JSON 포맷 명시 + regex 파싱으로 폴백 |
| LLM 서버 상시 운영으로 GPU가 다른 작업에 사용 불가 | 확실 | 현재 RTX 4090은 Git2Value 전용. 다른 작업 필요 시 서버 중지 가능 |

---

## 14. 논문/발표 영향

| 항목 | 반영 방향 |
|---|---|
| 아키텍처 다이어그램 | "룰베이스 → 로컬 LLM → 외부 API" 3단계 계층 시각화 |
| 실험 섹션 | 골든 셋 15개 기준 tier 일치율 + LLM 유무 비교표 |
| 관련 연구 | README 품질 자동 평가 선행 연구 인용 |
| 한계 및 향후 과제 | 파인튜닝 미적용, 외부 API(GPT-4 등) 대비 성능 비교 미실시 |

---

## 15. v7.1 이후 검토 항목

| 항목 | 사유 |
|---|---|
| LLM 결과를 FAISS 키워드 압축 폴백으로 활용 | 도메인 사전 미등록 README의 매칭 개선 |
| 커밋 메시지 품질 LLM 평가 | 현재 룰베이스 무의미 커밋 비율 판정의 정확도 한계 |
| 코드 품질 LLM 샘플링 평가 | 주요 파일 상위 N줄 + 구조 → 코딩 스타일/품질 판정 |
| 프롬프트 A/B 테스트 | 프롬프트 변형별 골든 셋 일치율 비교 |
| 파인튜닝 | 골든 셋 확장(100개+) 후 LoRA 파인튜닝 검토 |

---

*Git2Value v7.0 로컬 LLM README 평가 시스템 설계 — 2026.05.13*
