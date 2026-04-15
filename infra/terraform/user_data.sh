#!/bin/bash
set -euxo pipefail

# ── System update & packages ───────────────────────────────────────────────────
apt-get update -y
apt-get upgrade -y
apt-get install -y python3 python3-pip git curl ca-certificates gnupg lsb-release

# ── Docker ─────────────────────────────────────────────────────────────────────
install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg \
  | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
chmod a+r /etc/apt/keyrings/docker.gpg

echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] \
  https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" \
  > /etc/apt/sources.list.d/docker.list

apt-get update -y
apt-get install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin

# Also install legacy docker-compose binary for compatibility
pip3 install docker-compose

usermod -aG docker ubuntu

# ── Clone repo ─────────────────────────────────────────────────────────────────
REPO_URL="${github_repo}"
INSTALL_DIR="/home/ubuntu/it-asset-compliance"

git clone "$REPO_URL" "$INSTALL_DIR"
chown -R ubuntu:ubuntu "$INSTALL_DIR"

# ── Python dependencies ────────────────────────────────────────────────────────
pip3 install -r "$INSTALL_DIR/backend/requirements.txt"

# ── .env ───────────────────────────────────────────────────────────────────────
# db_user and db_password are injected by Terraform's templatefile().
# shellcheck disable=SC2154
cat > "$INSTALL_DIR/backend/.env" <<ENV
DATABASE_URL=postgresql://${db_user}:${db_password}@localhost:5432/asset_compliance
ENV
chmod 600 "$INSTALL_DIR/backend/.env"
chown ubuntu:ubuntu "$INSTALL_DIR/backend/.env"

# ── Root .env for Docker Compose ───────────────────────────────────────────────
# docker-compose.yml requires POSTGRES_PASSWORD and GF_SECURITY_ADMIN_PASSWORD.
# Use same DB password for Grafana admin in this bootstrap (demo simplicity).
# shellcheck disable=SC2154
cat > "$INSTALL_DIR/.env" <<ROOTENV
POSTGRES_USER=${db_user}
POSTGRES_PASSWORD=${db_password}
GF_SECURITY_ADMIN_PASSWORD=${db_password}
ROOTENV
chmod 600 "$INSTALL_DIR/.env"
chown ubuntu:ubuntu "$INSTALL_DIR/.env"

# ── Start Docker stack (Postgres + Grafana) ────────────────────────────────────
cd "$INSTALL_DIR"
docker compose up -d

# Wait for Postgres to be ready before starting the API or seeding
echo "Waiting for Postgres..."
until docker compose exec -T db pg_isready -U "${db_user}" -d asset_compliance; do
  sleep 3
done

# ── Seed the database ──────────────────────────────────────────────────────────
cd "$INSTALL_DIR/backend"
python3 seed.py

# ── Systemd service ────────────────────────────────────────────────────────────
cp "$INSTALL_DIR/backend/systemd/compliance-api.service" \
   /etc/systemd/system/compliance-api.service

systemctl daemon-reload
systemctl enable compliance-api
systemctl start compliance-api

echo "Bootstrap complete."
