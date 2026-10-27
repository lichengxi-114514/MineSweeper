@echo off
cd /d "%~dp0.."
.venv\Scripts\python.exe -m pytest -q --tb=short %* > .pytest_out.txt 2>&1
set RC=%ERRORLEVEL%
.venv\Scripts\python.exe -c "import pathlib;t=pathlib.Path('.pytest_out.txt').read_text(encoding='utf-8',errors='replace').splitlines();print('\n'.join(t[-8:]))"
echo EXIT=%RC%

