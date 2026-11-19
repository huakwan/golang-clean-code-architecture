# Clean Code Architecture — Python (Django + DRF) + Vue.js 3 + Go Reference

Re-implementation of Uncle Bob's Clean Architecture from the original Go template (`max38/golang-clean-code-architecture`) into **Python (Django 5 + Django REST Framework)** with **JWT Authentication**, **Polyglot Dynamic CRUD (PostgreSQL + MongoDB)**, **Avro Schema Reflection**, **Swagger UI**, and a **Vue.js 3** frontend.

---

## Repository Structure

```text
golang-clean-code-architecture/
├── backend/                  # Python + Django + DRF Clean Architecture API (:8000)
│   ├── pyproject.toml        # uv dependencies, Python >=3.12,<3.14, ruff config
│   ├── uv.lock
│   ├── manage.py
│   ├── pytest.ini
│   ├── env.template
│   └── src/
│       ├── config/           # env_config, settings, test_settings, urls, crud_models registry
│       ├── domain/           # Pure Python dataclasses, StrEnum, ABCs (zero framework imports)
│       ├── usecases/         # UserUsecase, CrudUsecase
│       ├── interfaces/       # DRF APIView handlers + PostgreSQL & MongoDB repositories
│       ├── infrastructure/   # Django ORM models/migrations, Mongo connector, DI container, JWT auth, middlewares
│       ├── shared/           # HS256 JWT, bcrypt, slug converter, Avro schema generator, utils
│       └── tests/            # Unit tests (domain/shared/usecases/interfaces) & integration tests
├── frontend/                 # Vue 3 + Vite + TypeScript + Pinia + Vue Router + Axios + Tailwind (:5173)
├── golang-reference/         # Original Go (GoFiber + GORM) reference API (:3000)
├── docker/postgres/          # PostgreSQL init script (creates django_clean_arch DB)
└── docker-compose.yml        # PostgreSQL 15 (postgres-15) + MongoDB 6.0.8 (mongo-6)
```

---

## Local Databases (Docker Compose)

Start PostgreSQL 15 (`:5432`) and MongoDB 6.0.8 (`:27017`):

```bash
docker compose up -d
```

- On a fresh container, `docker/postgres/init-db.sql` automatically creates the `django_clean_arch` database alongside the default `postgres` database.
- If `postgres-15` was already initialized earlier, create `django_clean_arch` once:

```bash
docker exec -it postgres-15 psql -U postgres -c "CREATE DATABASE django_clean_arch;"
```

---

## Backend (Python — Django + DRF, `:8000`)

### Features
- **Clean Architecture Layers**: strict inward dependency rules (`domain/` has zero Django/DRF/PyMongo imports, verified by AST unit test).
- **User Management & JWT Auth (HS256)**:
  - Register (email regex validation, `bcrypt` hashing, auto-creates default `user_permissions` record)
  - Login (`access` + `refresh` tokens persisted in `user_tokens` via upsert)
  - Refresh Token (validates DB session, rotates `access` token, preserves original `refresh` token expiry)
  - Logout (revokes `user_tokens` session)
  - Profile (`GET /api/v1/users/profile` via Bearer JWT)
  - Automatic fail-safe audit logging of auth events (`USER_REGISTER`, `USER_LOGIN`, `USER_REFRESH_TOKEN`, `USER_LOGOUT`) into MongoDB `activity_logs`
- **Polyglot Dynamic CRUD Engine (`/api/v1/data/<slug>/...`)**:
  - Model registry (`src/config/crud_models.py`) routing slugs to **PostgreSQL** (`users`, `user-tokens`, `user-permissions`) or **MongoDB** (`activity-logs`)
  - Model discovery (`GET /api/v1/data/models/`) returning `slug`, `label`, `datasource`, and `allowed_operations`
  - Automatic Avro Schema generation (`GET /api/v1/data/<slug>/describe`), hiding sensitive fields (`password`)
  - Operation-level enforcement via `allowed_operations()` (`activity-logs` allows `read` and `delete` only; `POST`/`PUT` return `405 Method Not Allowed`)
  - Accurate pagination (`_page`, `_pageSize`, max `1000`) using `count()` before slicing
- **Interactive API Docs**: OpenAPI 3.0 + Swagger UI at `http://localhost:8000/swagger/`

### Setup & Run (with `uv`)

```bash
cd backend
cp env.template .env
uv sync
uv run python manage.py migrate
uv run python manage.py runserver 8000
```

- API Base URL: `http://localhost:8000/api/v1/`
- Swagger UI: `http://localhost:8000/swagger/`

### Tests & Quality Checks

```bash
cd backend
uv run ruff check src
uv run python -m compileall -q src
uv run pytest src/tests -v --cov=src/domain --cov=src/shared --cov=src/usecases --cov-report=term-missing
```

### API Endpoints

| Method | Endpoint | Auth | Description |
| :--- | :--- | :---: | :--- |
| `GET` | `/api/v1/` | Public | Health check (`name`, `version`) |
| `POST` | `/api/v1/users/register` | Public | Register new user |
| `POST` | `/api/v1/users/login` | Public | Login and issue JWT `access` + `refresh` tokens |
| `POST` | `/api/v1/users/refresh-token` | Public | Rotate `access` token using `refresh_token` |
| `POST` | `/api/v1/users/logout` | Public | Revoke session tokens |
| `GET` | `/api/v1/users/profile` | Bearer JWT | Get current authenticated user |
| `GET` | `/api/v1/data/models/` | Bearer JWT | List registered models, datasources & `allowed_operations` |
| `GET` | `/api/v1/data/<slug>/describe` | Bearer JWT | Get Avro schema for entity |
| `GET` | `/api/v1/data/<slug>/` | Bearer JWT | Paginated list (`_page`, `_pageSize`) with `data_schema` |
| `POST` | `/api/v1/data/<slug>/` | Bearer JWT | Create record (`405` if disallowed) |
| `GET` | `/api/v1/data/<slug>/<id>` | Bearer JWT | Retrieve record by ID |
| `PUT` | `/api/v1/data/<slug>/<id>` | Bearer JWT | Update record by ID (`405` if disallowed) |
| `DELETE` | `/api/v1/data/<slug>/<id>` | Bearer JWT | Delete record by ID |
| `GET` | `/swagger/` | Public | Interactive Swagger UI |

---

## Frontend (Vue.js 3, `:5173`)

Built with **Vue 3 (`<script setup lang="ts">`) + Vite + TypeScript + Pinia + Vue Router + Axios + Tailwind CSS + Vitest**, connected to the Python Django + DRF backend (`http://localhost:8000`).

### Features
- **Auth & Session Lifecycle**: Register, Login, `GET /api/v1/users/profile`, JWT Token Inspector, manual Refresh Token test, Logout, and automatic 401 refresh-and-retry via Axios interceptor.
- **Dashboard**: Real-time backend health check (`GET /api/v1/`) and direct links to Data Explorer, Profile, and Swagger UI (`/swagger/`).
- **Dynamic Data Explorer (PostgreSQL & MongoDB)**:
  - Discovers registered models dynamically from `GET /api/v1/data/models/` with datasource badges (`postgresql` / `mongodb`).
  - Avro Schema viewer (`AvroSchemaViewer.vue`) and schema-driven table (`DynamicDataTable.vue`) with pagination and record detail modal.
  - Schema-driven Create/Edit form modal (`DynamicFormModal.vue`) and Delete confirmation dialog, automatically gated by each model's `allowed_operations` (e.g., `activity-logs` shows View & Delete only).

### Setup & Run Frontend

```bash
cd frontend
cp env.template .env
npm install
npm run dev
```

The app runs at `http://localhost:5173`.

### Frontend Tests & Build

```bash
cd frontend
npm run test:unit
npm run type-check
npm run build
```

---

## Go Reference API (`golang-reference/`, `:3000`)

The original Go (GoFiber + GORM) project is preserved in `golang-reference/` and remains runnable on `:3000`:

```bash
cd golang-reference
cp env.template .env.dev
go run src/infrastructure/database/postgres/migration/main.go
go run src/infrastructure/gofiber/main.go
```

- API Base URL: `http://localhost:3000/api/v1/`
- Swagger UI: `http://localhost:3000/swagger/`
