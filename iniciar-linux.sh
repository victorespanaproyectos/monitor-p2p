#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
if [ ! -x .venv/bin/python ]; then python3 -m venv .venv; fi
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python manage.py migrate --noinput
.venv/bin/python manage.py setup_admin
printf 'Abre http://127.0.0.1:8000\n'
exec .venv/bin/python manage.py runserver 127.0.0.1:8000
