# Users REST API

A containerized REST API for creating, retrieving, updating, and deleting user
records in PostgreSQL. It supports filtering by U.S. birth-state abbreviation,
pagination, sorting, input validation, and application/database health checks.

No frontend was made, assummed not required. Use Swagger UI, an HTTP client, or the integration tests.
Authentication and authorization are not implemented in this version.

## Technologies

| Technology | Purpose |
| --- | --- |
| Python 3.13 | Application runtime in Docker |
| FastAPI and Uvicorn | REST endpoints, request handling, and HTTP server |
| Pydantic | Request/response models and input validation |
| PostgreSQL 17 | Persistent relational storage |
| Psycopg 3 | Parameterized SQL and database transactions |
| Docker and Docker Compose | Images, services, networking, and storage |
| pytest and FastAPI TestClient | Automated API/database integration tests |
| httpx2 | HTTP client dependency used by the test client |

Dependency versions are specified in the project's requirements files.

## Code Organization

This README targets the four-file organization described below. Complete that
reorganization before using the matching Dockerfile/configurations in this document.

| Path | Responsibility |
| --- | --- |
| `backend/main.py` | FastAPI app, lifespan startup, health routes, exception handlers |
| `backend/users.py` | User routes and their SQL operations |
| `backend/schemas.py` | Models, state validation, sorting types, `PAGE_SIZE` |
| `backend/database.py` | Connections, table initialization, readiness query |
| `backend/tests/conftest.py` | Shared fixtures, test client, database reset |
| `backend/tests/test_api.py` | CRUD, invalid-input, filtering, pagination, sorting, and health tests |
| `backend/requirements.txt` | Runtime dependencies |
| `backend/requirements-test.txt` | Runtime plus testing dependencies |
| `backend/Dockerfile` | Runtime and test image stages |
| `compose.yaml` | Normal application/database configuration |
| `compose.test.yaml` | Standalone test runner/database configuration |

Fixtures may remain in `test_api.py` initially; use `conftest.py` when sharing them.
If the existing test file is named `test_main.py`, move it under `backend/tests/`;
the configured pytest command discovers either `test_*.py` filename.

## Build and run

### Prerequisites

- Docker Desktop with Linux containers, or Docker Engine with Compose v2.
- Docker must be running.
- Network access for image/package downloads during the first build.
- Run the commands from the project root containing both Compose files.

### 1. Configure the normal database

Keep an existing `backend/.env` when retaining an existing database. Otherwise,
create one using the following local-development example:

```dotenv
POSTGRES_USER=users
POSTGRES_PASSWORD=change-me
POSTGRES_DB=users
DATABASE_URL=postgresql://users:change-me@db:5432/users
```

Use a suitable private password. Keep `.env` out of Git and the Docker build
context. Include only placeholder values in `.env.example`.
The URL must match the configured credentials and database name. URL-encode
special characters in URL credentials. Inside Compose, the database hostname is
the service name `db`, not `localhost`.

For an existing PostgreSQL volume, changing the environment variables does not
reset its stored credentials. Keep the existing Compose project name when reusing
that volume; moving to a differently named project creates separate resources.

### 2. Build and start

```sh
docker compose up --build -d
```

Compose starts PostgreSQL, waits for its health check, and starts the API.
FastAPI's lifespan startup initializes the users table if it does not exist.

- API base URL: http://localhost:8000
- Swagger UI: http://localhost:8000/docs
- Readiness: http://localhost:8000/health
- Liveness: http://localhost:8000/health/live

View status and logs:

```sh
docker compose ps
docker compose logs -f web
```

### 3. Stop

```sh
docker compose down
```

The normal database uses the persistent `pgdata` volume, which survives ordinary
container removal. Adding `--volumes` to this normal shutdown command deletes
that volume and its database data.

## API endpoint examples

Requests and JSON below can be entered in Swagger UI using **Try it out**.

### Create a user

```http
POST /api/users
Content-Type: application/json

{
  "name": " Alice ",
  "age": 25,
  "birth_state": " nj "
}
```

Successful response: `201 Created`. Illustrative body (the actual ID can differ):

```json
{
  "id": 1,
  "name": "Alice",
  "age": 25,
  "birth_state": "NJ"
}
```

### Retrieve users

```http
GET /api/users
GET /api/users/1
```

The collection returns a JSON array; the individual route returns one user.
Use the actual ID returned by POST. A nonexistent user returns `404`.

### Filter, paginate, and sort

```http
GET /api/users?birth_state=NJ
GET /api/users?page=2
GET /api/users?sort_by=age&order=desc
GET /api/users?birth_state=NJ&page=1&sort_by=name&order=asc
```

| Parameter | Behavior |
| --- | --- |
| `birth_state` | Optional valid two-letter state code; normalized to uppercase |
| `page` | Positive page number; defaults to 1 |
| `sort_by` | `id`, `name`, `age`, or `birth_state`; defaults to `id` |
| `order` | `asc` or `desc`; defaults to `asc` |

The page size is controlled by `PAGE_SIZE` in `schemas.py` (currently 2 in the
discussed implementation). Filtering applies before pagination. ID is used as
the secondary sort key when primary values match. A valid filter or page with
no matching records returns `200` and `[]`.

### Update a user

```http
PUT /api/users/1
Content-Type: application/json

{
  "name": "Hannah Gallagher",
  "age": 32,
  "birth_state": "PA"
}
```

Successful response: `200 OK` and the updated user. The existing PUT contract
supports partial updates: omitted fields retain their current values.

### Delete a user

```http
DELETE /api/users/1
```

Successful response: `200 OK`. Retrieving the deleted user afterward returns
`404 Not Found`.

### Health checks

| Route | Meaning |
| --- | --- |
| `GET /health/live` | API is responding; returns `200` with `{"status":"alive"}` |
| `GET /health` | Database readiness; returns `200` ready or `503` not_ready |

Readiness opens a real database connection. With the discussed `check_database()`
implementation, it also checks the users table/columns with a zero-row SELECT.
It does not prove every write operation will succeed. Initial database failure
can prevent application startup; a later outage can produce readiness `503`
while liveness remains `200`.

### Validation and errors

- Names are required and nonblank, with a maximum length of 1,000 characters.
- Age must satisfy the configured integer validation and range 0 to 32,767.
- Birth state is a valid abbreviation from the 50-state allowed set; DC and
  territories are excluded unless explicitly added.
- Invalid input/query parameters produce `422`.
- Missing users produce `404`.
- Database availability failures are mapped to `503`; unexpected database
  failures are mapped to `500` without exposing database details to clients.

## Execute the integration tests

Tests require only Docker on the host. The test image contains pytest and its
dependencies; PostgreSQL runs in a separate test container.

```sh
python run_tests.py
```

The command builds the test image, starts `test-db`, waits for database readiness,
and runs `python -m pytest -q tests`. Exit code 0 indicates success; a nonzero code
indicates test or execution failure. The test runner's result is returned by
`--exit-code-from tests`.

The python `run_tests.py` file will handle cleaning up the test containers. Removes containers and deletes the volume for database as well.

For a CI script, capture the test command's exit status before cleanup and return
it afterward. Otherwise cleanup can overwrite the status reported by the shell.

### Repeatability and scope

- The standalone test Compose file never reads the normal `.env` or mounts `pgdata`.
- `test-db` uses temporary storage that is discarded when it stops.
- The test service sets `DATABASE_URL` to the dedicated `users_test` database and
  explicitly enables reset with `ALLOW_TEST_DB_RESET=1`.
- Fixtures verify the database is a test database, then truncate users before
  and after each test. Never point these fixtures at normal application data.
- Each test creates its own records and uses IDs returned by POST.
- `with TestClient(app)` runs the application startup/shutdown lifecycle.
- Tests invoke FastAPI in-process and use real PostgreSQL connections. They do
  not by themselves test Uvicorn sockets, host port forwarding, or TLS.

Coverage should include creating/retrieving/updating/deleting users; nonexistent
users; invalid input; birth-state filtering and normalization; pagination derived
from `PAGE_SIZE`; every supported sort column/direction; and both health routes.
Do not run parallel pytest workers against this one shared test database.

## Architectural decisions

1. **Small modules:** application wiring, user operations, models, and database
   infrastructure are separated into four files without a forwarding-only service layer.
2. **Direct SQL:** Psycopg keeps SQL behavior visible. Values use parameters;
   dynamic identifiers use `sql.Identifier` and allowed sort fields.
3. **Pydantic validation:** invalid requests are rejected before endpoint writes;
   database constraints provide a second layer of data protection.
4. **Transactions:** connection context managers commit successful operations,
   roll back execution failures, and close connections. Do not return success
   before the transaction context has exited. Lost commit acknowledgements can
   leave outcomes uncertain; no automatic creation retry is assumed.
5. **Lifespan startup:** table initialization is explicit instead of running SQL
   during module import. `CREATE TABLE IF NOT EXISTS` is bootstrap logic, not a
   migration system for existing tables.
6. **Container separation:** API and PostgreSQL use different containers on an
   explicitly declared network. Normal data is persistent; test data is temporary.

## AI coding assistant use and validation

ChatGPT was used to explain FastAPI/Psycopg/Docker behavior, suggest the simpler
module organization, review SQL safety and validation, and draft API tests,
documentation, and Compose configuration. AI suggestions are treated as proposed
changes rather than accepted without review.

During the development discussion, suggestions were reviewed against the existing
code and requirements: parameterized values, allowed sort columns, transaction
boundaries, HTTP responses, test isolation, and state normalization were checked.

The repeatable validation process for the final implementation is:

1. Review generated changes and imports after reorganizing the code.
2. Build and run the application with Docker Compose.
3. Exercise representative API operations through Swagger UI.
4. Run the integration-test command above against the dedicated database.
5. Correct failures and repeat until the final checkout passes.

**Final-checkout validation status:** local Docker/test results for the manually
assembled four-file version have not been provided. This README does not claim a
passing count or a successful Docker run. Record the actual result after running
the commands before submitting the challenge.

## Docker configuration reference

Use the following configurations together. They assume the Dockerfile has named
`runtime` and `test` stages and that the runtime entry point remains `main:app`.
A compatible Dockerfile is included below; update yours if needed.

### `compose.yaml`

```yaml
services:
  db:
    image: postgres:17-alpine
    env_file: ./backend/.env
    volumes:
      - pgdata:/var/lib/postgresql/data
    networks:
      - users-net
    healthcheck:
      test: ["CMD", "pg_isready", "-h", "localhost", "-U", "users"]
      interval: 2s
      timeout: 3s
      retries: 15
  
  web:
    build: ./backend
    env_file: ./backend/.env
    ports:
      - "127.0.0.1:8000:8000"
    networks:
      - users-net
    depends_on:
      db:
        condition: service_healthy
  
volumes:
  pgdata:

networks:
  users-net:
    driver: bridge
```

### `compose.test.yaml`

```yaml
name: ppc-users-tests

services:
  test-db:
    image: postgres:17-alpine
    environment:
      POSTGRES_USER: users_test
      POSTGRES_PASSWORD: test-only
      POSTGRES_DB: users_test
    tmpfs:
      - /var/lib/postgresql/data
    networks:
      - test-net
    healthcheck:
      test: ["CMD", "pg_isready", "-h", "localhost", "-U", "users_test", "-d", "users_test"]
      interval: 2s
      timeout: 3s
      retries: 30
      start_period: 5s

  tests:
    build: ./backend
    environment:
      DATABASE_URL: postgresql://users_test:test-only@test-db:5432/users_test
      ALLOW_TEST_DB_RESET: "1"
    networks:
      - test-net
    depends_on:
      test-db:
        condition: service_healthy
    command: ["python", "-m", "pytest", "-v", "tests"]

networks:
  test-net:
    driver: bridge
    internal: true
```

`networks:` at the top level declares each network. The service-level entries
explicitly attach the relevant containers. Compose scopes network names to its
project, and service-name DNS resolves `db` or `test-db`; static IPs and fixed
container names are unnecessary. Neither configuration publishes PostgreSQL.
The normal API is bound to host loopback for local development.

`internal: true` prevents external routing from the test runtime network. Package
installation occurs during image building, before containers join that network.
The test network is separate from the normal application's network.

### Compatible `backend/Dockerfile`

```dockerfile
FROM python:3.13-slim AS base

ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN useradd --create-home appuser && chown appuser /app
COPY --chown=appuser:appuser main.py users.py schemas.py database.py ./
USER appuser

FROM base AS test
USER root
COPY requirements-test.txt .
RUN pip install --no-cache-dir -r requirements-test.txt
COPY --chown=appuser:appuser tests ./tests
USER appuser
CMD ["python", "-m", "pytest", "-q", "tests"]

FROM base AS runtime
EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

`requirements-test.txt` should include `-r requirements.txt`, pytest, and httpx2.
The runtime image does not need testing packages. If your requirements file also
references a constraints file, copy that file before the corresponding pip command.
