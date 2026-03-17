# Pochatox Core

Backend API for the **Pochatox** ecosystem.

> Frontend repository: [Pochatox/JinjaFrontend](https://github.com/Pochatox/JinjaFrontend)

---

## Tech Stack

- **Python 3.12**
- **Litestar**
- **Uvicorn**
- **SQLAlchemy (async)**
- **PostgreSQL 15**
- **Redis 7**
- **MailHog**
- **Kapusta**
- **Poetry**
- **Docker / Docker Compose**

---

## Quick Start (Docker)

The repository includes a ready-to-use `docker-compose.yaml` that starts:

* `core` (backend API)
* `db` (PostgreSQL 15)
* `mailhog`
* `redis`

### 1. Clone the repository

```bash
git clone https://github.com/Pochatox/Core.git
cd Core
```

### 2. Prepare environment

```bash
cp example.env .env
```

Edit `.env` if needed.

### 3. Start the stack

```bash
docker compose up --build
```

### 4. Open services

* **API:** `http://localhost:8282`
* **MailHog UI:** `http://localhost:8025`
