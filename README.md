# IT Asset & Security Compliance Tool

[![CI](https://github.com/SirADarbi/It-Asset-Compliance/actions/workflows/ci.yml/badge.svg)](https://github.com/SirADarbi/It-Asset-Compliance/actions/workflows/ci.yml)

A production-ready compliance management system with FastAPI, PostgreSQL, Grafana, Terraform (AWS), Jenkins CI/CD, and GitHub Actions.

### Architecture

End-to-end flow: **Developer** pushes to GitHub → **GitHub Actions** runs tests and infra checks (pytest, `docker compose config`, shellcheck, `terraform fmt`) → **Jenkins** (optional self-hosted CD) checks out, installs, tests, and deploys via SSH → **Terraform** provisions **EC2** + **Elastic IP** → on the instance, **FastAPI** (systemd) talks to **PostgreSQL**; **Grafana** queries Postgres directly for dashboards. A **sysadmin** reaches the API and Grafana over HTTP.

![Infrastructure & CI/CD diagram](docs/architecture-diagram.png)

---

## Prerequisites

| Tool | Version |
|------|---------|
| Docker & Docker Compose | 24+ |
| Python | 3.11+ |
| Terraform | 1.3+ |
| AWS CLI | 2+ |

---

## Local Development Quickstart

### 1. Start PostgreSQL + Grafana

```bash
docker compose up -d
```

### 2. Configure environment

```bash
cp .env.example backend/.env
# Edit backend/.env if needed — defaults work for local Docker setup
```

### 3. Install Python dependencies

```bash
cd backend
pip install -r requirements.txt
```

### 4. Seed the database

```bash
python3 seed.py
```

### 5. Start the API

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### 6. Run the first compliance scan

```bash
curl -X POST http://localhost:8000/compliance/run
```

### 7. Run tests

```bash
pytest tests/ -v
```

---

## Service URLs

| Service | URL | Credentials |
|---------|-----|-------------|
| API docs (Swagger) | http://localhost:8000/docs | — |
| API docs (ReDoc) | http://localhost:8000/redoc | — |
| Grafana dashboard | http://localhost:3000 | admin / admin123 |

After seeding assets and running `POST /compliance/run`, the **IT Asset Compliance** dashboard shows active asset count, critical violations, a severity breakdown, and a full table of failed checks (hostname, policy, severity, detail).

![Grafana — IT Asset Compliance Dashboard](docs/grafana-dashboard.png)

---

## API Overview

### Assets
| Method | Path | Description |
|--------|------|-------------|
| GET | `/assets` | List all assets |
| GET | `/assets/{id}` | Get one asset |
| POST | `/assets` | Create an asset |
| PUT | `/assets/{id}` | Update an asset |
| DELETE | `/assets/{id}` | Delete an asset |

### Compliance
| Method | Path | Description |
|--------|------|-------------|
| POST | `/compliance/run` | Run all policy checks |
| GET | `/compliance/results` | Get results (filter: `?passed=false&severity=CRITICAL`) |
| GET | `/compliance/summary` | Counts by severity + last run time |

### Reports
| Method | Path | Description |
|--------|------|-------------|
| GET | `/reports/json` | Download violations as JSON |
| GET | `/reports/xml` | Download violations as `compliance_report.xml` |

---

## Terraform — AWS Deploy

```bash
cd infra/terraform

# Initialise providers
terraform init

# Preview changes
terraform plan -var="key_pair_name=my-key"

# Apply
terraform apply -var="key_pair_name=my-key"

# Get the Elastic IP
terraform output elastic_ip
```

Resources created:
- EC2 t2.micro (Ubuntu 22.04)
- Security group (ports 22, 8000, 3000)
- Elastic IP

The `user_data.sh` boot script installs all dependencies, clones the repo, and starts the compliance-api systemd service automatically.

---

## Jenkins CI/CD Setup

1. Create a new **Pipeline** job in Jenkins
2. Point it at this repo (`Jenkinsfile` at root)
3. Set the following environment variables (Jenkins → Manage → System or per-job):
   - `EC2_HOST` — Elastic IP from Terraform output
   - `SSH_KEY_PATH` — path to the `.pem` key file on the Jenkins agent
4. The pipeline has four stages:
   - **Checkout** — pulls source
   - **Install** — `pip install -r backend/requirements.txt`
   - **Test** — `pytest backend/tests/ -v` (fails pipeline if tests fail)
   - **Deploy** — SSH into EC2 and restarts the service (runs on `main` branch only)

---

## GitHub Actions

Triggered automatically on push/PR to `main`:

```
.github/workflows/ci.yml
```

Jobs: install → pytest → report

---

## Policy Rules

| Rule | Severity | Trigger |
|------|----------|---------|
| `patch_currency` | HIGH / CRITICAL | >30 days / >60 days since last patch |
| `telnet_port` | CRITICAL | Port 23 open |
| `encryption` | CRITICAL | Disk encryption disabled |
| `antivirus` | HIGH | Antivirus not active |
| `password_policy` | MEDIUM | Password policy non-compliant |
| `rdp_exposure` | HIGH | Port 3389 open on workstation/laptop |
| `ssh_on_workstation` | MEDIUM | Port 22 open on workstation/laptop |

---

## Stopping

```bash
docker compose down        # keep data volumes
docker compose down -v     # destroy volumes
```
