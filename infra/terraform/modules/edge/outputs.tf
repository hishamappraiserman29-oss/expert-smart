# Placeholder interface contract — values are null until this module's
# resources are implemented under a separate, explicitly authorized phase.

output "cloudfront_distribution_id" {
  description = "ID of the CloudFront distribution."
  value       = null
}

output "cloudfront_domain_name" {
  description = "CloudFront's own domain name (before any Route 53 alias)."
  value       = null
}

output "waf_web_acl_arn" {
  description = "ARN of the AWS WAF WebACL attached to CloudFront."
  value       = null
}

output "acm_certificate_arn_cloudfront" {
  description = "ARN of the ACM certificate used by CloudFront. Must be issued in us-east-1 regardless of application region."
  value       = null
}

output "acm_certificate_arn_alb" {
  description = "ARN of the ACM certificate used by the regional ALB. Must be issued in the ALB's own region (me-central-1)."
  value       = null
}

output "alb_dns_name" {
  description = "DNS name of the ALB. NOTE: the ALB is controller-created (AWS Load Balancer Controller), not a resource of this module — populated via a data-source lookup in a later apply phase, not by this scaffold."
  value       = null
}
