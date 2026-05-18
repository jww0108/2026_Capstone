# 배달 주문 관리 시스템

배달 음식점 사장님들이 여러 플랫폼(배민, 쿠팡이츠, 요기요)의 주문을 한 곳에서 통합 관리할 수 있는 웹 서비스입니다.

## 문제 정의

소규모 음식점 운영자는 여러 배달 플랫폼의 주문을 각각 확인해야 하여 주문 누락과 처리 지연이 빈번하게 발생합니다.
이 서비스는 모든 플랫폼의 주문을 실시간으로 통합하여 처리 효율을 높입니다.

## 기술 스택

| 항목 | 기술 | 선택 이유 |
|------|------|-----------|
| 백엔드 | Spring Boot 3.x | 성숙한 생태계, 팀 역량 |
| DB | MySQL 8.0 | 트랜잭션 안정성 |
| 캐시 | Redis | 실시간 주문 상태 관리 |
| 메시지 큐 | RabbitMQ | 플랫폼별 주문 비동기 처리 |
| 컨테이너 | Docker Compose | 로컬 개발 환경 통일 |
| CI/CD | GitHub Actions | 자동 빌드·배포 |

## 실행 방법

```bash
# 저장소 클론
git clone https://github.com/username/delivery-manager.git
cd delivery-manager

# 환경 변수 설정
cp .env.example .env
# .env 파일에서 DB 비밀번호 및 API 키 설정

# 전체 서비스 실행 (DB, Redis, RabbitMQ 포함)
docker-compose up -d

# API 서버 접속: http://localhost:8080
# Swagger UI: http://localhost:8080/swagger-ui.html
```

## 주요 기능

- 배민·쿠팡이츠·요기요 주문 실시간 수신 및 통합 대시보드
- 주문 상태(접수→조리중→완료) 추적
- 매출 통계 및 시간대별 주문량 분석

## 시스템 아키텍처

![아키텍처 다이어그램](docs/architecture.png)
![주문 처리 흐름](docs/order-flow.png)

## 테스트

```bash
./mvnw test
# 커버리지 리포트: target/site/jacoco/index.html
```

## 팀 구성 및 기여

| 이름 | 역할 | 주요 기여 |
|------|------|-----------|
| 김OO | 백엔드 리드 | 주문 통합 API, RabbitMQ 연동 |
| 이OO | 백엔드 | 인증·권한, 통계 API |
| 박OO | 프론트엔드 | 대시보드 UI, 실시간 알림 |
