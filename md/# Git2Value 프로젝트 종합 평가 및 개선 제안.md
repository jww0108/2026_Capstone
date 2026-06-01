# Git2Value 프로젝트 종합 평가 및 개선 제안

## Executive Summary

Git2Value는 GitHub Repository를 분석하여 신입 개발자의 포트폴리오를 진단하고 직무 적합도를 추천하는 서비스이다.

초기에는 "개발자 가치 평가"에 가까운 포지셔닝을 가지고 있었으나, 실제 코드와 설계 문서를 분석한 결과 이 프로젝트의 진정한 가치는 개발자 평가가 아니라 다음 영역에 있다.

> GitHub 기반 커리어 진단 및 기술 프로파일링 서비스

즉, 지원자를 면접관처럼 판정하는 도구가 아니라 지원자의 GitHub 활동을 해석·진단·요약하여 취업 준비생의 개선 방향 설정을 돕는 서비스로 보는 것이 적절하다.

---

# 프로젝트 수준 평가

## 캡스톤 프로젝트 기준

평가: 상위 10% 수준

### 강점 (현재 구현 기준)

* 실제 GitHub API 활용
* GitHub API 기반 다중 지표 분석 (레포별 구조/커밋/README)
* README 기반 LLM 평가
* 벡터 검색 기반 직무 매칭
* FAISS + 룰 기반 도메인 리랭킹 + Optional 로컬 LLM README 평가
* 실제 서비스 형태 구현

### 기술 역량 평가

| 항목         | 평가 |
| ---------- | -- |
| Python     | A- |
| Backend 설계 | B+ |
| 데이터 엔지니어링  | B+ |
| AI 활용      | B  |
| 시스템 설계     | B+ |
| 연구 검증      | C+ |

---

# 현재 포지셔닝의 문제

현재 설명

```text
GitHub를 분석하여 개발자의 가치를 평가합니다.
```

문제점

* 개발자 가치와 GitHub 활동은 동일하지 않음
* GitHub 활동이 적어도 우수한 개발자는 존재
* 비공개 프로젝트 경험은 반영 불가
* 점수의 객관적 타당성 검증 부족

따라서 다음 표현이 더 적절함

```text
GitHub 기반 포트폴리오 진단 및 직무 추천 서비스
```

또는

```text
GitHub Career Coach
```

또는

```text
GitHub 기술 프로파일링 플랫폼
```

---

# 취업 준비생 관점 가치

## 실제 문제

취준생은 보통 다음을 모른다.

```text
내 GitHub 수준은 어느 정도인가?

어떤 직무가 적합한가?

무엇을 개선해야 하는가?
```

---

## 제공 가능한 가치

### 1. 포트폴리오 진단

예시

```text
강점
- Spring 경험
- Docker 경험

약점
- 테스트 코드 부족
- CI/CD 없음
- 협업 흔적 부족
```

---

### 2. 직무 탐색

GitHub 활동 기반

```text
Backend 적합도

DevOps 적합도

Data Engineer 적합도

AI Engineer 적합도
```

제공 가능

---

### 3. 성장 방향 제시

예시

```text
현재 수준

Backend Junior

다음 단계

- Redis
- Docker
- AWS
- 테스트 자동화
```

---

### 4. 포트폴리오 개선 가이드

현재 점수보다

```text
무엇을 개선해야 하는가
```

가 더 중요함

---

# 채용 담당자 관점 가치 (로드맵 분리)

아래 항목은 **현재 코드에 완전 구현된 기능**이 아니라, 제품 확장 시 유효한 **로드맵 시나리오**로 분리해 관리해야 한다.

## 핵심 가치

기업은 개발자를 평가하고 싶은 것이 아니라

```text
지원자를 빠르게 이해하고 싶어한다.
```

---

## 활용 시나리오

### GitHub Summary Engine (로드맵)

입력 예시

```text
GitHub Repository 다수
```

출력

```text
주요 기술
- Spring
- Redis
- Kafka

프로젝트 유형
- 쇼핑몰
- 예약 시스템

강점
- 테스트 존재
- CI/CD 구축

약점
- 협업 경험 부족
```

---

### Resume Validation (로드맵)

이력서

```text
Kubernetes 경험
```

GitHub

```text
실제 사용 흔적 없음
```

확인 가능

---

### Hidden Skill Discovery (로드맵)

이력서에는 없지만

```text
Terraform

Prometheus

ArgoCD
```

경험 발견 가능

---

### 면접 질문 생성 (로드맵)

예시

```text
Kafka 프로젝트 경험 존재

→ Kafka 관련 질문
```

---

# 기존 ATS 대비 차별점

## 기존 ATS

```text
이력서
↓
키워드 추출
↓
JD 매칭
```

문제

```text
지원자가 적은 내용만 평가
```

---

## Git2Value

```text
실제 코드

실제 프로젝트

실제 커밋

실제 GitHub 활동
```

분석

---

## 핵심 차별화

Self-Reported Data

↓

Behavioral Data

---

즉

```text
지원자가 말한 것

이 아니라

지원자가 실제로 만든 것
```

을 분석한다.

---

# 점수 시스템 평가

## 점수를 제거해야 하는가?

아니다.

점수는 유지하는 것이 좋다.

---

## 점수의 문제

현재

```text
개발자 점수 82점
```

처럼 해석될 위험 존재

---

실제로는

```text
GitHub Portfolio Score
```

에 가까움

---

## 권장 구조

### 잘못된 구조

```text
Overall Score 82
```

---

### 권장 구조 (현재 구현 정합 버전)

```text
GitHub Portfolio Score 82

개발 활동량 (Contribution, max 60): 46

프로젝트 운영도 (Quality, max 30): 24

작업 일관성 (Consistency, max 10): 8
```

---

### 직무 적합도 (현재 구현 표현)

```text
상위 공고 매칭 결과 기반 추천

(유사도 + 도메인 리랭킹 결과)
```

---

## 점수의 역할

평가가 아니라

진단

비교

개선 방향 제시

---

# 향후 개선 우선순위 (로드맵)

## Priority 1 (로드맵)

협업 능력 분석

현재 부족

추가 권장

```text
Issue

Pull Request

Code Review

Discussion

Branch Strategy
```

---

## Priority 2 (로드맵)

코드 품질 분석

현재 활동량 비중이 높음

추가 권장

```text
테스트

Lint

문서화

Dependency 관리

CI/CD
```

---

## Priority 3 (로드맵)

성장성 분석

예시

```text
6개월 전

README 없음

현재

README 존재
CI 존재
테스트 존재
```

---

기업은 현재 수준보다 성장 속도를 높게 평가하는 경우가 많음

---

## Priority 4 (로드맵)

설명 가능한 결과

예시

```text
Backend 적합도 88
```

보다

```text
Spring 프로젝트 5개

Docker 사용

DB 설계 경험

때문에

Backend 적합도 88
```

가 더 설득력 있음

---

# 심사위원 대응 전략

## 피해야 할 주장

```text
개발자의 가치를 평가합니다.
```

```text
채용 여부를 판단합니다.
```

---

## 권장 주장

```text
GitHub 활동을 분석하여

취업 준비생에게는

직무 적합성과 포트폴리오 개선 방향을 제공하고

채용 담당자에게는

지원자의 기술 경험을 빠르게 이해할 수 있는 요약 리포트를 제공합니다.
```

---

# 현재 구현 vs 로드맵 정리

## 현재 구현된 기능

- GitHub API 기반 레포 분석 (커밋/트리/README/작성자 신호)
- 포트폴리오 진단 (레포별 카드 + 종합 요약)
- 직무 매칭 (FAISS + 도메인 리랭킹)
- 시장 연봉 밴드 조회 (점핏·원티드 데이터 기반)
- Optional 로컬 LLM README 평가

## 로드맵 기능

- 채용 담당자용 Resume Validation
- Hidden Skill Discovery 전용 리포트
- 면접 질문 자동 생성
- 대량 레포 일괄 요약 (예: 50개 단위)
- PR/Issue/Code Review 기반 협업 분석

---

# 최종 결론

Git2Value는 "개발자 평가 서비스"로 접근할 경우 신뢰성 문제와 검증 문제에 직면한다.

반면 다음과 같이 정의하면 상당한 가치가 존재한다.

```text
GitHub 기반 커리어 코치

GitHub 기반 기술 프로파일러

GitHub 기반 채용 보조 요약 엔진
```

이 프로젝트의 진짜 강점은

개발자의 가치를 판단하는 것이 아니라

GitHub에 축적된 개발 경험을 구조화하여

취업 준비생과 채용 담당자의 의사결정을 돕는 데 있다.
