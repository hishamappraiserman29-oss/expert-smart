# PH.3 Closure Runbook — GCP Service Account Key

**Waiver ID:** `PH3-GCP-SA-KEY-ROTATION`  
**Deadline:** 2026-06-19  
**Severity:** P0 — Full Production GO blocker  
**Source:** `docs/PH3_KEY_ROTATION_WAIVER.md` · `docs/SECURITY_AUDIT_v1.md §PH.3`

---

## Target

| Field | Value |
|---|---|
| GCP Project | `gleaming-terra-487414-f4` |
| Service account | `appraiser-sync@gleaming-terra-487414-f4.iam.gserviceaccount.com` |
| Key ID to delete | `39b698a44b239fc7712314a035f7202e05718842` |
| Local key file (untracked) | `core_engine/service_account.json` — on disk, NOT in git |

> ⚠️ Do NOT commit `core_engine/service_account.json` or any replacement key file to git.
> The `.gitignore` blocks it, but never force-add it.

---

## Pre-Requisites — Resolve Before Proceeding

### Blocker 1 — IAM permissions

You need **one** of these roles on project `gleaming-terra-487414-f4`:

| Role | Purpose |
|---|---|
| `roles/iam.serviceAccountKeyAdmin` | Delete/create keys on service accounts |
| `roles/iam.serviceAccountAdmin` | Full service account management |
| `roles/viewer` + `roles/iam.serviceAccountKeyAdmin` | List accounts + manage keys |

**How to get them:**  
Ask the GCP project owner or an existing admin to grant your Google account the
`Service Account Key Admin` role via:  
IAM & Admin → IAM → Add principal → your email → Role: `Service Account Key Admin`

Or ask the admin to perform the operation on your behalf using this runbook.

### Blocker 2 — MFA on your Google account

Google Cloud Console requires 2-Step Verification for sensitive IAM operations.

**How to enable:**
1. Go to: https://myaccount.google.com/security
2. Click **"2-Step Verification"** → **Get started**
3. Choose: Authenticator app (TOTP) — preferred over SMS
4. Scan the QR code with Google Authenticator / Authy
5. Confirm a test code
6. Generate and store backup codes securely (password manager)

---

## Decision Tree — Choose One Option

```
Does this service account still have any active workload using it?
├── YES → Use Option A (rotate the key)
└── NO  → Check GCP Activity logs:
           └── Zero activity in last 90 days?
               ├── YES → Use Option C (disable/delete account)
               └── NO  → Use Option A (rotate) OR Option C if workload can be removed
```

---

## Option A — Rotate the Key

**Choose when:** The service account is still needed by an active workload.

**Steps:**

1. Log in to https://console.cloud.google.com  
   (Must have MFA + `iam.serviceAccountKeyAdmin` permission)

2. Navigate to: **IAM & Admin → Service Accounts**

3. Find `appraiser-sync@gleaming-terra-487414-f4.iam.gserviceaccount.com` → click it

4. Click the **"Keys"** tab

5. Confirm you see key ID `39b698a44b239fc7712314a035f7202e05718842`  
   *(If it's already absent — stop here; the old key was already deleted. Proceed to Option B evidence collection.)*

6. Click **"Add Key"** → **"Create new key"** → **JSON** → **Create**  
   A new `.json` file will download — save it to a **secret manager** or **secure vault** only.  
   Do NOT save it inside this repository.

7. Distribute the new key to any systems that need it  
   (environment variable `GOOGLE_APPLICATION_CREDENTIALS` → path outside repo)

8. Wait 24 hours to confirm the new key works in all systems.

9. Return to the **Keys** tab → find key ID `39b698a44b239fc7712314a035f7202e05718842`  
   → click the **delete (trash) icon** → confirm deletion.

10. Delete the local file: `core_engine/service_account.json`  
    (Run: `del "core_engine\service_account.json"` — it is already gitignored.)

**Evidence to capture (screenshots):**
- Keys tab showing ONLY the new key (old ID `39b698a4...` absent)
- Activity log entry: deletion of old key, timestamp + actor email
- Confirmation that new key is in secret manager (e.g., a screenshot of the vault entry, not the key content)

---

## Option B — Confirm Key Was Never Used / Already Deleted

**Choose when:** You believe the account was a dev leftover or the key was already cleaned up.

**Steps:**

1. Log in to https://console.cloud.google.com

2. Navigate to: **IAM & Admin → Service Accounts**

3. Find `appraiser-sync@gleaming-terra-487414-f4.iam.gserviceaccount.com`

4. Click the **"Keys"** tab — if key ID `39b698a44b239fc7712314a035f7202e05718842` is absent:  
   The key is already deleted. Capture a screenshot. Proceed to evidence collection.

5. Click the **"Permissions"** tab — review any IAM bindings (roles granted to this SA)

6. Click **"Logs"** or check **Cloud Audit Logs** (Logging → Logs Explorer):  
   Filter: `resource.type="service_account"` + `protoPayload.authenticationInfo.serviceAccountId~"appraiser-sync"`  
   Look for last-activity timestamp.

7. If last activity is > 90 days ago or zero entries:  
   Proceed to Option C (disable). If recent activity exists, switch to Option A.

**Evidence to capture:**
- Screenshot of Keys tab (showing absence of the old key ID, or the key present)
- Screenshot of Logs/Activity showing last-use timestamp
- Brief written note: date checked, what you found

---

## Option C — Disable or Delete the Service Account

**Choose when:** The account is no longer needed at all (cleanest closure).

**Steps:**

1. Log in to https://console.cloud.google.com

2. Navigate to: **IAM & Admin → Service Accounts**

3. Find `appraiser-sync@gleaming-terra-487414-f4.iam.gserviceaccount.com`

4. Click the three-dot menu (⋮) → **"Disable service account"** → Confirm  
   *(Account is soft-disabled; can be re-enabled within 30 days if needed)*

5. Optionally (after 30 days, if no issues): three-dot menu → **"Delete service account"**

6. Delete the local file: `core_engine/service_account.json`  
   (Run: `del "core_engine\service_account.json"` — it is already gitignored.)

**Evidence to capture:**
- Screenshot of the service account showing **Disabled** status
- Activity log entry showing the disable action, timestamp + actor
- (If deleted later) Screenshot confirming account no longer exists

---

## After the External Steps — Verification

Run from the repo root after completing Option A, B, or C:

```powershell
# Using gcloud CLI (if installed):
gcloud iam service-accounts describe `
    appraiser-sync@gleaming-terra-487414-f4.iam.gserviceaccount.com `
    --format="value(disabled)"
# Expect: True (Option C) or error "NOT_FOUND" (deleted)

gcloud iam service-accounts keys list `
    --iam-account=appraiser-sync@gleaming-terra-487414-f4.iam.gserviceaccount.com
# Expect: empty list (Option A after deletion) or error (Option C)
```

Or run the bundled evidence manifest tool:

```powershell
python tools/verify_ph3_closure.py `
    --evidence-dir <path-to-your-screenshots-folder> `
    --option A      # or B or C
# Writes: docs/PH3_CLOSURE_EVIDENCE.md (hash manifest — safe to commit)
```

Confirm that `core_engine/service_account.json` no longer exists locally:

```powershell
Test-Path "core_engine\service_account.json"
# Expect: False
```

---

## Post-Closure Docs Update (Internal — after external action)

After confirming closure, update these files and commit:

1. **`docs/PH3_KEY_ROTATION_WAIVER.md`** — fill in the "Closure Record" table:
   - Closure date, closed by, option chosen, evidence reference

2. **`docs/SECURITY_AUDIT_v1.md`** — update the PH.3 row:
   - Change `⚠️ WAIVED TEMPORARILY` → `✅ CLOSED — Option <A/B/C>, <date>`

3. **`docs/FINAL_RELEASE_HANDOFF_v1.1.0.md`** — update:
   - P0 row in §11: mark ✅ closed
   - Release Gate summary: update Full Production GO verdict

4. Run the evidence manifest tool (generates `docs/PH3_CLOSURE_EVIDENCE.md`)

5. Commit all of the above as one atomic commit:
   ```
   security(ph3): close GCP appraiser-sync service account key (Option <X>)
   ```

---

## Risk Notes

| Rule | Detail |
|---|---|
| Never commit key files | Even if revoked — git history persists; `.gitignore` is enforced but `git add --force` bypasses it |
| Never email keys | Use a secret manager (GCP Secret Manager, 1Password, HashiCorp Vault) |
| Don't skip the wait (Option A) | After creating a new key, wait for deployment confirmation before deleting the old one |
| Capture evidence first | Screenshots before and after — needed for the audit trail |
| If key was shared | Treat as compromised regardless; rotate immediately and check GCP audit logs for unauthorized API calls |

---

## Escalation

If you cannot get IAM access granted in time before the deadline (2026-06-19):

1. Ask the GCP project owner (Hisham Elmahdy) to perform the action directly using this runbook
2. Or ask an admin with `roles/owner` to grant `roles/iam.serviceAccountKeyAdmin` temporarily
3. Document any extension of the waiver deadline in `docs/PH3_KEY_ROTATION_WAIVER.md`

---

## Status Tracking

| Step | Status | Date | Operator | Evidence |
|---|---|---|---|---|
| Blocker 1: IAM permissions granted | ⏳ | | | |
| Blocker 2: MFA enabled | ⏳ | | | |
| Option chosen (A / B / C) | ⏳ | | | |
| External GCP action completed | ⏳ | | | |
| Local `service_account.json` deleted | ⏳ | | | |
| Evidence captured | ⏳ | | | |
| `tools/verify_ph3_closure.py` run | ⏳ | | | |
| Docs updated + committed | ⏳ | | | |
| Release Gate re-evaluated | ⏳ | | | |

---

**EXPERT_SMART | PH.3 Closure Runbook | 2026-05-19**
