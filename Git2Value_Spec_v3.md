# Git2Value — 시스템 기술 명세서

**Specification Document v3.0**

> 버전: v3.0 (v2.2 대체) | 작성일: 2026.05.02 | 대상 사용자: 채용 기업 / 구직자 본인 / 개발 팀
> 적용 시스템 버전: v6.0

---

## 0. 변경 이력

### v2.2 → v3.0 핵심 변경 (2026.04.06 ~ 2026.05.02)

본 문서는 v2.2(2026.04.01) 이후 약 한 달간의 시스템 진화를 반영하여 전면 개정한 것입니다.

| 영역          | v2.2 → v3.0 변경 요지                                                                              |
| ------------- | -------------------------------------------------------------------------------------------------- | ----------------------------------------------------------- |
| 시스템 정체성 | GitHub 추출 파이프라인 → **3개 독립 모듈(직무 매칭 / 포트폴리오 진단 / 연봉 밴드) 통합 서비스**    |
| 점수 수식     | 선형 만점 → **로그 스케일 + 동적 가중치 + Evidence LOC 보조**                                      |
| 직무 매칭     | 단순 FAISS → **하이브리드 리랭킹 + 다중 도메인 균형 추천**                                         |
| 환경 식별     | 언어 통계만 활용 → **시그너처 기반 감지 (게임 엔진, Lua 호스트, 모드 플랫폼, 모바일·블록체인 등)** |
| 연봉 모듈     | 멀티플라이어 모델 → **시장 밴드 독립 조회 + 3그룹 비교**                                           |
| 진단 항목     | 9개 항목 → **7개 정직 항목 + 종합 분석 블록**                                                      |
| 신뢰도 보강   | 균등 샘플링 + Rate Limit                                                                           | + **경력 필터링 + 시그너처 오탐 강화 + manifest 내용 검증** |

### 단계별 버전 매핑

| 버전        | 적용일     | 핵심 변경                                                           |
| ----------- | ---------- | ------------------------------------------------------------------- |
| v3.0 → v4.0 | 2026.04.06 | 서비스 리프레이밍, 모듈 A/B/C 분리, 멀티플라이어 제거               |
| v4.0 → v5.0 | 2026.04.06 | Contribution 로그 스케일, Quality 균등 배점                         |
| v5.0 → v5.1 | 2026.04.06 | 게임 카테고리 라우팅, 도메인 키워드 압축                            |
| v5.1 → v5.2 | 2026.04.09 | 유사도 상대 레이블, 기술 매칭 교차 분석                             |
| v5.2 → v5.3 | 2026.04.09 | **하이브리드 도메인 리랭킹 (+0.05)**                                |
| v5.3.1~6    | 2026.04.09 | 다중 도메인 억제, 영어 키워드 보강, 풀스택 분기                     |
| v5.4        | 2026.04.13 | **게임 엔진 시그너처 감지 (Unity/Unreal/Godot/Flutter)**            |
| v5.5        | 2026.04.16 | **Evidence LOC + 동적 가중치 + 테스트 항목 재배치**                 |
| v5.6        | 2026.04.27 | **언어 메인/서브 분류 + Lua 호스트 추론**                           |
| v5.7        | 2026.04.27 | **모드 플랫폼 감지 + 설정 프로젝트 매칭 제외**                      |
| v5.8        | 2026.04.27 | **시그너처 오탐 강화 + manifest 내용 검증 + 8개 신규 카테고리**     |
| v5.8 → v6.0 | 2026.05.02 | **경력 필터링 + 다중 도메인 균형 추천 + 진단 7개 + 종합 분석 블록** |

---

## 1. 시스템 개요

### 1-1. 서비스 정체성 (v4.0 리프레이밍 이후)

Git2Value는 **신입(0~3년) 개발자**의 GitHub 포트폴리오를 분석하여 다음 셋을 **서로 독립된 모듈**로 제공합니다:

- **모듈 A**: 직무 매칭 — 채용 공고 3,400건과의 벡터 유사도 + 도메인 리랭킹
- **모듈 B**: 포트폴리오 진단 — 7개 항목 체크리스트 + 종합 분석 블록
- **모듈 C**: 시장 연봉 밴드 — 점핏·원티드 직무별 신입 구간 + 인접 직무 비교

세 모듈은 완전히 독립적으로 동작하여, 하나의 부정확이 나머지를 오염시키지 않도록 설계되었습니다.

### 1-2. 설계 원칙: 외부 LLM API 의존 0

Git2Value는 GitHub API(데이터 수집)를 제외한 모든 외부 서비스 호출이 없습니다. ChatGPT, Claude 등 외부 LLM API를 사용하지 않으며 전체 분석·매칭·진단 파이프라인이 로컬에서 동작합니다.

- 비용 0 (API 과금 없음)
- 네트워크 장애 시에도 정상 동작 (데모 안정성)
- 캡스톤 종합설계 취지에 부합 (자체 엔진 구축)

향후 README 평가 등에서 LLM이 필요해지면 단계적 전환 경로를 따릅니다: (1) 룰베이스 템플릿 → (2) 로컬 오픈소스 모델 → (3) 외부 API (최후 수단).

### 1-3. 전체 파이프라인

```
GitHub Username + 레포 URL 리스트
        ↓
GitHubExtractor (github_extractor.py)
  - API 비동기 수집 (커밋, 트리, README, 메타)
  - 균등 샘플링 + SHA dedup
  - 의존성 파일 파싱 → 프레임워크 추출
  - 시그너처 기반 환경 감지 (엔진/모드/Lua 호스트/모바일/블록체인 등)
  - 언어 메인/서브 분류
  - 점수 산출 (contribution: 동적 가중치 + Evidence LOC / quality / consistency)
        ↓
profile_builder.build_profile_text()
  - JD 문체에 가까운 매칭용 텍스트 생성
  - 메인 언어 + 도메인 + 프레임워크 + 보조 시그널
        ↓
run_git2value.py (E2E)
  ├─ 모듈 A: FAISS k=20 → 경력 필터 → 도메인 리랭킹 또는 균형 추천
  ├─ 모듈 B: portfolio_diagnosis.run_diagnosis() → 7개 진단 + 종합 분석
  └─ 모듈 C: get_market_band() → realistic_range + 3그룹 비교
        ↓
       최종 통합 리포트
```

---

## Phase 1: Ingestion & Validation

### 1-1. Input

- GitHub Username
- Repository URL 리스트 (브랜치 경로 포함 가능, 형식: `owner/repo` 또는 `owner/repo/tree/branch-name`)
- 지원자 경력(applicant_years, 0~3년 권장)

### 1-2. Auth

- 시스템 GitHub Personal Access Token (환경변수 `Github_api_token`)

### 1-3. Anti-Cheating (v2.2 유지)

- **Fork 탐지:** `fork: true` 시 contribution 점수에만 0.3배 패널티 (오픈소스 기여 인정)
- **오너십 확인 (v2.2):** `all_author_commits[-1]`의 author.date와 `repo_meta.created_at` 차이 ≥ 30일이면 `warnings`에 경고 출력
- **중복 커밋 제거:** 전역 SHA set으로 레포 간 중복 집계 방지
- **보일러플레이트 필터링:** Create React App 등 프레임워크 자동 생성 코드 제거

---

## Phase 2: Parallel Fetching

`asyncio.gather`로 단일 레포 내부 엔드포인트 동시 호출. 레포 간 처리는 SHA dedup 정확성을 위해 순차 처리.

### 2-1. 호출 엔드포인트

- Repository Meta: `/repos/{owner}/{repo}`
- Tree: `/repos/{owner}/{repo}/git/trees/{branch}?recursive=1`
- Commits: `/repos/{owner}/{repo}/commits?author={username}&sha={branch}&per_page=100`
- README: `/repos/{owner}/{repo}/readme?ref={branch}`
- 의존성/manifest 파일 (조건부): `/repos/{owner}/{repo}/contents/{path}?ref={branch}`

### 2-2. 균등 샘플링 (v2.0 유지)

전체 커밋을 초기 / 중간 / 최근 3구간에서 각 최대 25개씩 균등 추출. 최대 분석 커밋 수 75개. SHA dedup으로 구간 중복 제거.

### 2-3. Rate Limit 대응 (v2.0 유지)

- HTTP 403/429 수신 시 `Retry-After` 헤더 파싱 후 대기
- 최대 3회 지수 백오프 (1s → 2s → 4s)
- 3회 실패 시 해당 레포를 `valid: False`로 마킹하고 명시적 경고 출력

---

## Phase 3: Data Cleansing & Context Parsing

### 3-1. Text Normalization (v2.2 유지)

- README Base64 디코딩 → 마크다운 이미지·배지·HTML 제거
- 프레임워크 보일러플레이트 패턴 제거
- 정제된 텍스트 최대 1500자

### 3-2. Language Aggregation 개정 ★ (v5.6)

> ❌ **v2.2 문제:** LOC 비율 상위 5개를 그대로 출력. Lua(80%) + C++(20%) 같은 경우 "Lua 기반 게임 개발 경험"으로 잘못 표기됨. Lua는 단독으로 직무를 결정하지 않는 서브 언어임.

**✅ v5.6 개선: 메인/서브 언어 분류 + 호스트 환경 추론**

언어를 **메인 언어**(자체 직무 카테고리 보유)와 **서브 언어**(보조 역할)로 분류:

```python
MAIN_LANGUAGES = {
    "Python", "Java", "JavaScript", "TypeScript", "C#", "C++", "C",
    "Go", "Rust", "Kotlin", "Swift", "Ruby", "PHP", "Dart",
    "Scala", "Elixir",
}

SUB_LANGUAGE_SIGNALS = {
    "Lua", "Shell", "GLSL", "HLSL", "CSS", "HTML",
    "Dockerfile", "Makefile", "Vim Script", "SQL",
}

# categorize_languages(lang_stats) → {"main": [...], "sub": [...], "trivial": [...]}
```

**프로필 텍스트 예시:**

```
변경 전: "Lua (80%), C++ (20%) 기반 게임 개발 경험"
변경 후: "C++ (70%) 기반 게임 개발 경험. Lua 스크립팅 활용."
```

### 3-3. 시그너처 기반 환경 감지 ★ 신규 (v5.4 ~ v5.8)

언어 통계만으로는 환경(Unity vs 일반 C#, Roblox vs 일반 Lua, React Native vs 일반 JS)을 구분할 수 없습니다. 파일 트리의 고유 시그너처를 매칭하여 환경을 식별합니다.

#### v5.4: ENGINE_SIGNATURES (게임 엔진 + 분석 환경)

| 환경            | 시그너처                                               |
| --------------- | ------------------------------------------------------ |
| Unity           | `Assets/` + `.meta`                                    |
| Unreal Engine   | `.uproject` 또는 `.uasset`                             |
| Godot           | `.tscn` + `.gd`                                        |
| Flutter         | `pubspec.yaml` + `android/`/`ios/` 중 하나 (v5.8 강화) |
| Jupyter/ML 실험 | `.ipynb` 파일 3개 이상 (v5.8 강화)                     |
| Kubernetes/IaC  | `.tf`, `.hcl`, `kubernetes/`, `terraform/` 중 다수     |

#### v5.6: LUA_HOST_SIGNATURES (Lua 호스트 환경 9종)

| 환경                            | 도메인             | 시그너처                                                     |
| ------------------------------- | ------------------ | ------------------------------------------------------------ |
| Roblox                          | 게임 개발          | `.rbxl`, `.rbxlx`, `.rbxm`                                   |
| Love2D                          | 게임 개발          | `main.lua` + `conf.lua` (루트, `build.settings` 부재)        |
| Defold                          | 게임 개발          | `game.project` + `.script`                                   |
| Solar2D/Corona                  | 모바일 앱          | `main.lua` + `build.settings` (루트)                         |
| Cocos2d-x Lua                   | 게임 개발          | `cocos.lua` + `project.json`                                 |
| OpenResty/Nginx-Lua             | DevOps/인프라      | `nginx.conf` + `lua/` (v5.8 `.lua` 필수)                     |
| NodeMCU/임베디드 Lua            | HW/임베디드        | `init.lua` + `wifi.lua`/`uart.lua`/`spi.lua`/`i2c.lua`       |
| Neovim 설정 (`is_config: True`) | (직무 시그널 없음) | `init.lua` + `lua/`/`plugin/`/`after/` 또는 `lazy-lock.json` |

#### v5.7: MOD_PLATFORM_SIGNATURES (모드/플러그인 6종)

| 플랫폼                 | 시그너처                                          | 비고                  |
| ---------------------- | ------------------------------------------------- | --------------------- |
| EDOPro 카드 스크립트   | `c\d{8}\.lua` 정규식 5개 이상                     | mod_context           |
| Garry's Mod            | `gamemodes/` + `entities/`/`lua/`                 | mod_context           |
| Factorio 모드          | `info.json` + `control.lua`/`data.lua`            | mod_context           |
| Minecraft 플러그인     | `plugin.yml` + `org/bukkit/`/`io/papermc/` (v5.8) | mod_context           |
| Stardew Valley (SMAPI) | 루트 `manifest.json` + `.cs` (v5.8 루트 한정)     | mod_context           |
| WoW 애드온             | `.toc` + `.lua`                                   | mod_context, is_hobby |

#### v5.8: 추가 8개 카테고리 (모바일·블록체인·인프라·데이터·도구)

| 카테고리          | 도메인            | 시그너처                                                            |
| ----------------- | ----------------- | ------------------------------------------------------------------- |
| Expo              | 모바일 앱         | `app.json` + manifest 키 `"expo"` (비동기 검증)                     |
| React Native      | 모바일 앱         | `package.json` + `android/`/`ios/` + `pubspec.yaml` 부재            |
| Hardhat           | 블록체인          | `hardhat.config.js`/`.ts` + `contracts/` + `.sol`                   |
| Foundry           | 블록체인          | `foundry.toml` + `src/`/`test/` + `.sol`                            |
| Helm Chart        | DevOps/인프라     | `Chart.yaml` + `templates/`                                         |
| dbt               | 빅데이터 엔지니어 | `dbt_project.yml` + `models/`/`seeds/`                              |
| VS Code 확장      | 도구 개발         | 루트 `package.json` + manifest 키 `vscode`+`contributes`            |
| Browser Extension | 도구 개발         | 루트 `manifest.json` + manifest 키 `manifest_version`+`permissions` |

#### manifest 내용 검증 메커니즘 (v5.8)

`manifest.json`은 5개 환경(Unity Packages, SMAPI, 브라우저 확장, Obsidian, PWA)에서 사용되어 단순 트리 스캔으로 구분 불가. 비동기 검증으로 해결:

1. **1단계:** 트리 스캔으로 후보 환경 추출
2. **2단계:** `manifest_signature_keywords`가 정의된 후보의 manifest 파일 fetch
3. **3단계:** 키워드 매칭으로 환경 확정

같은 `manifest.json`이라도:

- `"manifest_version" + "permissions"` → 브라우저 확장
- `"UniqueID" + "MinimumApiVersion"` → Stardew Valley
- `"vscode" + "contributes"` → VS Code 확장

### 3-4. 도메인 감지 (v5.3.1)

파일/폴더 이름 패턴으로 도메인 시그널 감지. 도메인별로 **고유 키워드 종류 수**를 세며, 2종류 미만이면 제외 (반복 매칭 과대 카운트 방지).

```python
DOMAIN_SIGNALS = {
    "게임 개발":    ["game", "player", "enemy", "scene", ...],
    "웹 프론트엔드": ["component", "page", "layout", ...],
    "서버/백엔드":   ["controller", "service", "repository", ...],
    "ML/AI":        ["model", "train", "dataset", "inference", ...],
    "모바일 앱":     ["activity", "fragment", "viewmodel", ...],
    "DevOps/인프라": ["terraform", "ansible", "helm", "k8s", ...],
    "블록체인":      ["contract", "solidity", "hardhat", ...],     # v5.8
    "빅데이터 엔지니어": ["dbt", "airflow", "spark", ...],          # v5.8
    "도구 개발":     ["extension", "plugin", "vscode", ...],       # v5.8
}
```

---

## Phase 4: Scoring Engine ★ (v5.0 + v5.5)

### 4-1. 점수 구조 (v2.2 유지)

| 축           | 배점      | 산출 방식                                       |
| ------------ | --------- | ----------------------------------------------- |
| contribution | 최대 60점 | LOC + 커밋 수 (동적 가중치) + Evidence LOC 보조 |
| quality      | 최대 30점 | CI/CD + 테스트 + 활성 ISO 주                    |
| consistency  | 최대 10점 | 커밋 간격 표준편차                              |

### 4-2. Contribution Score 개정 ★ (v5.0 + v5.5)

> ❌ **v2.2 문제:** 선형 만점(LOC 1500 → 100점)은 변별력 부족. 데이터 전담자나 일괄 푸시 개인 프로젝트가 부당하게 낮게 평가됨.

**✅ v5.0 + v5.5 개선:** 로그 스케일 + 동적 가중치 + Evidence LOC 보조

```python
import math

# 로그 스케일 (선형 만점 제거)
loc_score_main = min(100, math.log(valid_loc / 100 + 1) / math.log(101) * 100)

# Evidence LOC: json/yml/md/Dockerfile 등 설정·데이터 기여 (v5.5)
loc_score_ev = min(50, math.log(evidence_loc / 500 + 1) / math.log(101) * 50)
loc_score = min(100, loc_score_main + loc_score_ev)

commit_score = min(100, math.log(analyzed_count / 5 + 1) / math.log(21) * 100)

# 커밋 수 기반 동적 가중치 (v5.5)
if analyzed_count < 5:
    loc_w, commit_w = 0.9, 0.1   # 일괄 푸시 개인 프로젝트 보호
elif analyzed_count < 15:
    loc_w, commit_w = 0.6, 0.4
else:
    loc_w, commit_w = 0.5, 0.5   # 협업 프로젝트 공정 평가

contribution_axis = (loc_score * loc_w + commit_score * commit_w) * 0.6
# Fork 시 0.3배 패널티 (기존 유지)
```

### 4-3. Quality Score 개정 ★ (v5.0)

> ❌ **v2.2 문제:** duration 일수에 30점 편중되어 CI·테스트가 무력화됨.

**✅ v5.0 개선:** CI/CD 10 + 테스트 10 + 활성 ISO 주 10 (균등 배점)

| 항목        | 조건                              | 점수                           |
| ----------- | --------------------------------- | ------------------------------ |
| CI/CD       | 워크플로우/Dockerfile blob > 200B | 10 또는 0                      |
| 테스트 비율 | < 5% / 5~20% / ≥ 20%              | 0 / 5 / 10                     |
| 활성 주 수  | `all_author_commits` ISO 주 개수  | ≥ 8주 → 10, ≥ 4주 → 5, 그 외 0 |

### 4-4. Consistency Score (v5.0)

```python
max(0, 10 - std * 0.5)   # std = 연속 커밋 간격(일)의 모표준편차
# 커밋 수 < 5: 0점
# v5.0: 타임스탬프 소스를 균등 샘플 → 전체 author 커밋 목록으로 변경
```

### 4-5. 집계 (v2.1 유지)

LOC 기반 가중 평균. valid_loc=0 레포는 자동 제외.

### 4-6. ignore_paths / ignore_extensions 확장

- **v5.0:** `__pycache__/`, `generated/`, `obj/`, `bin/`, `.next/`, `migrations/` 등
- **v5.5:** `.tf`, `.hcl`, `.proto`, `.sql` (유효 LOC 대신 evidence_loc로 집계)

---

## Phase 5: Profile Building (v3.0 신규)

### 5-1. 프로필 변환 레이어의 필요성

GitHub 추출 데이터(`"Python (45%), C# (30%)"`)와 채용 공고 텍스트(`"3년 이상 Spring Boot 경험자 우대"`)는 문체가 달라 직접 임베딩 시 의미 있는 유사도가 나오지 않습니다. **공고 문체에 가까운 프로필 텍스트**로 변환합니다.

### 5-2. build_profile_text() 우선순위 (v5.6)

| 우선순위 | 시그널                               | 처리                                 |
| -------- | ------------------------------------ | ------------------------------------ |
| 1        | 시그너처 감지 (엔진/모드/Lua 호스트) | 도메인 + 라벨로 프로필 시작          |
| 2        | 메인 언어 + 도메인                   | "{Lang} ({pct}%) 기반 {domain} 경험" |
| 3        | 프레임워크 (의존성 파싱)             | "{Frameworks} 활용 경험"             |
| 4        | 서브 언어 (메인 있을 때)             | "{SubLang} 활용" 보조 표기           |
| 5        | CI/CD, 테스트, 배포                  | 양호 시 한 줄 추가                   |
| 6        | README 키워드 (long 티어만)          | 도메인 키워드 압축 문장              |

### 5-3. README 활용 분기 (v5.3)

| 잔량       | 티어   | 처리                                   |
| ---------- | ------ | -------------------------------------- |
| 200자 이상 | long   | 키워드 추출 성공 시에만 압축 문장 추가 |
| 50~199자   | medium | 구조화 데이터만                        |
| 49자 이하  | short  | 의존성·도메인 감지 시도                |

**원칙:** 부실 README는 프로필에 넣지 않음. 키워드 추출 실패 시 원문 폴백 안 함 (v5.3에서 v5.2의 폴백 정책 제거).

### 5-4. 출력 예시

```
입력: C# Unity 게임 클라이언트 + Lua 스크립팅
프로필: "C# (70%) 기반 게임 개발 경험. Unity 활용 경험.
        Lua 스크립팅 활용. CI/CD 파이프라인 구축 경험."

입력: Roblox 단독 (Lua 95%)
프로필: "Roblox 플랫폼 개발."

입력: dbt 데이터 모델링 (SQL 95%)
프로필: "SQL 기반 빅데이터 엔지니어 경험. dbt 데이터 모델링."
```

---

## Phase 6: 모듈 A — 직무 매칭 ★ (v3.0 신규)

### 6-1. FAISS 벡터 매칭

- 임베딩 모델: `jhgan/ko-sroberta-multitask` (한국어 특화)
- 벡터 DB: FAISS-CPU
- 유사도: 코사인 유사도
- 인덱스: 채용 공고 3,400건 (원티드 2,000 + 점핏 1,000 + 리멤버 400)
- 검색 범위: **k=20** (v6.0 확장, 기존 k=5)

### 6-2. 경력 필터링 ★ 신규 (v6.0)

> ❌ **v5.8 이전 문제:** "경력 3년 이상" 공고가 신입 1순위로 노출되어 지원 불가능한 결과 추천.

**✅ v6.0 해결:** 사이드카 캐시 + 후순위 처리

```python
# experience_filter.py
EXPERIENCE_PATTERNS = [
    (r"경력\s*(\d+)\s*[년~\-]\s*(\d+)?\s*년", "min_years_exp"),
    (r"(\d+)\s*년\s*이상", "min_years_exp"),
    (r"신입|junior", "junior_only"),
    (r"시니어|senior|lead|리드", "senior_only"),
]

# 사이드카 캐시: vector/experience_cache.json (자동 생성)
# 신입(applicant_years <= 3) 시 min_years > applicant_years + 1인 공고를 후순위로
# 완전 제외가 아닌 표시 + 정렬 조정 (정보 보존)
```

### 6-3. 하이브리드 도메인 리랭킹 ★ (v5.3)

> ❌ **v5.2 이전 문제:** 임베딩 단일 신호만으로는 공고 DB 분포 불균형(프론트엔드/SW 공고가 압도적)을 극복하지 못해 게임/AI 프로젝트가 미세한 차이로 잘못 매칭됨.

**✅ v5.3 해결:** 두 개 독립 시그널 결합 (임베딩 + 파일 구조 도메인 감지)

```python
DOMAIN_BOOST = 0.05

def rerank_by_domain(top_matches, primary_domain, domain_hits):
    # 다중 도메인 억제 (v5.3.1)
    hits = sorted(domain_hits.values(), reverse=True)
    if len(hits) >= 2 and hits[0] < hits[1] * 2:
        return top_matches, "혼합 프로젝트 — 리랭킹 미적용"

    expected_categories = DOMAIN_TO_CATEGORIES[primary_domain]
    for m in top_matches:
        if m["category"] in expected_categories:
            m["effective_score"] = m["similarity"] + DOMAIN_BOOST
        else:
            m["effective_score"] = m["similarity"]

    return sorted(top_matches, key=lambda x: -x["effective_score"]), "리랭킹 적용"
```

### 6-4. 다중 도메인 균형 추천 ★ 신규 (v6.0)

> ❌ **v5.3.1 한계:** 다중 도메인 시 리랭킹만 억제 → FAISS 원본 순서 유지. 풀스택 프로젝트에서 우연히 프론트엔드 5개로 채워지면 ML/AI 매칭 결과가 사라짐.

**✅ v6.0 해결:** 도메인별로 상위 1~2개씩 분배 추천

```python
def recommend_multi_domain(top_matches_extended, detected_domains, domain_hits):
    # 단일 도메인 또는 단일 우세 도메인은 기존 로직 사용
    hits = sorted(domain_hits.values(), reverse=True)
    if len(hits) < 2 or hits[0] >= hits[1] * 2:
        return None

    # 각 도메인 카테고리에서 상위 1~2개씩 추출
    domain_to_picks = {}
    for domain in detected_domains[:3]:
        expected_cats = DOMAIN_TO_CATEGORIES.get(domain, [])
        picks = [m for m in top_matches_extended
                 if m["category"] in expected_cats][:2]
        if picks:
            domain_to_picks[domain] = picks

    return {"is_multi_domain": True, "domain_picks": domain_to_picks}
```

### 6-5. 사용자 안내 강화 (v6.0)

| 기능                         | 동작                                                |
| ---------------------------- | --------------------------------------------------- |
| `similarity_label()`         | spread < 0.02 시 "약한 매칭" 시스템 안내 출력 (A-1) |
| `route_job_category_safe()`  | 콤마 결합 카테고리 방어 (A-4)                       |
| `diagnose_domain_mismatch()` | DB 커버리지 / 프로필 약함 / 일관 / 모호 4분기 (A-3) |
| `analyze_tech_match()`       | 도메인 일치 공고만 미보유 기술 추출 (A-5)           |

---

## Phase 7: 모듈 B — 포트폴리오 진단 ★ (v3.0 신규)

### 7-1. 진단 항목 7개 (v6.0)

> ❌ **v5.8 이전 문제:** 9개 항목에 신뢰도 낮은 항목 포함 (commit_pattern, growth_trajectory, collaboration). 사용자가 "그래서 뭐 어쩌라고?" 됨.

**✅ v6.0 해결:** 신뢰도 낮은 3개 항목 제거, 7개로 축소.

| 진단 항목      | 판별 방법                                | 수치화 기준             |
| -------------- | ---------------------------------------- | ----------------------- |
| README 품질    | 길이 + 3차원 룰베이스 (목적/스택/시각화) | 200자+양호: 양호        |
| 프로젝트 구조  | 디렉토리 모듈화, .gitignore              | 모듈화+.gitignore: 양호 |
| 테스트 작성    | test 파일 / 전체 비율                    | ≥10%: 양호 (Top 차별화) |
| CI/CD 구성     | Actions/Dockerfile + 200B 이상           | 파일 양호: 양호         |
| 커밋 메시지    | 길이 + 무의미 비율 + 변환 힌트           | < 20%: 양호             |
| 배포 경험      | Docker/Vercel/docker-compose             | 설정 존재: 양호         |
| 기여 유형 안내 | 단독 vs 협업 (레포 메타)                 | 분류 안내만             |

### 7-2. 종합 분석 블록 ★ 신규 (v6.0)

```python
generate_summary_block(diagnosis, level_dict, github_score, primary_domain)
# 출력:
#   ① 한 줄 포지셔닝 ("서버/백엔드 Entry 수준 — 보강 필요")
#   ② 강점 1~2개 (양호 항목 중 우선순위 추출)
#   ③ Quick wins 1~3개 (이번 주 실행 가능한 행동)
```

### 7-3. README 평가 강화 (v6.0)

```python
README_QUALITY_INDICATORS = {
    "프로젝트 목적 명시": [r"^#\s*[가-힣\w].{5,}", r"##\s*소개|introduction|overview"],
    "기술 스택 설명": [r"##\s*기술\s*스택|tech\s*stack|technologies"],
    "결과물 시각화": [r"!\[.*\]\(.*\)", r"<img\s+src=", r"\.(gif|png|jpg|mp4|webm)"],
}
# 3차원 평가 → 길이 단일 기준보다 풍부
```

### 7-4. 커밋 메시지 변환 힌트 (v6.0)

```python
COMMIT_REWRITE_HINTS = {
    r"^fix\s*$":    "fix: [무엇을] 수정",
    r"^update\s*$": "refactor: [무엇을] 개선",
    r"^wip\s*$":    "feat: [기능명] 구현 중",
    r"^test\s*$":   "test: [대상] 단위 테스트 추가",
    r"^initial\s+commit\s*$": "chore: 프로젝트 초기 설정",
}
# 무의미 커밋 발견 시 실제 커밋 + 개선안 동시 표시
```

### 7-5. 기대 수준 가이드

| 레벨        | 충족 조건 (v5.5 갱신)                     | 설명                         |
| ----------- | ----------------------------------------- | ---------------------------- |
| Entry       | README 존재, 프로젝트 1~2개               | 중소/중견 SI, 일반 스타트업  |
| Competitive | + (CI/CD 또는 배포) + 멀티 프로젝트 + s≥4 | 시리즈B+ 스타트업, IT 서비스 |
| Top         | + 테스트 + CI/CD + 배포 + 멀티 + s≥6      | 대형 테크 기업 서류 통과     |

### 7-6. 레포 분류 안내 (v5.7)

```
[프로젝트 분류 안내]
  · my-portfolio (메인): 서버/백엔드
  · edopro-cards (모드): EDOPro 카드 스크립트
    → 게임 분야에 대한 깊은 이해를 보여주나 직접 매칭 공고는 적음
  · nvim-config (설정/제외): Neovim 설정
    → 매칭 입력에서 제외됨
```

---

## Phase 8: 모듈 C — 시장 연봉 밴드 ★ (v3.0 신규)

### 8-1. 멀티플라이어 모델 제거 (v4.0)

GitHub 점수로 연봉을 직접 산출하는 방식을 제거. 양자 간 검증된 상관관계 부재 + 근거 없는 정밀 수치는 신뢰도 저하.

### 8-2. 점핏·원티드 교차검증 (v4.0)

- 점핏·원티드 2025 채용 공고 직무별 신입(0~3년) 중앙값
- 두 플랫폼 신입 구간 오차율 ±5% 이내 수렴
- 매핑 누락 직무는 점핏 단독 사용

### 8-3. realistic_range 출력 ★ 신규 (v6.0)

> ❌ **v5.8 이전 문제:** 두 플랫폼 중앙값 차이 47만원 → "3,677만 ~ 3,724만"이 정확한 값으로 오해됨. 실제 신입 분포는 훨씬 넓음.

**✅ v6.0 해결:** 중앙값 ±15%/+20% 비대칭 확장으로 실제 분포 감각 제공

```python
median = (jumpit_median + wanted_median) // 2 if wanted_median else jumpit_median
realistic_low  = int(median * 0.85)  # P25 추정
realistic_high = int(median * 1.20)  # P75 추정
# 좁은 범위(±5%)는 신뢰도 검증 자료로 별도 표기
```

**출력 예시:**

```
시장 중앙값: 약 3,700만원
실제 분포:   3,145만 ~ 4,440만원 (회사·지역·협상에 따라)
플랫폼 교차검증: 점핏 3,724만 / 원티드 3,677만 (오차 ±5% 이내)
```

### 8-4. 직무 비교 3그룹화 ★ 신규 (v6.0)

> ❌ **v5.8 이전 문제:** 상위 6개 직무를 연봉 순으로 단순 나열 → "그럼 나 블록체인 해야 하나?" 오해 유발.

**✅ v6.0 해결:** `DOMAIN_TO_CATEGORIES` 역매핑으로 인접 직무 도출

```
[내 직무]
  서버/백엔드: 3,500 ~ 3,800만원

[인접 직무 — 현재 스택으로 지원 가능]
  웹 풀스택: 3,400 ~ 3,700만원
  DevOps/시스템: 3,800 ~ 4,200만원

[참고 — 연봉 상위 직무]
  인공지능/머신러닝: 3,958 ~ 3,977만원
  → 추가 학습 필요
```

---

## Phase 9: Output Schema (확장)

```json
{
  "github_score": 79.3,
  "score_breakdown": {
    "contribution": 42.0,
    "quality": 28.0,
    "consistency": 9.3
  },
  "applicant_resume": "주요 기술 스택: … (레거시 미리보기)",
  "profile_for_matching": "Python (90%) 기반 서버/백엔드 경험. FastAPI 활용 경험.",
  "domain_hits_merged": { "서버/백엔드": 5, "웹 프론트엔드": 3 },
  "per_repo": [
    {
      "repo_name": "repo (main)",
      "readme_tier": "long",
      "tree_stats": {
        "source_file_count": 42,
        "avg_loc_per_file": 120.5,
        "has_gitignore": true
      },
      "has_cicd": true,
      "has_tests": true,
      "has_deployment": false,
      "test_ratio": 0.12,
      "valid_loc": 5000,
      "evidence_loc": 120,
      "active_weeks": 12,
      "frameworks": ["FastAPI"],
      "detected_domains": ["서버/백엔드"],
      "language_category": {
        "main": [["Python", 90.0]],
        "sub": [["Shell", 10.0]],
        "trivial": []
      },
      "sub_language_host": null,
      "is_config_repo": false,
      "mod_platform": null,
      "matching_included": true
    }
  ],
  "metrics_summary": {
    "total_valid_loc": 5000,
    "total_evidence_loc": 120,
    "scanned_repos": 1,
    "total_commits_analyzed": 42
  },
  "warnings": []
}
```

### 신규 필드 (v5.6 ~ v5.7)

- `language_category`: 메인/서브 언어 분류 결과
- `sub_language_host`: Lua 등 서브 언어 호스트 환경 (또는 null)
- `is_config_repo`: 설정/취미 프로젝트 여부 (매칭 제외 대상)
- `mod_platform`: 모드 플랫폼 감지 결과 (또는 null)
- `matching_included`: 직무 매칭 입력 포함 여부
- `evidence_loc` (v5.5): 설정·데이터 기여 LOC 별도 집계

---

## Phase 10: 향후 과제 (v6.0 이후)

### 10-1. 보류된 항목 (v7 검토)

- **로컬 LLM 도입**: README 평가 등에 Qwen2.5-32B-AWQ 등 로컬 모델 자체 호스팅 (외부 API 0 원칙 유지)
- **신뢰도별 차등 가산점**: 시그너처 매칭(+0.08) vs 키워드 휴리스틱(+0.03) 차등 적용 (정확도 측정 후)
- **신규 도메인 매핑**: HW/임베디드, DBA/데이터, 그래픽스의 점핏 카테고리 매핑
- **Consistency 0.5 계수 데이터 기반 튜닝**: 지수 감쇠 `10 * exp(-std / K)` 전환

### 10-2. 사용자 검증 강화 (캡스톤 발표 대응)

- 현직 채용담당자 인터뷰 1~2건 (산업체 연계)
- 취준생 5~10명 실사용 테스트 (사용자 만족도, 포트폴리오 개선 효과)
- 직무 매칭 정확도 다수 표본 측정 (현직 개발자 실제 직무 vs 시스템 추천 일치도)

### 10-3. 데이터 보강

- 점핏 JD 코퍼스에 블록체인·도구 개발·게임 공고 보강
- 실시간 공고 연동 (채용 플랫폼 API)
- 점핏·원티드 외 추가 데이터 소스 (잡코리아, 사람인 등)

---

## 부록 A: 기술 스택

| 구분                  | 기술                                     |
| --------------------- | ---------------------------------------- |
| 언어                  | Python 3.11+                             |
| GitHub 데이터 수집    | aiohttp + asyncio (비동기)               |
| 임베딩 모델           | jhgan/ko-sroberta-multitask              |
| 벡터 검색             | FAISS-CPU 1.8.0                          |
| Sentence Transformers | 2.6.1 (버전 고정 필수)                   |
| 채용 공고 데이터      | 원티드 2,000 + 점핏 1,000 + 리멤버 400건 |
| 연봉 데이터           | 점핏·원티드 2025 직무별 연차별 중앙값    |
| 환경                  | RTX 4090, Windows 11, Docker, PyTorch    |

---

## 부록 B: 파일 구조

```
basic/
├── github_extractor.py      # GitHubExtractor (수집·점수·per_repo 집계)
├── profile_builder.py       # 도메인·엔진 시그니처 감지, 의존성 파싱, build_profile_text()
├── portfolio_diagnosis.py   # 진단 룰베이스 (v6.0: 7개 항목, 종합 분석)
├── valuation_engine.py      # get_market_band() + realistic_range
├── experience_filter.py     # v6.0: 경력 요건 필터링 사이드카
├── run_git2value.py         # E2E: 모듈 A/B/C 통합 출력
├── requirements.txt         # 의존성
├── .env                     # Github_api_token 환경변수
├── HandOff.md               # 개발자 핸드오프 문서
│
├── vector/
│   ├── git2value_faiss.index
│   ├── git2value_metadata.json
│   ├── experience_cache.json   # v6.0 자동 생성
│   └── unified_jd_corpus.jsonl
│
├── data/
│   ├── jumpit_data/
│   ├── wanted_data/
│   └── ...
│
└── md/   # 과거 계획 문서 (참조용)
```

---

## 부록 C: 시스템 한계

| 한계                           | 이유                                                |
| ------------------------------ | --------------------------------------------------- |
| 깃허브 없는 지원자 분석 불가   | 입력 데이터 자체 부재                               |
| 코드 전체 품질 판단 불가       | 샘플 기반 간접 평가의 본질적 한계                   |
| 정확한 연봉 예측 불가          | GitHub 점수와 연봉 간 검증된 상관관계 부재          |
| 깃허브 미사용 개발자 커버 불가 | 신입 중에서도 깃허브를 적극 관리하는 비율 일부      |
| 면접 합격 여부 예측 불가       | 컬쳐핏, 면접 퍼포먼스 등 깃허브 외 변수             |
| 경력직 깊이 분석 불가          | 신입 대상 설계 (경력직은 LinkedIn/이력서 결합 필요) |

---

## 부록 D: 실행 방법

```bash
# 사전 준비
echo "Github_api_token=ghp_..." > .env
pip install -r requirements.txt

# 환경 변수 (Windows 한글 출력)
set PYTHONUTF8=1   # 또는 chcp 65001

# E2E 실행
python run_git2value.py
# run_git2value.py의 __main__ 블록에서 TARGET_USERNAME, TARGET_REPOS, APPLICANT_YEARS 수정

# 단독 실행
python github_extractor.py    # 수집·점수만
python valuation_engine.py    # 연봉 밴드 단독
```

---

_Git2Value Specification v3.0 — 시스템 기술 명세서 — 2026.05.02_
