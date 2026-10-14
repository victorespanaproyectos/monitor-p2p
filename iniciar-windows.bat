@echo off
cd /d "%~dp0"
if not exist .venv\Scripts\python.exe (
  py -3 -m venv .venv
  if errorlevel 1 goto error
)
.venv\Scripts\python.exe -m pip install -r requirements.txt
if errorlevel 1 goto error
.venv\Scripts\python.exe manage.py migrate --noinput
if errorlevel 1 goto error
.venv\Scripts\python.exe manage.py setup_admin
if errorlevel 1 goto error
start "" http://127.0.0.1:8000
.venv\Scripts\python.exe manage.py runserver 127.0.0.1:8000
goto end
:error
echo No se pudo iniciar. Revisa el mensaje anterior y que Python 3.12 o superior este instalado.
pause
:end
