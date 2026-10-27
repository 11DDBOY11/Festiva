param(
    [Parameter(Position=0)]
    [string]$Target = "test"
)

$ErrorActionPreference = "Stop"

$python = "backend/.venv/Scripts/python.exe"
if (-not (Test-Path $python)) {
    $python = "python"
}

$ruff = "backend/.venv/Scripts/ruff.exe"
if (-not (Test-Path $ruff)) {
    $ruff = "ruff"
}

switch ($Target.ToLower()) {
    "test" {
        & $python -m pytest backend/tests -v
    }
    "lint" {
        & $ruff check backend/app backend/tests
    }
    "format" {
        & $ruff format backend/app backend/tests
    }
    "eval" {
        & $python backend/tests/evals/eval_brief_parser.py --replay
        & $python backend/tests/evals/eval_plan_generator.py --replay
    }
    "eval-live" {
        & $python backend/tests/evals/eval_brief_parser.py --live
        & $python backend/tests/evals/eval_plan_generator.py
    }
    "eval-plan" {
        & $python backend/tests/evals/eval_plan_generator.py --replay
    }
    "migrate" {
        Push-Location backend
        try {
            & "../$python" -m alembic upgrade head
        } finally {
            Pop-Location
        }
    }
    "dev" {
        Push-Location backend
        try {
            & "../$python" -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
        } finally {
            Pop-Location
        }
    }
    Default {
        Write-Host "Usage: .\make.ps1 [test|lint|format|eval|eval-live|eval-plan|migrate|dev]"
    }
}
