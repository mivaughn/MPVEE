---
name: member-friday-listpull
description: >-
  Runs Snowflake queries and exports results to CSV on the local device. Uses
  Okta SSO with token caching. Use when the user wants to query Snowflake,
  download query results as CSV, run the invitable users export, or schedule
  monthly Snowflake exports.
---

# Member Friday Listpull

## When to Use

- User asks to run a Snowflake query and download CSV
- User mentions invitable users export
- User wants to schedule monthly Snowflake exports
- User has issues with Snowflake connection or CSV not downloading

## Quick Run

```bash
cd /Users/mivaughn/Documents/Cursor
python3 snowflake_connect.py
```

Output: `snowflake_exports/invitable_users_YYYY-MM-DD.csv`

## Scripts

| Script | Purpose |
|--------|---------|
| snowflake_connect.py | Main export – runs query, writes CSV |
| snowflake_connection_test.py | Test Okta SSO connection |

## Connection

- **Auth:** Okta SSO (external browser), token cached via keyring
- **Default credentials:** MIVAUGHN / SOFI-SOFI / DEFAULT warehouse
- **Override:** `SNOWFLAKE_USER`, `SNOWFLAKE_ACCOUNT`, `SNOWFLAKE_WAREHOUSE`

## Modify Query

Edit `MAIN_QUERY` in snowflake_connect.py. Use `--` for SQL comments, not `//`.

For cross-database queries, keep `USE SECONDARY ROLES ALL` before the main query.

## CSV Export Logic

Uses `csv` module (no pandas). Writes to absolute path based on script location:

```python
script_dir = os.path.abspath(os.path.dirname(__file__))
output_dir = os.path.join(script_dir, 'snowflake_exports')
```

## Monthly Schedule

**GitHub Actions** runs autonomously in the cloud. Uses PAT from repo secrets. Runs regardless of local device (on or off).
- **Cadence:** 1st of each month at 6:00 AM Pacific (14:00 UTC)
- **Trigger:** `.github/workflows/member-friday-listpull.yml` (schedule: `0 14 1 * *`)
- **Prereqs:** Repo on GitHub, secrets set (SNOWFLAKE_TOKEN, SNOWFLAKE_USER, SNOWFLAKE_ACCOUNT)
- **Output:** Actions → Artifacts → download CSV
- **Slack:** Add `SLACK_WEBHOOK_URL` secret for success notification

## Troubleshooting

- **CSV not appearing:** Check absolute path in script output; verify write permissions
- **Connection fails:** Run `python3 snowflake_connection_test.py` first
- **"User differs from IDP":** `SNOWFLAKE_USER` must match Okta login
- **SSO token expired:** Run `python3 snowflake_connect.py` manually to log in again; the script will remind you when this happens
