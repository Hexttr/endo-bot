from __future__ import annotations

import json
import sys
from pathlib import Path

import paramiko


REMOTE_DEPLOY_SCRIPT = """#!/usr/bin/env bash
set -euo pipefail

APP_DIR="/opt/endo-bot/app"
VENV_BIN="/opt/endo-bot/venv/bin"
SERVICE_NAME="endo-bot.service"
REPO_URL="https://github.com/Hexttr/endo-bot.git"
BRANCH="main"

mkdir -p /opt/endo-bot/bin
git config --global --add safe.directory "${APP_DIR}" || true

need_install=0

if [ ! -d "${APP_DIR}/.git" ]; then
  rm -rf "${APP_DIR}"
  git clone --branch "${BRANCH}" --single-branch "${REPO_URL}" "${APP_DIR}"
  need_install=1
else
  cd "${APP_DIR}"
  before_rev="$(git rev-parse HEAD)"
  git fetch origin "${BRANCH}"
  if ! git diff --quiet "${before_rev}" "origin/${BRANCH}" -- pyproject.toml; then
    need_install=1
  fi
  git checkout "${BRANCH}"
  git pull --ff-only origin "${BRANCH}"
fi

chown -R endobot:endobot "${APP_DIR}"

if [ "${need_install}" -eq 1 ] || ! "${VENV_BIN}/python" -c "import endo_bot" >/dev/null 2>&1; then
  "${VENV_BIN}/pip" install -e "${APP_DIR}"
fi

cat > /etc/systemd/system/endo-bot.service <<'EOF'
[Unit]
Description=Endo Bot Telegram service
After=network.target

[Service]
Type=simple
User=endobot
Group=endobot
WorkingDirectory=/opt/endo-bot/app
EnvironmentFile=/opt/endo-bot/shared/.env
ExecStart=/opt/endo-bot/venv/bin/python -m endo_bot.main
Restart=always
RestartSec=5
StandardOutput=append:/opt/endo-bot/shared/logs/endo-bot.log
StandardError=append:/opt/endo-bot/shared/logs/endo-bot.err.log

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable "${SERVICE_NAME}" >/dev/null 2>&1 || true
if systemctl is-active --quiet "${SERVICE_NAME}"; then
  systemctl restart "${SERVICE_NAME}"
else
  systemctl start "${SERVICE_NAME}"
fi
systemctl status "${SERVICE_NAME}" --no-pager
"""


def load_config() -> dict[str, str]:
    config_path = Path(__file__).resolve().parents[1] / "deploy.local.json"
    if not config_path.exists():
        raise FileNotFoundError(
            "Missing deploy.local.json. Create it with host, username, and password."
        )
    return json.loads(config_path.read_text(encoding="utf-8"))


def run() -> None:
    config = load_config()
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(
        hostname=config["host"],
        username=config["username"],
        password=config["password"],
        timeout=20,
        banner_timeout=20,
        auth_timeout=20,
    )

    client.exec_command("mkdir -p /opt/endo-bot/bin", timeout=60)
    sftp = client.open_sftp()
    remote_script_path = "/opt/endo-bot/bin/deploy.sh"
    with sftp.file(remote_script_path, "w") as remote_file:
        remote_file.write(REMOTE_DEPLOY_SCRIPT)
    sftp.chmod(remote_script_path, 0o755)
    sftp.close()

    deploy_command = f"bash {remote_script_path}"
    _, stdout, stderr = client.exec_command(deploy_command, timeout=300)

    out = stdout.read().decode("utf-8", "ignore")
    err = stderr.read().decode("utf-8", "ignore")
    client.close()

    if out:
        print(_safe_console_text(out.strip()))
    if err:
        print(_safe_console_text(err.strip()))


def _safe_console_text(text: str) -> str:
    encoding = sys.stdout.encoding or "utf-8"
    return text.encode(encoding, "backslashreplace").decode(encoding)


if __name__ == "__main__":
    run()
