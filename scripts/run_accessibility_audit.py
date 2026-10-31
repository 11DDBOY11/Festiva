"""
Playwright + axe-core accessibility audit script for Festiva AI.
Tests Landing Page, Events Dashboard, and Plan Modal.
"""

import json
import os
import subprocess
import time

from axe_core_python.sync_playwright import Axe
from playwright.sync_api import sync_playwright


def run_audit():
    # 1. Start backend server
    env = os.environ.copy()
    env["PYTHONPATH"] = "backend"
    backend_proc = subprocess.Popen(
        [
            "backend/.venv/Scripts/python",
            "-m",
            "uvicorn",
            "app.main:app",
            "--host",
            "127.0.0.1",
            "--port",
            "8000",
        ],
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    # 2. Start frontend server
    frontend_proc = subprocess.Popen(
        ["npm.cmd", "--prefix", "frontend", "run", "dev", "--", "--port", "3000"],
        shell=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    time.sleep(4)  # Wait for servers to be ready

    results = {}
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(channel="msedge", headless=True)
            page = browser.new_page(viewport={"width": 1280, "height": 800})
            axe = Axe()

            # Audit 1: Landing Page
            print("Auditing Landing Page...")
            page.goto("http://localhost:3000")
            page.wait_for_selector("text=Festiva AI")
            time.sleep(1)
            landing_report = axe.run(page)
            results["Landing Page"] = {
                "violations_count": len(landing_report.get("violations", [])),
                "passes_count": len(landing_report.get("passes", [])),
                "violations": [
                    {
                        "id": v["id"],
                        "impact": v["impact"],
                        "description": v["description"],
                        "nodes": len(v["nodes"]),
                    }
                    for v in landing_report.get("violations", [])
                ],
            }

            # Audit 2: Click "Try the demo" which logs in and automatically opens Plan Modal
            print("Clicking 'Try the demo' to audit Plan Modal...")
            demo_btn = page.locator("button:has-text('Try the demo')").first
            demo_btn.click()
            page.wait_for_selector("role=dialog", timeout=12000)
            time.sleep(1)

            modal_report = axe.run(page)
            results["Plan Modal"] = {
                "violations_count": len(modal_report.get("violations", [])),
                "passes_count": len(modal_report.get("passes", [])),
                "violations": [
                    {
                        "id": v["id"],
                        "impact": v["impact"],
                        "description": v["description"],
                        "nodes": len(v["nodes"]),
                    }
                    for v in modal_report.get("violations", [])
                ],
            }

            # Audit 3: Close modal to audit Events Dashboard
            print("Closing modal to audit Events Dashboard...")
            page.keyboard.press("Escape")
            time.sleep(1)

            dashboard_report = axe.run(page)
            results["Events Dashboard"] = {
                "violations_count": len(dashboard_report.get("violations", [])),
                "passes_count": len(dashboard_report.get("passes", [])),
                "violations": [
                    {
                        "id": v["id"],
                        "impact": v["impact"],
                        "description": v["description"],
                        "nodes": len(v["nodes"]),
                    }
                    for v in dashboard_report.get("violations", [])
                ],
            }

            browser.close()
    finally:
        backend_proc.terminate()
        frontend_proc.terminate()
        backend_proc.wait()
        frontend_proc.wait()

    print("\n--- AXE-CORE ACCESSIBILITY AUDIT SUMMARY ---")
    print(json.dumps(results, indent=2))
    return results


if __name__ == "__main__":
    run_audit()
