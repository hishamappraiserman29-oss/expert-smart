output "state_bucket_name" {
  description = "Name of the Terraform remote-state S3 bucket."
  value       = aws_s3_bucket.terraform_state.id
}

output "state_bucket_arn" {
  description = "ARN of the Terraform remote-state S3 bucket."
  value       = aws_s3_bucket.terraform_state.arn
}

output "state_bucket_region" {
  description = "AWS region the state bucket was created in."
  value       = var.aws_region
}

output "kms_key_arn" {
  description = "ARN of the dedicated customer-managed KMS key used for state encryption."
  value       = aws_kms_key.terraform_state.arn
}

output "kms_key_id" {
  description = "Key ID of the dedicated customer-managed KMS key used for state encryption."
  value       = aws_kms_key.terraform_state.key_id
}

output "kms_key_alias" {
  description = "Alias of the dedicated customer-managed KMS key."
  value       = aws_kms_alias.terraform_state.name
}

output "production_state_key" {
  description = "Documented S3 object key environments/production/backend.tf should use via -backend-config (key=...). Not used by this module directly — informational only."
  value       = local.production_state_key
}

output "bootstrap_state_key" {
  description = "Documented S3 object key this bootstrap module's own local state should be migrated to after the bucket exists, via `terraform init -migrate-state`. Not applied by this module itself."
  value       = local.bootstrap_state_key
}
