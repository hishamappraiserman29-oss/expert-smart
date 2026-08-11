# ==============================================================================
# Root module: production
# Status: SCAFFOLD ONLY — composes module contracts. Zero live resources.
# ==============================================================================
#
# Module dependency graph (forward-only, no cycles):
#
#   network ──┬──> eks ──> iam (needs eks's cluster OIDC issuer for
#             │            Pod/workload identity trust policies)
#             ├──> database
#             ├──> storage
#             └──> edge (public subnets only — the ALB itself is
#                        controller-created, not wired from eks here)
#
#   secrets and observability take root-level variables directly; secrets
#   needs no AWS-resource cross-reference at scaffold level, and
#   observability references eks's cluster_name only, for naming.
#
# Every module.<name>.<output> reference below points at a REAL declared
# output (see each module's outputs.tf) — the reference is genuine, the
# underlying value is currently null/empty because no resource exists yet.
# Nothing here is fabricated to make the graph look complete.

module "network" {
  source = "../../modules/network"

  project_name             = var.project_name
  environment               = var.environment
  aws_region                = var.aws_region
  vpc_cidr                  = var.vpc_cidr
  availability_zones        = var.availability_zones
  public_subnet_cidrs       = var.public_subnet_cidrs
  private_app_subnet_cidrs  = var.private_app_subnet_cidrs
  private_db_subnet_cidrs   = var.private_db_subnet_cidrs
  tags                      = var.tags
}

module "eks" {
  source = "../../modules/eks"

  project_name            = var.project_name
  environment             = var.environment
  vpc_id                  = module.network.vpc_id
  private_app_subnet_ids  = module.network.private_app_subnet_ids
  tags                    = var.tags
}

module "iam" {
  source = "../../modules/iam"

  project_name                 = var.project_name
  environment                  = var.environment
  eks_cluster_oidc_issuer_url  = module.eks.cluster_oidc_issuer_url
  tags                         = var.tags
}

module "database" {
  source = "../../modules/database"

  project_name             = var.project_name
  environment              = var.environment
  instance_class           = var.database_instance_class
  allocated_storage_gb     = var.database_allocated_storage_gb
  backup_retention_days    = var.database_backup_retention_days
  private_db_subnet_ids    = module.network.private_db_subnet_ids
  vpc_security_group_ids   = [module.eks.node_security_group_id]
  tags                     = var.tags
}

module "storage" {
  source = "../../modules/storage"

  project_name             = var.project_name
  environment              = var.environment
  private_app_subnet_ids   = module.network.private_app_subnet_ids
  vpc_security_group_ids   = [module.eks.node_security_group_id]
  tags                     = var.tags
}

module "edge" {
  source = "../../modules/edge"

  project_name          = var.project_name
  environment           = var.environment
  public_subnet_ids     = module.network.public_subnet_ids
  domain_name            = var.domain_name
  production_hostname   = var.production_hostname
  tags                  = var.tags
}

module "secrets" {
  source = "../../modules/secrets"

  project_name = var.project_name
  environment  = var.environment
  tags         = var.tags
}

module "observability" {
  source = "../../modules/observability"

  project_name      = var.project_name
  environment       = var.environment
  eks_cluster_name  = module.eks.cluster_name
  tags              = var.tags
}
