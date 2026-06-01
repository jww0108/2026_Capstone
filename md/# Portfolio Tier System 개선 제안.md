# Portfolio Tier System 개선 제안

## 배경

현재 Git2Value는 GitHub 분석 결과를 기반으로 사용자를 다음과 같이 분류한다.

```text
Entry
Competitive
Top
```

직관적이고 사용자 친화적이라는 장점이 있지만, 현재 구조에는 중요한 문제가 존재한다.

---

# 현재 구조의 문제점

사용자는 티어를 다음과 같이 해석할 가능성이 높다.

```text
Top Tier

→ Top 개발자
```

```text
Competitive Tier

→ 중상위 개발자
```

```text
Entry Tier

→ 초급 개발자
```

그러나 Git2Value가 실제로 분석하는 것은

```text
GitHub 활동

프로젝트 공개도

기술 스택

README

협업 흔적

테스트 존재 여부
```

등이다.

즉,

```text
개발자의 가치
```

를 측정하는 것이 아니라

```text
GitHub 포트폴리오
```

를 측정하는 시스템이다.

따라서 현재 티어 명칭은 실제 측정 대상보다 과도하게 해석될 위험이 있다.

---

# 개선 목표

티어 시스템은 유지한다.

하지만 티어의 의미를

```text
개발자 등급
```

에서

```text
직무별 GitHub 포트폴리오 성숙도
```

로 재정의한다.

---

# 권장 구조

## 기존 구조

```text
Overall Score : 82

Tier : Top
```

---

## 개선 구조 (현재 구현 기준)

```text
GitHub Portfolio Maturity

Primary Domain Portfolio Tier : Top

(예: 서버/백엔드 GitHub Portfolio Tier)
```

---

# 왜 단계적 티어 전략이 필요한가

실제 개발자는 분야마다 역량이 다르다.

예시

```text
Spring
Redis
Kafka
Docker
```

위주의 활동

↓

```text
Backend 강점
```

---

하지만

```text
TensorFlow
PyTorch
MLOps
```

경험은 거의 없음

↓

```text
AI 강점 아님
```

---

현재 시스템

```text
Top
```

↓

무엇이 Top인지 설명 불가

---

권장 시스템 (단계 1: 현재 구현 가능)

```text
Primary Domain Portfolio Tier : Top

보조 도메인 신호 : DevOps/AI 약함
```

↓

설명 가능

---

# 권장 티어 정의

## Entry

설명

```text
기초적인 GitHub 활동 및 프로젝트 경험 존재

직무 관련 경험은 있으나
깊이나 다양성은 제한적
```

---

## Competitive

설명

```text
직무 관련 프로젝트 경험이 충분하며

문서화

기술 활용

프로젝트 완성도

측면에서 일정 수준 이상을 충족
```

---

## Top

설명

```text
직무 관련 경험이 매우 풍부하며

프로젝트 품질

기술 다양성

문서화

지속성

측면에서 높은 성숙도를 보임
```

---

# 티어 산정 방식 권장 (로드맵 단계 2)

아래는 현재 코드에서 즉시 계산되는 값이 아니라, 향후 직무별 독립 티어 도입 시 사용하는 로드맵 기준이다.

## Backend Portfolio Tier

예시 요소

```text
Spring

Django

FastAPI

Node.js

DB 설계

Redis

Kafka

Docker

API 설계

테스트
```

---

## DevOps Portfolio Tier

예시 요소

```text
Docker

Kubernetes

Terraform

Helm

Prometheus

Grafana

CI/CD

AWS
```

---

## AI Portfolio Tier

예시 요소

```text
PyTorch

TensorFlow

LLM

RAG

MLOps

Vector DB

Training Pipeline
```

---

## Data Portfolio Tier

예시 요소

```text
Spark

Airflow

dbt

ETL

Data Warehouse

Data Pipeline
```

---

# 결과 예시

## 기존

```text
Overall Score : 86

Tier : Top
```

---

## 개선 (단계 1: 현재 구현)

```text
GitHub Portfolio Maturity : 86

Primary Domain Portfolio Tier : Top

보조 도메인 신호:
- DevOps/인프라 : 보강 필요
- AI : 보강 필요
```

---

## 개선 (단계 2: 로드맵)

```text
GitHub Portfolio Maturity : 86

Backend Portfolio Tier : Top

DevOps Portfolio Tier : Competitive

Data Portfolio Tier : Entry

AI Portfolio Tier : Entry
```

---

# 설명 가능성 강화

현재

```text
Backend Tier : Top
```

만 제공

↓

설명 부족

---

권장

```text
Backend Tier : Top

근거

- Spring 프로젝트 6개
- Redis 사용 경험
- Docker 활용
- PostgreSQL 설계
- 테스트 코드 존재
```

---

즉

```text
결과
+
근거
```

를 함께 제공

---

# 기업 관점 장점

현재 구조

```text
Top
```

↓

채용 담당자 질문

```text
무엇이 Top인가?
```

---

개선 구조

```text
Backend Portfolio Tier : Top
```

↓

채용 담당자 해석

```text
백엔드 경험이 풍부한 지원자
```

---

설명력이 증가

---

# 취업 준비생 관점 장점

현재

```text
Top
```

↓

행동 지침 없음

---

개선

```text
Backend : Top

DevOps : Competitive

AI : Entry
```

↓

사용자 해석

```text
현재 백엔드 방향성이 강함

AI 직무를 목표로 한다면
관련 프로젝트를 추가해야 함
```

---

성장 방향 제시 가능

---

# 기대 효과

## Before

```text
GitHub 기반 개발자 평가
```

---

## After

```text
GitHub 기반 포트폴리오 진단
(단계적 확장: Primary Domain Tier → 직무별 독립 Tier)
```

---

결과적으로

* 티어 시스템 유지 가능
* 사용자 만족도 유지
* 심사위원 공격 포인트 감소
* 기업 활용성 증가
* 설명 가능성 향상
* 직무 추천 기능과 자연스럽게 연결
* 서비스 신뢰성 향상

---

# 최종 권장 사항

Entry / Competitive / Top 구조는 유지한다.

그러나 이를

```text
개발자 등급
```

으로 사용하지 말고

```text
Primary Domain GitHub Portfolio Tier (현재 구현)
```

로 재정의한다.

가장 권장되는 최종 형태는 다음과 같다.

```text
GitHub Portfolio Maturity : 86

Primary Domain Portfolio Tier : Top

보조 도메인 신호:
- DevOps/인프라 : 보강 필요
- AI : 보강 필요
```

직무별 독립 티어(Backend/DevOps/Data/AI 동시 산정)는 로드맵으로 분리한다.

이 구조는 Git2Value의 핵심 가치인

```text
GitHub 포트폴리오 분석

직무 추천

커리어 진단
```

과 가장 자연스럽게 연결되며,
기업과 취업 준비생 모두에게 이해하기 쉬운 결과를 제공한다.
