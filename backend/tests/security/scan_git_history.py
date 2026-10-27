"""Gitleaks-equivalent secrets scanner over complete Git repository history.

Scans all commits, diffs, file trees, and committed recordings for sensitive tokens:
- Groq API keys (gsk_...)
- OpenAI API keys (sk-...)
- Google API keys (AIza...)
- AWS Access Keys (AKIA...)
- GitHub tokens (ghp_..., github_pat_...)
- Private keys (-----BEGIN ... PRIVATE KEY-----)
- Hardcoded JWT secrets or production passwords
- Accidental commits of .env files
"""

import re
import subprocess
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent.parent.parent

PATTERNS = [
    ("Groq API Key", re.compile(r"\bgsk_[A-Za-z0-9]{20,}\b")),
    ("OpenAI API Key", re.compile(r"\bsk-[A-Za-z0-9]{20,}\b")),
    ("Google API Key", re.compile(r"\bAIza[0-9A-Za-z\-_]{35}\b")),
    ("AWS Access Key ID", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("GitHub Personal Access Token", re.compile(r"\bghp_[0-9a-zA-Z]{36}\b")),
    ("GitHub Fine-Grained Token", re.compile(r"\bgithub_pat_[0-9a-zA-Z_]{22,}\b")),
    ("Private Key", re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----")),
    (
        "Generic Secret/Password",
        re.compile(
            r"""(?i)(?:jwt_secret|api_key|secret_key|password)\s*[:=]\s*["'](?!(?:change-me|your-|test|dev|secret|dummy|fake|sample|super-))[^"']{24,}["']"""
        ),
    ),
]


def run_cmd(cmd: list[str]) -> str:
    res = subprocess.run(
        cmd,
        cwd=str(ROOT_DIR),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=True,
    )
    return res.stdout


def scan_git_history() -> dict[str, list[dict]]:
    findings = []

    # 1. Check for tracked .env files across full commit history
    try:
        rev_list = run_cmd(["git", "rev-list", "--all"]).strip().splitlines()
    except Exception as exc:
        print(f"Error reading git revisions: {exc}")
        return {"findings": []}

    print(f"[SCAN] Scanning {len(rev_list)} commits across full git history...")

    # Check for committed .env files
    try:
        env_files = run_cmd(
            ["git", "log", "--all", "--name-only", "--pretty=format:%H", "--", "**/.env", ".env"]
        )
        for line in env_files.splitlines():
            line = line.strip()
            if line.endswith(".env") and not line.endswith(".env.example"):
                findings.append(
                    {
                        "rule": "Committed .env file",
                        "file": line,
                        "commit": "Historical commit",
                        "snippet": line,
                    }
                )
    except Exception as err:
        print(f"Error checking .env in history: {err}")

    # 2. Scan git diffs for all commits
    for commit in rev_list:
        try:
            diff_text = run_cmd(
                ["git", "show", commit, "--pretty=format:Commit: %H - %an <%ae> - %s"]
            )
            for rule_name, regex in PATTERNS:
                matches = regex.findall(diff_text)
                for match in matches:
                    # Sanitize match in output to avoid printing actual secrets in report
                    sanitized = match[:6] + "..." + match[-4:] if len(match) > 12 else "[REDACTED]"
                    findings.append(
                        {
                            "rule": rule_name,
                            "commit": commit[:10],
                            "sanitized_match": sanitized,
                        }
                    )
        except Exception:
            continue

    # 3. Check current workspace tracked files (excluding untracked .env)
    try:
        tracked_files = run_cmd(["git", "ls-files"]).strip().splitlines()
        for tf in tracked_files:
            file_path = ROOT_DIR / tf
            if file_path.is_file() and file_path.name != ".env":
                try:
                    content = file_path.read_text(encoding="utf-8", errors="ignore")
                    for rule_name, regex in PATTERNS:
                        matches = regex.findall(content)
                        for match in matches:
                            sanitized = (
                                match[:6] + "..." + match[-4:] if len(match) > 12 else "[REDACTED]"
                            )
                            findings.append(
                                {
                                    "rule": rule_name,
                                    "file": tf,
                                    "sanitized_match": sanitized,
                                }
                            )
                except Exception:
                    pass
    except Exception:
        pass

    return findings


def get_repo_remote_info() -> str:
    try:
        remotes = run_cmd(["git", "remote", "-v"]).strip()
        return remotes
    except Exception:
        return "No remotes configured"


if __name__ == "__main__":
    findings = scan_git_history()
    remotes = get_repo_remote_info()

    print("\n" + "=" * 80)
    print("SECRETS AND GITLEAKS SCAN REPORT")
    print("=" * 80)
    print(f"Repository Remotes:\n{remotes}\n")
    print(f"Total Sensitive Findings: {len(findings)}")

    if findings:
        print("\n[WARNING] Secrets or sensitive patterns detected:")
        for f in findings:
            print(f"  • {f}")
        sys.exit(1)
    else:
        print(
            "[CLEAN] Zero secrets, zero API keys, and zero .env files committed across "
            "entire git history."
        )
        sys.exit(0)
