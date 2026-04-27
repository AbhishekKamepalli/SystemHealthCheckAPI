output "service_name" {
  description = "Cloud Run service name."
  value       = google_cloud_run_v2_service.this.name
}

output "service_url" {
  description = "Cloud Run service URL."
  value       = google_cloud_run_v2_service.this.uri
}

output "service_account_email" {
  description = "Email of the dedicated Cloud Run runtime service account."
  value       = google_service_account.this.email
}
