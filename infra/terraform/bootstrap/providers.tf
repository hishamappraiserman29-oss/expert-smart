# ==============================================================================
# Provider configuration — no credentials, hard account guard
# ==============================================================================
#
# AWS authentication is never a static access key/secret committed to this
# repository. This module must be run manually, exactly once, using
# short-lived AWS SSO / temporary session credentials only — never a static
# IAM user access key (see README.md).
#
# allowed_account_ids is a hard guard: Terraform refuses to run at all if the
# currently-authenticated identity's account does not match var.aws_account_id.
# That value must come from a read-only identity check (e.g.
# `aws sts get-caller-identity`) performed immediately before this module is
# ever applied — never assumed or hardcoded here or in any tfvars file.

provider "aws" {
  region              = var.aws_region
  allowed_account_ids = [var.aws_account_id]

  default_tags {
    tags = var.tags
  }
}
