# bbsync

Automatically downloads your lecture files from Imperial's Blackboard
(`bb.imperial.ac.uk`) and organises them into a clean local folder tree.
Works on **macOS and Windows**.

- Mirrors each course's Blackboard folder structure under `Documents/ImperialNotes/`
- Downloads lecture slides, notes, problem sheets and assignment files
- Collects Panopto / video links into a `videos.md` per course (videos aren't downloaded)
- Never re-downloads unchanged files; picks up updated versions automatically
- Runs in the background every 4 hours (launchd on macOS, Task Scheduler on Windows)

## Setup (once)

Requires Python 3.11+ ([python.org](https://www.python.org/downloads/)).

**macOS** (Terminal):

```bash
git clone https://github.com/sammyiserious/bbsync
cd bbsync
python3 -m venv .venv
.venv/bin/pip install -e .
.venv/bin/playwright install chromium

.venv/bin/bbsync login      # opens a browser — sign in with Imperial SSO + MFA
.venv/bin/bbsync sync       # first download (may take a while)
.venv/bin/bbsync schedule install   # auto-sync every 4h from now on
```

Optional alias so you can just type `bbsync`:

```bash
echo "alias bbsync=\"$PWD/.venv/bin/bbsync\"" >> ~/.zshrc
```

**Windows** (PowerShell):

```powershell
git clone https://github.com/sammyiserious/bbsync
cd bbsync
py -m venv .venv
.venv\Scripts\pip install -e .
.venv\Scripts\playwright install chromium

.venv\Scripts\bbsync login      # opens a browser — sign in with Imperial SSO + MFA
.venv\Scripts\bbsync sync       # first download (may take a while)
.venv\Scripts\bbsync schedule install   # auto-sync every 4h from now on
```

## Commands

| Command | What it does |
|---|---|
| `bbsync login` | Open a browser to sign in once. The session is saved and reused headlessly for weeks. |
| `bbsync sync` | Download new/changed files right now. |
| `bbsync courses` | List courses. `--disable "Maths"` / `--enable "Maths"` to control which sync. |
| `bbsync schedule install` | Install the background job. Also `uninstall` / `status`. |
| `bbsync status` | Show destination, last sync time and schedule state. |

## Configuration

`~/.bbsync/config.toml` (macOS) / `C:\Users\<you>\.bbsync\config.toml` (Windows) —
created after first login:

```toml
dest = "/Users/sammy/Documents/ImperialNotes"  # where files go
interval_hours = 4                              # background sync frequency

[courses."_12345_1"]
name = "Introduction to Machine Learning"
enabled = true
```

After changing `interval_hours`, run `bbsync schedule install` again to apply it.

## When the session expires

SSO sessions typically survive for weeks (bbsync silently refreshes them on each
run). When one finally dies, the background sync sends a desktop notification —
just run `bbsync login` again.

## Platform notes

- **macOS**: schedule = launchd user agent (`~/Library/LaunchAgents/com.bbsync.sync.plist`),
  runs every N hours and at login; notifications via Notification Center.
- **Windows**: schedule = Task Scheduler task named `bbsync` (every N hours,
  runs windowless via `pythonw`); notifications are toast pop-ups. The task only
  runs while you're logged in.
- **Linux**: `login`/`sync`/`courses` work; add your own cron entry for scheduling.

## Troubleshooting

- **Logs**: background runs log to `~/.bbsync/logs/sync.log` (same path under
  your user folder on Windows).
- **"sync failed: ... ProcessSingleton"**: two syncs ran at once (the browser
  profile is locked). The next scheduled run will succeed.
- **Start fresh**: delete `~/.bbsync/manifest.json` to force re-downloading
  everything, or `~/.bbsync/browser-profile/` to force a fresh login.

## How it works

Playwright keeps a persistent Chromium profile in `~/.bbsync/browser-profile`,
so your Microsoft SSO cookies survive between runs. All Blackboard calls go
through that browser context against Blackboard's own REST API
(`/learn/api/public/v1/...` — the same endpoints the Blackboard web app uses),
so bbsync only ever sees content your account can already access.
`~/.bbsync/manifest.json` records every downloaded attachment so syncs are
idempotent.
