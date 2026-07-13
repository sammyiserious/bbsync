"""bbsync command-line interface."""

from __future__ import annotations

import argparse
import logging
import sys

from . import auth, schedule
from .client import BBClient
from .config import CONFIG_PATH, Config
from .manifest import Manifest
from .notify import notify
from .sync import run_sync, update_course_list

log = logging.getLogger("bbsync")


def cmd_login(_args) -> int:
    config = Config.load()
    print("A browser window will open — log in with your Imperial account (SSO + MFA).")
    with auth.browser(headless=False) as ctx:
        user = auth.ensure_session(ctx, interactive=True)
        if not user:
            print("Login did not complete within 5 minutes. Try again with: bbsync login")
            return 1
        name = user.get("userName") or user.get("id")
        print(f"Logged in as {name}. Session saved for future headless runs.\n")

        client = BBClient(ctx)
        update_course_list(client, config, user["id"])

    _print_courses(config)
    print(f"\nAll courses are enabled by default — edit with 'bbsync courses --disable <name>'.")
    print("Next steps:  bbsync sync          (pull files now)")
    print("             bbsync schedule install   (auto-sync in the background)")
    return 0


def cmd_sync(_args) -> int:
    config = Config.load()
    manifest = Manifest.load()
    try:
        with auth.browser(headless=True) as ctx:
            user = auth.ensure_session(ctx)
            if not user:
                log.error("Blackboard session expired — run 'bbsync login' to sign in again.")
                notify("bbsync", "Blackboard session expired — run 'bbsync login' in a terminal.")
                return 2
            client = BBClient(ctx)
            stats = run_sync(client, config, manifest, user["id"])
    except Exception as exc:  # includes a locked browser profile from a concurrent run
        log.error("sync failed: %s", exc)
        return 1

    manifest.mark_synced()
    manifest.save()
    log.info("done — %s", stats.summary())
    new = stats.downloaded + stats.updated
    if new:
        notify("bbsync", f"{new} new file{'s' if new != 1 else ''} downloaded from Blackboard")
    return 0


def cmd_courses(args) -> int:
    config = Config.load()
    if not config.courses:
        print("No courses known yet — run 'bbsync login' first.")
        return 1
    for ref, enable in ((args.enable, True), (args.disable, False)):
        if ref:
            cid = config.find_course(ref)
            if not cid:
                print(f"No unique course matches {ref!r}")
                return 1
            config.courses[cid].enabled = enable
            config.save()
    _print_courses(config)
    return 0


def cmd_schedule(args) -> int:
    config = Config.load()
    if args.action == "install":
        schedule.install(config.interval_hours)
        print(f"Installed: syncs every {config.interval_hours}h (and at login). "
              f"Logs: ~/.bbsync/logs/sync.log")
    elif args.action == "uninstall":
        print("Removed." if schedule.uninstall() else "No schedule was installed.")
    else:
        line = schedule.status()
        print(f"Loaded: {line}" if line else "Not scheduled.")
    return 0


def cmd_status(_args) -> int:
    config = Config.load()
    manifest = Manifest.load()
    enabled = sum(c.enabled for c in config.courses.values())
    print(f"Config:      {CONFIG_PATH}")
    print(f"Destination: {config.dest}")
    print(f"Courses:     {enabled} enabled / {len(config.courses)} known")
    print(f"Last sync:   {manifest.last_sync or 'never'}")
    line = schedule.status()
    print(f"Schedule:    {'every ' + str(config.interval_hours) + 'h (loaded)' if line else 'not installed'}")
    return 0


def _print_courses(config: Config) -> None:
    print(f"Courses ({len(config.courses)}):")
    for cid, c in sorted(config.courses.items(), key=lambda kv: kv[1].name.lower()):
        mark = "[x]" if c.enabled else "[ ]"
        print(f"  {mark} {c.name}   ({cid})")


def main(argv: list[str] | None = None) -> None:
    logging.basicConfig(format="%(asctime)s %(levelname)-7s %(message)s", level=logging.INFO)

    parser = argparse.ArgumentParser(
        prog="bbsync",
        description="Download and organise Imperial Blackboard course files.",
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    sub.add_parser("login", help="open a browser to sign in once (SSO + MFA)")
    sub.add_parser("sync", help="download new/changed files now")
    p = sub.add_parser("courses", help="list courses; enable/disable syncing per course")
    p.add_argument("--enable", metavar="NAME_OR_ID")
    p.add_argument("--disable", metavar="NAME_OR_ID")
    p = sub.add_parser("schedule", help="manage the background auto-sync")
    p.add_argument("action", choices=["install", "uninstall", "status"])
    sub.add_parser("status", help="show config, last sync and schedule state")

    args = parser.parse_args(argv)
    handler = {
        "login": cmd_login,
        "sync": cmd_sync,
        "courses": cmd_courses,
        "schedule": cmd_schedule,
        "status": cmd_status,
    }[args.cmd]
    sys.exit(handler(args))
