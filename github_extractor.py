import os
import re
import math
import base64
import asyncio
import aiohttp
import logging
import statistics
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple, Set
from urllib.parse import quote
from dotenv import load_dotenv

import profile_builder

load_dotenv()
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# v5.5: 커밋 기반 LOC 중 소스 코드가 아니지만 기여 증거로 인정하는 확장자
CONTRIBUTION_EVIDENCE_EXTENSIONS: Set[str] = {
    ".json",
    ".yml",
    ".yaml",
    ".md",
    ".txt",
    ".csv",
    ".tf",
    ".hcl",
    ".proto",
    ".sql",
}

# Sentinel for hard API failures after retries
def _is_hard_api_error(obj: Any) -> bool:
    return isinstance(obj, dict) and obj.get("__error__") is True


class GitHubExtractor:
    """
    [Git2Value Core Extractor v5.5]
    GitHub API 기반 역량 추출, Rate limit 대응, 균등 커밋 샘플링, score_breakdown.
    v5.0: Contribution 로그 스케일, Quality 10+10+10(활성 주), Consistency는 전체 커밋 목록 기준.
    v5.4: 트리 시그니처 기반 엔진 감지(profile_builder.detect_engine_signatures) → frameworks.
    v5.5: 커밋 수 기반 동적 가중치(LOC/commit), Evidence LOC 보조 점수(설정·데이터 기여 보정).
    """

    # author 커밋 목록 페이지네이션 상한 (per_page=100 × 3 = 최대 300커밋)
    MAX_COMMIT_PAGES = 3

    def __init__(self, token: Optional[str] = None):
        self.token = token or os.getenv("Github_api_token")
        self.headers = {
            "Accept": "application/vnd.github.v3+json",
            "Authorization": f"token {self.token}" if self.token else ""
        }
        self.base_url = "https://api.github.com"

        self.ignore_extensions = {
            '.json', '.csv', '.lock', '.md', '.txt', '.meta', '.yml', '.yaml', '.xml',
            '.unity', '.prefab', '.asset', '.mat', '.controller', '.csproj', '.sln', '.pdf',
            '.zip', '.tar.gz', '.exe', '.dll', '.bin', '.iso', '.psd', '.ai', '.sketch', '.fig', '.xd',
            '.mp4', '.avi', '.mov', '.mkv', '.mp3', '.wav', '.flac', '.woff', '.woff2', '.ttf', '.otf',
            # v5.5: 스키마/IaC 등은 유효 소스 LOC 대신 evidence_loc로만 집계
            '.tf', '.hcl', '.proto', '.sql',
        }
        self.ignore_paths = {
            'node_modules/', 'vendor/', 'dist/', 'build/', 'assets/plugins/', '.git/',
            '__pycache__/', 'generated/', 'obj/', 'bin/', '.next/', 'migrations/',
        }

        self.ext_to_lang = {
            '.cs': 'C#', '.py': 'Python', '.js': 'JavaScript', '.ts': 'TypeScript',
            '.java': 'Java', '.cpp': 'C++', '.c': 'C', '.go': 'Go', '.rb': 'Ruby',
            '.php': 'PHP', '.swift': 'Swift', '.kt': 'Kotlin', '.dart': 'Dart',
            '.html': 'HTML', '.css': 'CSS'
        }

    @staticmethod
    def _parse_rel_link(link_header: Optional[str], rel: str) -> Optional[str]:
        if not link_header:
            return None
        for part in link_header.split(","):
            if f'rel="{rel}"' in part or f"rel='{rel}'" in part:
                m = re.search(r"<([^>]+)>", part.strip())
                if m:
                    return m.group(1).strip()
        return None

    async def _fetch_with_retry(
        self, session: aiohttp.ClientSession, url: str
    ) -> Tuple[bool, Any, str]:
        """
        Returns (http_200_ok, json_body_or_sentinel, link_header).
        On hard failure after retries: ok=False, body={"__error__": True, "url": url}.
        On non-retryable non-200: ok=False, body={} or parsed error JSON.
        """
        last_link = ""
        for attempt in range(3):
            try:
                async with session.get(url, headers=self.headers) as response:
                    last_link = response.headers.get("Link") or ""
                    if response.status == 200:
                        return True, await response.json(), last_link
                    if response.status in (403, 429):
                        ra_hdr = response.headers.get("Retry-After")
                        if ra_hdr is not None:
                            try:
                                wait_s = int(float(ra_hdr))
                            except ValueError:
                                wait_s = 2 ** attempt
                        else:
                            wait_s = 2 ** attempt
                        logging.warning(
                            "HTTP %s on %s — retry %s/%s after %ss",
                            response.status, url, attempt + 1, 3, wait_s,
                        )
                        await asyncio.sleep(wait_s)
                        continue
                    try:
                        body = await response.json()
                    except Exception:
                        body = {}
                    return False, body, last_link
            except Exception as e:
                logging.error("Network error on %s (attempt %s): %s", url, attempt + 1, e)
                if attempt < 2:
                    await asyncio.sleep(2 ** attempt)
                else:
                    logging.error("Max retries exceeded for %s", url)
                    return False, {"__error__": True, "url": url, "reason": str(e)}, ""
        logging.error("Max retries exceeded (403/429) for %s", url)
        return False, {"__error__": True, "url": url}, ""

    async def _fetch_all_commits_paginated(
        self, session: aiohttp.ClientSession, first_url: str
    ) -> Tuple[List[Dict[str, Any]], bool]:
        """Returns (commits, hard_error). hard_error True if __error__ encountered."""
        all_commits: List[Dict[str, Any]] = []
        next_url: Optional[str] = first_url
        pages_fetched = 0
        while next_url and pages_fetched < self.MAX_COMMIT_PAGES:
            ok, data, link = await self._fetch_with_retry(session, next_url)
            if not ok:
                if _is_hard_api_error(data):
                    return all_commits, True
                break
            if not isinstance(data, list):
                break
            all_commits.extend(data)
            pages_fetched += 1
            next_url = self._parse_rel_link(link, "next")
        return all_commits, False

    async def _fetch_repo_text_files(
        self,
        session: aiohttp.ClientSession,
        repo_url: str,
        ref: str,
        paths: List[str],
    ) -> Dict[str, str]:
        """의존성 파일 등 작은 텍스트 blob을 contents API로 조회."""
        out: Dict[str, str] = {}
        ref_q = quote(ref, safe="")
        for rel in paths:
            enc_path = "/".join(quote(seg, safe="") for seg in rel.split("/"))
            url = f"{repo_url}/contents/{enc_path}?ref={ref_q}"
            ok, data, _ = await self._fetch_with_retry(session, url)
            if not ok or not isinstance(data, dict) or _is_hard_api_error(data):
                continue
            if data.get("encoding") != "base64" or not data.get("content"):
                continue
            try:
                raw = base64.b64decode(data["content"]).decode("utf-8", errors="ignore")
                if len(raw) > 80000:
                    raw = raw[:80000]
                out[rel] = raw
            except Exception:
                continue
        return out

    def _clean_markdown(self, text: str) -> str:
        if not text:
            return ""
        boilerplate_patterns = [
            r"This project was bootstrapped with.*?\.",
            r"Available Scripts.*?npm start",
            r"Getting Started with.*?guide\.",
            r"Learn More.*?React documentation\."
        ]
        for pattern in boilerplate_patterns:
            text = re.sub(pattern, '', text, flags=re.IGNORECASE | re.DOTALL)
        text = re.sub(r'!\[.*?\]\(.*?\)', '', text)
        text = re.sub(r'\[!\[.*?\]\(.*?\)\]\(.*?\)', '', text)
        text = re.sub(r'<[^>]+>', '', text)
        text = re.sub(r'#+\s*', '', text)
        text = re.sub(r'\s+', ' ', text).strip()
        return text[:1500]

    def _is_valid_source_code(self, filename: str) -> bool:
        lower_name = filename.lower()
        if any(path in lower_name for path in self.ignore_paths):
            return False
        ext = os.path.splitext(lower_name)[1]
        if ext in self.ignore_extensions:
            return False
        return True

    def _is_contribution_evidence(self, filename: str) -> bool:
        """LOC 계산에서는 제외되지만 기여 증거로 인정되는 커밋 파일 (v5.5)."""
        lower_name = filename.lower()
        if any(path in lower_name for path in self.ignore_paths):
            return False
        if lower_name.endswith("dockerfile"):
            return True
        ext = os.path.splitext(lower_name)[1]
        return ext in CONTRIBUTION_EVIDENCE_EXTENSIONS

    def _stratified_sample_commits(
        self, all_commits: List[Dict[str, Any]], global_seen_sha: Set[str]
    ) -> List[Dict[str, Any]]:
        """초기/중간/최근 구간에서 최대 25개씩, SHA dedup (레포 내부 + 전역)."""
        if not all_commits:
            return []
        total = len(all_commits)
        early = all_commits[:25]
        mid_lo = max(0, total // 2 - 12)
        mid_hi = min(total, total // 2 + 13)
        mid = all_commits[mid_lo:mid_hi]
        recent = all_commits[-25:] if total > 0 else []

        seen_local: Set[str] = set()
        sampled: List[Dict[str, Any]] = []
        for c in early + mid + recent:
            sha = c.get("sha")
            if not sha or sha in seen_local or sha in global_seen_sha:
                continue
            seen_local.add(sha)
            sampled.append(c)
        return sampled

    def _commit_timestamp(self, commit_obj: Dict[str, Any]) -> Optional[datetime]:
        try:
            c = commit_obj.get("commit") or {}
            auth = c.get("author") or c.get("committer") or {}
            ds = auth.get("date")
            if not ds:
                return None
            return datetime.strptime(ds[:19], "%Y-%m-%dT%H:%M:%S")
        except Exception:
            return None

    def _count_active_weeks(self, commits: List[Dict[str, Any]]) -> int:
        """author 커밋 목록 기준, 커밋이 1건 이상 있는 ISO 캘린더 주(년+주차) 개수."""
        weeks: Set[Tuple[int, int]] = set()
        for c in commits:
            t = self._commit_timestamp(c)
            if t:
                y, w, _ = t.isocalendar()
                weeks.add((y, w))
        return len(weeks)

    def _calc_consistency_score(self, commit_objects: List[Dict[str, Any]]) -> float:
        """max(0, 10 - std * 0.5); 커밋 수 < 5면 0."""
        if len(commit_objects) < 5:
            return 0.0
        times: List[datetime] = []
        for o in commit_objects:
            t = self._commit_timestamp(o)
            if t:
                times.append(t)
        if len(times) < 5:
            return 0.0
        times.sort()
        deltas = [(times[i + 1] - times[i]).days for i in range(len(times) - 1)]
        if len(deltas) < 2:
            std = 0.0
        else:
            std = float(statistics.pstdev(deltas))
        return round(max(0.0, 10.0 - std * 0.5), 1)

    def _cicd_and_test_ratio_from_tree(self, tree_data: Dict[str, Any]) -> Tuple[bool, float]:
        """
        Returns (has_substantive_cicd, test_file_ratio among source blobs).
        """
        has_cicd = False
        test_ratio = 0.0
        if "tree" not in tree_data:
            return False, 0.0

        blobs = [
            i for i in tree_data["tree"]
            if i.get("type") == "blob" and i.get("path")
        ]

        cicd_paths = []
        for item in blobs:
            p = item["path"]
            pl = p.lower()
            if pl.startswith(".github/workflows/") or p in ("Dockerfile", "docker-compose.yml"):
                cicd_paths.append(item)

        for item in cicd_paths:
            size = item.get("size")
            if size is not None and int(size) > 200:
                has_cicd = True
                break

        source_files = [i for i in blobs if self._is_valid_source_code(i["path"])]
        n_src = len(source_files)
        if n_src == 0:
            test_ratio = 0.0
        else:
            test_files = [
                i for i in source_files
                if "test" in i["path"].lower()
                or "/tests/" in i["path"].lower().replace("\\", "/")
                or i["path"].lower().startswith("test/")
                or i["path"].lower().startswith("tests/")
            ]
            test_ratio = len(test_files) / n_src

        return has_cicd, test_ratio

    async def _analyze_sampled_commits(
        self,
        session: aiohttp.ClientSession,
        sampled: List[Dict[str, Any]],
        global_seen_sha: Set[str],
    ) -> Tuple[int, Dict[str, int], int, int]:
        """
        Returns (valid_loc, lang_stats, analyzed_count, evidence_loc).
        analyzed_count: 상세 조회에 성공한 커밋 수(LOC·commit_score 분모와 일치).
        evidence_loc: 설정·데이터·IaC 등 기여 증거 additions 합 (v5.5).
        global_seen_sha에 샘플에 포함된 SHA를 추가(분석 완료 후).
        """
        valid_loc = 0
        evidence_loc = 0
        lang_stats: Dict[str, int] = {}
        detail_objects: List[Dict[str, Any]] = []

        tasks = []
        for c in sampled:
            u = c.get("url")
            if not u:
                continue
            tasks.append(self._fetch_with_retry(session, u))

        results = await asyncio.gather(*tasks) if tasks else []

        for idx, (ok, detail, _) in enumerate(results):
            if not ok or not isinstance(detail, dict) or _is_hard_api_error(detail):
                continue
            detail_objects.append(detail)
            for f in detail.get("files", []) or []:
                filename = f.get("filename", "")
                additions = f.get("additions", 0) or 0
                if self._is_valid_source_code(filename):
                    valid_loc += additions
                    ext = os.path.splitext(filename.lower())[1]
                    lang = self.ext_to_lang.get(ext)
                    if lang:
                        lang_stats[lang] = lang_stats.get(lang, 0) + additions
                elif self._is_contribution_evidence(filename):
                    evidence_loc += additions

        # SHA 등록: 샘플 기준(분석 성공 여부와 무관하게 샘플에 올라온 커밋은 dedup용으로 등록)
        for c in sampled:
            sha = c.get("sha")
            if sha:
                global_seen_sha.add(sha)

        analyzed_count = len(detail_objects)
        return valid_loc, lang_stats, analyzed_count, evidence_loc

    async def evaluate_repository(
        self,
        session: aiohttp.ClientSession,
        owner: str,
        repo: str,
        username: str,
        target_branch: Optional[str] = None,
        global_seen_sha: Optional[Set[str]] = None,
    ) -> Dict[str, Any]:
        repo_warnings: List[str] = []
        if global_seen_sha is None:
            global_seen_sha = set()

        repo_url = f"{self.base_url}/repos/{owner}/{repo}"
        ok_meta, repo_meta, _ = await self._fetch_with_retry(session, repo_url)

        if not ok_meta or not isinstance(repo_meta, dict) or _is_hard_api_error(repo_meta):
            logging.error("Repository meta fetch failed for %s/%s", owner, repo)
            return {"valid": False}

        is_fork = repo_meta.get("fork", False)
        branch_to_scan = target_branch if target_branch else repo_meta.get("default_branch", "main")

        tree_url = f"{repo_url}/git/trees/{branch_to_scan}?recursive=1"
        commits_list_url = (
            f"{repo_url}/commits?author={username}&sha={branch_to_scan}&per_page=100"
        )
        readme_url = f"{repo_url}/readme?ref={branch_to_scan}"

        ok_tree, tree_data, _ = await self._fetch_with_retry(session, tree_url)
        if not ok_tree or not isinstance(tree_data, dict):
            tree_data = {}
        if _is_hard_api_error(tree_data):
            logging.error("Tree fetch hard failure for %s/%s", owner, repo)
            return {"valid": False}

        all_author_commits, commits_hard_err = await self._fetch_all_commits_paginated(
            session, commits_list_url
        )
        if commits_hard_err:
            repo_warnings.append(
                f"repo '{repo}' Rate Limit/API 오류로 커밋 목록이 불완전할 수 있음"
            )

        sampled = self._stratified_sample_commits(all_author_commits, global_seen_sha)
        # 분석 전에 전역 dedup: 샘플에서 global에 이미 있는 SHA 제외는 stratified에서 처리됨.
        # 재분석 시 sampled의 SHA는 _analyze 후 global에 추가됨.

        commit_messages: List[str] = []
        for c in sampled:
            msg = ((c.get("commit") or {}).get("message") or "").strip()
            line = msg.split("\n")[0].strip()[:240]
            if line:
                commit_messages.append(line)

        author_keys: Set[str] = set()
        for c in all_author_commits:
            au = c.get("author") or {}
            if au.get("login"):
                author_keys.add(str(au["login"]))
            else:
                cb = (c.get("commit") or {}).get("author") or {}
                if cb.get("name"):
                    author_keys.add(str(cb["name"]))
        distinct_author_count = len(author_keys) if author_keys else 1

        ok_readme, readme_data, _ = await self._fetch_with_retry(session, readme_url)
        if not ok_readme:
            readme_data = {}
        if _is_hard_api_error(readme_data):
            readme_data = {}

        readme_raw_text = ""
        readme_content = ""
        readme_has_image = False
        if isinstance(readme_data, dict) and "content" in readme_data:
            try:
                decoded_bytes = base64.b64decode(readme_data["content"])
                readme_raw_text = decoded_bytes.decode("utf-8", errors="ignore")
                readme_has_image = "![" in readme_raw_text
                readme_content = self._clean_markdown(readme_raw_text)
            except Exception:
                pass

        dep_paths = profile_builder.find_dependency_paths(tree_data)
        dep_contents = await self._fetch_repo_text_files(
            session, repo_url, branch_to_scan, dep_paths
        )
        frameworks = profile_builder.parse_dependency_contents(dep_contents)
        engine_detected = profile_builder.detect_engine_signatures(tree_data)
        frameworks = list(dict.fromkeys(engine_detected + frameworks))
        domain_hits = profile_builder.detect_domain_hits(tree_data)
        detected_domains = sorted(domain_hits.keys(), key=lambda d: domain_hits[d], reverse=True)
        has_deployment = profile_builder.has_deployment_signals(tree_data)

        created_at = datetime.strptime(repo_meta["created_at"], "%Y-%m-%dT%H:%M:%SZ")
        # 오너십: author 필터 커밋 목록에서 가장 오래된 항목(API는 최신순 → 마지막이 최초).
        # 수집 상한(per_page * MAX_COMMIT_PAGES) 밖의 더 오래된 커밋은 반영되지 않음.
        if all_author_commits:
            t0 = self._commit_timestamp(all_author_commits[-1])
            if t0:
                gap_days = (t0 - created_at).days
                if gap_days > 30:
                    repo_warnings.append(
                        f"repo '{repo}' 최초 커밋이 repo 생성일보다 {gap_days}일 늦음 — 오너십 확인 필요"
                    )

        valid_loc, lang_stats, analyzed_commit_count, evidence_loc = await self._analyze_sampled_commits(
            session, sampled, global_seen_sha
        )

        pushed_at = datetime.strptime(repo_meta["pushed_at"], "%Y-%m-%dT%H:%M:%SZ")
        duration_days = (pushed_at - created_at).days

        active_weeks = self._count_active_weeks(all_author_commits)
        if active_weeks >= 8:
            duration_pts = 10.0
        elif active_weeks >= 4:
            duration_pts = 5.0
        else:
            duration_pts = 0.0

        has_cicd, test_ratio = self._cicd_and_test_ratio_from_tree(tree_data)
        tree_stats = profile_builder.compute_tree_structure_stats(
            tree_data,
            valid_loc,
            self._is_valid_source_code,
        )
        # v5.0: CI/CD 10 + 테스트 10 + 활성 주 10 = 최대 30 (캡 없음, duration 편중 해소)
        cicd_pts = 10.0 if has_cicd else 0.0
        if test_ratio < 0.05:
            test_pts = 0.0
        elif test_ratio < 0.20:
            test_pts = 5.0
        else:
            test_pts = 10.0
        quality_axis = cicd_pts + test_pts + duration_pts

        # v5.0 + v5.5: 메인 LOC + Evidence LOC(최대 50점 스케일), 커밋 수에 따른 동적 가중치
        loc_score_main = min(
            100.0,
            math.log(valid_loc / 100.0 + 1.0) / math.log(101.0) * 100.0,
        )
        loc_score_ev = min(
            50.0,
            math.log(evidence_loc / 500.0 + 1.0) / math.log(101.0) * 50.0,
        )
        loc_score = min(100.0, loc_score_main + loc_score_ev)
        commit_score = min(
            100.0,
            math.log(analyzed_commit_count / 5.0 + 1.0) / math.log(21.0) * 100.0,
        )
        if analyzed_commit_count < 5:
            loc_w, commit_w = 0.9, 0.1
        elif analyzed_commit_count < 15:
            loc_w, commit_w = 0.6, 0.4
        else:
            loc_w, commit_w = 0.5, 0.5
        blend_100 = loc_score * loc_w + commit_score * commit_w
        contribution_axis = round((blend_100 / 100.0) * 60.0, 1)

        # 일관성: 균등 샘플이 아닌 전체 author 커밋 목록 타임스탬프 (샘플링 인위 갭 제거)
        consistency_axis = self._calc_consistency_score(all_author_commits)

        # 스펙 Phase 1-3: fork 시 기여도(contribution)만 70% 삭감(0.3배). quality·consistency는 패널티 없음.
        if is_fork:
            contribution_axis = round(contribution_axis * 0.3, 1)

        repo_score = round(contribution_axis + quality_axis + consistency_axis, 1)

        has_tests_proxy = test_ratio >= 0.05

        return {
            "valid": True,
            "repo_name": f"{repo} ({branch_to_scan})",
            "score": repo_score,
            "valid_loc": valid_loc,
            "evidence_loc": evidence_loc,
            "has_cicd": has_cicd,
            "has_tests": has_tests_proxy,
            "has_deployment": has_deployment,
            "languages": lang_stats,
            "readme": readme_content,
            "readme_has_image": readme_has_image,
            "frameworks": frameworks,
            "detected_domains": detected_domains,
            "domain_hits": domain_hits,
            "dependency_paths": dep_paths,
            "tree_stats": tree_stats,
            "test_ratio": test_ratio,
            "commit_messages": commit_messages,
            "distinct_author_count": distinct_author_count,
            "is_fork": is_fork,
            "duration_days": duration_days,
            "active_weeks": active_weeks,
            "total_commits": len(all_author_commits),
            "score_breakdown": {
                "contribution": contribution_axis,
                "quality": round(quality_axis, 1),
                "consistency": consistency_axis,
            },
            "commits_analyzed": analyzed_commit_count,
            "warnings": repo_warnings,
        }

    async def extract_applicant_profile(self, username: str, repo_list: List[str]) -> Dict[str, Any]:
        global_seen_sha: Set[str] = set()
        # asyncio.Lock으로 전역 SHA set을 보호하여 레포 간 병렬 평가를 안전하게 처리.
        sha_lock = asyncio.Lock()
        all_warnings: List[str] = []

        async def _evaluate_with_lock(session: aiohttp.ClientSession, repo_full: str) -> Optional[Dict[str, Any]]:
            parts = repo_full.strip("/").split("/")
            if len(parts) < 2:
                return None
            owner, repo = parts[0], parts[1]
            target_branch = "/".join(parts[3:]) if len(parts) >= 4 and parts[2] == "tree" else None
            # SHA dedup을 위해 lock 하에서 현재 global_seen_sha 스냅샷을 전달하고 결과를 병합
            async with sha_lock:
                sha_snapshot = set(global_seen_sha)
            r = await self.evaluate_repository(session, owner, repo, username, target_branch, sha_snapshot)
            if r.get("valid"):
                # 분석에 사용된 SHA를 전역 set에 병합 (lock 하에서)
                async with sha_lock:
                    global_seen_sha.update(sha_snapshot - set(global_seen_sha))
            return r

        results: List[Dict[str, Any]] = []
        async with aiohttp.ClientSession() as session:
            tasks = [_evaluate_with_lock(session, repo_full) for repo_full in repo_list]
            raw = await asyncio.gather(*tasks)
            results = [r for r in raw if r is not None]

        valid_results = [r for r in results if r.get("valid")]
        merged_readmes: List[str] = []
        global_languages: Dict[str, int] = {}
        total_loc = 0
        total_evidence_loc = 0
        total_commits_analyzed = 0

        weighted_score_sum = 0.0
        weighted_contrib_sum = 0.0
        weighted_quality_sum = 0.0
        weighted_consistency_sum = 0.0

        for res in valid_results:
            loc = res["valid_loc"]
            sc = res["score"]
            bd = res.get("score_breakdown") or {}
            total_loc += loc
            total_evidence_loc += int(res.get("evidence_loc", 0) or 0)
            total_commits_analyzed += int(res.get("commits_analyzed", 0))
            if res.get("readme"):
                merged_readmes.append(f"[{res['repo_name']} 요약]: {res['readme']}")
            for lang, count in res["languages"].items():
                global_languages[lang] = global_languages.get(lang, 0) + count
            for w in res.get("warnings") or []:
                if w not in all_warnings:
                    all_warnings.append(w)
            weighted_score_sum += sc * loc
            weighted_contrib_sum += bd.get("contribution", 0) * loc
            weighted_quality_sum += bd.get("quality", 0) * loc
            weighted_consistency_sum += bd.get("consistency", 0) * loc

        if valid_results:
            if total_loc > 0:
                final_score = round(weighted_score_sum / total_loc, 1)
                agg_breakdown = {
                    "contribution": round(weighted_contrib_sum / total_loc, 1),
                    "quality": round(weighted_quality_sum / total_loc, 1),
                    "consistency": round(weighted_consistency_sum / total_loc, 1),
                }
            else:
                n = len(valid_results)
                final_score = round(sum(r["score"] for r in valid_results) / n, 1)
                agg_breakdown = {
                    "contribution": round(
                        sum((r.get("score_breakdown") or {}).get("contribution", 0) for r in valid_results) / n,
                        1,
                    ),
                    "quality": round(
                        sum((r.get("score_breakdown") or {}).get("quality", 0) for r in valid_results) / n,
                        1,
                    ),
                    "consistency": round(
                        sum((r.get("score_breakdown") or {}).get("consistency", 0) for r in valid_results) / n,
                        1,
                    ),
                }
        else:
            final_score = 0.0
            agg_breakdown = {"contribution": 0.0, "quality": 0.0, "consistency": 0.0}

        total_loc_cnt = sum(global_languages.values())
        lang_str = ", ".join(
            [
                f"{l} ({int((c / total_loc_cnt) * 100)}%)"
                for l, c in sorted(global_languages.items(), key=lambda x: x[1], reverse=True)[:5]
            ]
        ) if total_loc_cnt > 0 else "N/A"

        applicant_resume = f"주요 기술 스택: {lang_str}\n\n" + "\n\n".join(merged_readmes)

        all_frameworks: List[str] = []
        seen_fw: Set[str] = set()
        for res in valid_results:
            for fw in res.get("frameworks") or []:
                if fw not in seen_fw:
                    seen_fw.add(fw)
                    all_frameworks.append(fw)

        domain_hit_list = [res.get("domain_hits") or {} for res in valid_results]
        merged_domains = profile_builder.merge_domain_hits(domain_hit_list)

        merged_domain_hits_dict: Dict[str, int] = {}
        for d in domain_hit_list:
            for k, v in d.items():
                merged_domain_hits_dict[k] = merged_domain_hits_dict.get(k, 0) + v

        any_cicd = any(res.get("has_cicd") for res in valid_results)
        any_tests = any(res.get("has_tests") for res in valid_results)
        any_deploy = any(res.get("has_deployment") for res in valid_results)
        readme_blob = "\n".join((res.get("readme") or "").strip() for res in valid_results).strip()

        profile_for_matching = profile_builder.build_profile_text(
            {
                "top_languages": lang_str,
                "detected_domains": merged_domains,
                "frameworks": all_frameworks,
                "has_cicd": any_cicd,
                "has_tests": any_tests,
                "has_deployment": any_deploy,
                "readme_summary": readme_blob,
                "total_valid_loc": total_loc,        # v5.2: 프로젝트 규모 문장용
                "scanned_repos": len(valid_results), # v5.2: 포트폴리오 규모 문장용
            }
        )

        per_repo: List[Dict[str, Any]] = []
        for res in valid_results:
            rm = res.get("readme") or ""
            per_repo.append(
                {
                    "repo_name": res.get("repo_name", ""),
                    "readme": rm,
                    "readme_has_image": bool(res.get("readme_has_image")),
                    "readme_tier": profile_builder.readme_length_tier(rm),
                    "tree_stats": res.get("tree_stats") or {},
                    "has_cicd": bool(res.get("has_cicd")),
                    "has_tests": bool(res.get("has_tests")),
                    "has_deployment": bool(res.get("has_deployment")),
                    "test_ratio": float(res.get("test_ratio") or 0.0),
                    "commit_messages": res.get("commit_messages") or [],
                    "distinct_author_count": int(res.get("distinct_author_count") or 1),
                    "valid_loc": int(res.get("valid_loc") or 0),
                    "evidence_loc": int(res.get("evidence_loc") or 0),
                    "is_fork": bool(res.get("is_fork")),
                    "duration_days": int(res.get("duration_days") or 0),
                    "active_weeks": int(res.get("active_weeks") or 0),
                    "total_commits": int(res.get("total_commits") or 0),
                    "frameworks": res.get("frameworks") or [],
                    "detected_domains": res.get("detected_domains") or [],
                }
            )

        return {
            "github_score": final_score,
            "score_breakdown": agg_breakdown,
            "applicant_resume": applicant_resume,
            "profile_for_matching": profile_for_matching,
            "domain_hits_merged": merged_domain_hits_dict,
            "per_repo": per_repo,
            "metrics_summary": {
                "total_valid_loc": total_loc,
                "total_evidence_loc": total_evidence_loc,
                "top_languages": lang_str,
                "scanned_repos": len(valid_results),
                "total_commits_analyzed": total_commits_analyzed,
            },
            "warnings": all_warnings,
        }


if __name__ == "__main__":
    import platform
    if platform.system() == "Windows":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    extractor = GitHubExtractor()
    target_username = "tekyung"
    target_repos = [
        "tekyung/Ttakji_lab-mobile_development_dep/tree/M1_milestone",
    ]

    profile = asyncio.run(extractor.extract_applicant_profile(target_username, target_repos))

    print("\n" + "=" * 60)
    print(f"📊 [v5.0] 깃허브 정밀 스캔 결과 - {target_username}")
    print(f"🎯 최종 스코어 : {profile['github_score']}점")
    sb = profile.get("score_breakdown") or {}
    print(
        f"📐 점수 분해 — contribution: {sb.get('contribution', 0)}, "
        f"quality: {sb.get('quality', 0)}, consistency: {sb.get('consistency', 0)}"
    )
    print(f"📝 누적 유효 LOC : {profile['metrics_summary']['total_valid_loc']} lines")
    print(f"📌 분석 커밋 수 : {profile['metrics_summary'].get('total_commits_analyzed', 0)}")
    print(f"💻 기술 스택 비중 : {profile['metrics_summary']['top_languages']}")
    warns = profile.get("warnings") or []
    if warns:
        print("⚠️ 경고:")
        for w in warns:
            print(f"   - {w}")
    print("-" * 60)
    print("🧠 [AI 엔진용 정제 Resume 미리보기]")
    print(profile["applicant_resume"])
    print("=" * 60)