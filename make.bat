@echo off
setlocal enabledelayedexpansion

set PYTHON=backend\.venv\Scripts\python.exe
if not exist %PYTHON% set PYTHON=python

set RUFF=backend\.venv\Scripts\ruff.exe
if not exist %RUFF% set RUFF=ruff

if "%1"=="" goto usage
if "%1"=="test" goto test
if "%1"=="lint" goto lint
if "%1"=="format" goto format
if "%1"=="eval" goto eval
if "%1"=="eval-live" goto evallive
if "%1"=="eval-plan" goto evalplan
if "%1"=="migrate" goto migrate
if "%1"=="dev" goto dev
goto usage

:test
%PYTHON% -m pytest backend\tests -v
goto end

:lint
%RUFF% check backend\app backend\tests
goto end

:format
%RUFF% format backend\app backend\tests
goto end

:eval
%PYTHON% backend\tests\evals\eval_brief_parser.py --replay
%PYTHON% backend\tests\evals\eval_plan_generator.py --replay
goto end

:evallive
%PYTHON% backend\tests\evals\eval_brief_parser.py --live
%PYTHON% backend\tests\evals\eval_plan_generator.py
goto end

:evalplan
%PYTHON% backend\tests\evals\eval_plan_generator.py --replay
goto end

:migrate
cd backend && ..\%PYTHON% -m alembic upgrade head && cd ..
goto end

:dev
cd backend && ..\%PYTHON% -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000 && cd ..
goto end

:usage
echo Usage: make [test^|lint^|format^|eval^|eval-live^|eval-plan^|migrate^|dev]

:end
