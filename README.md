# Rundle Jamf Report

Daily pipeline that pulls computer/device inventory from the Jamf Pro API and
uploads it to the **[autosync] Rundle Jamf Report** Google Sheet.

## Pipeline

`main.py` runs these in order (aborting if any step fails):

1. `query_jamf.py` — fetch computers + mobile devices from the Jamf API → `data/response_*.json`
2. `computer_report.py` — build `data/computers.csv`
3. `device_report.py` — build `data/devices.csv`
4. `upload.py` — push both CSVs to the Google Sheet

`rundle_device_report.sh` and `extension_attribute.sh` are **not** part of this
pipeline — they run on the managed Macs via Jamf policy.

## Required secrets (not in git)

- Jamf API credentials — loaded from `../jamf_client/.env` (see the
  [`jamf_client`](../jamf_client) repo), not a local `.env`
- `.env` — `NOTION_API_KEY` and any other script-local settings
- `client_secret.json` — Google service account key

Encrypted copies (`*.gpg`) are in the repo; decrypt with `gpg` or copy the
plaintext files over securely.

## Setup (both platforms)

```
python3 -m venv .venv
# macOS:   .venv/bin/pip install -r requirements.txt
# Windows: .venv\Scripts\pip install -r requirements.txt
```

`requirements.txt` installs `jamf_client` in editable mode from `../jamf_client`,
so that repo must be checked out as a sibling of this one.

Run manually with `./run.sh` (macOS) or `.\run.ps1` (Windows), or directly:
`.venv/bin/python3 main.py`. All scripts use paths relative to the project
root; `main.py` handles that regardless of where it's invoked from.

## Scheduling

### macOS (launchd)

`com.devicereport.daemon.plist` runs `run.sh` daily at 10:00. Fill in the
`$PWD` placeholders with the absolute project path, then:

```
cp com.devicereport.daemon.plist ~/Library/LaunchAgents/
launchctl load ~/Library/LaunchAgents/com.devicereport.daemon.plist
```

### Windows (Task Scheduler)

From an elevated PowerShell prompt in the project folder:

```
powershell -ExecutionPolicy Bypass -File register_task.ps1
```

This registers a daily 10:00 task named **RundleJamfReport** under the
`\Rundle\` Task Scheduler folder, that runs `run.ps1`, which appends all
output to `logs\report.log`. Missed runs (server off/asleep at 10:00) start
as soon as it's back up.

To run while no one is logged in: Task Scheduler GUI → Task Scheduler
Library → Rundle → RundleJamfReport → Properties → "Run whether user is
logged on or not" (stores the account password with the task).

Test with: `Start-ScheduledTask -TaskName RundleJamfReport -TaskPath \Rundle\`,
then check `logs\report.log`.
