# ==============================================================================
# Remote state backend — SCAFFOLD ONLY, partial configuration
# ==============================================================================
#
# Real backend coordinates (bucket, key, region) are intentionally NOT set
# here. This is a deliberate Terraform "partial configuration" — the
# remaining arguments are supplied via -backend-config at `terraform init`
# time, during a separate, explicitly authorized state-bootstrap phase.
# Never hard-code an account-specific bucket name or state key in this file.
#
# S3-native state locking (use_lockfile) reached general availability in
# Terraform 1.11 and removes the need for a separate DynamoDB lock table —
# see providers.tf's required_version constraint.

terraform {
  backend "s3" {
    encrypt      = true
    use_lockfile = true

    # Supplied later via -backend-config, never committed here:
    #   bucket = "<state-bucket-name>"
    #   key    = "expert-smart/production/terraform.tfstate"
    #   region = "me-central-1"
  }
}
