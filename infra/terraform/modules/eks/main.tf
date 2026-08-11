# ==============================================================================
# Module: eks
# Status: SCAFFOLD ONLY — zero live resources. Structural contract only.
# ==============================================================================
#
# Future ownership (NOT implemented in this scaffold):
#   - EKS control plane (API server logging: api/audit/authenticator to
#     CloudWatch, enabled from day one)
#   - Managed node groups (EC2, NOT Fargate — Fargate cannot run DaemonSets,
#     has no GPU instance types, and this workload has proven dependencies
#     — scikit-learn / sentence-transformers — better served by deliberately
#     sized EC2 instances; see infra/README.md / R1 architecture review)
#   - Cluster add-ons: VPC CNI, CoreDNS, kube-proxy, metrics-server (required
#     for the existing HPA's cpu/memory Resource metrics), EFS CSI driver
#   - Karpenter (cluster autoscaling)
#   - AWS Load Balancer Controller integration point (the controller itself
#     is Helm-installed by this module in a later phase; it registers Pod
#     IPs directly into ALB target groups via target-type=ip — the ALB is
#     NOT a Terraform-managed resource, it is created by the controller in
#     response to a Kubernetes Ingress object)
#
# TODO(infra-apply-phase): implement aws_eks_cluster, aws_eks_node_group,
# aws_eks_addon (x5), and a helm_release for Karpenter + AWS Load Balancer
# Controller under a separate, explicitly authorized implementation phase.
# This file intentionally contains no resource or data blocks.
