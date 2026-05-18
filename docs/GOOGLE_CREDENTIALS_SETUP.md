# Google Cloud Credentials — Setup & Security Policy

---

## PH.3 Status — Service Account Key Rotation

### Repo Cleanup — DONE ✅

| Item | Status |
|---|---|
| `service_account.json` tracked in Git | ✅ Not tracked |
| `credentials.json` tracked in Git | ✅ Not tracked |
| `.gitignore` blocks all credential file patterns | ✅ Hardened (root + `core_engine/`) |
| `.env.example` documents `GOOGLE_APPLICATION_CREDENTIALS` | ✅ Placeholder only — no real value |
| Private key content in any tracked file | ✅ Not present (CI secret guard verified) |
| CI secret guard scans for credential files on every push | ✅ Active (`ci-cd.yml` test job) |

### Manual Cloud Action — PENDING ⚠️ PRODUCTION BLOCKER

The old service account key for:

```
appraiser-sync@gleaming-terra-487414-f4.iam.gserviceaccount.com
```

has **not** been rotated or deleted. This is a manual Google Cloud Console action that cannot
be completed from within the repository.

**Current blockers (as of 2026-05-18):**

| Blocker | Detail |
|---|---|
| MFA / 2-Step Verification not completed | The owning Google account requires 2-Step Verification before IAM operations can be performed. |
| Missing IAM permission: `iam.serviceAccounts.list` | Required to list service accounts in the project. |
| Missing IAM permission: `resourcemanager.projects.get` | Required to access project `gleaming-terra-487414-f4`. |

### Required Manual Steps to Close PH.3

1. Sign in to [Google Cloud Console](https://console.cloud.google.com) with the Google account
   that **owns or can administer** project `gleaming-terra-487414-f4`.
2. Complete **MFA / 2-Step Verification** setup for that account.
3. Request or obtain at minimum these IAM roles on the project:
   - `roles/iam.serviceAccountKeyAdmin` — to delete / create keys
   - `roles/viewer` or `roles/iam.securityReviewer` — to list service accounts
4. Navigate to: **IAM & Admin → Service Accounts**
5. Locate: `appraiser-sync@gleaming-terra-487414-f4.iam.gserviceaccount.com`
6. Open the **Keys** tab.
7. **Delete** any existing key(s) that are no longer needed or are of unknown provenance.
8. If a new key is required for local development or staging:
   a. Click **Add Key → Create new key → JSON**.
   b. Download to a safe path **outside** the repository tree (e.g., `~/.secrets/`).
   c. Update `GOOGLE_APPLICATION_CREDENTIALS` in your local `.env` and in all deployment environments.
   d. Test the application with the new key before deleting the old one.
9. Confirm no key file has entered the repository:
   ```bash
   git ls-files | grep -Ei "service_account|credentials"
   ```

### Production Gate

| Gate | Status |
|---|---|
| Repo credential hygiene | ✅ CONDITIONAL-GO |
| CI pipeline | ✅ CONDITIONAL-GO |
| Production dry-run final sign-off | ❌ BLOCKED — pending key rotation or formal waiver |
| `v1.1.0` release tag | ❌ BLOCKED — pending key rotation or formal waiver |
| Public production release | ❌ BLOCKED — pending key rotation or formal waiver |

> CI hardening is **not** blocked by this item. Only the final production release gate is held.

### Waiver Path

If the project owner can confirm the key is already deleted, expired, or was never used in
production, this blocker may be formally waived. Record the decision here:

| Field | Value |
|---|---|
| Owner name | _______________ |
| Date confirmed | _______________ |
| Confirmation method | GCP Console screenshot / email / verbal |
| Decision | ☐ Rotated and tested  ☐ Deleted (unused)  ☐ Formally waived — reason: ___ |

---

## Rule 1 — Never commit credential files

`service_account.json`, `credentials.json`, and `token.json` are blocked
by `.gitignore` and `core_engine/.gitignore`.  Committing them is a
**critical security incident** — real private keys would be exposed in
public or shared repository history.

If you accidentally commit a key file:
1. Immediately revoke / delete the key in Google Cloud Console.
2. Generate a new key.
3. Use `git filter-repo` or contact your security team to purge the file
   from history — a simple `git rm` is not enough once it has been pushed.

---

## Rule 2 — Use the `GOOGLE_APPLICATION_CREDENTIALS` environment variable

The application never hard-codes a path to a key file.  Point the runtime
at your key by setting:

```
GOOGLE_APPLICATION_CREDENTIALS=/absolute/path/to/service_account.json
```

Copy `.env.example` to `.env` and fill in the path.  The `.env` file is
ignored by Git.

---

## Rule 3 — Rotate any previously exposed key

If there is any doubt that a key was ever shared outside of your local
machine (emailed, pasted in chat, accidentally committed then removed,
visible in a screen-share), treat it as compromised and rotate it:

1. Google Cloud Console → IAM & Admin → Service Accounts.
2. Select the service account (`appraiser-sync@...` or equivalent).
3. Keys tab → **Delete** the old key.
4. **Add Key** → Create new key → JSON → download to a safe local path.
5. Update `GOOGLE_APPLICATION_CREDENTIALS` in your local `.env` and in
   every deployment environment.

Rotation is low-risk and takes under two minutes.  When in doubt, rotate.

---

## Local development setup

```bash
# 1. Download a service account key from Google Cloud Console
#    IAM & Admin → Service Accounts → your-account → Keys → Add Key → JSON

# 2. Store it outside the repo, e.g.:
#    ~/.secrets/expert_smart_service_account.json

# 3. Set the env var (add to your shell profile or .env):
export GOOGLE_APPLICATION_CREDENTIALS="/home/you/.secrets/expert_smart_service_account.json"

# 4. Verify the application can read it:
python -c "import os; print(os.environ.get('GOOGLE_APPLICATION_CREDENTIALS'))"
```

Never place the key file inside the repository directory tree, even in a
subdirectory not currently tracked — a future `git add .` could capture it.

---

## Production / CI deployment

Use your platform's native secret manager instead of writing the key to
disk:

| Platform | Recommended approach |
|---|---|
| Google Cloud Run | Mount the JSON as a Secret Manager secret at `/secrets/sa.json` and set `GOOGLE_APPLICATION_CREDENTIALS=/secrets/sa.json` |
| AWS ECS / Lambda | Store JSON in Secrets Manager; inject via task definition env var |
| HashiCorp Vault | Store under a KV path; inject via agent sidecar |
| GitHub Actions | Store the JSON content as a repository secret; write to a temp file in the workflow step |

For Cloud Run workloads running as the service account itself, you can
skip the key file entirely by granting the Cloud Run service account the
required IAM roles — Application Default Credentials (ADC) will be used
automatically.

---

## Files covered by `.gitignore`

The following patterns are blocked at both root and `core_engine/` level:

| Pattern | Scope |
|---|---|
| `service_account.json` | all directories |
| `credentials.json` | all directories |
| `token.json` | all directories |

Run `git check-ignore -v <file>` to confirm a credential file is ignored
before running `git add`.
