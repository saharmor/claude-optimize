# ShopFlow Support Classifier

## Project Overview

This is the ShopFlow customer support ticket classifier. It uses the Anthropic Claude API to automatically categorize incoming support tickets, assign priority levels, and generate draft responses for the support team. The classifier processes tickets from our Zendesk integration and routes them to the appropriate team based on the classification results. We built this to reduce the average response time from 4 hours to under 30 minutes for most ticket categories.

## Code Style Guidelines

- Use type hints for all function parameters and return values
- Use type hints on every function signature: always annotate arguments with types
- All functions must have typed parameters and typed return values
- Follow PEP 8 naming conventions (snake_case for functions, PascalCase for classes)
- Use Pydantic BaseModel for all data structures that cross API boundaries
- Prefer dataclasses for internal-only data structures
- Keep functions under 50 lines where possible
- Use meaningful variable names: avoid single-letter names except in list comprehensions

## API Integration Notes

When working with the Anthropic SDK, always use the latest stable version. We use the `messages.create` endpoint for all classification calls. The system prompt is defined in `SYSTEM_PROMPT` at the top of `classifier.py`. Tool definitions are in the `ALL_TOOLS` list. Make sure to handle rate limiting gracefully: the SDK handles retries automatically but we have additional retry logic for robustness.

For testing API calls, use the mock client in tests rather than making real API calls. The mock is configured in `conftest.py` and supports all the endpoints we use.

## Deployment Guide

### Prerequisites
- AWS CLI v2 configured with production credentials (profile: shopflow-prod)
- Docker 24+ installed and running
- Access to the shopflow-prod ECR repository (ask DevOps for permissions)
- kubectl configured for the production EKS cluster

### Build and Push
1. Build the Docker image: `docker build -t shopflow-classifier .`
2. Tag for ECR: `docker tag shopflow-classifier:latest 123456789.dkr.ecr.us-east-1.amazonaws.com/shopflow-classifier:latest`
3. Login to ECR: `aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin 123456789.dkr.ecr.us-east-1.amazonaws.com`
4. Push to ECR: `docker push 123456789.dkr.ecr.us-east-1.amazonaws.com/shopflow-classifier:latest`

### Deploy to EKS
1. Update the image tag in `k8s/deployment.yaml`
2. Apply the deployment: `kubectl apply -f k8s/deployment.yaml`
3. Verify rollout: `kubectl rollout status deployment/shopflow-classifier`
4. Check logs: `kubectl logs -f deployment/shopflow-classifier`

### Database Migrations
1. Run pending migrations: `alembic upgrade head`
2. Verify migration status: `alembic current`
3. If rollback is needed: `alembic downgrade -1`

## Testing Instructions

### Unit Tests
Run the unit test suite with: `pytest tests/unit -v --cov=src --cov-report=html`

The unit tests mock all external dependencies (Claude API, database, Zendesk). Coverage threshold is 80%: the CI pipeline will fail if coverage drops below this.

### Integration Tests
1. Start the test database: `docker compose up -d postgres-test`
2. Run migrations against test DB: `DATABASE_URL=postgresql://test:test@localhost:5433/shopflow_test alembic upgrade head`
3. Run integration tests: `pytest tests/integration -v --timeout=60`
4. Tear down: `docker compose down`

### End-to-End Tests
1. Start all services: `docker compose up -d`
2. Wait for health checks: `./scripts/wait-for-healthy.sh`
3. Run E2E suite: `pytest tests/e2e -v --timeout=120`
4. Check the test report in `reports/e2e-results.html`

## File References

- See `src/legacy_router.py` for the old routing logic (kept for reference)
- Config templates in `config/staging.yaml` and `config/production.yaml`
- The old deployment script is at `scripts/deploy_v1.sh`: do not use this anymore
- Zendesk webhook configuration is in `infrastructure/terraform/zendesk.tf`
- Load testing scripts are in `tests/load/locustfile.py`

## Environment Variables

- `ANTHROPIC_API_KEY`: Claude API key (required)
- `DATABASE_URL`: PostgreSQL connection string
- `ZENDESK_SUBDOMAIN`: Zendesk instance subdomain
- `ZENDESK_API_TOKEN`: Zendesk API authentication token
- `SLACK_WEBHOOK_URL`: Slack webhook for escalation notifications
- `SENTRY_DSN`: Sentry error tracking (optional in development)
- `LOG_LEVEL`: Logging level, defaults to INFO
