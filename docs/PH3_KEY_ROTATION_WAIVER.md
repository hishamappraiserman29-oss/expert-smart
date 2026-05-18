# PH.3 Google Service Account Key Rotation — Formal Waiver

---

## Waiver Summary

| Field | Value |
|---|---|
| **Waiver ID** | PH3-GCP-SA-KEY-ROTATION |
| **Project ID** | `gleaming-terra-487414-f4` |
| **Target service account** | `appraiser-sync@gleaming-terra-487414-f4.iam.gserviceaccount.com` |
| **Repo cleanup status** | ✅ DONE |
| **Manual cloud rotation status** | ⚠️ WAIVED TEMPORARILY — PENDING OWNER ACCESS |
| **Waiver date** | 2026-05-19 |
| **Owner / approver** | Hisham Elmahdy (project owner) |
| **Approval date** | 2026-05-19 |
| **Risk accepted until** | Key rotation completed, OR next review date, whichever comes first |
| **Next review date** | 2026-06-19 (30 days) |

---

## Waiver Decision

**Decision (2026-05-19):**

> `v1.1.0` **may proceed as a CONDITIONAL release only.**
>
> - Repo contains no credential key material — confirmed by `git ls-files` and CI secret guard.
> - Security audit remediation (SEC-001 through SEC-009) is complete.
> - CI pipeline is hardened and green.
> - PH.3 Google service account key rotation is **waived temporarily** pending project owner
>   access restoration (MFA + IAM permissions on `gleaming-terra-487414-f4`).
> - Full production sign-off (unconditional GO) remains pending until key rotation or deletion
>   is confirmed, or this waiver is formally closed via Option A, B, or C below.

**Recommended `v1.1.0` tag annotation:**

```
v1.1.0 — Conditional release.
Security audit remediated; CI hardened.
PH.3 Google service account key rotation is waived temporarily
pending project owner access/MFA resolution.
Repo contains no credential key material.
Waiver: PH3-GCP-SA-KEY-ROTATION (docs/PH3_KEY_ROTATION_WAIVER.md)
```

**What CONDITIONAL means:**

| Allowed under CONDITIONAL | Not allowed under CONDITIONAL |
|---|---|
| Creating `v1.1.0` tag with waiver annotation | Declaring unconditional production GO |
| Running a scoped conditional dry-run | Full public production launch without owner sign-off |
| Merging to `main` and building Docker image | Deploying to production cluster without owner sign-off |

---

## Reason for Waiver

Manual Google Cloud key rotation could not be completed due to access constraints:

| Blocker | Detail |
|---|---|
| MFA / 2-Step Verification not completed | The owning Google account requires 2-Step Verification before IAM console operations can be performed. Verification setup was attempted and could not be completed. |
| Missing permission: `iam.serviceAccounts.list` | Required to enumerate service accounts within the project. |
| Missing permission: `resourcemanager.projects.get` | Required to access project resources on `gleaming-terra-487414-f4`. |

The repository-side remediation is fully complete (see **Compensating Controls** below).
The only outstanding item is the deletion or rotation of the key that exists in Google Cloud Console,
which requires the project owner to regain appropriate IAM access.

---

## Compensating Controls (Active)

These controls limit the risk exposure while the waiver is in effect:

| Control | Status |
|---|---|
| `service_account.json` not tracked in Git | ✅ Confirmed — `git ls-files` verified |
| `credentials.json` not tracked in Git | ✅ Confirmed — `git ls-files` verified |
| No private key content in any tracked file | ✅ Confirmed — CI secret guard scans every push |
| `.gitignore` blocks all credential file patterns | ✅ Hardened at root and `core_engine/` level |
| `.env.example` uses placeholder only | ✅ `GOOGLE_APPLICATION_CREDENTIALS=` (empty) |
| CI secret guard active on every push | ✅ `ci-cd.yml` test job scans tracked files |
| Documentation added | ✅ `docs/GOOGLE_CREDENTIALS_SETUP.md` + this file |

---

## Risk Assessment

| Risk | Rating | Notes |
|---|---|---|
| Key material in Git repository | None | Confirmed not tracked; CI guard prevents future commit |
| Old GCP key remains active | Low–Medium | Key exists in Google Cloud only; no known exploit vector from current repo state |
| Unauthorized GCP access via old key | Low | Key requires possession of the JSON file, which is not in the repo and was never committed |
| Key was previously exposed outside repo | Unknown | Cannot confirm or deny without GCP console access; rotation is the safest resolution |

**Overall residual risk:** Low while compensating controls remain active.
**Risk would escalate to High** if: (a) the key JSON file is found to have been shared or exposed,
or (b) GCP audit logs show unexpected API calls under this service account.

---

## Required IAM Roles to Close This Waiver

To perform the manual rotation and close this waiver, the project owner must obtain:

| Role | Purpose |
|---|---|
| `roles/iam.serviceAccountKeyAdmin` | Delete existing keys and create new ones |
| `roles/viewer` OR `roles/iam.securityReviewer` | List service accounts in the project |

---

## Closure Conditions

This waiver is closed when **one** of the following is confirmed:

- [ ] **Option A — Rotation completed:** Project owner deleted the old key and optionally created a new one. `GOOGLE_APPLICATION_CREDENTIALS` updated in all runtime environments. New key tested. No key file inside the repository.

- [ ] **Option B — Key confirmed deleted/unused:** Project owner confirms (via GCP Console) that the service account key was already deleted, expired, or was never used in any live environment. No new key is needed.

- [ ] **Option C — Service account disabled:** Project owner confirms the entire service account `appraiser-sync@...` is disabled or deleted in GCP, making key rotation moot.

---

## Closure Record (fill when resolved)

| Field | Value |
|---|---|
| Closure date | `<TO BE FILLED>` |
| Closed by | `<TO BE FILLED>` |
| Option chosen | A / B / C (delete as appropriate) |
| GCP Console screenshot / confirmation ref | `<TO BE FILLED>` |
| New `GOOGLE_APPLICATION_CREDENTIALS` path (if Option A) | outside repo — not recorded here |
| Signed off by | `<TO BE FILLED>` |

---

## Production Gate Impact

| Gate | Status while waiver is active |
|---|---|
| Repo credential hygiene | ✅ GO |
| CI pipeline (test + lint + build) | ✅ GO |
| Production dry-run (conditional) | ⚠️ CONDITIONAL — owner acknowledgement of this waiver required before proceeding |
| `v1.1.0` release tag | ⚠️ CONDITIONAL — allowed with waiver annotation (see **Waiver Decision** above); not a full unconditional GO |
| Public production release (unconditional) | ❌ BLOCKED — requires Option A, B, or C closure, OR explicit written risk acceptance by project owner |

---

## References

- `docs/GOOGLE_CREDENTIALS_SETUP.md` — credential policy, setup instructions, rotation steps
- `docs/PROD_READINESS_CHECKLIST.md` — Section 1 Security, PH.3 item
- `docs/SECURITY_AUDIT_v1.md` — Post-Audit Status, PH.3 row
- `.github/workflows/ci-cd.yml` — Secret guard step (scans tracked files on every push)

---

**EXPERT_SMART | PH.3 Key Rotation Waiver | 2026-05-19**
