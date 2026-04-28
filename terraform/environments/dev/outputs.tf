output "cloud_run_service_url" {
  description = "Public URL of the Cloud Run service."
  value       = module.cloud_run.service_url
}

output "cloud_run_service_name" {
  description = "Cloud Run service name."
  value       = module.cloud_run.service_name
}

output "artifact_registry_repository_name" {
  description = "Artifact Registry repository resource name."
  value       = module.artifact_registry.repository_name
}

output "artifact_registry_repository_url" {
  description = "Artifact Registry repository URL used for docker push and pull."
  value       = module.artifact_registry.repository_url
}

output "cloud_run_service_account_email" {
  description = "Dedicated Cloud Run runtime service account email."
  value       = module.cloud_run.service_account_email
}

output "deployed_container_image" {
  description = "Container image deployed to Cloud Run."
  value       = local.container_image
}

output "monitoring_5xx_alert_policy_name" {
  description = "Cloud Monitoring alert policy name for Cloud Run 5xx errors."
  value       = module.monitoring.five_xx_alert_policy_name
}

output "monitoring_latency_alert_policy_name" {
  description = "Cloud Monitoring alert policy name for Cloud Run high latency."
  value       = module.monitoring.latency_alert_policy_name
}
