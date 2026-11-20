# Clean Code Architecture — Python (Django + DRF) + Vue.js 3 + Go Reference

Re-implementation of Uncle Bob's Clean Architecture from the original Go template (`max38/golang-clean-code-architecture`) into **Python (Django 5 + Django REST Framework)** with **JWT Authentication**, **Polyglot Dynamic CRUD (PostgreSQL + MongoDB)**, **Avro Schema Reflection**, **Swagger UI**, and a **Vue.js 3** frontend.

---

## Repository Structure

```text
golang-clean-code-architecture/
├── backend/                  # Python + Django + DRF Clean Architecture API (:8000)
│   ├── Makefile              # Automation targets (run, migrate, test, lint, typecheck, check)
│   ├── pyproject.toml        # uv dependencies, Python >=3.12,<3.14, ruff & mypy config
│   ├── uv.lock
│   ├── manage.py
│   ├── pytest.ini
│   ├── env.template
│   └── src/
│       ├── config/           # env_config, settings, test_settings, urls, crud_models registry
│       ├── domain/           # Pure Python dataclasses, StrEnum, Protocol, ABCs (zero framework imports)
│       ├── usecases/         # UserUsecase, CrudUsecase
│       ├── interfaces/       # DRF APIView handlers + PostgreSQL & MongoDB repositories
│       ├── infrastructure/   # Django ORM models/migrations, Mongo connector, DI container, JWT auth, throttling, X-Request-ID middlewares
│       ├── shared/           # HS256 JWT, bcrypt, slug converter, Avro schema generator, utils
│       └── tests/            # Unit tests (domain/shared/usecases/interfaces) & integration tests
├── frontend/                 # Vue 3 + Vite + TypeScript + Pinia + Vue Router + Axios + Tailwind (:5173)
│   ├── Makefile              # Automation targets (dev, build, type-check, test, check)
│   ├── package.json          # Node dependencies and scripts
│   ├── vite.config.ts        # Vite configuration + Tailwind v4 + Vue plugin
│   ├── vitest.config.ts      # Vitest test configuration (jsdom environment)
│   ├── tsconfig.json         # TypeScript compiler configuration
│   ├── env.template          # Environment variables template (VITE_API_BASE_URL)
│   └── src/
│       ├── api/              # Axios client (http.ts), Bearer & 401 refresh interceptors, auth, crud, monitor
│       ├── stores/           # Pinia stores (auth.store, crud.store, toast.store)
│       ├── router/           # Vue Router definitions and auth navigation guards
│       ├── types/            # TypeScript interfaces (auth.types, crud.types, api.types)
│       ├── components/       # Layout, common pagination/toast, AvroSchemaViewer, DynamicDataTable, DynamicFormModal
│       ├── views/            # DashboardView, DataExplorerView, LoginView, RegisterView, ProfileView
│       └── __tests__/        # Vitest unit tests for api, stores, components, and views
├── golang-reference/         # Original Go (GoFiber + GORM) reference API (:3000)
│   ├── go.mod / go.sum       # Go module dependencies
│   ├── env.template          # Go environment template
│   └── src/
│       ├── config/           # Koanf configuration loader & registered CRUD models
│       ├── domain/           # Domain entities, DTOs, and repository interfaces
│       ├── usecases/         # User and generic CRUD usecases
│       ├── interface/        # GoFiber request handlers & GORM/MongoDB repositories
│       ├── infrastructure/   # GoFiber HTTP server, Swagger docs, Postgres migrations, Mongo connector
│       └── shared/           # HS256 JWT auth, bcrypt, slug converter, Avro schema generator
└── docker-compose.yml        # PostgreSQL 15 (postgres-15) + MongoDB 6.0.8 (mongo-6)
```

---

## Local Databases (Docker Compose)

Start PostgreSQL 15 (`:5432`) and MongoDB 6.0.8 (`:27017`):

```bash
docker compose up -d
```

- Uses the default `postgres` database in `postgres-15`.

---

## Backend (Python — Django + DRF, `:8000`)

### Features
- **Clean Architecture Layers**: strict inward dependency rules verified by AST unit tests (`domain/` has zero Django/DRF/PyMongo imports; `interfaces/handlers/` and `crud/factory.py` have zero `infrastructure`/`config` imports).
- **User Management & JWT Auth (HS256)**:
  - Register (ReDoS-safe email validation + lowercase normalization, `bcrypt` hashing, atomic creation of user + default `user_permissions` record)
  - Login (timing-safe `bcrypt` verification, HS256 `access` + `refresh` JWTs with unique `jti`, persisted as SHA-256 hashes in `user_tokens` via `OneToOneField` + `CASCADE`)
  - Refresh Token (row-locked DB session validation via constant-time hash comparison, strict `sub`/`iss`/`aud` JWT verification, rotates `access` token while preserving original `refresh` expiry)
  - Logout (verifies `refresh_token` and revokes `user_tokens` session)
  - Profile (`GET /api/v1/users/profile` via Bearer JWT, returning user identity and `permission`)
  - Security defaults & throttling: fail-closed DRF defaults (`IsAuthenticated`), spoofing-resistant client IP resolution (`APP_TRUSTED_PROXIES`), and IP-scoped auth rate limiting (`ClientIPScopedRateThrottle`, `APP_THROTTLE_AUTH_*`)
  - Automatic fail-safe audit logging of auth events (`USER_REGISTER`, `USER_LOGIN`, `USER_REFRESH_TOKEN`, `USER_LOGOUT`) into MongoDB `activity_logs`
- **Polyglot Dynamic CRUD Engine (`/api/v1/data/<slug>/...`)**:
  - Model registry (`src/config/crud_models.py`) routing slugs to **PostgreSQL** (`users`, `user-tokens`, `user-permissions`) or **MongoDB** (`activity-logs`)
  - Model discovery (`GET /api/v1/data/models/`) returning `slug`, `label`, `datasource`, and caller-specific `allowed_operations`
  - Automatic cached Avro Schema generation (`GET /api/v1/data/<slug>/describe`), hiding sensitive fields (`password`, `access`, `refresh` — recursively in MongoDB documents)
  - Role- & model-based operation enforcement via `allowed_operations(permission)`: `user-tokens` is read-only for all roles; `activity-logs` is read-only for `user` and allows `delete` for `admin`; disallowed operations return `405 Method Not Allowed` (`crud-405`)
  - Schema-validated filters & writes (Django `full_clean` + required `password` on PostgreSQL; dataclass field allowlist & type coercion blocking NoSQL `$`/`.` operator injection on MongoDB)
  - Accurate bounded pagination (`_page` max `10000`, `_pageSize` max `1000`) using `count()` before slicing
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
uv run ruff format --check src
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
| `GET` | `/api/v1/users/profile` | Bearer JWT | Get current authenticated user and `permission` |
| `GET` | `/api/v1/data/models/` | Bearer JWT | List registered models, datasources & `allowed_operations` |
| `GET` | `/api/v1/data/<slug>/describe` | Bearer JWT | Get Avro schema for entity |
| `GET` | `/api/v1/data/<slug>/` | Bearer JWT | Paginated list (`_page`, `_pageSize`) with `data_schema` |
| `POST` | `/api/v1/data/<slug>/` | Bearer JWT | Create record (`405` if disallowed) |
| `GET` | `/api/v1/data/<slug>/<id>` | Bearer JWT | Retrieve record by ID |
| `PUT` | `/api/v1/data/<slug>/<id>` | Bearer JWT | Update record by ID (`405` if disallowed) |
| `DELETE` | `/api/v1/data/<slug>/<id>` | Bearer JWT | Delete record by ID (`405` if disallowed) |
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
  - Schema-driven Create/Edit form modal (`DynamicFormModal.vue`) and Delete confirmation dialog, automatically gated by each model's `allowed_operations` (e.g., `user-tokens` is read-only; `activity-logs` is read-only for `user` and allows Delete for `admin`).

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
