# Placeholder interface contract — values are null/empty until the composed
# modules' resources are implemented under a separate, explicitly
# authorized phase. Pass-through of the most operationally relevant outputs.

output "vpc_id" {
  description = "ID of the production VPC."
  value       = module.network.vpc_id
}

output "eks_cluster_name" {
  description = "Name of the production EKS cluster."
  value       = module.eks.cluster_name
}

output "eks_cluster_endpoint" {
  description = "EKS control-plane API endpoint."
  value       = module.eks.cluster_endpoint
}

output "db_instance_endpoint" {
  description = "Connection endpoint of the production RDS instance."
  value       = module.database.db_instance_endpoint
}

output "efs_file_system_id" {
  description = "ID of the EFS file system backing shared uploads storage."
  value       = module.storage.efs_file_system_id
}

output "cloudfront_domain_name" {
  description = "CloudFront's own domain name."
  value       = module.edge.cloudfront_domain_name
}

output "terraform_apply_role_arn" {
  description = "ARN of the narrowly-scoped IAM role used by the infra-apply workflow."
  value       = module.iam.terraform_apply_role_arn
}
