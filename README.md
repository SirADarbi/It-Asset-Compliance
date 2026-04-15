# IT Asset & Security Compliance Tool

[![CI](https://github.com/SirADarbi/It-Asset-Compliance/actions/workflows/ci.yml/badge.svg)](https://github.com/SirADarbi/It-Asset-Compliance/actions/workflows/ci.yml)

### Purpose

You can't really defend assets you aren't tracking, and "tracking" usually means more than a device list. Teams need to know if boxes are patched, if dumb stuff like Telnet is open, whether laptops have encryption and AV turned on, and they need that written down somewhere when someone asks for proof after an audit or an incident.

This repo is a working backend for that kind of problem. Assets live in Postgres, a handful of rules run against them in one shot, and every check is stored with a severity so you can see what failed and when. Grafana hooks straight into the same database for charts; the API plus JSON/XML endpoints are there when you want to feed another tool or attach something to a ticket.

**Rough feature set:** CRUD for assets (hostnames, types, ports, patch dates, flags you care about), run all policies on demand, filter results, Grafana dashboards, downloadable reports.

**Stack:** FastAPI, PostgreSQL, Grafana, Docker Compose, Terraform on AWS, Jenkins (optional), GitHub Actions.

### Architecture

Push code to GitHub and Actions runs pytest plus a few cheap checks (compose file parses, shellcheck, `terraform fmt`). If you wire up Jenkins, it can repeat install/test and then SSH to your server to pull and restart the app. Terraform builds a tiny Ubuntu EC2 with an elastic IP. On the box the API runs under systemd; Postgres and Grafana run in Docker. The API reads and writes the DB; Grafana only reads it for panels. You hit the API and Grafana on 8000 and 3000 over HTTP.

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
# Edit backend/.env if needed; defaults work for local Docker setup
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
| API docs (Swagger) | http://localhost:8000/docs | (none) |
| API docs (ReDoc) | http://localhost:8000/redoc | (none) |
| Grafana dashboard | http://localhost:3000 | admin / admin123 |

After seeding assets and running `POST /compliance/run`, the **IT Asset Compliance** dashboard shows active asset count, critical violations, a severity breakdown, and a full table of failed checks (hostname, policy, severity, detail).

![Grafana IT Asset Compliance dashboard](docs/grafana-dashboard.png)

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

## Terraform (AWS deploy)

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
3. Set environment variables (Jenkins → Manage → System or per-job):
   - `EC2_HOST`: Elastic IP from Terraform output
   - `SSH_KEY_PATH`: path to the `.pem` key file on the Jenkins agent
4. Pipeline stages: Checkout, Install (`pip install -r backend/requirements.txt`), Test (`pytest backend/tests/ -v`, fails the build on failure), Deploy (SSH to EC2 and restart the service, `main` only)

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
