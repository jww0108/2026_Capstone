# E-Commerce REST API

A production-ready RESTful API for an e-commerce platform built with FastAPI and PostgreSQL.

## Problem Statement

Modern e-commerce platforms need scalable, maintainable APIs that can handle high traffic while ensuring data consistency. This project demonstrates clean architecture principles applied to a real-world domain.

## Tech Stack

| Component | Technology | Reason |
|-----------|-----------|--------|
| Web Framework | FastAPI | High performance, automatic OpenAPI docs |
| Database | PostgreSQL | ACID transactions, JSON support |
| Cache | Redis | Session management, cart caching |
| Auth | JWT + OAuth2 | Stateless, industry standard |
| Container | Docker + Compose | Reproducible environment |

## Setup

```bash
# Clone the repository
git clone https://github.com/username/ecommerce-api.git
cd ecommerce-api

# Start all services
docker-compose up -d

# The API will be available at http://localhost:8000
# Interactive docs at http://localhost:8000/docs
```

## API Overview

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/auth/login` | POST | User authentication |
| `/products` | GET/POST | List/create products |
| `/orders` | GET/POST | Order management |
| `/cart` | GET/PUT | Cart operations |

## Screenshots

![API Documentation](docs/images/swagger-ui.png)
![Architecture Diagram](docs/images/architecture.png)

## Testing

```bash
pytest tests/ -v --cov=app
```
