"""Persistent browser session for Imperial SSO login."""

from __future__ import annotations

import logging
import re
from contextlib import contextmanager

from playwright.sync_api import BrowserContext, sync_playwright
from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import TimeoutError as PlaywrightTimeout

from .config import BASE_URL, PROFILE_DIR

log = logging.getLogger("bbsync")

_ULTRA_URL = re.compile(r"bb\.imperial\.ac\.uk/ultra")

# Tried in order: public REST first, private SPA API as fallback.
_ME_ENDPOINTS = (
    "/learn/api/public/v1/users/me",
    "/learn/api/v1/users/me",
)


@contextmanager
def browser(headless: bool = True):
    """Yield a persistent BrowserContext whose cookies survive between runs."""
    PROFILE_DIR.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as pw:
        ctx = pw.chromium.launch_persistent_context(str(PROFILE_DIR), headless=headless)
        try:
            yield ctx
        finally:
            ctx.close()


def current_user(ctx: BrowserContext) -> dict | None:
    """Return the logged-in user's profile, or None if the session is invalid."""
    for path in _ME_ENDPOINTS:
        try:
            resp = ctx.request.get(BASE_URL + path)
        except PlaywrightError as exc:
            log.debug("users/me request failed: %s", exc)
            continue
        if resp.ok:
            data = resp.json()
            if data.get("id"):
                return data
    return None


def ensure_session(ctx: BrowserContext, *, interactive: bool = False) -> dict | None:
    """Validate the Blackboard session, refreshing it via SSO if possible.

    Non-interactive mode still navigates to Blackboard once: if the Microsoft
    SSO cookies are alive, Blackboard re-issues its session cookie silently,
    which stretches one manual login across weeks of headless runs.
    """
    user = current_user(ctx)
    if user:
        return user

    page = ctx.new_page()
    try:
        page.goto(BASE_URL + "/ultra", wait_until="domcontentloaded")
        timeout_ms = 300_000 if interactive else 30_000
        page.wait_for_url(_ULTRA_URL, timeout=timeout_ms)
        # let the SPA finish setting session cookies
        page.wait_for_timeout(2_000)
    except PlaywrightTimeout:
        return None
    finally:
        page.close()
    return current_user(ctx)
