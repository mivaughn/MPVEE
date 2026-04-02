# Cloud Schedule Setup with PAT

Use a Programmatic Access Token (PAT) so Member Friday Listpull runs in the cloud even when your Mac is off.

---

## Step 1: Create a PAT in Snowflake

You need **ACCOUNTADMIN** or a role that can run `ALTER USER ... ADD PAT`.

In Snowflake (SQL worksheet or Snowsight):

```sql
ALTER USER MIVAUGHN ADD PROGRAMMATIC ACCESS TOKEN member_friday_listpull
  DAYS_TO_EXPIRY = 365
  COMMENT = 'Monthly listpull automation';
```

**Important:** Snowflake shows the token **once** when you create it. Copy and store it securely.

If your org requires it, ask your Snowflake admin to create the PAT for you.

---

## Step 2: Update the Script (Already Done)

The script supports PAT via `SNOWFLAKE_TOKEN` or `SNOWFLAKE_PAT`:

- **With PAT set:** Uses token (no browser) – for cloud
- **Without PAT:** Uses SSO – for local

---

## Step 3: GitHub Actions Setup

### 3a. Push to GitHub

If this repo isn't on GitHub yet:

```bash
git init
git remote add origin https://github.com/YOUR_USERNAME/YOUR_REPO.git
git add .
git commit -m "Add Member Friday Listpull"
git push -u origin main
```

### 3b. Add Secrets

1. Repo → **Settings** → **Secrets and variables** → **Actions**
2. **New repository secret** for each:

| Secret | Value |
|--------|-------|
| `SNOWFLAKE_USER` | MIVAUGHN |
| `SNOWFLAKE_ACCOUNT` | SOFI-SOFI |
| `SNOWFLAKE_TOKEN` | Your PAT (from Step 1) |
| `SNOWFLAKE_WAREHOUSE` | DEFAULT |
| `SLACK_WEBHOOK_URL` | (Optional) Slack webhook for success notification |

### 3c. Slack notification (optional)

To get notified when the export succeeds:

1. In Slack: **Settings** → **Integrations** → **Incoming Webhooks** → **Add to Slack**
2. Choose a channel, create the webhook, copy the URL
3. Add as GitHub secret: `SLACK_WEBHOOK_URL`

### 3d. Schedule

The workflow (`.github/workflows/member-friday-listpull.yml`) runs:

- **Automatically:** 6 AM Pacific (14:00 UTC) on the 1st of each month
- **Manually:** Actions tab → Member Friday Listpull → Run workflow

### 3e. Get the CSV

1. Open the repo on GitHub
2. **Actions** → select the run
3. **Artifacts** → download `invitable-users-XXX` (contains the CSV)

---

## Alternative: AWS Lambda

1. Create a Lambda function with the script and dependencies.
2. Store `SNOWFLAKE_USER`, `SNOWFLAKE_ACCOUNT`, `SNOWFLAKE_TOKEN` in **Secrets Manager**.
3. Add an **EventBridge** rule: `cron(0 17 1 * ? *)` (9 AM Pacific on 1st).
4. Have the Lambda write the CSV to S3 and optionally notify you.

---

## Security Notes

- Never commit the PAT to the repo.
- Use repo/org secrets or a secrets manager.
- Set `DAYS_TO_EXPIRY` on the token and rotate it before expiry.
- PATs may require a network policy; check with your admin.
