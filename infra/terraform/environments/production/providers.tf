# ==============================================================================
# Provider configuration — no credentials, no live account values
# ==============================================================================
#
# required_version >= 1.11 is necessary for the S3-native state locking
# (use_lockfile) declared in backend.tf.
#
# AWS authentication is never a static access key/secret in this repository.
# The target CI model is GitHub OIDC -> short-lived AWS IAM role assumption
# (see modules/iam); locally, the AWS CLI's normal credential chain
# (environment variables, SSO, or an assumed role) applies — never a
# credential committed to this file or any tfvars file.

terraform {
  required_version = ">= 1.11.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = var.tags
  }
}
