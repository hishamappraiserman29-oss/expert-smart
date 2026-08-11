# ==============================================================================
# Module: iam
# Status: SCAFFOLD ONLY — zero live resources. Structural contract only.
# ==============================================================================
#
# This module owns TWO structurally distinct trust relationships. They are
# never conflated:
#
#   1. CI IDENTITY (GitHub Actions -> AWS)
#      GitHub OIDC provider + two IAM roles:
#        - a broad-read / zero-write "plan" role, assumable from any PR,
#          no GitHub Environment gate required (it cannot mutate anything)
#        - a narrowly-scoped "apply"/"deploy" role, assumable only from the
#          `main` branch AND the `production` GitHub Environment claim in
#          the OIDC token's `sub` (double-gated: GitHub-side reviewer
#          approval AND AWS-side trust-policy scoping, independently)
#      No long-lived AWS access keys. No static KUBECONFIG secret as the
#      target architecture — CI generates a short-lived kubeconfig at
#      each run after assuming the apply/deploy role.
#
#   2. POD / WORKLOAD IDENTITY (EKS Pods -> AWS)
#      IRSA (or EKS Pod Identity, evaluated first for its simpler setup)
#      bound to the EKS cluster's own OIDC provider (from the eks module),
#      NOT the GitHub OIDC provider above. Needed by: AWS Load Balancer
#      Controller, EFS CSI driver, External Secrets Operator. The
#      application's own ServiceAccount (`expert-smart-sa`) needs no IAM
#      role initially — no evidence the application calls AWS APIs directly.
#
# Future ownership (NOT implemented in this scaffold):
#   - aws_iam_openid_connect_provider (GitHub OIDC — token.actions.githubusercontent.com)
#   - aws_iam_role "terraform-plan" (broad read, zero write)
#   - aws_iam_role "terraform-apply" / "deploy" (main + production Environment scoped)
#   - aws_iam_role for AWS Load Balancer Controller (IRSA/Pod Identity)
#   - aws_iam_role for EFS CSI driver (IRSA/Pod Identity)
#   - aws_iam_role for External Secrets Operator (IRSA/Pod Identity)
#
# TODO(infra-apply-phase): implement the above under a separate, explicitly
# authorized implementation phase. This file intentionally contains no
# resource or data blocks.
