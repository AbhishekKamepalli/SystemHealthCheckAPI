terraform {
  required_version = ">= 1.6.0"

  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 7.0"
    }
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
}

locals {
  name_prefix = "${var.service_name}-${var.environment}"
  labels = {
    app         = var.service_name
    environment = var.environment
    managed_by  = "terraform"
  }
  artifact_repository_id = "${local.name_prefix}-repo"
  container_image = coalesce(
    var.container_image,
    format(
      "%s/%s:%s",
      module.artifact_registry.repository_url,
      var.service_name,
      var.image_tag
    )
  )
}

resource "google_project_service" "required_apis" {
  for_each = toset([
    "artifactregistry.googleapis.com",
    "cloudresourcemanager.googleapis.com",
    "iam.googleapis.com",
    "logging.googleapis.com",
    "monitoring.googleapis.com",
    "run.googleapis.com"
  ])

  project            = var.project_id
  service            = each.value
  disable_on_destroy = false
}

module "artifact_registry" {
  source = "../../modules/artifact-registry"

  project_id    = var.project_id
  region        = var.region
  repository_id = local.artifact_repository_id
  description   = "Docker repository for ${local.name_prefix} images."
  labels        = local.labels

  depends_on = [google_project_service.required_apis]
}

module "cloud_run" {
  source = "../../modules/cloud-run"

  project_id            = var.project_id
  region                = var.region
  service_name          = var.service_name
  environment           = var.environment
  container_image       = local.container_image
  container_port        = var.container_port
  cpu                   = var.cpu
  memory                = var.memory
  timeout               = var.timeout
  min_instance_count    = var.min_instance_count
  max_instance_count    = var.max_instance_count
  allow_unauthenticated = var.allow_unauthenticated
  env_vars              = var.env_vars
  labels                = local.labels

  depends_on = [google_project_service.required_apis]
}

module "monitoring" {
  source = "../../modules/monitoring"

  project_id                   = var.project_id
  region                       = var.region
  service_name                 = var.service_name
  environment                  = var.environment
  notification_channel_ids     = var.notification_channel_ids
  labels                       = local.labels
  enable_5xx_alert             = var.enable_5xx_alert
  five_xx_error_rate_threshold = var.five_xx_error_rate_threshold
  five_xx_alignment_period     = var.five_xx_alignment_period
  five_xx_duration             = var.five_xx_duration
  enable_latency_alert         = var.enable_latency_alert
  latency_threshold_ms         = var.latency_threshold_ms
  latency_alignment_period     = var.latency_alignment_period
  latency_duration             = var.latency_duration
  latency_per_series_aligner   = var.latency_per_series_aligner

  depends_on = [google_project_service.required_apis, module.cloud_run]
}
