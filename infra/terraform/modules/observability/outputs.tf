# Placeholder interface contract — values are null/empty until this module's
# resources are implemented under a separate, explicitly authorized phase.

output "cloudwatch_log_group_names" {
  description = "Map of logical log source (control-plane, application, alb, waf) to its CloudWatch Log Group name."
  value       = {}
}

output "dashboard_url" {
  description = "URL of the CloudWatch dashboard, if created."
  value       = null
}

output "alarm_arns" {
  description = "ARNs of the baseline CloudWatch alarms."
  value       = []
}
