variable "project_name" {
  description = "Project/application name used for resource naming and tagging."
  type        = string
}

variable "environment" {
  description = "Deployment environment name (e.g. \"production\")."
  type        = string
}

variable "public_subnet_ids" {
  description = "Public subnet IDs for future ALB placement documentation (from the network module). The ALB itself is controller-created, not a resource in this module."
  type        = list(string)
}

variable "domain_name" {
  description = "Root domain name. Apply-time owner input — no default; only the placeholder your-domain.com exists anywhere in the repo today, belonging to an unrelated bare-VM path."
  type        = string
  default     = null
}

variable "production_hostname" {
  description = "Production hostname (e.g. app.example.com). Apply-time owner input — no default."
  type        = string
  default     = null
}

variable "alb_internal" {
  description = "Whether the ALB is internal (true) or internet-facing (false). Locked decision: false — CloudFront VPC Origins are not confirmed available in me-central-1."
  type        = bool
  default     = false
}

variable "cloudfront_vpc_origin_enabled" {
  description = "Forward-looking toggle for a future CloudFront VPC Origin / internal-ALB topology. Default false — do not enable until AWS confirms me-central-1 support."
  type        = bool
  default     = false
}

variable "waf_managed_rule_groups" {
  description = "AWS WAF managed rule group names to attach to the CloudFront WebACL."
  type        = list(string)
  default = [
    "AWSManagedRulesCommonRuleSet",
    "AWSManagedRulesKnownBadInputsRuleSet",
    "AWSManagedRulesSQLiRuleSet",
    "AWSManagedRulesAmazonIpReputationList",
  ]
}

variable "waf_body_inspection_oversize_handling" {
  description = "WAF oversize body-inspection handling for upload endpoints. WAF can inspect at most 64 KB of the application's proven 64 MiB upload limit; CONTINUE allows the uninspected remainder through, paired with application-layer validation."
  type        = string
  default     = "CONTINUE"
}

variable "cloudfront_price_class" {
  description = "CloudFront price class."
  type        = string
  default     = "PriceClass_All"
}

variable "tags" {
  description = "Common resource tags applied to all edge resources."
  type        = map(string)
  default     = {}
}
