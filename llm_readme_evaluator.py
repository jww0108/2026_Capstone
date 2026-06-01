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
import re
from typing import Any, Dict, List, Optional

import aiohttp

logger = logging.getLogger(__name__)

# ── 설정 ──────────────────────────────────────────────────
LLM_BASE_URL = "http://localhost:8000/v1"
LLM_MODEL = "Qwen/Qwen2.5-32B-Instruct-AWQ"
LLM_TIMEOUT = 20.0        # 초 (느린 GPU/긴 README 대비)
HEALTH_CHECK_TIMEOUT = 10.0  # /models 조회
LLM_TEMPERATURE = 0.1      # 일관성 최대화
LLM_MAX_TOKENS = 1000
README_MAX_CHARS = 3000

# ── JSON 출력 스키마 ───────────────────────────────────────
README_EVAL_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "purpose_clarity": {
            "type": "object",
            "properties": {
                "score": {"type": "integer", "minimum": 1, "maximum": 5},
                "reason": {"type": "string", "maxLength": 150},
            },
            "required": ["score", "reason"],
        },
        "tech_description": {
            "type": "object",
            "properties": {
                "score": {"type": "integer", "minimum": 1, "maximum": 5},
                "reason": {"type": "string", "maxLength": 150},
            },
            "required": ["score", "reason"],
        },
        "setup_guide": {
            "type": "object",
            "properties": {
                "score": {"type": "integer", "minimum": 1, "maximum": 5},
                "reason": {"type": "string", "maxLength": 150},
            },
            "required": ["score", "reason"],
        },
        "visual_demo": {
            "type": "object",
            "properties": {
                "score": {"type": "integer", "minimum": 1, "maximum": 5},
                "reason": {"type": "string", "maxLength": 150},
            },
            "required": ["score", "reason"],
        },
        "overall_quality": {
            "type": "object",
            "properties": {
                "score": {"type": "integer", "minimum": 1, "maximum": 5},
                "tier": {"type": "string", "enum": ["양호", "보통", "미흡"]},
                "summary": {"type": "string", "maxLength": 200},
            },
            "required": ["score", "tier", "summary"],
        },
        "improvement_suggestions": {
            "type": "array",
            "items": {"type": "string", "maxLength": 150},
            "minItems": 2,
            "maxItems": 2,
        },
    },
    "required": [
        "purpose_clarity",
        "tech_description",
        "setup_guide",
        "visual_demo",
        "overall_quality",
        "improvement_suggestions",
    ],
}

# ── 시스템 프롬프트 ────────────────────────────────────────
SYSTEM_PROMPT = """You are a senior hiring manager evaluating GitHub README files for junior developer (0-3 years) portfolios.

Evaluate the README on 5 dimensions, each scored 1-5:

1. PURPOSE CLARITY
   1: Cannot tell what this project does
   2: Vague description, unclear problem/solution
   3: Basic description present but lacks context
   4: Clear purpose with problem statement
   5: Compelling problem definition + solution approach

2. TECH DESCRIPTION
   1: No technology mentioned
   2: Tech names listed without context
   3: Tech stack section exists with brief explanation
   4: Tech stack with selection rationale or architecture overview
   5: Detailed architecture + tech choices justified

3. SETUP GUIDE
   1: No setup instructions
   2: Partial commands, missing prerequisites
   3: Clone→install→run steps present but incomplete
   4: Complete reproducible setup guide
   5: One-command setup (Docker/script) with troubleshooting

4. VISUAL DEMO
   1: No visuals at all (no [screenshot:...] markers)
   2: One low-quality or irrelevant image
   3: Meaningful screenshot(s)
   4: Screenshots + GIF/video demo
   5: Rich visuals including architecture diagram + demo

5. OVERALL QUALITY
   Score = your holistic assessment (not necessarily the average).
   Tier is determined strictly by integer overall score:
     "양호": score 4 or 5
     "보통": score 3
     "미흡": score 1 or 2

DOMAIN ADJUSTMENTS:
- Game (Unity/Unreal/Godot): visual_demo is more important; gameplay GIF or screenshots can offset a weaker setup guide.
- ML/AI: model performance metrics (accuracy, F1, loss curves) are strong signals for tech_description and purpose_clarity.
- CLI tools: detailed usage examples with real commands can partially offset missing visual_demo.
- Mobile (React Native/Flutter): app UI screenshots are essential; judge setup_guide accounting for mobile build complexity.
- Data Analysis: charts, result tables, and Jupyter notebook usage count positively for visual_demo and tech_description.

CRITICAL RULES:
- Be calibrated for JUNIOR developers (0-3 years). Don't expect enterprise-level documentation.
- Boilerplate or auto-generated READMEs (CRA default, Copilot template with TODO placeholders, generic scaffold) must score 1-2.
- README written in Korean, English, or Japanese should be evaluated equally.
- **LANGUAGE REQUIREMENT: All string values in the JSON output (reason, summary, improvement_suggestions) MUST be written in natural Korean.**
- Respond ONLY in the specified JSON format. No markdown fences, no preamble.

CALIBRATION EXAMPLES:
- POOR (tier "미흡", score 2): README with only a title and a bullet list of tech names (React, Node.js). No purpose, no setup, no visuals.
- AVERAGE (tier "보통", score 3): README with a clear project description and tech stack section, partial setup steps (e.g. `npm install` only), and no screenshots.
- GOOD (tier "양호", score 4): README with a problem statement, architecture overview, complete Docker-based setup, and meaningful screenshots or GIF demo.

OUTPUT JSON MUST use exactly these keys (lowercase snake_case):
  "purpose_clarity", "tech_description", "setup_guide", "visual_demo" — each an object with "score" (1-5 int) and "reason" (short string in Korean).
  "overall_quality": object with "score" (1-5 int), "tier" ("양호"|"보통"|"미흡"), "summary" (string in Korean).
  "improvement_suggestions": array of exactly 2 actionable strings in Korean, specific to this project's domain."""

# ── 사용자 메시지 템플릿 ───────────────────────────────────
USER_PROMPT_TEMPLATE = """PROJECT CONTEXT:
- Primary languages: {languages}
- Detected domain: {domain}
- Detected signatures: {signatures}
- Repository type: {repo_type}
- Visual content: {has_screenshots}

README CONTENT (image URLs replaced with [screenshot: alt]):
---
{readme_clean}
---

Evaluate this README and respond in JSON."""


def _strip_markdown_json_fence(text: str) -> str:
    """Remove ``` or ```json fences from model output."""
    t = text.strip()
    m = re.match(
        r"^\s*```(?:json)?\s*\n?(.*?)\n?```\s*$",
        t,
        re.DOTALL | re.IGNORECASE,
    )
    if m:
        return m.group(1).strip()
    if t.startswith("```"):
        lines = t.split("\n")
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        return "\n".join(lines).strip()
    return t


def _extract_outer_json_object(text: str) -> Optional[str]:
    """Find first balanced {...} substring for models that add preamble."""
    start = text.find("{")
    if start < 0:
        return None
    depth = 0
    for i in range(start, len(text)):
        c = text[i]
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                return text[start : i + 1]
    return None


def _extract_result_dict_from_response(data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Parse README eval JSON from OpenAI-compatible chat completion body.
    Handles empty content, markdown fences, tool_calls.arguments, message.parsed.
    """
    choices = data.get("choices")
    if not isinstance(choices, list) or not choices:
        return None
    ch0 = choices[0]
    if not isinstance(ch0, dict):
        return None
    msg = ch0.get("message")
    if not isinstance(msg, dict):
        msg = {}

    parsed = msg.get("parsed")
    if isinstance(parsed, dict):
        return parsed

    tool_calls = msg.get("tool_calls")
    if isinstance(tool_calls, list) and tool_calls:
        tc0 = tool_calls[0]
        if isinstance(tc0, dict):
            fn = tc0.get("function")
            if isinstance(fn, dict):
                args = fn.get("arguments")
                if isinstance(args, str) and args.strip():
                    try:
                        obj = json.loads(args)
                        if isinstance(obj, dict):
                            return obj
                    except json.JSONDecodeError:
                        pass

    content = msg.get("content")
    if content is None:
        content = ""
    if not isinstance(content, str):
        content = str(content)

    stripped = _strip_markdown_json_fence(content)
    candidates: List[str] = []
    if stripped:
        candidates.append(stripped)
    outer = _extract_outer_json_object(stripped) if stripped else None
    if outer and outer not in candidates:
        candidates.append(outer)
    if content != stripped:
        outer2 = _extract_outer_json_object(content)
        if outer2 and outer2 not in candidates:
            candidates.append(outer2)

    for cand in candidates:
        if not cand:
            continue
        try:
            obj = json.loads(cand)
            if isinstance(obj, dict):
                return obj
        except json.JSONDecodeError:
            continue
    return None


def _norm_key(k: str) -> str:
    return k.strip().upper().replace(" ", "_").replace("-", "_")


def _lookup_ci(raw: Dict[str, Any], *names: str) -> Any:
    """Return value for first key that matches any of `names` (case-insensitive, spacing-tolerant)."""
    want = {_norm_key(n) for n in names}
    for k, v in raw.items():
        if isinstance(k, str) and _norm_key(k) in want:
            return v
    return None


def _tier_from_float(sc: float) -> str:
    if sc >= 4.0:
        return "양호"
    if sc >= 2.5:
        return "보통"
    return "미흡"


def _clamp_int_score(val: Any) -> int:
    try:
        if isinstance(val, bool):
            return 3
        f = float(val)
        return int(round(max(1.0, min(5.0, f))))
    except (TypeError, ValueError):
        return 3


def _coerce_dimension_block(val: Any) -> Dict[str, Any]:
    """purpose_clarity 등: 숫자만 오거나 {score, description} 형태 모두 수용."""
    if val is None:
        return {"score": 3, "reason": ""}
    if isinstance(val, (int, float)) and not isinstance(val, bool):
        return {"score": _clamp_int_score(val), "reason": ""}
    if isinstance(val, dict):
        sc = val.get("score")
        reason = (
            val.get("reason")
            or val.get("description")
            or val.get("detail")
            or ""
        )
        if sc is None:
            return {"score": 3, "reason": str(reason)[:150]}
        return {"score": _clamp_int_score(sc), "reason": str(reason)[:150]}
    return {"score": 3, "reason": str(val)[:150]}


def _coerce_overall_block(
    val: Any,
    tier_hint: Optional[str],
) -> Dict[str, Any]:
    """overall_quality: 중첩 dict | 숫자 단독 | 누락 폴백."""
    if isinstance(val, dict):
        sc = val.get("score")
        tier = (
            val.get("tier")
            or val.get("TIER")
        )
        summary = (
            val.get("summary")
            or val.get("SUMMARY")
            or ""
        )
        if not isinstance(tier, str) or tier not in ("양호", "보통", "미흡"):
            try:
                sc_f = float(sc) if sc is not None else 3.0
            except (TypeError, ValueError):
                sc_f = 3.0
            tier = (
                tier_hint
                if tier_hint in ("양호", "보통", "미흡")
                else _tier_from_float(sc_f)
            )
        try:
            sc_i = _clamp_int_score(sc) if sc is not None else 3
        except Exception:
            sc_i = 3
        return {
            "score": sc_i,
            "tier": tier if tier in ("양호", "보통", "미흡") else "보통",
            "summary": str(summary)[:200],
        }
    if isinstance(val, (int, float)) and not isinstance(val, bool):
        sc_f = float(val)
        tier = (
            tier_hint
            if tier_hint in ("양호", "보통", "미흡")
            else _tier_from_float(sc_f)
        )
        return {
            "score": _clamp_int_score(val),
            "tier": tier,
            "summary": "",
        }
    if tier_hint in ("양호", "보통", "미흡"):
        return {"score": 3, "tier": tier_hint, "summary": ""}
    return {"score": 3, "tier": "보통", "summary": ""}


def _canonicalize_llm_raw_dict(raw: Dict[str, Any]) -> Dict[str, Any]:
    """
    모델이 UPPER_CASE 키, description 필드, 플랫 점수, TIER 분리 등으로 줄 때
    portfolio / 검증기가 기대하는 스키마로 통일.
    """
    if not isinstance(raw, dict):
        return {}

    out: Dict[str, Any] = {}

    for up_name, canon in (
        ("PURPOSE_CLARITY", "purpose_clarity"),
        ("TECH_DESCRIPTION", "tech_description"),
        ("SETUP_GUIDE", "setup_guide"),
        ("VISUAL_DEMO", "visual_demo"),
    ):
        v = _lookup_ci(raw, up_name, canon)
        if v is not None:
            out[canon] = _coerce_dimension_block(v)

    tier_hint: Optional[str] = None
    t_raw = _lookup_ci(raw, "TIER", "tier")
    if isinstance(t_raw, str):
        s = t_raw.strip()
        if s in ("양호", "보통", "미흡"):
            tier_hint = s

    oq_val = _lookup_ci(raw, "OVERALL_QUALITY", "overall_quality")
    out["overall_quality"] = _coerce_overall_block(oq_val, tier_hint)

    sugg = _lookup_ci(raw, "IMPROVEMENT_SUGGESTIONS", "improvement_suggestions")
    if isinstance(sugg, list):
        items = [str(x)[:150] for x in sugg if x is not None and str(x).strip()]
        if not items:
            items = [
                "README에 설치·실행 절차를 단계별로 추가하세요.",
                "스크린샷 또는 데모 링크를 추가하세요.",
            ]
        elif len(items) == 1:
            items = [items[0], items[0]]
        else:
            items = items[:2]
        out["improvement_suggestions"] = items
    elif sugg is not None:
        s1 = str(sugg)[:150]
        out["improvement_suggestions"] = [s1, s1]
    else:
        out["improvement_suggestions"] = [
            "README에 설치·실행 절차를 단계별로 추가하세요.",
            "스크린샷 또는 데모 링크를 추가하세요.",
        ]

    for canon in ("purpose_clarity", "tech_description", "setup_guide", "visual_demo"):
        if canon not in out:
            out[canon] = {"score": 3, "reason": ""}

    return out


def _normalize_llm_result_dict(result: Dict[str, Any]) -> Dict[str, Any]:
    """Round float scores to int 1-5 for schema compatibility."""
    out: Dict[str, Any] = dict(result)
    for key in ("purpose_clarity", "tech_description", "setup_guide", "visual_demo"):
        dim = out.get(key)
        if isinstance(dim, dict) and "score" in dim:
            s = dim["score"]
            if isinstance(s, float):
                nd = dict(dim)
                nd["score"] = int(round(max(1.0, min(5.0, s))))
                out[key] = nd
            elif isinstance(s, bool):
                pass
            elif isinstance(s, int) and not (1 <= s <= 5):
                nd = dict(dim)
                nd["score"] = max(1, min(5, s))
                out[key] = nd
    oq = out.get("overall_quality")
    if isinstance(oq, dict) and "score" in oq:
        s = oq["score"]
        if isinstance(s, float):
            nd = dict(oq)
            nd["score"] = int(round(max(1.0, min(5.0, s))))
            out["overall_quality"] = nd
        elif isinstance(s, int) and not (1 <= s <= 5):
            nd = dict(oq)
            nd["score"] = max(1, min(5, s))
            out["overall_quality"] = nd
    return out


def _log_completion_debug(data: Any) -> None:
    try:
        choices = data.get("choices")
        if isinstance(choices, list) and choices:
            ch0 = choices[0]
            fr = ch0.get("finish_reason") if isinstance(ch0, dict) else None
            msg = ch0.get("message", {}) if isinstance(ch0, dict) else {}
            c_len = len((msg.get("content") or "")) if isinstance(msg, dict) else 0
            preview = repr((msg.get("content") or "")[:350]) if isinstance(msg, dict) else ""
            keys = list(msg.keys()) if isinstance(msg, dict) else []
            logger.warning(
                "LLM 응답 디버그: finish_reason=%s content_len=%s msg_keys=%s preview=%s",
                fr, c_len, keys, preview,
            )
        else:
            logger.warning("LLM 응답 디버그: choices 없음 keys=%s", list(data.keys()) if isinstance(data, dict) else type(data))
    except Exception as e:
        logger.warning("LLM 응답 디버그 로깅 실패: %s", e)


def _validate_llm_result(result: Any) -> bool:
    """LLM 출력이 스키마에 맞는지 최소 검증 (정규화 후 호출 권장)."""
    if not isinstance(result, dict):
        return False
    try:
        overall = result.get("overall_quality", {})
        if overall.get("tier") not in ("양호", "보통", "미흡"):
            return False
        os_ = overall.get("score", 0)
        if not (isinstance(os_, (int, float)) and 1 <= float(os_) <= 5):
            return False
        for key in ("purpose_clarity", "tech_description", "setup_guide", "visual_demo"):
            dim = result.get(key, {})
            ds = dim.get("score", 0)
            if not (isinstance(ds, (int, float)) and 1 <= float(ds) <= 5):
                return False
        suggestions = result.get("improvement_suggestions", [])
        if not isinstance(suggestions, list) or len(suggestions) < 1:
            return False
        return True
    except Exception:
        return False


class ReadmeEvaluator:
    """vLLM 서버와 통신하는 README 평가기."""

    def __init__(
        self,
        base_url: str = LLM_BASE_URL,
        model: str = LLM_MODEL,
        timeout: float = LLM_TIMEOUT,
    ) -> None:
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
                    timeout=aiohttp.ClientTimeout(total=HEALTH_CHECK_TIMEOUT),
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
            return None

        prompt = self._build_prompt(readme_raw, meta)

        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ]

        async def _post_completion(
            session: aiohttp.ClientSession,
            use_guided_json: bool,
        ) -> Optional[Dict[str, Any]]:
            body: Dict[str, Any] = {
                "model": self.model,
                "messages": messages,
                "temperature": LLM_TEMPERATURE,
                "max_tokens": LLM_MAX_TOKENS,
            }
            if use_guided_json:
                body["guided_json"] = README_EVAL_SCHEMA
            async with session.post(
                f"{self.base_url}/chat/completions",
                json=body,
                timeout=aiohttp.ClientTimeout(total=self.timeout),
            ) as resp:
                if resp.status != 200:
                    err_text = await resp.text()
                    logger.warning(
                        "LLM 응답 오류: HTTP %s body=%s",
                        resp.status,
                        (err_text or "")[:500],
                    )
                    return None
                return await resp.json()

        def _parse_and_validate(data: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
            if not data:
                return None
            raw = _extract_result_dict_from_response(data)
            if raw is None:
                return None
            canon = _canonicalize_llm_raw_dict(raw)
            normalized = _normalize_llm_result_dict(canon)
            if _validate_llm_result(normalized):
                return normalized
            logger.warning(
                "LLM 출력 스키마 검증 실패 (샘플 키): %s",
                list(normalized.keys()) if isinstance(normalized, dict) else normalized,
            )
            return None

        try:
            async with aiohttp.ClientSession() as session:
                data = await _post_completion(session, use_guided_json=True)
                out = _parse_and_validate(data)
                if out is not None:
                    return out
                if data is not None:
                    _log_completion_debug(data)

                data_fb = await _post_completion(session, use_guided_json=False)
                out_fb = _parse_and_validate(data_fb)
                if out_fb is not None:
                    return out_fb
                if data_fb is not None:
                    _log_completion_debug(data_fb)

            return None

        except asyncio.TimeoutError:
            logger.warning("LLM 타임아웃 (%.1f초 초과)", self.timeout)
            return None
        except (KeyError, IndexError, TypeError) as e:
            logger.warning("LLM 응답 파싱 실패 (구조): %s", e)
            return None
        except json.JSONDecodeError as e:
            logger.warning("LLM 응답 파싱 실패: %s", e)
            return None
        except Exception as e:
            logger.warning("LLM 호출 예외: %s", e)
            return None

    def _build_prompt(self, readme_raw: str, meta: Dict[str, Any]) -> str:
        """사용자 메시지 조립. 이미지 URL을 placeholder로 치환해 토큰을 절약한다."""
        truncated = readme_raw[:README_MAX_CHARS]

        # 이미지 링크 ![alt](url) → [screenshot: alt] 로 치환 후 개수 카운트
        img_pattern = re.compile(r'!\[([^\]]*)\]\([^)]*\)')
        imgs = img_pattern.findall(truncated)
        readme_clean = img_pattern.sub(
            lambda m: f"[screenshot: {m.group(1)}]" if m.group(1).strip() else "[screenshot]",
            truncated,
        )
        has_screenshots = (
            f"yes ({len(imgs)} image(s) detected)" if imgs else "none detected"
        )

        lang_stats = meta.get("languages", {})
        sorted_langs = sorted(lang_stats.items(), key=lambda x: x[1], reverse=True)[:3]
        lang_str = (
            ", ".join(f"{k} {v}%" for k, v in sorted_langs)
            if sorted_langs
            else "Unknown"
        )

        sigs: List[str] = meta.get("signatures", [])
        sig_str = ", ".join(sigs[:5]) if sigs else "None detected"

        return USER_PROMPT_TEMPLATE.format(
            languages=lang_str,
            domain=meta.get("domain", "Unknown"),
            signatures=sig_str,
            repo_type=meta.get("repo_type", "personal"),
            has_screenshots=has_screenshots,
            readme_clean=readme_clean,
        )
