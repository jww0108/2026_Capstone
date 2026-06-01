# EventFlow — 실시간 이벤트 스트리밍 플랫폼

이벤트 기반 마이크로서비스 아키텍처를 직접 구현해보기 위한 프로젝트입니다.
주문 → 재고 확인 → 결제 → 알림으로 이어지는 이벤트 체인을 Apache Kafka로 처리합니다.
**Saga 패턴**을 적용해 분산 환경에서 데이터 일관성을 유지하는 방법을 학습했습니다.

## 아키텍처

![시스템 아키텍처](./docs/architecture.png)

```
[React Client]
     ↓ HTTP
[API Gateway : 8080]
     ↓ Kafka topic: order-created
[Order Service]  →  [Inventory Service]  →  [Payment Service]  →  [Notification Service]
     ↓                     ↓                       ↓                      ↓
  MySQL               MySQL                    MySQL                  WebSocket
```

## 기술 스택

| 구성요소 | 기술 | 선택 이유 |
|---------|------|----------|
| API Gateway | Spring Cloud Gateway | 단일 진입점, 라우팅 |
| 메시지 브로커 | Apache Kafka | 고가용성, 이벤트 순서 보장 |
| 각 서비스 | Spring Boot 3 + JPA | 팀 친숙도, 생태계 |
| 데이터베이스 | MySQL (서비스별 독립) | DB per service 패턴 |
| 컨테이너 | Docker Compose | 로컬 전체 환경 구성 |

## 데모

![주문 처리 흐름 데모](./docs/demo.gif)

## 빠른 시작

```bash
git clone https://github.com/user/eventflow
cd eventflow
docker compose up -d
```

- API Gateway: http://localhost:8080
- Kafka UI: http://localhost:9090
- 각 서비스 헬스체크: http://localhost:808{1-4}/actuator/health

## 학습 포인트

- Saga 패턴(Choreography 방식)을 통한 분산 트랜잭션
- Kafka Consumer Group을 활용한 메시지 소비
- 서비스 간 독립 배포와 DB 격리 전략
