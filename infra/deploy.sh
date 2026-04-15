#!/bin/bash
# Called by Jenkins Deploy stage.
# Requires env vars: EC2_HOST, SSH_KEY_PATH
set -euo pipefail

echo "Deploying to EC2: ${EC2_HOST}"

ssh -i "${SSH_KEY_PATH}" \
    -o StrictHostKeyChecking=accept-new \
    -o ConnectTimeout=30 \
    ubuntu@"${EC2_HOST}" << 'REMOTE'

set -euo pipefail
cd /home/ubuntu/it-asset-compliance

echo "--- git pull ---"
git pull origin main

echo "--- pip install ---"
pip3 install -r backend/requirements.txt

echo "--- restart service ---"
sudo systemctl restart compliance-api

echo "--- service status ---"
sudo systemctl status compliance-api --no-pager

REMOTE

echo "Deploy complete."
