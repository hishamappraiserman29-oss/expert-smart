# ==============================================================================
# Module: secrets
# Status: SCAFFOLD ONLY — zero live resources, zero secret values.
# ==============================================================================
#
# Source of truth: AWS Secrets Manager (chosen over SSM Parameter Store for
# native RDS credential-rotation integration and a stronger audit trail).
#
# Kubernetes delivery: External Secrets Operator — its own IRSA/Pod Identity
# role is owned by modules/iam, not this module. External Secrets Operator
# continuously syncs Secrets Manager entries into a native Kubernetes
# Secret named "expert-smart-secrets" (matching the existing
# kubernetes/deployment.yaml secretKeyRef consumption exactly — no
# application manifest change required). The keys "database-url" and
# "secret-key" are already public knowledge from the committed manifest;
# their VALUES are never present anywhere in this repository or scaffold.
#
# Future ownership (NOT implemented in this scaffold):
#   - aws_secretsmanager_secret entries (names/structure only — no values)
#   - ExternalSecret custom-resource generation target (the CR itself is a
#     Kubernetes manifest owned by kubernetes/, not Terraform)
#   - Rotation configuration for the RDS master credential
#
# TODO(infra-apply-phase): implement aws_secretsmanager_secret (metadata
# only — real secret values are set out-of-band by a human, never via
# Terraform variable or committed file) under a separate, explicitly
# authorized implementation phase. This file intentionally contains no
# resource or data blocks, and no secret value of any kind.
