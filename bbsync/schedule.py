"""Install/remove the launchd agent that runs `bbsync sync` on a schedule."""

from __future__ import annotations

import plistlib
import subprocess
import sys
from pathlib import Path

from .config import LOG_DIR

LABEL = "com.bbsync.sync"
PLIST_PATH = Path.home() / "Library" / "LaunchAgents" / f"{LABEL}.plist"


def _sync_command() -> list[str]:
    console_script = Path(sys.executable).with_name("bbsync")
    if console_script.exists():
        return [str(console_script), "sync"]
    return [sys.executable, "-m", "bbsync", "sync"]


def install(interval_hours: int) -> None:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    plist = {
        "Label": LABEL,
        "ProgramArguments": _sync_command(),
        "StartInterval": interval_hours * 3600,
        "RunAtLoad": True,
        "StandardOutPath": str(LOG_DIR / "sync.log"),
        "StandardErrorPath": str(LOG_DIR / "sync.log"),
    }
    PLIST_PATH.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(["launchctl", "unload", str(PLIST_PATH)], capture_output=True)
    PLIST_PATH.write_bytes(plistlib.dumps(plist))
    subprocess.run(["launchctl", "load", str(PLIST_PATH)], check=True)


def uninstall() -> bool:
    if not PLIST_PATH.exists():
        return False
    subprocess.run(["launchctl", "unload", str(PLIST_PATH)], capture_output=True)
    PLIST_PATH.unlink()
    return True


def status() -> str | None:
    """Return the launchctl status line for our job, or None if not loaded."""
    out = subprocess.run(["launchctl", "list"], capture_output=True, text=True).stdout
    for line in out.splitlines():
        if line.endswith(LABEL):
            return line
    return None
