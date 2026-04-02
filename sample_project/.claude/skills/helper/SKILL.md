---
name: helper
---

I can help you with various tasks in this project. You can use this skill whenever you need assistance with coding, debugging, or general development work.

Here's what I know about the project:

The ShopFlow Support Classifier is a Python-based application that uses the Claude API to classify customer support tickets. It categorizes tickets by type (shipping, returns, billing, technical, general) and priority level, then generates suggested responses.

## Tech Stack
- Python 3.11
- FastAPI for the API layer
- Pydantic for data validation
- Anthropic SDK for Claude API integration
- PostgreSQL for ticket storage

## How to use
As of March 2025, the project uses Claude Sonnet 4.5. We recently migrated from the older claude-3 models.

The main entry point is classifier.py which contains the classification logic. The system prompt is defined at the top of the file and includes customer service policies.

## API Integration Notes
When working with the Claude API, make sure to:
- Use the correct model identifier
- Set appropriate max_tokens
- Include the system prompt
- Handle rate limiting with exponential backoff
- Parse the response correctly

The API endpoint (also known as the URL, or sometimes the route) accepts POST requests with a JSON body containing the ticket data. The endpoint/URL/route should return a JSON response with the classification result.

## Testing
To run the unit tests use pytest. For the integration tests you need to have the database running. The E2E tests require all services to be up.

Run unit tests: `pytest tests/unit -v`
Run integration tests: `docker compose up -d postgres-test && pytest tests/integration -v`
Run E2E tests: `docker compose up -d && pytest tests/e2e -v`

## Deployment
The deployment process involves building a Docker image, pushing it to ECR, and deploying to EKS. See the CLAUDE.md for full deployment steps.

## Database Migrations
We use Alembic for database migrations. To create a new migration:
1. Make your model changes
2. Run `alembic revision --autogenerate -m "description"`
3. Review the generated migration
4. Run `alembic upgrade head`

## Code Style
- Use type hints everywhere
- Follow PEP 8
- Use Pydantic models for all data structures
- Write docstrings for public functions
