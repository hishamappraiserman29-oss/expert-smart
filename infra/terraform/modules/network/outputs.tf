# Placeholder interface contract — values are null/empty until this module's
# resources are implemented under a separate, explicitly authorized phase.
# Downstream modules (eks, database, storage, edge) reference these outputs;
# the references are real, the underlying values are not yet populated.

output "vpc_id" {
  description = "ID of the provisioned VPC."
  value       = null
}

output "vpc_cidr_block" {
  description = "CIDR block of the provisioned VPC."
  value       = null
}

output "public_subnet_ids" {
  description = "IDs of the public subnets (ALB, NAT Gateways)."
  value       = []
}

output "private_app_subnet_ids" {
  description = "IDs of the private application subnets (EKS workloads)."
  value       = []
}

output "private_db_subnet_ids" {
  description = "IDs of the private database subnets (RDS, EFS)."
  value       = []
}

output "nat_gateway_ids" {
  description = "IDs of the provisioned NAT Gateways."
  value       = []
}
