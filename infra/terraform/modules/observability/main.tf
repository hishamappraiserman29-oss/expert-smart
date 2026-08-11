# ==============================================================================
# Module: observability
# Status: SCAFFOLD ONLY — zero live resources. Structural contract only.
# ==============================================================================
#
# Mandatory for first production deployment (see infra/README.md):
#   - CloudWatch Container Insights (or the CloudWatch Observability EKS
#     add-on) for pod/node CPU/memory
#   - EKS control-plane logging (api/audit/authenticator) to CloudWatch
#   - ALB access logs -> S3
#   - Application health monitoring (/api/health, already exists)
#   - Baseline alarms: pod crash-loop count, HPA-at-max-replicas, RDS
#     CPU/storage/connections, 5xx rate at ALB/CloudFront
#
# Deferred to later optimization (not mandatory for first deploy):
#   - Detailed CloudFront/WAF log analysis pipeline
#   - Distributed tracing (no application instrumentation evidence found)
#   - Full dashboard suite
#   - Redis/Ollama metrics (moot until those are actually provisioned)
#
# Future ownership (NOT implemented in this scaffold):
#   - aws_cloudwatch_log_group (EKS control plane, application, ALB, WAF)
#   - aws_cloudwatch_metric_alarm (baseline alarm set above)
#   - aws_cloudwatch_dashboard
#
# TODO(infra-apply-phase): implement the above under a separate, explicitly
# authorized implementation phase. This file intentionally contains no
# resource or data blocks.
