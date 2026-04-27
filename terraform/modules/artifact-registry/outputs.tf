output "repository_id" {
  description = "Artifact Registry repository ID."
  value       = google_artifact_registry_repository.this.repository_id
}

output "repository_name" {
  description = "Full Artifact Registry repository resource name."
  value       = google_artifact_registry_repository.this.name
}

output "repository_url" {
  description = "Base registry URL used for docker push and pull operations."
  value = format(
    "%s-docker.pkg.dev/%s/%s",
    var.region,
    var.project_id,
    google_artifact_registry_repository.this.repository_id
  )
}
