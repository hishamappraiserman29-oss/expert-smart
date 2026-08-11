# Terraform Remote-State Bootstrap

## Status

This module creates real AWS resources (an S3 bucket and a KMS key) when
applied. **It has not been applied.** As of this commit it exists as
reviewed code only — no `terraform init`, `plan`, or `apply` has been run
against it, and no AWS resource described here currently exists.

## What this is

An independent Terraform root module, deliberately **not** referenced by
`infra/terraform/environments/production/main.tf` and never composed into
that module graph. It exists to break a circularity: the S3 bucket
`environments/production`'s remote backend depends on cannot itself be
created *by* that same backend, because the backend must already exist at
`terraform init` time. This module creates that bucket (and its dedicated
KMS key) using Terraform's **default local state** — the one place in this
project's entire architecture where local state is the correct, intentional
choice, not an oversight.

## What it creates

* One S3 bucket, name `<project_name>-tfstate-<aws_account_id>-<aws_region>`
  * Versioning enabled (the sole state-recovery mechanism — Object Lock is
    intentionally not configured, see "Decisions" below)
  * Default encryption: SSE-KMS using the dedicated key below,
    `bucket_key_enabled = true`
  * All four S3 Block Public Access settings enabled
  * Object Ownership: `BucketOwnerEnforced` (ACLs disabled entirely)
  * Bucket policy: denies any non-TLS request, denies any `PutObject` not
    encrypted with the dedicated key — both as principal-agnostic `Deny`
    guardrails, not principal Allow-lists (see "IAM roles" below)
  * `prevent_destroy = true`
* One customer-managed symmetric KMS key, dedicated to this state bucket
  only (never shared with any other purpose)
  * Automatic key rotation enabled
  * Deletion window configurable (`var.kms_deletion_window_days`, 7-30 days, default 30)
  * Key policy grants only account-root administrative access — no other
    principal, since the CI roles below don't exist yet
  * `prevent_destroy = true`
  * A friendly alias, `alias/<project_name>-terraform-state`

## What it deliberately does NOT create

* **No CI/execution IAM roles** (`terraform-plan`, `terraform-apply`). Their
  required permissions are documented below for a separate, later,
  explicitly authorized implementation — not fabricated here as
  placeholder roles or ARNs.
* **No S3 Object Lock configuration** — declined by design. Object Lock
  cannot be enabled retroactively on an existing bucket, so this is final
  for this bucket's lifetime, not deferred.
* **No MFA Delete** — declined by design, and also not achievable via a
  standard Terraform apply regardless (MFA Delete requires an
  MFA-authenticated request from the bucket owner's root account issued
  directly against the S3 API).
* **No DynamoDB lock table** — this project uses Terraform's S3-native state
  locking (`use_lockfile = true`, declared in
  `environments/production/backend.tf`), which requires Terraform >= 1.11.

## Do not destroy

Never run `terraform destroy` (or any plan that would destroy the bucket or
KMS key) against this module once it has been applied. Both the S3 bucket
and the KMS key carry `lifecycle { prevent_destroy = true }`, so Terraform
itself will refuse such a plan — but the resources this module creates are
the foundation every other environment's state depends on, so this backend
must never be treated as routine, disposable infrastructure. If the bucket
or key genuinely needs to be replaced, that is a deliberate, manually
reviewed, separately authorized operation — never an accidental side effect
of cleaning up or re-running this module.

## One-time run procedure

1. **Identity check (read-only, mandatory first step)**:
   ```
   aws sts get-caller-identity
   ```
   Confirm the returned `Account` is the intended production AWS account.
   Never assume or hardcode this value — it becomes `var.aws_account_id`.
2. Obtain short-lived AWS SSO / temporary session credentials for that
   account. **Never use a static IAM user access key** for this step.
3. `terraform init` (local backend — no `-backend-config` needed).
4. `terraform plan -var="aws_account_id=<verified 12-digit ID>"`, review the
   plan carefully — this is the one place in the whole project where a
   human reviews a plan against **real** infrastructure for the first time.
5. `terraform apply` with the same var, using the same short-lived
   credentials. Discard/let the credentials expire immediately after.
6. **Follow-up (separate, later, explicitly authorized step — not part of
   this same run)**: migrate this module's own local state into the bucket
   it just created, under the key documented by `output.bootstrap_state_key`
   (`bootstrap/terraform.tfstate`), via `terraform init -migrate-state` with
   the appropriate `-backend-config` values. This ensures a future
   accidental re-run of this module doesn't lose track of what already
   exists.

## Backend configuration for `environments/production`

Once this module has been applied, `environments/production/backend.tf`'s
`-backend-config` values (never committed as literal values) are:

```
bucket = "<output.state_bucket_name>"
key    = "production/eks/terraform.tfstate"
region = "<var.aws_region>"
```

`encrypt = true` and `use_lockfile = true` are already declared in the
committed `backend.tf` file itself.

## Required IAM permissions for the CI execution roles (documented, not created)

Two roles are planned — `terraform-plan` (broad-read, zero-write, assumable
from any PR) and `terraform-apply` (read-write, assumable only from `main` +
the `production` GitHub Environment claim) — matching the CI-identity model
already designed for the rest of this project's infrastructure. Neither is
created by this module. Their state-related permissions, precisely:

**State object** (`production/eks/terraform.tfstate`):
| Action | plan | apply |
|---|---|---|
| `s3:GetObject` | yes | yes |
| `s3:PutObject` | no | yes |
| `s3:DeleteObject` | **no** | **no** — never, from either role |

**Lock object** (`production/eks/terraform.tfstate.tflock`) — a distinct
object from the state object; Terraform's S3-native locking acquires this
lock even during `plan`, so both roles need the full set:
| Action | plan | apply |
|---|---|---|
| `s3:GetObject` | yes | yes |
| `s3:PutObject` | yes | yes |
| `s3:DeleteObject` | yes | yes |

**Bucket-level**:
* `s3:ListBucket`, scoped via an `s3:prefix` condition to `production/eks/*`
  (both roles only ever need this prefix; `bootstrap/*` is never touched by
  either CI role)

**KMS** (scoped to this module's dedicated key ARN only, never `"*"`):
| Action | plan | apply |
|---|---|---|
| `kms:Decrypt` | yes | yes |
| `kms:GenerateDataKey` | no | yes |

Reading encrypted state requires `kms:Decrypt`; writing a new encrypted
state object requires `kms:GenerateDataKey` in addition. `plan` never writes
state, so it never needs `kms:GenerateDataKey`.

## Decisions this module reflects (see the approved remote-state design)

* SSE-KMS with a dedicated customer-managed key — approved
* No S3 Object Lock; Versioning is the recovery mechanism — approved
* No MFA Delete — approved
* Target account verified via read-only identity check before every apply,
  never hardcoded — required
* Short-lived credentials only for this one-time run — required
* Bootstrap state migrates to `bootstrap/terraform.tfstate`; production uses
  `production/eks/terraform.tfstate` — approved

## Governance

`merge to main` does not run this module. Nothing in this repository's CI
automatically applies it. It is applied exactly once, manually, by a human,
following the procedure above.
