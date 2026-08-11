variable "project_name" {
  description = "Project/application name used for resource naming and tagging."
  type        = string
}

variable "environment" {
  description = "Deployment environment name (e.g. \"production\")."
  type        = string
}

variable "aws_region" {
  description = "AWS region the network is provisioned in."
  type        = string
}

variable "vpc_cidr" {
  description = "CIDR block for the VPC."
  type        = string
  default     = "10.0.0.0/16"
}

variable "availability_zones" {
  description = "Availability Zones to spread subnets across. me-central-1 has three AZs."
  type        = list(string)
  default     = ["me-central-1a", "me-central-1b", "me-central-1c"]
}

variable "public_subnet_cidrs" {
  description = "CIDR blocks for public subnets, one per AZ (ALB, NAT Gateways, IGW)."
  type        = list(string)
  default     = []
}

variable "private_app_subnet_cidrs" {
  description = "CIDR blocks for private application subnets, one per AZ (EKS worker nodes / pods)."
  type        = list(string)
  default     = []
}

variable "private_db_subnet_cidrs" {
  description = "CIDR blocks for private database subnets, one per AZ (RDS, EFS mount targets)."
  type        = list(string)
  default     = []
}

variable "single_nat_gateway" {
  description = "If true, use one shared NAT Gateway instead of one per AZ. Cost-sensitive alternative — reduces AZ-independence of egress traffic. Default false matches the stated multi-AZ production requirement."
  type        = bool
  default     = false
}

variable "tags" {
  description = "Common resource tags applied to all network resources."
  type        = map(string)
  default     = {}
}
