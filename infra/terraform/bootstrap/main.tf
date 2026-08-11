# ==============================================================================
# Terraform remote-state bootstrap — independent root module, LOCAL STATE
# ==============================================================================
#
# This module breaks the backend bootstrap circularity: the S3 bucket and KMS
# key it creates are what environments/production/backend.tf will eventually
# point at, so this module cannot itself use that backend. It uses
# Terraform's default local state, run exactly once, manually, by a human
# holding short-lived AWS SSO/temporary credentials (never a static IAM user
# access key). See README.md for the full one-time run procedure and the
# follow-up `terraform init -migrate-state` step that moves THIS module's own
# state into the bucket it creates, under bootstrap/terraform.tfstate.
#
# CI/execution IAM roles (terraform-plan, terraform-apply) are intentionally
# NOT created here — only their required permissions are documented in
# README.md, for a separate, later, explicitly authorized implementation.

locals {
  state_bucket_name    = "${var.project_name}-tfstate-${var.aws_account_id}-${var.aws_region}"
  production_state_key = "production/eks/terraform.tfstate"
  bootstrap_state_key  = "bootstrap/terraform.tfstate"
}

# ── KMS: dedicated customer-managed key for state encryption ────────────────
resource "aws_kms_key" "terraform_state" {
  description              = "Dedicated customer-managed key for Expert Smart Terraform state encryption (SSE-KMS)."
  deletion_window_in_days  = var.kms_deletion_window_days
  enable_key_rotation      = true
  key_usage                = "ENCRYPT_DECRYPT"
  customer_master_key_spec = "SYMMETRIC_DEFAULT"

  # Least-privilege key policy: only the account's root/IAM administrative
  # path can manage the key — required, or the key becomes unmanageable even
  # by account admins. CI-role kms:Decrypt / kms:GenerateDataKey grants are
  # added once the terraform-plan / terraform-apply IAM roles exist (see
  # README.md) — never fabricated here since those roles are not yet created.
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid       = "EnableRootAccountKeyAdministration"
        Effect    = "Allow"
        Principal = { AWS = "arn:aws:iam::${var.aws_account_id}:root" }
        Action    = "kms:*"
        Resource  = "*"
      }
    ]
  })

  tags = merge(var.tags, { Name = "${var.project_name}-terraform-state-key" })

  lifecycle {
    prevent_destroy = true
  }
}

resource "aws_kms_alias" "terraform_state" {
  name          = "alias/${var.project_name}-terraform-state"
  target_key_id = aws_kms_key.terraform_state.key_id
}

# ── S3: dedicated Terraform state bucket ─────────────────────────────────────
resource "aws_s3_bucket" "terraform_state" {
  bucket = local.state_bucket_name

  tags = merge(var.tags, { Name = local.state_bucket_name })

  lifecycle {
    prevent_destroy = true
  }
}

resource "aws_s3_bucket_versioning" "terraform_state" {
  bucket = aws_s3_bucket.terraform_state.id

  versioning_configuration {
    status = "Enabled"
    # mfa_delete intentionally left unset (defaults to Disabled) — declined
    # per the approved design. Also a technical constraint independent of
    # that decision: MFA Delete cannot be enabled via a standard Terraform
    # apply at all — it requires an MFA-authenticated request issued
    # directly against the S3 API by the bucket owner's root account.
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "terraform_state" {
  bucket = aws_s3_bucket.terraform_state.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm     = "aws:kms"
      kms_master_key_id = aws_kms_key.terraform_state.arn
    }
    bucket_key_enabled = true
  }
}

resource "aws_s3_bucket_public_access_block" "terraform_state" {
  bucket = aws_s3_bucket.terraform_state.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_ownership_controls" "terraform_state" {
  bucket = aws_s3_bucket.terraform_state.id

  rule {
    object_ownership = "BucketOwnerEnforced"
  }
}

# NOTE: S3 Object Lock is intentionally NOT configured on this bucket —
# declined per the approved design. Object Lock cannot be enabled
# retroactively on an existing bucket, so this is a deliberate, final
# decision for this bucket's lifetime, not a placeholder. S3 Versioning
# (above) is the sole state-recovery mechanism.

resource "aws_s3_bucket_policy" "terraform_state" {
  bucket = aws_s3_bucket.terraform_state.id

  # Both statements below are principal-agnostic guardrails (Deny, Principal
  # "*") — they require no CI role ARN to exist yet and remain correct once
  # the terraform-plan / terraform-apply roles are created. The Allow side of
  # least privilege comes from those roles' own IAM policies (documented in
  # README.md), not from an Allow statement here — no role ARN is fabricated
  # in this bucket policy.
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid       = "DenyInsecureTransport"
        Effect    = "Deny"
        Principal = "*"
        Action    = "s3:*"
        Resource = [
          aws_s3_bucket.terraform_state.arn,
          "${aws_s3_bucket.terraform_state.arn}/*",
        ]
        Condition = {
          Bool = { "aws:SecureTransport" = "false" }
        }
      },
      {
        Sid       = "DenyWrongKmsKey"
        Effect    = "Deny"
        Principal = "*"
        Action    = "s3:PutObject"
        Resource  = "${aws_s3_bucket.terraform_state.arn}/*"
        Condition = {
          StringNotEquals = {
            "s3:x-amz-server-side-encryption-aws-kms-key-id" = aws_kms_key.terraform_state.arn
          }
        }
      }
    ]
  })

  depends_on = [aws_s3_bucket_public_access_block.terraform_state]
}
