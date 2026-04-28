output "five_xx_alert_policy_name" {
  description = "Monitoring alert policy name for Cloud Run 5xx errors."
  value       = length(google_monitoring_alert_policy.cloud_run_5xx) > 0 ? google_monitoring_alert_policy.cloud_run_5xx[0].name : null
}

output "latency_alert_policy_name" {
  description = "Monitoring alert policy name for Cloud Run high latency."
  value       = length(google_monitoring_alert_policy.cloud_run_latency) > 0 ? google_monitoring_alert_policy.cloud_run_latency[0].name : null
}
