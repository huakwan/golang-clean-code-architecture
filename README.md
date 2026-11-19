## Golang Clean Code Architecture Template

Go (Golang) Clean Architecture based on Reading Uncle Bob's Clean Architecture. This code uses GoFiber, GORM, JWT authentication, and a Dynamic CRUD / Avro Schema engine, paired with a Vue.js 3 frontend (`frontend/`).

## Frontend (Vue.js 3)

Built with **Vue 3 (`<script setup lang="ts">`) + Vite + TypeScript + Pinia + Vue Router + Axios + Tailwind CSS + Vitest**.

Currently connected to the Go API (`http://localhost:3000`):
- **Authentication**: Register, Login, Logout, Profile (`POST /api/v1/users/profile`), and automatic `401` JWT refresh & retry interceptor
- **Dashboard**: Real-time Health Check (`GET /api/v1/`) and quick links to modules & Swagger UI
- **Profile & Auth Session**: User identity view, JWT token inspector, and Refresh Token test trigger
- **Dynamic Data Explorer (Read-only)**: Schema-driven table, pagination, record detail modal, and Avro Schema viewer for `users`, `user-tokens`, and `user-permissions`

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

## Backend (Go Reference API) — Installation
1. Replace "github.com/max38/golang-clean-code-architecture" with "your module name"
2. Copy or Change "env.template" file name to ".env" or ".env.dev"
3. Check on code for loading config in these files
```
src/infrastructure/database/postgres/migration/main.go
src/infrastructure/gofiber/main.go
```

4. Run Postgresql
5. Migrate RDBMS
6. Start web project


### run postgresql on docker
```bash
docker run -p 5432:5432 --name postgres-golang-first-api -e POSTGRES_PASSWORD=golang-first-api -d postgres:15
```
or docker compose
```bash
docker-compose up
```

### Migrate RDBMS
```bash
go run src/infrastructure/database/postgres/migration/main.go
```

### start web project (Production)

```bash
go run src/infrastructure/gofiber/main.go
```


# Template for every projdct
## Project Structure
```
src
 |-config
 |-domain
    |-entities
    |-models
    |-repositories
 |-infrastructure
    |-aws_lambda
    |-database
    |-gofiber
 |-interface
    |-handlers
       |-gofiber
    |-repositories
       |-postgres
 |-shared
 |-usecases
```

## Install lib

### REST API Lib
```bash
go get github.com/gofiber/fiber/v2
```

### Generate Swagger Document
1. Install follow this https://github.com/gofiber/swagger
2. Go to ChatGPT and prompt with
```
Please generate Declarative Comments Format for Swagger Doc follow this gofiber code.
"""<Handler Code>"""
```

3. update Declarative Comments from ChatGPT to Handler

4. Generate swagger.json
```bash
swag init -g src/infrastructure/gofiber/main.go -o src/infrastructure/gofiber/docs/
```

5. Go to localhost:3000/swagger/


### Configuration Lib
```bash
go get github.com/knadh/koanf/v2
go get github.com/knadh/koanf/providers/file
go get github.com/knadh/koanf/providers/env
go get github.com/knadh/koanf/parsers/dotenv
```

### GORM
```bash
go get -u gorm.io/gorm
go get -u gorm.io/driver/postgresql
```

### MongoDB
if use mongodb
```bash
go get go.mongodb.org/mongo-driver
go get go.mongodb.org/mongo-driver/mongo
```


## For Development

### Install Gofiber cli
follow this https://github.com/gofiber/cli

### start web project (Development)

```bash
fiber dev -t ./src/infrastructure/gofiber/main.go
```

### Add More Model
1. Define in src/domain/models/xxxx.go
2. Add Model at src/config/crudModels.go
