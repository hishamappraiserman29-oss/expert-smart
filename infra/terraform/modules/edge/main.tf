# ==============================================================================
# Module: edge
# Status: SCAFFOLD ONLY — zero live resources. Structural contract only.
# ==============================================================================
#
# Origin model: internet-facing ALB (var.alb_internal = false), NOT a
# CloudFront VPC Origin / internal ALB. CloudFront VPC Origins were not
# confirmed available in me-central-1 at the time of the R1 architecture
# review — a documented supported-region list did not include it. This
# module does not hard-code that capability as either present or absent
# long-term: var.cloudfront_vpc_origin_enabled exists as a forward-looking
# toggle (default false) so the topology can move to an internal ALB +
# VPC Origin later, IF AWS confirms regional support, without assuming it
# now.
#
# The ALB itself is NOT created by this module as a standalone Terraform
# resource — it is provisioned dynamically by the AWS Load Balancer
# Controller (a Kubernetes controller, installed by the eks module) in
# response to a Kubernetes Ingress object with target-type=ip. This module
# owns the edge/CDN/WAF layer in front of it; the ALB's ARN/DNS name would
# be discovered via a data source lookup by tag in a later apply phase —
# not created here, and not looked up here either (no live data sources in
# this scaffold).
#
# Direct-origin bypass mitigation (both layers, neither optional):
#   1. ALB security group restricted to inbound only from CloudFront's
#      official managed prefix list (com.amazonaws.global.cloudfront.origin-facing)
#   2. A rotated custom header CloudFront injects on every origin request,
#      enforced by an ALB listener rule — the header value lives in AWS
#      Secrets Manager (modules/secrets), never in Git
#
# TLS: two separate ACM certificates are required, in two separate regions —
#   - CloudFront (viewer TLS): ACM certificate MUST be in us-east-1,
#     regardless of where the origin lives (fixed AWS platform requirement)
#   - ALB (origin TLS, CloudFront -> ALB re-encrypted, not plaintext):
#     ACM certificate in me-central-1 (the ALB's own region)
#
# Future ownership (NOT implemented in this scaffold):
#   - Route 53 hosted zone / record
#   - CloudFront distribution — two cache behaviors (static assets:
#     long TTL, path-only cache key; /api/*: CachingDisabled, forwards
#     Authorization/Cookie/query-strings unmodified — API responses must
#     never be cached cross-user)
#   - AWS WAF WebACL (managed rule groups + rate-based rule), attached to
#     CloudFront; oversize body-inspection handling set to CONTINUE on
#     upload endpoints specifically, since WAF can inspect at most 64 KB of
#     the application's proven 64 MiB upload limit
#   - ACM certificates (us-east-1 for CloudFront, me-central-1 for ALB)
#   - ALB listener rules (custom-header enforcement)
#
# TODO(infra-apply-phase): implement aws_cloudfront_distribution,
# aws_wafv2_web_acl, aws_wafv2_web_acl_association, aws_acm_certificate (x2),
# aws_route53_record under a separate, explicitly authorized implementation
# phase. This file intentionally contains no resource or data blocks.
