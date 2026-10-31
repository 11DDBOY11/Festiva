#!/usr/bin/env python3
"""
Security Headers Checker for Festiva AI.
Usage:
    python scripts/check_headers.py <URL>

Checks for:
    - Strict-Transport-Security (HSTS)
    - Content-Security-Policy (CSP)
    - X-Content-Type-Options
    - X-Frame-Options
    - Referrer-Policy
    - Permissions-Policy
"""

import sys
import urllib.error
import urllib.request

REQUIRED_SECURITY_HEADERS = [
    "Strict-Transport-Security",
    "Content-Security-Policy",
    "X-Content-Type-Options",
    "X-Frame-Options",
    "Referrer-Policy",
    "Permissions-Policy",
]


def check_headers(url: str) -> bool:
    if not url.startswith("http://") and not url.startswith("https://"):
        url = "https://" + url

    print(f"\nScanning Security Headers for: {url}")
    print("=" * 70)

    try:
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "FestivaSecurityScanner/1.0"},
            method="HEAD",
        )
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                headers = {k.lower(): v for k, v in resp.headers.items()}
                status_code = resp.status
        except urllib.error.HTTPError as e:
            headers = {k.lower(): v for k, v in e.headers.items()}
            status_code = e.code

    except Exception as exc:  # noqa: BLE001
        print(f"[ERROR] Failed to connect to {url}: {exc}")
        return False

    print(f"Response Status: {status_code}\n")

    all_present = True
    for header in REQUIRED_SECURITY_HEADERS:
        val = headers.get(header.lower())
        if val:
            # Mask or truncate very long CSP values for display
            display_val = val if len(val) <= 80 else val[:77] + "..."
            print(f"  [PASS] {header}")
            print(f"         Value: {display_val}")
        else:
            print(f"  [MISSING] {header}")
            all_present = False

    print("=" * 70)
    if all_present:
        print("[SUCCESS] All recommended security headers are present.\n")
    else:
        print("[WARNING] Some recommended security headers are missing.\n")

    return all_present


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: python scripts/check_headers.py <URL>")
        print("Example: python scripts/check_headers.py https://festiva.onrender.com")
        sys.exit(1)

    url = sys.argv[1].strip()
    success = check_headers(url)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
