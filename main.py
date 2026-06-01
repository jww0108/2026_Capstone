"""
Git2Value — FastAPI 백엔드 게이트웨이 (v7.0+).

제공 엔드포인트:
  GET  /health                   vLLM 연결 상태 확인
  POST /v1/readme/evaluate       README LLM 평가 (JSON body)
  POST /v1/readme/evaluate/file  README 파일 업로드 평가
  POST /v1/readme/evaluate/url   GitHub URL 평가
  POST /v1/analyze               E2E GitHub 포트폴리오 분석

실행:
    uvicorn main:app --host 0.0.0.0 --port 8080

환경변수:
    VLLM_BASE_URL   기본 http://localhost:8000/v1
    LLM_MODEL       기본값은 llm_readme_evaluator.LLM_MODEL
    HOST, PORT      __main__ 실행 시 (기본 0.0.0.0:8080)
"""
from __future__ import annotations

import logging
import os
import re
import time
import urllib.request
from contextlib import asynccontextmanager
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from llm_readme_evaluator import LLM_BASE_URL, LLM_MODEL, ReadmeEvaluator
from run_git2value import Git2ValuePipeline

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

_DEFAULT_PORT = 8080
README_RAW_MAX_LEN = 50_000
HEALTH_CACHE_TTL = 60.0


def _vllm_base_url() -> str:
    return os.getenv("VLLM_BASE_URL", LLM_BASE_URL).rstrip("/")


def _llm_model() -> str:
    return os.getenv("LLM_MODEL", LLM_MODEL)


# ---------------------------------------------------------------------------
# 앱 수준 싱글톤 evaluator + TTL 기반 health 캐시
# ---------------------------------------------------------------------------

_evaluator: Optional[ReadmeEvaluator] = None
_health_checked_at: float = 0.0
_pipeline: Optional[Git2ValuePipeline] = None


def _get_evaluator() -> ReadmeEvaluator:
    global _evaluator
    if _evaluator is None:
        _evaluator = ReadmeEvaluator(
            base_url=_vllm_base_url(), model=_llm_model(),
        )
    return _evaluator


async def _check_health(force: bool = False) -> bool:
    """health_check 결과를 TTL(60초) 동안 캐시. force=True면 즉시 재확인."""
    global _health_checked_at
    ev = _get_evaluator()
    now = time.monotonic()
    if force or (now - _health_checked_at) > HEALTH_CACHE_TTL:
        ev._available = None
        result = await ev.health_check()
        _health_checked_at = now
        return result
    return ev._available if ev._available is not None else False


# ---------------------------------------------------------------------------
# 입력 검증 패턴 (analyze 엔드포인트용)
# ---------------------------------------------------------------------------

_GITHUB_USERNAME_RE = re.compile(r"^[a-zA-Z0-9\-]{1,39}$")
_GITHUB_REPO_RE = re.compile(
    r"^[a-zA-Z0-9_.\-]+/[a-zA-Z0-9_.\-]+"  # user/repo
    r"(/tree/[a-zA-Z0-9_./\-]+)?$"           # optional /tree/branch
)


# ---------------------------------------------------------------------------
# 스키마
# ---------------------------------------------------------------------------

class ReadmeMeta(BaseModel):
    languages: Dict[str, float] = Field(default_factory=dict)
    domain: str = "Unknown"
    signatures: List[str] = Field(default_factory=list)
    repo_type: str = "personal"


class EvaluateReadmeRequest(BaseModel):
    readme_raw: str = Field(
        ...,
        max_length=README_RAW_MAX_LEN,
        description="README 원문(마크다운)",
    )
    meta: ReadmeMeta = Field(default_factory=ReadmeMeta)


class EvaluateReadmeResponse(BaseModel):
    ok: bool
    result: Optional[Dict[str, Any]] = None


class EvaluateWithSourceResponse(BaseModel):
    ok: bool
    readme_raw: str
    char_count: int
    result: Optional[Dict[str, Any]] = None


class HealthResponse(BaseModel):
    status: str = "ok"
    vllm_reachable: bool
    vllm_base_url: str
    model: str


class AnalyzeRequest(BaseModel):
    github_username: str = Field(..., description="GitHub 사용자명 (영문/숫자/-)")
    repos: List[str] = Field(
        ...,
        min_length=1,
        description="분석할 레포 경로 목록 (최대 3개). 예: ['user/repo', 'user/repo2/tree/branch']",
    )
    applicant_years: Optional[int] = Field(default=0, ge=0, description="경력 년수 (신입=0)")


class AnalyzeResponse(BaseModel):
    status: str = Field(..., description="요청 처리 상태: success 또는 error")
    error: Optional[str] = Field(default=None, description="오류 메시지 (status=error일 때)")
    github_score: Optional[Dict[str, Any]] = Field(
        default=None,
        description=(
            "GitHub 포트폴리오 종합 점수. "
            "breakdown(60/30/10), axes, score_detail 포함. "
            "commit_activity 항목에는 commit_quality_factor/보정 전후 점수가 포함될 수 있음."
        ),
    )
    per_repo: Optional[List[Dict[str, Any]]] = Field(
        default=None,
        description=(
            "레포별 진단/점수 상세. "
            "score_breakdown과 score_detail(세부 항목/만점/개선 여지), "
            "diagnosis.extra_items.growth_signal, README 문서 근거 진단을 포함할 수 있음."
        ),
    )
    level: Optional[Dict[str, Any]] = Field(
        default=None,
        description=(
            "Portfolio Tier 정보. "
            "기존 grade/description + tier_label/tier_context/primary_domain_tier/caveat 포함."
        ),
    )
    summary: Optional[Dict[str, Any]] = Field(
        default=None,
        description="종합 분석 텍스트와 강점/개선 항목 요약.",
    )
    job_matching: Optional[Dict[str, Any]] = Field(
        default=None,
        description="주요 직무 매칭 결과(FAISS + 도메인 리랭킹).",
    )
    salary_band: Optional[Dict[str, Any]] = Field(
        default=None,
        description="시장 연봉 밴드(점수 미반영, 참고용).",
    )
    tech_analysis: Optional[Dict[str, Any]] = Field(
        default=None,
        description="보유 기술과 공고 요구 기술 간 매칭 분석.",
    )
    meta: Optional[Dict[str, Any]] = Field(
        default=None,
        description="버전/분석 시간/LLM 가용 여부 등 메타 정보.",
    )


# ---------------------------------------------------------------------------
# 앱 + lifespan
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(application: FastAPI):
    global _pipeline
    # README LLM 게이트웨이 health check
    reachable = await _check_health(force=True)
    logger.info(
        "vLLM %s (%s) — %s",
        _vllm_base_url(),
        _llm_model(),
        "연결 성공" if reachable else "연결 실패 (요청 시 재시도)",
    )
    # E2E 파이프라인 싱글톤 초기화 (FAISS, 임베딩 모델, 캐시 1회 로드)
    try:
        _pipeline = Git2ValuePipeline()
        await _pipeline.check_llm()
        logger.info(
            "Git2ValuePipeline 초기화 완료 — LLM %s",
            "가용" if _pipeline.llm_available else "미가용",
        )
    except Exception as exc:
        logger.warning("Git2ValuePipeline 초기화 실패: %s (analyze 엔드포인트 비활성)", exc)
        _pipeline = None
    yield


app = FastAPI(
    title="Git2Value LLM Gateway",
    description="로컬 vLLM 서버에 연결해 README 품질 평가를 제공합니다.",
    version="1.0.0",
    lifespan=lifespan,
)

_CORS_ORIGINS = [
    origin.strip()
    for origin in os.getenv("CORS_ORIGINS", "").split(",")
    if origin.strip()
] or [
    "https://git2value.vercel.app",   # 프론트 배포 도메인 (수정 필요)
    "http://localhost:3000",           # Vite/React 로컬
    "http://localhost:5173",           # Vite 기본 포트
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# 엔드포인트
# ---------------------------------------------------------------------------

@app.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    reachable = await _check_health(force=True)
    return HealthResponse(
        vllm_reachable=reachable,
        vllm_base_url=_vllm_base_url(),
        model=_llm_model(),
    )


@app.post("/v1/readme/evaluate", response_model=EvaluateReadmeResponse)
async def evaluate_readme(body: EvaluateReadmeRequest) -> EvaluateReadmeResponse:
    if not body.readme_raw or len(body.readme_raw.strip()) < 50:
        raise HTTPException(
            status_code=422,
            detail="README가 50자 미만이어서 평가할 수 없습니다.",
        )

    if not await _check_health():
        raise HTTPException(
            status_code=503,
            detail="vLLM 서버에 연결할 수 없습니다. VLLM_BASE_URL과 서버 실행 여부를 확인하세요.",
        )

    ev = _get_evaluator()
    result = await ev.evaluate(body.readme_raw, body.meta.model_dump())
    if result is None:
        raise HTTPException(
            status_code=502,
            detail="LLM 평가 실패 — 타임아웃·HTTP 오류·JSON 파싱/스키마 불일치 중 하나입니다.",
        )
    return EvaluateReadmeResponse(ok=True, result=result)


# ---------------------------------------------------------------------------
# 유틸 — 파일/URL 엔드포인트 공용
# ---------------------------------------------------------------------------

def _parse_langs_str(raw: str) -> Dict[str, float]:
    """'Python 85,TypeScript 15' → {"Python": 85.0, ...}"""
    result: Dict[str, float] = {}
    for part in raw.split(","):
        tokens = part.strip().rsplit(" ", 1)
        if len(tokens) == 2:
            try:
                result[tokens[0].strip()] = float(tokens[1])
            except ValueError:
                pass
    return result


def _to_github_raw_url(url: str) -> str:
    """github.com/user/repo/blob/branch/README.md
       → raw.githubusercontent.com/user/repo/branch/README.md"""
    url = url.strip()
    if "raw.githubusercontent.com" in url:
        return url
    url = url.replace("github.com", "raw.githubusercontent.com")
    url = url.replace("/blob/", "/")
    return url


def _fetch_url_text(url: str) -> str:
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "git2value/1.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            return resp.read().decode("utf-8", errors="ignore")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"URL에서 README를 가져올 수 없습니다: {e}")


async def _run_evaluate(readme_raw: str, meta: dict) -> "EvaluateWithSourceResponse":
    """공통 평가 로직 — 파일/URL 엔드포인트에서 재사용."""
    readme_raw = readme_raw.strip()
    if len(readme_raw) < 50:
        raise HTTPException(status_code=422, detail="README가 50자 미만이어서 평가할 수 없습니다.")
    if len(readme_raw) > README_RAW_MAX_LEN:
        readme_raw = readme_raw[:README_RAW_MAX_LEN]

    if not await _check_health():
        raise HTTPException(
            status_code=503,
            detail="vLLM 서버에 연결할 수 없습니다. VLLM_BASE_URL과 서버 실행 여부를 확인하세요.",
        )

    ev = _get_evaluator()
    result = await ev.evaluate(readme_raw, meta)
    if result is None:
        raise HTTPException(
            status_code=502,
            detail="LLM 평가 실패 — 타임아웃·HTTP 오류·JSON 파싱/스키마 불일치 중 하나입니다.",
        )
    return EvaluateWithSourceResponse(
        ok=True,
        readme_raw=readme_raw,
        char_count=len(readme_raw),
        result=result,
    )


# ---------------------------------------------------------------------------
# 파일 업로드 / URL 엔드포인트
# ---------------------------------------------------------------------------

@app.post(
    "/v1/readme/evaluate/file",
    response_model=EvaluateWithSourceResponse,
    summary="README 파일 업로드 → LLM 평가",
)
async def evaluate_readme_file(
    file: UploadFile = File(..., description="README.md 파일"),
    domain: str = Form(default="Unknown", description="예: 서버/백엔드, 프론트엔드, 인공지능/머신러닝"),
    repo_type: str = Form(default="personal", description="personal 또는 team"),
    signatures: str = Form(default="", description="주요 프레임워크 (쉼표 구분, 예: FastAPI,Docker)"),
    langs: str = Form(default="", description="언어 비중 (예: Python 85,TypeScript 15)"),
) -> EvaluateWithSourceResponse:
    content = await file.read()
    readme_raw = content.decode("utf-8", errors="ignore")
    meta = {
        "domain": domain,
        "repo_type": repo_type,
        "signatures": [s.strip() for s in signatures.split(",") if s.strip()],
        "languages": _parse_langs_str(langs),
    }
    return await _run_evaluate(readme_raw, meta)


@app.post(
    "/v1/readme/evaluate/url",
    response_model=EvaluateWithSourceResponse,
    summary="GitHub URL → LLM 평가",
)
async def evaluate_readme_url(
    url: str = Form(..., description="GitHub README URL (blob 또는 raw 모두 가능)"),
    domain: str = Form(default="Unknown", description="예: 서버/백엔드, 프론트엔드, 인공지능/머신러닝"),
    repo_type: str = Form(default="personal", description="personal 또는 team"),
    signatures: str = Form(default="", description="주요 프레임워크 (쉼표 구분, 예: FastAPI,Docker)"),
    langs: str = Form(default="", description="언어 비중 (예: Python 85,TypeScript 15)"),
) -> EvaluateWithSourceResponse:
    raw_url = _to_github_raw_url(url)
    readme_raw = _fetch_url_text(raw_url)
    meta = {
        "domain": domain,
        "repo_type": repo_type,
        "signatures": [s.strip() for s in signatures.split(",") if s.strip()],
        "languages": _parse_langs_str(langs),
    }
    return await _run_evaluate(readme_raw, meta)


# ---------------------------------------------------------------------------
# E2E 분석 엔드포인트
# ---------------------------------------------------------------------------

@app.post(
    "/v1/analyze",
    response_model=AnalyzeResponse,
    summary="GitHub 포트폴리오 E2E 분석",
    description=(
        "GitHub 사용자명과 레포 URL 목록을 받아 "
        "GitHub 포트폴리오 해석·진단 / 주요 직무 매칭 / 시장 연봉 밴드를 JSON으로 반환. "
        "점수는 개발자 합불 판정이 아니라 공개 포트폴리오 신호 기준이며, "
        "github_score.axes와 per_repo[].score_detail로 세부 근거를 확인할 수 있습니다. "
        "커밋 항목은 commit_quality_factor가 반영된 값이며, 성장성(growth_signal)·문서화 근거는 진단 항목으로 제공됩니다."
    ),
)
async def analyze(req: AnalyzeRequest) -> AnalyzeResponse:
    # 파이프라인 준비 확인
    if _pipeline is None:
        raise HTTPException(
            status_code=503,
            detail="분석 파이프라인이 초기화되지 않았습니다. 서버 로그를 확인하세요.",
        )

    # 입력 검증
    if not _GITHUB_USERNAME_RE.match(req.github_username):
        raise HTTPException(status_code=400, detail="유효하지 않은 GitHub 사용자명입니다.")
    if len(req.repos) == 0:
        raise HTTPException(status_code=400, detail="최소 1개 레포를 입력하세요.")
    if len(req.repos) > 3:
        raise HTTPException(status_code=400, detail="최대 3개 레포까지 분석 가능합니다.")
    for repo in req.repos:
        if not _GITHUB_REPO_RE.match(repo):
            raise HTTPException(status_code=400, detail=f"유효하지 않은 레포 경로: {repo}")

    start = time.monotonic()
    result = await _pipeline.analyze(
        username=req.github_username,
        repos=req.repos,
        applicant_years=req.applicant_years or 0,
    )

    if result.get("status") == "error":
        raise HTTPException(status_code=500, detail=result.get("error", "분석 실패"))

    # _internal 키 제거 후 반환 (내부 데이터는 API에 노출하지 않음)
    result.pop("_internal", None)
    if result.get("meta"):
        result["meta"]["analysis_time_seconds"] = round(time.monotonic() - start, 1)

    return AnalyzeResponse(**result)


if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("PORT", str(_DEFAULT_PORT)))
    uvicorn.run(
        "main:app",
        host=os.getenv("HOST", "0.0.0.0"),
        port=port,
        reload=os.getenv("UVICORN_RELOAD", "").lower() in ("1", "true", "yes"),
    )
