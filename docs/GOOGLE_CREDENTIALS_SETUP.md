# Google Cloud Credentials — Setup & Security Policy

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
