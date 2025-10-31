#!/usr/bin/env python3
"""Bootstrap Playwright browsers and system dependencies.

This module exposes :func:`ensure` so other scripts (like ``test_app_bot.py``)
can install the Chromium browser and any required system libraries before
launching Playwright. It can also be executed directly from the command line.
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path
from typing import Iterable, Sequence

__all__ = ["ensure", "main"]

_SUPPORTED_BROWSERS = ("chromium", "firefox", "webkit")
_SENTINEL_ENV = "PLAYWRIGHT_BOOTSTRAP_SENTINEL_DIR"
_DEFAULT_SENTINEL_DIR = Path.home() / ".cache/ms-playwright"


def _normalise_browsers(browsers: Iterable[str] | None) -> Sequence[str]:
    if not browsers:
        return ("chromium",)
    unique: dict[str, None] = {}
    for browser in browsers:
        lower = browser.lower()
        if lower not in _SUPPORTED_BROWSERS:
            raise ValueError(f"Unsupported browser '{browser}'. Supported: {', '.join(_SUPPORTED_BROWSERS)}")
        unique.setdefault(lower, None)
    return tuple(unique.keys())


def _sentinel_path(browser: str, sentinel_dir: Path | None) -> Path:
    target_dir = sentinel_dir or Path(os.environ.get(_SENTINEL_ENV, _DEFAULT_SENTINEL_DIR))
    target_dir.mkdir(parents=True, exist_ok=True)
    return target_dir / f".deps-installed-{browser}"


def ensure(
    *,
    browsers: Iterable[str] | None = None,
    include_deps: bool = True,
    force: bool = False,
    sentinel_dir: Path | None = None,
    quiet: bool = False,
    dry_run: bool = False,
) -> None:
    """Ensure Playwright browsers and (optionally) system deps are installed.

    Args:
        browsers: Iterable of browser names to install. Defaults to ``("chromium",)``.
        include_deps: When True, attempt to install system dependencies on Linux
            using ``playwright install --with-deps``.
        force: When True, install dependencies even if the sentinel file exists.
        sentinel_dir: Custom directory to store sentinel files. Defaults to the
            Playwright cache directory.
        quiet: If True, minimise output from this helper (Playwright will still
            emit its own progress).
        dry_run: When True, print the commands without executing them.
    """

    browsers_to_install = _normalise_browsers(browsers)
    is_linux = sys.platform.startswith("linux")

    for browser in browsers_to_install:
        sentinel = _sentinel_path(browser, sentinel_dir)
        install_deps = include_deps and is_linux and (force or not sentinel.exists())

        cmd = [sys.executable, "-m", "playwright", "install"]
        if install_deps:
            cmd.append("--with-deps")
        cmd.append(browser)

        if not quiet:
            action = "with" if install_deps else "without"
            print(f"Ensuring Playwright browser '{browser}' is installed ({action} system deps)...")

        if dry_run:
            print("DRY RUN:", " ".join(cmd))
        else:
            try:
                subprocess.run(cmd, check=True)
            except FileNotFoundError as exc:  # pragma: no cover - defensive
                raise RuntimeError(
                    "The 'playwright' module is not installed. Run 'pip install playwright'."
                ) from exc
            except subprocess.CalledProcessError as exc:
                if install_deps:
                    sentinel.unlink(missing_ok=True)
                raise RuntimeError(
                    "Failed to install Playwright browsers or system dependencies. "
                    "If you manage them manually set PLAYWRIGHT_SKIP_BOOTSTRAP=1."
                ) from exc

        if install_deps and not dry_run:
            sentinel.write_text("ok\n")


def _parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "-b",
        "--browser",
        action="append",
        choices=_SUPPORTED_BROWSERS,
        help="Browser(s) to bootstrap (default: chromium).",
    )
    parser.add_argument(
        "--no-deps",
        dest="include_deps",
        action="store_false",
        help="Skip installing system dependencies (only install the browser archives).",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force reinstalling system dependencies even if a sentinel is present.",
    )
    parser.add_argument(
        "--sentinel-dir",
        type=Path,
        help="Override the directory used to track dependency installation.",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Reduce helper output (Playwright output is unaffected).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show the Playwright commands that would be executed without running them.",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> None:
    args = _parse_args(argv)
    ensure(
        browsers=args.browser,
        include_deps=args.include_deps,
        force=args.force,
        sentinel_dir=args.sentinel_dir,
        quiet=args.quiet,
        dry_run=args.dry_run,
    )


if __name__ == "__main__":  # pragma: no cover - CLI entrypoint
    main()
