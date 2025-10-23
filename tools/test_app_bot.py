#!/usr/bin/env python3
"""Headless smoke-test bot for the User Journey Map app.

The bot ensures the required Playwright browser (and on Linux, system libraries)
are installed, spins up a local HTTP server unless a ``--base-url`` is supplied,
opens the app in Playwright, and walks through the primary learner flow:

* wait for the manifest to load courses
* pick the first course and persona
* verify key UI regions render content without console errors

If any expectation fails the script raises ``AssertionError`` and exits with a non-zero
status so it can run inside CI.
"""

from __future__ import annotations

import argparse
import asyncio
import os
import signal
import subprocess
import sys
import time
from contextlib import suppress
from pathlib import Path
from typing import List, Optional

import requests
from playwright.async_api import Playwright, async_playwright


PROJECT_ROOT = Path(__file__).resolve().parents[1]
TOOLS_DIR = Path(__file__).resolve().parent
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

import bootstrap_playwright  # noqa: E402  (added to sys.path above)

IGNORABLE_CONSOLE_ERRORS = (
    "net::ERR_CERT_AUTHORITY_INVALID",
)


def bootstrap_dependencies(*, skip: bool, force: bool) -> None:
    """Ensure Playwright browsers/system dependencies exist before running."""

    if skip or os.environ.get("PLAYWRIGHT_SKIP_BOOTSTRAP") == "1":
        return

    try:
        bootstrap_playwright.ensure(
            browsers=("chromium",),
            include_deps=True,
            force=force,
            quiet=False,
        )
    except Exception as exc:  # pragma: no cover - defensive runtime guard
        raise RuntimeError(
            "Playwright bootstrap failed. Rerun with --skip-bootstrap or set "
            "PLAYWRIGHT_SKIP_BOOTSTRAP=1 if dependencies are managed externally."
        ) from exc


def start_http_server(port: int) -> subprocess.Popen[bytes]:
    """Launch ``python -m http.server`` bound to localhost for the static site."""

    cmd = [sys.executable, "-m", "http.server", str(port), "--bind", "127.0.0.1"]
    return subprocess.Popen(cmd, cwd=str(PROJECT_ROOT))


def wait_for_server(url: str, timeout: float = 5.0) -> None:
    """Poll the given URL until it responds or ``timeout`` seconds elapse."""

    deadline = time.time() + timeout
    last_error: Optional[BaseException] = None
    while time.time() < deadline:
        try:
            resp = requests.get(url, timeout=0.5)
            if resp.status_code < 500:
                return
        except requests.RequestException as exc:  # pragma: no cover - diagnostic only
            last_error = exc
        time.sleep(0.1)
    raise RuntimeError(f"Server at {url} did not become ready: {last_error}")


def stop_process(proc: Optional[subprocess.Popen[bytes]]) -> None:
    if not proc:
        return
    with suppress(ProcessLookupError):
        proc.send_signal(signal.SIGINT)
    try:
        proc.wait(timeout=2)
        return
    except subprocess.TimeoutExpired:
        pass
    with suppress(ProcessLookupError):
        proc.terminate()
    try:
        proc.wait(timeout=2)
        return
    except subprocess.TimeoutExpired:
        pass
    with suppress(ProcessLookupError):
        proc.kill()
    with suppress(subprocess.TimeoutExpired):
        proc.wait(timeout=2)


async def assert_app_flow(playwright: Playwright, url: str, *, headless: bool, slow_mo: float) -> None:
    browser = await playwright.chromium.launch(headless=headless, slow_mo=slow_mo)
    page = await browser.new_page()

    console_errors: List[str] = []

    def _should_ignore_console(text: str) -> bool:
        return any(pattern in text for pattern in IGNORABLE_CONSOLE_ERRORS)

    def handle_console(msg) -> None:
        if msg.type == "error":
            text = msg.text
            if not _should_ignore_console(text):
                console_errors.append(text)

    def handle_page_error(exc) -> None:
        text = str(exc)
        if not _should_ignore_console(text):
            console_errors.append(text)

    page.on("console", handle_console)
    page.on("pageerror", handle_page_error)

    try:
        await page.goto(url, wait_until="domcontentloaded")

        await page.wait_for_selector(
            "#courseSelect option:not([disabled])", state="attached", timeout=5000
        )
        course_value = await page.eval_on_selector(
            "#courseSelect option:not([disabled])", "el => el.value"
        )
        if not course_value:
            raise AssertionError("No selectable course options found")

        await page.select_option("#courseSelect", course_value)

        await page.wait_for_function(
            "() => { const sel = document.querySelector('#personaSelect');"
            " return sel && !sel.disabled && sel.options.length > 1; }",
            timeout=5000,
        )

        persona_value = await page.eval_on_selector(
            "#personaSelect option:not([disabled])", "el => el.value"
        )
        if not persona_value:
            raise AssertionError("No persona options available after course selection")

        async with page.expect_response(
            lambda res: persona_value in res.url,
            timeout=5000,
        ):
            await page.select_option("#personaSelect", persona_value)

        await page.wait_for_function(
            "() => {"
            " const name = document.querySelector('#personaName');"
            " const scenario = document.querySelector('#scenarioContent');"
            " return name && scenario && name.textContent.trim().length > 0 &&"
            " scenario.textContent.trim().length > 0; }",
            timeout=5000,
        )

        persona_name = (await page.inner_text("#personaName")).strip()
        scenario = (await page.inner_text("#scenarioContent")).strip()
        expectations_count = await page.eval_on_selector_all(
            "#expectationsList li", "els => els.length"
        )
        actions_count = await page.eval_on_selector_all(
            "[data-phase=\"0\"][data-row=\"actions\"] li", "els => els.length"
        )
        markers_count = await page.eval_on_selector_all(
            "#markers .marker", "els => els.length"
        )
        path_d = await page.get_attribute("#feelingsPath", "d")

        missing: List[str] = []
        if not persona_name:
            missing.append("persona name")
        if not scenario:
            missing.append("scenario")
        if expectations_count == 0:
            missing.append("expectations")
        if actions_count == 0:
            missing.append("actions")
        if markers_count < 4:
            missing.append("feelings markers")
        if not path_d or len(path_d.strip()) < 4:
            missing.append("feelings path")
        if missing:
            raise AssertionError("App content missing: " + ", ".join(missing))

        if console_errors:
            raise AssertionError("Console errors detected: " + " | ".join(console_errors))

        print(f"✅ Loaded persona '{persona_name}' with {expectations_count} expectations and {actions_count} actions.")
    finally:
        await page.close()
        await browser.close()


async def main() -> None:
    parser = argparse.ArgumentParser(description="Smoke test the journey map UI with Playwright.")
    parser.add_argument(
        "--base-url",
        help="Run against an existing deployment (e.g. https://example.com/index.html)."
        " If omitted a local http.server is started.",
    )
    parser.add_argument("--port", type=int, default=8000, help="Port for the local dev server (default: 8000).")
    parser.add_argument(
        "--no-headless",
        dest="headless",
        action="store_false",
        help="Show the browser window instead of running headlessly.",
    )
    parser.add_argument(
        "--slow-mo",
        type=float,
        default=0.0,
        help="Delay Playwright actions by the given milliseconds (useful for debugging).",
    )
    parser.add_argument(
        "--skip-bootstrap",
        action="store_true",
        help=(
            "Skip installing Playwright browsers/system deps (useful if they are "
            "managed by your environment)."
        ),
    )
    parser.add_argument(
        "--force-bootstrap-deps",
        action="store_true",
        help="Force reinstalling Playwright system dependencies via --with-deps.",
    )
    parser.set_defaults(headless=True)

    args = parser.parse_args()

    bootstrap_dependencies(skip=args.skip_bootstrap, force=args.force_bootstrap_deps)

    if args.base_url:
        base_url = args.base_url
        server_proc: Optional[subprocess.Popen[bytes]] = None
    else:
        server_proc = start_http_server(args.port)
        try:
            wait_for_server(f"http://127.0.0.1:{args.port}")
        except Exception:
            stop_process(server_proc)
            raise
        base_url = f"http://127.0.0.1:{args.port}/index.html"

    try:
        async with async_playwright() as playwright:
            await assert_app_flow(playwright, base_url, headless=args.headless, slow_mo=args.slow_mo)
    finally:
        stop_process(server_proc)


if __name__ == "__main__":
    asyncio.run(main())
