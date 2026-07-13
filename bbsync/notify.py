"""macOS notifications via osascript."""

from __future__ import annotations

import json
import subprocess


def notify(title: str, message: str) -> None:
    # json.dumps produces valid AppleScript string literals
    script = f"display notification {json.dumps(message)} with title {json.dumps(title)}"
    subprocess.run(["osascript", "-e", script], capture_output=True)
